#!/usr/bin/env python3
"""Delete exactly two reproducible extrema files after pair validation passes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT/"data/provenance/isimip3b_five_esm_late_drought_extrema_20260921.json"


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-dir", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    pair_dir = args.pair_dir if args.pair_dir.is_absolute() else ROOT/args.pair_dir
    validation_path = args.validation if args.validation.is_absolute() else ROOT/args.validation
    receipt_path = args.receipt if args.receipt.is_absolute() else ROOT/args.receipt
    require(not receipt_path.exists(), "fresh eviction receipt required")
    result_path = pair_dir/"result.json"; result = json.loads(result_path.read_text())
    validation = json.loads(validation_path.read_text())
    require(validation.get("status") == "passed", "independent pair validation not passed")
    require(validation.get("pair_result_sha256") == digest(result_path), "validated pair result changed")
    output = ROOT/result["output"]["path"]
    require(output.stat().st_size == result["output"]["bytes"] and digest(output) == result["output"]["sha256"], "derived output changed")
    frozen = json.loads(MANIFEST.read_text())
    candidates = []
    for source in result["sources"]:
        if source["variable"] not in {"tasmin", "tasmax"}:
            continue
        path = ROOT/source["path"]
        require(path.is_file() and path.stat().st_size == source["bytes"] and digest(path, "sha512") == source["sha512"], "extrema source identity changed")
        matches = [item for item in frozen["objects"] if item["file_name"] == path.name and item["sha512"] == source["sha512"]]
        require(len(matches) == 1, "extrema source is not uniquely recoverable from frozen manifest")
        candidates.append((path, matches[0]))
    require(len(candidates) == 2 and {item[1]["variable"] for item in candidates} == {"tasmin", "tasmax"}, "exact extrema pair required")
    free_before = shutil.disk_usage(ROOT).free
    records = []
    for path, metadata in candidates:
        records.append({"deleted_path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
                        "sha512": metadata["sha512"], "file_url": metadata["file_url"],
                        "dataset_id": metadata["dataset_id"], "file_id": metadata["file_id"],
                        "rights": metadata["rights"], "resource_doi": metadata["resource_doi"]})
    for path, _ in candidates:
        path.unlink()
    require(all(not path.exists() for path, _ in candidates), "one or more extrema files remain")
    receipt = {"schema": "validated_late_drought_extrema_eviction_v1", "status": "two_verified_reproducible_raw_files_deleted",
               "reason": "bounded local storage after independent derived-output validation", "esm": result["esm"],
               "scenario": result["scenario"], "pair_result_sha256": digest(result_path),
               "validation_sha256": digest(validation_path), "derived_output": result["output"],
               "deleted": records, "deleted_bytes": sum(item["bytes"] for item in records),
               "free_bytes_before": free_before, "free_bytes_after": shutil.disk_usage(ROOT).free,
               "recovery": "download each file_url and require the recorded byte count and SHA-512 before reuse",
               "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())}}
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = receipt_path.with_suffix(receipt_path.suffix+".partial")
    temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n"); temporary.replace(receipt_path)
    print(json.dumps({"status": receipt["status"], "deleted_bytes": receipt["deleted_bytes"], "free_bytes_after": receipt["free_bytes_after"]}))


if __name__ == "__main__":
    main()
