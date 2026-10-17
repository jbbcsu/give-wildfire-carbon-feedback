# Natural wetland methane feedback for GIVE

This isolated project audits a climate-to-natural-wetland-CH4 feedback upstream of GIVE damages. It excludes anthropogenic methane, rice agriculture, landfills, fossil methane, permafrost, freshwater systems, and wildfire.

## Decision

**Readiness benchmark only; no GIVE SCC and no scalar adjustment.** GIVE's FaIR 1.6.2 implementation already has separate fossil and natural methane inputs. The natural series is 168.8386206 Mt CH4/year in every year from 2015 through 2300, so it includes an absolute natural baseline but no future climate response.

Sloughter et al. (2026) implement a peer-reviewed MAGICC v7.6 feedback in which natural wetland methane is linear in GMST. Their uncertainty distribution has mean 30 and standard deviation 13 Mt CH4/year/K, calibrated against Zhang et al. (2017) and Kleinen et al. (2021). This is the shortest defensible reduced-form benchmark, but it uses GMST as a proxy for precipitation, inundation, wetland area, and other processes.

Production coupling is blocked because GIVE currently sets the methane fossil fraction to one for oxidation bookkeeping; feeding additional biogenic methane through that structure would spuriously treat oxidized wetland methane as fossil carbon. The absolute-emissions intercept, 2015 anchoring, methane lifetime calibration, and same-draw recursive pulse comparison also require validation.

## Reproduce the audit

```bash
python3 scripts/audit_readiness.py
python3 scripts/validate_contract.py
python3 -m unittest discover -s tests
```

The scripts produce audit receipts and no climate, damage, or SCC result.

