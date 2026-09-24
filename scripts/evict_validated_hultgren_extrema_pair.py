#!/usr/bin/env python3
"""Delete one reproducible extrema pair after both Hultgren regimes validate."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/provenance/isimip3b_five_esm_late_drought_extrema_20260921.json"


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rainfed-validation", type=Path, required=True)
    parser.add_argument("--irrigated-validation", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    validation_paths = [path if path.is_absolute() else ROOT / path for path in (args.rainfed_validation, args.irrigated_validation)]
    receipt_path = args.receipt if args.receipt.is_absolute() else ROOT / args.receipt
    require(not receipt_path.exists(), "fresh eviction receipt required")
    validations = [json.loads(path.read_text(encoding="utf-8")) for path in validation_paths]
    for validation in validations:
        require(validation["status"] == "validated_grid_basis_not_response_damage_or_scc", "basis validation did not pass")
        basis = ROOT / validation["basis"]["path"]
        require(basis.is_file() and basis.stat().st_size == validation["basis"]["bytes"] and digest(basis) == validation["basis"]["sha256"], "validated basis changed")
    sources = [validation["source_identity_from_builder_receipt"]["daily_climate"] for validation in validations]
    require(sources[0] == sources[1], "rainfed and irrigated daily climate identities differ")
    frozen = json.loads(MANIFEST.read_text(encoding="utf-8"))["objects"]
    candidates = []
    for variable in ("tasmin", "tasmax"):
        identity = sources[0][variable]
        path = ROOT / identity["path"]
        require(path.is_file() and path.stat().st_size == identity["bytes"] and digest(path, "sha512") == identity["sha512"], f"{variable} source identity changed")
        matches = [item for item in frozen if item["file_name"] == path.name and item["bytes"] == identity["bytes"] and item["sha512"] == identity["sha512"]]
        require(len(matches) == 1 and matches[0]["variable"] == variable, f"{variable} is not uniquely recoverable")
        candidates.append((path, matches[0]))
    require(len({path for path, _ in candidates}) == 2, "exactly two distinct extrema files required")

    free_before = shutil.disk_usage(ROOT).free
    deleted = []
    for path, metadata in candidates:
        deleted.append({
            "path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
            "sha512": metadata["sha512"], "file_url": metadata["file_url"],
            "dataset_id": metadata["dataset_id"], "file_id": metadata["file_id"],
            "rights": metadata["rights"], "resource_doi": metadata["resource_doi"],
        })
    for path, _ in candidates:
        path.unlink()
    require(all(not path.exists() for path, _ in candidates), "one or more extrema files remain")
    result = {
        "schema": "validated_hultgren_extrema_eviction/v1",
        "status": "two_verified_reproducible_raw_files_deleted_after_two_regime_validation",
        "reason": "bounded local storage after rainfed and irrigated basis validation",
        "validations": [
            {"path": str(path.relative_to(ROOT)), "sha256": digest(path)}
            for path in validation_paths
        ],
        "retained_bases": [validation["basis"] for validation in validations],
        "deleted": deleted,
        "deleted_bytes": sum(item["bytes"] for item in deleted),
        "free_bytes_before": free_before,
        "free_bytes_after": shutil.disk_usage(ROOT).free,
        "recovery": "download each file_url and require the recorded byte count and SHA-512 before reuse",
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = receipt_path.with_suffix(receipt_path.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(receipt_path)
    print(json.dumps({"status": result["status"], "deleted_bytes": result["deleted_bytes"], "free_bytes_after": result["free_bytes_after"]}, indent=2))


if __name__ == "__main__":
    main()
