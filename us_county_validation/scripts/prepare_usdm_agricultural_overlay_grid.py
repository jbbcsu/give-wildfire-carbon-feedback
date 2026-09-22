#!/usr/bin/env python3
"""Prepare compact numeric arrays so weekly overlays start with low RSS."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "build_usdm_agricultural_exposure.py"
SPEC = importlib.util.spec_from_file_location("agricultural_overlay", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load agricultural overlay builder")
OVERLAY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OVERLAY)


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    arguments = parser.parse_args()

    grid = OVERLAY.load_grid(arguments.grid)
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        arguments.out,
        county=grid["county"], mask=grid["mask"],
        group_index=grid["group_index"], cell_index=grid["cell_index"],
        weight=grid["weight"], x=grid["x"], y=grid["y"],
        rows=np.asarray([grid["rows"]], dtype=np.int64),
        unique_cells=np.asarray([grid["unique_cells"]], dtype=np.int64),
    )
    audit = {
        "schema": "usdm_agricultural_overlay_grid_v1",
        "source_grid": {"path": str(arguments.grid), "sha512": sha512(arguments.grid)},
        "output": {
            "path": str(arguments.out), "sha512": sha512(arguments.out),
            "bytes": arguments.out.stat().st_size,
        },
        "rows": int(grid["rows"]),
        "unique_cells": int(grid["unique_cells"]),
        "county_mask_groups": len(grid["county"]),
        "claim_boundary": "numeric computational projection of validated grid; no exposure, response, damage, or SCC",
    }
    arguments.audit_out.parent.mkdir(parents=True, exist_ok=True)
    arguments.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
