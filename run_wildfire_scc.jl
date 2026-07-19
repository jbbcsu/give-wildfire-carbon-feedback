#!/usr/bin/env julia

# Run from the repository root:
#   julia --project=. wildfire_extension/run_wildfire_scc.jl 100
#
# The optional first argument is the Monte Carlo sample size. Use 10000 for the
# full paper-scale run; smaller values are intended only for smoke tests.

using CSVFiles
using DataFrames
using Dates
using Mimi
using MimiGIVE
using Statistics
using VegaLite

include(joinpath(@__DIR__, "WildfireGIVE.jl"))
include(joinpath(@__DIR__, "..", "src", "discount_rates.jl"))

using .WildfireGIVE

const MODEL_YEARS = collect(1750:2300)
const DAMAGE_YEARS = collect(2020:2300)

function scenario_specs()
    return [
        (label = "baseline", include_wildfire_co2 = false, wildfire_scenario = :baseline),
        (label = "wildfire-low", include_wildfire_co2 = true, wildfire_scenario = :low),
        (label = "wildfire-medium", include_wildfire_co2 = true, wildfire_scenario = :medium),
        (label = "wildfire-high", include_wildfire_co2 = true, wildfire_scenario = :high),
        (label = "wildfire-stress", include_wildfire_co2 = true, wildfire_scenario = :stress),
    ]
end

function _scc_key(results; dr_label = "2.0%", region = :globe, sector = :total)
    for key in keys(results[:scc])
        if key.dr_label == dr_label && key.region == region && key.sector == sector
            return key
        end
    end
    error("No SCC result found for dr=$dr_label, region=$region, sector=$sector.")
end

function summarize_scc(results, scenario_label; dr_label = "2.0%")
    key = _scc_key(results; dr_label = dr_label)
    sccs_2020usd = results[:scc][key].sccs .* MimiGIVE.pricelevel_2005_to_2020
    return (
        scenario = scenario_label,
        dr_label = dr_label,
        mean_scc = mean(sccs_2020usd),
        median_scc = median(sccs_2020usd),
        p05_scc = quantile(sccs_2020usd, 0.05),
        p95_scc = quantile(sccs_2020usd, 0.95),
    )
end

function scc_samples_frame(results, scenario_label; dr_label = "2.0%")
    key = _scc_key(results; dr_label = dr_label)
    sccs_2020usd = results[:scc][key].sccs .* MimiGIVE.pricelevel_2005_to_2020
    return DataFrame(
        scenario = fill(scenario_label, length(sccs_2020usd)),
        dr_label = fill(dr_label, length(sccs_2020usd)),
        trial = collect(1:length(sccs_2020usd)),
        scc_2020usd_per_tco2 = sccs_2020usd,
    )
end

function discounted_marginal_damage_frame(results, scenario_label; dr_label = "2.0%")
    dr = first(filter(x -> x.label == dr_label, discount_rates))
    mds = results[:mds][(region = :globe, sector = :total)]
    cpc = results[:cpc][(region = :globe, sector = :total)]
    year_index = findfirst(isequal(2020), DAMAGE_YEARS)

    out = DataFrame(
        scenario = String[],
        dr_label = String[],
        year = Int[],
        mean_discounted_md = Float64[],
        median_discounted_md = Float64[],
        p05_discounted_md = Float64[],
        p95_discounted_md = Float64[],
    )

    for (col, year) in enumerate(DAMAGE_YEARS)
        factors = (cpc[:, year_index] ./ cpc[:, col]) .^ dr.eta .* (1 / (1 + dr.prtp)^(year - 2020))
        discounted = mds[:, col] .* factors .* MimiGIVE.pricelevel_2005_to_2020
        push!(
            out,
            (
                scenario_label,
                dr_label,
                year,
                mean(discounted),
                median(discounted),
                quantile(discounted, 0.05),
                quantile(discounted, 0.95),
            ),
        )
    end

    return out
end

function deterministic_path_frame(m, scenario_label)
    Mimi.run(m)
    return DataFrame(
        scenario = fill(scenario_label, length(MODEL_YEARS)),
        year = MODEL_YEARS,
        co2_ppm = m[:co2_cycle, :co2],
        total_forcing_wm2 = m[:total_forcing, :total_forcing],
        temperature_c = m[:temperature, :T],
        total_damage_2005usd_per_year = m[:DamageAggregator, :total_damage],
    )
end

function maybe_write_plots(output_dir, wildfire_paths, deterministic_paths, scc_samples, discounted_mds)
    try
        plots_dir = joinpath(output_dir, "plots")
        mkpath(plots_dir)

        wildfire_paths |>
            @vlplot(:line, x = :year, y = :wildfire_gtco2, color = :scenario, width = 650, height = 320) |>
            save(joinpath(plots_dir, "wildfire_emissions_path.html"))

        deterministic_paths |>
            @vlplot(:line, x = :year, y = :co2_ppm, color = :scenario, width = 650, height = 320) |>
            save(joinpath(plots_dir, "co2_concentration_path.html"))

        deterministic_paths |>
            @vlplot(:line, x = :year, y = :temperature_c, color = :scenario, width = 650, height = 320) |>
            save(joinpath(plots_dir, "temperature_path.html"))

        scc_samples |>
            @vlplot(:bar, x = {:scc_2020usd_per_tco2, bin = true}, y = "count()", color = :scenario, width = 650, height = 320) |>
            save(joinpath(plots_dir, "scc_distribution.html"))

        discounted_mds |>
            @vlplot(:line, x = :year, y = :mean_discounted_md, color = :scenario, width = 650, height = 320) |>
            save(joinpath(plots_dir, "discounted_marginal_damages.html"))
    catch err
        @warn "Could not write VegaLite plots; CSV outputs were still written." exception = err
    end
end

function run_experiments(; n = 100, include_stress = false, output_dir = joinpath(@__DIR__, "..", "output", "wildfire_extension"))
    mkpath(output_dir)
    specs = include_stress ? scenario_specs() : scenario_specs()[1:4]

    all_summaries = DataFrame()
    all_samples = DataFrame()
    all_paths = DataFrame()
    all_wildfire_paths = DataFrame()
    all_discounted_mds = DataFrame()

    for spec in specs
        scenario_dir = joinpath(output_dir, spec.label)
        mkpath(scenario_dir)

        m, wildfire_path = WildfireGIVE.get_model(
            include_wildfire_co2 = spec.include_wildfire_co2,
            wildfire_scenario = spec.wildfire_scenario,
            socioeconomics_source = :RFF,
        )

        wildfire_path[!, :scenario] = fill(spec.label, nrow(wildfire_path))
        wildfire_path |> save(joinpath(scenario_dir, "wildfire_emissions_path.csv"))
        append!(all_wildfire_paths, wildfire_path, cols = :union)

        paths = deterministic_path_frame(deepcopy(m), spec.label)
        paths |> save(joinpath(scenario_dir, "deterministic_climate_damage_paths.csv"))
        append!(all_paths, paths, cols = :union)

        results = MimiGIVE.compute_scc(
            m;
            year = 2020,
            last_year = 2300,
            discount_rates = discount_rates,
            fair_parameter_set = :random,
            rffsp_sampling = :random,
            n = n,
            gas = :CO2,
            output_dir = scenario_dir,
            save_md = true,
            save_cpc = true,
            compute_sectoral_values = true,
            compute_domestic_values = false,
            CIAM_foresight = :perfect,
            CIAM_GDPcap = true,
            pulse_size = 1e-4,
        )

        append!(all_summaries, DataFrame([summarize_scc(results, spec.label)]), cols = :union)
        append!(all_samples, scc_samples_frame(results, spec.label), cols = :union)
        append!(all_discounted_mds, discounted_marginal_damage_frame(results, spec.label), cols = :union)
    end

    baseline_mean = only(all_summaries[all_summaries.scenario .== "baseline", :mean_scc])
    all_summaries[!, :delta_mean_scc] = all_summaries.mean_scc .- baseline_mean
    all_summaries[!, :pct_delta_mean_scc] = 100.0 .* all_summaries.delta_mean_scc ./ baseline_mean

    all_summaries |> save(joinpath(output_dir, "scc_summary.csv"))
    all_samples |> save(joinpath(output_dir, "scc_samples.csv"))
    all_wildfire_paths |> save(joinpath(output_dir, "wildfire_emissions_paths.csv"))
    all_paths |> save(joinpath(output_dir, "deterministic_climate_damage_paths.csv"))
    all_discounted_mds |> save(joinpath(output_dir, "discounted_marginal_damages.csv"))

    # A direct plot-friendly difference from baseline for discounted marginal damages.
    baseline_mds = all_discounted_mds[all_discounted_mds.scenario .== "baseline", [:year, :mean_discounted_md]]
    rename!(baseline_mds, :mean_discounted_md => :baseline_mean_discounted_md)
    md_diff = leftjoin(all_discounted_mds, baseline_mds, on = :year)
    md_diff[!, :delta_mean_discounted_md] = md_diff.mean_discounted_md .- md_diff.baseline_mean_discounted_md
    md_diff |> save(joinpath(output_dir, "discounted_marginal_damage_differences.csv"))

    maybe_write_plots(output_dir, all_wildfire_paths, all_paths, all_samples, all_discounted_mds)

    return all_summaries
end

function main()
    n = length(ARGS) >= 1 ? parse(Int, ARGS[1]) : 100
    include_stress = length(ARGS) >= 2 ? parse(Bool, ARGS[2]) : false
    output_dir = length(ARGS) >= 3 ? ARGS[3] : joinpath(@__DIR__, "..", "output", "wildfire_extension")

    println("Running wildfire SCC experiments with n=$n. Output: $output_dir")
    summaries = run_experiments(n = n, include_stress = include_stress, output_dir = output_dir)
    println(summaries)
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
