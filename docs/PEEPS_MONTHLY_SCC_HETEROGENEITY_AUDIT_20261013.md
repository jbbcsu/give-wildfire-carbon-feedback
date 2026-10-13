# PEEPS monthly SCC country/FUND-region heterogeneity audit

## Finding

The small central global joint diagnostic is primarily a net of opposing
country and FUND-region accounting components. It is not evidence that the
underlying country components are uniformly small, and these accounting
components must not be relabeled as local biophysical or causal effects.

At the smallest pulse, fixed adaptation, and the 2% discount schedule:

| Scale | Positive components | Negative components | Gross absolute | Global net | Cancellation share |
|---|---:|---:|---:|---:|---:|
| 107 countries | +$0.011572 | -$0.007304 | $0.018876 | +$0.004269 | 77.4% |
| 16 FUND regions plus UNMAPPED | +$0.011145 | -$0.006877 | $0.018022 | +$0.004269 | 76.3% |

All values are 2020 USD per tCO2. The country gross absolute total is 4.42
times the absolute global net. Equivalently, the negative side offsets 63.1%
of the positive side. Of the 77.4% country-to-global cancellation, 4.5
percentage points occur when countries are netted within FUND regions and
72.9 percentage points occur when the signed region totals are netted
globally. The dominant mechanism is therefore cancellation across regions,
not merely within-region aggregation.

Excluding the separately preserved `UNMAPPED` Antigua and Barbuda row, eight
FUND regions are positive and eight are negative. The largest signed region
components remain USA (+$0.007231), China (-$0.002829), Eastern Europe
(+$0.001853), Latin America (-$0.001462), and Sub-Saharan Africa
(-$0.001388/tCO2). The United States component alone exceeds the absolute
global net.

## Component scale and concentration

The country distribution is highly concentrated and heavy-tailed rather than
uniform:

- median absolute country component: $0.00000721/tCO2;
- 95th percentile: $0.000743/tCO2;
- maximum: $0.007231/tCO2;
- 95 of 107 countries are individually below 1% of country gross absolute
  magnitude, and 103 are below 5%;
- the largest country supplies 38.3% of gross absolute magnitude; and
- the top five countries supply 71.7%, while the top ten supply 83.4%.

Thus most country accounting components are small, but a small number are
large enough that opposing signs materially determine the global result. The
correct conclusion is “concentrated components with substantial geographic
cancellation,” not “small local effects.”

This conclusion is not confined to the headline design cell. Across all 36
registered pulse × adaptation × discount cells, country cancellation in the
joint monthly channel ranges from 77.3% to 97.5%, with a median of 86.4%.
Gross absolute magnitude is a median 7.41 times the absolute net and reaches
39.90 times in the most offsetting cell. The global joint net is positive in
30 cells and negative in six, so even the sign of the net is design-sensitive.

## Timing heterogeneity

The timing increment also contains opposing country components. Its central
gross positive and negative sums are +$0.002054 and -$0.000724/tCO2, compared
with a +$0.001330 net; 52.1% of its gross absolute magnitude cancels. Its gross
absolute magnitude is 14.7% of the joint channel's gross absolute magnitude.

Timing amplifies the quantity-reference sign in 71 countries and offsets it
in 36. It changes the quantity-to-joint sign in ten countries. The absolute
timing component exceeds the absolute quantity component in 23 countries and
exceeds the absolute joint component in 15. These are accounting contrasts
under the matched monthly model; they are not heterogeneous causal timing
coefficients.

## Suggested claims/limitations insert

> At the smallest pulse under fixed adaptation and the 2% discount schedule,
> the +$0.004269/tCO2 global joint monthly-precipitation diagnostic is the net
> of +$0.011572/tCO2 in positive country components and -$0.007304/tCO2 in
> negative components. Gross absolute country components are 4.42 times the
> net, so 77.4% of their magnitude cancels. Most cancellation occurs across
> signed FUND-region totals (72.9% of country gross absolute magnitude), with
> a smaller 4.5% removed by within-region country netting. The distribution is
> concentrated: the five largest countries account for 71.7% of gross
> absolute magnitude, although 95 of 107 countries are individually below 1%
> of that total. The small global net therefore reflects concentrated,
> offsetting geographic accounting components rather than uniformly small
> effects. These values are national-market accounting contributions from a
> one-ESM, one-scenario, maize-only monthly-mean diagnostic—not local causal
> responses, household welfare incidence, total country damages, or a final
> precipitation SCC. The calculation omits daily drought and extremes, other
> crops, trade, storage, and adaptation costs; it uses standard deterministic
> GIVE discount factors while Moore agriculture remains installed, and it is
> not a paired GIVE agriculture replacement.

## Validation and reproducibility

The audit uses only the previously validated country and region tables. It
re-verifies their pinned hashes, reconstructs region totals from countries,
recomputes all 36 registered design cells, and independently validates the
central sign, cancellation, and timing identities. Maximum country-to-region
aggregation disagreement remains below `1e-15` USD/tCO2. The calculation
peaked at 105,447,424 bytes (100.56 MiB); the independent standard-library
validator peaked at 35,913,728 bytes (34.25 MiB).

- Audit: `scripts/audit_peeps_monthly_scc_heterogeneity.py`
- Independent validator:
  `scripts/validate_peeps_monthly_scc_heterogeneity_audit.py`
- Receipt:
  `data/provenance/peeps_monthly_scc_heterogeneity_audit_20261013.json`
- Validation receipt:
  `data/provenance/peeps_monthly_scc_heterogeneity_validation_20261013.json`
- Validated source receipt:
  `data/provenance/peeps_monthly_scc_country_decomposition_20261012.json`

Claim gates remain closed for local biophysical effects, country causal
effects, total country damages, a representative global precipitation SCC,
and paired GIVE agriculture replacement.
