# Multicrop rainfed precipitation-distribution diagnostic (2026-09-25)

## Result

This bounded diagnostic compares seasonal precipitation quantity with five within-season distribution extensions for rainfed maize, first rice, second rice, soybean, spring wheat, and winter wheat. It uses 368,022 positive observed GDHY crop-grid-year outcomes (1982–1989), producing 321,620 consecutive-year first differences and 126 model/holdout results.

The calculation is a held-out predictive screen only. It does **not** estimate causal rainfall effects, geographic or economic winners and losers, damage functions, response draws, or an SCC input.

| Crop | Holdout | Seasonal-quantity RMSE | Best distribution RMSE | Improvement | Descriptive best extension |
|---|---:|---:|---:|---:|---|
| Maize | spatial | 0.295892 | 0.294825 | 0.001067 | all distribution |
| Maize | temporal | 0.309293 | 0.308079 | 0.001213 | all distribution |
| Maize | wet-tail | 0.302010 | 0.300454 | 0.001556 | all distribution |
| First rice | spatial | 0.225631 | 0.224830 | 0.000802 | occurrence/intensity |
| First rice | temporal | 0.223234 | 0.223097 | 0.000137 | timing/concentration |
| First rice | wet-tail | 0.229302 | 0.228982 | 0.000320 | wet extremes |
| Second rice | spatial | 0.272957 | 0.271741 | 0.001216 | all distribution |
| Second rice | temporal | 0.274780 | 0.274051 | 0.000729 | occurrence/intensity |
| Second rice | wet-tail | 0.279842 | 0.279571 | 0.000272 | dry spells |
| Soybean | spatial | 0.223984 | 0.221409 | 0.002575 | all distribution |
| Soybean | temporal | 0.265686 | 0.264826 | 0.000860 | timing/concentration |
| Soybean | wet-tail | 0.223650 | 0.221719 | 0.001932 | all distribution |
| Spring wheat | spatial | 0.380096 | 0.375375 | 0.004721 | all distribution |
| Spring wheat | temporal | 0.363316 | 0.360137 | 0.003179 | dry spells |
| Spring wheat | wet-tail | 0.385776 | 0.382728 | 0.003048 | occurrence/intensity |
| Winter wheat | spatial | 0.293849 | 0.292938 | 0.000911 | occurrence/intensity |
| Winter wheat | temporal | 0.306405 | 0.303103 | 0.003302 | all distribution |
| Winter wheat | wet-tail | 0.301264 | 0.300842 | 0.000422 | occurrence/intensity |

The post-hoc best of five distribution extensions beats seasonal quantity in all 18 crop/holdout cells, but this is not a preregistered selection result and has no paired uncertainty or multiplicity correction. A fixed extension improves seasonal quantity in every holdout only for:

- maize: all five registered extensions;
- spring wheat: dry spells;
- winter wheat: occurrence/intensity and the full distribution model.

There is no all-holdout fixed-extension winner for either rice season or soybean. First-rice temporal RMSE is lower for temperature controls alone (0.223019) than for seasonal quantity (0.223234) or the best distribution extension (0.223097). For second rice, seasonal quantity is worse than zero-change in the spatial and temporal holdouts; the descriptive best distribution model only narrowly clears zero-change. These checks prevent interpreting the positive post-hoc comparison count as a universal precipitation-response result.

## Design and gates

- Models: temperature controls; seasonal quantity; quantity plus timing/concentration, occurrence/intensity, dry spells, wet extremes, or all distribution features.
- Within-season windows: 0–30%, 30–70%, and 70–100% of the crop calendar. These are temporal proxies, not observed phenological stages.
- Holdouts: five 5-degree spatial folds, the final two years, and the retrospective union of crop-specific 95th-percentile CDD/Rx1 climate extremes.
- Spatial labels are inherited and hash-locked from the existing `precipitation-scc-v1` validation panels. The reused label seed differs from the distribution specification's nominal `precipitation-distribution-diagnostic-v1` seed; therefore this is an audit of the existing folds, not a newly seeded fold assignment.
- Temporal and wet-tail training pairs are purged when either yield endpoint appears in the test set. Every recorded endpoint-overlap count is zero.
- The wet-tail test is a broad retrospective stress screen, not external rare-event validation.
- Source outcomes are GDHY modeled yields and the exposure basis is a rainfed calendar proxy over only 1982–1989.
- Coefficients are never exported. Causal interpretation, production selection, response-draw export, and SCC use are all false.
- Maximum reported worker RSS is 492,912,640 bytes (470.1 MiB), below the 512 MiB cap. A fresh validator recomputation peaked at 493,436,928 bytes and matched all non-runtime fields.

## Artifacts and reproduction

- Contract: `config/multicrop_rainfed_distribution_diagnostic_v1.lock.toml`
- Evaluator: `scripts/evaluate_multicrop_rainfed_distribution_diagnostic.py`
- Validator: `scripts/validate_multicrop_rainfed_distribution_diagnostic.py`
- Regression check: `scripts/test_multicrop_rainfed_distribution_diagnostic.py`
- Full result: `data/provenance/multicrop_rainfed_distribution_diagnostic_20260925.json`
- Validation receipt: `data/provenance/multicrop_rainfed_distribution_diagnostic_validation_20260925.json`

```bash
./.venv/bin/python scripts/test_multicrop_rainfed_distribution_diagnostic.py
./.venv/bin/python scripts/evaluate_multicrop_rainfed_distribution_diagnostic.py \
  --out data/provenance/multicrop_rainfed_distribution_diagnostic_20260925.json
./.venv/bin/python scripts/validate_multicrop_rainfed_distribution_diagnostic.py \
  data/provenance/multicrop_rainfed_distribution_diagnostic_20260925.json \
  --out data/provenance/multicrop_rainfed_distribution_diagnostic_validation_20260925.json
```

## Promotion gate

This result supports continuing distribution-aware work, especially dry-spell structure for spring wheat and occurrence/intensity for winter wheat. It does not support promotion to a global yield-response function. The next gate is a predeclared, externally validated causal or quasi-causal response specification with real crop phenology, broader years/outcomes, paired uncertainty, and geographic effect heterogeneity. Only after that can crop-area/value aggregation, economic winners/losers, marginal-CO2 forcing, GIVE damage propagation, discounting, and an SCC be defensibly attempted.
