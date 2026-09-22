#!/usr/bin/env python3
"""Audit the official Tuninetti--Davis (2026) Zenodo source release.

This is a source/reproducibility audit, not a crop-damage calculation.  It
reads only the frozen Zenodo metadata and the two small MATLAB files acquired
from record 18937255; the large output rasters are not downloaded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/tuninetti_2026_zenodo_18937255"
EXPECTED_RECORD_ID = 18937255
EXPECTED_DOI = "10.5281/zenodo.18937255"
EXPECTED_CODE = {
    "0_waterCROP_model.m": {
        "md5": "0e926ad05e8fce2f3be9f067e4fa41cd",
        "sha256": "5ab213e0f4ca96f3f3e8b63fa356dc3fa7d5c7d6b5ff58831211c4c34483238e",
    },
    "1_water_production_function.m": {
        "md5": "a525131c2a5600d42abaf1327fae7b01",
        "sha256": "9a65bb904642dd577f8b23ac5aa0a8f9ea636286815d608949d1fc1a2b70ed20",
    },
}
TARGET_OUTPUTS = (
    "FINAL_percentage_yield_variation_dueto_climate_RF_56_maize.txt",
    "FINAL_percentage_yield_variation_dueto_climate_IR_56_maize.txt",
    "FINAL_percentage_yield_variation_dueto_climate_RF_236_soybean.txt",
    "FINAL_percentage_yield_variation_dueto_climate_IR_236_soybean.txt",
)


def digest(path: Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data/interim/tuninetti_2026_source_audit_20260922/result.json",
    )
    args = parser.parse_args()

    record_path = RAW / "record.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    require(record["id"] == EXPECTED_RECORD_ID, "Zenodo record id changed")
    require(record["doi"] == EXPECTED_DOI, "Zenodo DOI changed")
    files = {item["key"]: item for item in record["files"]}
    require(set(EXPECTED_CODE).issubset(files), "published code files missing")
    require(set(TARGET_OUTPUTS).issubset(files), "maize/soy rainfed/irrigated outputs missing")

    code_records = []
    combined_text = ""
    for name, expected in EXPECTED_CODE.items():
        path = RAW / name
        require(path.is_file(), f"missing acquired code file: {name}")
        md5 = digest(path, "md5")
        sha256 = digest(path, "sha256")
        require(md5 == expected["md5"] == files[name]["checksum"].split(":", 1)[1], f"MD5 mismatch: {name}")
        require(sha256 == expected["sha256"], f"SHA-256 mismatch: {name}")
        text = path.read_text(encoding="utf-8", errors="replace")
        combined_text += text
        code_records.append(
            {
                "file": name,
                "bytes": path.stat().st_size,
                "md5": md5,
                "sha256": sha256,
                "line_count": len(text.splitlines()),
            }
        )

    required_markers = {
        "historical_period_1961_2018": "year = 1961:2018;",
        "median_eta": "nanmedian(ETrf,3)",
        "tenth_percentile_eta": "quantile(ETrf,0.10,3)",
        "maize_ky_1_25": "1.25",
        "soybean_ky_0_85": "0.85",
        "yield_response_equation": "ETrf_10th./ETrf_median",
        "lower_bound_minus_100_percent": "yield_perc_R(yield_perc_R<-100) = -100",
        "external_export_helper": "txt_per_QGis",
        "hardcoded_windows_path": "D:\\0001_DATA",
        "hardcoded_macos_path": "/Users/marta/Library/CloudStorage",
    }
    marker_checks = {key: marker in combined_text for key, marker in required_markers.items()}
    require(all(marker_checks.values()), "one or more preregistered source markers missing")

    target_outputs = {
        name: {
            "bytes": int(files[name]["size"]),
            "md5": files[name]["checksum"].split(":", 1)[1],
            "content_url": files[name]["links"]["self"],
        }
        for name in TARGET_OUTPUTS
    }
    answer = {
        "schema": "tuninetti_2026_source_audit_v1",
        "status": "passed",
        "scientific_role": "published_global_water_balance_benchmark_not_empirical_response_or_scc_parameterization",
        "source": {
            "article_doi": "10.1038/s41467-026-72715-y",
            "zenodo_record_id": record["id"],
            "zenodo_doi": record["doi"],
            "zenodo_created": record["created"],
            "zenodo_modified": record["modified"],
            "metadata_license": record["metadata"].get("license"),
            "metadata_sha256": digest(record_path, "sha256"),
            "published_file_count": len(files),
            "published_total_bytes": sum(int(item["size"]) for item in files.values()),
        },
        "code": code_records,
        "marker_checks": marker_checks,
        "maize_soy_outputs_not_acquired": target_outputs,
        "maize_soy_output_bytes_if_acquired": sum(item["bytes"] for item in target_outputs.values()),
        "reproducibility_findings": {
            "official_code_available": True,
            "official_output_rasters_available": True,
            "turnkey_reproduction_from_release_alone": False,
            "reasons": [
                "published scripts contain machine-specific absolute paths",
                "water-balance inputs and helper files/functions referenced by the scripts are not bundled in the record",
                "Zenodo record metadata does not declare a license",
            ],
        },
        "use_decision": {
            "external_spatial_process_benchmark": True,
            "direct_global_yield_response_parameter": False,
            "direct_scc_parameter": False,
            "reason": "The release maps historical median-to-tenth-percentile ETa sensitivity using prescribed FAO yield-response factors; it does not estimate a causal or transient SPEI-to-yield response.",
        },
    }
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    temporary.write_text(json.dumps(answer, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(json.dumps({"status": answer["status"], "files": len(files), "output": str(output)}))


if __name__ == "__main__":
    main()
