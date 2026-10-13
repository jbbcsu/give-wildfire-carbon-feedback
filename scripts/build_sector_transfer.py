#!/usr/bin/env python3
"""Build a fail-closed Moore labor/agriculture transfer interface.

The interface intentionally exports only replicated global partial-sector
means. It never treats the source model's total, mortality, energy, or sea-level
outputs as new damages, and it marks agriculture as replacement-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_SCHEMA = "moore_sector_transfer_contract/v1"
RECEIPT_SCHEMA = "labor_ag_sectoral_scc_stage_receipt/v1"
ALLOWED_TRANSFER_SECTORS = {"labor", "agriculture"}
EXPECTED_FUNCTIONS = {"ISO", "LANCET"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_bound_json(root: Path, spec: dict[str, str]) -> dict[str, Any]:
    path = root / spec["path"]
    require(path.is_file(), f"missing bound input: {spec['path']}")
    require(sha256(path) == spec["sha256"], f"hash mismatch: {spec['path']}")
    return json.loads(path.read_text())


def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get("schema") == EXPECTED_SCHEMA, "unexpected contract schema")
    sectors = contract.get("transfer_sectors")
    require(isinstance(sectors, list) and set(sectors) == ALLOWED_TRANSFER_SECTORS,
            "transfer sectors must be exactly labor and agriculture")
    forbidden = set(contract.get("forbidden_import_sectors", []))
    require(not (set(sectors) & forbidden), "forbidden sector requested for transfer")
    require(set(contract.get("receipts", {})) == EXPECTED_FUNCTIONS,
            "exactly ISO and LANCET receipts are required")
    rules = contract.get("sector_rules", {})
    require(rules.get("labor", {}).get("disposition") == "candidate_addition",
            "labor disposition must be candidate_addition")
    require(rules.get("agriculture", {}).get("disposition") == "replacement_only",
            "agriculture must be replacement_only")
    for sector in ALLOWED_TRANSFER_SECTORS:
        blockers = rules.get(sector, {}).get("promotion_blockers")
        require(isinstance(blockers, list) and blockers, f"{sector} blockers must remain explicit")
    gates = contract.get("hard_gates", {})
    required_closed = {
        "allow_total_scc_import",
        "allow_forbidden_sector_import",
        "allow_agriculture_addition",
        "allow_cross_function_quantile_averaging",
        "allow_combined_scc_claim",
    }
    require(required_closed <= set(gates), "missing hard gate")
    require(all(gates[name] is False for name in required_closed), "all hard gates must be false")


def validate_receipt(receipt: dict[str, Any], function: str,
                     invariants: dict[str, Any]) -> None:
    require(receipt.get("schema") == RECEIPT_SCHEMA, f"{function} receipt schema differs")
    require(receipt.get("labor_function") == function, f"{function} receipt mislabeled")
    for name, expected in invariants.items():
        require(receipt.get(name) == expected, f"{function} invariant differs: {name}")
    summary = receipt.get("summary", {})
    expected_sectors = {"agriculture", "cromar_mortality", "energy", "labor", "slr", "total"}
    require(set(summary) == expected_sectors, f"{function} sector support differs")
    means = []
    for sector, values in summary.items():
        value = values.get("expected_scc_2020usd_per_tco2")
        require(isinstance(value, (int, float)) and math.isfinite(value),
                f"{function} non-finite mean: {sector}")
        if sector != "total":
            means.append(float(value))
    total = float(summary["total"]["expected_scc_2020usd_per_tco2"])
    require(math.isclose(sum(means), total, rel_tol=0, abs_tol=1e-9),
            f"{function} sector means do not sum to total")


def build_transfer(root: Path, contract_path: Path) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text())
    validate_contract(contract)
    for spec in contract["implementation_evidence"].values():
        path = root / spec["path"]
        require(path.is_file(), f"missing implementation evidence: {spec['path']}")
        require(sha256(path) == spec["sha256"], f"implementation hash mismatch: {spec['path']}")

    receipts = {
        function: load_bound_json(root, spec)
        for function, spec in contract["receipts"].items()
    }
    for function, receipt in receipts.items():
        validate_receipt(receipt, function, contract["common_invariants"])

    sectors: dict[str, Any] = {}
    for sector in sorted(ALLOWED_TRANSFER_SECTORS):
        single = {
            function: float(receipt["summary"][sector]["expected_scc_2020usd_per_tco2"])
            for function, receipt in receipts.items()
        }
        sectors[sector] = {
            "disposition": contract["sector_rules"][sector]["disposition"],
            "claim_status": contract["sector_rules"][sector]["claim_status"],
            "single_function_means_2020usd_per_tco2": single,
            "equal_weight_structural_mean_2020usd_per_tco2": sum(single.values()) / 2,
            "structural_range_2020usd_per_tco2": [min(single.values()), max(single.values())],
            "promotion_blockers": contract["sector_rules"][sector]["promotion_blockers"],
        }

    return {
        "schema": "moore_sector_transfer_interface/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract": {"path": str(contract_path.relative_to(root)), "sha256": sha256(contract_path)},
        "source": {
            "article_doi": contract["article_doi"],
            "archive_doi": contract["source_archive_doi"],
            "license": contract["license"],
            "receipt_hashes": {name: spec["sha256"] for name, spec in contract["receipts"].items()},
        },
        "invariants": contract["common_invariants"],
        "sectors": sectors,
        "excluded_source_outputs": sorted(contract["forbidden_import_sectors"]),
        "overlap_and_claim_gates": {
            "source_partial_sector_isolation_verified": True,
            "labor_global_mean_benchmark_reproduced": True,
            "updated_agriculture_global_mean_reproduced": True,
            "labor_installed_in_target_give": False,
            "agriculture_replacement_delta_computed": False,
            "precipitation_overlap_allocated": False,
            "joint_cross_function_uncertainty_reconstructed": False,
            "combined_scc_authorized": False,
        },
        "claim_status": "transfer_interface_ready; global means only; no target GIVE installation or combined SCC",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--contract", type=Path, default=Path("config/moore_sector_transfer_v1.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    contract_path = args.contract if args.contract.is_absolute() else root / args.contract
    result = build_transfer(root, contract_path)
    if args.output:
        output = args.output if args.output.is_absolute() else root / args.output
        require(not output.exists(), "fresh output path required")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
