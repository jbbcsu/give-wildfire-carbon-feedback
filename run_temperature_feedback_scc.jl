#!/usr/bin/env julia

# Deterministic SCC experiment for a temperature-dependent wildfire CO2 feedback.
#
# This differs from the earlier exogenous wildfire-path tests. Here, added fire
# CO2 in year t depends on lagged global mean temperature in year t-1, so the
# SCC marginal pulse can induce additional fire CO2 and therefore tests a true
# feedback channel.

using CSVFiles
using DataFrames
using Mimi
using MimiGIVE
using Statistics

include(joinpath(@__DIR__, "WildfireGIVE.jl"))
include(joinpath(@__DIR__, "..", "src", "discount_rates.jl"))

using .WildfireGIVE

const MODEL_YEARS = collect(1750:2300)
const SCC_YEAR = 2020
const PULSE_SIZE_GTC = 1.0

function component_vector_or_zeros(m, component::Symbol, variable::Symbol)
    try
        return m[component, variable]
    catch
        return zeros(length(MODEL_YEARS))
    end
end

function deterministic_path_frame(m, scenario_label)
    Mimi.run(m)

    feedback_gtc = component_vector_or_zeros(m, :wildfire_temperature_feedback_co2, :feedback_gtc)
    warming_lagged_c = component_vector_or_zeros(m, :wildfire_temperature_feedback_co2, :warming_lagged_c)

    return DataFrame(
        scenario = fill(scenario_label, length(MODEL_YEARS)),
        year = MODEL_YEARS,
        co2_emissions_gtc = m[:co2_cycle, :E_co2],
        feedback_fire_gtc = feedback_gtc,
        feedback_fire_gtco2 = feedback_gtc .* WildfireGIVE.GTC_TO_GTCO2,
        feedback_warming_lagged_c = warming_lagged_c,
        co2_ppm = m[:co2_cycle, :co2],
        total_forcing_wm2 = m[:total_forcing, :total_forcing],
        temperature_c = m[:temperature, :T],
        total_damage_2005usd_per_year = m[:DamageAggregator, :total_damage],
    )
end

function deterministic_scc_frame(m, scenario_label)
    results = MimiGIVE.compute_scc(
        m;
        year = SCC_YEAR,
        last_year = 2300,
        discount_rates = discount_rates,
        n = 0,
        gas = :CO2,
        compute_domestic_values = false,
        CIAM_foresight = :perfect,
        CIAM_GDPcap = true,
        pulse_size = PULSE_SIZE_GTC,
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

function calibrate_sensitivity_for_cumulative_gtco2(
    baseline_paths::DataFrame;
    target_cumulative_gtco2::Real,
    start_year::Int = 2021,
    end_year::Int = 2050,
    gross_reference_fire_carbon_pgc::Real = 2.2,
    reference_year::Int = 2020,
)
    ref_temp = only(baseline_paths[baseline_paths.year .== reference_year, :]).temperature_c
    gross_reference_fire_gtco2 = Float64(gross_reference_fire_carbon_pgc) * WildfireGIVE.GTC_TO_GTCO2
    denominator = 0.0

    for row in eachrow(baseline_paths)
        if start_year <= row.year <= end_year
            lag_year = row.year - 1
            lag_temp = only(baseline_paths[baseline_paths.year .== lag_year, :]).temperature_c
            denominator += gross_reference_fire_gtco2 * max(lag_temp - ref_temp, 0.0)
        end
    end

    denominator > 0.0 || error("Cannot calibrate sensitivity: no positive baseline warming.")
    return Float64(target_cumulative_gtco2) / denominator
end

function scenario_specs(baseline_paths::DataFrame)
    # RESFire-style projections motivate a deliberately high gross-fire stress
    # calibration. This is not a net, not-already-in-RFF residual estimate.
    resfire_sensitivity = calibrate_sensitivity_for_cumulative_gtco2(
        baseline_paths;
        target_cumulative_gtco2 = 111.889,
    )

    return [
        (
            label = "baseline",
            feedback = false,
            sensitivity_per_c = 0.0,
            net_persistence_fraction = 0.0,
            not_embedded_fraction = 0.0,
            source_note = "No wildfire feedback.",
        ),
        (
            label = "feedback-residual-medium",
            feedback = true,
            sensitivity_per_c = 0.10,
            net_persistence_fraction = 0.10,
            not_embedded_fraction = 0.50,
            source_note = "Conservative residual: 10% gross fire response per C, 10% persistent, 50% not already embedded.",
        ),
        (
            label = "feedback-residual-high",
            feedback = true,
            sensitivity_per_c = 0.50,
            net_persistence_fraction = 0.30,
            not_embedded_fraction = 0.75,
            source_note = "High residual: larger response and persistence but still partial double-counting protection.",
        ),
        (
            label = "feedback-resfire-half-gross",
            feedback = true,
            sensitivity_per_c = 0.50 * resfire_sensitivity,
            net_persistence_fraction = 1.00,
            not_embedded_fraction = 1.00,
            source_note = "Half of RESFire-style gross fire CO2 stress calibration; intentionally not netted.",
        ),
        (
            label = "feedback-resfire-gross",
            feedback = true,
            sensitivity_per_c = resfire_sensitivity,
            net_persistence_fraction = 1.00,
            not_embedded_fraction = 1.00,
            source_note = "RESFire-style gross fire CO2 stress calibration; intentionally not netted.",
        ),
    ]
end

function build_feedback_model(spec)
    m, _ = WildfireGIVE.get_model(
        include_wildfire_co2 = false,
        socioeconomics_source = :RFF,
    )

    if spec.feedback
        WildfireGIVE.apply_wildfire_temperature_feedback_co2!(
            m;
            start_year = SCC_YEAR,
            reference_temperature_year = SCC_YEAR,
            gross_reference_fire_carbon_pgc = 2.2,
            sensitivity_per_c = spec.sensitivity_per_c,
            net_persistence_fraction = spec.net_persistence_fraction,
            not_embedded_fraction = spec.not_embedded_fraction,
            max_feedback_gtco2 = 100.0,
            ar6_scenario = "ssp245",
        )
    end

    return m
end

function marginal_feedback_diagnostics(m, scenario_label)
    out = DataFrame(
        scenario = String[],
        year = Int[],
        base_feedback_gtco2 = Float64[],
        modified_feedback_gtco2 = Float64[],
        pulse_induced_feedback_gtco2 = Float64[],
        base_temperature_c = Float64[],
        modified_temperature_c = Float64[],
        pulse_induced_temperature_c = Float64[],
    )

    mm = MimiGIVE.get_marginal_model(
        deepcopy(m);
        year = SCC_YEAR,
        gas = :CO2,
        pulse_size = PULSE_SIZE_GTC,
    )
    Mimi.run(mm)

    base_feedback = component_vector_or_zeros(mm.base, :wildfire_temperature_feedback_co2, :feedback_gtc) .* WildfireGIVE.GTC_TO_GTCO2
    modified_feedback = component_vector_or_zeros(mm.modified, :wildfire_temperature_feedback_co2, :feedback_gtc) .* WildfireGIVE.GTC_TO_GTCO2

    for year in [2020, 2021, 2030, 2050, 2100, 2200, 2300]
        idx = findfirst(isequal(year), MODEL_YEARS)
        push!(
            out,
            (
                scenario_label,
                year,
                base_feedback[idx],
                modified_feedback[idx],
                modified_feedback[idx] - base_feedback[idx],
                mm.base[:temperature, :T][idx],
                mm.modified[:temperature, :T][idx],
                mm.modified[:temperature, :T][idx] - mm.base[:temperature, :T][idx],
            ),
        )
    end

    cumulative_induced_gtco2 = sum(modified_feedback .- base_feedback)
    max_induced_gtco2 = maximum(modified_feedback .- base_feedback)
    push!(
        out,
        (
            scenario_label,
            9999,
            sum(base_feedback),
            sum(modified_feedback),
            cumulative_induced_gtco2,
            NaN,
            NaN,
            max_induced_gtco2,
        ),
    )

    return out
end

function summarize_benchmark_paths(paths::DataFrame, baseline_paths::DataFrame)
    out = DataFrame()
    for scenario in unique(paths.scenario), year in [2020, 2030, 2050, 2100, 2200, 2300]
        row = only(paths[(paths.scenario .== scenario) .& (paths.year .== year), :])
        base = only(baseline_paths[baseline_paths.year .== year, :])
        push!(
            out,
            (
                scenario = scenario,
                year = year,
                feedback_fire_gtco2 = row.feedback_fire_gtco2,
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

function write_scenario_metadata(specs, output_dir)
    rows = DataFrame(
        scenario = String[],
        feedback = Bool[],
        sensitivity_per_c = Float64[],
        net_persistence_fraction = Float64[],
        not_embedded_fraction = Float64[],
        source_note = String[],
    )
    for spec in specs
        push!(
            rows,
            (
                spec.label,
                spec.feedback,
                spec.sensitivity_per_c,
                spec.net_persistence_fraction,
                spec.not_embedded_fraction,
                spec.source_note,
            ),
        )
    end
    rows |> save(joinpath(output_dir, "scenario_assumptions.csv"))
    return rows
end

function run_temperature_feedback(output_dir = joinpath(@__DIR__, "..", "output", "wildfire_temperature_feedback"))
    mkpath(output_dir)

    baseline_model, _ = WildfireGIVE.get_model(
        include_wildfire_co2 = false,
        socioeconomics_source = :RFF,
    )
    baseline_paths = deterministic_path_frame(deepcopy(baseline_model), "baseline")

    specs = scenario_specs(baseline_paths)
    assumptions = write_scenario_metadata(specs, output_dir)

    all_paths = DataFrame()
    all_scc = DataFrame()
    all_marginal_feedback = DataFrame()

    for spec in specs
        println("Running $(spec.label)")
        m = spec.label == "baseline" ? baseline_model : build_feedback_model(spec)

        paths = spec.label == "baseline" ? baseline_paths : deterministic_path_frame(deepcopy(m), spec.label)
        append!(all_paths, paths, cols = :union)
        append!(all_scc, deterministic_scc_frame(m, spec.label), cols = :union)
        append!(all_marginal_feedback, marginal_feedback_diagnostics(m, spec.label), cols = :union)
    end

    add_baseline_differences!(all_scc)
    benchmark_paths = summarize_benchmark_paths(all_paths, baseline_paths)

    all_scc |> save(joinpath(output_dir, "deterministic_scc_summary.csv"))
    all_paths |> save(joinpath(output_dir, "deterministic_climate_damage_paths.csv"))
    all_marginal_feedback |> save(joinpath(output_dir, "marginal_temperature_feedback_diagnostics.csv"))
    benchmark_paths |> save(joinpath(output_dir, "benchmark_path_summary.csv"))

    println("2.0% SCC:")
    println(all_scc[all_scc.dr_label .== "2.0%", :])
    println("Benchmark paths:")
    println(benchmark_paths)
    println("Assumptions:")
    println(assumptions)

    return all_scc
end

if abspath(PROGRAM_FILE) == @__FILE__
    output_dir = length(ARGS) >= 1 ? ARGS[1] : joinpath(@__DIR__, "..", "output", "wildfire_temperature_feedback")
    run_temperature_feedback(output_dir)
end
