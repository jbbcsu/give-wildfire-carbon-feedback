#!/usr/bin/env python3
"""Rerun the registered assembly and compare the direct table exactly."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from assemble_us_national_nclimgrid_features import (
    DEFAULT_OUTPUT,
    add_arguments,
    assemble_from_args,
)
from us_national_nclimgrid_common import (
    OUTCOME_KEYS,
    atomic_write_json,
    sha256_file,
    sha256_records,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    parser.add_argument("--candidate", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    expected, assembly_audit = assemble_from_args(args)
    candidate_path = Path(args.candidate)
    candidate = pd.read_parquet(candidate_path).sort_values(OUTCOME_KEYS).reset_index(drop=True)
    pd.testing.assert_frame_equal(
        candidate, expected.sort_values(OUTCOME_KEYS).reset_index(drop=True),
        check_dtype=True, check_exact=True,
    )
    receipt = {
        "schema": "us_national_nclimgrid_feature_assembly_recomputation_validation_v1",
        "status": "candidate_exactly_matches_registered_assembly_recomputation",
        "candidate_path": str(candidate_path),
        "candidate_sha256": sha256_file(candidate_path),
        "candidate_rows": int(len(candidate)),
        "candidate_key_sha256": sha256_records(candidate, OUTCOME_KEYS),
        "assembly_audit": assembly_audit,
        "raw_payloads_revalidated": not args.skip_raw_revalidation,
        "independent_implementation": False,
        "relationship_estimated": False,
        "causal_effect_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
    }
    atomic_write_json(Path(args.out), receipt)
    print(
        f"validated exact {len(candidate)}-row national feature assembly; "
        "no fit, causal effect, damage, or SCC"
    )


if __name__ == "__main__":
    main()
