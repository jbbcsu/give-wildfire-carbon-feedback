#!/usr/bin/env python3
"""Independent validator for the aggregate-only FrEDI transport smoke test."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import resource
import sys
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 50


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(262144)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def load_json(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def finite(value: str) -> Decimal:
    number = Decimal(value)
    assert number.is_finite()
    return number


def peak_mib() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / (1024 * 1024 if sys.platform == "darwin" else 1024)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    config_path = root / "config/fredi_transport_heat_v4_1_1.json"
    config = load_json(config_path)
    manifest_path = root / config["source_manifest"]
    manifest = load_json(manifest_path)
    alignment_path = root / config["alignment_audit"]
    alignment = load_json(alignment_path)
    assert alignment["status"] == "PASS"
    assert Decimal(str(alignment["tolerance"])) <= Decimal("1e-12")
    assert all(Decimal(str(row["max_abs_difference"])) <= Decimal("1e-12") for row in alignment["comparisons"])
    for item in manifest["files"]:
        if item["raw_path"] is None:
            assert item.get("vendored") is False
            continue
        source = root / item["raw_path"]
        assert source.stat().st_size == item["bytes"], source
        assert digest(source) == item["sha256"], source

    assert config["scope"]["allowed_released_aggregates"] == ["Roads", "Rail"]
    gates = {g["endpoint"]: g["available_in_public_v4_1_1_runtime"] for g in config["component_gates"]}
    assert gates == {
        "road_repair": False,
        "road_user": False,
        "rail_replacement": False,
        "rail_delay": False,
    }
    assert config["claim_status"]["global_extrapolation"] == "prohibited"
    assert config["claim_status"]["SCC"] == "closed"

    raw = root / "data/raw/fredi_data/inst/extdata/fredi"
    scaled = {}
    state_support = {}
    for sector in ("Roads", "Rail"):
        seen = set()
        sector_values = {}
        for row in rows(raw / "gcm" / f"{sector}_scaledimpacts.csv"):
            assert row["sector"] == sector
            assert row["impactType"] == "NA" and row["impactYear"] == "NA"
            seen.add(row["postal"])
            bin_value = int(row["modelUnitValue"])
            if bin_value in (1, 2):
                key = (row["postal"], row["model"], row["variant"], bin_value)
                assert key not in sector_values
                sector_values[key] = finite(row["value"])
        assert len(seen) == 49
        scaled[sector] = sector_values
        state_support[sector] = seen
    assert state_support["Roads"] == state_support["Rail"]
    states = state_support["Roads"]

    miles = {}
    for sector, token in (("Roads", "road"), ("Rail", "rail")):
        observations = {}
        for row in rows(raw / "scalars" / f"Scalar_physScalar_{token}_miles.csv"):
            observations.setdefault(row["postal"], {})[int(row["year"])] = finite(row["value"])
        assert set(observations) == states
        assert all(set(values) == {2010, 2090} for values in observations.values())
        assert all(values[2010] == values[2090] for values in observations.values())
        miles[sector] = {postal: values[2010] for postal, values in observations.items()}

    road_adj = {}
    for variant in config["smoke_test"]["variants"]:
        path = raw / "scalars" / f"Scalar_damageAdj_road_miles_and_pop_{variant}.csv"
        selected = {
            row["postal"]: finite(row["value"])
            for row in rows(path)
            if int(row["year"]) == 2020
        }
        assert set(selected) == states
        road_adj[variant] = selected
    rail_growth_rows = list(rows(raw / "scalars/Scalar_damageAdj_rail_growth_factor.csv"))
    selected_growth = [finite(row["value"]) for row in rail_growth_rows if int(row["year"]) == 2020]
    assert len(selected_growth) == 1
    rail_growth = selected_growth[0]

    expected = {}
    half = Decimal("0.5")
    quantizer = Decimal("0.000001")
    for sector in ("Roads", "Rail"):
        for variant in config["smoke_test"]["variants"]:
            for model in config["smoke_test"]["models"]:
                terms = []
                for postal in sorted(states):
                    lower = scaled[sector][(postal, model, variant, 1)]
                    upper = scaled[sector][(postal, model, variant, 2)]
                    interpolated = (lower + upper) * half
                    adjustment = road_adj[variant][postal] if sector == "Roads" else rail_growth
                    terms.append(interpolated * miles[sector][postal] * adjustment)
                expected[(sector, variant, model)] = sum(terms, Decimal("0")).quantize(quantizer)

    output_path = root / config["smoke_test"]["output"]
    observed_rows = list(rows(output_path))
    assert len(observed_rows) == 36
    assert set(observed_rows[0]) == {
        "scope", "model_type", "driver_conus_degC_rel1995", "economic_year", "gcm",
        "variant", "released_aggregate", "annual_impact_2015usd_per_year", "component_resolution"
    }
    observed = {}
    for row in observed_rows:
        assert row["scope"] == "CONUS_48_plus_DC"
        assert row["model_type"] == "GCM"
        assert row["driver_conus_degC_rel1995"] == "1.5"
        assert row["economic_year"] == "2020"
        assert row["component_resolution"] == "combined_public_surface"
        assert row["released_aggregate"] in {"Roads", "Rail"}
        key = (row["released_aggregate"], row["variant"], row["gcm"])
        assert key not in observed
        observed[key] = finite(row["annual_impact_2015usd_per_year"])
    assert observed == expected

    receipt_path = root / config["smoke_test"]["receipt"]
    receipt = load_json(receipt_path)
    assert receipt["config"]["sha256"] == digest(config_path)
    assert receipt["source_manifest"]["sha256"] == digest(manifest_path)
    assert receipt["alignment_audit"] == {
        "path": config["alignment_audit"],
        "sha256": digest(alignment_path),
        "status": "PASS",
    }
    for path, expected_hash in receipt["execution_code"].items():
        assert digest(root / path) == expected_hash
    assert receipt["output"]["sha256"] == digest(output_path)
    assert receipt["output"]["rows"] == 36
    assert receipt["component_gates"] == gates
    assert receipt["claim_status"] == config["claim_status"]
    assert receipt["excluded"] == {
        "drivers": ["SLR"],
        "sectors": ["CoastalProperties", "HTF", "InlandFlooding", "UrbanDrainage"],
        "global_extrapolation": True,
    }
    assert not any("scc" in key.lower() for key in observed_rows[0])
    assert peak_mib() < 512
    print(json.dumps({
        "status": "PASS",
        "independent_rows_recomputed": len(observed),
        "state_dc_count": len(states),
        "max_abs_difference_2015usd_per_year": "0.000000",
        "peak_rss_mib": round(peak_mib(), 3),
        "component_gate": "CLOSED",
        "scc_gate": "CLOSED"
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
