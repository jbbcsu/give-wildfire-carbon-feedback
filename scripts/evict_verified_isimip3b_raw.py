#!/usr/bin/env python3
"""Remove only reproducible ISIMIP files bound to completed source receipts.

The command is fail-closed: it verifies every candidate's current size and
SHA-512, the registered content-audit hash, and the registered derived GMST
output before deleting any file.  It then writes a permanent deletion receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tomllib


RECEIPT_PATTERN = "isimip3b_rimex_contiguous_*_complete_*.toml"


def digest(path: Path, algorithm: str) -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def build_plan(root: Path) -> list[dict[str, object]]:
    receipt_paths = sorted((root / "data/provenance").glob(RECEIPT_PATTERN))
    require(receipt_paths, "no completed ISIMIP source receipts found")
    candidates: list[dict[str, object]] = []
    seen: set[Path] = set()
    eligible_receipts = 0
    for receipt_path in receipt_paths:
        receipt = tomllib.loads(receipt_path.read_text(encoding="utf-8"))
        require(receipt.get("all_six_catalogue_files_byte_and_sha512_validated") is True,
                f"source checksum gate is closed: {receipt_path}")
        require(receipt.get("all_six_files_full_content_validated") is True,
                f"content gate is closed: {receipt_path}")
        files = receipt.get("files", [])
        # The earliest GFDL pilot uses a legacy nested receipt. Preserve that
        # raw block rather than infer deletion candidates from another schema.
        if not files:
            continue
        require(len(files) == 6, f"expected six files in {receipt_path}")
        eligible_receipts += 1
        gmst = receipt.get("same_realization_gmst", {})
        gmst_path = root / str(gmst.get("output", ""))
        require(gmst_path.is_file(), f"derived GMST output is missing: {gmst_path}")
        require(digest(gmst_path, "sha256") == gmst.get("output_sha256"),
                f"derived GMST hash differs: {gmst_path}")
        for item in files:
            matches = list((root / "data/raw/isimip3b").glob(f"**/{item['file_name']}"))
            require(len(matches) == 1, f"raw filename must resolve exactly once: {item['file_name']}")
            path = matches[0].resolve()
            require(path not in seen, f"duplicate raw candidate: {path}")
            require(path.is_file() and path.stat().st_size == int(item["bytes"]),
                    f"raw size differs: {path}")
            audit_path = root / str(item["content_audit"])
            require(audit_path.is_file(), f"content audit is missing: {audit_path}")
            require(digest(audit_path, "sha256") == item["content_audit_sha256"],
                    f"content-audit hash differs: {audit_path}")
            seen.add(path)
            candidates.append({
                "path": relative(path, root),
                "bytes": int(item["bytes"]),
                "sha512": str(item["sha512"]),
                "source_receipt": relative(receipt_path, root),
                "source_catalogue": str(receipt["source_catalogue"]),
                "resource_doi": str(receipt["resource_doi"]),
                "rights": str(receipt["rights"]),
            })
    require(eligible_receipts > 0 and len(candidates) == eligible_receipts * 6,
            "candidate count differs from completed receipt matrix")
    return candidates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    candidates = build_plan(root)
    total_bytes = sum(int(item["bytes"]) for item in candidates)
    if not args.execute:
        print(f"verified dry-run: {len(candidates)} files, {total_bytes} bytes")
        return

    # Recompute all source hashes before the first deletion.  This makes a
    # failed preflight non-destructive and binds the deletion to exact bytes.
    for index, item in enumerate(candidates, start=1):
        path = root / str(item["path"])
        require(digest(path, "sha512") == item["sha512"], f"raw SHA-512 differs: {path}")
        print(f"verified {index}/{len(candidates)} {item['path']}", flush=True)

    free_before = shutil.disk_usage(root).free
    for item in candidates:
        (root / str(item["path"])).unlink()
    free_after = shutil.disk_usage(root).free
    require(all(not (root / str(item["path"])).exists() for item in candidates),
            "one or more raw candidates remain after deletion")
    result = {
        "schema": "verified_isimip3b_local_raw_eviction_v1",
        "status": "deleted_reproducible_public_raw_files_after_full_preflight",
        "file_count": len(candidates),
        "registered_bytes_deleted": total_bytes,
        "filesystem_free_bytes_before": free_before,
        "filesystem_free_bytes_after": free_after,
        "filesystem_free_bytes_change": free_after - free_before,
        "recovery": "Re-query the registered ISIMIP dataset API and require the recorded filename, byte count, and SHA-512 before reuse.",
        "unique_or_derived_data_deleted": False,
        "files": candidates,
    }
    out = args.out if args.out.is_absolute() else root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = out.with_suffix(out.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(out)
    print(f"deleted {len(candidates)} verified files; registered bytes={total_bytes}")


if __name__ == "__main__":
    main()
