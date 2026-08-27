#!/usr/bin/env python3
"""Assemble validated early, middle, and later candidate tables by family.

This is a lineage and continuity gate only. Candidate moisture families remain
separate, and the output does not authorize coefficient, damage, or SCC use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


PROJECT = Path(__file__).resolve().parents[1]
CONTRACT_ID = "continuous_candidate_period_assembly_v1"
KEYS = ["harvest_year", "lat", "lon_360", "crop"]
PERIODS = {"early": (1982, 1989), "middle": (1990, 2011), "later": (2012, 2016)}
FAMILIES = {"direct", "heat", "scpdsi"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT.resolve()))
    except ValueError as error:
        raise ValueError("candidate assembly paths must remain inside the project") from error


def require_boolean_false(frame: pd.DataFrame, name: str) -> None:
    if name not in frame or frame[name].isna().any():
        raise ValueError(f"required closed gate missing or null: {name}")
    normalized = frame[name].astype(str).str.lower()
    if not normalized.isin({"false", "0"}).all():
        raise ValueError(f"candidate unexpectedly opens {name}")


def validate_frame(
    frame: pd.DataFrame,
    *,
    crop: str,
    family: str,
    period: str,
) -> dict[str, object]:
    if family not in FAMILIES or period not in PERIODS:
        raise ValueError("unknown family or period")
    required = set(KEYS + ["yield_observed", "yield_t_ha"])
    if missing := required - set(frame.columns):
        raise ValueError(f"candidate missing fields {sorted(missing)}")
    if frame.empty or frame.duplicated(KEYS).any():
        raise ValueError("candidate is empty or has duplicate crop-grid-year keys")
    if set(frame.crop.astype(str)) != {crop}:
        raise ValueError("candidate crop differs from contract")
    start, end = PERIODS[period]
    years = pd.to_numeric(frame.harvest_year, errors="coerce")
    if not np.isfinite(years).all() or not np.equal(years, np.floor(years)).all():
        raise ValueError("candidate harvest years must be finite integers")
    if set(years.astype(int)) != set(range(start, end + 1)):
        raise ValueError("candidate does not cover the exact period")
    observed = frame.yield_observed
    if observed.isna().any() or not observed.astype(str).str.lower().isin({"true", "false", "1", "0"}).all():
        raise ValueError("yield_observed is not Boolean")
    observed_bool = observed.astype(str).str.lower().isin({"true", "1"})
    yields = pd.to_numeric(frame.yield_t_ha, errors="coerce")
    if not observed_bool.eq(yields.notna()).all():
        raise ValueError("yield flag and value missingness disagree")
    if not np.isfinite(yields.loc[observed_bool]).all() or (yields.loc[observed_bool] <= 0).any():
        raise ValueError("observed yields must be finite and positive")
    require_boolean_false(frame, "scc_authorized")
    if family == "direct":
        if set(frame.response_basis_contract_id.astype(str)) != {"gdhy_aggregate_irrigation_distribution_candidate_v1"}:
            raise ValueError("direct basis contract changed")
        require_boolean_false(frame, "fit_authorized")
        require_boolean_false(frame, "production_model_form_frozen")
    elif family == "heat":
        if set(frame.heat_control_basis_contract_id.astype(str)) != {"global_crop_stage_heat_control_basis_v1"}:
            raise ValueError("heat basis contract changed")
        for gate in (
            "family_stacking_authorized", "coefficient_export_authorized",
            "causal_interpretation_authorized", "production_model_selection_authorized",
            "production_fit_authorized", "response_draw_authorized",
            "damage_calculation_authorized", "future_projection_authorized",
            "selection_by_scc_authorized",
        ):
            require_boolean_false(frame, gate)
    else:
        if set(frame.response_basis_contract_id.astype(str)) != {"gdhy_aggregate_irrigation_scpdsi_candidate_v1"}:
            raise ValueError("scPDSI basis contract changed")
        for gate in ("fit_authorized", "causal_interpretation_authorized", "future_projection_authorized"):
            require_boolean_false(frame, gate)
        require_boolean_false(frame, "direct_weather_terms_included")
    return {
        "period": period,
        "year_start": start,
        "year_end": end,
        "rows": int(len(frame)),
        "observed_outcomes": int(observed_bool.sum()),
        "unique_cells": int(frame[["lat", "lon_360"]].drop_duplicates().shape[0]),
        "rows_by_year": {str(int(k)): int(v) for k, v in frame.groupby(years.astype(int)).size().items()},
        "observed_by_year": {str(int(k)): int(v) for k, v in observed_bool.groupby(years.astype(int)).sum().items()},
    }


def assemble(
    inputs: dict[str, Path],
    *,
    crop: str,
    family: str,
    output: Path,
) -> dict[str, object]:
    if set(inputs) != set(PERIODS):
        raise ValueError("declare exactly early, middle, and later inputs")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite continuous candidate: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(output.suffix + ".partial")
    if partial.exists():
        raise FileExistsError(f"stale partial output exists: {partial}")
    records: list[dict[str, object]] = []
    schema: pa.Schema | None = None
    writer: pq.ParquetWriter | None = None
    try:
        for period in PERIODS:
            path = inputs[period]
            table = pq.read_table(path)
            frame = table.to_pandas()
            record = validate_frame(frame, crop=crop, family=family, period=period)
            if schema is None:
                schema = table.schema
                writer = pq.ParquetWriter(partial, schema, compression="zstd")
            elif not table.schema.equals(schema):
                raise ValueError("candidate period schemas differ")
            assert writer is not None
            writer.write_table(table)
            record.update({"path": relative(path), "sha256": sha256(path), "bytes": path.stat().st_size})
            records.append(record)
        assert writer is not None
        writer.close()
        writer = None
        output_table = pq.read_table(partial)
        output_frame = output_table.to_pandas()
        if output_frame.duplicated(KEYS).any():
            raise ValueError("period assembly creates duplicate keys")
        if set(output_frame.harvest_year.astype(int)) != set(range(1982, 2017)):
            raise ValueError("assembled candidate is not continuous through 1982-2016")
        partial.replace(output)
    except Exception:
        if writer is not None:
            writer.close()
        if partial.exists():
            partial.unlink()
        raise
    return {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "status": "validated_continuous_candidate_1982_2016",
        "crop": crop,
        "family": family,
        "year_start": 1982,
        "year_end": 2016,
        "periods": records,
        "output": {"path": relative(output), "sha256": sha256(output), "bytes": output.stat().st_size, "rows": int(len(output_frame)), "observed_outcomes": int(output_frame.yield_observed.astype(bool).sum())},
        "families_stacked": False,
        "fit_performed": False,
        "coefficient_export_authorized": False,
        "causal_interpretation_authorized": False,
        "damage_calculation_authorized": False,
        "future_projection_authorized": False,
        "scc_authorized": False,
    }


def parse_inputs(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("input must have period=path form")
        period, filename = value.split("=", 1)
        if period in result:
            raise ValueError(f"duplicate input period {period}")
        result[period] = Path(filename)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True, help="early=PATH, middle=PATH, or later=PATH")
    parser.add_argument("--crop", required=True)
    parser.add_argument("--family", choices=sorted(FAMILIES), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()
    receipt = assemble(parse_inputs(args.input), crop=args.crop, family=args.family, output=args.out)
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], **receipt["output"]}, indent=2))


if __name__ == "__main__":
    main()
