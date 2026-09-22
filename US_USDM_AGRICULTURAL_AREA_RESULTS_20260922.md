# U.S. drought--yield agricultural-area spatial-fidelity results

**Status:** completed historical sensitivity with independent numerical and
resource validation. This is not a causal yield response, future drought
projection, global damage function, or SCC input.

## Question

The initial U.S. benchmark weighted U.S. Drought Monitor (USDM) categories by
whole-county area, whereas Kuwayama et al. (2019) report intersecting weekly
USDM maps with agricultural land. This analysis asks whether that spatial
approximation materially changes the historical corn and soybean results.

## Frozen construction

The analysis uses the official 2008 USDA NASS 30 m Cropland Data Layer (CDL)
and all 679 official Tuesday USDM vector maps from 26 September 2000 through 24
September 2013. Two outcome-blind masks are reported together because the
article does not list its exact CDL codes:

- **Cultivated:** crop classes plus code 61, Fallow/Idle Cropland.
- **Broad agriculture:** the cultivated mask plus code 176,
  Grassland/Pasture.

The national pass reduces the 30 m CDL to agricultural-pixel-weighted 3.96 km
equal-area support points. Weekly mutually exclusive D0--D4 polygons are then
integrated over October of the preceding year through September of the harvest
year. The crop outcomes, continental irrigation classifier, fixed effects,
state trends, direct-weather hierarchy, and inferential checks are unchanged
from the corrected whole-county benchmark.

## Exposure accounting

The grid contains 970,190 sparse rows for 2,909 counties and two masks. Broad
support strictly exceeds cultivated support in every county, normalized
weights sum to one within `5.67e-15`, and the grid build peaked at 430,145,536
bytes RSS. The final 77-batch spatial overlay contains 75,634
county-mask-harvest-year rows. No retained support point belongs to more than
one USDM class, and category plus no-drought time reconciles to 365/7 or 366/7
weeks within `1.43e-14`. The maximum accepted batch peak was 622,051,328 bytes,
below the 640 MiB ceiling.

Full-support means partly reflect different county coverage:

| Basis | County-years | Counties | D0 | D1 | D2 | D3 | D4 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Published Table 2 | 40,040 | -- | 8.470 | 5.660 | 3.870 | 2.260 | 0.800 |
| Whole county | 39,299 | 3,023 | 8.603 | 5.739 | 3.906 | 2.287 | 0.821 |
| Cultivated | 37,817 | 2,909 | 8.496 | 5.691 | 3.893 | 2.292 | 0.826 |
| Broad agriculture | 37,817 | 2,909 | 8.497 | 5.695 | 3.882 | 2.296 | 0.827 |

On the exact common support of 36,803 county-years in 2,831 counties, means
are 8.586/5.749/3.926/2.327/0.841 for whole-county, 8.557/5.738/3.921/
2.318/0.848 for cultivated, and 8.558/5.743/3.911/2.322/0.849 for broad
agriculture. Agricultural weighting therefore changes national means only
modestly on fixed support. The apparent larger full-support movement toward
the published means must not be attributed solely to weighting.

## Historical drought-only associations

Entries are exact fitted percent changes in yield for one additional
area-equivalent week, conditional on the other categories, county and year
fixed effects, and state-specific trends.

| Crop | Support | Basis | D0 | D1 | D2 | D3 | D4 |
|---|---|---|---:|---:|---:|---:|---:|
| Corn | Dryland | County | -0.1365 | -0.3093 | -0.6136 | -1.0719 | -1.1413 |
| Corn | Dryland | Cultivated | -0.1409 | -0.3059 | -0.6107 | -1.0858 | -1.1468 |
| Corn | Dryland | Broad | -0.1378 | -0.3125 | -0.6099 | -1.0796 | -1.1477 |
| Corn | Irrigated | County | -0.0858 | -0.0414 | -0.1233 | -0.1233 | -0.4881 |
| Corn | Irrigated | Cultivated | -0.0907 | -0.0395 | -0.1346 | -0.1172 | -0.4722 |
| Corn | Irrigated | Broad | -0.0911 | -0.0355 | -0.1358 | -0.1180 | -0.4750 |
| Soybean | Dryland | County | -0.1747 | -0.5888 | -0.5750 | -0.8394 | -0.6190 |
| Soybean | Dryland | Cultivated | -0.1794 | -0.5880 | -0.5785 | -0.8444 | -0.6262 |
| Soybean | Dryland | Broad | -0.1770 | -0.5909 | -0.5805 | -0.8398 | -0.6195 |
| Soybean | Irrigated | County | -0.0025 | -0.2108 | -0.2899 | -0.3987 | -0.0699 |
| Soybean | Irrigated | Cultivated | -0.0104 | -0.2130 | -0.2824 | -0.4051 | -0.0628 |
| Soybean | Irrigated | Broad | -0.0075 | -0.2110 | -0.2881 | -0.3982 | -0.0712 |

All 20 estimates remain negative for both masks, and the dryland-versus-
irrigated qualitative ordering is unchanged. Relative to whole-county weights,
the maximum absolute coefficient movement is 0.01593 percentage point for the
cultivated mask and 0.01314 for the broad mask; mean absolute movements are
0.00612 and 0.00420 percentage point. The two agricultural masks differ by at
most 0.00836 percentage point. Thus, coarse agricultural weighting is not the
source of the benchmark's principal drought-only pattern.

## Direct-weather hierarchy and inference sensitivity

Once April--September rainfall and heat are controlled, the cultivated-mask
slopes are:

| Crop | Support | D0 | D1 | D2 | D3 | D4 |
|---|---|---:|---:|---:|---:|---:|
| Corn | Dryland | +0.0436 | -0.0083 | -0.2546 | -0.4184 | -0.1811 |
| Corn | Irrigated | +0.0462 | +0.0581 | +0.0283 | -0.0133 | -0.0916 |
| Soybean | Dryland | +0.0267 | -0.2292 | -0.1628 | -0.1047 | +0.3267 |
| Soybean | Irrigated | +0.1686 | -0.0420 | -0.1186 | -0.1865 | +0.3731 |

The broad-mask estimates differ from these by at most 0.00806 percentage
point, and the maximum difference between either agricultural mask and the
whole-county specification is 0.01292 percentage point. With state-cluster CR1
and a `G-1` t reference, cultivated-mask corn-dryland D2 (-0.2546%, p=.0135)
and D3 (-0.4184%, p=.0083), and soybean-dryland D1 (-0.2292%, p=.0045) and D2
(-0.1628%, p=.0373), remain negative at p<.05. All four retain their signs in
every represented-state deletion. The broad mask yields the same conclusion.
Several other coefficients are imprecise or change sign, including positive
soybean D4 terms; individual severity slopes are therefore not interpreted as
structural marginal damages.

## Independent validation and interpretation

Independent joint sparse-design validators reproduce drought-only slopes
within `1.45e-11`. Weather/state-robustness validators reproduce full designs
and sentinel deletions within `1.29e-08`, and state covariance entries within
`4.76e-10`. All source identities, construction outputs, and validation
receipts are hash-bound in `data/provenance/`; raw archives remain ignored.

The finding is narrow but useful: at approximately 4 km, whole-county versus
agricultural-area weighting and cultivated versus broad agricultural masks do
not materially alter the U.S. historical conclusions. It does not establish
causality or provide the missing climate-to-drought link. A predeclared
multi-resolution sentinel audit (3.96 km versus about 1 km and native 30 m)
remains necessary before calling the spatial approximation resolved. No
coefficient in this analysis is authorized for global transfer, damage
monetization, or SCC calculation.
