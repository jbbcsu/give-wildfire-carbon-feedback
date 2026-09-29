# Sorghum/cotton all-practice outcome benchmark results

## Result

The paired direct-practice outcomes are highly coherent with the same-source
NASS all-production-practice yield series, but they are selected regional
samples and become much more selected after 2007. This strengthens confidence
that the paired yield values are internally consistent while reinforcing that
the null predictive gates cannot be interpreted as national crop-response
tests.

| Crop | Positive all-practice county-years | Paired direct-practice county-years | Benchmark matches | Paired share of all-practice universe | All-practice states / paired states | Rounding-tolerant bracket share | Gates |
|---|---:|---:|---:|---:|---:|---:|---|
| Sorghum grain | 25,025 | 5,226 | 5,225 | 20.88% | 24 / 6 | 99.79% | Support pass; bracket pass |
| Upland cotton | 16,596 | 3,501 | 3,501 | 21.10% | 18 / 6 | 99.94% | Support pass; bracket pass |

The support gate requires an all-practice match for at least 90% of direct
pairs. It passes at 99.98% for sorghum and 100% for cotton. The prespecified
numeric-coherence gate requires at least 95% of matched all-practice yields to
fall between the two reported practice yields after a small rounding
tolerance. It also passes decisively.

## Selection and time support

The paired samples cover only about one fifth of all positive county-year
records overall and omit most states in the all-practice universe:

- Sorghum pairs occur in Colorado, Kansas, Nebraska, New Mexico, Oklahoma, and
  Texas. Eighteen of 24 all-practice states are absent.
- Cotton pairs occur in Arkansas, Louisiana, Mississippi, New Mexico,
  Oklahoma, and Texas. Twelve of 18 all-practice states are absent.

Selection intensifies in the frozen 2008--2018 terminal period:

| Crop | 1981--2007 paired / all-practice | 2008--2018 paired / all-practice | Terminal annual coverage range |
|---|---:|---:|---:|
| Sorghum grain | 5,048 / 22,729 (22.21%) | 178 / 2,296 (7.75%) | 1.57%--12.50% |
| Upland cotton | 3,037 / 13,171 (23.06%) | 464 / 3,425 (13.55%) | 5.00%--21.07% |

This support contraction is an identification/readiness limitation, not a
failed data-integrity check. It provides a concrete reason to retain the
strict geographic and terminal predictive gates and to resist extrapolating
either crop's null result to national production.

## Yield coherence

For sorghum, 5,214 of 5,225 matched all-practice yields lie exactly within the
reported irrigated/non-irrigated interval. Eleven lie below it, none above;
the maximum outside distance is 15.2 bu/acre. For cotton, 3,499 of 3,501 lie
within the exact interval, with one below and one above; the maximum outside
distance is 4 lb/acre. The small prespecified rounding allowance does not
change these counts, but both crops remain far above the 95% gate.

The rare interval violations remain visible and are not deleted or used to
tune any model. The audit does not have practice acreage weights and therefore
does not attempt to reconstruct the all-practice yield arithmetically.

## Boundary and consequence

This was the highest-value next U.S. validation step because it tests outcome
support and same-source coherence without fitting another exploratory weather
response. No weather or drought index was read. Direct-weather and PDSI/SPEI
families remain mutually exclusive, practices remain separate, and no
coefficient or row prediction is released.

The source outcome is ready for continued historical robustness work, but the
sample-selection evidence keeps national-representativeness, causal,
irrigation-treatment, future/global transfer, damage, and SCC gates closed.
Given the already-null predictive promotions, another flexible sorghum/cotton
fit is not warranted by this audit.

## Validation and resources

The independent validator reparsed all 76 hash-bound raw responses, all 46,409
API rows, and all 41,621 positive coded all-practice rows. It independently
reconstructed every crop, year, state, overlap, interval, and gate aggregate
exactly and verified that the locally loaded credential occurs in neither
tracked receipt.

- Acquisition peak RSS: 58,703,872 bytes.
- Production audit peak RSS: 149,159,936 bytes.
- Independent validation peak RSS: 146,915,328 bytes.
- All runs remained below 512 MiB.

## Artifacts

- Protocol: `US_SORGHUM_COTTON_ALL_PRACTICE_BENCHMARK_PROTOCOL_20260928.md`
- Acquisition implementation:
  `us_county_validation/scripts/acquire_nass_sorghum_cotton_all_practice_benchmark.py`
- Credential-free acquisition receipt:
  `data/provenance/nass_sorghum_cotton_all_practice_acquisition_20260928.json`
- Audit implementation:
  `us_county_validation/scripts/audit_nass_sorghum_cotton_all_practice_benchmark.py`
- Audit result:
  `data/provenance/nass_sorghum_cotton_all_practice_benchmark_audit_20260928.json`
- Independent validator:
  `us_county_validation/scripts/validate_nass_sorghum_cotton_all_practice_benchmark.py`
- Validation result:
  `data/provenance/nass_sorghum_cotton_all_practice_benchmark_validation_20260928.json`
- Raw benchmark JSON remains ignored under
  `data/raw/us_county/nass_api/sorghum_cotton_all_practice_benchmark_1981_2018/`.
