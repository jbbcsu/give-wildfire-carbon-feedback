# Complete published PEEPS MPI monthly rainfall input: acquisition result

This is a **source acquisition and structure validation result only**. No
agricultural yield, welfare, damages or SCC estimate is produced.

The preregistered transfer in `PUBLISHED_PEEPS_FULL_MONTH_PROTOCOL_20260917.md`
streamed the complete author PEEPS v1.1 `outputs.tar.gz` from
https://doi.org/10.5281/zenodo.7557622 **without saving the 3.2-GB
archive**. The exact received 3,244,457,764 bytes matched the published
Zenodo MD5 `eed1a0e8a43bf915c78ec68d0f37e357`. Only the twelve
`MPI-ESM1-2-HR_ssp585_pr_monthly_patterns_{jan,...,dec}.nc` files were
retained in ignored
`data/interim/peeps_author_mpi_ssp585_monthly_20260917/`, totaling
14,355,000 bytes (1,196,250 bytes each). Every selected file's SHA-256
is in `selected_months_receipt.json`; no unselected source data were
retained. The author license is CC BY 4.0.

The monitored one-worker transfer completed in 860.30 s, with sampled
peak group RSS 41,893,888 B and sampled new owned output 14,358,335 B.
The independent structure validator used peak 115,179,520 B. Both passed
the 512 MiB memory and 130 GiB free-disk rules; free disk remained about
133 GiB. All twelve files opened as NetCDF, shared the same native 192 by
384 MPI grid, had 73,728 finite slope and intercept values each, and
reported `source_id=MPI-ESM1-2-HR`, `experiment_id=ssp585`,
`variant_label=ensemble_avg`, `grid_label=gn`, `variable_id=pr`, and
`variable_units=kg m-2 s-1`. The full-source December SHA-256 exactly
matched the earlier independent partial-range December pilot,
`13e17ee549adfe109356b765cc25a50c2adc539399b95c09eeae73ec0b237699`.
The checks and per-month coefficient ranges are in
`all_month_structure_validation.json`.

These are **the authors' published coefficients**, not our separately
fitted PEEPS-style GFDL/IPSL response. They solve the immediate source-
access question without extra local storage. They do **not** resolve the
known negative-rainfall issue shown by the December crop-support probe,
the mapping between author absolute GMST and a matched GIVE/FAIR pulse,
within-month dry spells/extremes, monthly crop-calendar weighting, an
independent whole-scenario test, or global joint agricultural welfare
replacement. Those gates remain open before any SCC use.

Next: preregister and evaluate monthly amount/seasonality on crop-year
support against same-model climate reference. Contrast published linear
levels with a source-matched positive-baseline anomaly application without
silently clipping negatives. Keep daily dry-spell/extreme pathways anchored
to direct daily ISIMIP evidence, not the monthly PEEPS coefficients.
