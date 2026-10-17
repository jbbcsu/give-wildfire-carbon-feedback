# Terrestrial and freshwater ecosystem-service damages

This isolated project audits ecosystem and biodiversity omissions in GIVE and implements the strongest bounded, open benchmark that passed the initial evidence gate: the CONUS freshwater-quality recreational welfare response in EPA FrEDI v4.1.1.

The benchmark values climate-driven changes in freshwater quality through user and nonuser willingness to pay. It is not agriculture, commercial forestry, marine fisheries, coral services, municipal water supply, or health damages. It is also not a global estimate.

Run:

```bash
python3 scripts/acquire_pinned_fredi_runtime.py
python3 scripts/run_water_quality_partial_scc.py
python3 scripts/validate_water_quality_partial_scc.py
python3 -m unittest discover -s tests -v
```

The runtime can be reacquired with `--download-missing`. Raw FrEDI data are ignored. All reported results use matched GIVE baseline/pulse temperatures, official FrEDI response functions, official population scaling, 2015-to-2020 GDP-deflator conversion, and GIVE's 2% Ramsey discount path.

## Claim boundary

The result is a **CONUS-only freshwater recreation willingness-to-pay partial SCC benchmark**. The configuration prohibits global extrapolation and addition to a combined GIVE SCC until cross-sector overlap—especially freshwater fishing, biodiversity nonuse, and municipal water—is resolved.

The current five-GCM mean is `$0.01668/tCO2` in 2020 USD, with a range of `$0.01283-$0.02184/tCO2`. See `results/WATER_QUALITY_CONUS_PARTIAL_SCC_V1.md` for interpretation and omissions.
