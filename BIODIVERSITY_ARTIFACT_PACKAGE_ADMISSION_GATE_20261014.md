# Biodiversity nonuse artifact-package admission gate

## Result

The seven-part author request now has an executable, fail-closed import and
validation interface. It admits a candidate package for later source and
scientific review only when all seven artifact groups are present, licensed,
checksum-pinned, internally complete, and consistent with a nonuse/existence-
value-only accounting boundary.

Admission does not validate the publication result, estimate a coefficient
or damage function, normalize an emissions pulse, apply discounting,
calculate an SCC, or authorize inclusion in GIVE.

## Required package

The machine-readable contract is
`config/biodiversity_artifact_package_contract_v1.json`. A candidate
`package_manifest.json` must use schema
`biodiversity_nonuse_artifact_package_v1` and bind 17 distinct file roles to
the original seven request groups:

1. article source revision, Julia project/manifest, and run instructions;
2. all 16 regional valuation rows and their derivation;
3. 389 Urban groups, including the three explicitly censored all-extinct
   cases, plus 20,000 checksum-pinned `phi` draws and bootstrap documentation;
4. a complete one-to-one article country/ISO3/FUND-region mapping;
5. 10,000 joint socioeconomic, climate, response, valuation, and discount
   draw links plus the dependence method;
6. an explicit unnormalized, undiscounted CO2 pulse manifest and matched
   annual country and global baseline/pulse outputs; and
7. exact checksums, resolved license terms, and the nonuse boundary record.

Every artifact group must reference a license that explicitly permits
redistribution, derivative use, and GIVE research use. Blank or unresolved
terms, nonempty third-party restrictions, missing files, checksum drift,
symlinks, and path traversal fail closed.

## Scientific and accounting checks

The importer requires exact CSV headers and rejects implicit missingness. It
validates the 16-region coefficient table, Urban censor semantics, bootstrap
draw IDs and seed, complete mapping, and every joint-draw reference. Annual
rows must form the full declared run-country-year rectangle and be ordered as
adjacent baseline/pulse pairs. Fixed inputs must match within each pair, and
all dynamic fields must be identical before the declared first-divergence
year.

For every row, the validator independently recomputes the climate deficit and
annual country nonuse damage with the existing tested reference equations.
It then streams country sums by run, year, and path role against the supplied
global rows. The streamed design avoids loading the annual output cube into
memory. Discount factors are checked as matched metadata but never applied.

The allowed boundary includes only nonuse/existence value. Agriculture,
fisheries and aquaculture, reef tourism/recreation, coastal protection,
carbon-cycle feedbacks, hunting/subsistence, commercial harvest, other
recreation, and all other market or use services must be explicitly excluded.
No allocation, imputation, or renormalization is allowed.

## Current public evidence

The prior official-source audit at MimiGIVE commit
`abf0b6feab1ca246cfe41ac205a65d292851c281` remains a negative control. Its
554 tracked files passed the pinned hash checks, but the scoped search found
no public biodiversity/nonuse component. Therefore zero of the seven required
artifact groups is available from that public release. The gate rejects it as
incomplete; it does not infer that no private or differently named artifact
exists.

The machine-readable rejection, containing only source pins and categorical
missing-artifact results, is
`data/provenance/biodiversity_public_evidence_artifact_admission_20261014.json`.
The approximate published benchmark is neither imported nor used as a
calibration target.

## Commands

Validate a future package:

```bash
python3 python/validate_biodiversity_artifact_package.py package \
  /path/to/package/package_manifest.json
```

Reproduce the public-evidence rejection:

```bash
python3 python/validate_biodiversity_artifact_package.py public-evidence
```

Run focused synthetic tests:

```bash
python3 test/test_validate_biodiversity_artifact_package.py -v
```

The passing synthetic fixture contains the contract-specified 16 regions,
389 Urban groups, three censored cases, 20,000 response draws, 10,000 joint
draws, and a complete matched annual pair. Focused failures cover unresolved
license, missing artifact group, incomplete valuation regions, invalid climate
censoring, incomplete mapping, unknown joint response draw, pulse-unit drift,
unmatched paths, nonadditive global output, overlap leakage, and checksum
drift. Synthetic values provide no empirical or SCC claim.

## Remaining blocker

No real package is present locally. The regional coefficients and their
derivation, response calibration and joint draws, article mapping, matched
annual baseline/pulse outputs, executable source/environment, and applicable
licenses and boundary statement must still be obtained from the authors or a
new official release. Until a real delivery passes this gate and subsequent
scientific reproduction, the biodiversity GIVE component remains unavailable.
