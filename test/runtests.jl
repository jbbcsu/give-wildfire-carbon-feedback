using Test
using Mimi

include(joinpath(@__DIR__, "..", "src", "PrecipitationDamages.jl"))
include(joinpath(@__DIR__, "..", "src", "AdaptationScenarios.jl"))
include(joinpath(@__DIR__, "..", "src", "CropResponseAggregation.jl"))
include(joinpath(@__DIR__, "..", "src", "JointAgriculture.jl"))
include(joinpath(@__DIR__, "..", "src", "AgricultureReplacementAudit.jl"))
include(joinpath(@__DIR__, "..", "src", "PairedAgricultureAudit.jl"))

@defcomp GraphDamageAggregator begin
    fund_regions = Index()
    damage_ag = Parameter(index=[time, fund_regions])
    observed_damage_ag = Variable(index=[time, fund_regions])

    function run_timestep(p, v, d, t)
        for r in d.fund_regions
            v.observed_damage_ag[t, r] = p.damage_ag[t, r]
        end
    end
end

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

@testset "Agriculture replacement component graph" begin
    m = Model()
    set_dimension!(m, :time, [2020])
    set_dimension!(m, :fund_regions, ["USA"])
    add_comp!(m, JointAgriculture)
    add_comp!(m, GraphDamageAggregator, :DamageAggregator, after=:JointAgriculture)
    connect_param!(m, :DamageAggregator => :damage_ag, :JointAgriculture => :agcost)
    audit = AgricultureReplacementAudit.audit_agriculture_replacement(m)
    @test audit.passed
    @test audit.damage_ag_producers == [(component=:JointAgriculture, variable=:agcost)]
    @test isempty(audit.forbidden_components_present)

    absent = Model()
    set_dimension!(absent, :time, [2020])
    set_dimension!(absent, :fund_regions, ["USA"])
    absent_audit = AgricultureReplacementAudit.audit_agriculture_replacement(
        absent; throw_on_error=false)
    @test !absent_audit.passed
    @test occursin("required component DamageAggregator is absent",
                   only(absent_audit.errors))

    missing = Model()
    set_dimension!(missing, :time, [2020])
    set_dimension!(missing, :fund_regions, ["USA"])
    add_comp!(missing, GraphDamageAggregator, :DamageAggregator)
    missing_audit = AgricultureReplacementAudit.audit_agriculture_replacement(
        missing; throw_on_error=false)
    @test !missing_audit.passed
    @test occursin("exactly one internal producer", only(missing_audit.errors))
    @test_throws ErrorException AgricultureReplacementAudit.audit_agriculture_replacement(missing)

    wrong_source = Model()
    set_dimension!(wrong_source, :time, [2020])
    set_dimension!(wrong_source, :fund_regions, ["USA"])
    add_comp!(wrong_source, JointAgriculture, :Agriculture)
    add_comp!(wrong_source, GraphDamageAggregator, :DamageAggregator, after=:Agriculture)
    connect_param!(wrong_source, :DamageAggregator => :damage_ag, :Agriculture => :agcost)
    wrong_audit = AgricultureReplacementAudit.audit_agriculture_replacement(
        wrong_source; throw_on_error=false)
    @test !wrong_audit.passed
    @test wrong_audit.damage_ag_producers == [(component=:Agriculture, variable=:agcost)]
    @test wrong_audit.forbidden_components_present == [:Agriculture]
    @test length(wrong_audit.errors) == 2

    coexistence = Model()
    set_dimension!(coexistence, :time, [2020])
    set_dimension!(coexistence, :fund_regions, ["USA"])
    add_comp!(coexistence, JointAgriculture)
    add_comp!(coexistence, JointAgriculture, :Agriculture, after=:JointAgriculture)
    add_comp!(coexistence, GraphDamageAggregator, :DamageAggregator, after=:Agriculture)
    connect_param!(coexistence, :DamageAggregator => :damage_ag,
                   :JointAgriculture => :agcost)
    coexistence_audit = AgricultureReplacementAudit.audit_agriculture_replacement(
        coexistence; throw_on_error=false)
    @test !coexistence_audit.passed
    @test coexistence_audit.damage_ag_producers == [(component=:JointAgriculture, variable=:agcost)]
    @test coexistence_audit.forbidden_components_present == [:Agriculture]
end

@testset "Paired agriculture component outputs" begin
    function run_agriculture_path(seasonal_precip)
        m = Model()
        set_dimension!(m, :time, [2020, 2021])
        set_dimension!(m, :fund_regions, ["USA"])
        set_dimension!(m, :crops, ["maize", "wheat"])
        add_comp!(m, CropResponseAggregation)
        add_comp!(m, JointAgriculture, after=:CropResponseAggregation)
        connect_param!(m, :JointAgriculture => :joint_loss_fraction,
                       :CropResponseAggregation => :regional_loss_fraction)

        zeros_trc = zeros(2, 1, 2)
        for parameter in (
            :mean_temp_anomaly, :precip_timing_anomaly, :water_stress_anomaly,
            :wet_extreme_anomaly, :heat_extreme_anomaly,
        )
            update_param!(m, :CropResponseAggregation, parameter, zeros_trc)
        end
        update_param!(m, :CropResponseAggregation, :seasonal_precip_anomaly,
                      seasonal_precip)
        for parameter in (
            :beta_temp, :beta_timing, :beta_water_stress, :beta_wet_extreme,
            :beta_heat_extreme, :beta_temp_precip,
        )
            update_param!(m, :CropResponseAggregation, parameter, zeros(1, 2))
        end
        update_param!(m, :CropResponseAggregation, :beta_precip, [0.2 0.1])
        update_param!(m, :CropResponseAggregation, :crop_value_share, [0.4 0.6])
        update_param!(m, :CropResponseAggregation, :adaptation_loss_multiplier,
                      ones(2, 1, 2))
        update_param!(m, :CropResponseAggregation, :adaptation_cost_share,
                      zeros_trc)

        update_param!(m, :JointAgriculture, :income, [100.0; 110.0;;])
        update_param!(m, :JointAgriculture, :population, [10.0; 10.0;;])
        update_param!(m, :JointAgriculture, :gdp90, [80.0])
        update_param!(m, :JointAgriculture, :pop90, [10.0])
        update_param!(m, :JointAgriculture, :agrish0, [0.1])
        run(m)
        return (
            crop_raw_loss_fraction=Array(m[:CropResponseAggregation, :crop_raw_loss_fraction]),
            crop_adjusted_loss_fraction=Array(m[:CropResponseAggregation, :crop_adjusted_loss_fraction]),
            regional_loss_fraction=Array(m[:CropResponseAggregation, :regional_loss_fraction]),
            agcost=Array(m[:JointAgriculture, :agcost]),
        )
    end

    baseline = run_agriculture_path(zeros(2, 1, 2))
    pulse_features = zeros(2, 1, 2)
    pulse_features[2, 1, 1] = 0.05
    pulse = run_agriculture_path(pulse_features)

    audit = PairedAgricultureAudit.audit_paired_agriculture_outputs(
        [2020, 2021], baseline, pulse; first_divergence_year=2021)
    @test audit.passed
    @test audit.n_predivergence_years == 1
    @test audit.maximum_absolute_differences.crop_raw_loss_fraction ≈ 0.01
    @test audit.maximum_absolute_differences.regional_loss_fraction ≈ 0.004
    @test audit.maximum_absolute_differences.agcost > 0

    zero_pulse = PairedAgricultureAudit.audit_paired_agriculture_outputs(
        [2020, 2021], baseline, baseline;
        first_divergence_year=2021, expect_identical=true)
    @test zero_pulse.passed
    @test zero_pulse.maximum_absolute_differences.agcost == 0

    early_change = merge(pulse, (
        regional_loss_fraction=copy(pulse.regional_loss_fraction),
    ))
    early_change.regional_loss_fraction[1, 1] = 0.1
    early_audit = PairedAgricultureAudit.audit_paired_agriculture_outputs(
        [2020, 2021], baseline, early_change;
        first_divergence_year=2021, throw_on_error=false)
    @test !early_audit.passed
    @test any(occursin("before first_divergence_year", error)
              for error in early_audit.errors)

    zero_control_audit = PairedAgricultureAudit.audit_paired_agriculture_outputs(
        [2020, 2021], baseline, pulse;
        first_divergence_year=2021, expect_identical=true, throw_on_error=false)
    @test !zero_control_audit.passed
    @test any(occursin("zero-pulse control", error)
              for error in zero_control_audit.errors)

    malformed = merge(pulse, (agcost=reshape(copy(pulse.agcost), 2, 1, 1),))
    malformed_audit = PairedAgricultureAudit.audit_paired_agriculture_outputs(
        [2020, 2021], baseline, malformed;
        first_divergence_year=2021, throw_on_error=false)
    @test !malformed_audit.passed
    @test any(occursin("shapes", error) || occursin("dimensions", error)
              for error in malformed_audit.errors)

    nonnumeric = merge(pulse, (agcost=Any[0.0; "bad";;],))
    nonnumeric_audit = PairedAgricultureAudit.audit_paired_agriculture_outputs(
        [2020, 2021], baseline, nonnumeric;
        first_divergence_year=2021, throw_on_error=false)
    @test !nonnumeric_audit.passed
    @test any(occursin("nonnumeric or nonfinite", error)
              for error in nonnumeric_audit.errors)

    malformed_years_audit = PairedAgricultureAudit.audit_paired_agriculture_outputs(
        Any["2020", 2021], baseline, pulse;
        first_divergence_year=2021, throw_on_error=false)
    @test !malformed_years_audit.passed
    @test any(occursin("integer sequence", error)
              for error in malformed_years_audit.errors)

    @test_throws ErrorException PairedAgricultureAudit.audit_paired_agriculture_outputs(
        [2020, 2021], baseline, pulse; first_divergence_year=2020)
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
