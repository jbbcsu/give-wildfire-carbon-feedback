#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tempfile

from validate_global_continuous_geographic_cluster_contract import validate


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/global_continuous_geographic_cluster_v1.toml"


def expect_failure(old: str, new: str, message: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "contract.toml"
        source = CONFIG.read_text(encoding="utf-8")
        assert old in source
        path.write_text(source.replace(old, new, 1), encoding="utf-8")
        try:
            validate(path, ROOT)
        except ValueError as error:
            assert message in str(error), str(error)
        else:
            raise AssertionError(f"tampered contract passed: {message}")


result = validate(CONFIG, ROOT)
assert result["status"] == "geographic_and_source_cluster_audit_preregistered_not_evaluated"
assert result["input_receipts"] == 6
assert result["fold_count"] == 5
assert result["bootstrap_replicates"] == 5000
assert result["coefficient_export_authorized"] is False
assert result["damage_or_scc_authorized"] is False

expect_failure("count = 5", "count = 4", "fold count")
expect_failure("replicates = 5000", "replicates = 4999", "bootstrap lock")
expect_failure("one_parquet_file_at_a_time = true", "one_parquet_file_at_a_time = false", "resource gate")
expect_failure("model_promotion_authorized = false", "model_promotion_authorized = true", "closed gate")
expect_failure("excluded_end_year = 2011", "excluded_end_year = 2010", "endpoint purge")

print("global continuous geographic/source-cluster contract tests passed")
