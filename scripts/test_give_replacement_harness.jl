#!/usr/bin/env julia

"""
Executed zero-response integration test for the joint agriculture replacement
against an unmodified MimiGIVE model. The supplied response arrays and
agricultural shares are synthetic control inputs. This script runs one ordinary
GIVE path only to verify component execution and agriculture-damage aggregation;
it does not run a marginal pulse, discount a damage difference, or report an SCC.

Run with the GIVE repository root as the first argument while activating that
repository's Julia project.
"""

length(ARGS) == 1 || error("usage: test_give_replacement_harness.jl GIVE_REPOSITORY_ROOT")

give_root = abspath(only(ARGS))
isfile(joinpath(give_root, "packages", "MimiGIVE", "Project.toml")) ||
    error("argument is not a compatible GIVE repository root")
dirname(Base.active_project()) == give_root ||
    error("activate the GIVE repository project passed as the argument")

using Mimi
using MimiGIVE
using Test

project_root = normpath(joinpath(@__DIR__, ".."))
include(joinpath(project_root, "src", "CropResponseAggregation.jl"))
include(joinpath(project_root, "src", "JointAgriculture.jl"))
include(joinpath(project_root, "src", "AgricultureReplacementAudit.jl"))
include(joinpath(project_root, "src", "AgricultureReplacementHarness.jl"))

crops = [
    "maize",
    "rice_first",
    "rice_second",
    "soybean",
    "wheat_spring",
    "wheat_winter",
]
model = MimiGIVE.get_model()
n_regions = Mimi.dim_count(model, :fund_regions)
n_times = Mimi.dim_count(model, :time)
n_crops = length(crops)

AgricultureReplacementHarness.install_joint_agriculture_replacement!(
    model,
    CropResponseAggregation,
    JointAgriculture;
    crops=crops,
    agrish0=fill(0.1, n_regions),
)
AgricultureReplacementAudit.audit_agriculture_replacement(model)

zero_features = zeros(n_times, n_regions, n_crops)
for parameter in (
    :mean_temp_anomaly,
    :seasonal_precip_anomaly,
    :precip_timing_anomaly,
    :water_stress_anomaly,
    :wet_extreme_anomaly,
    :heat_extreme_anomaly,
)
    update_param!(model, :CropResponseAggregation, parameter, zero_features)
end
for parameter in (
    :beta_temp,
    :beta_precip,
    :beta_timing,
    :beta_water_stress,
    :beta_wet_extreme,
    :beta_heat_extreme,
    :beta_temp_precip,
)
    update_param!(model, :CropResponseAggregation, parameter, zeros(n_regions, n_crops))
end
update_param!(
    model,
    :CropResponseAggregation,
    :crop_value_share,
    fill(1 / n_crops, n_regions, n_crops),
)
update_param!(
    model,
    :CropResponseAggregation,
    :adaptation_loss_multiplier,
    ones(n_times, n_regions, n_crops),
)
update_param!(
    model,
    :CropResponseAggregation,
    :adaptation_cost_share,
    zero_features,
)

Mimi.build!(model)
run(model)

years = collect(Mimi.dim_keys(model, :time))
active_indices = findall(year -> year >= 2020, years)
@test first(years[active_indices]) == 2020
@test last(years[active_indices]) == 2300

function require_complete_constant(values, expected)
    active = values[active_indices, ntuple(_ -> Colon(), ndims(values) - 1)...]
    @test !any(ismissing, active)
    @test all(
        value -> isapprox(value, expected; atol=1e-12, rtol=0.0),
        skipmissing(vec(active)),
    )
end

for variable in (
    :crop_raw_loss_fraction,
    :crop_adjusted_loss_fraction,
    :regional_loss_fraction,
)
    require_complete_constant(
        Array(model[:CropResponseAggregation, variable]),
        0.0,
    )
end
require_complete_constant(
    Array(model[:CropResponseAggregation, :coverage_share]),
    1.0,
)
for variable in (:raw_climate_loss_fraction, :climate_loss_fraction, :agcost)
    require_complete_constant(Array(model[:JointAgriculture, variable]), 0.0)
end
require_complete_constant(
    Array(model[:DamageAggregator, :agriculture_damage]),
    0.0,
)

println("full GIVE replacement synthetic zero-response execution passed")
