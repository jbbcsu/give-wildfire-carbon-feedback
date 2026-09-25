#!/usr/bin/env python3
"""Validate the primary manuscript's DOI reference set against locked metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


DOI_PATTERN = re.compile(r"\]\(https://doi\.org/(10\.[^)]+)\)", re.IGNORECASE)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def normalize(value: str) -> str:
    return re.sub(r"-\s+", "-", " ".join(value.split())).lower()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    manuscript = args.manuscript.read_text()
    registry = json.loads(args.registry.read_text())
    require(registry["schema"] == "manuscript_reference_registry/v1", "registry schema differs")
    require(registry["status"] == "publisher_metadata_verified", "registry status differs")
    records = registry["records"]
    expected = {record["doi"].lower(): record for record in records}
    observed = [match.lower().rstrip(".,;") for match in DOI_PATTERN.findall(manuscript)]
    require(set(observed) == set(expected), f"manuscript DOI set differs: observed={sorted(set(observed))}")
    counts = {doi: observed.count(doi) for doi in expected}
    require(all(count >= 2 for count in counts.values()), f"DOI missing in-text or reference occurrence: {counts}")
    reference_text = manuscript.split("## References", 1)
    require(len(reference_text) == 2, "References section missing")
    references = reference_text[1]
    for doi, record in expected.items():
        require(record["first_author"] in references, f"reference author missing: {doi}")
        require(str(record["citation_year"]) in references, f"reference year missing: {doi}")
        require(normalize(record["title"]) in normalize(references), f"reference title missing: {doi}")
    nonmatch = registry["explicit_nonmatch"]["doi"].lower()
    require(nonmatch not in manuscript.lower(), "wildfire-method DOI conflated with agriculture source")
    result = {
        "schema": "manuscript_reference_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "checks": {
            "registered_dois": len(expected),
            "observed_doi_links": len(observed),
            "every_doi_in_text_and_references": True,
            "reference_author_year_title_present": True,
            "wildfire_agriculture_doi_nonconflation": True,
        },
        "doi_link_counts": counts,
        "sources": {
            "manuscript": {"path": str(args.manuscript), "sha256": digest(args.manuscript)},
            "registry": {"path": str(args.registry), "sha256": digest(args.registry)},
        },
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])),
            "sha256": digest(Path(__file__).resolve()),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "checks": result["checks"]}, indent=2))


if __name__ == "__main__":
    main()
