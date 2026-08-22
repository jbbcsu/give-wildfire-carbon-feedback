using Test
using BiodiversityNonuse

@testset "species stock" begin
    @test next_biodiversity(1.0, 0.0; theta=0.001, phi=0.0) == 0.999
    @test next_biodiversity(1.0, 2.0; theta=0.001, phi=0.01) < 0.999
    @test no_climate_biodiversity(1.0, 2; theta=0.001) ≈ 0.999^2
    @test climate_deficit(0.9, 0.8) ≈ 0.1
    @test climate_deficit(0.8, 0.9) == 0
end

@testset "nonuse valuation" begin
    @test per_capita_wtp(100.0, 0.8, 0.0; beta=2.0) == 0
    @test per_capita_wtp(100.0, 0.8, 0.1; beta=2.0) > 0
    @test per_capita_wtp(100.0, 0.8, 0.1; beta=0.0) == 0
    @test country_damage(10.0, 100.0, 0.8, 0.1; beta=2.0) ≈
          10 * per_capita_wtp(100.0, 0.8, 0.1; beta=2.0)
end

@testset "domain checks" begin
    @test_throws DomainError next_biodiversity(1.0, 10.0; theta=0.1, phi=0.1)
    @test_throws DomainError per_capita_wtp(100.0, 0.0, 0.1; beta=1.0)
    @test_throws DomainError country_damage(-1.0, 100.0, 0.8, 0.1; beta=1.0)
end
