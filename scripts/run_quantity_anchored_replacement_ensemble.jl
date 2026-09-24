#!/usr/bin/env julia

using DataFrames
using CSVFiles
using Mimi
using MimiGIVE
using SHA

length(ARGS) == 4 || error("usage: script GIVE_ROOT INCREMENT.csv EXPECTED_DIAGNOSTIC.csv OUTPUT.csv")
give_root, increment_path, expected_path, output_path = ARGS
isfile(output_path) && error("fresh output required")
dirname(Base.active_project()) == abspath(give_root) || error("GIVE project mismatch")

project = normpath(joinpath(@__DIR__, ".."))
include(joinpath(project, "src", "AgricultureReplacementAudit.jl"))
include(joinpath(project, "src", "AnchoredAnnualAgriculture.jl"))
using .AgricultureReplacementAudit
using .AnchoredAnnualAgriculture

const PULSE = 0.000025
const RFF_SAMPLE_ID = 6546
const SOURCE_HASH = bytes2hex(sha256(read(increment_path)))
const DISCOUNT_RATES = [
    (label="1.5%", prtp=exp(9.149606e-05)-1, eta=1.016010),
    (label="2.0%", prtp=exp(0.001972641)-1, eta=1.244458999),
    (label="2.5%", prtp=exp(0.004618784)-1, eta=1.421158088),
    (label="3.0%", prtp=exp(0.007702711)-1, eta=1.567899391),
]

increment_frame = DataFrame(load(increment_path))
expected_frame = DataFrame(load(expected_path))
models = sort(unique(String.(increment_frame.climate_model)))
length(models) == 26 || error("climate-model support differs")

original = MimiGIVE.get_model(socioeconomics_source=:RFF, RFFSPsample=RFF_SAMPLE_ID)
Mimi.run(original)
years = collect(Mimi.dim_keys(original, :time))
regions = collect(Mimi.dim_keys(original, :fund_regions))
active = findall(year -> year >= 2020, years)
baseline = zeros(length(years), length(regions))
baseline[active, :] = original[:Agriculture, :agcost][active, :]
baseline_hash = bytes2hex(sha256(reinterpret(UInt8, vec(baseline))))
original_agriculture = copy(original[:DamageAggregator, :agriculture_damage])
original_cpc = copy(original[:global_netconsumption, :net_cpc])

fresh = MimiGIVE.get_model(socioeconomics_source=:RFF, RFFSPsample=RFF_SAMPLE_ID)
anchored = install_anchored_replacement(fresh;
    years=years, regions=regions, baseline_amounts=baseline,
    evidence_role=AnchoredAnnualAgriculture.ROLE,
    baseline_source_hash=baseline_hash)
audit_agriculture_replacement(anchored;
    expected_source_component=:AnchoredAnnualMoney,
    expected_source_variable=:agcost)
Mimi.run(anchored)
base_ag_error = maximum(abs.(anchored[:DamageAggregator, :agriculture_damage][active] .- original_agriculture[active]))
base_cpc_error = maximum(abs.(anchored[:global_netconsumption, :net_cpc][active] .- original_cpc[active]))
base_ag_error == 0.0 || error("anchored baseline agriculture differs")
base_cpc_error == 0.0 || error("anchored baseline CPC differs")

year_index = Dict(year => index for (index, year) in enumerate(years))
region_index = Dict(String(region) => index for (index, region) in enumerate(regions))
year0 = findfirst(==(2020), years)
last = findfirst(==(2300), years)
cpc = anchored[:global_netconsumption, :net_cpc]

open(output_path, "w") do io
    println(io, "climate_model,discount_rate_label,paired_replacement_usd2005_per_tco2,expected_diagnostic_usd2005_per_tco2,expected_diagnostic_usd2020_per_tco2,absolute_error,numerical_error_bound_usd2005_per_tco2,baseline_agriculture_error_usd,baseline_cpc_error,regional_increment_error_billion_usd2005,aggregated_increment_error_usd")
    for (model_number, model_name) in enumerate(models)
        increment = zeros(size(baseline))
        model_rows = filter(row -> String(row.climate_model) == model_name, increment_frame)
        nrow(model_rows) == 281 * 16 || error("regional support differs for $(model_name)")
        for row in eachrow(model_rows)
            increment[year_index[Int(row.year)], region_index[String(row.fund_region)]] =
                Float64(row.marginal_damage_difference_billion_usd2005)
        end
        count(value -> !iszero(value), increment) > 0 || error("empty marginal increment for $(model_name)")

        mm = MimiGIVE.get_marginal_model(anchored; year=2020, gas=:CO2, pulse_size=PULSE)
        set_anchored_pulse_path!(mm.modified;
            years=years, regions=regions, baseline_amounts=baseline,
            marginal_increment=increment,
            evidence_role=AnchoredAnnualAgriculture.ROLE,
            baseline_source_hash=baseline_hash,
            increment_source_hash=SOURCE_HASH)
        audit_agriculture_replacement(mm.base;
            expected_source_component=:AnchoredAnnualMoney,
            expected_source_variable=:agcost)
        audit_agriculture_replacement(mm.modified;
            expected_source_component=:AnchoredAnnualMoney,
            expected_source_variable=:agcost)
        Mimi.run(mm)

        observed_increment = mm.modified[:AnchoredAnnualMoney, :agcost] .- mm.base[:AnchoredAnnualMoney, :agcost]
        increment_error = maximum(abs.(observed_increment[active, :] .- increment[active, :]))
        increment_error <= 1e-12 || error("installed regional increment differs for $(model_name)")
        agriculture_delta = mm.modified[:DamageAggregator, :agriculture_damage] .- mm.base[:DamageAggregator, :agriculture_damage]
        expected_delta = vec(sum(increment, dims=2)) .* 1e9
        agriculture_delta_error = maximum(abs.(agriculture_delta[active] .- expected_delta[active]))
        agriculture_delta_error <= 0.01 || error("aggregated agriculture increment differs for $(model_name)")
        agriculture_md = agriculture_delta .* (12/44) ./ (1e9 * PULSE)
        expected_rows = filter(row ->
            String(row.climate_model) == model_name && row.pulse_size_gtc == PULSE &&
            String(row.adaptation) == "fixed" && String(row.tail_rule) == "uncapped" &&
            String(row.elasticity_id) == "hultgren_pair_010_004" &&
            String(row.yield_to_supply_mapping) == "horizontal_output", expected_frame)
        nrow(expected_rows) == 4 || error("expected diagnostic support differs for $(model_name)")

        for rate in DISCOUNT_RATES
            factors = [(cpc[year0] / cpc[index])^rate.eta /
                (1 + rate.prtp)^(years[index] - 2020) for index in year0:last]
            paired = sum(factors .* agriculture_md[year0:last])
            match = findfirst(value -> isapprox(Float64(value), rate.prtp; rtol=0.0, atol=1e-15), expected_rows.prtp)
            isnothing(match) && error("expected discount schedule absent")
            expected_2005 = Float64(expected_rows[match, :partial_scc_diagnostic_usd2005_per_tco2])
            expected_2020 = Float64(expected_rows[match, :partial_scc_diagnostic_usd2020_per_tco2])
            absolute_error = abs(paired - expected_2005)
            numerical_bound = agriculture_delta_error * sum(abs, factors) * (12/44) / (1e9 * PULSE)
            absolute_error <= numerical_bound + 1e-15 || error("paired replacement differs for $(model_name)")
            println(io, join((model_name, rate.label, paired, expected_2005, expected_2020,
                absolute_error, numerical_bound, base_ag_error, base_cpc_error,
                increment_error, agriculture_delta_error), ","))
        end
        println("completed_model=$(model_number)/$(length(models)) name=$(model_name)"); flush(stdout)
        mm = nothing
        GC.gc()
    end
end

println("status=pass")
println("models=$(length(models))")
println("output_sha256=$(bytes2hex(sha256(read(output_path))))")
