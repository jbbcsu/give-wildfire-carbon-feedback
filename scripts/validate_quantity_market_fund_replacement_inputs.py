#!/usr/bin/env python3
"""Independently reconstruct every alternative market FUND-region input row."""

from __future__ import annotations
import argparse, csv, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RECEIPTS=[
 "data/provenance/quantity_market_fund_008_002_horizontal_20260924.json",
 "data/provenance/quantity_market_fund_008_002_fixed_20260924.json",
 "data/provenance/quantity_market_fund_010_004_fixed_20260924.json",
 "data/provenance/quantity_market_fund_050_006_horizontal_20260924.json",
 "data/provenance/quantity_market_fund_050_006_fixed_20260924.json",
]
ADAPTATION={"fixed":(0.0,0.0),"trend":(0.003,0.35),"upper":(0.007,0.70)}
TAILS=["uncapped","published_analogue_p01_p99"]
PULSE=0.000025; CHUNK=16; VALUE="maize_gross_production_value_common_price_2014_2016_usd"


def digest(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for block in iter(lambda:f.read(8*1024*1024),b""): h.update(block)
 return h.hexdigest()


def require(value:bool,message:str)->None:
 if not value: raise ValueError(message)


def main()->None:
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("--output",type=Path,required=True); a=p.parse_args(); require(not a.output.exists(),"fresh output required")
 receipts=[json.loads((ROOT/name).read_text()) for name in RECEIPTS]; require(all(r["schema"]=="quantity_market_fund_replacement_input/v1" for r in receipts),"receipt schema differs")
 source=receipts[0]["sources"]; panel_path=Path(source["panel"]["path"]); slopes_path=Path(source["slopes"]["path"]); fair_path=Path(source["fair"]["path"]); mapping_path=Path(source["fund_mapping"]["path"]); order_path=Path(source["fund_order"]["path"])
 for r in receipts:
  for key,path in [("panel",panel_path),("slopes",slopes_path),("fair",fair_path),("fund_mapping",mapping_path),("fund_order",order_path)]: require(r["sources"][key]["sha256"]==digest(path),f"{key} identity differs")
 panel=pd.read_parquet(panel_path); slopes=pd.read_csv(slopes_path); fair=pd.read_csv(fair_path); years=np.arange(2020,2301,dtype=int); temperature=fair.loc[fair.pulse_size_gtc.eq(PULSE)&fair.year.isin(years)].sort_values("year").difference_k.to_numpy(float); require(len(temperature)==281,"FAIR support differs")
 with mapping_path.open(newline="",encoding="utf-8-sig") as f: mapping={r["ISO3"]:r["fundregion"] for r in csv.DictReader(f)}
 with order_path.open(newline="",encoding="utf-8") as f: regions=[r["fund_region"] for r in csv.DictReader(f)]
 region_index={r:i for i,r in enumerate(regions)}; models=sorted(slopes.source.unique()); central_receipt=json.loads(Path(receipts[0]["sources"]["market"]["receipt"]).read_text()); damage_receipt=json.loads(Path(central_receipt["sources"]["central_paths"]["receipt"]).read_text()); lower=float(damage_receipt["tail_rules"]["published_analogue_p01_p99"]["lower_log_yield_per_gtc"]); upper=float(damage_receipt["tail_rules"]["published_analogue_p01_p99"]["upper_log_yield_per_gtc"])
 prepared={}
 for model in models:
  selected=slopes.loc[slopes.source.eq(model)&slopes.slope_available,["iso3","patterns.area"]]; require(not selected.duplicated("iso3").any(),"duplicate slope")
  slope_map=dict(zip(selected.iso3,selected["patterns.area"])); frame=panel.loc[panel.iso3.isin(slope_map)].copy(); frame["independent_slope"]=frame.iso3.map(slope_map); frame=frame.sort_values(["iso3","native_lat_index","native_lon_index"]).reset_index(drop=True); require(not frame.empty,"empty model frame")
  beta=frame.independent_slope.to_numpy(float)/frame.annual_precip_mean_mm.to_numpy(float); first=frame.quantity_first_order_index.to_numpy(float)*beta; second=frame.quantity_second_order_index.to_numpy(float)*beta*beta; values=frame[VALUE].to_numpy(float); iso=frame.iso3.to_numpy(); starts=np.r_[0,np.flatnonzero(iso[1:]!=iso[:-1])+1]; countries=iso[starts]; country_value=np.add.reduceat(values,starts); region_ids=np.asarray([region_index[mapping[c]] for c in countries],dtype=int); prepared[model]=(first,second,values,starts,country_value,region_ids)
 total_rows=0; max_abs=0.0; max_rel=0.0; cases=[]
 for receipt_name,r in zip(RECEIPTS,receipts):
  spec=r["specification"]; supply=float(spec["supply_elasticity"]); demand=float(spec["demand_elasticity_magnitude"]); exponent=1.0 if spec["yield_to_supply_mapping"]=="horizontal_output" else 1.0+supply; output_path=Path(r["output"]["path"]); require(digest(output_path)==r["output"]["sha256"],"regional output hash differs"); compared=0
  with output_path.open(newline="",encoding="utf-8") as f:
   reader=csv.DictReader(f)
   for model in models:
    first,second,values,starts,country_value,region_ids=prepared[model]
    for begin in range(0,len(years),CHUNK):
     end=min(begin+CHUNK,len(years)); block_years=years[begin:end]; t=temperature[begin:end]; raw=first[:,None]*t[None,:]+second[:,None]*t[None,:]*t[None,:]
     for adaptation,(rate,cap) in ADAPTATION.items():
      attenuation=1.0-np.minimum(rate*np.maximum(block_years-2020,0),cap)
      for tail in TAILS:
       response=raw if tail=="uncapped" else np.clip(raw/PULSE,lower,upper)*PULSE; adapted=np.where(response<0,response*attenuation[None,:],response); country_output=np.add.reduceat(np.exp(exponent*adapted)*values[:,None],starts,axis=0); ratio=country_output/country_value[:,None]; shift=np.log(ratio); price=-shift/(supply+demand); z=(1.0-demand)*price; multiplier=np.ones_like(z); nz=z!=0; multiplier[nz]=np.expm1(z[nz])/z[nz]; country_damage=-country_value[:,None]*shift/(1.0+supply)*multiplier*float(central_receipt["currency"]["central_scalar"])/1e9; regional=np.zeros((16,len(block_years))); np.add.at(regional,region_ids,country_damage)
       for j,year in enumerate(block_years):
        for i,region in enumerate(regions):
         row=next(reader,None); require(row is not None,"regional output ended early"); require(row["climate_model"]==model and int(row["year"])==int(year) and row["adaptation"]==adaptation and row["tail_rule"]==tail and row["fund_region"]==region,"regional key order or value differs"); observed=float(row["marginal_damage_difference_billion_usd2005"]); expected=float(regional[i,j]); error=abs(observed-expected); max_abs=max(max_abs,error); max_rel=max(max_rel,error/max(abs(expected),1e-30)); require(error<=2e-18+2e-13*abs(expected),"regional numeric value differs"); compared+=1
   require(next(reader,None) is None,"regional output has extra rows")
  require(compared==r["support"]["rows"]==701376,"case row count differs"); total_rows+=compared; cases.append({"elasticity_id":spec["elasticity_id"],"yield_to_supply_mapping":spec["yield_to_supply_mapping"],"rows_compared":compared,"receipt":receipt_name,"receipt_sha256":digest(ROOT/receipt_name),"output_sha256":digest(output_path)})
 result={"schema":"quantity_market_fund_replacement_inputs_validation/v1","created_at_utc":datetime.now(timezone.utc).isoformat(),"status":"pass","scope":"independent country-response, market-welfare, and FUND-allocation reconstruction for all five alternative market inputs","validation":{"cases":len(cases),"rows_compared":total_rows,"all_keys_exact":True,"all_values_within_fixed_plus_relative_tolerance":True,"maximum_absolute_error_billion_usd2005":max_abs,"maximum_relative_error":max_rel},"cases":cases,"claim_boundary":"regional engineering validation for the narrow quantity channel; not distributional welfare incidence beyond the registered vessel/country mapping","implementation":{"path":str(Path(__file__).resolve().relative_to(ROOT)),"sha256":digest(Path(__file__).resolve())}}
 a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); print(json.dumps(result,indent=2))


if __name__=="__main__": main()
