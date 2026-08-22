#!/usr/bin/env python3
"""Acquire a pinned USDA NASS Quick Stats crops bulk snapshot safely.

The raw archive is large, ignored by git, and downloaded in verified HTTP
ranges.  A sidecar locks the upstream object identity before a partial file is
continued; completion writes a streaming SHA-512 manifest record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path


DEFAULT_URL = "https://www.nass.usda.gov/datasets/qs.crops_20260821.txt.gz"


def response_headers(url: str) -> dict[str, str]:
    output = subprocess.run(
        ["curl", "--fail", "--location", "--silent", "--show-error", "--head", url],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    headers: dict[str, str] = {}
    for key in ("content-length", "etag", "last-modified", "content-type"):
        matches = re.findall(rf"(?im)^{re.escape(key)}:\s*(.+?)\s*$", output)
        if matches:
            headers[key] = matches[-1]
    if "content-length" not in headers:
        raise RuntimeError("NASS response did not declare Content-Length")
    return headers


def sha512_file(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL,
                        help="explicit dated USDA bulk archive URL")
    parser.add_argument("--out-dir", default="data/raw/us_county/nass")
    parser.add_argument("--chunk-mib", type=int, default=16)
    parser.add_argument("--chunks-per-run", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    args = parser.parse_args()
    if min(args.chunk_mib, args.chunks_per_run, args.timeout_seconds) < 1:
        raise ValueError("chunk size, chunk count, and timeout must be positive")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = args.url.rsplit("/", 1)[-1]
    if not re.fullmatch(r"qs\.crops_\d{8}\.txt\.gz", filename):
        raise ValueError("URL must name an explicit dated qs.crops_YYYYMMDD.txt.gz snapshot")
    target = out_dir / filename
    partial = target.with_suffix(target.suffix + ".partial")
    identity_file = target.with_suffix(target.suffix + ".source.json")

    headers = response_headers(args.url)
    expected_bytes = int(headers["content-length"])
    identity = {
        "url": args.url,
        "content_length": expected_bytes,
        "etag": headers.get("etag"),
        "last_modified": headers.get("last-modified"),
        "content_type": headers.get("content-type"),
    }
    if identity_file.exists():
        previous = json.loads(identity_file.read_text(encoding="utf-8"))
        if previous != identity:
            raise RuntimeError("Upstream object identity changed; do not continue the partial archive")
    else:
        identity_file.write_text(json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if target.exists():
        if target.stat().st_size != expected_bytes:
            raise RuntimeError("Completed target length differs from the pinned response")
        status = "existing"
    else:
        if partial.exists() and partial.stat().st_size > expected_bytes:
            raise RuntimeError("Partial archive is longer than the pinned response")
        chunk_bytes = args.chunk_mib * 1024 * 1024
        for _ in range(args.chunks_per_run):
            start = partial.stat().st_size if partial.exists() else 0
            if start == expected_bytes:
                break
            end = min(start + chunk_bytes - 1, expected_bytes - 1)
            piece = partial.with_suffix(partial.suffix + ".chunk")
            piece.unlink(missing_ok=True)
            command = [
                "curl", "--fail", "--location", "--silent", "--show-error",
                "--retry", "3", "--max-time", str(args.timeout_seconds),
                "--range", f"{start}-{end}", "--output", str(piece),
            ]
            if headers.get("etag"):
                command.extend(["--header", f"If-Range: {headers['etag']}"])
            command.append(args.url)
            subprocess.run(command, check=True)
            expected_piece = end - start + 1
            observed_piece = piece.stat().st_size if piece.exists() else 0
            if observed_piece != expected_piece:
                raise RuntimeError(
                    f"Range {start}-{end} returned {observed_piece} bytes; expected {expected_piece}"
                )
            with partial.open("ab") as destination, piece.open("rb") as source:
                while block := source.read(1024 * 1024):
                    destination.write(block)
            piece.unlink()
        observed = partial.stat().st_size if partial.exists() else 0
        if observed < expected_bytes:
            print(f"partial: {observed}/{expected_bytes} bytes")
            return
        if observed != expected_bytes:
            raise RuntimeError("Partial archive length differs from the pinned response")
        partial.replace(target)
        status = "downloaded"

    record = {
        "source": "USDA NASS Quick Stats crops bulk snapshot",
        "url": args.url,
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "bytes": target.stat().st_size,
        "sha512": sha512_file(target),
        "file": str(target),
        "license": "USDA public data; verify record-level disclosure flags and citation requirements",
        "role": "US county crop yield, production, and harvested-area outcomes",
    }
    with (out_dir / "MANIFEST.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
    print(f"{status}: {target.name} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
