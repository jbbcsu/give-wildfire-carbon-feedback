#!/usr/bin/env python3
"""Independent coefficient identity check for paired-practice gap fits."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_PAIRED = PROJECT / "data/provenance/us_paired_practice_gap_association_20260827.json"
DEFAULT_SEPARATE = PROJECT / "data/provenance/us_direct_practice_precipitation_association_20260826.json"
DEFAULT_OUT = PROJECT / "data/provenance/us_paired_practice_gap_independent_validation_20260827.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT))
    except ValueError:
        return str(path)


def validate(paired_path: Path, separate_path: Path, tolerance: float = 2e-12) -> dict[str, object]:
    paired = json.loads(paired_path.read_text(encoding="utf-8"))
    separate = json.loads(separate_path.read_text(encoding="utf-8"))
    if paired.get("schema") != "us_paired_practice_gap_association_result_v1":
        raise ValueError("paired-practice result schema changed")
    if separate.get("schema") != "us_direct_practice_precipitation_association_result_v1":
        raise ValueError("separate-practice result schema changed")
    for result in (paired, separate):
        if result.get("causal_claim_authorized") is not False:
            raise ValueError("audited result opens a causal claim")
        if result.get("damage_claim_authorized") is not False or result.get("scc_claim_authorized") is not False:
            raise ValueError("audited result opens damage or SCC use")

    separate_index = {
        (row["crop"], row["irrigation_practice"], row["form"]): row
        for row in separate["estimates"]
    }
    expected_keys = {
        (row["crop"], practice, row["form"])
        for row in paired["estimates"] for practice in ("irrigated", "non_irrigated")
    }
    if set(separate_index) != expected_keys:
        raise ValueError("separate-practice estimate product differs from paired result")

    maximum = 0.0
    comparisons = 0
    rows = []
    for gap in paired["estimates"]:
        crop, form = gap["crop"], gap["form"]
        irrigated = separate_index[(crop, "irrigated", form)]
        non_irrigated = separate_index[(crop, "non_irrigated", form)]
        if gap["rows"] != irrigated["rows"] or gap["rows"] != non_irrigated["rows"]:
            raise ValueError("paired and separate fits do not use identical row counts")
        left = {row["term"]: float(row["estimate"]) for row in irrigated["coefficients"]}
        right = {row["term"]: float(row["estimate"]) for row in non_irrigated["coefficients"]}
        observed = {row["term"]: float(row["estimate"]) for row in gap["coefficients"]}
        if set(left) != set(right) or set(left) != set(observed):
            raise ValueError("coefficient terms differ across paired and separate fits")
        row_maximum = 0.0
        for term in sorted(observed):
            difference = abs(observed[term] - (left[term] - right[term]))
            maximum = max(maximum, difference)
            row_maximum = max(row_maximum, difference)
            comparisons += 1
        rows.append({
            "crop": crop,
            "form": form,
            "coefficient_count": len(observed),
            "maximum_absolute_difference_from_irrigated_minus_non_irrigated": row_maximum,
        })
    if maximum > tolerance:
        raise ValueError(f"paired coefficient identity differs by {maximum}")
    return {
        "schema": "us_paired_practice_gap_independent_validation_v1",
        "status": "validated_against_difference_of_separate_practice_coefficients",
        "identity": "paired_gap_coefficient_equals_irrigated_coefficient_minus_non_irrigated_coefficient",
        "paired_result": {"path": display_path(paired_path), "sha256": sha256(paired_path)},
        "separate_result": {"path": display_path(separate_path), "sha256": sha256(separate_path)},
        "comparisons": comparisons,
        "maximum_absolute_difference": maximum,
        "tolerance": tolerance,
        "rows": rows,
        "standard_errors_cross_checked": False,
        "standard_error_note": "The paired fit estimates county-clustered uncertainty on the within-pair yield gap; separate-fit standard errors omit their cross-practice covariance and are not subtracted.",
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paired", type=Path, default=DEFAULT_PAIRED)
    parser.add_argument("--separate", type=Path, default=DEFAULT_SEPARATE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = validate(args.paired.resolve(), args.separate.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(
        "paired-practice independent validation passed: "
        f"{result['comparisons']} coefficients, max difference {result['maximum_absolute_difference']:.3g}"
    )


if __name__ == "__main__":
    main()
