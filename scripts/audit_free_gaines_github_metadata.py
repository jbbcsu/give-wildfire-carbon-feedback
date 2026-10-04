#!/usr/bin/env python3
"""Query authoritative GitHub metadata for the pinned Free/Gaines candidate.

This script reads repository metadata only. It does not download repository
blobs, run the model, validate scientific inputs, or authorize an estimate.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from typing import Any


REPOSITORY = "SFG-UCSB/cc_trade"
COMMIT = "dfd250ddd806973f463e83097a3ed39dd27f8bfb"
API_ROOT = f"https://api.github.com/repos/{REPOSITORY}"
LICENSE_NAMES = {
    "license", "license.md", "license.txt",
    "licence", "licence.md", "licence.txt", "copying",
}
DEPENDENCY_LOCK_NAMES = {
    "renv.lock", "packrat.lock", "environment.yml", "environment.yaml",
    "requirements.txt", "project.toml", "manifest.toml", "description",
}
NAMED_SOURCE_BASENAMES = {
    "eez_delta_k_df.rds",
    "global_cc_1nation_manuscript_2019Feb12.rds",
}
FORMAT_SCRIPT = "code/Step1_format_gaines_data.R"


def get_json(url: str, timeout: float) -> Any:
    result = subprocess.run(
        [
            "curl", "-fsS", "--max-time", str(timeout),
            "-H", "Accept: application/vnd.github+json",
            "-H", "X-GitHub-Api-Version: 2022-11-28",
            "-H", "User-Agent: GIVE-free-gaines-metadata-audit",
            url,
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"GitHub API query failed for {url}: {result.stderr.strip()}")
    return json.loads(result.stdout)


def summarize(
    repository: dict[str, Any],
    commit: dict[str, Any],
    tree: dict[str, Any],
    releases: list[dict[str, Any]],
    tags: list[dict[str, Any]],
    retrieved_utc: str,
) -> dict[str, Any]:
    if repository.get("full_name") != REPOSITORY:
        raise ValueError("GitHub repository identity changed")
    if commit.get("sha") != COMMIT:
        raise ValueError("GitHub commit identity changed")
    if tree.get("truncated") is not False:
        raise ValueError("GitHub recursive tree is truncated; absence cannot be established")

    entries = tree.get("tree")
    if not isinstance(entries, list):
        raise ValueError("GitHub recursive tree is missing")
    paths = [entry["path"] for entry in entries]

    def basename(path: str) -> str:
        return path.rsplit("/", 1)[-1].lower()

    format_entries = [entry for entry in entries if entry.get("path") == FORMAT_SCRIPT]
    if len(format_entries) != 1:
        raise ValueError("pinned formatting script is missing or duplicated")
    format_entry = format_entries[0]

    return {
        "schema": "free_gaines_github_metadata_audit_v1",
        "retrieved_utc": retrieved_utc,
        "repository": {
            "id": repository.get("id"),
            "full_name": repository["full_name"],
            "default_branch": repository.get("default_branch"),
            "default_branch_head": commit["sha"],
            "pushed_at": repository.get("pushed_at"),
            "updated_at": repository.get("updated_at"),
            "archived": repository.get("archived"),
            "disabled": repository.get("disabled"),
            "github_detected_license": repository.get("license"),
            "releases": [release.get("tag_name") for release in releases],
            "tags": [tag.get("name") for tag in tags],
        },
        "pinned_tree": {
            "commit": COMMIT,
            "commit_date": commit.get("commit", {}).get("committer", {}).get("date"),
            "git_tree_sha": commit.get("commit", {}).get("tree", {}).get("sha"),
            "recursive_listing_sha": tree.get("sha"),
            "recursive_listing_truncated": tree["truncated"],
            "entry_count": len(entries),
            "license_names_searched": sorted(LICENSE_NAMES),
            "license_matches": sorted(path for path in paths if basename(path) in LICENSE_NAMES),
            "dependency_lock_names_searched": sorted(DEPENDENCY_LOCK_NAMES),
            "dependency_lock_matches": sorted(
                path for path in paths if basename(path) in DEPENDENCY_LOCK_NAMES
            ),
            "named_source_matches": {
                name: sorted(path for path in paths if basename(path) == name.lower())
                for name in sorted(NAMED_SOURCE_BASENAMES)
            },
            "format_script": {
                "path": format_entry["path"],
                "type": format_entry.get("type"),
                "git_blob_sha": format_entry.get("sha"),
                "size_bytes": format_entry.get("size"),
                "api_url": format_entry.get("url"),
            },
        },
        "api_queries": {
            "repository": API_ROOT,
            "default_branch_head": f"{API_ROOT}/commits/{repository.get('default_branch')}",
            "pinned_commit": f"{API_ROOT}/commits/{COMMIT}",
            "pinned_recursive_tree": f"{API_ROOT}/git/trees/{COMMIT}?recursive=1",
            "releases": f"{API_ROOT}/releases?per_page=100",
            "tags": f"{API_ROOT}/tags?per_page=100",
        },
        "resolution": {
            "default_branch_head_matches_pinned_commit": commit["sha"] == COMMIT,
            "repository_license_blocker_resolved": repository.get("license") is not None,
            "versioned_release_blocker_resolved": bool(releases or tags),
            "dependency_lock_blocker_resolved": bool(
                [path for path in paths if basename(path) in DEPENDENCY_LOCK_NAMES]
            ),
            "named_raw_source_blocker_resolved": all(
                any(basename(path) == name.lower() for path in paths)
                for name in NAMED_SOURCE_BASENAMES
            ),
            "scientific_validation_authorized": False,
            "damage_or_scc_authorized": False,
        },
        "scope_note": (
            "Null GitHub license metadata and filename absence in the complete pinned tree "
            "do not prove that no off-repository license, release, dependency record, or "
            "source artifact exists; they establish that the queried repository endpoints "
            "do not supply the required evidence."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    if args.timeout <= 0:
        raise ValueError("timeout must be positive")

    repository = get_json(API_ROOT, args.timeout)
    default_branch = repository.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch:
        raise ValueError("GitHub default branch is unavailable")
    commit = get_json(f"{API_ROOT}/commits/{default_branch}", args.timeout)
    pinned_commit = get_json(f"{API_ROOT}/commits/{COMMIT}", args.timeout)
    if commit.get("sha") != pinned_commit.get("sha"):
        raise ValueError("default branch no longer points to the pinned candidate commit")
    tree = get_json(f"{API_ROOT}/git/trees/{COMMIT}?recursive=1", args.timeout)
    releases = get_json(f"{API_ROOT}/releases?per_page=100", args.timeout)
    tags = get_json(f"{API_ROOT}/tags?per_page=100", args.timeout)
    retrieved_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    print(json.dumps(summarize(repository, pinned_commit, tree, releases, tags, retrieved_utc), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
