#!/usr/bin/env julia

"""Reproduce an aggregate-water marginal SCC benchmark from MimiFUND v3.13.0.

This is deliberately not a municipal-water estimate. FUND's water calibration
bundles multiple water-resource endpoints. The script exposes one-year and
official ten-year pulse shapes without changing or allocating the endpoint.
"""

using Mimi
using MimiFUND
using Printf

const FIRST_YEAR = 1950
const LAST_YEAR = 2300
const PULSE_YEAR = 2025
const PRTP = 0.02
const ETA = 0.0
const PRICE_FACTOR_1995_TO_2020 = 105.377 / 66.939
const REGION_CODES = ["USA", "CAN", "WEU", "JPK", "ANZ", "EEU", "FSU", "MDE",
                      "CAM", "LAM", "SAS", "SEA", "CHI", "MAF", "SSA", "SIS"]

year_index(year::Int) = year - FIRST_YEAR + 1

function configure_pulse!(mm, shape::String, pulse_size_tco2::Float64)
    add = zeros(length(FIRST_YEAR:3000))
    normalized_total = pulse_size_tco2 / 1e6 * (12 / 44) # tCO2 to MtC
    start = year_index(PULSE_YEAR)
    if shape == "one_year"
        add[start] = normalized_total
    elseif shape == "ten_year"
        add[start:start + 9] .= normalized_total / 10
    else
        error("unknown pulse shape: $shape")
    end
    Mimi.update_param!(mm.modified, :add, add)
    implied_tco2 = sum(add) * 1e6 / (12 / 44)
    @assert isapprox(implied_tco2, pulse_size_tco2; rtol=1e-12)
end

function discount_factors(mm, ntimesteps::Int)
    ypc = mm.base[:socioeconomic, :ypc]
    factors = zeros(ntimesteps, length(REGION_CODES))
    for region in eachindex(REGION_CODES)
        factor = 1.0
        for time in year_index(PULSE_YEAR):ntimesteps
            factors[time, region] = factor
            growth = (ypc[time, region] - ypc[time - 1, region]) / ypc[time - 1, region]
            factor /= 1 + PRTP + ETA * growth
        end
    end
    factors
end

function run_case(shape::String, pulse_size_tco2::Float64)
    mm = MimiFUND.get_marginal_model(year=PULSE_YEAR, gas=:CO2,
                                     pulse_size=pulse_size_tco2)
    configure_pulse!(mm, shape, pulse_size_tco2)
    ntimesteps = year_index(LAST_YEAR)
    Mimi.run(mm; ntimesteps=ntimesteps)

    # MarginalModel indexing returns (modified - base) / pulse_size.
    # The water component is in billions of 1995 USD. In FUND's economic-loss
    # aggregator, water enters with a negative sign, so damage is -Δwater.
    marginal_water_billion_1995usd_per_tco2 = mm[:impactwaterresources, :water]
    marginal_damage_1995usd_per_tco2 = -1e9 .* marginal_water_billion_1995usd_per_tco2
    factors = discount_factors(mm, ntimesteps)
    discounted_by_region = vec(sum(marginal_damage_1995usd_per_tco2[1:ntimesteps, :] .* factors,
                                   dims=1))
    annual_global = vec(sum(marginal_damage_1995usd_per_tco2[1:ntimesteps, :], dims=2))
    annual_discounted = vec(sum(marginal_damage_1995usd_per_tco2[1:ntimesteps, :] .* factors,
                                dims=2))
    return (scc_1995=sum(discounted_by_region),
            scc_2020=sum(discounted_by_region) * PRICE_FACTOR_1995_TO_2020,
            discounted_by_region=discounted_by_region,
            annual_global=annual_global,
            annual_discounted=annual_discounted)
end

function write_outputs(output_dir::String)
    mkpath(output_dir)
    cases = [("one_year", 1e7), ("one_year", 1e8),
             ("ten_year", 1e7), ("ten_year", 1e8)]
    results = Dict((shape, pulse) => run_case(shape, pulse) for (shape, pulse) in cases)

    open(joinpath(output_dir, "mimifund_aggregate_water_cases.csv"), "w") do io
        println(io, "pulse_shape,pulse_size_tco2,pulse_year,last_year,prtp,eta,source_price_year,target_price_year,aggregate_water_scc_1995usd_per_tco2,aggregate_water_scc_2020usd_per_tco2")
        for (shape, pulse) in cases
            result = results[(shape, pulse)]
            @printf(io, "%s,%.0f,%d,%d,%.8f,%.8f,1995,2020,%.12f,%.12f\n",
                    shape, pulse, PULSE_YEAR, LAST_YEAR, PRTP, ETA,
                    result.scc_1995, result.scc_2020)
        end
    end

    central = results[("one_year", 1e7)]
    open(joinpath(output_dir, "mimifund_aggregate_water_annual_central.csv"), "w") do io
        println(io, "year,undiscounted_global_marginal_damage_1995usd_per_tco2,discounted_global_marginal_damage_1995usd_per_tco2")
        for year in PULSE_YEAR:LAST_YEAR
            index = year_index(year)
            @printf(io, "%d,%.12f,%.12f\n", year,
                    central.annual_global[index], central.annual_discounted[index])
        end
    end

    open(joinpath(output_dir, "mimifund_aggregate_water_region_central.csv"), "w") do io
        println(io, "fund_region,discounted_aggregate_water_scc_1995usd_per_tco2,discounted_aggregate_water_scc_2020usd_per_tco2")
        for (index, region) in enumerate(REGION_CODES)
            value = central.discounted_by_region[index]
            @printf(io, "%s,%.12f,%.12f\n", region, value, value * PRICE_FACTOR_1995_TO_2020)
        end
    end

    central_10m = results[("one_year", 1e7)].scc_1995
    central_100m = results[("one_year", 1e8)].scc_1995
    relative_difference = abs(central_100m - central_10m) / max(abs(central_10m), eps())
    @printf("aggregate_water_scc_1995usd_per_tco2=%.12f\n", central_10m)
    @printf("aggregate_water_scc_2020usd_per_tco2=%.12f\n", results[("one_year", 1e7)].scc_2020)
    @printf("one_year_pulse_size_relative_difference=%.12g\n", relative_difference)
end

length(ARGS) == 1 || error("usage: compute_mimifund_aggregate_water_benchmark.jl OUTPUT_DIR")
write_outputs(ARGS[1])
