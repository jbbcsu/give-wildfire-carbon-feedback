#!/usr/bin/env python3
"""Acquire four official maize/soy drought-sensitivity rasters, sequentially."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/tuninetti_2026_zenodo_18937255"
NAMES = (
    "FINAL_percentage_yield_variation_dueto_climate_RF_56_maize.txt",
    "FINAL_percentage_yield_variation_dueto_climate_IR_56_maize.txt",
    "FINAL_percentage_yield_variation_dueto_climate_RF_236_soybean.txt",
    "FINAL_percentage_yield_variation_dueto_climate_IR_236_soybean.txt",
)


def digest(path: Path, algorithm: str = "md5") -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunk-mib", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.chunk_mib <= 16:
        raise ValueError("chunk-mib must be between 1 and 16")
    metadata = json.loads((RAW / "record.json").read_text(encoding="utf-8"))
    records = {item["key"]: item for item in metadata["files"]}
    receipts = []
    for name in NAMES:
        record = records[name]
        target = RAW / name
        expected_md5 = record["checksum"].split(":", 1)[1]
        if target.exists() and target.stat().st_size == int(record["size"]) and digest(target) == expected_md5:
            status = "already_valid"
        else:
            partial = target.with_suffix(target.suffix + ".partial")
            if partial.exists():
                partial.unlink()
            request = Request(record["links"]["self"], headers={"User-Agent": "GIVE-precipitation-source-audit/1.0"})
            with urlopen(request, timeout=120) as response, partial.open("wb") as stream:
                shutil.copyfileobj(response, stream, length=args.chunk_mib * 1024 * 1024)
            if partial.stat().st_size != int(record["size"]) or digest(partial) != expected_md5:
                raise ValueError(f"official size or MD5 mismatch: {name}")
            partial.replace(target)
            status = "downloaded_and_validated"
        receipts.append(
            {
                "file": name,
                "status": status,
                "bytes": target.stat().st_size,
                "md5": expected_md5,
                "sha256": digest(target, "sha256"),
                "url": record["links"]["self"],
            }
        )
        print(json.dumps(receipts[-1]), flush=True)
    receipt = {
        "schema": "tuninetti_2026_crop_raster_acquisition_v1",
        "status": "passed",
        "zenodo_record_id": metadata["id"],
        "zenodo_doi": metadata["doi"],
        "files": receipts,
        "total_bytes": sum(item["bytes"] for item in receipts),
    }
    output = ROOT / "data/interim/tuninetti_2026_crop_raster_acquisition_20260922/result.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)


if __name__ == "__main__":
    main()
