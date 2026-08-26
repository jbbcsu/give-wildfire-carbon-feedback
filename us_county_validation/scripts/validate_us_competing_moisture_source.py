#!/usr/bin/env python3
"""Validate and hash-bind one raw U.S. competing-moisture source table.

The receipt is a pre-fit schema, gate, source, and calendar-lineage check.  It
does not recompute daily nClimGrid fields, monthly NOAA PDSI, or the fixed
calendar from the publisher PDF; that limitation is explicit in the receipt.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_us_competing_moisture_inputs import (
    DEFAULT_PROTOCOL,
    SOURCE_FAMILIES,
    build_source_receipt,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", required=True, choices=sorted(SOURCE_FAMILIES))
    parser.add_argument("--input", required=True)
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    receipt = build_source_receipt(
        Path(args.input), args.family, Path(args.protocol)
    )
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"validated and hash-bound {receipt['candidate']['validated_rows_on_locked_sample']} "
        f"{args.family} rows; no fit, causal effect, damage, or SCC"
    )


if __name__ == "__main__":
    main()
