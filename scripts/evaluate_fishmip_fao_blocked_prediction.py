#!/usr/bin/env python3
"""Evaluate frozen-scale FishMIP level prediction on a later FAO block."""

from __future__ import annotations
import argparse, csv, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

YEARS=np.arange(1950,2015); CAL=(1990,1999); TEST=(2000,2014)


def digest(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
 return h.hexdigest()


def require(value:bool,message:str)->None:
 if not value: raise ValueError(message)


def score(observed:np.ndarray,predicted:np.ndarray)->dict[str,float]:
 relative=(predicted-observed)/observed
 return {"relative_rmse":float(np.sqrt(np.mean(relative**2))),"relative_mae":float(np.mean(np.abs(relative))),"log_rmse":float(np.sqrt(np.mean((np.log(predicted)-np.log(observed))**2)))}


def main()->None:
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("--status-result",type=Path,required=True); p.add_argument("--ledger-receipt",type=Path,required=True); p.add_argument("--temporal",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args(); require(not a.output.exists(),"fresh output required")
 status=json.loads(a.status_result.read_text()); ledger=json.loads(a.ledger_receipt.read_text()); require(status["schema"]=="fishmip_fao_status_sensitivity/v1" and ledger["schema"]=="fao_fishstat_marine_status_ledger/v1","source schema differs"); require(digest(a.temporal)==status["sources"]["temporal_diagnostic"]["sha256"],"temporal identity differs")
 ledger_path=Path(ledger["output"]["path"]); require(digest(ledger_path)==ledger["output"]["sha256"],"ledger identity differs"); temporal=json.loads(a.temporal.read_text()); require([r["year"] for r in temporal["annual"]]==YEARS.tolist(),"years differ")
 totals={family:{int(y):0.0 for y in YEARS} for family in status["status_families"]}
 with ledger_path.open(newline="",encoding="utf-8") as f:
  for row in csv.DictReader(f):
   year=int(row["year"])
   if year not in totals["A_only"]: continue
   for family,codes in status["status_families"].items():
    if row["status_code"] in codes: totals[family][year]+=float(row["tonnes_live_weight"])
 cal=(YEARS>=CAL[0])&(YEARS<=CAL[1]); test=(YEARS>=TEST[0])&(YEARS<=TEST[1]); results=[]
 for family,values in totals.items():
  observed=np.asarray([values[int(y)] for y in YEARS]); require((observed>0).all(),"observed series nonpositive"); baseline=np.repeat(float(observed[cal].mean()),test.sum()); baseline_score=score(observed[test],baseline)
  for path in temporal["paths"]:
   pid=path["path_id"]; modeled=np.asarray([r[f"{pid}_mean_density"] for r in temporal["annual"]]); scale=float(observed[cal].mean()/modeled[cal].mean()); model_score=score(observed[test],modeled[test]*scale); results.append({"status_family":family,"path_id":pid,"calibration_scale_tonnes_per_density_unit":scale,"constant_mean_benchmark":baseline_score,"scaled_fishmip":model_score,"fishmip_minus_benchmark":{key:model_score[key]-baseline_score[key] for key in baseline_score},"fishmip_beats_benchmark_relative_rmse":model_score["relative_rmse"]<baseline_score["relative_rmse"]})
 result={"schema":"fishmip_fao_blocked_level_prediction/v1","created_at_utc":datetime.now(timezone.utc).isoformat(),"status":"post_existing_evidence_blocked_level_prediction_complete","design":{"calibration_years":list(CAL),"holdout_years":list(TEST),"calibration":"one multiplicative scale equalizing calibration-block arithmetic means","benchmark":"constant calibration-block observed mean","metrics":["relative_rmse","relative_mae","log_rmse"]},"support":{"status_families":status["status_families"],"paths":4,"comparisons":len(results)},"results":results,"sources":{"status_result":{"path":str(a.status_result),"sha256":digest(a.status_result)},"ledger":{"path":str(ledger_path),"sha256":digest(ledger_path),"receipt":str(a.ledger_receipt),"receipt_sha256":digest(a.ledger_receipt)},"temporal":{"path":str(a.temporal),"sha256":digest(a.temporal)}},"claim_gates":{"blocked_predictive_diagnostic":True,"model_or_status_selection":False,"causal_climate_response":False,"welfare_damage_or_scc":False},"limitations":["The split is evaluated after related historical evidence was inspected and is not a pristine preregistered test.","Observed landings combine ecology, effort, management, markets, technology, and reporting.","The four paths are not probability draws and no winner is selected."],"implementation":{"path":str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])),"sha256":digest(Path(__file__).resolve())}}
 a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); print(json.dumps({"status":result["status"],"results":[{"family":r["status_family"],"path":r["path_id"],"fishmip_rmse":r["scaled_fishmip"]["relative_rmse"],"benchmark_rmse":r["constant_mean_benchmark"]["relative_rmse"],"beats":r["fishmip_beats_benchmark_relative_rmse"]} for r in results]},indent=2))


if __name__=="__main__": main()
