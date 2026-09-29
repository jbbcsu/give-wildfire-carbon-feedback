#!/usr/bin/env python3
"""Validate the metadata-only manifest without opening tabular data columns."""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "data/provenance/us_corn_untracked_source_reproducibility_20260929.json"


def digest(path: Path, algorithm: str) -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def git_output(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)


def validate(manifest_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text())
    artifacts = manifest.get("artifacts", [])
    if len(artifacts) != 10 or len({item["path"] for item in artifacts}) != 10:
        raise AssertionError("manifest must contain exactly ten unique artifacts")
    policy = manifest.get("inspection_policy", {})
    if policy.get("parquet_data_pages_read") != 0 or policy.get("outcome_columns_opened") is not False:
        raise AssertionError("metadata-only inspection boundary is not fail-closed")

    total_bytes = 0
    for item in artifacts:
        relative = item["path"]
        path = ROOT / relative
        if path.exists() != item["present"]:
            raise AssertionError(f"presence changed: {relative}")
        if not path.is_file():
            raise AssertionError(f"not a regular file: {relative}")
        size = path.stat().st_size
        total_bytes += size
        if size != item["size_bytes"]:
            raise AssertionError(f"size changed: {relative}")
        if digest(path, "sha256") != item["sha256"]:
            raise AssertionError(f"SHA-256 changed: {relative}")
        if "sha512" in item and digest(path, "sha512") != item["sha512"]:
            raise AssertionError(f"SHA-512 changed: {relative}")
        tracked = git_output("ls-files", "--error-unmatch", "--", relative).returncode == 0
        ignored = git_output("check-ignore", "-q", "--", relative).returncode == 0
        if tracked != item["git_tracked"] or ignored != item["git_ignored"]:
            raise AssertionError(f"git disposition changed: {relative}")
        for provenance in item["provenance"]:
            if not (ROOT / provenance).is_file():
                raise AssertionError(f"missing provenance reference: {provenance}")
        if not item["role"] or not item["license"] or "from_publishers_only" not in item["regeneration_without_credentials"]:
            raise AssertionError(f"incomplete metadata: {relative}")

    return {"status": "validated", "artifact_count": len(artifacts), "total_bytes": total_bytes,
            "parquet_data_pages_read": 0, "outcome_columns_opened": False,
            "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    print(json.dumps(validate(args.manifest.resolve()), sort_keys=True))


if __name__ == "__main__":
    main()
