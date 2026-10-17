using Mimi
using MimiFUND
using SHA
using Printf

const EXPECTED_COMMIT = "3f5fe29ffb753a49ff070d04b74ae42abd23576b"
const REGIONS = ["USA", "CAN", "WEU", "JPK", "ANZ", "EEU", "FSU", "MDE",
                 "CAM", "LAM", "SAS", "SEA", "CHI", "MAF", "SSA", "SIS"]
const USD1995_TO_USD2020 = 105.377 / 66.939
const PULSE_YEAR = 2025
const LAST_YEAR = 3000
const FORBM = [5.325e-5, 1.123e-5, 2.528e-5, 4.173e-5, -0.0001211,
               5.462e-5, -2.348e-5, 0.0, 1.806e-5, 2.411e-5, 6.237e-5,
               6.674e-5, 8.723e-5, 0.0, 1.141e-5, 0.0]
const FORBM_SD = [1.422e-5, 7.152e-5, 5.7e-6, 1.235e-5, 3.255e-5,
                  2.472e-5, 5.312e-5, 3.386e-5, 3.429e-5, 1.195e-5,
                  2.294e-5, 2.772e-5, 3.22e-5, 3.386e-5, 3.459e-5, 3.386e-5]

root = normpath(joinpath(@__DIR__, ".."))
source = get(ENV, "MIMIFUND_SOURCE", joinpath(root, "data", "raw", "MimiFUND-v3.13.0"))
outdir = joinpath(root, "results")
mkpath(outdir)

function verify_source(source)
    isdir(joinpath(source, ".git")) || error("MIMIFUND_SOURCE is not a Git checkout: $source")
    commit = readchomp(`git -C $source rev-parse HEAD`)
    commit == EXPECTED_COMMIT || error("MimiFUND commit mismatch: $commit")
    manifest = joinpath(root, "config", "source_manifest.csv")
    for line in readlines(manifest)[2:end]
        isempty(strip(line)) && continue
        fields = split(line, ',')
        path, expected = fields[4], fields[5]
        actual = bytes2hex(sha256(read(joinpath(source, path))))
        actual == expected || error("SHA-256 mismatch for $path")
    end
end

function discount_matrix(mm, nt, rate)
    df = zeros(nt, length(REGIONS))
    first = MimiFUND.getindexfromyear(PULSE_YEAR)
    for r in eachindex(REGIONS), t in first:nt
        df[t, r] = (1 + rate)^(-(t - first))
    end
    return df
end

function ramsey_matrix(mm, nt; eta=1.45, prtp=0.015)
    ypc = mm.base[:socioeconomic, :ypc]
    df = zeros(nt, length(REGIONS))
    first = MimiFUND.getindexfromyear(PULSE_YEAR)
    for r in eachindex(REGIONS)
        x = 1.0
        for t in first:nt
            df[t, r] = x
            growth = (ypc[t, r] - ypc[t - 1, r]) / ypc[t - 1, r]
            x /= 1 + prtp + eta * growth
        end
    end
    return df
end

function run_case(; pulse_size=1e7, forco2=nothing, forel=nothing,
                  fornl=nothing, forbm=nothing)
    model = MimiFUND.get_model()
    if forco2 !== nothing
        update_param!(model, :impactforests, :forco2, forco2)
    end
    forel !== nothing && update_param!(model, :impactforests, :forel, forel)
    fornl !== nothing && update_param!(model, :impactforests, :fornl, fornl)
    forbm !== nothing && update_param!(model, :forbm, forbm)
    mm = MimiFUND.get_marginal_model(model; year=PULSE_YEAR, gas=:CO2,
                                     pulse_size=pulse_size)
    nt = MimiFUND.getindexfromyear(LAST_YEAR)
    run(mm; ntimesteps=nt)
    # Mimi MarginalModel divides differences by pulse_size. FUND forestry is a
    # benefit in billion 1995 USD and is subtracted in impact aggregation.
    marginal_damage = -1e9 .* mm[:impactforests, :forests]
    return mm, marginal_damage, nt
end

function scc(md, df, nt; horizon=2300)
    last = min(nt, MimiFUND.getindexfromyear(horizon))
    return sum(md[2:last, :] .* df[2:last, :])
end

verify_source(source)
mm, central, nt = run_case()
mm_small, small_pulse, nt_small = run_case(pulse_size=1e6)
mm_temp, temperature_only, nt_temp = run_case(forco2=0.0)
co2_only = central .- temperature_only

rates = [0.02, 0.025, 0.03]
central_1995 = Dict(rate => scc(central, discount_matrix(mm, nt, rate), nt) for rate in rates)
temp_1995 = Dict(rate => scc(temperature_only, discount_matrix(mm_temp, nt_temp, rate), nt_temp) for rate in rates)
co2_1995 = Dict(rate => scc(co2_only, discount_matrix(mm, nt, rate), nt) for rate in rates)
small_1995 = scc(small_pulse, discount_matrix(mm_small, nt_small, 0.02), nt_small)
ramsey_1995 = scc(central, ramsey_matrix(mm, nt), nt)
horizon_2100 = scc(central, discount_matrix(mm, nt, 0.02), nt; horizon=2100)
horizon_3000 = scc(central, discount_matrix(mm, nt, 0.02), nt; horizon=3000)
linearity_relerr = abs(small_1995 - central_1995[0.02]) / max(abs(central_1995[0.02]), eps())

# One-at-a-time ±1 source-standard-deviation diagnostics. These are not a
# confidence interval: the legacy source distributions are neither a modern
# posterior nor necessarily independent.
sensitivity_specs = [
    ("forbm_minus_1sd", (; forbm=FORBM .- FORBM_SD)),
    ("forbm_plus_1sd", (; forbm=FORBM .+ FORBM_SD)),
    ("forco2_minus_1sd", (; forco2=2.2972 - 1.1486)),
    ("forco2_plus_1sd", (; forco2=2.2972 + 1.1486)),
    ("forel_minus_1sd", (; forel=-0.51)),
    ("forel_plus_1sd", (; forel=-0.11)),
    ("fornl_minus_1sd", (; fornl=0.5)),
    ("fornl_plus_1sd", (; fornl=1.5)),
]
sensitivity = Dict{String, Float64}("central" => central_1995[0.02] * USD1995_TO_USD2020)
for (name, kwargs) in sensitivity_specs
    mm_s, md_s, nt_s = run_case(; kwargs...)
    value = scc(md_s, discount_matrix(mm_s, nt_s, 0.02), nt_s) * USD1995_TO_USD2020
    sensitivity[name] = value
end

open(joinpath(outdir, "summary.csv"), "w") do io
    println(io, "metric,value,unit")
    for rate in rates
        key = replace(@sprintf("%.3f", rate), "." => "p")
        @printf(io, "central_fixed_%s_1995usd,%.12g,1995_USD_per_tCO2\n", key, central_1995[rate])
        @printf(io, "central_fixed_%s_2020usd,%.12g,2020_USD_per_tCO2\n", key, central_1995[rate] * USD1995_TO_USD2020)
        @printf(io, "temperature_only_fixed_%s_2020usd,%.12g,2020_USD_per_tCO2\n", key, temp_1995[rate] * USD1995_TO_USD2020)
        @printf(io, "co2_only_fixed_%s_2020usd,%.12g,2020_USD_per_tCO2\n", key, co2_1995[rate] * USD1995_TO_USD2020)
    end
    @printf(io, "central_ramsey_1995usd,%.12g,1995_USD_per_tCO2\n", ramsey_1995)
    @printf(io, "central_ramsey_2020usd,%.12g,2020_USD_per_tCO2\n", ramsey_1995 * USD1995_TO_USD2020)
    @printf(io, "fixed_2pct_horizon_2100_2020usd,%.12g,2020_USD_per_tCO2\n", horizon_2100 * USD1995_TO_USD2020)
    @printf(io, "fixed_2pct_horizon_3000_2020usd,%.12g,2020_USD_per_tCO2\n", horizon_3000 * USD1995_TO_USD2020)
    @printf(io, "pulse_linearity_relative_error,%.12g,ratio\n", linearity_relerr)
end

open(joinpath(outdir, "parameter_sensitivity_fixed_2pct_2020usd.csv"), "w") do io
    println(io, "scenario,scc_2020_usd_per_tco2,interpretation")
    for name in sort(collect(keys(sensitivity)))
        label = name == "central" ? "source default" : "one-at-a-time source parameter diagnostic"
        @printf(io, "%s,%.12g,%s\n", name, sensitivity[name], label)
    end
end

df2 = discount_matrix(mm, nt, 0.02)
regional = vec(sum(central[2:MimiFUND.getindexfromyear(2300), :] .*
                   df2[2:MimiFUND.getindexfromyear(2300), :], dims=1)) .* USD1995_TO_USD2020
open(joinpath(outdir, "regional_fixed_2pct_2020usd.csv"), "w") do io
    println(io, "region,scc_2020_usd_per_tco2")
    for (region, value) in zip(REGIONS, regional)
        @printf(io, "%s,%.12g\n", region, value)
    end
end

linearity_relerr < 1e-4 || error("Pulse linearity gate failed: $linearity_relerr")
abs(central_1995[0.02] - (temp_1995[0.02] + co2_1995[0.02])) < 1e-10 ||
    error("Channel add-up gate failed")

@printf("Forestry benchmark (2020 USD/tCO2; 2%%): %.6f\n", central_1995[0.02] * USD1995_TO_USD2020)
@printf("Pulse-linearity relative error: %.3g\n", linearity_relerr)
