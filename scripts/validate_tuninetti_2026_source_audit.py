#!/usr/bin/env python3
"""Independently validate the saved Tuninetti--Davis source audit."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/tuninetti_2026_zenodo_18937255"


def digest(path: Path, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "data/interim/tuninetti_2026_source_audit_20260922/result.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data/interim/tuninetti_2026_source_audit_20260922/validation.json",
    )
    args = parser.parse_args()
    input_path = args.input if args.input.is_absolute() else ROOT / args.input
    result = json.loads(input_path.read_text(encoding="utf-8"))
    metadata = json.loads((RAW / "record.json").read_text(encoding="utf-8"))
    files = {item["key"]: item for item in metadata["files"]}

    assert result["status"] == "passed"
    assert metadata["id"] == result["source"]["zenodo_record_id"] == 18937255
    assert digest(RAW / "record.json") == result["source"]["metadata_sha256"]
    assert len(files) == result["source"]["published_file_count"]
    assert sum(int(item["size"]) for item in files.values()) == result["source"]["published_total_bytes"]
    for record in result["code"]:
        path = RAW / record["file"]
        assert digest(path) == record["sha256"]
        assert digest(path, "md5") == record["md5"] == files[record["file"]]["checksum"].split(":", 1)[1]
    expected_output_bytes = sum(int(files[name]["size"]) for name in result["maize_soy_outputs_not_acquired"])
    assert expected_output_bytes == result["maize_soy_output_bytes_if_acquired"]
    assert all(result["marker_checks"].values())
    assert result["use_decision"] == {
        "direct_global_yield_response_parameter": False,
        "direct_scc_parameter": False,
        "external_spatial_process_benchmark": True,
        "reason": "The release maps historical median-to-tenth-percentile ETa sensitivity using prescribed FAO yield-response factors; it does not estimate a causal or transient SPEI-to-yield response.",
    }

    answer = {
        "schema": "tuninetti_2026_source_audit_validation_v1",
        "status": "passed",
        "input_sha256": digest(input_path),
        "independent_checks": 10 + 2 * len(result["code"]) + len(result["marker_checks"]),
        "source_output_bytes_recomputed": expected_output_bytes,
    }
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    temporary.write_text(json.dumps(answer, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(json.dumps(answer))


if __name__ == "__main__":
    main()
