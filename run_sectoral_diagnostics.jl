#!/usr/bin/env julia

# Sectoral marginal-damage diagnostic for the source-informed wildfire extension.
# This intentionally keeps the run small enough for audit iteration and writes
# transparent unit checks plus simple SVG plots with no extra plotting packages.

using CSVFiles
using DataFrames
using Mimi
using MimiGIVE
using Printf
using Random
using Statistics

import Mimi: SampleStore, add_RV!, add_transform!

include(joinpath(@__DIR__, "WildfireGIVE.jl"))
include(joinpath(@__DIR__, "..", "src", "discount_rates.jl"))

using .WildfireGIVE

const MODEL_YEARS = collect(1750:2300)
const DAMAGE_YEARS = collect(2020:2300)
const USD_2005_TO_2020 = MimiGIVE.pricelevel_2005_to_2020

function deterministic_path_frame(m, scenario_label)
    Mimi.run(m)
    return DataFrame(
        scenario = fill(scenario_label, length(MODEL_YEARS)),
        year = MODEL_YEARS,
        co2_emissions_gtc = m[:co2_cycle, :E_co2],
        co2_ppm = m[:co2_cycle, :co2],
        co2_forcing_wm2 = m[:co2_forcing, :rf_co2],
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

function compute_sectoral_scc_mcs(m; n, output_dir, seed, post_hook = nothing, fair_ids, rff_ids)
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
        save_md = true,
        save_cpc = true,
        compute_sectoral_values = true,
        compute_domestic_values = false,
        CIAM_foresight = :perfect,
        CIAM_GDPcap = true,
        post_mcs_creation_function = post_hook,
        pulse_size = 1e-4,
    )
end

function sectoral_scc_samples_frame(results, scenario_label)
    out = DataFrame()
    for key in keys(results[:scc])
        sccs_2020usd = results[:scc][key].sccs .* USD_2005_TO_2020
        append!(
            out,
            DataFrame(
                scenario = fill(scenario_label, length(sccs_2020usd)),
                sector = fill(String(key.sector), length(sccs_2020usd)),
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

function summarize_sectoral_scc(samples::DataFrame)
    summary = combine(
        groupby(samples, [:scenario, :sector, :dr_label, :prtp, :eta]),
        :scc_2020usd_per_tco2 => mean => :mean_scc,
        :scc_2020usd_per_tco2 => median => :median_scc,
        :scc_2020usd_per_tco2 => (x -> quantile(x, 0.05)) => :p05_scc,
        :scc_2020usd_per_tco2 => (x -> quantile(x, 0.95)) => :p95_scc,
    )

    baseline_mean = Dict(
        (row.sector, row.dr_label) => row.mean_scc
        for row in eachrow(summary)
        if row.scenario == "baseline"
    )
    baseline_median = Dict(
        (row.sector, row.dr_label) => row.median_scc
        for row in eachrow(summary)
        if row.scenario == "baseline"
    )

    summary[!, :delta_mean_scc] = [
        row.mean_scc - baseline_mean[(row.sector, row.dr_label)]
        for row in eachrow(summary)
    ]
    summary[!, :pct_delta_mean_scc] = [
        baseline_mean[(row.sector, row.dr_label)] == 0.0 ? NaN :
        100.0 * (row.mean_scc - baseline_mean[(row.sector, row.dr_label)]) / baseline_mean[(row.sector, row.dr_label)]
        for row in eachrow(summary)
    ]
    summary[!, :delta_median_scc] = [
        row.median_scc - baseline_median[(row.sector, row.dr_label)]
        for row in eachrow(summary)
    ]
    return summary
end

function discount_matrix(results, dr_label::String)
    dr = only([d for d in discount_rates if d.label == dr_label])
    cpc = results[:cpc][(region = :globe, sector = :total)]
    cpc_2020 = cpc[:, 1]
    out = similar(cpc)
    for trial in axes(cpc, 1), (j, year) in enumerate(DAMAGE_YEARS)
        out[trial, j] =
            (cpc_2020[trial] / cpc[trial, j])^dr.eta *
            1.0 / (1.0 + dr.prtp)^(year - 2020)
    end
    return out
end

function marginal_damage_summary(results, scenario_label; dr_label = "2.0%")
    discount = discount_matrix(results, dr_label)
    out = DataFrame()
    for key in keys(results[:mds])
        key.region == :globe || continue
        sector = String(key.sector)
        mds_2020usd = results[:mds][key] .* USD_2005_TO_2020
        discounted = mds_2020usd .* discount
        for (j, year) in enumerate(DAMAGE_YEARS)
            raw_col = view(mds_2020usd, :, j)
            disc_col = view(discounted, :, j)
            push!(
                out,
                (
                    scenario = scenario_label,
                    sector = sector,
                    dr_label = dr_label,
                    year = year,
                    mean_md_2020usd_per_tco2 = mean(raw_col),
                    median_md_2020usd_per_tco2 = median(raw_col),
                    mean_discounted_md_2020usd_per_tco2 = mean(disc_col),
                    median_discounted_md_2020usd_per_tco2 = median(disc_col),
                ),
            )
        end
    end
    return out
end

function marginal_damage_difference(md_summary::DataFrame)
    baseline = md_summary[md_summary.scenario .== "baseline", :]
    wildfire = md_summary[md_summary.scenario .== "wildfire-source-uncertainty", :]
    diff = innerjoin(
        wildfire,
        baseline,
        on = [:sector, :dr_label, :year],
        makeunique = true,
        renamecols = "_wildfire" => "_baseline",
    )
    diff[!, :delta_mean_md_2020usd_per_tco2] =
        diff.mean_md_2020usd_per_tco2_wildfire .- diff.mean_md_2020usd_per_tco2_baseline
    diff[!, :delta_mean_discounted_md_2020usd_per_tco2] =
        diff.mean_discounted_md_2020usd_per_tco2_wildfire .- diff.mean_discounted_md_2020usd_per_tco2_baseline
    return diff
end

function mean_wildfire_path(emissions_draws::DataFrame)
    out = combine(
        groupby(emissions_draws, :year),
        :wildfire_gtco2 => mean => :wildfire_gtco2,
        :wildfire_gtc => mean => :wildfire_gtc,
    )
    sort!(out, :year)
    return out
end

function unit_check_frame(baseline_paths, wildfire_paths, mean_path)
    years = [2020, 2030, 2050, 2100, 2200, 2300]
    rows = DataFrame()
    for year in years
        b = only(baseline_paths[baseline_paths.year .== year, :])
        w = only(wildfire_paths[wildfire_paths.year .== year, :])
        p = only(mean_path[mean_path.year .== year, :])
        push!(
            rows,
            (
                year = year,
                added_wildfire_gtco2_per_year = p.wildfire_gtco2,
                added_wildfire_gtc_per_year = p.wildfire_gtc,
                model_e_co2_delta_gtc_per_year = w.co2_emissions_gtc - b.co2_emissions_gtc,
                baseline_e_co2_gtc_per_year = b.co2_emissions_gtc,
                wildfire_e_co2_gtc_per_year = w.co2_emissions_gtc,
                co2_ppm_delta = w.co2_ppm - b.co2_ppm,
                co2_forcing_delta_wm2 = w.co2_forcing_wm2 - b.co2_forcing_wm2,
                temperature_delta_c = w.temperature_c - b.temperature_c,
                total_damage_delta_2020usd_per_year = (w.total_damage_2005usd_per_year - b.total_damage_2005usd_per_year) * USD_2005_TO_2020,
            ),
        )
    end
    return rows
end

function line_points(xs, ys, xscale, yscale)
    return join([@sprintf("%.2f,%.2f", xscale(x), yscale(y)) for (x, y) in zip(xs, ys)], " ")
end

function write_temperature_svg(paths::DataFrame, output_path::String)
    mkpath(dirname(output_path))
    years = paths.year
    y_abs_min = minimum(paths.temperature_c[paths.year .>= 2020]) - 0.1
    y_abs_max = maximum(paths.temperature_c[paths.year .>= 2020]) + 0.1

    baseline = paths[(paths.scenario .== "baseline") .& (paths.year .>= 2020), :]
    wildfire = paths[(paths.scenario .== "wildfire-source-uncertainty-mean") .& (paths.year .>= 2020), :]
    delta = innerjoin(
        wildfire[:, [:year, :temperature_c]],
        baseline[:, [:year, :temperature_c]],
        on = :year,
        makeunique = true,
        renamecols = "_wildfire" => "_baseline",
    )
    delta[!, :temperature_delta_c] = delta.temperature_c_wildfire .- delta.temperature_c_baseline

    width = 960
    height = 650
    left = 76
    right = 32
    top1 = 40
    panel_h = 238
    gap = 78
    top2 = top1 + panel_h + gap
    bottom = 58
    plot_w = width - left - right
    y_delta_min = min(0.0, minimum(delta.temperature_delta_c)) - 0.002
    y_delta_max = maximum(delta.temperature_delta_c) + 0.002
    xscale(x) = left + (x - 2020) / (2300 - 2020) * plot_w
    yabs(y) = top1 + panel_h - (y - y_abs_min) / (y_abs_max - y_abs_min) * panel_h
    ydel(y) = top2 + panel_h - (y - y_delta_min) / (y_delta_max - y_delta_min) * panel_h

    open(output_path, "w") do io
        println(io, """<svg xmlns="http://www.w3.org/2000/svg" width="$width" height="$height" viewBox="0 0 $width $height">""")
        println(io, """<rect width="100%" height="100%" fill="white"/>""")
        println(io, """<text x="$left" y="24" font-size="18" font-family="Arial" font-weight="700">Global mean temperature: baseline vs mean wildfire CO2 addition</text>""")

        for (top, ytitle) in [(top1, "Temperature anomaly (C)"), (top2, "Wildfire minus baseline (C)")]
            println(io, """<line x1="$left" y1="$(top + panel_h)" x2="$(left + plot_w)" y2="$(top + panel_h)" stroke="#333"/>""")
            println(io, """<line x1="$left" y1="$top" x2="$left" y2="$(top + panel_h)" stroke="#333"/>""")
            println(io, """<text transform="translate(22,$(top + panel_h / 2)) rotate(-90)" text-anchor="middle" font-size="13" font-family="Arial">$ytitle</text>""")
        end

        for year in [2020, 2050, 2100, 2200, 2300]
            x = xscale(year)
            println(io, """<line x1="$x" y1="$(top1 + panel_h)" x2="$x" y2="$(top2 + panel_h)" stroke="#e5e5e5"/>""")
            println(io, """<text x="$x" y="$(height - 26)" text-anchor="middle" font-size="12" font-family="Arial">$year</text>""")
        end

        println(io, """<polyline points="$(line_points(baseline.year, baseline.temperature_c, xscale, yabs))" fill="none" stroke="#3764ad" stroke-width="2.4"/>""")
        println(io, """<polyline points="$(line_points(wildfire.year, wildfire.temperature_c, xscale, yabs))" fill="none" stroke="#c45135" stroke-width="2.4"/>""")
        println(io, """<polyline points="$(line_points(delta.year, delta.temperature_delta_c, xscale, ydel))" fill="none" stroke="#604b9b" stroke-width="2.4"/>""")
        println(io, """<text x="$(left + 10)" y="$(top1 + 22)" font-size="12" font-family="Arial" fill="#3764ad">baseline</text>""")
        println(io, """<text x="$(left + 10)" y="$(top1 + 40)" font-size="12" font-family="Arial" fill="#c45135">mean wildfire addition</text>""")
        println(io, """<text x="$(left + 10)" y="$(top2 + 22)" font-size="12" font-family="Arial" fill="#604b9b">temperature delta</text>""")
        println(io, """<text x="$(left + plot_w / 2)" y="$(height - 4)" text-anchor="middle" font-size="13" font-family="Arial">Year</text>""")
        println(io, "</svg>")
    end
end

function write_sector_delta_svg(diff::DataFrame, output_path::String)
    mkpath(dirname(output_path))
    plot_data = diff[(diff.year .>= 2020) .& (diff.sector .!= "total"), :]
    sectors = ["cromar_mortality", "agriculture", "energy", "slr"]
    colors = Dict(
        "cromar_mortality" => "#8c3d78",
        "agriculture" => "#4f7f39",
        "energy" => "#c9862b",
        "slr" => "#3764ad",
    )

    width = 960
    height = 520
    left = 84
    right = 30
    top = 42
    bottom = 70
    plot_w = width - left - right
    plot_h = height - top - bottom
    yvals = plot_data.delta_mean_discounted_md_2020usd_per_tco2
    y_min = min(0.0, minimum(yvals))
    y_max = max(0.0, maximum(yvals))
    pad = 0.08 * max(y_max - y_min, 1e-9)
    y_min -= pad
    y_max += pad
    xscale(x) = left + (x - 2020) / (2300 - 2020) * plot_w
    yscale(y) = top + plot_h - (y - y_min) / (y_max - y_min) * plot_h

    open(output_path, "w") do io
        println(io, """<svg xmlns="http://www.w3.org/2000/svg" width="$width" height="$height" viewBox="0 0 $width $height">""")
        println(io, """<rect width="100%" height="100%" fill="white"/>""")
        println(io, """<text x="$left" y="25" font-size="18" font-family="Arial" font-weight="700">Change in discounted marginal damages by sector, 2.0% case</text>""")
        println(io, """<line x1="$left" y1="$(top + plot_h)" x2="$(left + plot_w)" y2="$(top + plot_h)" stroke="#333"/>""")
        println(io, """<line x1="$left" y1="$top" x2="$left" y2="$(top + plot_h)" stroke="#333"/>""")
        zero_y = yscale(0.0)
        println(io, """<line x1="$left" y1="$zero_y" x2="$(left + plot_w)" y2="$zero_y" stroke="#aaa" stroke-dasharray="5,5"/>""")
        for year in [2020, 2050, 2100, 2200, 2300]
            x = xscale(year)
            println(io, """<line x1="$x" y1="$top" x2="$x" y2="$(top + plot_h)" stroke="#ececec"/>""")
            println(io, """<text x="$x" y="$(height - 32)" text-anchor="middle" font-size="12" font-family="Arial">$year</text>""")
        end
        for sector in sectors
            rows = plot_data[plot_data.sector .== sector, :]
            sort!(rows, :year)
            println(io, """<polyline points="$(line_points(rows.year, rows.delta_mean_discounted_md_2020usd_per_tco2, xscale, yscale))" fill="none" stroke="$(colors[sector])" stroke-width="2.2"/>""")
        end
        for (i, sector) in enumerate(sectors)
            x = left + (i - 1) * 205
            y = height - 52
            println(io, """<rect x="$x" y="$y" width="14" height="14" fill="$(colors[sector])"/>""")
            println(io, """<text x="$(x + 20)" y="$(y + 12)" font-size="12" font-family="Arial">$sector</text>""")
        end
        println(io, """<text transform="translate(24,$(top + plot_h / 2)) rotate(-90)" text-anchor="middle" font-size="13" font-family="Arial">Delta discounted MD (2020 USD per tCO2 per year)</text>""")
        println(io, """<text x="$(left + plot_w / 2)" y="$(height - 6)" text-anchor="middle" font-size="13" font-family="Arial">Year</text>""")
        println(io, "</svg>")
    end
end

function run_diagnostics(; n = 100, output_dir = joinpath(@__DIR__, "..", "output", "wildfire_sectoral_diagnostics_100"), seed = 20260502)
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

    mean_path = mean_wildfire_path(emissions_draws)
    mean_path |> save(joinpath(output_dir, "mean_wildfire_emissions_path.csv"))

    wildfire_mean_model, _ = WildfireGIVE.get_model(
        include_wildfire_co2 = true,
        wildfire_scenario = :custom,
        custom_gtco2 = mean_path.wildfire_gtco2,
        socioeconomics_source = :RFF,
    )
    wildfire_mean_paths = deterministic_path_frame(wildfire_mean_model, "wildfire-source-uncertainty-mean")
    all_paths = vcat(baseline_paths, wildfire_mean_paths, cols = :union)
    all_paths |> save(joinpath(output_dir, "deterministic_temperature_damage_paths.csv"))

    unit_check = unit_check_frame(baseline_paths, wildfire_mean_paths, mean_path)
    unit_check |> save(joinpath(output_dir, "unit_check_mean_wildfire_path.csv"))
    write_temperature_svg(all_paths, joinpath(output_dir, "global_temperature_paths_and_delta.svg"))

    wildfire_years, wildfire_matrix = wildfire_path_matrix(emissions_draws, n)
    hook = wildfire_mcs_hook(wildfire_years, wildfire_matrix)

    fair_rng = MersenneTwister(seed + 1)
    rff_rng = MersenneTwister(seed + 2)
    fair_ids = rand(fair_rng, 1:2237, n)
    rff_ids = rand(rff_rng, 1:10_000, n)
    DataFrame(trial = 1:n, fair_parameter_set_id = fair_ids, rffsp_sample_id = rff_ids) |>
        save(joinpath(output_dir, "paired_mcs_ids.csv"))

    baseline_results = compute_sectoral_scc_mcs(
        baseline_model;
        n = n,
        output_dir = joinpath(output_dir, "baseline-sectoral"),
        seed = seed + 3,
        fair_ids = fair_ids,
        rff_ids = rff_ids,
    )

    wildfire_model, _ = WildfireGIVE.get_model(
        include_wildfire_co2 = true,
        wildfire_scenario = :baseline,
        socioeconomics_source = :RFF,
    )
    wildfire_results = compute_sectoral_scc_mcs(
        wildfire_model;
        n = n,
        output_dir = joinpath(output_dir, "wildfire-sectoral"),
        seed = seed + 3,
        post_hook = hook,
        fair_ids = fair_ids,
        rff_ids = rff_ids,
    )

    sectoral_samples = vcat(
        sectoral_scc_samples_frame(baseline_results, "baseline"),
        sectoral_scc_samples_frame(wildfire_results, "wildfire-source-uncertainty"),
        cols = :union,
    )
    sectoral_summary = summarize_sectoral_scc(sectoral_samples)
    sectoral_samples |> save(joinpath(output_dir, "sectoral_scc_samples.csv"))
    sectoral_summary |> save(joinpath(output_dir, "sectoral_scc_summary.csv"))

    md_summary = vcat(
        marginal_damage_summary(baseline_results, "baseline", dr_label = "2.0%"),
        marginal_damage_summary(wildfire_results, "wildfire-source-uncertainty", dr_label = "2.0%"),
        cols = :union,
    )
    md_summary |> save(joinpath(output_dir, "sectoral_marginal_damage_summary_2pct.csv"))
    md_diff = marginal_damage_difference(md_summary)
    md_diff |> save(joinpath(output_dir, "sectoral_marginal_damage_difference_2pct.csv"))
    write_sector_delta_svg(md_diff, joinpath(output_dir, "discounted_marginal_damage_delta_by_sector_2pct.svg"))

    println("Unit check:")
    println(unit_check)
    println("Sectoral SCC summary, 2.0%:")
    println(sectoral_summary[sectoral_summary.dr_label .== "2.0%", :])
    return sectoral_summary
end

function main()
    n = length(ARGS) >= 1 ? parse(Int, ARGS[1]) : 100
    output_dir = length(ARGS) >= 2 ? ARGS[2] : joinpath(@__DIR__, "..", "output", "wildfire_sectoral_diagnostics_100")
    seed = length(ARGS) >= 3 ? parse(Int, ARGS[3]) : 20260502
    println("Running wildfire sectoral diagnostics with n=$n. Output: $output_dir")
    run_diagnostics(n = n, output_dir = output_dir, seed = seed)
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
