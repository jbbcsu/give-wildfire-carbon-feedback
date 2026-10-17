# Forestry/timber market climate-damage benchmark

This isolated project audits and benchmarks **market welfare changes in timber
and forest products**. It excludes wildfire carbon feedbacks, smoke mortality,
nonmarket ecosystem services, agriculture, and property damage.

The executable benchmark reproduces only the forestry component of the tagged
open-source MimiFUND model. It is an external, legacy benchmark—not yet an
additive GIVE damage sector. The model's published documentation and executable
defaults disagree on two forestry coefficients, so the integration contract is
fail-closed until that discrepancy is resolved or a newer response calibration
is substituted.

## Reproduce

Requirements: Git, Julia 1.8.x, and about 1 GiB free memory. Raw upstream code
is downloaded to `data/raw/` and ignored by Git.

```bash
./forestry_market/scripts/acquire_mimifund.sh
JULIA_DEPOT_PATH=/tmp/forestry_julia_depot julia \
  --project=forestry_market/data/raw/MimiFUND-v3.13.0 \
  -e 'using Pkg; Pkg.instantiate()'
MIMIFUND_SOURCE=forestry_market/data/raw/MimiFUND-v3.13.0 \
  JULIA_DEPOT_PATH=/tmp/forestry_julia_depot julia \
  --project=forestry_market/data/raw/MimiFUND-v3.13.0 \
  forestry_market/scripts/run_benchmark.jl
python3 -m unittest discover -s forestry_market/tests -v
```

The primary reported quantity is the global forestry-market welfare
contribution from a 2025 CO2 pulse, discounted at a constant 2% and expressed
in 2020 USD per metric tonne CO2. Positive values are damages; negative values
are benefits. See `docs/AUDIT_AND_DECISION.md` before using any result.
