# Permafrost carbon feedback for GIVE

This isolated project audits a temperature-to-permafrost-CO2/CH4 feedback that could be inserted upstream of GIVE damages, analogously to—but wholly separate from—the wildfire-carbon project.

## Decision

**Readiness scaffold only; no SCC and no scalar adjustment.** FaIR 1.6.2 in the published GIVE implementation has temperature-dependent carbon uptake but no explicit permafrost carbon stock or thaw-emissions component. An authoritative 2025 EPA/NCEE implementation also treats permafrost and Amazon carbon feedbacks as additions absent from FaIR 1.6.2. However, safe GIVE integration requires recursive baseline and pulse runs, explicit biogenic-methane routing, validation of parameter/artifact discrepancies, and proof that socioeconomic emissions pathways do not already contain the feedback.

The open, peer-reviewed PerCX v1.0.1 model is vendored under its Apache-2.0 license as the leading implementation candidate. It was coupled by its authors to FaIR 1.6.4 and constrained to AR6 permafrost response ranges. Vendoring is for audit and tests only; it does not authorize production coupling.

## Run

```bash
python3 scripts/audit_readiness.py
python3 scripts/validate_contract.py
python3 -m unittest discover -s tests
```

The scripts create a machine-readable readiness receipt and deliberately create no climate or SCC result.
