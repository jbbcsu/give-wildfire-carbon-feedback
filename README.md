# Top-down macroeconomic damage comparator

This isolated project source-pins a leading published top-down global macroeconomic SCC as a **mutually exclusive comparison** to GIVE and the expanded bottom-up sector modules. It is not added to sector totals and is not interpreted as an estimate of “missing sectors.”

The selected primary result is Bilal and Känzig (2026), *Quarterly Journal of Economics*, DOI `10.1093/qje/qjag011`. Their open replication table reports a central global-temperature SCC of **1,206.97 in 2024 international dollars per tCO2**, with a paper-reported 95% confidence interval of **399–2,015**. The same framework reports 148.94 using local rather than global temperature and 1,519.63 in the longer Barro-Ursúa sample, illustrating major structural/specification sensitivity.

```bash
python3 scripts/build_comparator.py
python3 scripts/validate_comparator.py
python3 -m unittest discover -s tests -v
```

No re-estimation, currency conversion, or GIVE harmonization is performed. See `docs/LITERATURE_AND_OVERLAP_AUDIT.md`.
