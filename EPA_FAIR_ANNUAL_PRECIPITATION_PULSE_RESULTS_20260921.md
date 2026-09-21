# EPA/FAIR annual precipitation-pulse benchmark: validated result

## Result

The published EPA country/model annual-precipitation slopes can be mapped
directly to the matched core-GIVE FAIR marginal temperature path. For each
finite country/model pair, the benchmark calculates

`annual precipitation change = EPA slope × pulse-minus-baseline temperature`.

The calculation retains 4,703 finite country/model pairs covering all 184
GIVE countries. At every positive pulse size and selected year, 53.63% of
pair-level changes are positive and 46.37% are negative; 103 country ensemble
medians are positive and 81 are negative. These sign shares are inherited from
the published EPA slopes, because the FAIR pulse temperature change is
positive.

For the smallest validated pulse (0.000025 GtC), the 2100 temperature
difference is `3.7015962e-8 K`. Across country/model pairs, the resulting 2100
annual-precipitation change has a median of `1.0075122e-7 mm yr-1`, a 5th to
95th percentile range of `-3.1812482e-6` to `3.8770529e-6 mm yr-1`, and a
minimum to maximum range of `-1.3421976e-5` to `1.7869277e-5 mm yr-1`.
The very small magnitude is expected for this deliberately small marginal
carbon pulse and is not an annual-climate scenario projection.

After normalization by pulse size, the two smallest positive FAIR pulses agree
over 2021–2300 to a maximum relative discrepancy of `1.5764e-4`. The maximum
absolute normalized precipitation discrepancy is
`1.1784e-4 mm yr-1 GtC-1`. This supports numerical use of the saved marginal
temperature path at the tested scale.

## Validation and provenance

- Main result SHA-256:
  `9fe97f534794a67fc013ddd3654c4a8a62ccc88d94b54beb780bc6d092116be2`.
- Independent validation result SHA-256:
  `33f726572653c12dc67da7423730be0be153af417bce5dbf8c5bed2bef534039`.
- A separate standard-library implementation reconstructed all 18
  pulse/year summaries and convergence statistics, passing 256 numeric and
  support checks.
- The builder's sampled peak process-group RSS was 83,640,320 bytes; the
  independent validator's was 196,608 bytes. Both completed below the 512 MiB
  cap with the 130 GiB free-disk floor intact.
- Missing EPA slopes remain missing. No slope, baseline precipitation, crop
  response, damage, or SCC value was imputed.

## Interpretation boundary

This closes only the annual-quantity climate-link engineering gate. It shows
that a published precipitation pattern can be driven by GIVE's actual FAIR
marginal warming, providing a transparent literature-based benchmark. It does
not represent within-season timing, dry spells, heavy-rain extremes, drought,
joint heat–moisture effects, yields, irrigation, adaptation, economic damage,
or an SCC increment. The daily ISIMIP/GGCMI and U.S. county tracks remain
necessary for those claims.
