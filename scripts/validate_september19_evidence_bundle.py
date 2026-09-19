#!/usr/bin/env python3
"""Cross-check the tracked September 19 precipitation evidence bundle."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def validate() -> dict[str, object]:
    required = [
        "SEPTEMBER19_REPRODUCIBILITY_INDEX.md",
        "PRECIPITATION_DAMAGE_EVIDENCE_SYNTHESIS_20260919.md",
        "manuscript/SEPTEMBER19_STRUCTURAL_BENCHMARK_INSERT.md",
        "manuscript/SEPTEMBER19_METHODS_SI_INSERT.md",
        "GFDL_FUTURE_SPEI_CROP_WINDOW_PROTOCOL_20260919.md",
        "GFDL_FUTURE_SPEI_CROP_WINDOW_RESULTS_20260919.md",
        "FOUR_CORNER_WELFARE_ATTRIBUTION_PROTOCOL_20260919.md",
        "FOUR_CORNER_WELFARE_ATTRIBUTION_RESULTS_20260919.md",
        "FIXED_POSITIVE_CROP_SUPPORT_PROTOCOL_20260919.md",
        "FIXED_POSITIVE_CROP_SUPPORT_RESULTS_20260919.md",
        "FIXED_POSITIVE_WELFARE_SENSITIVITY_PROTOCOL_20260919.md",
        "FIXED_POSITIVE_WELFARE_SENSITIVITY_RESULTS_20260919.md",
        "PUBLISHED_DROUGHT_PRODUCT_ACCESS_AUDIT_20260919.md",
    ]
    for relative in required:
        require((ROOT / relative).is_file(), f"required artifact missing: {relative}")

    drought = load("data/provenance/gfdl_future_spei_crop_windows_20260919.json")
    require(drought["validation"]["status"] == "passed", "future SPEI validation failed")
    require(drought["validation"]["checks"] == 1_066_451, "future SPEI check count changed")
    require(drought["outputs"]["regime"]["rows"] == 163_350, "SPEI regime support changed")
    require(drought["outputs"]["combined"]["rows"] == 150_390, "SPEI combined support changed")

    attribution = load("data/provenance/four_corner_welfare_attribution_20260919.json")
    require(attribution["case_count"] == 96, "four-corner case count changed")
    require(attribution["mechanically_admissible_case_count"] == 84, "admissible case count changed")
    require(attribution["validation_check_count"] == 3_081, "four-corner checks changed")

    support = load("data/provenance/fixed_positive_crop_support_20260919.json")
    require(support["validation_check_count"] == 154, "support audit checks changed")
    require(support["both_model_excluded_unique_cell_regimes"] == 186, "excluded support changed")

    sensitivity = load("data/provenance/fixed_positive_welfare_sensitivity_20260919.json")
    require(sensitivity["case_count"] == 96, "fixed-support case count changed")
    require(sensitivity["validation_check_count"] == 1_929, "fixed-support checks changed")
    require(sensitivity["partial_support_only"] is True, "partial-support gate changed")
    require(sensitivity["crop_model_repaired"] is False, "crop-repair gate changed")

    access = load("data/provenance/published_drought_product_access_20260919.json")
    require(access["payload_bytes_downloaded"] == 0, "unexpected drought payload was downloaded")
    require(access["give_archive_total_bytes"] == 160_184_380_129, "archive total changed")

    receipts = [attribution, sensitivity]
    for receipt in receipts:
        for key in ("empirical_damage_authorized", "agriculture_replacement_authorized",
                    "give_export_authorized", "scc_authorized"):
            require(receipt[key] is False, f"release gate unexpectedly open: {key}")
    require(access["future_drought_estimated"] is False, "access audit relabeled as drought estimate")
    require(access["damage_or_scc_result"] is False, "access audit relabeled as damage/SCC")

    manuscript = (ROOT / "manuscript/SEPTEMBER19_STRUCTURAL_BENCHMARK_INSERT.md").read_text()
    methods = (ROOT / "manuscript/SEPTEMBER19_METHODS_SI_INSERT.md").read_text()
    for phrase in ("No result in this insert is an empirical precipitation damage function",
                   "must not be stacked"):
        require(phrase in manuscript, f"manuscript interpretation gate missing: {phrase}")
    for phrase in ("matched baseline and emissions-pulse", "false flags"):
        require(phrase in methods, f"Methods SI release gate missing: {phrase}")

    return {
        "status": "passed",
        "required_artifact_count": len(required),
        "future_spei_validation_checks": drought["validation"]["checks"],
        "four_corner_validation_checks": attribution["validation_check_count"],
        "fixed_support_validation_checks": sensitivity["validation_check_count"],
        "empirical_damage_authorized": False,
        "give_export_authorized": False,
        "scc_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2, sort_keys=True))
