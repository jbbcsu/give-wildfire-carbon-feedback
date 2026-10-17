# Climate-sensitive infectious disease in GIVE

This isolated project evaluates whether published climate–infectious-disease evidence can support a new GIVE damage component without overlapping GIVE's temperature mortality, coastal mortality, air-pollution mortality, labor, or other sector modules.

The primary bridge is the peer-reviewed dengue temperature response in Childs et al. (2025), covering 21 countries in the Americas and Asia. The repository pins and audits the authors' open analysis code. It does **not** yet report a dengue SCC: the public source does not contain a ready marginal-CO2 pulse calculation, monetization layer, or global coverage.

## Current status

- Existing GIVE coverage has been audited: the core health module is temperature-driven all-cause mortality; CIAM separately values coastal-storm mortality. Infectious-disease morbidity is absent.
- The Childs et al. estimator and projection code are pinned at commit `cd8e354df0291a930d489ef1171b448112476c7b` and verified by SHA-256.
- The allowed first endpoint is nonfatal dengue morbidity. Deaths and lost wages remain closed until overlap with all-cause mortality and labor productivity is resolved.
- A machine-readable claim gate prevents production of an additive SCC before coverage, matched pulse, valuation, overlap, and independent validation gates pass.

## Reproduce the audit

Requires Python 3.9+ and no third-party packages.

```bash
python3 scripts/audit_infectious_disease_readiness.py
python3 -m unittest discover -s tests -v
```

To recover missing small upstream source files from the exact commit:

```bash
python3 scripts/acquire_pinned_sources.py --download-missing
```

The 5.5 GB Zenodo archive is deliberately not downloaded by these commands. The upstream projection workflow itself warns that 25 bootstrap projections can require roughly 75 GB of memory; full execution therefore requires a separately approved, bounded HPC workflow.

## Key documents

- `INFECTIOUS_DISEASE_GIVE_READINESS_20261017.md`: coverage audit, evidence assessment, overlap boundary, and exact next steps.
- `config/infectious_disease_readiness_v1.json`: executable claim gates and target definition.
- `contracts/dengue_marginal_pulse_contract_v1.csv`: header-only data interface; it contains no fabricated observations.
- `provenance/source_manifest_v1.json`: immutable source hashes, licenses, and citations.

## Claim boundary

This is a readiness scaffold and published-response benchmark, not an SCC result. No synthetic epidemiological observations, coefficients, projected cases, or damages are included.

