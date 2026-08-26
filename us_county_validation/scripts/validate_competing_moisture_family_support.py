#!/usr/bin/env python3
"""Require identical U.S. outcome/holdout support across moisture families."""
from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = PROJECT_ROOT / "config/us_county_drought_predictor_contract_v1.toml"
KEYS = ["county_geoid", "outcome_crop", "harvest_year", "irrigation_practice"]
FOLD_COLUMNS = set(KEYS) | {
    "spatial_fold", "is_temporal_holdout", "is_climate_extreme", "validation_design"
}
FORBIDDEN_DROUGHT_DIRECT = re.compile(
    r"(^|_)(pr|precip|precipitation|prcp|tas|temperature|tavg|tmin|tmax|pet|heat)(_|$)",
    re.IGNORECASE,
)
FORBIDDEN_DIRECT_INDEX = re.compile(r"(^|_)(pdsi|spei|drought_index)(_|$)", re.IGNORECASE)
OUTCOME_LEAKAGE = re.compile(
    r"(^|_)(yield|production|outcome_value|dependent_variable)(_|$)", re.IGNORECASE
)
DROUGHT_FEATURE = re.compile(r"(^|_)(pdsi|spei|drought|index)(_|$)", re.IGNORECASE)


def read_table(path: str) -> pd.DataFrame:
    source = Path(path)
    return pd.read_parquet(source) if source.suffix.lower() in {".parquet", ".pq"} else pd.read_csv(source)


def parse_bool(series: pd.Series, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        if series.isna().any():
            raise ValueError(f"{label} contains missing values")
        return series.astype(bool)
    values = series.astype("string").str.strip().str.lower()
    if values.isna().any() or (~values.isin(["true", "false"])).any():
        raise ValueError(f"{label} must contain only true/false")
    return values.eq("true")


def normalize_keys(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    if missing := set(KEYS) - set(frame.columns):
        raise ValueError(f"{label} lacks common outcome keys {sorted(missing)}")
    result = frame.copy()
    result["county_geoid"] = result.county_geoid.astype("string").str.strip()
    if result.county_geoid.str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError(f"{label} county_geoid must be five digits")
    for column in ["outcome_crop", "irrigation_practice"]:
        result[column] = result[column].astype("string").str.strip()
        if result[column].isna().any() or result[column].eq("").any():
            raise ValueError(f"{label} {column} must be nonblank")
    result["harvest_year"] = pd.to_numeric(result.harvest_year, errors="raise").astype("int64")
    if result.duplicated(KEYS).any():
        raise ValueError(f"{label} contains duplicate common outcome keys")
    return result.sort_values(KEYS).reset_index(drop=True)


def key_index(frame: pd.DataFrame) -> pd.MultiIndex:
    return pd.MultiIndex.from_frame(frame[KEYS], names=KEYS)


def validate_folds(frame: pd.DataFrame) -> pd.DataFrame:
    if missing := FOLD_COLUMNS - set(frame.columns):
        raise ValueError(f"common fold table lacks {sorted(missing)}")
    result = normalize_keys(frame, "Common fold table")
    result["spatial_fold"] = pd.to_numeric(result.spatial_fold, errors="raise").astype("int64")
    result["is_temporal_holdout"] = parse_bool(result.is_temporal_holdout, "is_temporal_holdout")
    result["is_climate_extreme"] = parse_bool(result.is_climate_extreme, "is_climate_extreme")
    result["validation_design"] = result.validation_design.astype("string").str.strip()
    if result.validation_design.nunique() != 1 or result.validation_design.eq("").any():
        raise ValueError("common folds require exactly one nonblank validation_design")
    if result.spatial_fold.nunique() < 2:
        raise ValueError("common folds do not populate at least two spatial folds")
    if result.groupby("county_geoid", observed=True).spatial_fold.nunique().gt(1).any():
        raise ValueError("a county changes spatial fold across outcome years")
    if not result.is_temporal_holdout.any() or result.is_temporal_holdout.all():
        raise ValueError("common temporal holdout is empty or contains every row")
    if result.groupby("harvest_year", observed=True).is_temporal_holdout.nunique().gt(1).any():
        raise ValueError("temporal holdout status differs within a harvest year")
    training_years = result.loc[~result.is_temporal_holdout, "harvest_year"]
    holdout_years = result.loc[result.is_temporal_holdout, "harvest_year"]
    if int(training_years.max()) >= int(holdout_years.min()):
        raise ValueError("final temporal holdout is not a terminal block after all training years")
    if not result.is_climate_extreme.any() or result.is_climate_extreme.all():
        raise ValueError("common extreme holdout is empty or contains every row")
    return result


def load_contract(path: Path = DEFAULT_CONTRACT) -> dict[str, object]:
    try:
        contract = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"cannot read drought predictor contract {path}") from error
    if not isinstance(contract.get("pdsi"), dict) or not isinstance(contract.get("spei"), dict):
        raise ValueError("drought predictor contract lacks PDSI/SPEI sections")
    if contract.get("response_estimation_authorized") is not False or contract.get("scc_use_authorized") is not False:
        raise ValueError("drought predictor contract unexpectedly authorizes estimation/SCC use")
    return contract


def validate_numeric_features(result: pd.DataFrame, columns: list[str], family_id: str) -> None:
    if not columns:
        raise ValueError(f"family {family_id} contains no recognized predictor columns")
    for column in columns:
        numeric = pd.to_numeric(result[column], errors="raise")
        if not np.isfinite(numeric.to_numpy(dtype=float)).all():
            raise ValueError(f"family {family_id} predictor {column} contains missing/nonfinite values")


def validate_family(
    frame: pd.DataFrame,
    family_id: str,
    expected_keys: pd.MultiIndex,
    first_temporal_holdout: int,
    contract: dict[str, object],
) -> pd.DataFrame:
    result = normalize_keys(frame, f"Family {family_id}")
    if not key_index(result).equals(expected_keys):
        missing = len(expected_keys.difference(key_index(result)))
        extra = len(key_index(result).difference(expected_keys))
        raise ValueError(f"family {family_id} differs from common support: missing={missing}, extra={extra}")
    if "feature_family" not in result:
        raise ValueError(f"family {family_id} lacks feature_family")
    values = result.feature_family.astype("string").str.strip()
    if values.nunique() != 1 or values.iloc[0] != family_id:
        raise ValueError(f"family {family_id} feature_family identity differs")
    if leaking := sorted(
        column for column in result.columns
        if column not in KEYS and OUTCOME_LEAKAGE.search(column)
    ):
        raise ValueError(f"family {family_id} contains outcome/leakage columns {leaking}")
    if family_id == "direct_weather":
        if forbidden := sorted(column for column in result.columns if FORBIDDEN_DIRECT_INDEX.search(column)):
            raise ValueError(f"direct-weather family contains drought-index columns {forbidden}")
        validate_numeric_features(
            result,
            [column for column in result.columns if FORBIDDEN_DROUGHT_DIRECT.search(column)],
            family_id,
        )
    elif family_id == "pdsi" or family_id.startswith("spei_"):
        if forbidden := sorted(column for column in result.columns if FORBIDDEN_DROUGHT_DIRECT.search(column)):
            raise ValueError(f"drought family {family_id} contains direct-weather columns {forbidden}")
        required = {
            "index_calibration_start_year", "index_calibration_end_year", "index_source_id",
            "irrigation_in_index",
        }
        if family_id.startswith("spei_"):
            required |= {"index_scale_months", "index_distribution"}
        if missing := required - set(result.columns):
            raise ValueError(f"drought family {family_id} lacks {sorted(missing)}")
        family_contract = contract["pdsi" if family_id == "pdsi" else "spei"]
        assert isinstance(family_contract, dict)
        starts = pd.to_numeric(result.index_calibration_start_year, errors="raise").astype("int64")
        ends = pd.to_numeric(result.index_calibration_end_year, errors="raise").astype("int64")
        if starts.nunique() != 1 or ends.nunique() != 1 or int(starts.iloc[0]) > int(ends.iloc[0]):
            raise ValueError(f"drought family {family_id} has inconsistent calibration metadata")
        expected_calibration = (
            int(family_contract["calibration_start_year"]),
            int(family_contract["calibration_end_year"]),
        )
        if (int(starts.iloc[0]), int(ends.iloc[0])) != expected_calibration:
            raise ValueError(f"drought family {family_id} calibration differs from the locked contract")
        if first_temporal_holdout <= int(ends.iloc[0]):
            raise ValueError(
                f"drought family {family_id} calibration ends in {int(ends.iloc[0])}, "
                f"not before temporal holdout {first_temporal_holdout}"
            )
        if parse_bool(result.irrigation_in_index, f"{family_id} irrigation_in_index").any():
            raise ValueError(f"climatic drought family {family_id} cannot claim irrigation in the index")
        source = result.index_source_id.astype("string").str.strip()
        if source.nunique() != 1 or source.iloc[0] != str(family_contract["source_id"]):
            raise ValueError(f"drought family {family_id} source differs from the locked contract")
        if family_id.startswith("spei_"):
            scales = pd.to_numeric(result.index_scale_months, errors="raise").astype("int64")
            distributions = result.index_distribution.astype("string").str.strip()
            allowed_scales = {int(value) for value in family_contract["candidate_scales_months"]}
            allowed_distributions = {
                str(family_contract["primary_distribution_candidate"]),
                str(family_contract["sensitivity_distribution"]),
            }
            if scales.nunique() != 1 or int(scales.iloc[0]) not in allowed_scales:
                raise ValueError(f"drought family {family_id} uses an unlocked SPEI scale")
            if distributions.nunique() != 1 or distributions.iloc[0] not in allowed_distributions:
                raise ValueError(f"drought family {family_id} uses an unlocked SPEI distribution")
        metadata = required | set(KEYS) | {
            "feature_family", "index_name", "index_scale_months", "index_scale_role",
            "index_distribution", "index_calibration_role", "response_estimation_authorized",
            "scc_authorized", "damage_authorized", "causal_claim_authorized", "analysis_role",
            "source_role",
        }
        validate_numeric_features(
            result,
            [column for column in result.columns if column not in metadata and DROUGHT_FEATURE.search(column)],
            family_id,
        )
    else:
        raise ValueError(f"unrecognized moisture family identity {family_id}")
    for flag in [
        "response_estimation_authorized", "scc_authorized", "damage_authorized",
        "causal_claim_authorized",
    ]:
        if flag in result and parse_bool(result[flag], f"{family_id} {flag}").any():
            raise ValueError(f"historical family support unexpectedly authorizes {flag}")
    return result


def validate_support(
    folds: pd.DataFrame,
    families: dict[str, pd.DataFrame],
    contract: dict[str, object] | None = None,
) -> dict[str, object]:
    common = validate_folds(folds)
    contract = load_contract() if contract is None else contract
    if "direct_weather" not in families or not ({"pdsi"} & set(families) or any(key.startswith("spei_") for key in families)):
        raise ValueError("comparison requires direct_weather and at least one PDSI/SPEI family")
    expected = key_index(common)
    first_temporal = int(common.loc[common.is_temporal_holdout, "harvest_year"].min())
    summaries: dict[str, object] = {}
    for family_id in sorted(families):
        validated = validate_family(families[family_id], family_id, expected, first_temporal, contract)
        summaries[family_id] = {
            "rows": len(validated),
            "counties": int(validated.county_geoid.nunique()),
            "years": [int(validated.harvest_year.min()), int(validated.harvest_year.max())],
        }
    return {
        "status": "common_outer_holdout_support_validated",
        "outcome_rows": len(common),
        "families": summaries,
        "spatial_folds": int(common.spatial_fold.nunique()),
        "temporal_holdout_rows": int(common.is_temporal_holdout.sum()),
        "temporal_holdout_first_year": first_temporal,
        "extreme_holdout_rows": int(common.is_climate_extreme.sum()),
        "validation_design": str(common.validation_design.iloc[0]),
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
    }


def parse_family(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("family must be FAMILY_ID=PATH")
    family, path = value.split("=", 1)
    if not family or not path:
        raise argparse.ArgumentTypeError("family must be FAMILY_ID=PATH")
    return family, path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folds", required=True)
    parser.add_argument("--family", action="append", type=parse_family, required=True)
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    family_paths = dict(args.family)
    if len(family_paths) != len(args.family):
        raise ValueError("duplicate family identifiers")
    audit = validate_support(
        read_table(args.folds),
        {family: read_table(path) for family, path in family_paths.items()},
        load_contract(Path(args.contract)),
    )
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"validated {audit['outcome_rows']} common outcome rows across "
        f"{len(audit['families'])} moisture families; no causal/damage/SCC claim"
    )


if __name__ == "__main__":
    main()
