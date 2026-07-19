#!/usr/bin/env julia

# Gross-fire share diagnostic. This deliberately ignores double counting and
# short-run biogenic regrowth so we can size fire carbon against GIVE/RFF-SP.

using CSVFiles
using DataFrames
using Mimi
using MimiGIVE

include(joinpath(@__DIR__, "WildfireGIVE.jl"))
using .WildfireGIVE

const MODEL_YEARS = collect(1750:2300)
const BENCHMARK_YEARS = [2023, 2030, 2050, 2100, 2200, 2300]
const PREINDUSTRIAL_CO2_PPM = 278.052989189439
const GROSS_REFERENCE_FIRE_GTC = 2.2

function run_path(m)
    Mimi.run(m)
    return DataFrame(
        year = MODEL_YEARS,
        e_co2_gtc = m[:co2_cycle, :E_co2],
        co2_ppm = m[:co2_cycle, :co2],
        temperature_c = m[:temperature, :T],
    )
end

function ratio_path(years; mid_ratio, late_ratio)
    out = zeros(Float64, length(years))
    for (i, year) in enumerate(years)
        out[i] =
            if year < 2020
                0.0
            elseif year <= 2050
                1.0 + (mid_ratio - 1.0) * (year - 2020) / (2050 - 2020)
            elseif year <= 2100
                mid_ratio + (late_ratio - mid_ratio) * (year - 2050) / (2100 - 2050)
            else
                late_ratio
            end
    end
    return out
end

function scenario_paths()
    rcp45_ratio = ratio_path(MODEL_YEARS, mid_ratio = 1.190336455, late_ratio = 1.33134478)
    rcp85_ratio = ratio_path(MODEL_YEARS, mid_ratio = 1.547338981, late_ratio = 2.011448836)
    return Dict(
        "gross_fire_constant_2p2GtC" => [year >= 2020 ? GROSS_REFERENCE_FIRE_GTC : 0.0 for year in MODEL_YEARS],
        "gross_fire_usda_valmartin_pierce_rcp45" => GROSS_REFERENCE_FIRE_GTC .* rcp45_ratio,
        "gross_fire_usda_valmartin_pierce_rcp85" => GROSS_REFERENCE_FIRE_GTC .* rcp85_ratio,
    )
end

function run_diagnostics(output_dir = joinpath(@__DIR__, "..", "output", "gross_fire_share_diagnostics"))
    mkpath(output_dir)

    baseline_model = MimiGIVE.get_model(socioeconomics_source = :RFF)
    baseline = run_path(baseline_model)
    baseline |> save(joinpath(output_dir, "baseline_path.csv"))

    rows = DataFrame()
    for (scenario, fire_gtc) in scenario_paths()
        fire_gtco2 = fire_gtc .* WildfireGIVE.GTC_TO_GTCO2
        m, _ = WildfireGIVE.get_model(
            include_wildfire_co2 = true,
            wildfire_scenario = :custom,
            custom_gtco2 = fire_gtco2,
            socioeconomics_source = :RFF,
        )
        path = run_path(m)
        path[!, :scenario] = fill(scenario, nrow(path))
        path |> save(joinpath(output_dir, "$(scenario)_path.csv"))

        for year in BENCHMARK_YEARS
            idx = findfirst(isequal(year), MODEL_YEARS)
            b = baseline[idx, :]
            p = path[idx, :]
            push!(
                rows,
                (
                    scenario = scenario,
                    year = year,
                    fire_gtc_per_year = fire_gtc[idx],
                    fire_gtco2_per_year = fire_gtco2[idx],
                    baseline_e_co2_gtc_per_year = b.e_co2_gtc,
                    fire_pct_of_baseline_annual_co2_emissions = 100.0 * fire_gtc[idx] / b.e_co2_gtc,
                    baseline_co2_ppm = b.co2_ppm,
                    added_co2_ppm = p.co2_ppm - b.co2_ppm,
                    added_pct_of_full_baseline_atmospheric_co2 = 100.0 * (p.co2_ppm - b.co2_ppm) / b.co2_ppm,
                    added_pct_of_baseline_co2_above_preindustrial = 100.0 * (p.co2_ppm - b.co2_ppm) / (b.co2_ppm - PREINDUSTRIAL_CO2_PPM),
                    temperature_delta_c = p.temperature_c - b.temperature_c,
                ),
            )
        end
    end

    # 2023 Canada/global sizing from Byrne et al. numbers supplied in the thread:
    # Canada 2023 fire carbon = 647 TgC and equals 26.7% of global wildfire carbon.
    canada_2023_gtc = 647.0 / 1000.0
    canada_excess_gtc = (647.0 - 121.0) / 1000.0
    global_2023_gtc = canada_2023_gtc / 0.267
    b2023 = baseline[findfirst(isequal(2023), MODEL_YEARS), :]
    canada_rows = DataFrame(
        scenario = ["canada_2023_fire_gross", "canada_2023_excess", "global_2023_fire_implied_by_canada_share"],
        year = fill(2023, 3),
        fire_gtc_per_year = [canada_2023_gtc, canada_excess_gtc, global_2023_gtc],
        fire_gtco2_per_year = [canada_2023_gtc, canada_excess_gtc, global_2023_gtc] .* WildfireGIVE.GTC_TO_GTCO2,
        baseline_e_co2_gtc_per_year = fill(b2023.e_co2_gtc, 3),
        fire_pct_of_baseline_annual_co2_emissions = 100.0 .* [canada_2023_gtc, canada_excess_gtc, global_2023_gtc] ./ b2023.e_co2_gtc,
    )
    canada_rows |> save(joinpath(output_dir, "canada_2023_fire_fraction_of_baseline_emissions.csv"))

    rows |> save(joinpath(output_dir, "gross_fire_share_diagnostics.csv"))
    println(rows)
    println(canada_rows)
    return rows
end

if abspath(PROGRAM_FILE) == @__FILE__
    output_dir = length(ARGS) >= 1 ? ARGS[1] : joinpath(@__DIR__, "..", "output", "gross_fire_share_diagnostics")
    run_diagnostics(output_dir)
end
