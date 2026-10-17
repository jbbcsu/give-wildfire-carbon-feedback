# Labor-productivity fast-track release

Status date: 17 October 2026.

## Result

The labor contribution is ready as a GIVE-compatible **partial SCC mean** under
the frozen Moore et al. (2026) setup: 2025 CO2 pulse, RFF-SP socioeconomic
paths, the paper's 2% Ramsey discount schedule, and 2020 USD. Two independently
reproduced 10,000-draw runs give:

| Published response specification | Labor partial SCC mean (2020 USD/tCO2) | Monte Carlo SE | Within-case 5th–95th percentile |
|---|---:|---:|---:|
| Lancet | 29.2638 | 0.2266 | 0.1875–70.7842 |
| ISO | 51.8647 | 0.4442 | 1.0421–133.8827 |
| Equal-weight mean of case means | **40.5643** | not pooled | not pooled |

The arithmetic mean is the transparent structural central estimate and rounds
to the article's reported $41/tCO2. The range of structural case means is
$29.26–$51.86/tCO2. The two sets of quantiles and Monte Carlo standard errors
are retained separately; averaging them would not yield a valid mixture
distribution.

## Fast integration rule

This release transfers only the labor partial SCC. It can be added to a target
GIVE expected SCC when the target uses the same pulse year, currency,
discounting, and RFF-SP setup and an audit confirms that no labor-productivity
sector is already active. It does not transfer the source model's total or
updated-agriculture SCC. A combined uncertainty distribution requires retained
joint draws or a newly specified coupling and is not claimed here.

This is a reproduction and transfer of published response functions, not a new
causal labor-response estimate. The implementation is from the authors'
MIT-licensed archive (Zenodo DOI 10.5281/zenodo.21483095); the article DOI is
10.1038/s41558-026-02749-z.

## Reproduce the release artifact

```sh
python3 -m unittest test/test_labor_fasttrack_release.py
python3 scripts/build_labor_fasttrack_release.py \
  --output-json data/provenance/labor_fasttrack_release_20261017.json \
  --output-csv output/labor_fasttrack_release_20261017.csv
```

Both input receipts are hash-bound. The builder fails closed if a receipt,
model invariant, sector boundary, or uncertainty-pooling rule changes.
