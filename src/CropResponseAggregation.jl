#=
Crop-specific joint climate-response and aggregation contract.

All feature and coefficient arrays are supplied externally from a registered
response bundle. `crop_value_share` is a fixed baseline share of total
agricultural value, not a climate-responsive production weight. By default the
component refuses incomplete agricultural coverage so an omitted crop cannot
silently receive zero climate damage in an SCC run.
=#
using Mimi

@defcomp CropResponseAggregation begin
    fund_regions = Index()
    crops = Index()

    mean_temp_anomaly = Parameter(index=[time, fund_regions, crops], unit="degC")
    seasonal_precip_anomaly = Parameter(index=[time, fund_regions, crops], unit="registered transformed units")
    precip_timing_anomaly = Parameter(index=[time, fund_regions, crops], unit="registered transformed units")
    water_stress_anomaly = Parameter(index=[time, fund_regions, crops], unit="registered transformed units")
    wet_extreme_anomaly = Parameter(index=[time, fund_regions, crops], unit="registered transformed units")
    heat_extreme_anomaly = Parameter(index=[time, fund_regions, crops], unit="registered transformed units")

    beta_temp = Parameter(index=[fund_regions, crops])
    beta_precip = Parameter(index=[fund_regions, crops])
    beta_timing = Parameter(index=[fund_regions, crops])
    beta_water_stress = Parameter(index=[fund_regions, crops])
    beta_wet_extreme = Parameter(index=[fund_regions, crops])
    beta_heat_extreme = Parameter(index=[fund_regions, crops])
    beta_temp_precip = Parameter(index=[fund_regions, crops])

    # Shares are measured against the complete agricultural value pool in each
    # region. The default production gate therefore requires their sum to one.
    crop_value_share = Parameter(index=[fund_regions, crops])
    require_full_coverage = Parameter{Bool}(default=true)
    weight_tolerance = Parameter(default=1e-8)

    # Adaptation is crop specific and applied before aggregation. Cost is a
    # share of the crop's baseline value; benefits are not attenuated.
    adaptation_loss_multiplier = Parameter(index=[time, fund_regions, crops])
    adaptation_cost_share = Parameter(index=[time, fund_regions, crops])
    floor_on_crop_damages = Parameter{Bool}(default=true)
    ceiling_on_crop_benefits = Parameter{Bool}(default=false)

    crop_raw_loss_fraction = Variable(index=[time, fund_regions, crops])
    crop_adjusted_loss_fraction = Variable(index=[time, fund_regions, crops])
    coverage_share = Variable(index=[time, fund_regions])
    regional_loss_fraction = Variable(index=[time, fund_regions])

    function run_timestep(p, v, d, t)
        p.weight_tolerance >= 0 || error("weight_tolerance must be nonnegative")

        for r in d.fund_regions
            coverage = 0.0
            regional_loss = 0.0

            for c in d.crops
                weight = p.crop_value_share[r, c]
                isfinite(weight) && weight >= 0 ||
                    error("crop_value_share must be finite and nonnegative")
                coverage += weight

                multiplier = p.adaptation_loss_multiplier[t, r, c]
                isfinite(multiplier) && multiplier >= 0 ||
                    error("adaptation_loss_multiplier must be finite and nonnegative")
                cost_share = p.adaptation_cost_share[t, r, c]
                isfinite(cost_share) && cost_share >= 0 ||
                    error("adaptation_cost_share must be finite and nonnegative")

                raw = p.beta_temp[r, c] * p.mean_temp_anomaly[t, r, c] +
                      p.beta_precip[r, c] * p.seasonal_precip_anomaly[t, r, c] +
                      p.beta_timing[r, c] * p.precip_timing_anomaly[t, r, c] +
                      p.beta_water_stress[r, c] * p.water_stress_anomaly[t, r, c] +
                      p.beta_wet_extreme[r, c] * p.wet_extreme_anomaly[t, r, c] +
                      p.beta_heat_extreme[r, c] * p.heat_extreme_anomaly[t, r, c] +
                      p.beta_temp_precip[r, c] * p.mean_temp_anomaly[t, r, c] *
                                                   p.seasonal_precip_anomaly[t, r, c]
                isfinite(raw) || error("crop response is nonfinite; check feature and coefficient bundle")
                v.crop_raw_loss_fraction[t, r, c] = raw

                bounded = p.floor_on_crop_damages ? min(1.0, raw) : raw
                bounded = p.ceiling_on_crop_benefits ? max(-1.0, bounded) : bounded
                adjusted = min(0.0, bounded) + multiplier * max(0.0, bounded) + cost_share
                v.crop_adjusted_loss_fraction[t, r, c] = adjusted
                regional_loss += weight * adjusted
            end

            coverage <= 1.0 + p.weight_tolerance ||
                error("crop_value_share sums to more than total agricultural value")
            if p.require_full_coverage && abs(coverage - 1.0) > p.weight_tolerance
                error("full-coverage SCC run requires crop_value_share to sum to one")
            end
            v.coverage_share[t, r] = coverage
            v.regional_loss_fraction[t, r] = regional_loss
        end
    end
end
