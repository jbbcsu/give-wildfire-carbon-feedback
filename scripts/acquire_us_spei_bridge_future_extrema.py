#!/usr/bin/env python3
"""Acquire one frozen future extrema object for the 11-cell SPEI bridge queue."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_isimip3b_late_drought_case import acquire  # noqa: E402

MANIFEST = ROOT / "data/provenance/isimip3b_five_esm_late_drought_extrema_20260921.json"
MANIFEST_SHA256 = "bb844ed1b7565465972f371dd5edcf1d90ae6ea8998db9d5a078d1946dcbd57f"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esm", required=True)
    parser.add_argument("--scenario", choices=("ssp126", "ssp370", "ssp585"), required=True)
    parser.add_argument("--variable", choices=("tasmin", "tasmax"), required=True)
    args = parser.parse_args()
    if digest(MANIFEST) != MANIFEST_SHA256:
        raise ValueError("frozen future extrema manifest changed")
    manifest = json.loads(MANIFEST.read_text())
    matches = [item for item in manifest["objects"]
               if (item["esm"], item["scenario"], item["variable"])
               == (args.esm, args.scenario, args.variable)]
    if len(matches) != 1:
        raise ValueError("exactly one frozen extrema object required")
    path = acquire(matches[0])
    print(json.dumps({"status": "verified_extrema_object_resident", "esm": args.esm,
                      "scenario": args.scenario, "variable": args.variable,
                      "path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
                      "sha512": matches[0]["sha512"], "file_url": matches[0]["file_url"]}))


if __name__ == "__main__":
    main()
