#=
Isolated replacement agriculture component for precipitation-SCC research.

This component is not included in MimiGIVE and does not read wildfire files.
It is designed to replace the temperature-only MooreAg component once the
coefficient inputs are estimated and independently validated.
=#
using Mimi

@defcomp JointAgriculture begin
    fund_regions = Index()

    income = Parameter(index=[time, fund_regions], unit="billion US\$2005/yr")
    population = Parameter(index=[time, fund_regions], unit="million")
    gdp90 = Parameter(index=[fund_regions], unit="billion US\$2005/yr")
    pop90 = Parameter(index=[fund_regions], unit="million")
    agrish0 = Parameter(index=[fund_regions])
    agel = Parameter(default=0.31)

    # All climate inputs are crop-calendar/exposure weighted departures from a
    # documented historical baseline.  Values come from the external pipeline.
    temp_anomaly = Parameter(index=[time, fund_regions], unit="degC")
    seasonal_precip_anomaly = Parameter(index=[time, fund_regions], unit="documented feature units")
    dry_spell_anomaly = Parameter(index=[time, fund_regions], unit="days")
    wet_extreme_anomaly = Parameter(index=[time, fund_regions], unit="documented feature units")

    # Region-specific coefficients are estimated jointly.  CO2 fertilization,
    # crop calendars, and market feedback must be represented once upstream or
    # downstream according to the registered accounting specification.
    beta_temp = Parameter(index=[fund_regions])
    beta_precip = Parameter(index=[fund_regions])
    beta_dry_spell = Parameter(index=[fund_regions])
    beta_wet_extreme = Parameter(index=[fund_regions])
    beta_temp_precip = Parameter(index=[fund_regions])
    # Multiplier applies only to positive loss; adaptation cannot erase modeled
    # climate benefits. Cost is an annual share of agricultural value and is
    # explicitly visible rather than hidden in an effectiveness coefficient.
    adaptation_loss_multiplier = Parameter(index=[time, fund_regions])
    adaptation_cost_share = Parameter(index=[time, fund_regions])
    floor_on_damages = Parameter{Bool}(default=true)
    ceiling_on_benefits = Parameter{Bool}(default=false)

    agrish = Variable(index=[time, fund_regions])
    raw_climate_loss_fraction = Variable(index=[time, fund_regions])
    climate_loss_fraction = Variable(index=[time, fund_regions])
    agcost = Variable(index=[time, fund_regions], unit="billion US\$2005/yr")

    function run_timestep(p, v, d, t)
        for r in d.fund_regions
            ypc = p.income[t, r] / p.population[t, r] * 1000.
            ypc90 = p.gdp90[r] / p.pop90[r] * 1000.
            v.agrish[t, r] = p.agrish0[r] * (ypc / ypc90)^(-p.agel)

            raw = p.beta_temp[r] * p.temp_anomaly[t, r] +
                  p.beta_precip[r] * p.seasonal_precip_anomaly[t, r] +
                  p.beta_dry_spell[r] * p.dry_spell_anomaly[t, r] +
                  p.beta_wet_extreme[r] * p.wet_extreme_anomaly[t, r] +
                  p.beta_temp_precip[r] * p.temp_anomaly[t, r] * p.seasonal_precip_anomaly[t, r]
            v.raw_climate_loss_fraction[t, r] = raw
            loss = p.floor_on_damages ? min(1., raw) : raw
            loss = p.ceiling_on_benefits ? max(-1., loss) : loss
            loss = min(0., loss) + p.adaptation_loss_multiplier[t, r] * max(0., loss) + p.adaptation_cost_share[t, r]
            v.climate_loss_fraction[t, r] = loss
            v.agcost[t, r] = p.income[t, r] * v.agrish[t, r] * loss
        end
    end
end
