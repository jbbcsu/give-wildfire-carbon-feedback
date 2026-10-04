#!/usr/bin/env python3
"""Validate the authoritative Free/Gaines GitHub metadata receipt."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/audit_free_gaines_github_metadata.py"
RECEIPT_PATH = ROOT / "data/provenance/free_gaines_github_metadata_20261004.json"
INVENTORY_PATH = ROOT / "data/provenance/free_gaines_welfare_bridge_candidate_inventory_20261004.json"
SOURCE_AUDIT_PATH = ROOT / "data/provenance/alternative_global_fisheries_welfare_audit_20260928.json"
spec = importlib.util.spec_from_file_location("free_gaines_github_metadata", SCRIPT_PATH)
assert spec and spec.loader
auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)


receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
source_audit = json.loads(SOURCE_AUDIT_PATH.read_text(encoding="utf-8"))
repository = receipt["repository"]
tree = receipt["pinned_tree"]
resolution = receipt["resolution"]
pinned_audit = source_audit["closest_candidate_source_audit"]
candidate_source = inventory["sources"][0]

assert receipt["schema"] == "free_gaines_github_metadata_audit_v1"
assert repository["full_name"] == "SFG-UCSB/cc_trade"
assert repository["id"] == 154888535
assert repository["default_branch_head"] == pinned_audit["commit"] == candidate_source["version"]
assert repository["github_detected_license"] is None
assert repository["releases"] == []
assert repository["tags"] == []

# The recursive API result must be complete before filename absence is usable.
assert tree["recursive_listing_truncated"] is False
assert tree["entry_count"] == 244
assert tree["license_matches"] == []
assert tree["dependency_lock_matches"] == []
assert tree["named_source_matches"] == {
    "eez_delta_k_df.rds": [],
    "global_cc_1nation_manuscript_2019Feb12.rds": [],
}
assert tree["format_script"] == {
    "api_url": "https://api.github.com/repos/SFG-UCSB/cc_trade/git/blobs/21d9d993b1469bfd963eee64584925be43b42c36",
    "git_blob_sha": "21d9d993b1469bfd963eee64584925be43b42c36",
    "path": "code/Step1_format_gaines_data.R",
    "size_bytes": 12521,
    "type": "blob",
}
assert tree["format_script"]["path"] == pinned_audit["pinned_files"]["format_script"]["path"]

assert resolution == {
    "damage_or_scc_authorized": False,
    "default_branch_head_matches_pinned_commit": True,
    "dependency_lock_blocker_resolved": False,
    "named_raw_source_blocker_resolved": False,
    "repository_license_blocker_resolved": False,
    "scientific_validation_authorized": False,
    "versioned_release_blocker_resolved": False,
}
assert inventory["responses"] == inventory["incidence"] == inventory["welfare"] == []

# Unit-check the fail-closed tree requirement without making a network call.
try:
    auditor.summarize(
        {"full_name": auditor.REPOSITORY},
        {"sha": auditor.COMMIT},
        {"truncated": True, "tree": []},
        [],
        [],
        "test-only",
    )
except ValueError as error:
    assert "truncated" in str(error)
else:
    raise AssertionError("truncated GitHub tree was not rejected")

print("Free/Gaines authoritative GitHub metadata receipt remains fail-closed")
