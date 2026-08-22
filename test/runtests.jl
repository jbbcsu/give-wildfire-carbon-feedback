using Test
using Mimi

include(joinpath(@__DIR__, "..", "src", "PrecipitationDamages.jl"))
include(joinpath(@__DIR__, "..", "src", "AdaptationScenarios.jl"))
include(joinpath(@__DIR__, "..", "src", "CropResponseAggregation.jl"))
include(joinpath(@__DIR__, "..", "src", "JointAgriculture.jl"))

@testset "PrecipitationDamages contract" begin
    m = Model()
    set_dimension!(m, :time, [2020])
    set_dimension!(m, :country, ["AAA"])
    add_comp!(m, PrecipitationDamages)
    update_param!(m, :PrecipitationDamages, :mean_precip_anomaly, reshape([2.0], 1, 1))
    update_param!(m, :PrecipitationDamages, :heavy_precip_anomaly, reshape([3.0], 1, 1))
    update_param!(m, :PrecipitationDamages, :exposure, reshape([10.0], 1, 1))
    update_param!(m, :PrecipitationDamages, :beta_mean, [4.0])
    update_param!(m, :PrecipitationDamages, :beta_heavy, [5.0])
    update_param!(m, :PrecipitationDamages, :adaptation_multiplier, reshape([0.5], 1, 1))
    run(m)
    @test m[:PrecipitationDamages, :damages][1, 1] == 115.0
end

function set_crop_response_inputs!(m; weights=reshape([0.25, 0.75], 1, 2), require_full=true)
    zeros3 = zeros(1, 1, 2)
    zeros2 = zeros(1, 2)
    update_param!(m, :CropResponseAggregation, :mean_temp_anomaly, zeros3)
    update_param!(m, :CropResponseAggregation, :seasonal_precip_anomaly, reshape([2.0, 0.0], 1, 1, 2))
    update_param!(m, :CropResponseAggregation, :precip_timing_anomaly, zeros3)
    update_param!(m, :CropResponseAggregation, :water_stress_anomaly, zeros3)
    update_param!(m, :CropResponseAggregation, :wet_extreme_anomaly, zeros3)
    update_param!(m, :CropResponseAggregation, :heat_extreme_anomaly, reshape([0.0, 4.0], 1, 1, 2))
    update_param!(m, :CropResponseAggregation, :beta_temp, zeros2)
    update_param!(m, :CropResponseAggregation, :beta_precip, reshape([0.1, 0.0], 1, 2))
    update_param!(m, :CropResponseAggregation, :beta_timing, zeros2)
    update_param!(m, :CropResponseAggregation, :beta_water_stress, zeros2)
    update_param!(m, :CropResponseAggregation, :beta_wet_extreme, zeros2)
    update_param!(m, :CropResponseAggregation, :beta_heat_extreme, reshape([0.0, 0.05], 1, 2))
    update_param!(m, :CropResponseAggregation, :beta_temp_precip, zeros2)
    update_param!(m, :CropResponseAggregation, :crop_value_share, weights)
    update_param!(m, :CropResponseAggregation, :require_full_coverage, require_full)
    update_param!(m, :CropResponseAggregation, :adaptation_loss_multiplier, reshape([0.5, 1.0], 1, 1, 2))
    update_param!(m, :CropResponseAggregation, :adaptation_cost_share, reshape([0.01, 0.0], 1, 1, 2))
end

@testset "Crop-specific response and replacement contract" begin
    m = Model()
    set_dimension!(m, :time, [2020])
    set_dimension!(m, :fund_regions, ["USA"])
    set_dimension!(m, :crops, ["maize", "wheat"])
    add_comp!(m, CropResponseAggregation)
    add_comp!(m, JointAgriculture, after=:CropResponseAggregation)
    set_crop_response_inputs!(m)
    update_param!(m, :JointAgriculture, :income, reshape([100.0], 1, 1))
    update_param!(m, :JointAgriculture, :population, reshape([10.0], 1, 1))
    update_param!(m, :JointAgriculture, :gdp90, [80.0])
    update_param!(m, :JointAgriculture, :pop90, [8.0])
    update_param!(m, :JointAgriculture, :agrish0, [0.1])
    connect_param!(m, :JointAgriculture => :joint_loss_fraction,
                   :CropResponseAggregation => :regional_loss_fraction)
    run(m)
    @test m[:CropResponseAggregation, :crop_raw_loss_fraction][1, 1, :] ≈ [0.2, 0.2]
    @test m[:CropResponseAggregation, :crop_adjusted_loss_fraction][1, 1, :] ≈ [0.11, 0.2]
    @test m[:CropResponseAggregation, :coverage_share][1, 1] ≈ 1.0
    @test m[:JointAgriculture, :raw_climate_loss_fraction][1, 1] ≈ 0.1775
    @test m[:JointAgriculture, :agcost][1, 1] ≈ 1.775
end

@testset "Crop coverage gates" begin
    m = Model()
    set_dimension!(m, :time, [2020])
    set_dimension!(m, :fund_regions, ["USA"])
    set_dimension!(m, :crops, ["maize", "wheat"])
    add_comp!(m, CropResponseAggregation)
    set_crop_response_inputs!(m; weights=reshape([0.25, 0.50], 1, 2))
    @test_throws ErrorException run(m)

    m_partial = Model()
    set_dimension!(m_partial, :time, [2020])
    set_dimension!(m_partial, :fund_regions, ["USA"])
    set_dimension!(m_partial, :crops, ["maize", "wheat"])
    add_comp!(m_partial, CropResponseAggregation)
    set_crop_response_inputs!(m_partial; weights=reshape([0.25, 0.50], 1, 2), require_full=false)
    run(m_partial)
    @test m_partial[:CropResponseAggregation, :coverage_share][1, 1] ≈ 0.75
    @test m_partial[:CropResponseAggregation, :regional_loss_fraction][1, 1] ≈ 0.1275
end

@testset "Crop zero-feature conservation" begin
    m = Model()
    set_dimension!(m, :time, [2020])
    set_dimension!(m, :fund_regions, ["USA"])
    set_dimension!(m, :crops, ["maize", "wheat"])
    add_comp!(m, CropResponseAggregation)
    set_crop_response_inputs!(m)
    for feature in (:mean_temp_anomaly, :seasonal_precip_anomaly, :precip_timing_anomaly,
                    :water_stress_anomaly, :wet_extreme_anomaly, :heat_extreme_anomaly)
        update_param!(m, :CropResponseAggregation, feature, zeros(1, 1, 2))
    end
    update_param!(m, :CropResponseAggregation, :adaptation_cost_share, zeros(1, 1, 2))
    run(m)
    @test m[:CropResponseAggregation, :regional_loss_fraction][1, 1] == 0.0
end

@testset "Adaptation scenarios" begin
    years = [2020, 2030]
    @test AdaptationScenarios.adaptation_multiplier(years, 2; scenario=:fixed) == ones(2, 2)
    @test AdaptationScenarios.adaptation_multiplier(years, 2; scenario=:trend)[1, 1] == 1
    @test AdaptationScenarios.adaptation_multiplier(years, 2; scenario=:trend)[2, 1] < 1
    @test AdaptationScenarios.adaptation_multiplier(years, 1; scenario=:upper)[2, 1] <
          AdaptationScenarios.adaptation_multiplier(years, 1; scenario=:trend)[2, 1]
    @test AdaptationScenarios.adaptation_cost_share(years, 2) == zeros(2, 2)
    crop_schedule = AdaptationScenarios.adaptation_multiplier(years, 2, 3; scenario=:trend)
    @test size(crop_schedule) == (2, 2, 3)
    @test crop_schedule[:, :, 1] == crop_schedule[:, :, 3]
    @test AdaptationScenarios.adaptation_cost_share(years, 2, 3) == zeros(2, 2, 3)
end
