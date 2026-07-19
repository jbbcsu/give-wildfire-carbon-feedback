#!/usr/bin/env julia

# Summarize the public Val Martin, Pierce, and Heald USDA projected fire
# emissions data. The archive does not include CO2 directly, so this script
# extracts CO and burned-area changes as proxies for the projected fire-activity
# scaling in RCP4.5/SSP1 and RCP8.5/SSP3.

using NetCDF
using Printf

const AVOGADRO = 6.02214076e23
const CO_G_PER_MOL = 28.0101
const DAYS_IN_MONTH_NOLEAP = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

function _year_month(date_int)
    s = lpad(string(Int(date_int)), 8, "0")
    return parse(Int, s[1:4]), parse(Int, s[5:6])
end

function _window_label(year)
    if 2001 <= year <= 2010
        return "baseline_2001_2010"
    elseif 2041 <= year <= 2050
        return "midcentury_2041_2050"
    elseif 2091 <= year <= 2100
        return "latecentury_2091_2100"
    else
        return nothing
    end
end

function summarize_co_emissions(path, area_path)
    bb = ncread(path, "bb")
    dates = ncread(path, "date")
    area_km2 = ncread(area_path, "area")
    area_cm2 = area_km2 .* 1e10

    annual = Dict{Int,Float64}()
    for t in eachindex(dates)
        year, month = _year_month(dates[t])
        seconds = DAYS_IN_MONTH_NOLEAP[month] * 24 * 60 * 60
        molecules_per_second = sum(Float64.(bb[:, :, t]) .* area_cm2)
        tg_co = molecules_per_second * seconds / AVOGADRO * CO_G_PER_MOL / 1e12
        annual[year] = get(annual, year, 0.0) + tg_co
    end

    return annual
end

function summarize_area_burned(path)
    burned = ncread(path, "areaburned")
    dates = ncread(path, "date")

    annual = Dict{Int,Float64}()
    for t in eachindex(dates)
        year, _ = _year_month(dates[t])
        value = sum(x -> isfinite(x) ? x : 0.0, Float64.(burned[:, :, t]))
        annual[year] = get(annual, year, 0.0) + value
    end

    return annual
end

function mean_window(annual, label)
    values = Float64[]
    for (year, value) in annual
        _window_label(year) == label && push!(values, value)
    end
    isempty(values) && return NaN
    return sum(values) / length(values)
end

function write_summary(output_path, rows)
    mkpath(dirname(output_path))
    open(output_path, "w") do io
        println(io, "source,scenario,metric,period,value,ratio_to_baseline")
        for row in rows
            @printf(
                io,
                "%s,%s,%s,%s,%.10g,%.10g\n",
                row.source,
                row.scenario,
                row.metric,
                row.period,
                row.value,
                row.ratio,
            )
        end
    end
end

function main()
    zip_extract_root = length(ARGS) >= 1 ? ARGS[1] :
        "/Users/jbb/Dropbox/GIVE/fire_data/usda_val_martin_2018/extract"
    output_path = length(ARGS) >= 2 ? ARGS[2] :
        joinpath(@__DIR__, "source_data", "usda_val_martin_fire_projection_summary.csv")

    area_path = joinpath(zip_extract_root, "Data", "AuxiliaryData", "cesm130_clm5_firemodule_area_f09x125.nc")
    periods = ["baseline_2001_2010", "midcentury_2041_2050", "latecentury_2091_2100"]
    rows = NamedTuple[]

    for scenario in ["RCP45", "RCP85"]
        co_path = joinpath(zip_extract_root, "Data", "Emissions", "CESM_$(scenario)_CO_surface_2000-2050-2100_0.9x1.25.nc")
        burned_path = joinpath(zip_extract_root, "Data", "AuxiliaryData", "CESM_$(scenario)_AreaBurned_2000-2050-2100_0.9x1.25.nc")

        co_annual = summarize_co_emissions(co_path, area_path)
        burned_annual = summarize_area_burned(burned_path)

        for (metric, annual) in [("CO_TgCO_per_year", co_annual), ("area_burned_km2_per_year", burned_annual)]
            baseline = mean_window(annual, "baseline_2001_2010")
            for period in periods
                value = mean_window(annual, period)
                push!(
                    rows,
                    (
                        source = "ValMartinPierceHeald2018_USDA",
                        scenario = scenario,
                        metric = metric,
                        period = period,
                        value = value,
                        ratio = value / baseline,
                    ),
                )
            end
        end
    end

    write_summary(output_path, rows)
    println("Wrote ", output_path)
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
