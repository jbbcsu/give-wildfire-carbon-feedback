#!/usr/bin/env python3
"""Acquire the documented CRU global scPDSI historical benchmark.

The download is deliberately separate from projected climate inputs.  It is a
compact historical benchmark for drought-response and coverage validation;
future SCC drought paths must be recomputed from matched future climate draws.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path


URL = "https://crudata.uea.ac.uk/cru/data/drought/cru-ts4.10.1903-2025.scpdsi.nc"
FILENAME = "cru-ts4.10.1903-2025.scpdsi.nc"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="data/raw/drought/cru_scpdsi")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--chunk-mib", type=int, default=16,
                        help="verified HTTP range size; deliberately bounded for resumable acquisition")
    parser.add_argument("--chunks-per-run", type=int, default=1,
                        help="number of complete chunks to acquire before exiting")
    args = parser.parse_args()
    if args.timeout_seconds < 1 or args.chunk_mib < 1 or args.chunks_per_run < 1:
        raise ValueError("timeout, chunk size, and chunks per run must be positive")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / FILENAME
    headers = subprocess.run(
        ["curl", "--fail", "--location", "--silent", "--show-error", "--head", URL],
        check=True, capture_output=True, text=True,
    ).stdout
    match = re.search(r"(?im)^content-length:\s*(\d+)\s*$", headers)
    if not match:
        raise RuntimeError("CRU response did not declare Content-Length")
    expected_bytes = int(match.group(1))
    if target.exists() and target.stat().st_size != expected_bytes:
        raise RuntimeError(f"Completed target has {target.stat().st_size} bytes, expected {expected_bytes}; remove corrupt target first")

    temporary = target.with_suffix(target.suffix + ".partial")
    if target.exists():
        payload = target.read_bytes()
        status = "existing"
    else:
        if temporary.exists() and temporary.stat().st_size > expected_bytes:
            raise RuntimeError(f"Partial file has {temporary.stat().st_size} bytes, expected at most {expected_bytes}; remove corrupt partial first")
        chunk_size = args.chunk_mib * 1024 * 1024
        for _ in range(args.chunks_per_run):
            start = temporary.stat().st_size if temporary.exists() else 0
            if start == expected_bytes:
                break
            end = min(start + chunk_size - 1, expected_bytes - 1)
            piece = temporary.with_suffix(temporary.suffix + ".chunk")
            piece.unlink(missing_ok=True)
            # A range response is downloaded to a separate file, measured,
            # and only then appended. This prevents an interrupted process
            # from leaving an ambiguous continuation state.
            subprocess.run(
                ["curl", "--fail", "--location", "--silent", "--show-error", "--retry", "3",
                 "--max-time", str(args.timeout_seconds), "--range", f"{start}-{end}",
                 "--output", str(piece), URL],
                check=True,
            )
            expected_piece = end - start + 1
            if not piece.exists() or piece.stat().st_size != expected_piece:
                raise RuntimeError(f"Range {start}-{end} returned {piece.stat().st_size if piece.exists() else 0} bytes, expected {expected_piece}")
            with temporary.open("ab") as destination, piece.open("rb") as source:
                while block := source.read(1024 * 1024):
                    destination.write(block)
            piece.unlink()
        if not temporary.exists() or temporary.stat().st_size < expected_bytes:
            print(f"partial: {temporary.stat().st_size if temporary.exists() else 0}/{expected_bytes} bytes")
            return
        if temporary.stat().st_size != expected_bytes:
            raise RuntimeError("Partial file length differs from official Content-Length")
        temporary.replace(target)
        payload = target.read_bytes()
        status = "downloaded"
    record = {
        "source": "Climatic Research Unit global self-calibrating PDSI",
        "url": URL,
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "bytes": len(payload),
        "sha512": hashlib.sha512(payload).hexdigest(),
        "file": str(target),
        "license": "ODbL-1.0; attribution required by CRU",
        "role": "historical drought benchmark; not a future SCC climate input",
    }
    with (out_dir / "MANIFEST.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
    print(f"{status}: {target.name} ({len(payload)} bytes)")


if __name__ == "__main__":
    main()
