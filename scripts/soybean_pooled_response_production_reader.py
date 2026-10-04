#!/usr/bin/env python3
"""Token-gated projected-column reader for pooled soybean production inputs.

The factory validates the existing authorization token plus bindings to this
reader and its configuration before any declared outcome-bearing path can be
hashed or opened. The reader is dependency-injected into the existing adapter;
it never imports or invokes the response engine.
"""
from __future__ import annotations

import hashlib
import resource
import sys
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from pandas.api.types import is_bool_dtype, is_integer_dtype

import soybean_pooled_response_execution_gate as access_gate


class ReaderViolation(ValueError):
    """Raised when authorization, provenance, or source contracts fail."""


def require(value: bool, message: str) -> None:
    if not value:
        raise ReaderViolation(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def resolve_inside(root: Path, relative: str) -> Path:
    require(not Path(relative).is_absolute(), "declared paths must be repository-relative")
    path = (root / relative).resolve()
    require(path == root or root in path.parents, "declared path escapes repository root")
    return path


def _expected_metadata(config: dict[str, Any], family: str) -> dict[str, Any]:
    section = config["source_contracts"][family]
    return {name: value for name, value in section.items() if name not in {"features", "path_role"}}


class AuthorizedLevelReader:
    """Stateful family-separated loader created only after token validation."""

    def __init__(self, root: Path, config: dict[str, Any], declared: dict[str, dict[str, Any]], authorization: dict[str, Any]):
        self.root = root
        self.config = config
        self.declared = declared
        self.authorization = authorization
        self._verified: set[str] = set()
        self._country: pd.DataFrame | None = None
        self._active_source: str | None = None
        self._active_keys: pd.DataFrame | None = None
        self._events: list[dict[str, Any]] = []
        self._source_stats: dict[str, dict[str, Any]] = {}

    @property
    def declared_paths(self) -> dict[str, str]:
        return {name: item["path"] for name, item in self.declared.items()}

    def _verified_path(self, role: str) -> Path:
        require(role in self.declared, f"undeclared source role: {role}")
        item = self.declared[role]
        path = resolve_inside(self.root, item["path"])
        require(path.is_file(), f"declared source is absent: {role}")
        if role not in self._verified:
            require(digest(path) == item["pinned_sha256"], f"declared source hash differs: {role}")
            self._verified.add(role)
            self._events.append({"role": role, "action": "hash_verified_after_authorization"})
        return path

    def _load_country(self) -> pd.DataFrame:
        if self._country is not None:
            return self._country
        path = self._verified_path("country_proxy")
        columns = ["lat", "lon_360", "country_label", "country_count"]
        parquet = pq.ParquetFile(path)
        require(set(columns) <= set(parquet.schema_arrow.names), "country proxy schema is incomplete")
        country = parquet.read(columns=columns, use_threads=False).to_pandas()
        require(len(country) > 0, "country proxy is empty")
        require(not country.duplicated(["lat", "lon_360"]).any(), "country proxy has duplicate cells")
        require(is_integer_dtype(country["country_count"].dtype), "country_count must be integer")
        self._events.append({"role": "country_proxy", "action": "projected_columns_opened", "columns": columns, "rows": int(len(country))})
        self._country = country
        return country

    def _read_family(self, family: str) -> pd.DataFrame:
        section = self.config["source_contracts"][family]
        role = section["path_role"]
        features = list(section["features"])
        metadata = _expected_metadata(self.config, family)
        columns = ["lat", "lon_360", "harvest_year", "crop", "yield_observed", "yield_t_ha"] + features + list(metadata)
        path = self._verified_path(role)
        parquet = pq.ParquetFile(path)
        require(set(columns) <= set(parquet.schema_arrow.names), f"{family} source schema is incomplete")
        pieces: list[pd.DataFrame] = []
        constants = {name: set() for name in metadata}
        source_rows = 0
        observed_positive_rows = 0
        source_years: set[int] = set()
        omitted = set(metadata) | {"crop"}
        retained_columns = [name for name in columns if name not in omitted]
        for batch in parquet.iter_batches(batch_size=int(self.config["reader"]["batch_rows"]), columns=columns, use_threads=False):
            source_rows += batch.num_rows
            require(pc.all(pc.equal(batch.column(batch.schema.get_field_index("crop")), pa.scalar(self.config["sample"]["crop"]))).as_py(), f"{family} contains another crop")
            for name in metadata:
                constants[name].update(pc.unique(batch.column(batch.schema.get_field_index(name))).to_pylist())
            year_column = batch.column(batch.schema.get_field_index("harvest_year"))
            require(pa.types.is_integer(year_column.type) and year_column.null_count == 0, f"{family} harvest_year must be nonnull integer")
            years = year_column.to_numpy(zero_copy_only=False).astype(np.int64, copy=False)
            source_years.update(int(value) for value in np.unique(years))
            for name in ["lat", "lon_360"] + features:
                column = batch.column(batch.schema.get_field_index(name))
                require(column.null_count == 0, f"{family} {name} contains null values")
                values = np.asarray(column.to_numpy(zero_copy_only=False), dtype=float)
                require(np.isfinite(values).all(), f"{family} {name} contains nonfinite values")
            observed_column = batch.column(batch.schema.get_field_index("yield_observed"))
            require(pa.types.is_boolean(observed_column.type) and observed_column.null_count == 0, f"{family} yield_observed must be nonnull Boolean")
            observed = observed_column.to_numpy(zero_copy_only=False).astype(bool, copy=False)
            yield_column = batch.column(batch.schema.get_field_index("yield_t_ha"))
            yields = np.asarray(yield_column.to_numpy(zero_copy_only=False), dtype=float)
            finite_yield = np.isfinite(yields)
            require(np.array_equal(observed, finite_yield), f"{family} yield flag and finite magnitude differ")
            require(np.all(yields[observed] > 0), f"{family} observed yields must be positive")
            if np.any(observed):
                observed_batch = batch.filter(pa.array(observed))
                pieces.append(observed_batch.select(retained_columns).to_pandas())
                observed_positive_rows += int(observed.sum())
        require(source_rows > 0 and pieces, f"{family} source has no observed positive support")
        for name, expected in metadata.items():
            require(constants[name] == {expected}, f"{family} basis contract differs for {name}")
        year_min, year_max = int(self.config["sample"]["level_year_minimum"]), int(self.config["sample"]["level_year_maximum"])
        require(source_years == set(range(year_min, year_max + 1)), f"{family} full-source level years must equal {year_min}-{year_max}")
        frame = pd.concat(pieces, ignore_index=True)
        require(len(frame) == observed_positive_rows, f"{family} observed-row accumulation differs")
        require(not frame.duplicated(["lat", "lon_360", "harvest_year"]).any(), f"{family} source has duplicate cell-years")
        require(is_integer_dtype(frame["harvest_year"].dtype), f"{family} harvest_year must be integer")
        require(is_bool_dtype(frame["yield_observed"].dtype), f"{family} yield_observed must be Boolean")
        numeric = ["lat", "lon_360"] + features
        require(np.isfinite(frame[numeric].to_numpy(float)).all(), f"{family} contains nonfinite coordinates or features")
        observed = frame["yield_observed"].to_numpy(bool)
        yields = pd.to_numeric(frame["yield_t_ha"], errors="coerce").to_numpy(float)
        require(observed.all(), f"{family} accumulated a non-observed row")
        require(np.array_equal(observed, np.isfinite(yields)), f"{family} yield flag and finite magnitude differ")
        require(np.all(yields[observed] > 0), f"{family} observed yields must be positive")

        country = self._load_country()
        frame = frame.merge(country, on=["lat", "lon_360"], how="left", validate="many_to_one")
        singleton = frame["country_count"].eq(1) & frame["country_label"].notna() & frame["country_label"].astype(str).str.len().gt(0)
        frame = frame.loc[singleton].copy()
        common = ["lat", "lon_360", "harvest_year", "country_label", "country_count", "yield_observed", "yield_t_ha"]
        self._source_stats[family] = {
            "full_source_rows": int(source_rows),
            "full_source_years": sorted(source_years),
            "observed_positive_rows_accumulated": int(observed_positive_rows),
            "unobserved_rows_validated_not_accumulated": int(source_rows - observed_positive_rows),
            "singleton_country_rows_returned": int(len(frame)),
        }
        self._events.append({"role": role, "action": "projected_observed_rows_opened", "columns": columns, **self._source_stats[family]})
        return frame[common + features].reset_index(drop=True)

    def __call__(self, name: str) -> pd.DataFrame:
        require(name in {"direct", "scpdsi", "heat"}, "undeclared source family")
        if name in {"direct", "scpdsi"}:
            frame = self._read_family(name)
            self._active_source = name
            self._active_keys = frame[["lat", "lon_360", "harvest_year"]].copy()
            return frame
        require(self._active_source in {"direct", "scpdsi"} and self._active_keys is not None, "heat must be loaded after its moisture family")
        heat = self._read_family("heat")
        heat = heat.merge(self._active_keys.assign(_active=True), on=["lat", "lon_360", "harvest_year"], how="inner", validate="one_to_one")
        heat = heat.drop(columns="_active")
        require(len(heat) == len(self._active_keys), f"heat support differs from active {self._active_source} support")
        return heat

    def audit(self) -> dict[str, Any]:
        rss = peak_rss_bytes()
        require(rss < int(self.config["memory_cap_bytes"]), "reader memory cap exceeded")
        return {
            "authorization_validated_before_source_access": True,
            "synthetic_authorization": bool(self.authorization["synthetic"]),
            "verified_roles": sorted(self._verified),
            "events": list(self._events),
            "source_stats": dict(self._source_stats),
            "peak_rss_bytes": rss,
            "memory_cap_bytes": int(self.config["memory_cap_bytes"]),
            "memory_gate_passed": True,
        }


def build_authorized_reader(
    root: Path,
    config_path: Path,
    token_path: Path | None,
    *,
    manifest_path: Path | None = None,
    test_mode: bool = False,
) -> AuthorizedLevelReader:
    require(type(test_mode) is bool, "test_mode must be an explicit boolean")
    root, config_path = root.resolve(), config_path.resolve()
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    for name, binding in config["bindings"].items():
        path = resolve_inside(root, binding["path"])
        require(digest(path) == binding["sha256"], f"reader binding hash differs: {name}")
    require(digest(Path(__file__).resolve()) == config["reader_identity"]["sha256"], "reader implementation hash differs")
    production_manifest = resolve_inside(root, config["bindings"]["dry_run_manifest"]["path"])
    if test_mode:
        require(manifest_path is not None, "synthetic reader test requires an explicit manifest")
        selected_manifest = manifest_path.resolve()
    else:
        require(manifest_path is None or manifest_path.resolve() == production_manifest, "production manifest override is forbidden")
        selected_manifest = production_manifest
    gate_config = resolve_inside(root, config["bindings"]["gate_config"]["path"])
    try:
        authorization = access_gate.validate_authorization_token(token_path, selected_manifest, gate_config, root, test_mode=test_mode)
    except access_gate.GateViolation as error:
        raise ReaderViolation(f"reader authorization failed before source access: {error}") from error
    token = access_gate.read_json(token_path)  # token existence already checked by the gate
    require(token.get("production_reader_sha256") == config["reader_identity"]["sha256"], "token does not bind the production reader")
    require(token.get("production_reader_config_sha256") == digest(config_path), "token does not bind the production reader config")
    manifest = access_gate.read_json(selected_manifest)
    declared = manifest["production_declared_path_bindings"]
    require(set(declared) == {"direct", "heat", "scpdsi", "country_proxy"}, "production path-role closure differs")
    for role, item in declared.items():
        require(isinstance(item, dict) and isinstance(item.get("path"), str) and isinstance(item.get("pinned_sha256"), str), f"declared source binding is incomplete: {role}")
        resolve_inside(root, item["path"])
    require(not any(config["claim_gates"].values()), "reader config opens a claim gate")
    return AuthorizedLevelReader(root, config, declared, authorization)
