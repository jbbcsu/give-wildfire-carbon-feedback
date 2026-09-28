# Hultgren Rice2 response/application-domain audit — 2026-09-28

## Decision

The validated 1982–2019 Rice2 weather basis cannot yet be passed to the published pooled rice response source-faithfully. The weather primitives are ready; the blocking object is an unambiguous mapping from each Rice2 grid cell and season to the prepared author panel's estimation UID and its four moderators.

The gate remains fail-closed at **zero authorized response-application rows**. No coefficient was evaluated and no MIRCA weight, yield effect, damage, SCC, or GIVE input was constructed.

## What the author artifacts provide

The recovered prepared rice panel exactly reproduces the published estimation sample: 166,174 observations, 6,274 UIDs, 656 country-year clusters, and 581 ADM1 clusters. All four moderators are finite and constant within an estimation-sample UID:

| Required field | Pinned author value | Source-faithful grid status | Unauthorized substitute/choice |
|---|---:|---|---|
| `ln_gdppc` | Yes, verbatim by UID | No complete Rice2 cell-to-UID map | PWT country snapshots or spatial interpolation |
| `irrigated_share` | Yes, verbatim by UID | No complete Rice2 cell-to-UID map | Treating `ri2_noirr`/`ri2_firr` as 0/1 irrigation; the response moderator is a continuous UID share |
| `lr_tmax_crop` | Yes, verbatim by UID | No complete Rice2 cell-to-UID map | Recomputed GSWP climatology |
| `lr_prcp_crop` | Yes, verbatim by UID | No complete Rice2 cell-to-UID map | Recomputed GSWP climatology; author caps are 200 for GDD, 300 for KDD, 250 for precipitation, and 175 for Tmin |
| Season label | `total`, `first`, `second`, `third` | No authoritative GGCMI `ri2`-to-panel-series crosswalk | Treating the ordinal name `ri2` as proof that it is the panel's `second` series |
| Application geography | UID, ADM1, and country-year identifiers | Public impact hierarchy is not a direct UID membership table | Fuzzy names, dominant-region assignment, or partial-cell assignment |

The published fixed-effect architecture is UID effects, ADM1-specific linear and quadratic time trends, and country-year effects, with two-way clustering by ADM1 and country-year. Numerical fixed-effect levels are not required for a weather contrast holding moderators fixed; they would be required for transported level prediction or refitting, neither of which is authorized.

The estimation sample covers 1950–2010. Thus 179,713 Rice2 rows per branch lie in the 1982–2010 calendar overlap and 55,773 rows per branch (2011–2019) are temporally outside the historical estimation years. This is an extrapolation diagnostic, not permission to truncate or refit.

## Season and geography findings

The estimation sample contains:

- 6,089 `total` UIDs and 162,634 rows;
- 77 `first` UIDs and 1,560 rows;
- 56 `second` UIDs and 1,189 rows; and
- 52 `third` UIDs and 791 rows.

The 56 `second` UIDs occur only in Sri Lanka (25) and Vietnam (31). They are ADM1-level series. A terminal-region-only exact name crosswalk therefore finds none of them, while finding 336 unique UIDs overall—all `total` series.

The stronger diagnostic is promising but not complete: matching each `second` UID's ADM1 name or listed alternative against **any** node in the pinned author hierarchy gives exactly one hierarchy node for 43 UIDs (18 Sri Lanka, 25 Vietnam), no node for 10, and two nodes for 3. The hierarchy explicitly records each node's descendants, so those 43 unique parent matches are the bounded path to test next; they have not yet been expanded to terminal polygons or asserted equivalent to GGCMI Rice2.

## Exact strict-support coverage

Across the 6,197 strict Rice2 cells per branch:

| Gate | Cells | Fraction | 1982–2019 cell-years per branch |
|---|---:|---:|---:|
| Any positive-area author-region intersection | 6,197 | 100% | 235,486 |
| Exactly one author region covering the full cell | 669 | 10.7955% | 25,422 |
| Any terminal region linked to an exact estimation UID | 70 | 1.1296% | 2,660 |
| One distinct exact UID among intersecting terminal regions | 42 | 0.6777% | 1,596 |
| One full-cell region and one exact UID | 4 | 0.06455% | 152 |
| Above strict geography plus author `second` label | 0 | 0% | 0 |
| Above plus exact planting/harvest/length concordance | 0 | 0% | 0 |

All four of the strongest current geographic matches are author `total` series. Treating them as Rice2 would be a season-allocation modeling choice, so they remain unauthorized.

## Frozen fail-closed protocol

A Rice2 row may reach response evaluation only after all of these hold:

1. One source-reconstructed author estimation UID owns the cell; partial or competing region assignments are excluded.
2. The UID is explicitly the relevant seasonal reporting series. Name similarity between `ri2` and `second` is not sufficient by itself.
3. Author and GGCMI planting month, harvest month, and season length agree exactly under the validated reporting-year rule.
4. `ln_gdppc`, `irrigated_share`, `lr_tmax_crop`, and `lr_prcp_crop` are attached verbatim from that UID. No country proxy, climate recomputation, interpolation, or missing-value fill is allowed.
5. The published pooled coefficients remain fixed. Only weather contrasts at fixed moderators may be evaluated; no fixed-effect level prediction or refit is permitted.
6. Author-domain min/max and p01–p99 diagnostics are reported, not used silently for trimming or winsorization.

Current authorized count under this protocol: **0**.

## Single safest next computation

Expand the 43 uniquely matched `second`-season hierarchy parent nodes to their pinned descendant terminal polygons, intersect those polygons with the 6,197 strict Rice2 cells, and retain only cells having one UID plus exact author/GGCMI planting-month, harvest-month, and season-length concordance. Report attrition separately for Sri Lanka and Vietnam and leave all ambiguous, unmatched, partial-cell, and calendar-discordant cells excluded.

This is bounded, uses only resident pinned author hierarchy/geometry and the validated Rice2 calendar, and still does not evaluate coefficients. It directly tests whether a nonzero source-faithful Rice2 application subset exists.

## Validation and artifacts

- Contract: `config/hultgren_rice2_response_application_domain_v1.toml`
- Audit: `scripts/audit_hultgren_rice2_response_application_domain.py`
- Audit receipt: `data/provenance/hultgren_rice2_response_application_domain_audit_20260928.json`
- Independent validator: `scripts/validate_hultgren_rice2_response_application_domain.py`
- Validation receipt: `data/provenance/hultgren_rice2_response_application_domain_validation_20260928.json`

The audit peak RSS was 506,855,424 bytes and the independent validator peak RSS was 467,238,912 bytes, both below the 536,870,912-byte ceiling. The validator independently reproduced the 166,174-row estimation sample, 6,274 UIDs, terminal-link counts, 43/10/3 parent-node diagnostic, and all reported spatial coverage counts.

Claim gates remain closed for response evaluation, MIRCA weights, yield effects, damages, SCC, and GIVE integration.
