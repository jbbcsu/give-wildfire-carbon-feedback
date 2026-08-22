using Test
using Mimi

include(joinpath(@__DIR__, "..", "src", "PrecipitationDamages.jl"))
include(joinpath(@__DIR__, "..", "src", "AdaptationScenarios.jl"))
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

@testset "JointAgriculture replacement contract" begin
    m = Model()
    set_dimension!(m, :time, [2020])
    set_dimension!(m, :fund_regions, ["USA"])
    add_comp!(m, JointAgriculture)
    update_param!(m, :JointAgriculture, :income, reshape([100.0], 1, 1))
    update_param!(m, :JointAgriculture, :population, reshape([10.0], 1, 1))
    update_param!(m, :JointAgriculture, :gdp90, [80.0])
    update_param!(m, :JointAgriculture, :pop90, [8.0])
    update_param!(m, :JointAgriculture, :agrish0, [0.1])
    update_param!(m, :JointAgriculture, :temp_anomaly, reshape([1.0], 1, 1))
    update_param!(m, :JointAgriculture, :seasonal_precip_anomaly, reshape([2.0], 1, 1))
    update_param!(m, :JointAgriculture, :dry_spell_anomaly, reshape([3.0], 1, 1))
    update_param!(m, :JointAgriculture, :wet_extreme_anomaly, reshape([4.0], 1, 1))
    update_param!(m, :JointAgriculture, :beta_temp, [0.01])
    update_param!(m, :JointAgriculture, :beta_precip, [0.02])
    update_param!(m, :JointAgriculture, :beta_dry_spell, [0.03])
    update_param!(m, :JointAgriculture, :beta_wet_extreme, [0.04])
    update_param!(m, :JointAgriculture, :beta_temp_precip, [0.05])
    update_param!(m, :JointAgriculture, :adaptation_loss_multiplier, reshape([0.5], 1, 1))
    update_param!(m, :JointAgriculture, :adaptation_cost_share, reshape([0.01], 1, 1))
    run(m)
    @test m[:JointAgriculture, :raw_climate_loss_fraction][1, 1] ≈ 0.4
    @test m[:JointAgriculture, :climate_loss_fraction][1, 1] ≈ 0.21
    @test m[:JointAgriculture, :agcost][1, 1] ≈ 2.1
end

@testset "Adaptation scenarios" begin
    years = [2020, 2030]
    @test AdaptationScenarios.adaptation_multiplier(years, 2; scenario=:fixed) == ones(2, 2)
    @test AdaptationScenarios.adaptation_multiplier(years, 2; scenario=:trend)[1, 1] == 1
    @test AdaptationScenarios.adaptation_multiplier(years, 2; scenario=:trend)[2, 1] < 1
    @test AdaptationScenarios.adaptation_multiplier(years, 1; scenario=:upper)[2, 1] <
          AdaptationScenarios.adaptation_multiplier(years, 1; scenario=:trend)[2, 1]
    @test AdaptationScenarios.adaptation_cost_share(years, 2) == zeros(2, 2)
end
