#!/usr/bin/env python3
"""Integration-style tests for bounded SPEI chunking, receipts, and I/O."""
from __future__ import annotations

from argparse import Namespace
from pathlib import Path
import tempfile
from unittest.mock import patch

import numpy as np
import pandas as pd

import build_spei_grid_chunk as pipeline

from build_spei_grid_chunk import (
    ALGORITHM_VERSION,
    MonthlyCheckpoint,
    SourceInventory,
    SourceRecord,
    SpatialSlice,
    aggregate_daily_to_monthly,
    load_checkpoint,
    load_source_inventory,
    numerical_environment_identity,
    parse_spatial_slice,
    result_dataset,
    save_checkpoint,
    signature,
    support_audit,
    validate_output_netcdf,
    with_hash_envelope,
    write_netcdf_atomic,
)
from spei_monthly_engine import construct_monthly_spei
from validate_spei_competitor_contract import load_contract


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/spei_competitor_v1.toml"


def rejected(expected: str, function, *args, **kwargs) -> None:
    try:
        function(*args, **kwargs)
    except (ValueError, RuntimeError) as error:
        assert expected.lower() in str(error).lower(), error
    else:
        raise AssertionError(f"invalid input accepted; expected {expected!r}")


def synthetic_monthly() -> tuple[pd.DatetimeIndex, np.ndarray, np.ndarray]:
    dates = pd.date_range("1981-01-01", "2019-12-01", freq="MS")
    year = dates.year.to_numpy()
    month = dates.month.to_numpy()
    balance = (
        (month - 6.5) * 1.7
        + (((year - 1980) * 37 + month * 11) % 29 - 14) * 0.9
        + (((year - 1980) * month) % 7) * 0.13
    )
    et0 = np.full((len(dates), 1, 1), 100.0)
    return dates, et0 + balance[:, None, None], et0


def main() -> None:
    dates = pd.date_range("1984-01-01", "1984-02-29", freq="D")
    shape = (len(dates), 2, 1)
    precipitation = np.ones(shape)
    tmin = np.full(shape, 10.0)
    tmax = np.full(shape, 20.0)
    precipitation[4, 1, 0] = np.nan
    daily = aggregate_daily_to_monthly(
        dates,
        precipitation,
        tmin,
        tmax,
        np.array([40.0, 41.0]),
    )
    assert daily.precipitation_mm[:, 0, 0].tolist() == [31.0, 29.0]
    assert np.isnan(daily.precipitation_mm[0, 1, 0])
    assert daily.precipitation_mm[1, 1, 0] == 29.0
    assert daily.daily_complete_count[:, 1, 0].tolist() == [30, 29]
    assert daily.audit["monthly_incomplete"] == 1
    assert daily.audit["imputed_values"] == 0

    invalid_precipitation = np.ones(shape)
    invalid_precipitation[0, 0, 0] = -1.0
    rejected(
        "negative",
        aggregate_daily_to_monthly,
        dates,
        invalid_precipitation,
        tmin,
        tmax,
        np.array([40.0, 41.0]),
    )
    invalid_maximum = tmax.copy()
    invalid_maximum[0, 0, 0] = 9.0
    rejected(
        "tmax",
        aggregate_daily_to_monthly,
        dates,
        np.ones(shape),
        tmin,
        invalid_maximum,
        np.array([40.0, 41.0]),
    )
    rejected(
        "chronology",
        aggregate_daily_to_monthly,
        dates.delete(8),
        np.ones((len(dates) - 1, 2, 1)),
        tmin[:-1],
        tmax[:-1],
        np.array([40.0, 41.0]),
    )

    contract = load_contract(CONTRACT)
    us = load_source_inventory("nclimgrid", contract)
    globe = load_source_inventory("isimip", contract)
    assert len(us.records) == 468 and us.records[0].start_date == "1981-01-01"
    assert len(globe.records) == 16 and globe.records[-1].end_date == "2019-12-31"
    assert us.declared_file_set_sha512 != globe.declared_file_set_sha512

    args = Namespace(lat_start=0, lat_count=8, lon_start=0, lon_count=8)
    assert parse_spatial_slice(args, "isimip").cells == 64
    rejected(
        "at most",
        parse_spatial_slice,
        Namespace(lat_start=0, lat_count=9, lon_start=0, lon_count=8),
        "isimip",
    )

    with tempfile.TemporaryDirectory(prefix="spei_chunk_test_") as directory:
        temporary = Path(directory)
        checkpoint = MonthlyCheckpoint(
            months=daily.months,
            precipitation_mm=daily.precipitation_mm,
            et0_mm=daily.et0_mm,
            daily_complete_count=daily.daily_complete_count,
            calendar_day_count=daily.calendar_day_count,
            latitude=np.array([40.0, 41.0]),
            longitude=np.array([-105.0]),
            audit={**daily.audit, "files_schema_validated": 1, "unused_mean_metadata_validated": 1},
        )
        record = SourceRecord(
            name="synthetic.nc",
            path=temporary / "synthetic.nc",
            size_bytes=1,
            sha512="0" * 128,
            variable="synthetic",
            block="1984",
            start_date="1984-01-01",
            end_date="1984-02-29",
        )
        environment = numerical_environment_identity()
        block_signature = signature({"numerical_environment": environment})
        saved, receipt = save_checkpoint(
            temporary,
            checkpoint,
            source="synthetic",
            block="1984",
            block_signature=block_signature,
            records=[record],
        )
        loaded = load_checkpoint(
            temporary,
            source="synthetic",
            block="1984",
            block_signature=block_signature,
        )
        assert loaded is not None
        restored, restored_receipt = loaded
        assert receipt == restored_receipt
        assert np.allclose(saved.et0_mm, restored.et0_mm, equal_nan=True)
        rejected(
            "stale",
            load_checkpoint,
            temporary,
            source="synthetic",
            block="1984",
            block_signature="2" * 128,
        )
        altered_environment = dict(environment)
        altered_environment["numpy"] = "environment-mismatch-fixture"
        assert signature({"numerical_environment": altered_environment}) != block_signature
        with patch.object(
            pipeline,
            "numerical_environment_identity",
            return_value=altered_environment,
        ):
            rejected(
                "numerical environment",
                load_checkpoint,
                temporary,
                source="synthetic",
                block="1984",
                block_signature=block_signature,
            )

        months, monthly_p, monthly_e = synthetic_monthly()
        result = construct_monthly_spei(months, monthly_p, monthly_e)
        combined = MonthlyCheckpoint(
            months=months,
            precipitation_mm=monthly_p,
            et0_mm=monthly_e,
            daily_complete_count=np.broadcast_to(
                months.days_in_month.to_numpy(dtype=np.int16)[:, None, None],
                monthly_p.shape,
            ).copy(),
            calendar_day_count=months.days_in_month.to_numpy(dtype=np.int16),
            latitude=np.array([39.75]),
            longitude=np.array([-99.75]),
            audit={},
        )
        support = support_audit("isimip", combined, result)
        assert support["cells_with_all_36_valid_fits"] == 1
        dummy_inventory = SourceInventory(
            source="isimip",
            root=temporary,
            provenance_path=CONTRACT,
            provenance_sha512="3" * 128,
            source_id="synthetic_source",
            dataset_doi="https://example.invalid/synthetic",
            license="CC0-1.0",
            records=(),
            declared_file_set_sha512="4" * 128,
        )
        run_signature = "5" * 128
        dataset = result_dataset(
            "isimip",
            dummy_inventory,
            SpatialSlice(100, 101, 160, 161),
            run_signature,
            "6" * 128,
            "7" * 128,
            combined,
            result,
        )
        output = temporary / "synthetic_spei.nc"
        write_netcdf_atomic(output, dataset)
        dataset.close()
        validate_output_netcdf(
            output,
            source="isimip",
            run_signature=run_signature,
            spatial=SpatialSlice(100, 101, 160, 161),
        )
        assert output.stat().st_size > 0
        envelope = with_hash_envelope(
            {"schema_version": ALGORITHM_VERSION, "all_gates_false": True}
        )
        assert len(envelope["receipt_payload_sha512"]) == 128

    print("Bounded SPEI chunk pipeline tests passed; checkpoint and NetCDF receipts verified")


if __name__ == "__main__":
    main()
