# Heat morbidity integration audit for GIVE

This isolated project audits nonfatal, temperature-sensitive health morbidity while excluding mortality, air pollution, infectious disease, wildfire smoke, labor productivity, and lost wages.

**Result: fail closed. No morbidity SCC is estimated.** GIVE does not contain a distinct morbidity module. Two strong published candidates establish material effects, but neither currently exposes all inputs needed for a matched marginal CO2 pulse:

- Lay et al. (2018) provide multi-city U.S. projections and separable direct medical expenditures for hyperthermia emergency-department visits, but not executable fitted MSA response objects.
- Gould et al. (2025) provide modern temperature-bin estimates and projections for California ED visits and hospital admissions. Their Zenodo record provides code and nonprivate climate inputs, but the encounter records needed to estimate the response are restricted, and no medical-cost valuation is supplied.

The four Lay et al. published scenario/year observations are transcribed solely as an evidence benchmark. They must not be interpolated into an SCC.

```bash
python3 scripts/finalize_contract.py
python3 scripts/validate_contract.py
python3 -m unittest discover -s tests -v
```

See `docs/LITERATURE_AND_INTEGRATION_AUDIT.md` for the evidence hierarchy, overlap gates, and executable next step.
