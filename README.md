# Biodiversity nonuse damages in GIVE

This isolated project evaluates and reproduces a biodiversity **nonuse-value**
damage extension to GIVE. It is separate from precipitation/agriculture,
fisheries, and wildfire work.

The initial target follows Wingenroth et al. (2024): global temperature changes
remaining species-level biodiversity, and country income/population translate
the climate-driven biodiversity deficit into willingness-to-pay damages.

No SCC estimate is authorized until the published parameter scaling, regional
valuation coefficients, uncertainty draws, and GIVE country/region mappings are
independently reproduced.

`python/biodiversity_kernel.py` is the executable tested reference. The Julia
module mirrors it for eventual Mimi/GIVE integration. On this host it is
tested with the repository-level Julia 1.8.5 runtime and a project-local,
gitignored depot:

```sh
JULIA_DEPOT_PATH=.julia_depot ../tools/julia-1.8.5/bin/julia --project=. test/runtests.jl
```

## Boundaries

- Include existence/nonuse value only.
- Exclude crop productivity, fisheries, coral tourism, coastal protection,
  carbon-cycle feedbacks, and other market ecosystem services.
- Use matched baseline and marginal-pulse climate paths.
- Add the component once to consumption/damages and discount once.
