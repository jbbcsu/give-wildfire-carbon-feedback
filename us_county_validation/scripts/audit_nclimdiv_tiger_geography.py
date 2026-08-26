#!/usr/bin/env python3
"""Audit naive NOAA internal-state/county keys against a Census county vintage."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import shapefile

from extract_nclimdiv_county_pdsi import INTERNAL_STATE_TO_CENSUS


def nclimdiv_geoids(path: Path) -> set[str]:
    internal: set[str] = set()
    with path.open("r", encoding="ascii", newline="") as stream:
        for raw in stream:
            if not raw.endswith("\n") or len(raw) != 99:
                raise ValueError("nClimDiv input differs from the exact fixed-width contract")
            key = raw[:5]
            if key[:2] not in INTERNAL_STATE_TO_CENSUS or not key[2:].isdigit():
                raise ValueError(f"nClimDiv has an unknown internal county key {key}")
            internal.add(key)
    return {INTERNAL_STATE_TO_CENSUS[key[:2]][0] + key[2:] for key in internal}


def tiger_geoids(path: Path) -> set[str]:
    reader = shapefile.Reader(str(path))
    fields = [field[0] for field in reader.fields[1:]]
    if not {"GEOID", "STATEFP"} <= set(fields):
        raise ValueError("TIGER county shapefile lacks GEOID/STATEFP")
    geoid_position, state_position = fields.index("GEOID"), fields.index("STATEFP")
    conus_states = {value[0] for value in INTERNAL_STATE_TO_CENSUS.values()}
    result = {
        str(record[geoid_position])
        for record in reader.records()
        if str(record[state_position]) in conus_states
    }
    if any(len(value) != 5 or not value.isdigit() for value in result):
        raise ValueError("TIGER county inventory contains malformed GEOIDs")
    return result


def audit(nclimdiv_path: Path, tiger_path: Path) -> dict[str, object]:
    pdsi = nclimdiv_geoids(nclimdiv_path)
    census = tiger_geoids(tiger_path)
    return {
        "status": "requires_explicit_crosswalk" if pdsi != census else "exact_geography_match",
        "nclimdiv_transformed_key_count": len(pdsi),
        "tiger_conus_key_count": len(census),
        "exact_key_intersection_count": len(pdsi & census),
        "nclimdiv_only_transformed_geoids": sorted(pdsi - census),
        "tiger_only_geoids": sorted(census - pdsi),
        "full_panel_extraction_authorized": pdsi == census,
        "rule": "Do not guess unmatched keys; require an authoritative crosswalk or exclude them with a reported support loss.",
        "causal_claim_authorized": False,
        "scc_claim_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nclimdiv", required=True)
    parser.add_argument("--tiger-shapefile", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = audit(Path(args.nclimdiv), Path(args.tiger_shapefile))
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"nClimDiv/TIGER geography: intersection={result['exact_key_intersection_count']}; "
        f"nClimDiv-only={result['nclimdiv_only_transformed_geoids']}; "
        f"TIGER-only={result['tiger_only_geoids']}; "
        f"full-panel-authorized={str(result['full_panel_extraction_authorized']).lower()}"
    )


if __name__ == "__main__":
    main()
