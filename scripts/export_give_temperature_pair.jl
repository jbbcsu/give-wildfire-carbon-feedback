#!/usr/bin/env julia

# Regenerate the baseline/pulse temperature, consumption, and Ramsey-discount
# pair. The committed CSV is hash-pinned so reproducing the flood calculation
# does not require Julia.

using Mimi
using MimiGIVE

const YEARS = collect(1750:2300)
const PULSE_YEAR = 2025
const PULSE_SIZE_GTC = 1e-4
const CONUS_MULTIPLIER = 1.421
const REFERENCE_YEAR = 1995
const PRTP = 0.0019745879362491614
const ETA = 1.244458999

length(ARGS) == 1 || error("usage: export_give_temperature_pair.jl OUTPUT.csv")
output = abspath(ARGS[1])
ispath(output) && error("fresh output required: $output")
mkpath(dirname(output))

model = MimiGIVE.get_model(socioeconomics_source = :RFF)
marginal = MimiGIVE.get_marginal_model(
    model; year = PULSE_YEAR, gas = :CO2, pulse_size = PULSE_SIZE_GTC,
)
Mimi.run(marginal)

base_temperature = marginal.base[:temperature, :T]
pulse_temperature = marginal.modified[:temperature, :T]
base_cpc = marginal.base[:global_netconsumption, :net_cpc]
ref_index = findfirst(isequal(REFERENCE_YEAR), YEARS)
pulse_index = findfirst(isequal(PULSE_YEAR), YEARS)

open(output, "w") do io
    println(io, "year,base_gmst_c,pulse_gmst_c,base_conus_anomaly_c,pulse_conus_anomaly_c,base_net_cpc,ramsey_discount_factor")
    for (index, year) in enumerate(YEARS)
        base_anomaly = CONUS_MULTIPLIER * (base_temperature[index] - base_temperature[ref_index])
        pulse_anomaly = CONUS_MULTIPLIER * (pulse_temperature[index] - pulse_temperature[ref_index])
        discount = year < PULSE_YEAR ? 0.0 :
            (base_cpc[pulse_index] / base_cpc[index])^ETA / (1 + PRTP)^(year - PULSE_YEAR)
        println(io, join((year, base_temperature[index], pulse_temperature[index], base_anomaly,
            pulse_anomaly, base_cpc[index], discount), ","))
    end
end

println("wrote=$output")

