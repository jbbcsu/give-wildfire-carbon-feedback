#!/usr/bin/env julia

# Run a source-informed wildfire uncertainty experiment.
# This is intentionally a small Monte Carlo (default n=100), not the 10,000-draw
# Rennert et al. replication.

using CSVFiles
using DataFrames
using Mimi
using MimiGIVE
using Random
using Statistics

import Mimi: SampleStore, add_RV!, add_transform!

include(joinpath(@__DIR__, "WildfireGIVE.jl"))
include(joinpath(@__DIR__, "..", "src", "discount_rates.jl"))

using .WildfireGIVE

const MODEL_YEARS = collect(1750:2300)

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

function wildfire_path_matrix(emissions_draws::DataFrame, n::Int)
    years = sort(unique(emissions_draws.year))
    matrix = Array{Float64}(undef, n, length(years))
    for draw in 1:n
        rows = emissions_draws[emissions_draws.draw .== draw, :]
        sort!(rows, :year)
        matrix[draw, :] .= rows.wildfire_gtc
    end
    return years, matrix
end

function wildfire_mcs_hook(path_years, path_matrix)
    return function (mcs)
        for (i, year) in enumerate(path_years)
            rv_name = Symbol("rv_wildfire_co2_gtc_$year")
            add_RV!(mcs, rv_name, SampleStore(path_matrix[:, i]))
            add_transform!(mcs, :wildfire_co2_emissions_add, :(=), rv_name, [year])
        end
    end
end

function scc_samples_frame(results, scenario_label; dr_label = "2.0%")
    out = DataFrame()
    for key in keys(results[:scc])
        sccs_2020usd = results[:scc][key].sccs .* MimiGIVE.pricelevel_2005_to_2020
        append!(
            out,
            DataFrame(
                scenario = fill(scenario_label, length(sccs_2020usd)),
                dr_label = fill(key.dr_label, length(sccs_2020usd)),
                prtp = fill(key.prtp, length(sccs_2020usd)),
                eta = fill(key.eta, length(sccs_2020usd)),
                trial = collect(1:length(sccs_2020usd)),
                scc_2020usd_per_tco2 = sccs_2020usd,
            ),
            cols = :union,
        )
    end
    return out
end

function summarize_scc(samples::DataFrame)
    return combine(
        groupby(samples, [:scenario, :dr_label, :prtp, :eta]),
        :scc_2020usd_per_tco2 => mean => :mean_scc,
        :scc_2020usd_per_tco2 => median => :median_scc,
        :scc_2020usd_per_tco2 => (x -> quantile(x, 0.05)) => :p05_scc,
        :scc_2020usd_per_tco2 => (x -> quantile(x, 0.95)) => :p95_scc,
    )
end

function add_differences!(summary::DataFrame)
    baseline = Dict(
        row.dr_label => row.mean_scc
        for row in eachrow(summary)
        if row.scenario == "baseline"
    )
    baseline_median = Dict(
        row.dr_label => row.median_scc
        for row in eachrow(summary)
        if row.scenario == "baseline"
    )

    summary[!, :delta_mean_scc] = [
        row.mean_scc - baseline[row.dr_label]
        for row in eachrow(summary)
    ]
    summary[!, :pct_delta_mean_scc] = [
        100.0 * (row.mean_scc - baseline[row.dr_label]) / baseline[row.dr_label]
        for row in eachrow(summary)
    ]
    summary[!, :delta_median_scc] = [
        row.median_scc - baseline_median[row.dr_label]
        for row in eachrow(summary)
    ]
    return summary
end

function write_scc_distribution_svg(samples::DataFrame, summary::DataFrame, output_path::String; dr_label = "2.0%")
    data = samples[samples.dr_label .== dr_label, :]
    stats = summary[summary.dr_label .== dr_label, :]

    width = 960
    height = 560
    left = 78
    right = 30
    top = 42
    bottom = 72
    plot_w = width - left - right
    plot_h = height - top - bottom
    bins = 30

    xmin = minimum(data.scc_2020usd_per_tco2)
    xmax = maximum(data.scc_2020usd_per_tco2)
    pad = 0.05 * (xmax - xmin)
    xmin -= pad
    xmax += pad
    bin_width = (xmax - xmin) / bins

    scenarios = unique(data.scenario)
    colors = Dict("baseline" => "#3764ad", "wildfire-source-uncertainty" => "#c45135")

    counts = Dict{String,Vector{Int}}()
    ymax = 0
    for scenario in scenarios
        values = data[data.scenario .== scenario, :scc_2020usd_per_tco2]
        c = zeros(Int, bins)
        for value in values
            idx = clamp(floor(Int, (value - xmin) / bin_width) + 1, 1, bins)
            c[idx] += 1
        end
        counts[scenario] = c
        ymax = max(ymax, maximum(c))
    end

    xscale(x) = left + (x - xmin) / (xmax - xmin) * plot_w
    yscale(y) = top + plot_h - y / ymax * plot_h

    mkpath(dirname(output_path))
    open(output_path, "w") do io
        println(io, """<svg xmlns="http://www.w3.org/2000/svg" width="$width" height="$height" viewBox="0 0 $width $height">""")
        println(io, """<rect width="100%" height="100%" fill="white"/>""")
        println(io, """<text x="$(left)" y="24" font-size="18" font-family="Arial" font-weight="700">SCC distribution, $dr_label discount case (n=$(length(unique(data.trial))))</text>""")
        println(io, """<line x1="$left" y1="$(top + plot_h)" x2="$(left + plot_w)" y2="$(top + plot_h)" stroke="#333"/>""")
        println(io, """<line x1="$left" y1="$top" x2="$left" y2="$(top + plot_h)" stroke="#333"/>""")
        println(io, """<text x="$(left + plot_w / 2)" y="$(height - 22)" text-anchor="middle" font-size="13" font-family="Arial">2020 USD per tCO2</text>""")
        println(io, """<text transform="translate(22,$(top + plot_h / 2)) rotate(-90)" text-anchor="middle" font-size="13" font-family="Arial">Count</text>""")

        for (scenario_index, scenario) in enumerate(scenarios)
            color = get(colors, scenario, "#777")
            offset = (scenario_index - 1.5) * (plot_w / bins) * 0.22
            for i in 1:bins
                c = counts[scenario][i]
                x0 = xscale(xmin + (i - 1) * bin_width) + offset
                x1 = xscale(xmin + i * bin_width) + offset
                y0 = yscale(c)
                bar_w = max(x1 - x0, 1.0) * 0.62
                println(io, """<rect x="$x0" y="$y0" width="$bar_w" height="$(top + plot_h - y0)" fill="$color" opacity="0.48"/>""")
            end
        end

        for row in eachrow(stats)
            color = get(colors, row.scenario, "#777")
            mx = xscale(row.mean_scc)
            md = xscale(row.median_scc)
            println(io, """<line x1="$mx" y1="$top" x2="$mx" y2="$(top + plot_h)" stroke="$color" stroke-width="2"/>""")
            println(io, """<line x1="$md" y1="$top" x2="$md" y2="$(top + plot_h)" stroke="$color" stroke-width="2" stroke-dasharray="5,5"/>""")
            label_y = row.scenario == "baseline" ? top + 18 : top + 38
            println(io, """<text x="$(mx + 4)" y="$label_y" font-size="12" font-family="Arial" fill="$color">$(row.scenario) mean $(round(row.mean_scc, digits=1))</text>""")
            println(io, """<text x="$(md + 4)" y="$(label_y + 15)" font-size="12" font-family="Arial" fill="$color">median $(round(row.median_scc, digits=1))</text>""")
        end

        legend_y = height - 46
        for (i, scenario) in enumerate(scenarios)
            color = get(colors, scenario, "#777")
            x = left + (i - 1) * 250
            println(io, """<rect x="$x" y="$legend_y" width="16" height="16" fill="$color" opacity="0.65"/>""")
            println(io, """<text x="$(x + 22)" y="$(legend_y + 13)" font-size="12" font-family="Arial">$scenario</text>""")
        end
        println(io, "</svg>")
    end
end

function compute_scc_mcs(m; n, output_dir, seed, post_hook = nothing, fair_ids, rff_ids)
    Random.seed!(seed)
    return MimiGIVE.compute_scc(
        m;
        year = 2020,
        last_year = 2300,
        discount_rates = discount_rates,
        fair_parameter_set = :deterministic,
        fair_parameter_set_ids = fair_ids,
        rffsp_sampling = :deterministic,
        rffsp_sampling_ids = rff_ids,
        n = n,
        gas = :CO2,
        output_dir = output_dir,
        save_md = false,
        save_cpc = false,
        compute_sectoral_values = false,
        compute_domestic_values = false,
        CIAM_foresight = :perfect,
        CIAM_GDPcap = true,
        post_mcs_creation_function = post_hook,
        pulse_size = 1e-4,
    )
end

function run_experiment(; n = 100, output_dir = joinpath(@__DIR__, "..", "output", "wildfire_source_uncertainty_100"), seed = 20260502)
    mkpath(output_dir)

    baseline_model = MimiGIVE.get_model(socioeconomics_source = :RFF)
    baseline_paths = deterministic_path_frame(deepcopy(baseline_model), "baseline")
    baseline_paths |> save(joinpath(output_dir, "baseline_deterministic_climate_damage_paths.csv"))

    parameter_draws, emissions_draws = WildfireGIVE.source_informed_wildfire_draws(
        n = n,
        years = baseline_paths.year,
        temperature_c = baseline_paths.temperature_c,
        seed = seed,
    )
    parameter_draws |> save(joinpath(output_dir, "wildfire_parameter_draws.csv"))
    emissions_draws |> save(joinpath(output_dir, "wildfire_emissions_draws.csv"))

    wildfire_years, wildfire_matrix = wildfire_path_matrix(emissions_draws, n)
    hook = wildfire_mcs_hook(wildfire_years, wildfire_matrix)

    fair_rng = MersenneTwister(seed + 1)
    rff_rng = MersenneTwister(seed + 2)
    fair_ids = rand(fair_rng, 1:2237, n)
    rff_ids = rand(rff_rng, 1:10_000, n)
    DataFrame(trial = 1:n, fair_parameter_set_id = fair_ids, rffsp_sample_id = rff_ids) |>
        save(joinpath(output_dir, "paired_mcs_ids.csv"))

    baseline_results = compute_scc_mcs(
        baseline_model;
        n = n,
        output_dir = joinpath(output_dir, "baseline"),
        seed = seed + 3,
        fair_ids = fair_ids,
        rff_ids = rff_ids,
    )

    wildfire_model, _ = WildfireGIVE.get_model(
        include_wildfire_co2 = true,
        wildfire_scenario = :baseline,
        socioeconomics_source = :RFF,
    )

    wildfire_results = compute_scc_mcs(
        wildfire_model;
        n = n,
        output_dir = joinpath(output_dir, "wildfire-source-uncertainty"),
        seed = seed + 3,
        post_hook = hook,
        fair_ids = fair_ids,
        rff_ids = rff_ids,
    )

    samples = vcat(
        scc_samples_frame(baseline_results, "baseline"),
        scc_samples_frame(wildfire_results, "wildfire-source-uncertainty"),
        cols = :union,
    )
    summary = summarize_scc(samples)
    add_differences!(summary)

    samples |> save(joinpath(output_dir, "scc_samples.csv"))
    summary |> save(joinpath(output_dir, "scc_summary.csv"))
    write_scc_distribution_svg(
        samples,
        summary,
        joinpath(output_dir, "scc_distribution_2pct.svg"),
        dr_label = "2.0%",
    )

    println(summary[summary.dr_label .== "2.0%", :])
    return summary
end

function main()
    n = length(ARGS) >= 1 ? parse(Int, ARGS[1]) : 100
    output_dir = length(ARGS) >= 2 ? ARGS[2] : joinpath(@__DIR__, "..", "output", "wildfire_source_uncertainty_100")
    seed = length(ARGS) >= 3 ? parse(Int, ARGS[3]) : 20260502
    println("Running source-informed wildfire SCC uncertainty experiment with n=$n. Output: $output_dir")
    run_experiment(n = n, output_dir = output_dir, seed = seed)
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
