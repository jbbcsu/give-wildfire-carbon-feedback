#!/usr/bin/env julia

# Monte Carlo SCC experiment for temperature-dependent wildfire CO2 feedbacks.
#
# The script pairs RFF-SP and FAIR draws across baseline and feedback scenarios.
# Feedback-parameter uncertainty is sampled with transparent scenario-specific
# triangular distributions. The residual cases are the double-counting-cautious
# cases; RESFire cases are gross stress diagnostics.

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
const SCC_YEAR = 2020
const PULSE_SIZE_GTC = 1e-4
const GROSS_REFERENCE_FIRE_CARBON_PGC = 2.2

function triangular(rng::AbstractRNG, low::Real, mode::Real, high::Real)
    low = Float64(low)
    mode = Float64(mode)
    high = Float64(high)
    low <= mode <= high || error("Triangular parameters must satisfy low <= mode <= high.")
    u = rand(rng)
    c = (mode - low) / (high - low)
    if u < c
        return low + sqrt(u * (high - low) * (mode - low))
    else
        return high - sqrt((1.0 - u) * (high - low) * (high - mode))
    end
end

function deterministic_path_frame(m, scenario_label)
    Mimi.run(m)
    feedback_gtc =
        try
            m[:wildfire_temperature_feedback_co2, :feedback_gtc]
        catch
            zeros(length(MODEL_YEARS))
        end
    return DataFrame(
        scenario = fill(scenario_label, length(MODEL_YEARS)),
        year = MODEL_YEARS,
        co2_emissions_gtc = m[:co2_cycle, :E_co2],
        feedback_fire_gtco2 = feedback_gtc .* WildfireGIVE.GTC_TO_GTCO2,
        co2_ppm = m[:co2_cycle, :co2],
        total_forcing_wm2 = m[:total_forcing, :total_forcing],
        temperature_c = m[:temperature, :T],
        total_damage_2005usd_per_year = m[:DamageAggregator, :total_damage],
    )
end

function calibrate_resfire_sensitivity(baseline_paths::DataFrame; target_cumulative_gtco2::Real = 111.889)
    ref_temp = only(baseline_paths[baseline_paths.year .== SCC_YEAR, :]).temperature_c
    gross_reference_fire_gtco2 = GROSS_REFERENCE_FIRE_CARBON_PGC * WildfireGIVE.GTC_TO_GTCO2
    denominator = 0.0

    for row in eachrow(baseline_paths)
        if 2021 <= row.year <= 2050
            lag_temp = only(baseline_paths[baseline_paths.year .== row.year - 1, :]).temperature_c
            denominator += gross_reference_fire_gtco2 * max(lag_temp - ref_temp, 0.0)
        end
    end

    denominator > 0.0 || error("Cannot calibrate RESFire sensitivity.")
    return Float64(target_cumulative_gtco2) / denominator
end

function scenario_draws(scenario::String, n::Int, seed::Int, resfire_sensitivity::Float64)
    rng = MersenneTwister(seed)
    rows = DataFrame(
        trial = collect(1:n),
        scenario = fill(scenario, n),
        sensitivity_per_c = zeros(n),
        net_persistence_fraction = zeros(n),
        not_embedded_fraction = zeros(n),
        resfire_multiplier = ones(n),
        source_note = fill("", n),
    )

    for trial in 1:n
        if scenario == "baseline"
            rows.sensitivity_per_c[trial] = 0.0
            rows.net_persistence_fraction[trial] = 0.0
            rows.not_embedded_fraction[trial] = 0.0
            rows.source_note[trial] = "No wildfire feedback."
        elseif scenario == "feedback-residual-medium"
            rows.sensitivity_per_c[trial] = triangular(rng, 0.07, 0.10, 0.15)
            rows.net_persistence_fraction[trial] = triangular(rng, 0.05, 0.10, 0.20)
            rows.not_embedded_fraction[trial] = triangular(rng, 0.25, 0.50, 0.75)
            rows.source_note[trial] = "Double-counting-cautious residual draw."
        elseif scenario == "feedback-residual-high"
            rows.sensitivity_per_c[trial] = triangular(rng, 0.25, 0.50, 0.75)
            rows.net_persistence_fraction[trial] = triangular(rng, 0.15, 0.30, 0.50)
            rows.not_embedded_fraction[trial] = triangular(rng, 0.50, 0.75, 1.00)
            rows.source_note[trial] = "High residual draw with partial double-counting protection."
        elseif scenario == "feedback-resfire-half-gross"
            multiplier = triangular(rng, 0.50, 1.00, 1.50)
            rows.resfire_multiplier[trial] = multiplier
            rows.sensitivity_per_c[trial] = 0.50 * resfire_sensitivity * multiplier
            rows.net_persistence_fraction[trial] = 1.0
            rows.not_embedded_fraction[trial] = 1.0
            rows.source_note[trial] = "Half-gross RESFire stress draw; not netted or embedded-adjusted."
        elseif scenario == "feedback-resfire-gross"
            multiplier = triangular(rng, 0.50, 1.00, 1.50)
            rows.resfire_multiplier[trial] = multiplier
            rows.sensitivity_per_c[trial] = resfire_sensitivity * multiplier
            rows.net_persistence_fraction[trial] = 1.0
            rows.not_embedded_fraction[trial] = 1.0
            rows.source_note[trial] = "Gross RESFire stress draw; not netted or embedded-adjusted."
        else
            error("Unknown scenario: $scenario")
        end
    end

    return rows
end

function feedback_mcs_hook(draws::DataFrame)
    return function (mcs)
        add_RV!(mcs, :rv_wildfire_sensitivity_per_c, SampleStore(draws.sensitivity_per_c))
        add_transform!(mcs, :wildfire_temperature_feedback_co2, :sensitivity_per_c, :(=), :rv_wildfire_sensitivity_per_c)

        add_RV!(mcs, :rv_wildfire_net_persistence_fraction, SampleStore(draws.net_persistence_fraction))
        add_transform!(mcs, :wildfire_temperature_feedback_co2, :net_persistence_fraction, :(=), :rv_wildfire_net_persistence_fraction)

        add_RV!(mcs, :rv_wildfire_not_embedded_fraction, SampleStore(draws.not_embedded_fraction))
        add_transform!(mcs, :wildfire_temperature_feedback_co2, :not_embedded_fraction, :(=), :rv_wildfire_not_embedded_fraction)
    end
end

function build_model(scenario::String)
    if scenario == "baseline"
        return MimiGIVE.get_model(socioeconomics_source = :RFF)
    end

    m, _ = WildfireGIVE.get_model(
        include_wildfire_co2 = false,
        socioeconomics_source = :RFF,
    )
    WildfireGIVE.apply_wildfire_temperature_feedback_co2!(
        m;
        start_year = SCC_YEAR,
        reference_temperature_year = SCC_YEAR,
        gross_reference_fire_carbon_pgc = GROSS_REFERENCE_FIRE_CARBON_PGC,
        sensitivity_per_c = 0.0,
        net_persistence_fraction = 0.0,
        not_embedded_fraction = 0.0,
        max_feedback_gtco2 = 100.0,
        ar6_scenario = "ssp245",
    )
    return m
end

function compute_scc_mcs(m; n::Int, output_dir::String, fair_ids, rff_ids, post_hook = nothing, mcs_seed::Int = 20260503)
    # MimiGIVE's MCS setup samples several non-FAIR/non-RFF uncertainties with
    # rand(...). Resetting the RNG for each scenario pairs those uncertainty
    # streams across baseline and wildfire cases.
    Random.seed!(mcs_seed)
    return MimiGIVE.compute_scc(
        m;
        year = SCC_YEAR,
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
        pulse_size = PULSE_SIZE_GTC,
    )
end

function scc_samples_frame(results, scenario::String)
    out = DataFrame()
    for key in keys(results[:scc])
        sccs = results[:scc][key].sccs .* MimiGIVE.pricelevel_2005_to_2020
        append!(
            out,
            DataFrame(
                scenario = fill(scenario, length(sccs)),
                dr_label = fill(key.dr_label, length(sccs)),
                prtp = fill(key.prtp, length(sccs)),
                eta = fill(key.eta, length(sccs)),
                trial = collect(1:length(sccs)),
                scc_2020usd_per_tco2 = sccs,
            ),
            cols = :union,
        )
    end
    return out
end

function summarize_scc(samples::DataFrame)
    summary = combine(
        groupby(samples, [:scenario, :dr_label, :prtp, :eta]),
        :scc_2020usd_per_tco2 => mean => :mean_scc,
        :scc_2020usd_per_tco2 => median => :median_scc,
        :scc_2020usd_per_tco2 => (x -> quantile(x, 0.025)) => :p025_scc,
        :scc_2020usd_per_tco2 => (x -> quantile(x, 0.05)) => :p05_scc,
        :scc_2020usd_per_tco2 => (x -> quantile(x, 0.95)) => :p95_scc,
        :scc_2020usd_per_tco2 => (x -> quantile(x, 0.975)) => :p975_scc,
    )

    baseline_mean = Dict(row.dr_label => row.mean_scc for row in eachrow(summary) if row.scenario == "baseline")
    baseline_median = Dict(row.dr_label => row.median_scc for row in eachrow(summary) if row.scenario == "baseline")
    summary[!, :delta_mean_scc] = [row.mean_scc - baseline_mean[row.dr_label] for row in eachrow(summary)]
    summary[!, :pct_delta_mean_scc] = [100.0 * (row.mean_scc - baseline_mean[row.dr_label]) / baseline_mean[row.dr_label] for row in eachrow(summary)]
    summary[!, :delta_median_scc] = [row.median_scc - baseline_median[row.dr_label] for row in eachrow(summary)]
    return summary
end

function write_density_svg(samples::DataFrame, summary::DataFrame, output_path::String; dr_label = "2.0%")
    data = samples[samples.dr_label .== dr_label, :]
    scenarios = unique(data.scenario)
    width, height = 1020, 610
    left, right, top, bottom = 80, 30, 42, 82
    plot_w = width - left - right
    plot_h = height - top - bottom
    bins = 55
    xmin = quantile(data.scc_2020usd_per_tco2, 0.005)
    xmax = quantile(data.scc_2020usd_per_tco2, 0.995)
    pad = 0.08 * (xmax - xmin)
    xmin -= pad
    xmax += pad
    bin_width = (xmax - xmin) / bins
    colors = Dict(
        "baseline" => "#345995",
        "feedback-residual-medium" => "#03CEA4",
        "feedback-residual-high" => "#FB4D3D",
        "feedback-resfire-half-gross" => "#CA7DF9",
        "feedback-resfire-gross" => "#F5A623",
    )

    counts = Dict{String,Vector{Int}}()
    ymax = 0
    for scenario in scenarios
        values = data[data.scenario .== scenario, :scc_2020usd_per_tco2]
        c = zeros(Int, bins)
        for value in values
            if xmin <= value <= xmax
                idx = clamp(floor(Int, (value - xmin) / bin_width) + 1, 1, bins)
                c[idx] += 1
            end
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
        println(io, """<text x="$left" y="25" font-family="Arial" font-size="18" font-weight="700">Social cost of CO2 with endogenous wildfire-carbon feedbacks</text>""")
        println(io, """<line x1="$left" y1="$(top + plot_h)" x2="$(left + plot_w)" y2="$(top + plot_h)" stroke="#222"/>""")
        println(io, """<line x1="$left" y1="$top" x2="$left" y2="$(top + plot_h)" stroke="#222"/>""")
        println(io, """<text x="$(left + plot_w / 2)" y="$(height - 24)" text-anchor="middle" font-family="Arial" font-size="13">2020 USD per tCO2, $dr_label near-term discount rate</text>""")
        println(io, """<text transform="translate(24,$(top + plot_h / 2)) rotate(-90)" text-anchor="middle" font-family="Arial" font-size="13">Monte Carlo count</text>""")
        for (scenario_index, scenario) in enumerate(scenarios)
            color = get(colors, scenario, "#777")
            offset = (scenario_index - (length(scenarios) + 1) / 2) * (plot_w / bins) * 0.13
            for i in 1:bins
                c = counts[scenario][i]
                x0 = xscale(xmin + (i - 1) * bin_width) + offset
                x1 = xscale(xmin + i * bin_width) + offset
                y0 = yscale(c)
                println(io, """<rect x="$x0" y="$y0" width="$(max(x1-x0,1.0)*0.52)" height="$(top + plot_h - y0)" fill="$color" opacity="0.36"/>""")
            end
        end
        stats = summary[summary.dr_label .== dr_label, :]
        for row in eachrow(stats)
            color = get(colors, row.scenario, "#777")
            x = xscale(row.mean_scc)
            println(io, """<line x1="$x" y1="$top" x2="$x" y2="$(top + plot_h)" stroke="$color" stroke-width="2"/>""")
        end
        legend_y = height - 62
        for (i, scenario) in enumerate(scenarios)
            color = get(colors, scenario, "#777")
            x = left + ((i - 1) % 3) * 300
            y = legend_y + floor(Int, (i - 1) / 3) * 22
            row = only(stats[stats.scenario .== scenario, :])
            println(io, """<rect x="$x" y="$y" width="14" height="14" fill="$color" opacity="0.72"/>""")
            println(io, """<text x="$(x+20)" y="$(y+12)" font-family="Arial" font-size="12">$scenario mean $(round(row.mean_scc, digits=1))</text>""")
        end
        println(io, "</svg>")
    end
end

function run_mcs(;
    n::Int = 10_000,
    output_dir::String = joinpath(@__DIR__, "..", "output", "wildfire_temperature_feedback_mcs_10000"),
    seed::Int = 20260503,
    scenario_filter::Union{Nothing,Vector{String}} = nothing,
)
    mkpath(output_dir)
    baseline_model = build_model("baseline")
    baseline_paths = deterministic_path_frame(deepcopy(baseline_model), "baseline")
    baseline_paths |> save(joinpath(output_dir, "baseline_deterministic_paths.csv"))
    resfire_sensitivity = calibrate_resfire_sensitivity(baseline_paths)

    rng_fair = MersenneTwister(seed + 1)
    rng_rff = MersenneTwister(seed + 2)
    fair_ids = rand(rng_fair, 1:2237, n)
    rff_ids = rand(rng_rff, 1:10_000, n)
    DataFrame(trial = 1:n, fair_parameter_set_id = fair_ids, rffsp_sample_id = rff_ids) |>
        save(joinpath(output_dir, "paired_mcs_ids.csv"))

    all_scenarios = [
        "baseline",
        "feedback-residual-medium",
        "feedback-residual-high",
        "feedback-resfire-half-gross",
        "feedback-resfire-gross",
    ]
    scenarios =
        isnothing(scenario_filter) ? all_scenarios :
        filter(scenario -> scenario in scenario_filter || scenario == "baseline", all_scenarios)
    isempty(scenarios) && error("No scenarios selected.")
    if !isnothing(scenario_filter)
        unknown = setdiff(scenario_filter, all_scenarios)
        isempty(unknown) || error("Unknown scenario(s): $(join(unknown, ", "))")
    end

    all_samples = DataFrame()
    all_draws = DataFrame()
    for (scenario_index, scenario) in enumerate(scenarios)
        println("Running $scenario with n=$n")
        scenario_dir = joinpath(output_dir, scenario)
        mkpath(scenario_dir)
        draws = scenario_draws(scenario, n, seed + 10 + scenario_index, resfire_sensitivity)
        draws |> save(joinpath(scenario_dir, "feedback_parameter_draws.csv"))
        append!(all_draws, draws, cols = :union)

        m = build_model(scenario)
        hook = scenario == "baseline" ? nothing : feedback_mcs_hook(draws)
        results = compute_scc_mcs(
            m;
            n = n,
            output_dir = scenario_dir,
            fair_ids = fair_ids,
            rff_ids = rff_ids,
            post_hook = hook,
            mcs_seed = seed + 1000,
        )
        samples = scc_samples_frame(results, scenario)
        samples |> save(joinpath(scenario_dir, "scc_samples.csv"))
        append!(all_samples, samples, cols = :union)
    end

    all_draws |> save(joinpath(output_dir, "all_feedback_parameter_draws.csv"))
    all_samples |> save(joinpath(output_dir, "all_scc_samples.csv"))
    summary = summarize_scc(all_samples)
    summary |> save(joinpath(output_dir, "scc_summary.csv"))
    write_density_svg(all_samples, summary, joinpath(output_dir, "figure_scc_distribution_2pct.svg"), dr_label = "2.0%")
    println(summary[summary.dr_label .== "2.0%", :])
    return summary
end

if abspath(PROGRAM_FILE) == @__FILE__
    n = length(ARGS) >= 1 ? parse(Int, ARGS[1]) : 10_000
    output_dir = length(ARGS) >= 2 ? ARGS[2] : joinpath(@__DIR__, "..", "output", "wildfire_temperature_feedback_mcs_$(n)")
    seed = length(ARGS) >= 3 ? parse(Int, ARGS[3]) : 20260503
    scenario_filter =
        length(ARGS) >= 4 && lowercase(ARGS[4]) != "all" ?
        String.(split(ARGS[4], ",")) :
        nothing
    run_mcs(n = n, output_dir = output_dir, seed = seed, scenario_filter = scenario_filter)
end
