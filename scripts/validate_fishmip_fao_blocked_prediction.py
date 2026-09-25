#!/usr/bin/env python3
"""Independently reconstruct the blocked FishMIP/FAO prediction scores."""

from __future__ import annotations
import argparse,csv,hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
import numpy as np

YEARS=np.arange(1950,2015)


def digest(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
 return h.hexdigest()


def require(value:bool,message:str)->None:
 if not value: raise ValueError(message)


def score(o,p):
 relative=(p-o)/o
 return {"relative_rmse":math.sqrt(math.fsum(float(x*x) for x in relative)/len(o)),"relative_mae":math.fsum(float(abs(x)) for x in relative)/len(o),"log_rmse":math.sqrt(math.fsum(float(x*x) for x in (np.log(p)-np.log(o)))/len(o))}


def main():
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("--result",type=Path,required=True); p.add_argument("--panel-receipt",type=Path,required=True); p.add_argument("--temporal",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args(); require(not a.output.exists(),"fresh output required")
 result=json.loads(a.result.read_text()); panel=json.loads(a.panel_receipt.read_text()); require(result["schema"]=="fishmip_fao_blocked_level_prediction/v1","result differs"); source=Path(panel["sources"]["input"]["path"]); require(digest(source)==panel["sources"]["input"]["sha256"],"full source differs"); temporal=json.loads(a.temporal.read_text()); require(digest(a.temporal)==result["sources"]["temporal"]["sha256"],"temporal differs")
 codes=result["support"]["status_families"]; totals={family:{int(y):[] for y in YEARS} for family in codes}
 with source.open(newline="",encoding="utf-8") as f:
  for row in csv.DictReader(f):
   if row["environment_class"]!="marine" or row["measure_code"]!="Q_tlw": continue
   for y in YEARS:
    for family,family_codes in codes.items():
     if row[f"status_{y}"] in family_codes: totals[family][int(y)].append(float(row[f"value_{y}"]))
 cal=(YEARS>=1990)&(YEARS<=1999); test=(YEARS>=2000)&(YEARS<=2014); saved={(r["status_family"],r["path_id"]):r for r in result["results"]}; checks=0; maximum=0.0
 for family,year_values in totals.items():
  observed=np.asarray([math.fsum(year_values[int(y)]) for y in YEARS]); baseline=np.repeat(float(observed[cal].mean()),test.sum()); baseline_score=score(observed[test],baseline)
  for path in temporal["paths"]:
   pid=path["path_id"]; modeled=np.asarray([r[f"{pid}_mean_density"] for r in temporal["annual"]]); scale=float(observed[cal].mean()/modeled[cal].mean()); model_score=score(observed[test],modeled[test]*scale); row=saved[(family,pid)]
   for label,rebuilt in [("constant_mean_benchmark",baseline_score),("scaled_fishmip",model_score)]:
    for key,value in rebuilt.items(): maximum=max(maximum,abs(value-row[label][key])); checks+=1
   require((model_score["relative_rmse"]<baseline_score["relative_rmse"])==row["fishmip_beats_benchmark_relative_rmse"],"benchmark comparison differs")
 require(checks==48 and maximum<=1e-12,"blocked scores differ")
 out={"schema":"fishmip_fao_blocked_level_prediction_validation/v1","created_at_utc":datetime.now(timezone.utc).isoformat(),"status":"pass","source":{"result":str(a.result),"result_sha256":digest(a.result),"full_export":str(source),"full_export_sha256":digest(source)},"validation":{"metric_checks":checks,"maximum_absolute_error":maximum,"direct_full_export_reconstruction":True},"claim_boundary":"predictive diagnostic only; no model/status selection, causal attribution, welfare, damage, or SCC"}; a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); print(json.dumps(out,indent=2))


if __name__=="__main__": main()
