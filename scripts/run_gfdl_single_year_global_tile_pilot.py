#!/usr/bin/env python3
"""Run one source-locked, resource-bounded 2032 maize climate-feature tile."""
from __future__ import annotations

import hashlib
from pathlib import Path
import tomllib

from run_bounded_job import run


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RECEIPT = ROOT / "data/provenance/isimip3b_rimex_contiguous_gfdl_ssp126_2031_2040.toml"
RAW_ROOT = ROOT / "data/raw/isimip3b/gfdl-esm4/ssp126"
CALENDAR = ROOT / "data/raw/crop_calendars/ggcmi-crop-calendar-phase3_2015soc_mai_noirr.nc"
OUT_ROOT = ROOT / "data/interim/gfdl_ssp126_global_2032_maize_tile_20260917"


def digest(path: Path, algorithm: str) -> str:
    result = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def source_file(receipt: dict, section: str, variable: str) -> Path:
    record = receipt[section]
    path = RAW_ROOT / variable / record["file_name"]
    if not path.is_file() or path.stat().st_size != record["bytes"]:
        raise ValueError(f"source size/path gate failed: {path}")
    if digest(path, "sha512") != record["sha512"]:
        raise ValueError(f"source SHA-512 gate failed: {path}")
    audit = ROOT / record["content_audit"]
    if not audit.is_file() or digest(audit, "sha256") != record["content_audit_sha256"]:
        raise ValueError(f"source content-audit gate failed: {audit}")
    return path


def main() -> None:
    receipt = tomllib.loads(SOURCE_RECEIPT.read_text(encoding="utf-8"))
    if not (
        receipt.get("esm") == "GFDL-ESM4"
        and receipt.get("member") == "r1i1p1f1"
        and receipt.get("scenario") == "ssp126"
        and receipt.get("dataset_version") == "20210512"
        and receipt.get("period_start_year") == 2031
        and receipt.get("period_end_year") == 2040
    ):
        raise ValueError("source identity gate failed")
    pr = source_file(receipt, "precipitation", "pr")
    tas = source_file(receipt, "paired_temperature", "tas")
    if not CALENDAR.is_file():
        raise FileNotFoundError(CALENDAR)
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    for label, builder in (
        ("season", "build_crop_year_features.py"),
        ("stages", "build_crop_stage_features.py"),
    ):
        output = OUT_ROOT / f"{label}_lat100_110.parquet"
        job_receipt = OUT_ROOT / f"{label}_lat100_110.resource.json"
        log = OUT_ROOT / f"{label}_lat100_110.log"
        if output.exists() or job_receipt.exists() or log.exists():
            raise FileExistsError(f"pilot output already exists: {label}")
        command = [
            str(ROOT / ".venv/bin/python"), str(ROOT / "scripts" / builder),
            "--precip", str(pr), "--temperature", str(tas),
            "--calendar", str(CALENDAR), "--crop", "mai", "--irrigation", "noirr",
            "--year-start", "2032", "--year-end", "2032",
            "--lat-start", "100", "--lat-stop", "110",
            "--wet-day-mm", "1", "--out", str(output),
        ]
        result = run(
            command, job_receipt, log, max_mib=512, min_free_gib=130,
            max_log_mib=2, interval=0.2, write_paths=[output], max_new_disk_mib=64,
        )
        print(f"{label}: {result['status']}; peak RSS {result['sampled_peak_group_rss_bytes']} bytes", flush=True)
        if result["status"] != "completed":
            raise RuntimeError(f"{label} failed resource/command gate: {result['status']}")


if __name__ == "__main__":
    main()
