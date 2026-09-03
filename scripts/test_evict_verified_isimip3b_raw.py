#!/usr/bin/env python3
"""Static safety checks for the verified raw-data eviction utility."""
from pathlib import Path


source = (Path(__file__).parent / "evict_verified_isimip3b_raw.py").read_text(encoding="utf-8")
assert ".unlink()" in source
assert "rmtree" not in source
assert "RECEIPT_PATTERN" in source
assert "all_six_files_full_content_validated" in source
assert "digest(path, \"sha512\") == item[\"sha512\"]" in source
assert "for item in candidates:\n        (root / str(item[\"path\"])).unlink()" in source
assert source.index("for index, item in enumerate(candidates") < source.index(".unlink()")

print("verified ISIMIP eviction static safety tests passed")
