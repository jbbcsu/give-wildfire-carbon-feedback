#!/usr/bin/env julia

# Quick deterministic wildfire-carbon SCC experiment.
#
# This is intentionally not the full Rennert et al. Monte Carlo. It uses one
# deterministic GIVE model configuration: the default RFF-SP sample in MimiRFFSPs
# and the non-MCS `MimiGIVE.compute_scc(..., n=0)` path.

using CSVFiles
using DataFrames
using Mimi
using MimiGIVE

include(joinpath(@__DIR__, "WildfireGIVE.jl"))
include(joinpath(@__DIR__, "..", "src", "discount_rates.jl"))

using .WildfireGIVE

const MODEL_YEARS = collect(1750:2300)

function scenario_specs(mode::Symbol)
    if mode == :temperature
        return [
            (label = "baseline", scenario = :baseline, include_wildfire_co2 = false, path_kind = :baseline),
            (label = "climate-fire-low", scenario = :low, include_wildfire_co2 = true, path_kind = :temperature),
            (label = "climate-fire-medium", scenario = :medium, include_wildfire_co2 = true, path_kind = :temperature),
            (label = "climate-fire-high", scenario = :high, include_wildfire_co2 = true, path_kind = :temperature),
        ]
    elseif mode == :canada2023
        return [
            (label = "baseline", scenario = :baseline, include_wildfire_co2 = false, path_kind = :baseline),
            (label = "canada2023-low", scenario = :low, include_wildfire_co2 = true, path_kind = :canada2023),
            (label = "canada2023-medium", scenario = :medium, include_wildfire_co2 = true, path_kind = :canada2023),
            (label = "canada2023-high", scenario = :high, include_wildfire_co2 = true, path_kind = :canada2023),
        ]
    else
        error("Unknown quick-run mode $mode. Use :temperature or :canada2023.")
    end
end

function deterministic_path_frame(m, scenario_label)
    Mimi.run(m)
    return DataFrame(
        scenario = fill(scenario_label, length(MODEL_YEARS)),
        year = MODEL_YEARS,
        co2_emissions_gtc = m[:co2_cycle, :E_co2],
        co2_ppm = m[:co2_cycle, :co2],
        total_forcing_wm2 = m[:total_forcing, :total_forcing],
        temperature_c = m[:temperature, :T],
        total_damage_2005usd_per_year = m[:DamageAggregator, :total_damage],
    )
end

function deterministic_scc_frame(m, scenario_label)
    results = MimiGIVE.compute_scc(
        m;
        year = 2020,
        last_year = 2300,
        discount_rates = discount_rates,
        n = 0,
        gas = :CO2,
        compute_domestic_values = false,
        CIAM_foresight = :perfect,
        CIAM_GDPcap = true,
        # The deterministic n=0 SCC helper relies on Mimi's MarginalModel scaling
        # and is stable with its historical 1 GtC pulse. The replication MCS uses
        # a smaller 1e-4 GtC pulse and normalizes it in the post-trial function.
        pulse_size = 1.0,
    )

    out = DataFrame(
        scenario = String[],
        dr_label = String[],
        prtp = Float64[],
        eta = Float64[],
        scc_2005usd_per_tco2 = Float64[],
        scc_2020usd_per_tco2 = Float64[],
    )

    for key in sort(collect(keys(results)), by = x -> x.dr_label)
        push!(
            out,
            (
                scenario_label,
                key.dr_label,
                key.prtp,
                key.eta,
                results[key],
                results[key] * MimiGIVE.pricelevel_2005_to_2020,
            ),
        )
    end

    return out
end

function add_baseline_differences!(scc::DataFrame)
    baseline = Dict(
        row.dr_label => row.scc_2020usd_per_tco2
        for row in eachrow(scc)
        if row.scenario == "baseline"
    )

    scc[!, :delta_scc_2020usd_per_tco2] = [
        row.scc_2020usd_per_tco2 - baseline[row.dr_label]
        for row in eachrow(scc)
    ]
    scc[!, :pct_delta_scc] = [
        100.0 * (row.scc_2020usd_per_tco2 - baseline[row.dr_label]) / baseline[row.dr_label]
        for row in eachrow(scc)
    ]

    return scc
end

function run_quick(; output_dir = joinpath(@__DIR__, "..", "output", "wildfire_quick"), mode::Symbol = :temperature)
    mkpath(output_dir)

    baseline_model, baseline_wildfire_path = WildfireGIVE.get_model(
        include_wildfire_co2 = false,
        socioeconomics_source = :RFF,
    )
    baseline_paths = deterministic_path_frame(deepcopy(baseline_model), "baseline")

    all_scc = DataFrame()
    all_paths = DataFrame()
    all_wildfire_paths = DataFrame()

    for spec in scenario_specs(mode)
        scenario_dir = joinpath(output_dir, spec.label)
        mkpath(scenario_dir)

        if spec.label == "baseline"
            m = baseline_model
            wildfire_path = baseline_wildfire_path
        elseif spec.path_kind == :temperature
            wildfire_path = WildfireGIVE.climate_response_wildfire_path(
                scenario = spec.scenario,
                years = baseline_paths.year,
                temperature_c = baseline_paths.temperature_c,
            )
            m, _ = WildfireGIVE.get_model(
                include_wildfire_co2 = true,
                wildfire_scenario = :custom,
                custom_gtco2 = wildfire_path.wildfire_gtco2,
                socioeconomics_source = :RFF,
            )
        elseif spec.path_kind == :canada2023
            wildfire_path = WildfireGIVE.canada_2023_excess_wildfire_path(
                scenario = spec.scenario,
                years = baseline_paths.year,
                temperature_c = baseline_paths.temperature_c,
            )
            m, _ = WildfireGIVE.get_model(
                include_wildfire_co2 = true,
                wildfire_scenario = :custom,
                custom_gtco2 = wildfire_path.wildfire_gtco2,
                socioeconomics_source = :RFF,
            )
        else
            error("Unsupported path kind $(spec.path_kind).")
        end

        wildfire_path[!, :scenario] = fill(spec.label, nrow(wildfire_path))
        wildfire_path |> save(joinpath(scenario_dir, "wildfire_emissions_path.csv"))
        append!(all_wildfire_paths, wildfire_path, cols = :union)

        paths =
            spec.label == "baseline" ? baseline_paths :
            deterministic_path_frame(deepcopy(m), spec.label)
        paths |> save(joinpath(scenario_dir, "deterministic_climate_damage_paths.csv"))
        append!(all_paths, paths, cols = :union)

        scc = deterministic_scc_frame(m, spec.label)
        scc |> save(joinpath(scenario_dir, "deterministic_scc.csv"))
        append!(all_scc, scc, cols = :union)
    end

    add_baseline_differences!(all_scc)

    all_scc |> save(joinpath(output_dir, "deterministic_scc_summary.csv"))
    all_paths |> save(joinpath(output_dir, "deterministic_climate_damage_paths.csv"))
    all_wildfire_paths |> save(joinpath(output_dir, "wildfire_emissions_paths.csv"))

    return all_scc
end

function main()
    output_dir = length(ARGS) >= 1 ? ARGS[1] : joinpath(@__DIR__, "..", "output", "wildfire_quick")
    mode = length(ARGS) >= 2 ? Symbol(ARGS[2]) : :temperature
    println("Running deterministic quick wildfire SCC experiment. Mode: $mode. Output: $output_dir")
    scc = run_quick(output_dir = output_dir, mode = mode)
    println(scc[scc.dr_label .== "2.0%", :])
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
