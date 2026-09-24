#!/usr/bin/env julia

using Mimi
using MimiGIVE
using SHA

length(ARGS) == 1 || error("usage: export_give_deterministic_discount_path.jl OUTPUT.csv")
output = ARGS[1]
isfile(output) && error("fresh output required: $output")

const RFF_SAMPLE_ID = 6546
model = MimiGIVE.get_model(socioeconomics_source=:RFF, RFFSPsample=RFF_SAMPLE_ID)
Mimi.run(model)

years = collect(1750:2300)
cpc = model[:global_netconsumption, :net_cpc]
net_consumption = model[:global_netconsumption, :net_consumption]
global_gdp = model[:global_netconsumption, :global_gdp]
global_population = model[:global_netconsumption, :global_population]
total_damage = model[:DamageAggregator, :total_damage]
length(cpc) == length(years) || error("unexpected GIVE time dimension")

open(output, "w") do io
    println(io, "year,rff_sample_id,net_cpc_2005usd_per_person,net_consumption_billion_2005usd,global_gdp_billion_2005usd,global_population_million,total_damage_2005usd")
    for (index, year) in enumerate(years)
        year < 2020 && continue
        values = (cpc[index], net_consumption[index], global_gdp[index], global_population[index], total_damage[index])
        all(isfinite, values) || error("nonfinite deterministic GIVE value in $year")
        println(io, join((year, RFF_SAMPLE_ID, values...), ","))
    end
end

println("rows=281")
println("rff_sample_id=$(RFF_SAMPLE_ID)")
println("output_sha256=$(bytes2hex(open(SHA.sha256, output)))")
