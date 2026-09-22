#!/usr/bin/env python3
"""Adapt crop-agnostic CDL-weighted USDM exposure to frozen response inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import pandas as pd


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--exposure", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    arguments = parser.parse_args()

    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    mask_id = str(contract["mask_id"])
    crops = list(map(str, contract["crops"]))
    year_min, year_max = int(contract["year_min"]), int(contract["year_max"])
    source = pd.read_parquet(arguments.exposure)
    category_columns = [f"weeks_d{level}" for level in range(5)]
    required = {
        "county_geoid", "mask_id", "harvest_year", "represented_days",
        "total_equivalent_weeks", "analysis_role", "scc_authorized",
        *category_columns,
    }
    if missing := required - set(source.columns):
        raise ValueError(f"agricultural exposure lacks {sorted(missing)}")
    if source.scc_authorized.any():
        raise ValueError("source exposure violates SCC boundary")
    source = source.loc[
        source.mask_id.eq(mask_id) & source.harvest_year.between(year_min, year_max)
    ].copy()
    if source.empty or source.duplicated(["county_geoid", "harvest_year"]).any():
        raise ValueError("selected agricultural exposure is empty or duplicated")
    years = set(range(year_min, year_max + 1))
    if set(map(int, source.harvest_year.unique())) != years:
        raise ValueError("selected agricultural exposure has incomplete year support")
    expected_days = source.harvest_year.map(
        lambda value: 366 if pd.Timestamp(int(value), 1, 1).is_leap_year else 365
    )
    if not source.represented_days.astype(int).eq(expected_days).all():
        raise ValueError("selected agricultural exposure has incomplete annual day support")

    outputs = []
    for crop in crops:
        part = source[["county_geoid", "harvest_year", "weeks_none", *category_columns]].copy()
        part.insert(1, "outcome_crop", crop)
        part = part.rename(columns={
            "weeks_none": "none_weeks",
            **{f"weeks_d{level}": f"d{level}_weeks" for level in range(5)},
        })
        part["source_area_basis"] = str(contract["source_area_basis_value"])
        part["published_area_basis"] = "agricultural_area_unspecified_cdl_codes"
        part["exact_published_exposure_replication"] = False
        part["analysis_role"] = "historical_external_validation_only"
        part["scc_authorized"] = False
        outputs.append(part)
    result = pd.concat(outputs, ignore_index=True)
    keys = ["county_geoid", "outcome_crop", "harvest_year"]
    if result.duplicated(keys).any():
        raise ValueError("adapted exposure duplicates response keys")
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(arguments.out, index=False)
    audit = {
        "schema": "usdm_agricultural_area_response_adapter_audit_v1",
        "config": {"path": str(arguments.config), "sha256": sha256(arguments.config)},
        "input": {"path": str(arguments.exposure), "sha256": sha256(arguments.exposure)},
        "output": {"path": str(arguments.out), "sha256": sha256(arguments.out), "rows": len(result)},
        "mask_id": mask_id,
        "crops": crops,
        "year_min": year_min,
        "year_max": year_max,
        "counties": int(result.county_geoid.nunique()),
        "source_area_basis": str(contract["source_area_basis_value"]),
        "exact_published_exposure_replication": False,
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
    }
    arguments.audit_out.parent.mkdir(parents=True, exist_ok=True)
    arguments.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {len(result)} response exposure rows for {mask_id}")


if __name__ == "__main__":
    main()
