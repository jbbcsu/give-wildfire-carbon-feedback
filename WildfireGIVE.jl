module WildfireGIVE

using CSVFiles
using DataFrames
using Mimi
using MimiGIVE
using Random

export GTCO2_TO_GTC,
       GTC_TO_GTCO2,
       wildfire_co2_path,
       climate_response_wildfire_path,
       canada_2023_excess_wildfire_path,
       source_informed_wildfire_draws,
       write_wildfire_path,
       apply_wildfire_co2!,
       apply_wildfire_temperature_feedback_co2!,
       get_model

const GTCO2_TO_GTC = 12.0 / 44.0
const GTC_TO_GTCO2 = 44.0 / 12.0

const DEFAULT_MODEL_YEARS = collect(1750:2300)
const CANADA_2023_EXCESS_GTCO2 = ((647.0 - 121.0) / 1000.0) * GTC_TO_GTCO2

# Temperature-lagged wildfire CO2 feedback.
#
# This component adds a simple global fire-carbon feedback to the annual CO2
# emissions stream. Fire emissions in year `t` respond to global mean temperature
# in year `t-1`, which avoids a same-year algebraic loop and mirrors the lagged
# temperature dependence already used inside FAIR's CO2 carbon cycle.
#
# All quantities that enter FAIR are GtC/yr. `reference_fire_gtc` is a gross
# global fire-carbon flux. The feedback is scaled by (1) a fractional response per
# degree C, (2) a net-persistence fraction, and (3) a not-already-embedded fraction
# to reduce double counting with RFF-SP aggregate AFOLU / natural-stock CO2.
@defcomp wildfire_temperature_feedback_co2 begin
    baseline_co2              = Parameter(index=[time]) # Baseline annual CO2 emissions (GtC yr^-1).
    temperature               = Parameter(index=[time]) # Global mean surface temperature anomaly (K).
    start_year                = Parameter()             # First year in which the feedback may add emissions.
    reference_temperature_year = Parameter{Int}()       # Year used as the zero-feedback temperature reference.
    reference_fire_gtc        = Parameter()             # Gross reference global fire carbon emissions (GtC yr^-1).
    sensitivity_per_c         = Parameter()             # Fractional gross fire-emissions increment per K.
    net_persistence_fraction  = Parameter()             # Share of gross fire carbon treated as persistent net CO2.
    not_embedded_fraction     = Parameter()             # Share not assumed already embedded in aggregate baseline CO2.
    max_feedback_gtc          = Parameter()             # Diagnostic cap for annual added fire CO2 (GtC yr^-1).

    temperature_reference_c    = Variable(index=[time])  # Trial-specific reference temperature anomaly (K).
    warming_lagged_c           = Variable(index=[time])  # Positive lagged warming above the reference temperature (K).
    feedback_gtc              = Variable(index=[time])  # Added net fire CO2 entering FAIR (GtC yr^-1).
    output_co2                = Variable(index=[time])  # Baseline plus feedback CO2 emissions (GtC yr^-1).

    function run_timestep(p, v, d, t)
        if is_first(t) || gettime(t) <= p.start_year
            v.temperature_reference_c[t] = 0.0
            v.warming_lagged_c[t] = 0.0
            v.feedback_gtc[t] = 0.0
        else
            v.temperature_reference_c[t] = p.temperature[TimestepValue(p.reference_temperature_year)]
            v.warming_lagged_c[t] = max(p.temperature[t-1] - v.temperature_reference_c[t], 0.0)
            v.feedback_gtc[t] = min(
                p.reference_fire_gtc *
                p.sensitivity_per_c *
                v.warming_lagged_c[t] *
                p.net_persistence_fraction *
                p.not_embedded_fraction,
                p.max_feedback_gtc,
            )
        end

        v.output_co2[t] = p.baseline_co2[t] + v.feedback_gtc[t]
    end
end

"""
    wildfire_co2_path(; scenario=:medium, years=1750:2300, start_year=2020,
        custom_gtco2=nothing)

Construct a stylized *net additional* wildfire CO2 emissions path in GtCO2/yr and
GtC/yr. The path is intended to represent emissions above whatever fire-related
net land-carbon flux is already implicit in the baseline emissions scenario.

Scenarios:
- `:low`: 0.10 GtCO2/yr from `start_year` onward.
- `:medium`: 0.25 GtCO2/yr in `start_year`, growing 0.5%/yr.
- `:high`: 0.50 GtCO2/yr in `start_year`, growing 1.0%/yr, capped at 5.0 GtCO2/yr.
- `:stress`: 2.00 GtCO2/yr in `start_year`, growing 1.5%/yr, capped at 20.0 GtCO2/yr.
- `:custom`: use `custom_gtco2`, which must have one value for each year.
"""
function wildfire_co2_path(;
    scenario::Union{Symbol,String} = :medium,
    years = DEFAULT_MODEL_YEARS,
    start_year::Int = 2020,
    custom_gtco2::Union{Nothing,AbstractVector{<:Real}} = nothing,
)
    scenario = Symbol(scenario)
    years = collect(years)
    gtco2 = zeros(Float64, length(years))

    if scenario in (:none, :off, :baseline)
        # Leave the model unchanged.
    elseif scenario == :low
        gtco2 .= [year >= start_year ? 0.10 : 0.0 for year in years]
    elseif scenario == :medium
        gtco2 .= [year >= start_year ? 0.25 * 1.005^(year - start_year) : 0.0 for year in years]
    elseif scenario == :high
        gtco2 .= [year >= start_year ? min(0.50 * 1.01^(year - start_year), 5.0) : 0.0 for year in years]
    elseif scenario == :stress
        gtco2 .= [year >= start_year ? min(2.00 * 1.015^(year - start_year), 20.0) : 0.0 for year in years]
    elseif scenario == :custom
        custom_gtco2 === nothing && error("scenario=:custom requires custom_gtco2.")
        length(custom_gtco2) == length(years) ||
            error("custom_gtco2 must have one value for each year.")
        gtco2 .= Float64.(custom_gtco2)
    else
        error("Unknown wildfire_scenario $scenario.")
    end

    return DataFrame(
        year = years,
        wildfire_scenario = fill(string(scenario), length(years)),
        wildfire_gtco2 = gtco2,
        wildfire_gtc = gtco2 .* GTCO2_TO_GTC,
    )
end

function _triangular(rng::AbstractRNG, low::Real, mode::Real, high::Real)
    low = Float64(low)
    mode = Float64(mode)
    high = Float64(high)
    low <= mode <= high || error("Triangular parameters must satisfy low <= mode <= high.")
    u = rand(rng)
    c = (mode - low) / (high - low)
    if u < c
        return low + sqrt(u * (high - low) * (mode - low))
    else
        return high - sqrt((1 - u) * (high - low) * (high - mode))
    end
end

function _temperature_scaled_path(years, temperature_c, target_2050_gtco2, ratio_2100)
    start_year = 2020
    mid_year = 2050
    late_year = 2100

    start_index = findfirst(isequal(start_year), years)
    mid_index = findfirst(isequal(mid_year), years)
    late_index = findfirst(isequal(late_year), years)

    start_index === nothing && error("years must include $start_year.")
    mid_index === nothing && error("years must include $mid_year.")
    late_index === nothing && error("years must include $late_year.")

    t_start = temperature_c[start_index]
    t_mid = temperature_c[mid_index]
    t_late = temperature_c[late_index]

    target_2100_gtco2 = target_2050_gtco2 * ratio_2100
    pre_slope = target_2050_gtco2 / max(t_mid - t_start, eps(Float64))
    post_slope = (target_2100_gtco2 - target_2050_gtco2) / max(t_late - t_mid, eps(Float64))

    return [
        if year < start_year
            0.0
        elseif year <= mid_year
            max((temperature_c[i] - t_start) * pre_slope, 0.0)
        else
            max(target_2050_gtco2 + (temperature_c[i] - t_mid) * post_slope, 0.0)
        end
        for (i, year) in enumerate(years)
    ]
end

"""
    source_informed_wildfire_draws(; n, years, temperature_c, seed=20260502)

Generate source-informed wildfire CO2 pathway draws. Magnitudes are anchored on
the Byrne et al. 2024 Canada-2023 excess fire carbon estimate
(`647 - 121 = 526 TgC = 1.93 GtCO2/yr`). Post-2050 growth uses a triangular
draw bounded by the Val Martin et al. USDA projected fire-emissions and burned
area late-century/mid-century ratios. Net persistence and not-already-embedded
fractions are explicit uncertainty parameters to reduce double counting.
"""
function source_informed_wildfire_draws(;
    n::Int,
    years = DEFAULT_MODEL_YEARS,
    temperature_c::AbstractVector,
    seed::Int = 20260502,
)
    years = collect(years)
    length(temperature_c) == length(years) ||
        error("temperature_c must have one value for each year.")
    any(ismissing, temperature_c) &&
        error("temperature_c contains missing values.")
    temperature_c = Float64.(temperature_c)

    rng = MersenneTwister(seed)
    emissions_rows = DataFrame()
    parameter_rows = DataFrame(
        draw = Int[],
        canada_excess_gtco2 = Float64[],
        gross_target_fraction_2050 = Float64[],
        net_persistence_fraction = Float64[],
        not_embedded_fraction = Float64[],
        net_target_2050_gtco2 = Float64[],
        ratio_2100_to_2050 = Float64[],
        source_note = String[],
    )

    for draw in 1:n
        gross_target_fraction_2050 = _triangular(rng, 0.25, 1.00, 2.00)
        net_persistence_fraction = _triangular(rng, 0.25, 0.60, 1.00)
        not_embedded_fraction = _triangular(rng, 0.50, 0.80, 1.00)
        ratio_2100_to_2050 = _triangular(rng, 1.06, 1.20, 1.32)

        net_target_2050_gtco2 =
            CANADA_2023_EXCESS_GTCO2 *
            gross_target_fraction_2050 *
            net_persistence_fraction *
            not_embedded_fraction

        path_gtco2 = _temperature_scaled_path(
            years,
            temperature_c,
            net_target_2050_gtco2,
            ratio_2100_to_2050,
        )

        append!(
            emissions_rows,
            DataFrame(
                draw = fill(draw, length(years)),
                year = years,
                wildfire_gtco2 = path_gtco2,
                wildfire_gtc = path_gtco2 .* GTCO2_TO_GTC,
            ),
            cols = :union,
        )

        push!(
            parameter_rows,
            (
                draw,
                CANADA_2023_EXCESS_GTCO2,
                gross_target_fraction_2050,
                net_persistence_fraction,
                not_embedded_fraction,
                net_target_2050_gtco2,
                ratio_2100_to_2050,
                "Canada2023 excess magnitude; ValMartin2018 USDA late/mid-century fire scaling; explicit net/not-embedded fractions",
            ),
        )
    end

    return parameter_rows, emissions_rows
end

function _canada_2023_target_fraction(scenario::Symbol)
    if scenario in (:low, :canada2023_low, :boreal_low)
        return 0.25
    elseif scenario in (:medium, :canada2023_medium, :boreal_medium)
        return 0.50
    elseif scenario in (:high, :canada2023_high, :boreal_high)
        return 1.00
    elseif scenario in (:stress, :canada2023_stress, :boreal_stress)
        return 2.00
    else
        error("Unknown Canada-2023 wildfire scenario $scenario.")
    end
end

"""
    canada_2023_excess_wildfire_path(; scenario=:medium, years=1750:2300,
        start_year=2020, target_year=2050)

Construct a Canada-2023-calibrated added fire CO2 pathway.

The default target is the 2023 Canadian fire-carbon estimate from Byrne et al.
minus their cited 2010-2022 top-down Canadian average:

- 647 TgC in 2023
- 121 TgC/yr recent average
- excess = 526 TgC/yr = 0.526 GtC/yr = 1.93 GtCO2/yr

    Low/medium/high reach 25%, 50%, and 100% of that excess by 2050 and continue
increasing after 2050. If a baseline temperature path is provided, emissions are
scaled to warming above 2020, normalized so the selected target is reached at
2050. Without a temperature path, the function linearly extrapolates the
2020-2050 ramp. The default `net_persistence_fraction` and
`not_embedded_fraction` are 1.0 for this stress-style diagnostic; set them below
1.0 when interpreting the path as persistent net CO2 or as already partly
embedded in RFF-SP aggregate CO2.
"""
function canada_2023_excess_wildfire_path(;
    scenario::Union{Symbol,String} = :medium,
    years = DEFAULT_MODEL_YEARS,
    temperature_c::Union{Nothing,AbstractVector} = nothing,
    start_year::Int = 2020,
    target_year::Int = 2050,
    canada_2023_tgc::Real = 647.0,
    canada_recent_average_tgc::Real = 121.0,
    target_fraction::Union{Nothing,Real} = nothing,
    net_persistence_fraction::Real = 1.0,
    not_embedded_fraction::Real = 1.0,
)
    scenario = Symbol(scenario)
    years = collect(years)
    if !isnothing(temperature_c)
        length(temperature_c) == length(years) ||
            error("temperature_c must have one value for each year.")
        any(ismissing, temperature_c) &&
            error("temperature_c contains missing values; run the baseline model before constructing this path.")
        temperature_c = Float64.(temperature_c)
    end

    target_fraction =
        isnothing(target_fraction) ? _canada_2023_target_fraction(scenario) : Float64(target_fraction)

    excess_tgc = Float64(canada_2023_tgc - canada_recent_average_tgc)
    excess_gtc = excess_tgc / 1000.0
    excess_gtco2 = excess_gtc * GTC_TO_GTCO2
    target_gtco2 =
        excess_gtco2 *
        target_fraction *
        Float64(net_persistence_fraction) *
        Float64(not_embedded_fraction)

    ramp_denominator = max(target_year - start_year, 1)
    scale =
        if isnothing(temperature_c)
            [year < start_year ? 0.0 : (year - start_year) / ramp_denominator for year in years]
        else
            start_index = findfirst(isequal(start_year), years)
            target_index = findfirst(isequal(target_year), years)
            start_index === nothing && error("start_year $start_year is not in years.")
            target_index === nothing && error("target_year $target_year is not in years.")
            temp_delta_to_target = temperature_c[target_index] - temperature_c[start_index]
            abs(temp_delta_to_target) < eps(Float64) &&
                error("Temperature change between start_year and target_year is too small to scale the path.")
            [
                year < start_year ? 0.0 :
                max((temperature_c[i] - temperature_c[start_index]) / temp_delta_to_target, 0.0)
                for (i, year) in enumerate(years)
            ]
        end

    gtco2 = target_gtco2 .* scale

    return DataFrame(
        year = years,
        wildfire_scenario = fill("canada-2023-excess-$(scenario)", length(years)),
        temperature_scaled = fill(!isnothing(temperature_c), length(years)),
        temperature_c = isnothing(temperature_c) ? fill(missing, length(years)) : temperature_c,
        scaling_to_2050_target = scale,
        canada_2023_tgc = fill(Float64(canada_2023_tgc), length(years)),
        canada_recent_average_tgc = fill(Float64(canada_recent_average_tgc), length(years)),
        canada_excess_tgc = fill(excess_tgc, length(years)),
        canada_excess_gtco2 = fill(excess_gtco2, length(years)),
        target_fraction = fill(target_fraction, length(years)),
        target_year = fill(target_year, length(years)),
        net_persistence_fraction = fill(Float64(net_persistence_fraction), length(years)),
        not_embedded_fraction = fill(Float64(not_embedded_fraction), length(years)),
        wildfire_gtco2 = gtco2,
        wildfire_gtc = gtco2 .* GTCO2_TO_GTC,
    )
end

function _climate_response_assumptions(
    scenario::Symbol;
    sensitivity_per_c::Union{Nothing,Real},
    net_persistence_fraction::Union{Nothing,Real},
    not_embedded_fraction::Union{Nothing,Real},
)
    defaults =
        if scenario in (:low, :climate_low, :climate_fire_low)
            (sensitivity_per_c = 0.07, net_persistence_fraction = 0.05, not_embedded_fraction = 0.25)
        elseif scenario in (:medium, :climate_medium, :climate_fire_medium)
            (sensitivity_per_c = 0.10, net_persistence_fraction = 0.10, not_embedded_fraction = 0.50)
        elseif scenario in (:high, :climate_high, :climate_fire_high)
            (sensitivity_per_c = 0.15, net_persistence_fraction = 0.20, not_embedded_fraction = 0.75)
        elseif scenario in (:stress, :climate_stress, :climate_fire_stress)
            (sensitivity_per_c = 0.25, net_persistence_fraction = 0.35, not_embedded_fraction = 1.00)
        else
            error("Unknown climate-response wildfire scenario $scenario.")
        end

    return (
        sensitivity_per_c = isnothing(sensitivity_per_c) ? defaults.sensitivity_per_c : Float64(sensitivity_per_c),
        net_persistence_fraction = isnothing(net_persistence_fraction) ? defaults.net_persistence_fraction : Float64(net_persistence_fraction),
        not_embedded_fraction = isnothing(not_embedded_fraction) ? defaults.not_embedded_fraction : Float64(not_embedded_fraction),
    )
end

"""
    climate_response_wildfire_path(; scenario=:medium, years, temperature_c,
        start_year=2020, reference_temperature_year=2020,
        gross_reference_fire_carbon_pgc=2.2)

Build a transparent first-pass climate-response wildfire CO2 path.

The calculation starts from a gross reference global fire carbon flux and applies:

1. a fractional gross fire-emissions response per degree C of warming above the
   reference year,
2. a net-persistence fraction, because much gross biomass-burning carbon can be
   reabsorbed through regrowth, and
3. a not-embedded fraction, because RFF-SP aggregate CO2 already includes broad
   AFOLU / natural-stock expert judgments.

The returned `wildfire_gtco2` is therefore intended to be a net additional,
not-already-embedded residual, not total gross biomass-burning CO2.
"""
function climate_response_wildfire_path(;
    scenario::Union{Symbol,String} = :medium,
    years = DEFAULT_MODEL_YEARS,
    temperature_c::AbstractVector,
    start_year::Int = 2020,
    reference_temperature_year::Int = 2020,
    gross_reference_fire_carbon_pgc::Real = 2.2,
    sensitivity_per_c::Union{Nothing,Real} = nothing,
    net_persistence_fraction::Union{Nothing,Real} = nothing,
    not_embedded_fraction::Union{Nothing,Real} = nothing,
)
    scenario = Symbol(scenario)
    years = collect(years)
    length(temperature_c) == length(years) ||
        error("temperature_c must have one value for each year.")
    any(ismissing, temperature_c) &&
        error("temperature_c contains missing values; run the baseline model before constructing a climate-response path.")
    temperature_c = Float64.(temperature_c)

    assumptions = _climate_response_assumptions(
        scenario;
        sensitivity_per_c = sensitivity_per_c,
        net_persistence_fraction = net_persistence_fraction,
        not_embedded_fraction = not_embedded_fraction,
    )

    reference_index = findfirst(isequal(reference_temperature_year), years)
    reference_index === nothing &&
        error("reference_temperature_year $reference_temperature_year is not in years.")

    gross_reference_fire_gtco2 = Float64(gross_reference_fire_carbon_pgc) * GTC_TO_GTCO2
    reference_temperature_c = Float64(temperature_c[reference_index])

    warming_above_reference = [
        year >= start_year ? max(Float64(temp) - reference_temperature_c, 0.0) : 0.0
        for (year, temp) in zip(years, temperature_c)
    ]
    gross_increment_gtco2 =
        gross_reference_fire_gtco2 .* assumptions.sensitivity_per_c .* warming_above_reference
    gtco2 =
        gross_increment_gtco2 .*
        assumptions.net_persistence_fraction .*
        assumptions.not_embedded_fraction

    return DataFrame(
        year = years,
        wildfire_scenario = fill("climate-response-$(scenario)", length(years)),
        temperature_c = Float64.(temperature_c),
        reference_temperature_year = fill(reference_temperature_year, length(years)),
        reference_temperature_c = fill(reference_temperature_c, length(years)),
        warming_above_reference_c = warming_above_reference,
        gross_reference_fire_pgc = fill(Float64(gross_reference_fire_carbon_pgc), length(years)),
        gross_reference_fire_gtco2 = fill(gross_reference_fire_gtco2, length(years)),
        sensitivity_per_c = fill(assumptions.sensitivity_per_c, length(years)),
        gross_increment_gtco2 = gross_increment_gtco2,
        net_persistence_fraction = fill(assumptions.net_persistence_fraction, length(years)),
        not_embedded_fraction = fill(assumptions.not_embedded_fraction, length(years)),
        wildfire_gtco2 = gtco2,
        wildfire_gtc = gtco2 .* GTCO2_TO_GTC,
    )
end

function write_wildfire_path(path::DataFrame, filename::AbstractString)
    mkpath(dirname(filename))
    path |> save(filename)
    return filename
end

function _repo_root()
    return normpath(joinpath(@__DIR__, ".."))
end

function _ar6_total_co2_emissions_gtc(ar6_scenario::String, years)
    path = joinpath(
        _repo_root(),
        "packages",
        "MimiGIVE",
        "data",
        "FAIR_ar6",
        "AR6_emissions_$(ar6_scenario)_1750_2300.csv",
    )
    isfile(path) || error("Could not find AR6 emissions file: $path")

    df = DataFrame(load(path))
    rows = indexin(collect(years), df.Year)
    any(isnothing, rows) && error("AR6 emissions file does not cover all model years.")
    rows = Int.(rows)

    return df.FossilCO2[rows] .+ df.OtherCO2[rows]
end

"""
    apply_wildfire_co2!(m; include_wildfire_co2=true, wildfire_scenario=:medium,
        start_year=2020, custom_gtco2=nothing, ar6_scenario="ssp245")

Insert the wildfire emissions path into GIVE's annual CO2 emissions stream before
the existing `:co2_emissions_identity` component. This placement is deliberate:
`MimiGIVE.add_marginal_emissions!` later adds the SCC pulse after that identity
component, so both the base and marginal models inherit the same wildfire-adjusted
baseline and the marginal ton is not contaminated by the wildfire scenario itself.

Units entering FAIR are GtC/yr. Scenario inputs are documented in GtCO2/yr and
converted with 12/44.
"""
function apply_wildfire_co2!(
    m::Mimi.Model;
    include_wildfire_co2::Bool = true,
    wildfire_scenario::Union{Symbol,String} = :medium,
    start_year::Int = 2020,
    custom_gtco2::Union{Nothing,AbstractVector{<:Real}} = nothing,
    ar6_scenario::String = "ssp245",
)
    time = collect(Mimi.dim_keys(m, :time))
    path = wildfire_co2_path(
        scenario = include_wildfire_co2 ? wildfire_scenario : :baseline,
        years = time,
        start_year = start_year,
        custom_gtco2 = custom_gtco2,
    )

    if !include_wildfire_co2
        return path
    end

    Mimi.add_comp!(m, Mimi.adder, :wildfire_co2_emissions, before = :co2_emissions_identity)
    Mimi.set_param!(m, :wildfire_co2_emissions, :add, :wildfire_co2_emissions_add, path.wildfire_gtc)

    # Preserve the original historical/backup behavior used in MimiGIVE.main_model:
    # before the socioeconomic component begins in 2020, FAIR receives the AR6
    # FossilCO2 + OtherCO2 stream; from 2020 onward it receives RFF-SP/SSP CO2.
    ar6_total_co2 = _ar6_total_co2_emissions_gtc(ar6_scenario, time)
    Mimi.connect_param!(
        m,
        :wildfire_co2_emissions => :input,
        :Socioeconomic => :co2_emissions,
        ar6_total_co2,
    )
    Mimi.connect_param!(
        m,
        :co2_emissions_identity => :input_co2,
        :wildfire_co2_emissions => :output,
    )

    return path
end

"""
    apply_wildfire_temperature_feedback_co2!(m; ...)

Add a temperature-dependent wildfire CO2 feedback to GIVE's annual CO2 emissions
stream before `:co2_emissions_identity`. Because the component reads lagged
temperature, the marginal SCC model can generate extra wildfire CO2 after the
CO2 pulse warms the model. This is the SCC-relevant feedback test, unlike a
fixed exogenous wildfire path that is identical in the base and pulse runs.
"""
function apply_wildfire_temperature_feedback_co2!(
    m::Mimi.Model;
    start_year::Int = 2020,
    reference_temperature_year::Int = 2020,
    gross_reference_fire_carbon_pgc::Real = 2.2,
    sensitivity_per_c::Real = 0.10,
    net_persistence_fraction::Real = 0.10,
    not_embedded_fraction::Real = 0.50,
    max_feedback_gtco2::Real = 100.0,
    ar6_scenario::String = "ssp245",
)
    time = collect(Mimi.dim_keys(m, :time))
    ar6_total_co2 = _ar6_total_co2_emissions_gtc(ar6_scenario, time)

    Mimi.add_comp!(
        m,
        wildfire_temperature_feedback_co2,
        :wildfire_temperature_feedback_co2,
        before = :co2_emissions_identity,
    )
    Mimi.set_param!(m, :wildfire_temperature_feedback_co2, :start_year, Float64(start_year))
    Mimi.set_param!(m, :wildfire_temperature_feedback_co2, :reference_temperature_year, reference_temperature_year)
    Mimi.set_param!(m, :wildfire_temperature_feedback_co2, :reference_fire_gtc, Float64(gross_reference_fire_carbon_pgc))
    Mimi.set_param!(m, :wildfire_temperature_feedback_co2, :sensitivity_per_c, Float64(sensitivity_per_c))
    Mimi.set_param!(m, :wildfire_temperature_feedback_co2, :net_persistence_fraction, Float64(net_persistence_fraction))
    Mimi.set_param!(m, :wildfire_temperature_feedback_co2, :not_embedded_fraction, Float64(not_embedded_fraction))
    Mimi.set_param!(m, :wildfire_temperature_feedback_co2, :max_feedback_gtc, Float64(max_feedback_gtco2) * GTCO2_TO_GTC)

    Mimi.connect_param!(
        m,
        :wildfire_temperature_feedback_co2 => :baseline_co2,
        :Socioeconomic => :co2_emissions,
        ar6_total_co2,
    )
    Mimi.connect_param!(
        m,
        :wildfire_temperature_feedback_co2 => :temperature,
        :temperature => :T,
    )
    Mimi.connect_param!(
        m,
        :co2_emissions_identity => :input_co2,
        :wildfire_temperature_feedback_co2 => :output_co2,
    )

    return DataFrame(
        year = time,
        reference_temperature_year = fill(reference_temperature_year, length(time)),
        gross_reference_fire_gtco2 = fill(Float64(gross_reference_fire_carbon_pgc) * GTC_TO_GTCO2, length(time)),
        sensitivity_per_c = fill(Float64(sensitivity_per_c), length(time)),
        net_persistence_fraction = fill(Float64(net_persistence_fraction), length(time)),
        not_embedded_fraction = fill(Float64(not_embedded_fraction), length(time)),
        max_feedback_gtco2 = fill(Float64(max_feedback_gtco2), length(time)),
    )
end

"""
    get_model(; include_wildfire_co2=false, wildfire_scenario=:medium, kwargs...)

Build the ordinary MimiGIVE model and optionally add the wildfire CO2 extension.
All unrecognized keyword arguments are passed to `MimiGIVE.get_model`.
"""
function get_model(;
    include_wildfire_co2::Bool = false,
    wildfire_scenario::Union{Symbol,String} = :medium,
    start_year::Int = 2020,
    custom_gtco2::Union{Nothing,AbstractVector{<:Real}} = nothing,
    socioeconomics_source::Symbol = :RFF,
    SSP_scenario::Union{Nothing,String} = nothing,
    kwargs...,
)
    m = MimiGIVE.get_model(;
        socioeconomics_source = socioeconomics_source,
        SSP_scenario = SSP_scenario,
        kwargs...,
    )

    ar6_scenario =
        socioeconomics_source == :RFF ? "ssp245" :
        socioeconomics_source == :SSP ? lowercase(SSP_scenario) :
        error("Unsupported socioeconomics_source: $socioeconomics_source")

    path = apply_wildfire_co2!(
        m,
        include_wildfire_co2 = include_wildfire_co2,
        wildfire_scenario = wildfire_scenario,
        start_year = start_year,
        custom_gtco2 = custom_gtco2,
        ar6_scenario = ar6_scenario,
    )

    return m, path
end

end
