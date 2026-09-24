#!/usr/bin/env python3
"""Audit name-based linkage of published maize moderators to author regions."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODERATORS = ["irrigated_share", "lr_prcp_crop", "lr_tmax_crop", "ln_gdppc"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def normalized(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def names(name: object, alternatives: object) -> set[str]:
    values = {normalized(name)}
    if pd.notna(alternatives):
        values.update(normalized(value) for value in str(alternatives).split("|") if value)
    return values - {"", "nan"}


def example_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    records = []
    for row in frame.head(50).itertuples(index=False):
        records.append({
            "uid": int(row.uid), "iso": row.iso, "adm1": row.adm1, "adm2": row.adm2,
            "candidate_count": int(row.candidate_count),
            "region_key": row.region_key if pd.notna(row.region_key) else None,
            "area_harv": float(row.area_harv) if pd.notna(row.area_harv) else None,
        })
    return records


def json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--hierarchy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh audit output required")

    columns = ["iso", "adm1", "adm2", "uid", "area_harv", *MODERATORS]
    panel = pd.read_stata(args.panel, columns=columns, convert_categoricals=False)
    variation = panel.groupby("uid", sort=False)[MODERATORS].nunique(dropna=False).max()
    if (variation > 1).any():
        raise ValueError(f"moderators vary within uid: {variation[variation > 1].to_dict()}")
    regions = panel.drop_duplicates("uid").copy()
    hierarchy = pd.read_csv(args.hierarchy, comment="#", dtype={"region-key": str, "parent-key": str})
    parent = hierarchy[["region-key", "name", "alternatives"]].rename(
        columns={"region-key": "parent-key", "name": "parent_name", "alternatives": "parent_alternatives"}
    )
    terminal = hierarchy[hierarchy.is_terminal.eq(True)].merge(parent, on="parent-key", how="left", validate="many_to_one")
    terminal = terminal.rename(columns={"region-key": "region_key"})
    terminal["iso"] = terminal.region_key.str.split(".").str[0]

    lookup: dict[tuple[str, str, str], list[str]] = {}
    for row in terminal.itertuples(index=False):
        for adm1_name in names(row.parent_name, row.parent_alternatives):
            for adm2_name in names(row.name, row.alternatives):
                lookup.setdefault((row.iso, adm1_name, adm2_name), []).append(row.region_key)

    records = []
    for row in regions.itertuples(index=False):
        candidates = sorted(set(lookup.get((row.iso, normalized(row.adm1), normalized(row.adm2)), [])))
        records.append({
            "uid": int(row.uid), "iso": row.iso, "adm1": row.adm1, "adm2": row.adm2,
            "candidate_count": len(candidates), "region_key": candidates[0] if len(candidates) == 1 else None,
            "area_harv": float(row.area_harv) if pd.notna(row.area_harv) else None,
        })
    matches = pd.DataFrame(records)
    region_status = matches.candidate_count.value_counts().sort_index().to_dict()
    row_match = panel.uid.map(matches.set_index("uid").candidate_count).eq(1)
    area = panel.area_harv.fillna(0.0).clip(lower=0.0)
    panel_status = panel.assign(unique_match=row_match, nonnegative_area=area)
    country = panel_status.groupby("iso", sort=True).apply(
        lambda group: pd.Series({
            "rows": len(group),
            "unique_uid": group.uid.nunique(),
            "row_unique_match_fraction": group.unique_match.mean(),
            "harvest_area_unique_match_fraction_among_nonmissing_area": (
                group.loc[group.unique_match, "nonnegative_area"].sum() / group.nonnegative_area.sum()
                if group.nonnegative_area.sum() else None
            ),
        }),
        include_groups=False,
    ).reset_index()
    result = {
        "schema": "hultgren_region_moderator_crosswalk_audit/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "name_crosswalk_audit_not_yet_authorized_for_response_transport",
        "sources": {
            "historical_ready_panel": {"path": str(args.panel), "bytes": args.panel.stat().st_size, "sha256": digest(args.panel)},
            "author_hierarchy": {"path": str(args.hierarchy), "bytes": args.hierarchy.stat().st_size, "sha256": digest(args.hierarchy)},
        },
        "panel": {"rows": len(panel), "unique_uid": int(panel.uid.nunique()), "countries": int(panel.iso.nunique())},
        "hierarchy": {"terminal_regions": len(terminal), "countries": int(terminal.iso.nunique())},
        "moderators_constant_within_uid": True,
        "unique_region_status_by_candidate_count": {str(key): int(value) for key, value in region_status.items()},
        "unique_region_match_fraction": float((matches.candidate_count == 1).mean()),
        "panel_row_unique_match_fraction": float(row_match.mean()),
        "harvest_area_nonmissing_rows": int(panel.area_harv.notna().sum()),
        "harvest_area_unique_match_fraction_among_nonmissing_area": float(area[row_match].sum() / area.sum()) if area.sum() else None,
        "country_coverage": country.to_dict(orient="records"),
        "unmatched_examples": example_records(matches[matches.candidate_count.eq(0)]),
        "ambiguous_examples": example_records(matches[matches.candidate_count.gt(1)]),
        "interpretation": "Only exact normalized author names/alternatives within ISO and parent administrative unit are tested. Unmatched or ambiguous regions require explicit crosswalk remediation; no fuzzy match is silently accepted.",
        "claim_gates": {
            "crosswalk_complete": bool((matches.candidate_count == 1).all()),
            "future_response_authorized": False,
            "damage_or_scc_authorized": False,
        },
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = json_ready(result)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "unique_region_status_by_candidate_count", "unique_region_match_fraction", "panel_row_unique_match_fraction", "harvest_area_unique_match_fraction_among_nonmissing_area")}, indent=2))


if __name__ == "__main__":
    main()
