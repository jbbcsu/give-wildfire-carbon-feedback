#!/usr/bin/env python3
"""Independently validate the matched deterministic GIVE climate/discount pair."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def validate(root: Path, config_path: Path) -> dict:
    config = json.loads(config_path.read_text())
    target = config["give_target"]
    spec = target["temperature_pair"]
    path = root / spec["path"]
    require(path.is_file(), "temperature pair missing")
    require(digest(path) == spec["sha256"], "temperature pair hash mismatch")
    require(digest(root / "scripts/export_give_matched_temperature_pair.jl") == spec["exporter_sha256"], "exporter hash mismatch")
    give_manifest = root.parent / "paper-2022-scc-give-zenodo/Manifest.toml"
    require(digest(give_manifest) == spec["give_manifest_sha256"], "GIVE manifest hash mismatch")
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    require(len(rows) == spec["rows"] == 551, "pair row count differs")
    expected_header = ["year", "base_gmst_c", "pulse_gmst_c", "base_conus_anomaly_c", "pulse_conus_anomaly_c", "base_net_cpc", "ramsey_discount_factor"]
    require(list(rows[0]) == expected_header, "pair schema differs")
    years = [int(row["year"]) for row in rows]
    require(years == list(range(1750, 2301)), "pair years differ")
    pulse_year = target["pulse_year"]
    multiplier = config["response"]["global_to_conus_multiplier"]
    for row in rows:
        year = int(row["year"])
        base = float(row["base_gmst_c"])
        pulse = float(row["pulse_gmst_c"])
        base_conus = float(row["base_conus_anomaly_c"])
        pulse_conus = float(row["pulse_conus_anomaly_c"])
        require(all(math.isfinite(value) for value in (base, pulse, base_conus, pulse_conus)), f"nonfinite climate row {year}")
        if year >= 1995:
            require(base_conus >= 0 and pulse_conus >= 0, f"negative post-reference anomaly {year}")
        if year < pulse_year:
            require(base == pulse and base_conus == pulse_conus, f"pre-pulse divergence {year}")
            require(float(row["ramsey_discount_factor"]) == 0, f"pre-pulse discount factor {year}")
        else:
            cpc = float(row["base_net_cpc"])
            discount = float(row["ramsey_discount_factor"])
            require(math.isfinite(cpc) and cpc > 0, f"invalid post-pulse consumption {year}")
            require(math.isfinite(discount) and discount > 0, f"invalid post-pulse discount factor {year}")
    reference = rows[1995 - 1750]
    require(float(reference["base_conus_anomaly_c"]) == 0, "base reference is not zero")
    require(float(reference["pulse_conus_anomaly_c"]) == 0, "pulse reference is not zero")
    for row in rows:
        base_expected = multiplier * (float(row["base_gmst_c"]) - float(reference["base_gmst_c"]))
        pulse_expected = multiplier * (float(row["pulse_gmst_c"]) - float(reference["pulse_gmst_c"]))
        require(math.isclose(float(row["base_conus_anomaly_c"]), base_expected, rel_tol=0, abs_tol=1e-12), "base CONUS conversion differs")
        require(math.isclose(float(row["pulse_conus_anomaly_c"]), pulse_expected, rel_tol=0, abs_tol=1e-12), "pulse CONUS conversion differs")
    post_deltas = [float(row["pulse_gmst_c"]) - float(row["base_gmst_c"]) for row in rows if int(row["year"]) > pulse_year]
    require(max(post_deltas) > 0 and min(post_deltas) >= 0, "post-pulse response is absent or negative")
    pulse_row = rows[pulse_year - 1750]
    require(float(pulse_row["ramsey_discount_factor"]) == 1.0, "pulse-year discount factor differs")
    return {
        "schema": "fredi_transport_give_temperature_pair_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "rows": len(rows),
        "years": [years[0], years[-1]],
        "pulse_year": pulse_year,
        "pre_pulse_identity": True,
        "official_conus_conversion_recomputed": True,
        "post_pulse_response_positive": True,
        "max_pulse_gmst_difference_c": max(post_deltas),
        "max_base_conus_anomaly_c": max(float(row["base_conus_anomaly_c"]) for row in rows if int(row["year"]) >= 1995),
        "pair_sha256": digest(path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/fredi_transport_matched_pulse_v1.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    result = validate(ROOT, args.config.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
