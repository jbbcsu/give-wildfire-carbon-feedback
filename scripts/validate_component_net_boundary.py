#!/usr/bin/env python3
"""Validate released EPA ozone, PM2.5-candidate, and net summaries fail-closed.

The validator reads only two small checked-in summaries plus source text. It
does not calibrate to article values, read ignored trial streams, or calculate
a replacement SCC.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "epa_globalaq_component_net_gate_config/v1"
COMPONENT_SCHEMA = [
    "discount.rate", "Pollutant", "Model", "mean_npd", "mean.npd.cert.eq",
    "npd_2.5", "npd_97.5", "median",
]
NET_SCHEMA = [
    "discount.rate", "Model", "mean_npd", "mean.npd.cert.eq", "npd_2.5",
    "npd_97.5", "median",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def read_csv_exact(path: Path, columns: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames == columns, f"unexpected schema: {path.name}")
        rows = list(reader)
    require(rows, f"empty summary: {path.name}")
    return rows


def finite_float(value: str, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"non-numeric {label}") from exc
    require(math.isfinite(number), f"non-finite {label}")
    return number


def validate_unique(rows: list[dict[str, str]], keys: tuple[str, ...], label: str) -> None:
    identities = [tuple(row[key] for key in keys) for row in rows]
    require(len(identities) == len(set(identities)), f"duplicate {label} rows")


def bind_files(root: Path, config: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, spec in config["bound_files"].items():
        path = root / spec["path"]
        require(path.is_file() and not path.is_symlink(), f"missing regular file: {spec['path']}")
        require(sha256(path) == spec["sha256"], f"hash mismatch: {spec['path']}")
        if "bytes" in spec:
            require(path.stat().st_size == spec["bytes"], f"size mismatch: {spec['path']}")
        paths[name] = path
    return paths


def validate_source_metadata(paths: dict[str, Path], config: dict[str, Any]) -> dict[str, Any]:
    texts = {
        name: path.read_text(encoding="utf-8")
        for name, path in paths.items()
        if name not in {"component_summary", "net_summary"}
    }
    for name, tokens in config["required_source_tokens"].items():
        missing = [token for token in tokens if token not in texts[name]]
        require(not missing, f"missing {name} source tokens: {missing}")

    search = config["boundary_metadata_search"]
    hits = []
    for name in search["files"]:
        lowered = texts[name].lower()
        for phrase in search["case_insensitive_phrases"]:
            if phrase.lower() in lowered:
                hits.append({"file": name, "phrase": phrase})
    require(len(hits) == search["expected_hits"], "burning-boundary metadata inventory changed")

    input_text = texts["input_builder"]
    rft_text = texts["reduced_form_tool"]
    npv_text = texts["npv_code"]
    return {
        "input_builder_uses_2024_dollars": (
            "gdp_2011_to_2024" in input_text and "dollar.year = 2024" in input_text
        ),
        "reduced_form_uses_2024_vsl": "$2024 VSL" in rft_text,
        "reduced_form_header_claims_2020": "Code adjusts all $ values for $2020" in rft_text,
        "npv_header_claims_2020": "Units: All $ values for $2020" in npv_text,
        "explicit_2024_to_2020_conversion_verified": False,
        "price_year_resolved": False,
        "repository_burning_boundary_hits": hits,
        "repository_machine_verifies_open_burning_exclusion": False,
        "article_boundary_is_external_to_repository": True,
        "component_and_net_aggregation_objects_are_distinct": True,
    }


def reconcile(root: Path, config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    require(config.get("schema") == SCHEMA, "unexpected config schema")
    require(set(config["hard_gates"].values()) == {False}, "all hard gates must remain false")

    repo = root / "vendor/globalAQ_rft"
    source = config["source"]
    require(git(repo, "rev-parse", "HEAD") == source["commit"], "vendor commit differs")
    require(git(repo, "remote", "get-url", "origin") == source["repository_url"] + ".git",
            "vendor origin differs")
    tree = git(repo, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    require(len(tree) == source["tree_entry_count"], "vendor tree entry count differs")

    observed = config["official_remote_observation"]
    require(observed["head"] == source["commit"] and observed["main"] == source["commit"],
            "recorded remote revision differs")
    require(observed["tags"] == [] and observed["releases"] == [],
            "recorded release inventory differs")

    paths = bind_files(root, config)
    metadata = validate_source_metadata(paths, config)
    summary = config["summary_contract"]
    require(summary["component_columns"] == COMPONENT_SCHEMA, "configured component schema differs")
    require(summary["net_columns"] == NET_SCHEMA, "configured net schema differs")
    component_rows = read_csv_exact(paths["component_summary"], COMPONENT_SCHEMA)
    net_rows = read_csv_exact(paths["net_summary"], NET_SCHEMA)
    validate_unique(component_rows, ("discount.rate", "Pollutant", "Model"), "component")
    validate_unique(net_rows, ("discount.rate", "Model"), "net")

    rate = summary["discount_rate"]
    models = set(summary["models"])
    pollutants = set(summary["component_pollutants"])
    selected_components = [row for row in component_rows if row["discount.rate"] == rate]
    selected_net = [row for row in net_rows if row["discount.rate"] == rate]
    require({row["Pollutant"] for row in selected_components} == pollutants,
            "2% component pollutant support differs")
    require({row["Model"] for row in selected_components} == models,
            "2% component model support differs")
    require(len(selected_components) == len(models) * len(pollutants),
            "2% component row count differs")
    require({row["Model"] for row in selected_net} == models and len(selected_net) == len(models),
            "2% net model support differs")

    component_by_model: dict[str, dict[str, float]] = {model: {} for model in models}
    for row in selected_components:
        component_by_model[row["Model"]][row["Pollutant"]] = finite_float(
            row["mean_npd"], f"{row['Pollutant']} {row['Model']} mean_npd"
        )
    net_by_model = {
        row["Model"]: finite_float(row["mean_npd"], f"net {row['Model']} mean_npd")
        for row in selected_net
    }
    model_reconciliation = {}
    for model in sorted(models):
        component_sum = sum(component_by_model[model].values())
        model_reconciliation[model] = {
            "ozone": component_by_model[model]["Ozone"],
            "pm25_candidate": component_by_model[model]["PM"],
            "component_sum": component_sum,
            "separate_net": net_by_model[model],
            "net_minus_component_sum": net_by_model[model] - component_sum,
        }

    means = {
        "ozone": sum(values["Ozone"] for values in component_by_model.values()) / len(models),
        "pm": sum(values["PM"] for values in component_by_model.values()) / len(models),
        "net": sum(net_by_model.values()) / len(models),
    }
    means["component_sum"] = means["ozone"] + means["pm"]
    means["net_minus_component_sum"] = means["net"] - means["component_sum"]
    expected = config["expected_checked_in_2pct_means"]
    tolerance = expected["absolute_tolerance"]
    for field in ("ozone", "pm", "component_sum", "net", "net_minus_component_sum"):
        require(abs(means[field] - expected[field]) <= tolerance,
                f"registered checked-in mean changed: {field}")

    article = config["article"]
    article_values = article["reported_2pct_ramsey_usd_per_tco2"]
    return {
        "schema": "epa_globalaq_component_net_gate_receipt/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "blocked_final_article_artifacts_and_metadata_unavailable",
        "source": {
            "repository_url": source["repository_url"],
            "commit": source["commit"],
            "tree_entry_count": len(tree),
            "official_remote_observation": observed,
            "bound_file_hashes_valid": True,
        },
        "released_2pct_ramsey": {
            "endpoint_roles": summary["component_output_role"],
            "net_role": summary["net_output_role"],
            "model_reconciliation": model_reconciliation,
            "model_mean_reconciliation": {
                "ozone": means["ozone"],
                "pm25_candidate": means["pm"],
                "component_sum": means["component_sum"],
                "separate_net": means["net"],
                "net_minus_component_sum": means["net_minus_component_sum"],
            },
            "same_stream_additivity_verified": False,
        },
        "article_alignment": {
            "doi": article["doi"],
            "reported_values_external_benchmark_only": article_values,
            "released_component_values_equal_article": False,
            "released_net_value_equals_article": False,
            "calibration_or_rescaling_performed": False,
        },
        "metadata_audit": metadata,
        "hard_gates": config["hard_gates"],
        "required_final_artifacts": [
            "article-generating versioned code and environment",
            "same-run trial/model ozone, PM2.5, and net streams with identifiers",
            "explicit final currency/price year and any conversion",
            "machine-readable emissions/species boundary confirming open-burning exclusion",
        ],
        "claim_status": (
            "released summaries reconciled as separate ozone, PM2.5-candidate, and net artifacts; "
            "non-wildfire boundary, price year, final-article reproduction, and GIVE transfer remain closed"
        ),
        "config": {
            "path": str(config_path.relative_to(root)),
            "sha256": sha256(config_path),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--config", type=Path,
        default=Path("config/epa_globalaq_component_net_gate_v1.json"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    result = reconcile(root, config_path)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else root / args.output
        require(not output.exists(), "fresh output path required")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
