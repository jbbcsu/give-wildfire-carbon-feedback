using Test
using Mimi

include(joinpath(@__DIR__, "..", "src", "PrecipitationDamages.jl"))
include(joinpath(@__DIR__, "..", "src", "AdaptationScenarios.jl"))

@testset "PrecipitationDamages contract" begin
    m = Model()
    set_dimension!(m, :time, [2020])
    set_dimension!(m, :country, ["AAA"])
    add_comp!(m, PrecipitationDamages)
    update_param!(m, :mean_precip_anomaly, reshape([2.0], 1, 1))
    update_param!(m, :heavy_precip_anomaly, reshape([3.0], 1, 1))
    update_param!(m, :exposure, reshape([10.0], 1, 1))
    update_param!(m, :beta_mean, [4.0])
    update_param!(m, :beta_heavy, [5.0])
    update_param!(m, :adaptation_multiplier, reshape([0.5], 1, 1))
    run(m)
    @test m[:PrecipitationDamages, :damages][1, 1] == 115.0
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
