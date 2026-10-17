#!/usr/bin/env python3
"""Audit vendored PerCX mechanics and write a non-result readiness receipt."""
import ast
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_percx(path: Path):
    spec = importlib.util.spec_from_file_location("vendored_percx", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def unused_decay_argument(source: str) -> bool:
    tree = ast.parse(source)
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "PFC_species_response")
    return not any(isinstance(n, ast.Name) and n.id == "decay_rate" and isinstance(n.ctx, ast.Load) for n in ast.walk(func))

def main() -> int:
    cfg = json.loads((ROOT / "config/permafrost_feedback_contract_v1.json").read_text())
    source = ROOT / cfg["percx"]["source_path"]
    params = ROOT / cfg["percx"]["parameter_path"]
    with params.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    model = load_percx(source)
    t = np.arange(0.0, 101.0)
    zero = np.zeros_like(t)
    warm = np.minimum(t * 0.03, 3.0)
    p = rows[0]
    args = tuple(float(p[k]) for k in ("A_CO2", "A_CH4", "tau"))
    zco2, zch4 = model.PFC_species_response(zero, t, *args, 1400.0, float(p["decay"]))
    wco2, wch4 = model.PFC_species_response(warm, t, *args, 1400.0, float(p["decay"]))
    receipt = {
        "schema": "permafrost_feedback_readiness_receipt/v1",
        "status": cfg["status"],
        "give_integration_authorized": cfg["scope"]["give_integration_authorized"],
        "scc_adjustment_authorized": cfg["scope"]["scc_adjustment_authorized"],
        "vendored_hashes_match": all((digest(ROOT / cfg["percx"][key]) == cfg["percx"][key.replace("_path", "_sha256")]) for key in ("source_path", "parameter_path", "license_path")),
        "parameter_rows_in_archive": len(rows),
        "article_reported_retained_parameter_rows": 775,
        "parameter_count_reconciled": len(rows) == 775,
        "decay_argument_used_in_released_species_function": not unused_decay_argument(source.read_text()),
        "mechanical_checks": {
            "zero_temperature_zero_emissions": bool(np.all(zco2 == 0) and np.all(zch4 == 0)),
            "warming_emissions_nonnegative": bool(np.all(wco2 >= 0) and np.all(wch4 >= 0)),
            "finite_pool_respected": bool(float(np.sum(wco2 + wch4)) <= 1400.0 + 1e-9),
            "fixed_six_to_one_carbon_ratio_in_first_parameter": abs(args[0] / args[1] - 6.0) < 1e-10
        },
        "climate_or_scc_result_created": False
    }
    out = ROOT / "provenance/permafrost_feedback_readiness_receipt_v1.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
