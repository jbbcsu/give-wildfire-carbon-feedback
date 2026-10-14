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

`python/validate_biodiversity_pair.py` is a fail-closed accounting preflight
for externally produced baseline/pulse bundles. It requires exact matched
draw-country-year keys and fixed socioeconomic/valuation identities,
recomputes every deficit and country damage, and enforces pre-divergence and
zero-pulse identity. Its output explicitly does not validate empirical
parameters, overlap, discounting, damages, or an SCC.

`config/biodiversity_replication_request_v1.json` is the versioned, seven-part
external-artifact request that now defines the empirical gate. Validate its
fail-closed semantics and, optionally, the pinned official MimiGIVE checkout:

```sh
python3 python/validate_replication_request.py \
  --request config/biodiversity_replication_request_v1.json \
  --source-root /path/to/MimiGIVE.jl \
  --out data/provenance/biodiversity_public_release_audit_20261014.json
```

The current validated conclusion is only that the pinned public repository
does not expose a biodiversity/nonuse component under the configured search
scope and that exact author artifacts are required. See
`BIODIVERSITY_ARTIFACT_REQUEST_20261014.md`. This is not evidence that the
approximately USD 8/tCO2 publication benchmark has been reproduced or is
eligible for inclusion in GIVE.

`python/validate_biodiversity_artifact_package.py` now turns that seven-part
request into a fail-closed admission gate. It validates checksummed licensed
source/environment files, all 16 regional coefficients, the 389-group and
20,000-draw climate response, complete mapping, 10,000 joint draw links,
matched annual country/global baseline-pulse paths, and the nonuse-only
overlap boundary. The annual reconciliation is streamed to keep memory
bounded. The current public evidence supplies 0 of 7 groups and is rejected.
See `BIODIVERSITY_ARTIFACT_PACKAGE_ADMISSION_GATE_20261014.md`. Passing this
gate would not itself validate a damage function or SCC.

## Boundaries

- Include existence/nonuse value only.
- Exclude crop productivity, fisheries, coral tourism, coastal protection,
  carbon-cycle feedbacks, and other market ecosystem services.
- Use matched baseline and marginal-pulse climate paths.
- Add the component once to consumption/damages and discount once.
