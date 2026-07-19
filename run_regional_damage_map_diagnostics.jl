#!/usr/bin/env julia

# Regional damage diagnostics for the wildfire-carbon GIVE extension.
#
# This script creates country-level map inputs from the deterministic source-
# informed mean wildfire CO2 pathway. GIVE's core damage modules are not all
# country-native, so the output is deliberately labeled as a diagnostic:
# - mortality and energy are country-level in GIVE;
# - agriculture is FUND-region-level and is allocated to countries by baseline
#   country GDP share within each FUND region;
# - CIAM sea-level damages and Qiu-style smoke mortality are not included.

using CSVFiles
using DataFrames
using Mimi
using MimiGIVE
using Statistics

include(joinpath(@__DIR__, "WildfireGIVE.jl"))
include(joinpath(@__DIR__, "..", "src", "discount_rates.jl"))

using .WildfireGIVE

const MODEL_YEARS = collect(1750:2300)
const DAMAGE_YEARS = collect(2020:2300)
const USD_2005_TO_2020 = MimiGIVE.pricelevel_2005_to_2020
const CO2_MASS_CONVERSION = 12.0 / 44.0

zero_missing(A) = Float64.(coalesce.(A, 0.0))

function read_fund_mapping(repo::AbstractString)
    mapping = DataFrame(load(joinpath(repo, "packages", "MimiGIVE", "data", "Mapping_countries_to_fund_regions.csv")))
    rename!(mapping, names(mapping)[1] => :ISO3)
    return mapping
end

function read_mean_wildfire_path(repo::AbstractString)
    path = joinpath(repo, "output", "wildfire_sectoral_diagnostics_100", "mean_wildfire_emissions_path.csv")
    isfile(path) || error("Mean wildfire path not found: $path. Run run_sectoral_diagnostics.jl first.")
    df = DataFrame(load(path))
    sort!(df, :year)
    return df
end

function build_models(mean_path::DataFrame)
    baseline = MimiGIVE.get_model(socioeconomics_source = :RFF)
    wildfire, _ = WildfireGIVE.get_model(
        include_wildfire_co2 = true,
        wildfire_scenario = :custom,
        custom_gtco2 = mean_path.wildfire_gtco2,
        socioeconomics_source = :RFF,
    )
    Mimi.run(baseline)
    Mimi.run(wildfire)
    return baseline, wildfire
end

function discount_factors_2pct(base_model)
    dr = only([d for d in discount_rates if d.label == "2.0%"])
    years = collect(Mimi.dim_keys(base_model, :time))
    cpc = base_model[:global_netconsumption, :net_cpc]
    i2020 = findfirst(isequal(2020), years)
    damage_idxs = indexin(DAMAGE_YEARS, years)
    cpc_2020 = cpc[i2020]
    return [
        (cpc_2020 / cpc[i])^dr.eta * 1.0 / (1.0 + dr.prtp)^(year - 2020)
        for (i, year) in zip(damage_idxs, DAMAGE_YEARS)
    ]
end

function allocate_agriculture_to_countries(ag_region_delta, gdp, countries, fund_regions, mapping::DataFrame)
    country_fund = Dict(String(row.ISO3) => String(row.fundregion) for row in eachrow(mapping))
    fund_to_country_idxs = Dict{String, Vector{Int}}()
    for fund in String.(fund_regions)
        fund_to_country_idxs[fund] = Int[]
    end
    for (i, iso3) in enumerate(String.(countries))
        fund = get(country_fund, iso3, "")
        if haskey(fund_to_country_idxs, fund)
            push!(fund_to_country_idxs[fund], i)
        end
    end

    out = zeros(size(gdp, 1), length(countries))
    for (fidx, fund) in enumerate(String.(fund_regions))
        country_idxs = fund_to_country_idxs[fund]
        isempty(country_idxs) && continue
        for tidx in axes(gdp, 1)
            region_gdp = sum(gdp[tidx, country_idxs])
            if region_gdp > 0
                for cidx in country_idxs
                    out[tidx, cidx] = ag_region_delta[tidx, fidx] * gdp[tidx, cidx] / region_gdp
                end
            else
                out[tidx, country_idxs] .= ag_region_delta[tidx, fidx] / length(country_idxs)
            end
        end
    end
    return out
end

function core_damage_country_matrices(base_model, wildfire_model, mapping::DataFrame)
    years = collect(Mimi.dim_keys(base_model, :time))
    countries = collect(Mimi.dim_keys(base_model, :country))
    fund_regions = collect(Mimi.dim_keys(base_model, :fund_regions))

    mortality = zero_missing(
        (wildfire_model[:CromarMortality, :mortality_costs] .-
         base_model[:CromarMortality, :mortality_costs]) .* USD_2005_TO_2020
    )

    energy = zero_missing(
        (wildfire_model[:energy_damages, :energy_costs_dollar] .-
         base_model[:energy_damages, :energy_costs_dollar]) .* 1e9 .* USD_2005_TO_2020
    )

    agriculture_region = zero_missing(
        (wildfire_model[:Agriculture, :agcost] .-
         base_model[:Agriculture, :agcost]) .* 1e9 .* USD_2005_TO_2020
    )

    gdp = zero_missing(base_model[:Socioeconomic, :gdp])
    agriculture = allocate_agriculture_to_countries(agriculture_region, gdp, countries, fund_regions, mapping)

    return (
        years = years,
        countries = countries,
        mortality = mortality,
        energy = energy,
        agriculture = agriculture,
        total = mortality .+ energy .+ agriculture,
    )
end

function marginal_damage_country_matrices(base_model, wildfire_model, mapping::DataFrame)
    years = collect(Mimi.dim_keys(base_model, :time))
    countries = collect(Mimi.dim_keys(base_model, :country))
    fund_regions = collect(Mimi.dim_keys(base_model, :fund_regions))

    baseline_mm = MimiGIVE.get_marginal_model(deepcopy(base_model); year = 2020, gas = :CO2, pulse_size = 1.0)
    wildfire_mm = MimiGIVE.get_marginal_model(deepcopy(wildfire_model); year = 2020, gas = :CO2, pulse_size = 1.0)
    Mimi.run(baseline_mm)
    Mimi.run(wildfire_mm)

    mortality = zero_missing(
        (wildfire_mm[:CromarMortality, :mortality_costs] .-
         baseline_mm[:CromarMortality, :mortality_costs]) .* CO2_MASS_CONVERSION .* USD_2005_TO_2020
    )

    energy = zero_missing(
        (wildfire_mm[:energy_damages, :energy_costs_dollar] .-
         baseline_mm[:energy_damages, :energy_costs_dollar]) .* 1e9 .* CO2_MASS_CONVERSION .* USD_2005_TO_2020
    )

    agriculture_region = zero_missing(
        (wildfire_mm[:Agriculture, :agcost] .-
         baseline_mm[:Agriculture, :agcost]) .* 1e9 .* CO2_MASS_CONVERSION .* USD_2005_TO_2020
    )

    gdp = zero_missing(base_model[:Socioeconomic, :gdp])
    agriculture = allocate_agriculture_to_countries(agriculture_region, gdp, countries, fund_regions, mapping)

    return (
        years = years,
        countries = countries,
        mortality = mortality,
        energy = energy,
        agriculture = agriculture,
        total = mortality .+ energy .+ agriculture,
    )
end

function annual_at(mat, years, year)
    idx = findfirst(isequal(year), years)
    idx === nothing && error("Year $year not found in model years.")
    return vec(mat[idx, :])
end

function cumulative_discounted(mat, years, discount)
    damage_idxs = indexin(DAMAGE_YEARS, years)
    out = zeros(size(mat, 2))
    for (j, idx) in enumerate(damage_idxs)
        out .+= vec(mat[idx, :]) .* discount[j]
    end
    return out
end

function country_output_frame(base_model, core, marginal, mapping::DataFrame, discount)
    years = core.years
    countries = String.(core.countries)
    country_names = Dict(String(row.ISO3) => String(row.country) for row in eachrow(mapping))
    fund_regions = Dict(String(row.ISO3) => String(row.fundregion) for row in eachrow(mapping))
    pop = base_model[:Socioeconomic, :population]
    i2020 = findfirst(isequal(2020), years)
    i2100 = findfirst(isequal(2100), years)

    core_pv_total = cumulative_discounted(core.total, years, discount)
    core_pv_mortality = cumulative_discounted(core.mortality, years, discount)
    core_pv_energy = cumulative_discounted(core.energy, years, discount)
    core_pv_agriculture = cumulative_discounted(core.agriculture, years, discount)

    md_pv_total = cumulative_discounted(marginal.total, years, discount)
    md_pv_mortality = cumulative_discounted(marginal.mortality, years, discount)
    md_pv_energy = cumulative_discounted(marginal.energy, years, discount)
    md_pv_agriculture = cumulative_discounted(marginal.agriculture, years, discount)

    out = DataFrame(
        iso3 = countries,
        country = [get(country_names, iso3, iso3) for iso3 in countries],
        fund_region = [get(fund_regions, iso3, "") for iso3 in countries],

        total_damage_delta_2050_billion_2020usd_per_year = annual_at(core.total, years, 2050) ./ 1e9,
        total_damage_delta_2100_billion_2020usd_per_year = annual_at(core.total, years, 2100) ./ 1e9,
        total_damage_delta_2300_billion_2020usd_per_year = annual_at(core.total, years, 2300) ./ 1e9,

        mortality_damage_delta_2100_billion_2020usd_per_year = annual_at(core.mortality, years, 2100) ./ 1e9,
        energy_damage_delta_2100_billion_2020usd_per_year = annual_at(core.energy, years, 2100) ./ 1e9,
        agriculture_damage_delta_2100_billion_2020usd_per_year = annual_at(core.agriculture, years, 2100) ./ 1e9,

        cumulative_discounted_damage_delta_billion_2020usd = core_pv_total ./ 1e9,
        cumulative_discounted_mortality_delta_billion_2020usd = core_pv_mortality ./ 1e9,
        cumulative_discounted_energy_delta_billion_2020usd = core_pv_energy ./ 1e9,
        cumulative_discounted_agriculture_delta_billion_2020usd = core_pv_agriculture ./ 1e9,

        incremental_scc_core_delta_2020usd_per_tco2 = md_pv_total,
        incremental_scc_mortality_delta_2020usd_per_tco2 = md_pv_mortality,
        incremental_scc_energy_delta_2020usd_per_tco2 = md_pv_energy,
        incremental_scc_agriculture_delta_2020usd_per_tco2 = md_pv_agriculture,

        population_2020_million = vec(pop[i2020, :]),
        population_2100_million = vec(pop[i2100, :]),
    )

    out[!, :cumulative_discounted_damage_delta_2020usd_per_2020_person] =
        out.cumulative_discounted_damage_delta_billion_2020usd .* 1e9 ./ (out.population_2020_million .* 1e6)
    out[!, :total_damage_delta_2100_2020usd_per_2100_person_per_year] =
        out.total_damage_delta_2100_billion_2020usd_per_year .* 1e9 ./ (out.population_2100_million .* 1e6)

    return out
end

function write_top_country_tables(out::DataFrame, output_dir::AbstractString)
    top_total = sort(out, :cumulative_discounted_damage_delta_billion_2020usd, rev = true)[1:min(20, nrow(out)), :]
    top_md = sort(out, :incremental_scc_core_delta_2020usd_per_tco2, rev = true)[1:min(20, nrow(out)), :]
    top_total |> save(joinpath(output_dir, "top20_total_incremental_damage_countries.csv"))
    top_md |> save(joinpath(output_dir, "top20_incremental_scc_core_countries.csv"))
end

function run_regional_damage_diagnostics(;
    repo = normpath(joinpath(@__DIR__, "..")),
    output_dir = joinpath(repo, "output", "wildfire_regional_damage_diagnostics"),
)
    mkpath(output_dir)
    mapping = read_fund_mapping(repo)
    mean_path = read_mean_wildfire_path(repo)
    baseline, wildfire = build_models(mean_path)
    discount = discount_factors_2pct(baseline)

    core = core_damage_country_matrices(baseline, wildfire, mapping)
    marginal = marginal_damage_country_matrices(baseline, wildfire, mapping)
    out = country_output_frame(baseline, core, marginal, mapping, discount)
    sort!(out, :iso3)
    out |> save(joinpath(output_dir, "regional_damage_delta_by_country.csv"))
    write_top_country_tables(out, output_dir)

    metadata = DataFrame(
        item = [
            "scenario",
            "discounting",
            "included_sectors",
            "excluded_sectors",
            "agriculture_allocation",
            "total_damage_map_units",
            "incremental_scc_map_units",
            "interpretation_warning",
        ],
        value = [
            "Deterministic source-informed mean wildfire CO2 pathway from output/wildfire_sectoral_diagnostics_100/mean_wildfire_emissions_path.csv",
            "2.0% near-term Ramsey discount specification from Rennert et al. replication code",
            "Cromar temperature mortality, Clarke energy, Moore agriculture",
            "CIAM sea-level rise, smoke mortality, non-CO2 fire forcers, adaptation or suppression effects not in these core modules",
            "FUND-region agriculture damage changes allocated to countries by baseline country GDP share within each FUND region and year",
            "Billion 2020 USD for present-value totals; billion 2020 USD per year for annual snapshots",
            "2020 USD per tCO2 change in discounted country-level core marginal damages; excludes CIAM sea-level SCC contribution",
            "These maps are diagnostics, not a welfare-incidence model and not a claim about where fires occur.",
        ],
    )
    metadata |> save(joinpath(output_dir, "regional_damage_map_metadata.csv"))

    println("Wrote regional damage diagnostics to $output_dir")
    println("Top total-damage countries:")
    println(first(sort(out[:, [:iso3, :country, :cumulative_discounted_damage_delta_billion_2020usd]], :cumulative_discounted_damage_delta_billion_2020usd, rev = true), 10))
    println("Top incremental core-SCC countries:")
    println(first(sort(out[:, [:iso3, :country, :incremental_scc_core_delta_2020usd_per_tco2]], :incremental_scc_core_delta_2020usd_per_tco2, rev = true), 10))
end

if abspath(PROGRAM_FILE) == @__FILE__
    repo = length(ARGS) >= 1 ? ARGS[1] : normpath(joinpath(@__DIR__, ".."))
    output_dir = length(ARGS) >= 2 ? ARGS[2] : joinpath(repo, "output", "wildfire_regional_damage_diagnostics")
    run_regional_damage_diagnostics(repo = repo, output_dir = output_dir)
end
