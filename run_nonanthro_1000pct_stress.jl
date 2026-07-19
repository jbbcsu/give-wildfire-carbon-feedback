#!/usr/bin/env julia

# Deliberately extreme static stress test:
# increase the non-anthropogenic/fire-carbon addition by 1000% (10x) and
# compute a deterministic SCC. This is not a scientifically defensible scenario;
# it is a model-behavior diagnostic.

using CSVFiles
using DataFrames
using Mimi
using MimiGIVE
using Statistics

include(joinpath(@__DIR__, "WildfireGIVE.jl"))
include(joinpath(@__DIR__, "..", "src", "discount_rates.jl"))

using .WildfireGIVE

const MODEL_YEARS = collect(1750:2300)
const GROSS_REFERENCE_FIRE_GTC = 2.2
const STRESS_MULTIPLIER = 10.0

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

function source_informed_mean_path(baseline_paths; n = 100, seed = 20260502)
    _, emissions_draws = WildfireGIVE.source_informed_wildfire_draws(
        n = n,
        years = baseline_paths.year,
        temperature_c = baseline_paths.temperature_c,
        seed = seed,
    )
    mean_path = combine(
        groupby(emissions_draws, :year),
        :wildfire_gtco2 => mean => :wildfire_gtco2,
        :wildfire_gtc => mean => :wildfire_gtc,
    )
    sort!(mean_path, :year)
    return mean_path
end

function summarize_benchmark_paths(paths::DataFrame, baseline_paths::DataFrame)
    years = [2020, 2030, 2050, 2100, 2200, 2300]
    out = DataFrame()
    for scenario in unique(paths.scenario), year in years
        row = only(paths[(paths.scenario .== scenario) .& (paths.year .== year), :])
        base = only(baseline_paths[baseline_paths.year .== year, :])
        push!(
            out,
            (
                scenario = scenario,
                year = year,
                co2_emissions_gtc = row.co2_emissions_gtc,
                co2_emissions_delta_gtc = row.co2_emissions_gtc - base.co2_emissions_gtc,
                co2_ppm = row.co2_ppm,
                co2_ppm_delta = row.co2_ppm - base.co2_ppm,
                temperature_c = row.temperature_c,
                temperature_delta_c = row.temperature_c - base.temperature_c,
                total_damage_2020usd_per_year = row.total_damage_2005usd_per_year * MimiGIVE.pricelevel_2005_to_2020,
                total_damage_delta_2020usd_per_year = (row.total_damage_2005usd_per_year - base.total_damage_2005usd_per_year) * MimiGIVE.pricelevel_2005_to_2020,
            ),
        )
    end
    return out
end

function run_stress(output_dir = joinpath(@__DIR__, "..", "output", "nonanthro_1000pct_stress"))
    mkpath(output_dir)

    baseline_model, _ = WildfireGIVE.get_model(
        include_wildfire_co2 = false,
        socioeconomics_source = :RFF,
    )
    baseline_paths = deterministic_path_frame(deepcopy(baseline_model), "baseline")

    mean_path = source_informed_mean_path(baseline_paths)
    source_gtco2 = mean_path.wildfire_gtco2 .* STRESS_MULTIPLIER
    gross_gtco2 = [
        year >= 2020 ? GROSS_REFERENCE_FIRE_GTC * STRESS_MULTIPLIER * WildfireGIVE.GTC_TO_GTCO2 : 0.0
        for year in MODEL_YEARS
    ]

    scenarios = [
        (
            label = "baseline",
            model = baseline_model,
            added_gtco2 = zeros(length(MODEL_YEARS)),
        ),
        (
            label = "10x_source_informed_mean",
            model = WildfireGIVE.get_model(
                include_wildfire_co2 = true,
                wildfire_scenario = :custom,
                custom_gtco2 = source_gtco2,
                socioeconomics_source = :RFF,
            )[1],
            added_gtco2 = source_gtco2,
        ),
        (
            label = "10x_gross_global_fire_2p2GtC",
            model = WildfireGIVE.get_model(
                include_wildfire_co2 = true,
                wildfire_scenario = :custom,
                custom_gtco2 = gross_gtco2,
                socioeconomics_source = :RFF,
            )[1],
            added_gtco2 = gross_gtco2,
        ),
    ]

    all_paths = DataFrame()
    all_scc = DataFrame()
    added_paths = DataFrame()

    for scenario in scenarios
        path = deterministic_path_frame(deepcopy(scenario.model), scenario.label)
        append!(all_paths, path, cols = :union)
        append!(all_scc, deterministic_scc_frame(scenario.model, scenario.label), cols = :union)
        append!(
            added_paths,
            DataFrame(
                scenario = fill(scenario.label, length(MODEL_YEARS)),
                year = MODEL_YEARS,
                added_gtco2_per_year = scenario.added_gtco2,
                added_gtc_per_year = scenario.added_gtco2 .* WildfireGIVE.GTCO2_TO_GTC,
            ),
            cols = :union,
        )
    end

    add_baseline_differences!(all_scc)
    path_summary = summarize_benchmark_paths(all_paths, baseline_paths)

    all_scc |> save(joinpath(output_dir, "deterministic_scc_summary.csv"))
    all_paths |> save(joinpath(output_dir, "deterministic_climate_damage_paths.csv"))
    added_paths |> save(joinpath(output_dir, "added_nonanthro_carbon_paths.csv"))
    path_summary |> save(joinpath(output_dir, "benchmark_path_summary.csv"))

    println("2.0% SCC:")
    println(all_scc[all_scc.dr_label .== "2.0%", :])
    println("Benchmark paths:")
    println(path_summary)
    return all_scc
end

if abspath(PROGRAM_FILE) == @__FILE__
    output_dir = length(ARGS) >= 1 ? ARGS[1] : joinpath(@__DIR__, "..", "output", "nonanthro_1000pct_stress")
    run_stress(output_dir)
end
