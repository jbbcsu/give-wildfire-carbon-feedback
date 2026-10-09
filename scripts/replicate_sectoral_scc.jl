using DataFrames
using Dates
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
const LABOR_FUNCTION = get(ENV, "LABOR_FUNCTION", "ISO")
const DISCOUNT_RATES = [
    (label = "2.0%", prtp = exp(0.001972641) - 1, eta = 1.244458999),
]

LABOR_FUNCTION in ("ISO", "Lancet") || error("LABOR_FUNCTION must be ISO or Lancet")
N >= 2 || error("N_TRIALS must be at least 2")

output_dir = joinpath(
    ROOT,
    "output",
    "replication",
    "pulse2025_n$(N)_$(lowercase(LABOR_FUNCTION))_seed$(SEED)",
)
mkpath(output_dir)

model = get_model(
    socioeconomics_source = :RFF,
    labor_damage_function = LABOR_FUNCTION,
)
Random.seed!(SEED)
started = now()
results = compute_scc(
    model;
    year = 2025,
    last_year = 2300,
    discount_rates = DISCOUNT_RATES,
    fair_parameter_set = :random,
    rffsp_sampling = :random,
    n = N,
    gas = :CO2,
    output_dir = output_dir,
    save_md = false,
    save_cpc = false,
    compute_sectoral_values = true,
    CIAM_foresight = :perfect,
    CIAM_GDPcap = true,
    pulse_size = 1e-4,
    compute_labor_country_sccs = false,
)

rows = NamedTuple[]
for (key, value) in results[:scc]
    draws = collect(skipmissing(value.sccs)) .* PRICELEVEL_2005_TO_2020
    push!(
        rows,
        (
            sector = String(key.sector),
            discount_rate = String(key.dr_label),
            expected_scc_2020usd_per_tco2 = mean(draws),
            se_expected_scc = std(draws) / sqrt(length(draws)),
            q05 = quantile(draws, 0.05),
            median = quantile(draws, 0.50),
            q95 = quantile(draws, 0.95),
            draws = length(draws),
            labor_function = LABOR_FUNCTION,
        ),
    )
end

sort!(rows; by = row -> row.sector)
summary_path = joinpath(output_dir, "sectoral_scc_summary.csv")
open(summary_path, "w") do io
    println(
        io,
        "sector,discount_rate,expected_scc_2020usd_per_tco2,se_expected_scc,q05,median,q95,draws,labor_function",
    )
    for row in rows
        println(
            io,
            join(
                (
                    row.sector,
                    row.discount_rate,
                    row.expected_scc_2020usd_per_tco2,
                    row.se_expected_scc,
                    row.q05,
                    row.median,
                    row.q95,
                    row.draws,
                    row.labor_function,
                ),
                ",",
            ),
        )
    end
end

println("started=$started")
println("completed=$(now())")
println("wrote=$summary_path")
for row in rows
    println(row)
end

