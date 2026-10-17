#!/usr/bin/env python3
"""Validate the published FrEDI transport target before matched-pulse execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
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


def audit(root: Path, config_path: Path) -> dict:
    config = json.loads(config_path.read_text())
    require(config["schema"] == "fredi_transport_matched_pulse_contract/v1", "wrong schema")
    selection = config["selection"]
    require(selection["sector"] == "heat-driven road and rail infrastructure", "wrong sector")
    require(selection["global_scc_claim_allowed"] is False, "global claim must remain closed")
    sources = config["sources"]
    manifest_path = root / sources["manifest"]["path"]
    require(manifest_path.is_file(), "source manifest missing")
    require(digest(manifest_path) == sources["manifest"]["sha256"], "source manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text())
    require(manifest["upstreams"]["FrEDI"]["commit"] == sources["fredi_commit"], "FrEDI commit differs")
    require(manifest["upstreams"]["FrEDI_Data"]["commit"] == sources["fredi_data_commit"], "FrEDI_Data commit differs")
    bound = {item["raw_path"]: item for item in manifest["files"] if item["raw_path"]}
    for name in ("runtime_sysdata", "temperature_conversion_source"):
        relative = sources[name]
        require(relative in bound, f"{name} is not manifest-bound")
        path = root / relative
        require(path.stat().st_size == bound[relative]["bytes"], f"{name} size differs")
        require(digest(path) == bound[relative]["sha256"], f"{name} hash differs")
    conversion = (root / sources["temperature_conversion_source"]).read_text()
    require("c1 <- 1.421" in conversion, "official conversion multiplier absent")
    require("new_temps   <- c1*temp_global + c0" in conversion, "global-to-CONUS formula absent")
    require(config["response"]["global_to_conus_multiplier"] == 1.421, "configured conversion differs")
    require(config["response"]["primary_variant"] == "Reactive", "official primary variant differs")
    require(config["response"]["released_aggregates"] == ["Roads", "Rail"], "aggregate scope differs")
    require(config["response"]["include_each_released_aggregate_once"] is True, "aggregate accounting differs")
    require(config["give_target"]["require_matched_base_pulse_temperature_and_consumption"] is True, "matched paths required")
    pair = config["give_target"]["temperature_pair"]
    pair_path = root / pair["path"]
    require(pair_path.is_file() and digest(pair_path) == pair["sha256"], "matched pair binding differs")
    with pair_path.open() as handle:
        pair_rows = sum(1 for _ in handle) - 1
    require(pair_rows == pair["rows"], "matched pair row count differs")
    gates = config["claim_gates"]
    require(gates["official_response_and_runtime_provenance_verified"] is True, "source gate must be open")
    require(gates["matched_give_temperature_pair_built"] is True, "matched GIVE pair gate must be open")
    for name in ("price_year_conversion_pinned", "common_gcm_temperature_support_verified", "matched_annual_damage_pair_validated", "discount_and_pulse_normalization_validated", "conus_partial_scc_authorized", "global_extrapolation_authorized"):
        require(gates[name] is False, f"prematurely open gate: {name}")

    inspection = subprocess.run(
        ["Rscript", str(root / "scripts/inspect_fredi_transport_runtime.R"), str(root / sources["runtime_sysdata"])],
        check=True, capture_output=True, text=True,
    )
    runtime = json.loads(inspection.stdout)
    require(runtime["transport_scaled_rows"] == 9114, "runtime transport row count differs")
    require(runtime["states"] == 49, "runtime geography differs")
    require(set(runtime["models"]) == set(config["response"]["gcm_surfaces"]), "runtime models differ")
    require(set(runtime["variants"]) == {"NoAdapt", "Proactive", "Reactive"}, "runtime variants differ")
    require(set(runtime["sectors"]) == {"Roads", "Rail"}, "runtime sectors differ")
    primary = runtime["primary_rows"]
    require(len(primary) == 6, "runtime sector/variant rows differ")
    admitted = [row for row in primary if row["sectorprimary"] == 1 and row["includeaggregate"] == 1]
    require({(row["sector"], row["variant"]) for row in admitted} == {("Roads", "Reactive"), ("Rail", "Reactive")}, "primary/additive flags differ")
    support = {row["scalarName"]: row["year"] for row in runtime["scalar_support"]}
    require(set(support) == {"road_miles", "rail_miles", "road_miles_and_pop_Reactive", "rail_growth_factor"}, "runtime scalar set differs")
    require(all(value == [2010, 2300] for value in support.values()), "runtime scalar support does not reach 2300")

    return {
        "schema": "fredi_transport_matched_pulse_target_audit/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "target_ready_climate_pair_and_scc_gates_closed",
        "selected_sector": selection,
        "source_manifest": {"path": sources["manifest"]["path"], "sha256": digest(manifest_path)},
        "runtime": runtime,
        "verified": {"official_temperature_conversion": True, "runtime_through_2300": True, "primary_reactive_aggregates": ["Roads", "Rail"], "state_dc_count": 49, "gcm_count": 6},
        "claim_gates": gates,
        "next_actions": ["build matched GIVE baseline/pulse GMST and consumption path", "apply the official 1.421 CONUS conversion relative to 1995", "evaluate paired annual Reactive Roads and Rail damages on common model support", "pin 2015-to-2020 USD conversion", "validate Ramsey discounting and pulse normalization"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/fredi_transport_matched_pulse_v1.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    result = audit(ROOT, args.config.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "verified": result["verified"]}, indent=2))


if __name__ == "__main__":
    main()
