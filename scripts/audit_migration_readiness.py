#!/usr/bin/env python3
"""Validate the fail-closed migration integration contract."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    config_path = ROOT / "config/migration_readiness_v1.json"
    config = json.loads(config_path.read_text())
    assert config["schema"] == "give_migration_readiness/v1"
    assert config["target"]["numeric_scc_authorized"] is False
    assert config["next_model_contract"]["claim_status"] == "BLOCKED_NO_ADDITIVE_SCC"
    assert config["existing_give_coverage"]["coastal_relocation"]["do_not_add_again"] is True

    forbidden = set(config["forbidden_shortcuts"])
    assert "cost_per_migrant times projected migrants" in forbidden
    assert "counting CIAM coastal relocation twice" in forbidden
    assert len(config["admission_gates"]) >= 10
    assert len(config["candidates"]) >= 4
    assert all(candidate["failed_gates"] for candidate in config["candidates"])
    assert all(candidate["disposition"] for candidate in config["candidates"])

    zenodo = ROOT / "data/reference/zenodo_7681424_record.json"
    dataverse = ROOT / "data/reference/harvard_dataverse_WOC3AD_metadata.json"
    z = json.loads(zenodo.read_text())
    d = json.loads(dataverse.read_text())
    zfile = z["files"][0]
    dversion = d["data"]["latestVersion"]
    assert z["doi"] == "10.5281/zenodo.7681424"
    assert zfile["size"] == 2303161642
    assert zfile["checksum"] == "md5:343ad34579940a46c4b71b5eda3bb422"
    assert d["status"] == "OK" and len(dversion["files"]) == 80
    assert sum(item["dataFile"]["filesize"] for item in dversion["files"]) == 116615273052

    result = {
        "schema": "give_migration_readiness_result/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_NO_ADDITIVE_SCC",
        "numeric_scc_produced": False,
        "reason": "No screened source jointly passes welfare, marginal-pulse, separability, overlap, and reproducibility gates.",
        "verified": {
            "ciam_coastal_relocation_already_covered": True,
            "noncoastal_migration_explicitly_missing": True,
            "candidate_count": len(config["candidates"]),
            "zenodo_replication_package": {"bytes": zfile["size"], "md5": zfile["checksum"]},
            "dataverse_replication_package": {"files": len(dversion["files"]), "bytes": sum(item["dataFile"]["filesize"] for item in dversion["files"])},
            "all_candidates_fail_at_least_one_gate": True
        },
        "inputs": {
            "config": {"path": str(config_path.relative_to(ROOT)), "sha256": sha256(config_path)},
            "zenodo_metadata": {"path": str(zenodo.relative_to(ROOT)), "sha256": sha256(zenodo)},
            "dataverse_metadata": {"path": str(dataverse.relative_to(ROOT)), "sha256": sha256(dataverse)}
        },
        "next_action": "Use Cruz-Rossi-Hansberg as a non-additive structural sensitivity only, or estimate incremental real/nonpecuniary relocation costs under the interface contract before adding a sector."
    }
    output = ROOT / "results/migration_readiness_result_v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

