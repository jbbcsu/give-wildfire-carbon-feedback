#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tempfile

from validate_isimip3b_rimex_catalogue_track_feasibility_contract import validate


root = Path(__file__).resolve().parents[1]
config = root / "config/isimip3b_rimex_catalogue_track_feasibility_v1.toml"
result = validate(config, root)
assert result["status"] == "validated_before_official_catalogue_metadata_query"
assert result["minimum_esm_member_tracks"] == 7
assert result["window_starts"] == [2015, 2036, 2057, 2078]
assert result["window_ends"] == [2035, 2056, 2077, 2098]
assert result["final_ensemble_selection_authorized"] is False
assert result["acquisition_authorized"] is False

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "contract.toml"
    tampered.write_text(
        config.read_text(encoding="utf-8").replace(
            "query_must_not_filter_ensemble_member = true",
            "query_must_not_filter_ensemble_member = false",
        ),
        encoding="utf-8",
    )
    try:
        validate(tampered, root)
    except ValueError as error:
        assert "member discovery gate changed" in str(error)
    else:
        raise AssertionError("pre-filtered member discovery passed")

print("ISIMIP3b catalogue track-feasibility preregistration tests passed")
