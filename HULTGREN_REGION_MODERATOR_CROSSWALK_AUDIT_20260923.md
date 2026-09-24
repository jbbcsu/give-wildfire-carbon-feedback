# Hultgren region/moderator crosswalk audit

Date: 2026-09-23

## Question

Can the region-level moderators in the recovered published maize regression panel be joined directly by administrative names to the authors' public future-impact-region hierarchy?

## Result

No, not at defensible global coverage. Exact normalized matching within ISO country, parent administrative name (including listed alternatives), and terminal administrative name gives one unique author-region match for 3,255 of 13,171 panel UIDs (24.71%). It uniquely matches 32.75% of panel rows. Among observations with nonmissing harvested area, matched rows contain 4.23% of the recorded area.

One UID is ambiguous and 9,915 are unmatched. The U.S. is an important exception: 99.9% of its panel rows match uniquely by this rule, although its `area_harv` field is missing and therefore does not contribute to the area statistic. Coverage is very low in several large non-U.S. panels, including Brazil, China, India, and Mexico.

The moderator values (`irrigated_share`, long-run precipitation, long-run temperature, and log GDP per capita) are constant within each panel UID, so moderator instability is not the failure. The failure is the spatial crosswalk.

## Interpretation

The author hierarchy describes agglomerated impact regions. Its terminal label is not a complete list of every source administrative unit absorbed into an agglomeration. Consequently, fuzzy name matching would create undocumented and potentially consequential global assignments. This route is rejected for the global transport unless the full membership crosswalk is recovered.

This does not block grid-weather construction. It does block the shortcut of attaching the historical panel moderators directly to all public impact-region polygons.

## Defensible routes forward

1. Request the complete source-unit/GADM-to-`hierid` agglomeration membership table from the authors. The unsent data request now names this object explicitly.
2. In parallel, build the moderators directly on the public impact-region geometry: fixed MIRCA rainfed/irrigated shares, baseline gridded crop-weather climatologies, and an explicitly chosen GDP-per-capita spatial/scenario convention. Each substitute must be labeled as alternative-product transport and subjected to sensitivity analysis.
3. Use the nearly complete U.S. exact-name linkage as a validation subset, not as evidence that the global linkage is complete.

No response, yield change, monetary damage, or SCC estimate is authorized by this audit.

The machine-readable receipt is `data/provenance/hultgren_region_moderator_crosswalk_audit_20260923.json` and the implementation is `scripts/audit_hultgren_region_moderator_crosswalk.py`.
