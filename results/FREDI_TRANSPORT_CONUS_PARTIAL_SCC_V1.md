# FrEDI road and rail heat damages: CONUS partial SCC

## Result

For the matched 2025 GIVE CO2 pulse, the primary FrEDI `Reactive` specification
produces a **CONUS road-and-rail partial SCC of $0.21448 per metric tonne of
CO2** in 2020 USD. This is the unweighted mean across the six released FrEDI
GCM-pattern response surfaces. The six-surface range is $0.10021–$0.41146.

The primary mean comprises $0.12927/tCO2 from the released `Roads` aggregate
and $0.08521/tCO2 from `Rail`. These are not component-resolved estimates:
Roads combines repair and road-user costs, while Rail combines replacement and
delay costs in the public FrEDI release.

Adaptation is consequential. The corresponding mean is $1.56842/tCO2 under
`NoAdapt` and $0.01482/tCO2 under `Proactive`. The Proactive six-surface range
includes zero (-$0.05854 to $0.06646/tCO2), so it should not be described as a
robust positive effect.

## What the estimate means

This is a **partial CONUS contribution**, not a global SCC and not a new total
GIVE SCC. It evaluates the annual difference between matched GIVE baseline and
pulse temperatures, converts global warming to CONUS warming with EPA's 1.421
factor, applies FrEDI v4.1.1 state-level response functions and annual
infrastructure scalars, converts 2015 USD to 2020 USD, discounts with the
matched GIVE Ramsey factors, and divides by the exact 2025 pulse of
366,666.6667 metric tonnes CO2.

## Claim limits

- The calculation stops in 2092. In 2093 the GIVE path exceeds 3°C CONUS
  warming, the lowest maximum temperature shared by all six released surfaces.
  No response-function extrapolation is used. Omitted post-2092 marginal
  damages make this a truncated partial SCC.
- The six FrEDI GCM surfaces describe pattern uncertainty in the published
  impact functions. Their unweighted mean and range are descriptive, not a
  fitted probability distribution.
- Cross-sector addition remains unauthorized. Road-user and rail-delay costs
  must first be reconciled with any labor, market-output, or other transport
  accounting boundaries.
- Results apply only to the 48 contiguous states plus DC. There is no
  U.S.-to-world scaling.

## Provenance and validation

FrEDI code is pinned to release v4.1.1 (`08ead1b...`) and FrEDI_Data to commit
`b506a3e...`. The 2015-to-2020 conversion is 105.362 / 97.315 =
1.082690232749319, from the BEA GDP implicit price deflator series `GDPDEF` as
served by [Federal Reserve FRED](https://fred.stlouisfed.org/series/GDPDEF).

An independent Python implementation reconstructs all 2,448 annual rows from
the raw FrEDI response and scalar tables. The largest difference from the
official R runtime calculation is $0.000588 in annual 2015-USD damages, arising
from floating-point evaluation against damage levels measured in billions of
dollars. The SCC outputs agree well beyond the reported precision. Validation
runs below 40 MiB locally and passed under a 1 GiB memory cap with `nice -n 10`
on `darecompute-02`.
