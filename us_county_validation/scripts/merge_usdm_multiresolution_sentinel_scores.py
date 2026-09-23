#!/usr/bin/env python3
"""Merge bounded score batches and freeze the outcome-blind sentinel set."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tomllib
from datetime import date
from pathlib import Path

import numpy as np

from build_usdm_agricultural_exposure import configured_dates
from select_usdm_multiresolution_sentinels import choose_counties, separated_top_dates


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--shape-config", type=Path, required=True)
    parser.add_argument("--score-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--inventory-out", type=Path, required=True)
    arguments = parser.parse_args()
    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    shape_contract = tomllib.loads(arguments.shape_config.read_text(encoding="utf-8"))
    expected_dates = configured_dates(shape_contract)
    files = sorted(arguments.score_dir.glob("scores_*.npz"))
    if not files:
        raise FileNotFoundError("no score batches found")

    reference = None
    rows = []
    audits = []
    for path in files:
        audit_path = path.with_suffix(".audit.json")
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        if audit.get("schema") != "usdm_multiresolution_sentinel_score_batch_v1":
            raise ValueError(f"unexpected score audit schema for {path.name}")
        if sha256_file(path) != audit["output"]["sha256"]:
            raise ValueError(f"score-batch identity differs for {path.name}")
        with np.load(path, allow_pickle=False) as archive:
            current = {
                "counties": archive["counties"].copy(),
                "states": archive["states"].copy(),
                "area": archive["area"].copy(),
            }
            if reference is None:
                reference = current
            elif not all(np.array_equal(current[key], reference[key]) for key in current):
                raise ValueError("county support differs across score batches")
            dates = archive["dates"].astype("U10")
            ambiguity = archive["ambiguity"].astype(np.float32)
        if ambiguity.shape != (len(dates), len(reference["counties"])):
            raise ValueError(f"score matrix shape differs for {path.name}")
        rows.extend((str(value), ambiguity[index]) for index, value in enumerate(dates))
        audits.append(audit)

    rows.sort(key=lambda item: item[0])
    dates_text = [item[0] for item in rows]
    if dates_text != [value.isoformat() for value in expected_dates] or len(set(dates_text)) != len(dates_text):
        raise ValueError("score batches do not cover the configured maps exactly once")
    ambiguity = np.stack([item[1] for item in rows])
    counties = reference["counties"]
    states = reference["states"]
    area = reference["area"]
    p95 = np.quantile(ambiguity, 0.95, axis=0)
    maximum = ambiguity.max(axis=0)
    chosen = choose_counties(counties, states, area, p95, maximum, int(contract["area_strata"]))

    sentinels = []
    inventory_rows = []
    for stratum, index in chosen:
        date_indices = separated_top_dates(
            ambiguity[:, index], expected_dates, int(contract["dates_per_county"]),
            int(contract["minimum_date_separation_days"]),
        )
        sentinels.append({
            "area_stratum_zero_based": int(stratum),
            "county_geoid": str(counties[index]),
            "state_fips": str(states[index]),
            "cultivated_area_m2": float(area[index]),
            "weekly_ambiguity_p95": float(p95[index]),
            "weekly_ambiguity_max": float(maximum[index]),
            "selected_weeks": [
                {"map_date": expected_dates[i].isoformat(), "ambiguity": float(ambiguity[i, index])}
                for i in date_indices
            ],
        })
        inventory_rows.append({"county_geoid": str(counties[index]), "classifier_eligible": "true"})

    arguments.inventory_out.parent.mkdir(parents=True, exist_ok=True)
    with arguments.inventory_out.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["county_geoid", "classifier_eligible"])
        writer.writeheader()
        writer.writerows(sorted(inventory_rows, key=lambda row: row["county_geoid"]))
    source_grid_hashes = {audit["grid"]["sha512"] for audit in audits}
    manifest_hashes = {audit["vector_manifest"]["sha256"] for audit in audits}
    if len(source_grid_hashes) != 1 or len(manifest_hashes) != 1:
        raise ValueError("source identities differ across score batches")
    output = {
        "schema": "usdm_multiresolution_sentinel_selection_v1",
        "config": str(arguments.config),
        "selection_mask": str(contract["selection_mask"]),
        "selection_uses_outcomes": False,
        "grid_sha512": next(iter(source_grid_hashes)),
        "vector_manifest_sha256": next(iter(manifest_hashes)),
        "maps_scored": len(expected_dates),
        "counties_scored": len(counties),
        "score_batches": len(audits),
        "maximum_batch_peak_rss_bytes": max(int(audit["resource"]["peak_rss_bytes"]) for audit in audits),
        "sentinels": sentinels,
        "inventory": {"path": str(arguments.inventory_out), "sha256": sha256_file(arguments.inventory_out)},
        "claim_boundary": "outcome-blind spatial measurement audit only; not causal, damage, global-transfer, or SCC evidence",
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
