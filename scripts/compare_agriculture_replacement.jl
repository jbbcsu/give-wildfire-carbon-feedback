using DataFrames
using Dates
using Mimi
using MimiGIVE
using Random
using Statistics

const ROOT = normpath(joinpath(@__DIR__, ".."))
const SOURCE = joinpath(
    ROOT,
    "vendor",
    "moore_2026",
    "lrennels-paper-2026-give-labor-ag-5d034e7",
)
include(joinpath(SOURCE, "src", "main.jl"))

const PRICELEVEL_2005_TO_2020 = 113.648 / 87.504
const SEED = 24523438
const N = parse(Int, get(ENV, "N_TRIALS", "100"))
const PULSE_YEAR = 2025
const PULSE_SIZE = 1e-4
const DISCOUNT_RATES = [
    (label = "2.0%", prtp = exp(0.001972641) - 1, eta = 1.244458999),
]

N >= 2 || error("N_TRIALS must be at least 2")

const OUTPUT_DIR = joinpath(
    ROOT,
    "output",
    "agriculture_replacement",
    "pulse$(PULSE_YEAR)_n$(N)_seed$(SEED)",
)
ispath(OUTPUT_DIR) && error("fresh output directory required: $OUTPUT_DIR")
mkpath(OUTPUT_DIR)

function isolate_original_agriculture!(model)
    update_param!(model, :DamageAggregator, :include_slr, false)
    update_param!(model, :DamageAggregator, :include_cromar_mortality, false)
    update_param!(model, :DamageAggregator, :include_energy, false)
    return model
end

function isolate_updated_agriculture!(model)
    update_param!(model, :DamageAggregator, :include_slr, false)
    update_param!(model, :DamageAggregator, :include_cromar_mortality, false)
    update_param!(model, :DamageAggregator, :include_energy, false)
    update_param!(model, :DamageAggregator, :include_labor, false)
    return model
end

function run_version(version::String)
    model = if version == "legacy"
        isolate_original_agriculture!(MimiGIVE.get_model(socioeconomics_source = :RFF))
    elseif version == "updated"
        isolate_updated_agriculture!(get_model(socioeconomics_source = :RFF))
    else
        error("unsupported version: $version")
    end
    Random.seed!(SEED)
    version_dir = joinpath(OUTPUT_DIR, version)
    results = if version == "legacy"
        MimiGIVE.compute_scc(
            model;
            year = PULSE_YEAR,
            last_year = 2300,
            discount_rates = DISCOUNT_RATES,
            fair_parameter_set = :random,
            rffsp_sampling = :random,
            n = N,
            gas = :CO2,
            output_dir = version_dir,
            save_md = false,
            save_cpc = false,
            compute_sectoral_values = true,
            CIAM_foresight = :perfect,
            CIAM_GDPcap = true,
            pulse_size = PULSE_SIZE,
        )
    else
        compute_scc(
            model;
            year = PULSE_YEAR,
            last_year = 2300,
            discount_rates = DISCOUNT_RATES,
            fair_parameter_set = :random,
            rffsp_sampling = :random,
            n = N,
            gas = :CO2,
            output_dir = version_dir,
            save_md = false,
            save_cpc = false,
            compute_sectoral_values = true,
            CIAM_foresight = :perfect,
            CIAM_GDPcap = true,
            pulse_size = PULSE_SIZE,
            compute_labor_country_sccs = false,
        )
    end
    matches = [(key, value) for (key, value) in results[:scc] if key.sector == :agriculture]
    length(matches) == 1 || error("expected one agriculture/discount-rate result for $version")
    key, value = only(matches)
    String(key.dr_label) == "2.0%" || error("unexpected discount rate")
    draws = collect(skipmissing(value.sccs)) .* PRICELEVEL_2005_TO_2020
    length(draws) == N || error("missing $version draws")
    all(isfinite, draws) || error("non-finite $version draws")
    open(joinpath(OUTPUT_DIR, "$(version)_agriculture_draws_2020usd_per_tco2.csv"), "w") do io
        println(io, "trial,scc_2020usd_per_tco2")
        for (trial, scc) in enumerate(draws)
            println(io, "$trial,$scc")
        end
    end
    return (
        version = version,
        expected_scc_2020usd_per_tco2 = mean(draws),
        se_expected_scc = std(draws) / sqrt(length(draws)),
        q05 = quantile(draws, 0.05),
        median = quantile(draws, 0.50),
        q95 = quantile(draws, 0.95),
        draws = length(draws),
    )
end

started = now()
legacy = run_version("legacy")
GC.gc()
updated = run_version("updated")

summary_path = joinpath(OUTPUT_DIR, "agriculture_replacement_summary.csv")
open(summary_path, "w") do io
    println(io, "version,expected_scc_2020usd_per_tco2,se_expected_scc,q05,median,q95,draws")
    for row in (legacy, updated)
        println(io, join(Tuple(row), ","))
    end
end

println("started=$started")
println("completed=$(now())")
println("wrote=$summary_path")
println(legacy)
println(updated)
println("mean_replacement_delta_2020usd_per_tco2=$(updated.expected_scc_2020usd_per_tco2 - legacy.expected_scc_2020usd_per_tco2)")
println("warning=draw-level deltas are prohibited because the two model versions have different agriculture uncertainty parameterizations")
