using Dates
using Mimi
using MimiGIVE
using Random
using Statistics

const ROOT = normpath(joinpath(@__DIR__, ".."))
const SOURCE = joinpath(ROOT, "vendor", "moore_2026", "lrennels-paper-2026-give-labor-ag-5d034e7")
include(joinpath(SOURCE, "src", "main.jl"))

const PRICELEVEL_2005_TO_2020 = 113.648 / 87.504
const SEED = 24523438
const N = parse(Int, get(ENV, "N_TRIALS", "2"))
const VERSION_NAME = get(ENV, "AG_VERSION", "")
const PULSE_YEAR = 2025
const PULSE_SIZE = 1e-4
const MAX_RSS_BYTES = 512 * 1024^2
const DISCOUNT_RATES = [(label = "2.0%", prtp = exp(0.001972641) - 1, eta = 1.244458999)]

VERSION_NAME in ("legacy", "updated") || error("AG_VERSION must be legacy or updated")
N >= 2 || error("N_TRIALS must be at least 2")
const OUTPUT_DIR = joinpath(ROOT, "output", "agriculture_replacement_split", "pulse$(PULSE_YEAR)_n$(N)_seed$(SEED)", VERSION_NAME)
ispath(OUTPUT_DIR) && error("fresh output directory required: $OUTPUT_DIR")
mkpath(OUTPUT_DIR)

model = if VERSION_NAME == "legacy"
    value = MimiGIVE.get_model(socioeconomics_source = :RFF)
    update_param!(value, :DamageAggregator, :include_slr, false)
    update_param!(value, :DamageAggregator, :include_cromar_mortality, false)
    update_param!(value, :DamageAggregator, :include_energy, false)
    value
else
    value = get_model(socioeconomics_source = :RFF)
    update_param!(value, :DamageAggregator, :include_slr, false)
    update_param!(value, :DamageAggregator, :include_cromar_mortality, false)
    update_param!(value, :DamageAggregator, :include_energy, false)
    update_param!(value, :DamageAggregator, :include_labor, false)
    value
end

Random.seed!(SEED)
started = now()
common = (
    year = PULSE_YEAR,
    last_year = 2300,
    discount_rates = DISCOUNT_RATES,
    fair_parameter_set = :random,
    rffsp_sampling = :random,
    n = N,
    gas = :CO2,
    output_dir = joinpath(OUTPUT_DIR, "engine"),
    save_md = false,
    save_cpc = false,
    compute_sectoral_values = true,
    CIAM_foresight = :perfect,
    CIAM_GDPcap = true,
    pulse_size = PULSE_SIZE,
)
results = VERSION_NAME == "legacy" ? MimiGIVE.compute_scc(model; common...) : compute_scc(model; common..., compute_labor_country_sccs = false)
matches = [(key, value) for (key, value) in results[:scc] if key.sector == :agriculture]
length(matches) == 1 || error("expected one agriculture result")
key, value = only(matches)
String(key.dr_label) == "2.0%" || error("discount rate differs")
draws = collect(skipmissing(value.sccs)) .* PRICELEVEL_2005_TO_2020
length(draws) == N || error("draw count differs")
all(isfinite, draws) || error("non-finite draws")
peak_rss_bytes = Sys.maxrss()
println("process_peak_rss_bytes=$peak_rss_bytes")
println("max_rss_bytes=$MAX_RSS_BYTES")
peak_rss_bytes <= MAX_RSS_BYTES || error("512 MiB RSS cap exceeded")

open(joinpath(OUTPUT_DIR, "agriculture_summary.csv"), "w") do io
    println(io, "version,expected_scc_2020usd_per_tco2,se_expected_scc,q05,median,q95,draws")
    println(io, join((VERSION_NAME, mean(draws), std(draws) / sqrt(length(draws)), quantile(draws, 0.05), quantile(draws, 0.5), quantile(draws, 0.95), length(draws)), ","))
end
open(joinpath(OUTPUT_DIR, "agriculture_draws_2020usd_per_tco2.csv"), "w") do io
    println(io, "trial,scc_2020usd_per_tco2")
    for (trial, scc) in enumerate(draws)
        println(io, "$trial,$scc")
    end
end
open(joinpath(OUTPUT_DIR, "run_metadata.csv"), "w") do io
    println(io, "version,julia_version,julia_threads,pulse_year,pulse_size,seed,draws,process_peak_rss_bytes,max_rss_bytes")
    println(io, join((VERSION_NAME, VERSION, Threads.nthreads(), PULSE_YEAR, PULSE_SIZE, SEED, N, peak_rss_bytes, MAX_RSS_BYTES), ","))
end
println("started=$started")
println("completed=$(now())")
println("wrote=$OUTPUT_DIR")
