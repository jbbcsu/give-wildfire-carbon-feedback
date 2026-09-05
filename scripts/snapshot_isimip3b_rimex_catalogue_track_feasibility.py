#!/usr/bin/env python3
"""Screen the official ISIMIP catalogue for complete RIME-X member tracks.

Only API metadata are read. No climate payload is downloaded or opened.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import re
import resource
import ssl
import tomllib
from urllib.parse import urlencode, urlparse
import urllib.request
from typing import Callable

from validate_isimip3b_rimex_catalogue_track_feasibility_contract import validate as validate_contract


PERIOD_RE = re.compile(r"_(\d{4})_(\d{4})\.nc$")
PLAN_FIELDS = (
    "esm_id", "member_id", "scenario", "variable", "dataset_id", "dataset_name",
    "dataset_version", "file_id", "file_name", "file_start_year", "file_end_year",
    "size_bytes", "sha512", "file_url", "rights", "public", "restricted",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def observed_rss_bytes() -> int:
    raw = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return raw if platform.system() == "Darwin" else raw * 1024


def fetch_json(url: str) -> dict:
    parsed = urlparse(url)
    require(parsed.scheme == "https" and parsed.netloc == "data.isimip.org", "unexpected catalogue host")
    request = urllib.request.Request(url, headers={"User-Agent": "GIVE-RIMEX-catalogue-track-feasibility/1"})
    try:
        import certifi
    except ImportError:
        context = ssl.create_default_context()
    else:
        context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=60, context=context) as response:
        return json.load(response)


def fetch_all(url: str, fetch: Callable[[str], dict]) -> list[dict]:
    results: list[dict] = []
    next_url: str | None = url
    expected_count: int | None = None
    while next_url:
        payload = fetch(next_url)
        count = int(payload.get("count", -1))
        require(count >= 0, "catalogue payload lacks a nonnegative count")
        expected_count = count if expected_count is None else expected_count
        require(count == expected_count, "catalogue pagination count changed")
        page_results = payload.get("results")
        require(isinstance(page_results, list), "catalogue results are not a list")
        results.extend(page_results)
        candidate_next = payload.get("next")
        next_url = str(candidate_next) if candidate_next else None
    require(expected_count == len(results), "catalogue pagination did not return the declared count")
    return results


def query_urls(config: dict) -> dict[tuple[str, str], str]:
    source, screen = config["source"], config["screen"]
    urls: dict[tuple[str, str], str] = {}
    for scenario in screen["scenarios"]:
        for variable in screen["variables"]:
            parameters = {
                "simulation_round": source["simulation_round"],
                "product": source["product"],
                "region": source["region"],
                "time_step": source["time_step"],
                "bias_adjustment": source["bias_adjustment"],
                "climate_scenario": scenario,
                "climate_variable": variable,
            }
            require("climate_forcing" not in parameters and "ensemble_member" not in parameters, "discovery query was pre-filtered")
            urls[(scenario, variable)] = f"{source['catalogue_api']}?{urlencode(parameters)}"
    return urls


def _periods(dataset: dict, source: dict) -> list[tuple[int, int, dict]]:
    periods: list[tuple[int, int, dict]] = []
    for item in dataset.get("files", []):
        match = PERIOD_RE.search(str(item.get("name", "")))
        require(match is not None, f"file lacks a closed year block: {item.get('name')}")
        start, end = map(int, match.groups())
        require(start <= end, "reversed file year block")
        checksum = str(item.get("checksum", ""))
        require(item.get("checksum_type") == "sha512" and len(checksum) == 128, "file SHA-512 metadata missing")
        require(str(item.get("version")) == source["dataset_version"], "file version changed")
        require(int(item.get("size", 0)) > 0, "file size is not positive")
        require(str(item.get("file_url", "")).startswith("https://files.isimip.org/"), "unexpected climate file URL")
        periods.append((start, end, item))
    periods.sort(key=lambda value: (value[0], value[1], str(value[2].get("id", ""))))
    require(periods, "dataset has no files")
    require(len({str(item.get("id", "")) for _, _, item in periods}) == len(periods), "duplicate file id")
    for previous, current in zip(periods, periods[1:]):
        require(current[0] == previous[1] + 1, f"noncontiguous file years: {previous[:2]} then {current[:2]}")
    return periods


def _covers_window(periods: list[tuple[int, int, dict]], start: int, end: int) -> bool:
    covered: set[int] = set()
    for file_start, file_end, _ in periods:
        covered.update(range(max(start, file_start), min(end, file_end) + 1))
    return covered == set(range(start, end + 1))


def evaluate(config_path: Path, preregistration_path: Path, root: Path, fetch: Callable[[str], dict] = fetch_json) -> tuple[list[dict[str, object]], dict[str, object]]:
    preregistration = validate_contract(config_path, root)
    require(sha256(preregistration_path) == sha256(root / "data/provenance/isimip3b_rimex_catalogue_track_feasibility_preregistration_20260905.json"), "preregistration path changed")
    stored_preregistration = json.loads(preregistration_path.read_text(encoding="utf-8"))
    require(stored_preregistration == preregistration, "stored preregistration differs from validated contract")
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    source, screen = config["source"], config["screen"]
    urls = query_urls(config)

    cells: dict[tuple[str, str], dict[tuple[str, str], tuple[dict, list[tuple[int, int, dict]]]]] = {}
    query_counts: dict[str, int] = {}
    for (scenario, variable), url in urls.items():
        cell: dict[tuple[str, str], tuple[dict, list[tuple[int, int, dict]]]] = {}
        results = fetch_all(url, fetch)
        query_counts[f"{scenario}/{variable}"] = len(results)
        for dataset in results:
            spec = dataset.get("specifiers", {})
            expected = {
                "simulation_round": source["simulation_round"], "product": source["product"],
                "region": source["region"], "time_step": source["time_step"],
                "bias_adjustment": source["bias_adjustment"], "climate_scenario": scenario,
                "climate_variable": variable,
            }
            require(all(spec.get(key) == value for key, value in expected.items()), "dataset specifiers changed")
            esm, member = str(spec.get("climate_forcing", "")), str(spec.get("ensemble_member", ""))
            require(esm and member, "dataset lacks ESM/member identity")
            key = (esm, member)
            require(key not in cell, f"duplicate dataset for {scenario}/{variable}/{esm}/{member}")
            require(str(dataset.get("version")) == source["dataset_version"], "dataset version changed")
            require(dataset.get("public") is True and dataset.get("restricted") is False, "dataset is not public/unrestricted")
            require(dataset.get("rights", {}).get("short") == source["rights"], "dataset rights changed")
            require(source["resource_doi"] in {item.get("doi") for item in dataset.get("resources", [])}, "dataset resource DOI changed")
            periods = _periods(dataset, source)
            for start, end in zip(screen["window_starts"], screen["window_ends"], strict=True):
                require(_covers_window(periods, int(start), int(end)), f"incomplete window {start}-{end} for {scenario}/{variable}/{esm}/{member}")
            require(sum(int(item.get("size", 0)) for _, _, item in periods) == int(dataset.get("size", 0)), "dataset/file byte totals differ")
            cell[key] = (dataset, periods)
        cells[(scenario, variable)] = cell

    required_cells = set(urls)
    require(set(cells) == required_cells, "catalogue query matrix incomplete")
    eligible_tracks = set.intersection(*(set(cell) for cell in cells.values()))
    all_tracks = set.union(*(set(cell) for cell in cells.values()))
    incomplete_tracks = sorted(all_tracks - eligible_tracks)

    rows_by_file: dict[str, dict[str, object]] = {}
    for esm, member in sorted(eligible_tracks):
        for scenario, variable in sorted(required_cells):
            dataset, periods = cells[(scenario, variable)][(esm, member)]
            for file_start, file_end, item in periods:
                if not any(file_start <= int(end) and file_end >= int(start) for start, end in zip(screen["window_starts"], screen["window_ends"], strict=True)):
                    continue
                file_id = str(item.get("id", ""))
                row = {
                    "esm_id": esm, "member_id": member, "scenario": scenario, "variable": variable,
                    "dataset_id": str(dataset.get("id", "")), "dataset_name": str(dataset.get("name", "")),
                    "dataset_version": str(dataset.get("version", "")), "file_id": file_id,
                    "file_name": str(item.get("name", "")), "file_start_year": file_start, "file_end_year": file_end,
                    "size_bytes": int(item.get("size", 0)), "sha512": str(item.get("checksum", "")),
                    "file_url": str(item.get("file_url", "")), "rights": source["rights"],
                    "public": "true", "restricted": "false",
                }
                require(file_id not in rows_by_file or rows_by_file[file_id] == row, "file id maps to conflicting metadata")
                rows_by_file[file_id] = row

    rows = sorted(rows_by_file.values(), key=lambda row: (str(row["esm_id"]), str(row["member_id"]), str(row["scenario"]), str(row["variable"]), int(row["file_start_year"])))
    members_per_family: dict[str, int] = {}
    for esm, _ in eligible_tracks:
        members_per_family[esm] = members_per_family.get(esm, 0) + 1
    capped_capacity = sum(min(int(screen["maximum_members_per_esm_family"]), count) for count in members_per_family.values())
    metadata_feasible = capped_capacity >= int(screen["minimum_esm_member_tracks"]) and len(members_per_family) >= int(screen["minimum_esm_families"])
    status = "metadata_feasible_only_no_ensemble_selected" if metadata_feasible else "catalogue_track_gate_failed_insufficient_complete_tracks"
    maximum_rss = observed_rss_bytes()
    ceiling = int(config["resources"]["maximum_peak_resident_memory_bytes"])
    require(maximum_rss < ceiling, "peak RSS exceeded 2 GiB")
    rounded_rss = ((maximum_rss + 64 * 1024**2 - 1) // (64 * 1024**2)) * (64 * 1024**2)
    audit: dict[str, object] = {
        "schema": "isimip3b_rimex_catalogue_track_feasibility_audit_v1",
        "status": status,
        "preregistration": {"path": preregistration_path.relative_to(root).as_posix(), "sha256": sha256(preregistration_path)},
        "config": {"path": config_path.relative_to(root).as_posix(), "sha256": sha256(config_path)},
        "official_catalogue_api": source["catalogue_api"],
        "query_filters_excluded": ["climate_forcing", "ensemble_member"],
        "query_counts": query_counts,
        "query_count": len(urls),
        "eligible_complete_esm_member_tracks": [{"esm_id": esm, "member_id": member} for esm, member in sorted(eligible_tracks)],
        "eligible_complete_track_count": len(eligible_tracks),
        "eligible_esm_family_count": len(members_per_family),
        "eligible_track_capacity_after_two_member_family_cap": capped_capacity,
        "minimum_required_tracks": int(screen["minimum_esm_member_tracks"]),
        "minimum_required_families": int(screen["minimum_esm_families"]),
        "incomplete_track_count": len(incomplete_tracks),
        "incomplete_tracks": [{"esm_id": esm, "member_id": member} for esm, member in incomplete_tracks],
        "balanced_dataset_count": len(eligible_tracks) * len(required_cells),
        "unique_required_source_file_count": len(rows),
        "unique_required_source_file_catalogue_bytes": sum(int(row["size_bytes"]) for row in rows),
        "window_starts": screen["window_starts"], "window_ends": screen["window_ends"],
        "all_metadata_public_unrestricted_cc0": True,
        "global_daily_files_read": 0, "climate_payload_bytes_downloaded": 0,
        "peak_rss_observed_rounded_up_to_64_mib_bytes": rounded_rss,
        "peak_rss_gate_bytes": ceiling, "peak_rss_gate_passed": True,
        "final_ensemble_selected": False, "storage_plan_authorized": False,
        "member_independence_established": False, "adverse_mri_stability_resolved": False,
        "acquisition_authorized": False, "dependence_fit_authorized": False,
        "fair_feature_response_authorized": False, "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
        "interpretation": (
            f"The official catalogue exposes {len(eligible_tracks)} complete ESM-member tracks across all three registered SSPs, "
            f"daily pr/tas, and four pairwise-nonoverlapping 21-year windows. The locked design requires at least "
            f"{screen['minimum_esm_member_tracks']} tracks from at least {screen['minimum_esm_families']} families. "
            "This metadata screen selects no ensemble and authorizes no acquisition, fit, FAIR response, crop response, damage, or SCC calculation."
        ),
    }
    return rows, audit


def write_plan(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=PLAN_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    rows, audit = evaluate(args.config.resolve(), args.preregistration.resolve(), root)
    write_plan(args.plan.resolve(), rows)
    audit["plan"] = {"path": args.plan.resolve().relative_to(root).as_posix(), "sha256": sha256(args.plan.resolve())}
    audit["implementation"] = {"path": Path(__file__).resolve().relative_to(root).as_posix(), "sha256": sha256(Path(__file__).resolve())}
    args.audit.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"ISIMIP3b catalogue track screen: {audit['status']}; tracks={audit['eligible_complete_track_count']}; files={audit['unique_required_source_file_count']}")


if __name__ == "__main__":
    main()
