#!/usr/bin/env python3
"""Independently reconstruct FishStat status sensitivity from the full export."""

from __future__ import annotations
import argparse, csv, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

YEARS = np.arange(1950, 2015)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()


def require(value: bool, message: str) -> None:
    if not value: raise ValueError(message)


def independent_metrics(o: np.ndarray, m: np.ndarray) -> dict[str, float]:
    def correlation(x: np.ndarray, y: np.ndarray) -> float:
        x = x - x.mean(); y = y - y.mean(); return float((x @ y) / math.sqrt(float(x @ x) * float(y @ y)))
    return {"level_pearson": correlation(o, m), "level_rmse": float(math.sqrt(math.fsum(float(x*x) for x in (m-o)) / len(o))), "first_difference_pearson": correlation(np.diff(o), np.diff(m)), "first_difference_rmse": float(math.sqrt(math.fsum(float(x*x) for x in (np.diff(m)-np.diff(o))) / (len(o)-1)))}


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--result",type=Path,required=True); p.add_argument("--panel-receipt",type=Path,required=True); p.add_argument("--temporal",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args(); require(not a.output.exists(),"fresh output required")
    result=json.loads(a.result.read_text()); panel=json.loads(a.panel_receipt.read_text()); require(result["schema"]=="fishmip_fao_status_sensitivity/v1","result differs")
    source=Path(panel["sources"]["input"]["path"]); require(digest(source)==panel["sources"]["input"]["sha256"],"full export hash differs"); temporal=json.loads(a.temporal.read_text()); require(digest(a.temporal)==result["sources"]["temporal_diagnostic"]["sha256"],"temporal hash differs")
    totals={name:{int(y):[] for y in YEARS} for name in result["status_families"]}; selected=0
    with source.open(newline="",encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["environment_class"]!="marine" or row["measure_code"]!="Q_tlw": continue
            selected+=1
            for year in YEARS:
                status=row[f"status_{year}"]; value=float(row[f"value_{year}"])
                for family,codes in result["status_families"].items():
                    if status in codes: totals[family][int(year)].append(value)
    observed={}
    for family,year_values in totals.items():
        raw=np.asarray([math.fsum(year_values[int(y)]) for y in YEARS]); observed[family]=raw/float(raw[YEARS>=2005].mean())
    lookup={(r["path_id"],r["start_year"]):r for r in result["comparisons"]}; checks=0; max_error=0.0
    for path in temporal["paths"]:
        pid=path["path_id"]; modeled=np.asarray([r[f"{pid}_normalized"] for r in temporal["annual"]])
        for start in [1950,1980]:
            mask=YEARS>=start; saved=lookup[(pid,start)]
            for family in result["status_families"]:
                rebuilt=independent_metrics(observed[family][mask],modeled[mask])
                for key,value in rebuilt.items(): max_error=max(max_error,abs(value-saved[family][key])); checks+=1
    require(checks==64 and max_error<=1e-12,"metric reconstruction differs")
    out={"schema":"fishmip_fao_status_sensitivity_validation/v1","created_at_utc":datetime.now(timezone.utc).isoformat(),"status":"pass","source":{"result":str(a.result),"result_sha256":digest(a.result),"full_export":str(source),"full_export_sha256":digest(source)},"validation":{"marine_records_selected":selected,"metric_checks":checks,"maximum_absolute_error":max_error,"direct_full_export_reconstruction":True},"claim_boundary":"observation-status sensitivity only; no calibration selection, attribution, welfare, damage, or SCC"}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); print(json.dumps(out,indent=2))


if __name__=="__main__": main()
