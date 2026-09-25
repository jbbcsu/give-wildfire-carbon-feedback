#!/usr/bin/env python3
"""Validate and register all market/adaptation/tail paired GIVE results."""

from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
CASES=[
 ("hultgren_pair_008_002","horizontal_output","data/interim/paired_market_008_002_horizontal_results.csv","data/provenance/paired_market_008_002_horizontal_job_20260924.json","data/provenance/quantity_market_fund_008_002_horizontal_20260924.json"),
 ("hultgren_pair_008_002","fixed_input_cost","data/interim/paired_market_008_002_fixed_results.csv","data/provenance/paired_market_008_002_fixed_job_20260924.json","data/provenance/quantity_market_fund_008_002_fixed_20260924.json"),
 ("hultgren_pair_010_004","horizontal_output","data/interim/quantity_anchored_replacement_adaptation_tail_results_20260924.csv","data/provenance/quantity_anchored_replacement_adaptation_tail_job_20260924.json","data/provenance/quantity_replacement_adaptation_tail_ensemble_input_20260924.json"),
 ("hultgren_pair_010_004","fixed_input_cost","data/interim/paired_market_010_004_fixed_results.csv","data/provenance/paired_market_010_004_fixed_job_20260924.json","data/provenance/quantity_market_fund_010_004_fixed_20260924.json"),
 ("hultgren_pair_050_006","horizontal_output","data/interim/paired_market_050_006_horizontal_results.csv","data/provenance/paired_market_050_006_horizontal_job_20260924.json","data/provenance/quantity_market_fund_050_006_horizontal_20260924.json"),
 ("hultgren_pair_050_006","fixed_input_cost","data/interim/paired_market_050_006_fixed_results.csv","data/provenance/paired_market_050_006_fixed_job_20260924.json","data/provenance/quantity_market_fund_050_006_fixed_20260924.json"),
]


def digest(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for block in iter(lambda:f.read(8*1024*1024),b""): h.update(block)
 return h.hexdigest()


def require(value:bool,message:str)->None:
 if not value: raise ValueError(message)


def main()->None:
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("--diagnostic-receipt",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args(); require(not a.output.exists(),"fresh output required")
 diagnostic=json.loads(a.diagnostic_receipt.read_text()); require(diagnostic["schema"]=="epa_fair_hultgren_quantity_partial_scc_diagnostic/v1","diagnostic receipt differs"); expected_path=Path(diagnostic["output"]["path"]); require(digest(expected_path)==diagnostic["output"]["sha256"],"diagnostic hash differs")
 expected=pd.read_csv(expected_path); expected=expected.loc[expected.pulse_size_gtc.eq(0.000025)]; keys=["climate_model","adaptation","tail_rule","elasticity_id","yield_to_supply_mapping","discount_rate_label"]
 frames=[]; sources=[]; peak=0; max_error=0; max_bound=0; max_aggregate=0; max_region=0
 for elasticity,mapping,result_name,job_name,input_name in CASES:
  result_path=ROOT/result_name; job_path=ROOT/job_name; input_path=ROOT/input_name; require(result_path.is_file() and job_path.is_file() and input_path.is_file(),f"case artifact absent: {elasticity} {mapping}")
  frame=pd.read_csv(result_path); require(len(frame)==624,"case support differs")
  if "elasticity_id" not in frame: frame["elasticity_id"]=elasticity
  if "yield_to_supply_mapping" not in frame: frame["yield_to_supply_mapping"]=mapping
  require(frame.elasticity_id.eq(elasticity).all() and frame.yield_to_supply_mapping.eq(mapping).all(),"case labels differ")
  require(not frame.duplicated(keys).any(),"case keys duplicate"); require(frame.baseline_agriculture_error_usd.eq(0).all() and frame.baseline_cpc_error.eq(0).all(),"baseline identity differs"); require(frame.regional_increment_error_billion_usd2005.max()<=1e-12 and frame.aggregated_increment_error_usd.max()<=0.05,"level reconstruction differs"); require((frame.absolute_error<=frame.numerical_error_bound_usd2005_per_tco2+1e-15).all(),"paired error exceeds bound")
  comparison=frame.merge(expected.loc[expected.elasticity_id.eq(elasticity)&expected.yield_to_supply_mapping.eq(mapping),keys+["partial_scc_diagnostic_usd2005_per_tco2","partial_scc_diagnostic_usd2020_per_tco2"]],on=keys,how="outer",validate="one_to_one",indicator=True); require(len(comparison)==624 and comparison._merge.eq("both").all(),"diagnostic keys differ"); require(comparison.expected_usd2005_per_tco2.eq(comparison.partial_scc_diagnostic_usd2005_per_tco2).all() and comparison.expected_usd2020_per_tco2.eq(comparison.partial_scc_diagnostic_usd2020_per_tco2).all(),"diagnostic values differ")
  job=json.loads(job_path.read_text()); require(job["status"]=="completed" and job["returncode"]==0,"job failed"); peak=max(peak,int(job["sampled_peak_group_rss_bytes"])); max_error=max(max_error,float(frame.absolute_error.max())); max_bound=max(max_bound,float(frame.numerical_error_bound_usd2005_per_tco2.max())); max_aggregate=max(max_aggregate,float(frame.aggregated_increment_error_usd.max())); max_region=max(max_region,float(frame.regional_increment_error_billion_usd2005.max())); frames.append(frame); sources.append({"elasticity_id":elasticity,"yield_to_supply_mapping":mapping,"result":{"path":result_name,"bytes":result_path.stat().st_size,"sha256":digest(result_path)},"job":{"path":job_name,"sha256":digest(job_path),**job},"regional_input_receipt":{"path":input_name,"sha256":digest(input_path)}})
 combined=pd.concat(frames,ignore_index=True); require(len(combined)==3744 and not combined.duplicated(keys).any(),"combined support differs")
 summaries={}
 for (rate,elasticity,mapping),group in combined.groupby(["discount_rate_label","elasticity_id","yield_to_supply_mapping"],sort=True):
  v=group.expected_usd2020_per_tco2; summaries.setdefault(rate,{}).setdefault(elasticity,{})[mapping]={"cells":len(v),"mean_usd2020_per_tco2":float(v.mean()),"median_usd2020_per_tco2":float(v.median()),"minimum_usd2020_per_tco2":float(v.min()),"maximum_usd2020_per_tco2":float(v.max()),"negative_cells":int((v<0).sum())}
 result={"schema":"quantity_full_structural_paired_ensemble/v1","created_at_utc":datetime.now(timezone.utc).isoformat(),"status":"paired_full_registered_market_adaptation_tail_design_pass","support":{"climate_models":26,"market_specifications":6,"adaptations":3,"tail_rules":2,"discount_schedules":4,"paired_paths":936,"result_rows":3744},"summary":summaries,"validation":{"baseline_agriculture_and_cpc_exact_every_run":True,"all_3744_external_values_reconstructed_exactly":True,"maximum_regional_increment_error_billion_usd2005":max_region,"maximum_annual_aggregation_cancellation_error_usd":max_aggregate,"maximum_paired_vs_external_error_usd2005_per_tco2":max_error,"maximum_propagated_bound_usd2005_per_tco2":max_bound,"all_paired_errors_below_bounds":True,"maximum_sampled_process_group_rss_bytes":peak},"sources":{"diagnostic":{"path":str(expected_path),"sha256":digest(expected_path),"receipt":str(a.diagnostic_receipt),"receipt_sha256":digest(a.diagnostic_receipt)},"cases":sources},"claim_gates":{"paired_registered_structural_design":True,"probabilistic_uncertainty":False,"empirical_coefficient_uncertainty":False,"full_precipitation_agriculture_scc":False},"limitations":["The six market specifications, three adaptation scenarios, and two tail rules are balanced design choices, not probability draws.","The response remains the annual maize rainfall-quantity channel and excludes timing, drought, temperature, other crops, irrigation adaptation, trade, storage, and adaptation costs."],"implementation":{"path":str(Path(__file__).resolve().relative_to(ROOT)),"sha256":digest(Path(__file__).resolve())}}
 a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); print(json.dumps({"status":result["status"],"support":result["support"],"validation":result["validation"],"summary_2pct":summaries["2.0%"]},indent=2))


if __name__=="__main__": main()
