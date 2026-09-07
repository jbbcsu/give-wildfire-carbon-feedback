#!/usr/bin/env python3
"""Validate the aggregate geographic/source-cluster audit artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import tomllib

from validate_global_continuous_geographic_cluster_contract import CONTRASTS, MODELS, validate as validate_contract


CONTRAST_PAIRS = {
    "quantity_minus_controls_only": ("quantity", "controls_only"),
    "quantity_distribution_minus_quantity": ("quantity_distribution", "quantity"),
    "scpdsi_mean_minus_quantity": ("scpdsi_mean", "quantity"),
    "scpdsi_stages_minus_quantity": ("scpdsi_stages", "quantity"),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def walk_keys(value: object) -> list[str]:
    if isinstance(value, dict):
        return [str(key) for key in value] + [key for item in value.values() for key in walk_keys(item)]
    if isinstance(value, list):
        return [key for item in value for key in walk_keys(item)]
    return []


def validate_payload(
    result: dict[str, object], config: dict[str, object], root: Path,
    result_path: Path | None = None, resource: dict[str, object] | None = None,
) -> dict[str, object]:
    require(result.get("schema") == "global_continuous_geographic_cluster_audit_v1", "result schema changed")
    require(result.get("role") == config["role"], "result role changed")
    require(result.get("status") == "completed_exploratory_geographic_and_source_cluster_diagnostic", "result status changed")
    require(result.get("config_sha256") == sha256(root / "config/global_continuous_geographic_cluster_v1.toml"), "config hash mismatch")
    require(result.get("protocol_sha256") == sha256(root / config["protocol_path"]), "protocol hash mismatch")
    require(result.get("preregistration_sha256") == sha256(root / "data/provenance/global_continuous_geographic_cluster_preregistration_20260907.json"), "preregistration hash mismatch")
    require(result.get("parent_result_sha256") == sha256(root / config["parent_result_path"]), "parent hash mismatch")
    require(result.get("implementation_sha256") == sha256(root / "scripts/global_continuous_geographic_cluster_audit.py"), "implementation hash mismatch")
    for gate in ("coefficient_exported", "row_predictions_exported", "model_promotion_authorized", "causal_response_authorized", "damage_or_scc_authorized"):
        require(result.get(gate) is False, f"closed result gate changed: {gate}")
    forbidden = {"beta", "betas", "coefficient", "coefficients", "prediction", "predictions"}
    require(not forbidden.intersection(walk_keys(result)), "forbidden fitted detail exported")

    bootstrap = result.get("bootstrap", {})
    require(bootstrap.get("cluster") == config["uncertainty"]["cluster"], "bootstrap cluster changed")
    require(bootstrap.get("resampling") == config["uncertainty"]["resampling"], "bootstrap resampling changed")
    require(bootstrap.get("replicates") == 5000 and bootstrap.get("seed") == 20260907, "bootstrap lock changed")
    require(bootstrap.get("generator") == "numpy.random.Generator(PCG64)", "bootstrap generator changed")

    parent = json.loads((root / config["parent_result_path"]).read_text(encoding="utf-8"))
    crops = result.get("crops", {})
    require(set(crops) == {"maize", "soy"}, "crop set changed")
    summary: dict[str, object] = {}
    for crop in ("maize", "soy"):
        payload = crops[crop]
        parent_metrics = parent["crops"][crop]["metrics"]
        expected_train = {parent_metrics[model]["train_pairs"] for model in MODELS}
        expected_test = {parent_metrics[model]["test_pairs"] for model in MODELS}
        require(expected_train == {payload.get("unique_training_pairs")}, "training support changed")
        require(expected_test == {payload.get("unique_terminal_pairs")}, "terminal support changed")
        require(payload.get("training_source_blocks", 0) >= 10, "training block support failed")
        require(payload.get("held_out_source_blocks", 0) >= 10, "held-out block support failed")
        blocks = payload.get("held_out_source_blocks_by_fold", {})
        require(set(blocks) == {str(fold) for fold in range(5)}, "fold block keys changed")
        require(all(value >= 2 for value in blocks.values()), "per-fold block support failed")
        require(sum(blocks.values()) == payload["held_out_source_blocks"], "block total mismatch")

        folds = payload.get("folds", [])
        require(len(folds) == 5 and {item.get("fold") for item in folds} == set(range(5)), "fold result set changed")
        require(sum(item.get("test_pairs", 0) for item in folds) == payload["unique_terminal_pairs"], "fold test total mismatch")
        for item in folds:
            require(item.get("train_pairs", 0) > 0 and item.get("test_pairs", 0) > 0, "empty fold support")
            require(item.get("held_out_source_blocks") == blocks[str(item["fold"])], "fold block count mismatch")
            require(set(item.get("metrics", {})) == set(MODELS), "fold model set changed")
            for metric in item["metrics"].values():
                require(math.isfinite(metric.get("rmse", math.nan)) and metric["rmse"] >= 0, "invalid fold RMSE")
                require(math.isfinite(metric.get("scaled_gram_condition", math.nan)) and metric["scaled_gram_condition"] <= 1e10, "condition gate failed")

        pooled = payload.get("pooled_metrics", {})
        require(set(pooled) == set(MODELS), "pooled model set changed")
        for metric in pooled.values():
            require(metric.get("test_pairs") == payload["unique_terminal_pairs"], "pooled support mismatch")
            require(math.isfinite(metric.get("rmse", math.nan)) and metric["rmse"] >= 0, "invalid pooled RMSE")
        contrasts = payload.get("paired_rmse_contrasts", {})
        require(set(contrasts) == set(CONTRASTS), "contrast set changed")
        for name, (left, right) in CONTRAST_PAIRS.items():
            contrast = contrasts[name]
            expected = pooled[left]["rmse"] - pooled[right]["rmse"]
            require(math.isclose(contrast.get("point_rmse_difference", math.nan), expected, rel_tol=0, abs_tol=1e-15), "point contrast mismatch")
            interval = contrast.get("cluster_bootstrap", {})
            values = [interval.get(key, math.nan) for key in ("p025", "median", "p975")]
            require(all(math.isfinite(value) for value in values), "nonfinite bootstrap interval")
            require(values[0] <= values[1] <= values[2], "bootstrap quantiles unordered")

        input_hashes = payload.get("input_hashes", {})
        require(set(input_hashes) == {"direct", "heat", "scpdsi"}, "input hash families changed")
        for item in config["inputs"]:
            if item["crop"] != crop:
                continue
            receipt_path = root / item["receipt_path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            observed = input_hashes[item["family"]]
            require(observed.get("receipt_sha256") == item["receipt_sha256"], "input receipt binding changed")
            require(observed.get("data_sha256") == receipt["output"]["sha256"], "input data binding changed")
        summary[crop] = {
            "training_pairs": payload["unique_training_pairs"],
            "terminal_pairs": payload["unique_terminal_pairs"],
            "held_out_source_blocks": payload["held_out_source_blocks"],
        }

    if result_path is not None:
        require(result_path.stat().st_size <= config["resources"]["result_bytes_maximum"], "result byte ceiling failed")
    if resource is not None:
        require(resource.get("monitor_status") == "completed" and resource.get("monitor_returncode") == 0, "resource monitor failed")
        require(resource.get("sampled_peak_group_rss_bytes", 2**63) <= config["resources"]["sampled_peak_resident_memory_bytes_maximum"], "sampled RSS ceiling failed")
        require(resource.get("audit_result_sha256") == sha256(result_path), "resource result hash mismatch")
        require(resource.get("audit_result_bytes") == result_path.stat().st_size, "resource result size mismatch")
        require(resource.get("large_work_authorized") is False, "large-work gate changed")

    return {
        "schema": "global_continuous_geographic_cluster_validation_v1",
        "status": "validated_exploratory_geographic_and_source_cluster_diagnostic",
        "result_sha256": sha256(result_path) if result_path is not None else None,
        "validator_sha256": sha256(Path(__file__)),
        "crops": summary,
        "coefficient_exported": False,
        "model_promotion_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--resource", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    validate_contract(args.config.resolve(), root)
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    result = json.loads(args.result.read_text(encoding="utf-8"))
    resource = json.loads(args.resource.read_text(encoding="utf-8"))
    validation = validate_payload(result, config, root, args.result.resolve(), resource)
    args.out.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("global continuous geographic/source-cluster result passed")


if __name__ == "__main__":
    main()
