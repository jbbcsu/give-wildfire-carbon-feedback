#!/usr/bin/env python3
"""Tests for binding the rejected 3.96 km diagnostic into the final summary."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from summarize_usdm_agricultural_area_results import rejected_diagnostic_summary


def payload() -> dict[str, object]:
    return {
        "schema": "usdm_agricultural_area_spatial_basis_comparison_v1",
        "bases": {"county": {}, "cultivated": {}, "broad": {}},
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "global_transfer_authorized": False,
        "scc_claim_authorized": False,
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "diagnostic.json"
        path.write_text(json.dumps(payload()) + "\n", encoding="utf-8")
        result = rejected_diagnostic_summary(path)
        assert result["status"] == "rejected_by_frozen_native_resolution_sentinel_gate"
        assert result["comparison"]["bases"].keys() == {"county", "cultivated", "broad"}

        invalid = payload()
        invalid["scc_claim_authorized"] = True
        path.write_text(json.dumps(invalid) + "\n", encoding="utf-8")
        try:
            rejected_diagnostic_summary(path)
        except ValueError as error:
            assert "scc_claim_authorized" in str(error)
        else:
            raise AssertionError("open SCC claim gate was accepted")
    print("agricultural-area summary diagnostic-binding tests passed")


if __name__ == "__main__":
    main()
