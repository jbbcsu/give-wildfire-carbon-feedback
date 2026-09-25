#!/usr/bin/env python3
"""Validate local Markdown links and images in the manuscript bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--document", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    require(not output.exists(), "fresh output required")

    checked: list[dict] = []
    external = 0
    local = 0
    for supplied in args.document:
        document = supplied if supplied.is_absolute() else root / supplied
        require(document.is_file(), f"document missing: {document}")
        for target in LINK_PATTERN.findall(document.read_text()):
            target = target.strip().strip("<>")
            if target.startswith(("https://", "http://")):
                external += 1
                continue
            if target.startswith("#"):
                continue
            path_part = target.split("#", 1)[0]
            require(path_part, f"empty local link: {document}")
            linked = (document.parent / path_part).resolve()
            require(linked.is_relative_to(root), f"local link escapes project: {document}: {target}")
            require(linked.is_file(), f"local link missing: {document}: {target}")
            local += 1
            checked.append(
                {
                    "document": str(document.relative_to(root)),
                    "target": target,
                    "resolved": str(linked.relative_to(root)),
                    "sha256": digest(linked),
                }
            )

    result = {
        "schema": "manuscript_link_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "checks": {
            "documents": len(args.document),
            "local_links_resolved": local,
            "external_links_syntax_scanned": external,
            "missing_local_links": 0,
            "local_links_escaping_project": 0,
        },
        "local_targets": checked,
        "sources": {
            str((document if document.is_absolute() else root / document).resolve().relative_to(root)): {
                "sha256": digest((document if document.is_absolute() else root / document).resolve())
            }
            for document in args.document
        },
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(root)),
            "sha256": digest(Path(__file__).resolve()),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "checks": result["checks"]}, indent=2))


if __name__ == "__main__":
    main()
