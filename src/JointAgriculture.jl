#=
Isolated replacement agriculture component for precipitation-SCC research.

This component is not included in MimiGIVE and does not read wildfire files.
It is designed to replace the temperature-indexed MooreAg component, which has
no explicit separable precipitation input in this checkout, once the
crop-specific response bundle and welfare mapping are independently validated.
Crop responses are calculated by `CropResponseAggregation`; this component
only translates its regional joint-loss fraction into the existing `agcost`
interface.
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

    # Output from CropResponseAggregation. It already includes the declared
    # crop-specific response, fixed baseline weights, and adaptation scenario.
    joint_loss_fraction = Parameter(index=[time, fund_regions])

    agrish = Variable(index=[time, fund_regions])
    raw_climate_loss_fraction = Variable(index=[time, fund_regions])
    climate_loss_fraction = Variable(index=[time, fund_regions])
    agcost = Variable(index=[time, fund_regions], unit="billion US\$2005/yr")

    function run_timestep(p, v, d, t)
        for r in d.fund_regions
            ypc = p.income[t, r] / p.population[t, r] * 1000.
            ypc90 = p.gdp90[r] / p.pop90[r] * 1000.
            v.agrish[t, r] = p.agrish0[r] * (ypc / ypc90)^(-p.agel)

            v.raw_climate_loss_fraction[t, r] = p.joint_loss_fraction[t, r]
            v.climate_loss_fraction[t, r] = p.joint_loss_fraction[t, r]
            v.agcost[t, r] = p.income[t, r] * v.agrish[t, r] * p.joint_loss_fraction[t, r]
        end
    end
end
