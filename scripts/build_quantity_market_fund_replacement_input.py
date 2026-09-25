#!/usr/bin/env python3
"""Build one market specification's FUND-region input for paired replacement."""

from __future__ import annotations
import argparse, csv, hashlib, json, tomllib
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

from build_epa_fair_hultgren_quantity_damage_paths import ADAPTATION, VALUE, YEAR_CHUNK, adaptation_factors, model_frame, response_coefficients
from build_epa_fair_hultgren_quantity_market_sensitivities import MAPPINGS, damage_from_ratio

PULSE = 0.000025


def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(8*1024*1024),b""): h.update(block)
    return h.hexdigest()


def require(value: bool, message: str) -> None:
    if not value: raise ValueError(message)


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ["market_receipt","fund_receipt","panel","slopes","fair","fund_mapping","fund_order","registry","output","receipt"]: p.add_argument(f"--{name.replace('_','-')}",type=Path,required=True)
    p.add_argument("--elasticity-id",required=True); p.add_argument("--mapping",choices=MAPPINGS,required=True)
    a=p.parse_args(); require(not a.output.exists() and not a.receipt.exists(),"fresh outputs required")
    market=json.loads(a.market_receipt.read_text()); fund=json.loads(a.fund_receipt.read_text()); registry=tomllib.loads(a.registry.read_text())
    require(market["schema"]=="epa_fair_hultgren_quantity_market_sensitivities/v1" and fund["schema"]=="epa_fair_hultgren_quantity_fund_paths/v1","receipt differs")
    for path,key in [(a.panel,"panel"),(a.slopes,"slopes"),(a.fair,"fair")]: require(digest(path)==market["sources"][key]["sha256"],f"{key} hash differs")
    require(digest(a.fund_mapping)==fund["sources"]["fund_mapping"]["sha256"] and digest(a.fund_order)==fund["sources"]["fund_order"]["sha256"],"FUND registry differs")
    pairs={str(r["id"]):(float(r["supply"]),-float(r["demand_signed"])) for r in registry["elasticity_pairs"]}; require(a.elasticity_id in pairs,"elasticity absent"); supply,demand=pairs[a.elasticity_id]; require(supply>0 and demand>0,"elasticity signs differ")
    with a.fund_mapping.open(newline="",encoding="utf-8-sig") as f: country_region={r["ISO3"]:r["fundregion"] for r in csv.DictReader(f)}
    with a.fund_order.open(newline="",encoding="utf-8") as f: regions=[r["fund_region"] for r in csv.DictReader(f)]
    require(len(regions)==16,"FUND region count differs"); region_index={r:i for i,r in enumerate(regions)}; scalar=float(market["currency"]["central_scalar"])
    central_receipt=json.loads(Path(market["sources"]["central_paths"]["receipt"]).read_text()); tail=central_receipt["tail_rules"]["published_analogue_p01_p99"]; lower=float(tail["lower_log_yield_per_gtc"]); upper=float(tail["upper_log_yield_per_gtc"])
    panel=pd.read_parquet(a.panel); slopes=pd.read_csv(a.slopes); fair=pd.read_csv(a.fair); years=np.arange(2020,2301,dtype=np.int32); temperature=fair.loc[fair.pulse_size_gtc.eq(PULSE)&fair.year.isin(years)].sort_values("year").difference_k.to_numpy(); require(len(temperature)==281,"FAIR support differs")
    market_path=Path(market["output"]["path"]); require(digest(market_path)==market["output"]["sha256"],"market source hash differs")
    expected=pd.read_parquet(market_path,filters=[("pulse_size_gtc","==",PULSE),("elasticity_id","==",a.elasticity_id),("yield_to_supply_mapping","==",a.mapping)],columns=["climate_model","year","adaptation","tail_rule","damage_change_billion_usd2005"])
    lookup={(r.climate_model,int(r.year),r.adaptation,r.tail_rule):float(r.damage_change_billion_usd2005) for r in expected.itertuples(index=False)}; require(len(lookup)==26*281*3*2,"market support differs")
    a.output.parent.mkdir(parents=True,exist_ok=True); rows=0; max_error=0.0; models=sorted(slopes.source.unique()); exponent=1.0 if a.mapping=="horizontal_output" else 1.0+supply
    with a.output.open("w",newline="",encoding="utf-8") as out:
        writer=csv.DictWriter(out,fieldnames=["climate_model","year","adaptation","tail_rule","fund_region","marginal_damage_difference_billion_usd2005"]); writer.writeheader()
        for model in models:
            frame=model_frame(panel,slopes,model); first,second=response_coefficients(frame); values=frame[VALUE].to_numpy(float); iso=frame.iso3.to_numpy(); starts=np.r_[0,np.flatnonzero(iso[1:]!=iso[:-1])+1]; country_value=np.add.reduceat(values,starts); countries=iso[starts]; missing=sorted(set(countries)-set(country_region)); require(not missing,f"unmapped countries: {missing}"); country_regions=np.asarray([region_index[country_region[c]] for c in countries],dtype=np.int16)
            for start in range(0,len(years),YEAR_CHUNK):
                stop=min(start+YEAR_CHUNK,len(years)); chunk_years=years[start:stop]; t=temperature[start:stop]; raw=first[:,None]*t[None,:]+second[:,None]*np.square(t[None,:]); tails={"uncapped":raw,"published_analogue_p01_p99":np.clip(raw/PULSE,lower,upper)*PULSE}
                for adaptation in ADAPTATION:
                    factor=adaptation_factors(chunk_years,adaptation)
                    for tail_rule,response in tails.items():
                        adapted=np.where(response<0,response*factor[None,:],response); country_output=np.add.reduceat(np.exp(exponent*adapted)*values[:,None],starts,axis=0); ratios=country_output/country_value[:,None]; country_damage=damage_from_ratio(country_value,ratios,supply,demand)*scalar/1e9; regional=np.zeros((16,len(chunk_years))); np.add.at(regional,country_regions,country_damage)
                        for j,year in enumerate(chunk_years):
                            target=lookup[(model,int(year),adaptation,tail_rule)]; max_error=max(max_error,abs(float(regional[:,j].sum())-target))
                            for i,region in enumerate(regions): writer.writerow({"climate_model":model,"year":int(year),"adaptation":adaptation,"tail_rule":tail_rule,"fund_region":region,"marginal_damage_difference_billion_usd2005":repr(float(regional[i,j]))}); rows+=1
    require(rows==26*281*3*2*16,"row support differs"); require(max_error<=2e-12,f"global reconciliation differs: {max_error}"); require(a.output.stat().st_size<64*2**20,"output exceeds 64 MiB")
    result={"schema":"quantity_market_fund_replacement_input/v1","created_at_utc":datetime.now(timezone.utc).isoformat(),"status":"country_reconstructed_market_specification_allocated_to_fund_regions","specification":{"pulse_size_gtc":PULSE,"elasticity_id":a.elasticity_id,"yield_to_supply_mapping":a.mapping,"supply_elasticity":supply,"demand_elasticity_magnitude":demand},"support":{"climate_models":models,"adaptations":ADAPTATION,"tail_rules":["uncapped","published_analogue_p01_p99"],"years":[2020,2300],"fund_regions":regions,"paths":156,"rows":rows},"validation":{"regional_sums_reconcile_to_every_registered_global_market_path":True,"maximum_absolute_global_reconciliation_error_billion_usd2005":max_error},"sources":{"market":{"path":str(market_path),"sha256":digest(market_path),"receipt":str(a.market_receipt),"receipt_sha256":digest(a.market_receipt)},"panel":{"path":str(a.panel),"sha256":digest(a.panel)},"slopes":{"path":str(a.slopes),"sha256":digest(a.slopes)},"fair":{"path":str(a.fair),"sha256":digest(a.fair)},"fund_mapping":{"path":str(a.fund_mapping),"sha256":digest(a.fund_mapping)},"fund_order":{"path":str(a.fund_order),"sha256":digest(a.fund_order)},"registry":{"path":str(a.registry),"sha256":digest(a.registry)}},"output":{"path":str(a.output),"bytes":a.output.stat().st_size,"sha256":digest(a.output)},"claim_gate":"engineering_input_only_until_paired_give_validation","implementation":{"path":str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])),"sha256":digest(Path(__file__).resolve())}}
    a.receipt.parent.mkdir(parents=True,exist_ok=True); a.receipt.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); print(json.dumps({"status":result["status"],"specification":result["specification"],"support":result["support"],"validation":result["validation"],"output":result["output"]},indent=2))


if __name__=="__main__": main()
