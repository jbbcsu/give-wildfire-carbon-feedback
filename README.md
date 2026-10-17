# Freshwater fisheries and recreational angling: GIVE audit

This isolated project evaluates a freshwater-fisheries endpoint beyond ocean fisheries and beyond the existing FrEDI freshwater-quality willingness-to-pay benchmark.

## Result

The audit identifies a credible U.S. consumer-surplus benchmark but **does not produce an SCC**. EPA's CIRA II freshwater-fish analysis links temperature and precipitation to stream temperature, streamflow, fish-guild habitat, angling days, and recreation value for the conterminous United States. Its published outputs are scenario/era changes, not annual matched baseline-versus-one-ton-pulse paths. Its angling service also overlaps the recreation bundle in FrEDI water quality. Those two gates prevent addition to GIVE.

The pinned CIRA II table is useful as an external magnitude and sign benchmark. It must not be divided by scenario emissions or interpreted as a marginal SCC.

## Reproduce the audit

```bash
python3 scripts/finalize_contract.py
python3 scripts/validate_contract.py
python3 -m unittest discover -s tests
```

No raw biological data, restricted information, or output labeled as an SCC is stored here.
