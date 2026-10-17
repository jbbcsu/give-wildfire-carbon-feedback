# MimiFUND aggregate-water marginal benchmark

## Sector selection

Municipal water/drought was selected over energy demand. GIVE already includes
a global country-level building heating/cooling expenditure component. Its
municipal water-supply sector is absent. This result advances the closest
executable global water route while retaining the earlier conclusion that no
municipal-only transfer is currently admissible.

## Reproduced benchmark

Using MimiFUND v3.13.0 at commit
`3f5fe29ffb753a49ff070d04b74ae42abd23576b`, a 2025 one-year CO2 pulse, annual
damages through 2300, and constant 2% discounting gives an aggregate
water-resources marginal value of:

- **$1.450727/tCO2 in 1995 USD**;
- **$2.283770/tCO2 in 2020 USD**, using the pinned BEA GDP deflator ratio
  `105.377 / 66.939`.

This is a deterministic benchmark, not a municipal-water SCC and not an
addition to GIVE. FUND's water coefficient bundles urban supply, irrigation,
amenity/ecosystem, and other water-resource evidence. Its equation responds to
temperature directly; it does not model drought indices, runoff, storage,
water quality, treatment, conveyance, or system reliability.

The result is numerically stable to the tested pulse size: changing the
one-year pulse from 10 million to 100 million tCO2 changes the 1995-dollar
benchmark by 0.00098%. The official FUND ten-year pulse shape gives
$2.079794/tCO2 in 2020 USD, about 8.9% below the one-year target-shape result.
The release README describes its default as 10 GtCO2, but the code default is
`1e7` metric tonnes, or 10 MtCO2. The implementation and output record use the
code quantity and do not silently resolve the documentation discrepancy.

## Regional heterogeneity

The 16 FUND-region central estimates contain both positive and negative
values. Their 2020-dollar positive sum is +$3.281829/tCO2 and negative sum is
-$0.998060/tCO2, leaving the +$2.283770/tCO2 net. Thus 46.6% of gross absolute
regional value cancels in the global mean. China is the largest negative
regional contribution (-$0.996957/tCO2), while the former Soviet Union is the
largest positive contribution (+$1.234861/tCO2). These are reduced-form FUND
regions, not new causal estimates.

## Integration status

All promotion gates remain closed because:

1. the endpoint is not municipal-only;
2. no explicit drought or hydrologic response is modeled;
3. FUND documentation describes global temperature while release code uses
   regional temperature;
4. only the deterministic central calibration was run;
5. overlap with GIVE agriculture, energy, and ecosystem services is unresolved.

The annual and region-level files are valid for external comparison and future
replacement design. They must not be added to headline GIVE SCC totals.

## Reproduction

Clone MimiFUND v3.13.0 into `vendor/MimiFUND.jl`, copy the checked-in manifest
to that clone, instantiate, and run:

```bash
cp environment/MimiFUND-v3.13.0-Manifest.toml vendor/MimiFUND.jl/Manifest.toml
julia --project=vendor/MimiFUND.jl -e 'using Pkg; Pkg.instantiate()'
nice -n 10 julia --project=vendor/MimiFUND.jl \
  scripts/compute_mimifund_aggregate_water_benchmark.jl data/derived
python3 python/validate_mimifund_aggregate_water_benchmark.py
python3 -m unittest discover -s test -v
```
