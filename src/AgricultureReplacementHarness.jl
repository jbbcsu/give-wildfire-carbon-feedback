"""
Install the isolated joint agriculture components into a MimiGIVE-style model.

This module changes model topology and supplies only the legacy agricultural-
value baseline parameters. It does not load a response bundle, run a marginal
emissions experiment, discount damages, or calculate an SCC.
"""
module AgricultureReplacementHarness

using Mimi

export AgricultureInstallationAudit, install_joint_agriculture_replacement!

struct AgricultureInstallationAudit
    passed::Bool
    crops::Vector{String}
    first_year::Int
    retained_sector_flags::NamedTuple
end

_component_names(model::Mimi.Model) =
    Set(nameof(component) for component in Mimi.compdefs(model))

function _require_components(names, required)
    missing = sort!(collect(setdiff(Set(required), names)))
    isempty(missing) ||
        error("model is missing required component(s): $(join(string.(missing), ", "))")
end

function _set_or_check_crop_dimension!(model::Mimi.Model, crops::Vector{String})
    existing = try
        String.(Mimi.dim_keys(model, :crops))
    catch error_value
        error_value isa KeyError || rethrow()
        nothing
    end
    if existing === nothing
        set_dimension!(model, :crops, crops)
    elseif existing != crops
        error("existing crops dimension does not match the declared ordered crops")
    end
end

function _validate_region_vector(model, name::String, values; strictly_positive::Bool)
    values isa AbstractVector || error("$(name) must be a vector")
    length(values) == Mimi.dim_count(model, :fund_regions) ||
        error("$(name) length must match fund_regions")
    predicate = strictly_positive ?
        value -> value isa Real && isfinite(value) && value > 0 :
        value -> value isa Real && isfinite(value) && value >= 0
    all(predicate, values) ||
        error("$(name) must contain finite $(strictly_positive ? "positive" : "nonnegative") values")
end

function _connect_or_set_baseline!(
    model::Mimi.Model,
    parameter::Symbol,
    source_component::Symbol,
    explicit_value,
)
    if source_component in _component_names(model)
        explicit_value === nothing ||
            error("$(parameter) must not be supplied twice")
        connect_param!(model, :JointAgriculture => parameter, source_component => :output)
    else
        explicit_value === nothing &&
            error("$(parameter) requires either $(source_component).output or an explicit value")
        update_param!(model, :JointAgriculture, parameter, explicit_value)
    end
end

"""
    install_joint_agriculture_replacement!(model, response_component,
                                            agriculture_component; ...)

Delete the legacy component named `Agriculture`, add components named
`CropResponseAggregation` and `JointAgriculture`, reconnect the existing GIVE
regional socioeconomic aggregators, and connect `JointAgriculture.agcost` once
to `DamageAggregator.damage_ag`.

`agrish0` is required and explicit because it defines the baseline agricultural
value pool. RFF-style models normally provide `gdp90` and `pop90` through their
existing no-time aggregators; SSP-style models must pass those arrays explicitly.
The caller remains responsible for validating and loading every crop-response
parameter after installation.
"""
function install_joint_agriculture_replacement!(
    model::Mimi.Model,
    response_component,
    agriculture_component;
    crops,
    agrish0,
    first_year::Integer=2020,
    gdp90=nothing,
    pop90=nothing,
    agel::Real=0.31,
    before_component::Symbol=:energy_damages,
)
    crop_names = String.(collect(crops))
    isempty(crop_names) && error("crops must be a nonempty ordered vector")
    length(unique(crop_names)) == length(crop_names) || error("crops must be unique")
    all(crop -> !isempty(strip(crop)), crop_names) || error("crop names must be nonblank")
    isfinite(agel) && agel >= 0 || error("agel must be finite and nonnegative")
    Int(first_year) in Mimi.dim_keys(model, :time) ||
        error("first_year must be a modeled year")
    _validate_region_vector(model, "agrish0", agrish0; strictly_positive=false)

    names = _component_names(model)
    _require_components(
        names,
        (
            :Agriculture,
            :Agriculture_aggregator_population,
            :Agriculture_aggregator_gdp,
            :DamageAggregator,
            before_component,
        ),
    )
    isempty(intersect(names, Set((:CropResponseAggregation, :JointAgriculture)))) ||
        error("joint agriculture components are already installed")

    for (parameter, source_component, explicit_value) in (
        (:pop90, :Agriculture_aggregator_pop90, pop90),
        (:gdp90, :Agriculture_aggregator_gdp90, gdp90),
    )
        if source_component in names
            explicit_value === nothing || error("$(parameter) must not be supplied twice")
        else
            explicit_value === nothing &&
                error("$(parameter) requires either $(source_component).output or an explicit value")
            _validate_region_vector(
                model, string(parameter), explicit_value; strictly_positive=true)
        end
    end

    _set_or_check_crop_dimension!(model, crop_names)

    # Deep deletion also removes unshared MooreAg-only model parameters such as
    # GTAP coefficients and temperature-damage bounds. Shared socioeconomic
    # aggregators and other damage sectors remain untouched.
    delete!(model, :Agriculture; deep=true)
    add_comp!(
        model,
        response_component,
        :CropResponseAggregation;
        first=Int(first_year),
        before=before_component,
    )
    add_comp!(
        model,
        agriculture_component,
        :JointAgriculture;
        first=Int(first_year),
        before=before_component,
    )

    connect_param!(
        model,
        :JointAgriculture => :joint_loss_fraction,
        :CropResponseAggregation => :regional_loss_fraction,
    )
    connect_param!(
        model,
        :JointAgriculture => :population,
        :Agriculture_aggregator_population => :output,
    )
    connect_param!(
        model,
        :JointAgriculture => :income,
        :Agriculture_aggregator_gdp => :output,
    )
    _connect_or_set_baseline!(
        model, :pop90, :Agriculture_aggregator_pop90, pop90)
    _connect_or_set_baseline!(
        model, :gdp90, :Agriculture_aggregator_gdp90, gdp90)

    update_param!(model, :JointAgriculture, :agrish0, agrish0)
    update_param!(model, :JointAgriculture, :agel, Float64(agel))
    connect_param!(
        model,
        :DamageAggregator => :damage_ag,
        :JointAgriculture => :agcost,
    )

    # Preserve the declared GIVE sector boundary explicitly: agriculture,
    # Cromar mortality, energy, and CIAM remain enabled, while DICE and
    # Howard--Sterner aggregate damages remain disabled.
    retained_flags = (
        include_ag=true,
        include_cromar_mortality=true,
        include_energy=true,
        include_slr=true,
        include_dice2016R2=false,
        include_hs_damage=false,
    )
    for (parameter, value) in pairs(retained_flags)
        update_param!(model, :DamageAggregator, parameter, value)
    end

    return AgricultureInstallationAudit(
        true,
        crop_names,
        Int(first_year),
        retained_flags,
    )
end

end
