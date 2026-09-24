# FAO FishStat marine-tonnage source panel

## Result

The reconciled FAO FishStat Global Capture Production 1950--2024 export was
filtered to `environment_class = marine` and `measure_code = Q_tlw`. The
result contains 27,625 source records and 2,071,875 annual value/status pairs.
Every source field, status symbol, and row order is retained. The compressed
panel is 2,217,526 bytes with SHA-256
`7b3dcb8bfcd9b1857274c7972ef9d0ddfb62deec825b0ff7af1af26918b97ec4`.

An independent validator compared every output row and field with the exact
ordered subsequence of the reconciled 30,918-record headless export. Header,
field values, ordering, and the absence of extra rows all pass.

## Scientific boundary

This is an observed-source integrity result, not a climate-response estimate.
It does not select admissible observation statuses, treat missing or suppressed
values as zero, allocate vessel-flag landings to harvest EEZs or consumers,
calibrate FishMIP, value welfare, estimate damages, or calculate an SCC.

Country is primarily vessel flag, nominal landings exclude discards, and the
source does not identify effort, management, or climate causation. Those steps
remain separate preregistered gates.

## Reproduction

Run `scripts/build_fao_fishstat_marine_tonnage_panel.py` against the
checksum-pinned reconciled headless export, then run
`scripts/validate_fao_fishstat_marine_tonnage_panel.py`. The generated panel is
ignored by Git; its build and validation receipts are versioned under
`data/provenance/`.
