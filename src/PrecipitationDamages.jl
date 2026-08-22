#=
Standalone Mimi component contract for the precipitation-SCC project.

This file is deliberately unintegrated: all coefficient arrays must be
supplied explicitly from an empirically estimated coefficient bundle.
It has no imports from the wildfire project.
=#
using Mimi

@defcomp PrecipitationDamages begin
    country = Index()
    # Annual, exposure-weighted anomalies/index departures from the empirical baseline.
    mean_precip_anomaly = Parameter(index=[time, country])
    heavy_precip_anomaly = Parameter(index=[time, country])
    exposure = Parameter(index=[time, country], unit="persons or assets; documented by pathway")
    # Monetary loss per exposure-unit and index-unit; must be supplied by a registered estimate.
    beta_mean = Parameter(index=[country])
    beta_heavy = Parameter(index=[country])
    adaptation_multiplier = Parameter(index=[time, country])
    damages = Variable(index=[time, country], unit="US\$2005/yr")

    function run_timestep(p, v, d, t)
        for c in d.country
            raw = p.exposure[t, c] * (p.beta_mean[c] * p.mean_precip_anomaly[t, c] +
                                       p.beta_heavy[c] * p.heavy_precip_anomaly[t, c])
            v.damages[t, c] = p.adaptation_multiplier[t, c] * raw
        end
    end
end
