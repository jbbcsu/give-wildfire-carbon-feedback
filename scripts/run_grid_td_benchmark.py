#!/usr/bin/env python3
"""Run source-pinned FrEDI ElecTD matched-pulse benchmark."""
from __future__ import annotations
import csv, hashlib, json, resource, sys
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path
getcontext().prec = 40
ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def read(path):
    with path.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]),lineterminator='\n');w.writeheader();w.writerows(data)
def curve(points):
    p=sorted(set([(Decimal(0),Decimal(0))]+points)); x1,y1=p[-2];x2,y2=p[-1]
    if x2!=30:p.append((Decimal(30),y2+(Decimal(30)-x2)*(y2-y1)/(x2-x1)))
    return dict(p)
def linear(c,x):
    xs=sorted(c)
    if not xs[0]<=x<=xs[-1]:raise ValueError('outside response support')
    if x in c:return c[x]
    hi=next(v for v in xs if v>x);lo=xs[xs.index(hi)-1]
    return c[lo]+(x-lo)*(c[hi]-c[lo])/(hi-lo)
def scalar_at(points,year):return linear(points,Decimal(year))

def main():
    cfg=json.loads((ROOT/'config/grid_td_benchmark_v1.json').read_text());assert cfg['scope']['additivity_to_give_authorized'] is False
    for k in ('response','growth','give_pair','price'):
        s=cfg['sources'][k]
        if digest(ROOT/s['path'])!=s['sha256']:raise ValueError(f'hash mismatch {s["path"]}')
    raw=defaultdict(list);response=read(ROOT/cfg['sources']['response']['path'])
    if len(response)!=4557:raise ValueError('unexpected ElecTD rows')
    for r in response:
        if r['sector']!='ElecTD' or r['impactType']!='NA':raise ValueError('unauthorized response')
        if r['value'] not in ('','NA'):raw[(r['postal'],r['model'],r['variant'])].append((Decimal(r['modelUnitValue']),Decimal(r['value'])))
    curves={k:curve(v) for k,v in raw.items()}
    if len(curves)!=49*6*3:raise ValueError('incomplete curves')
    growth_raw=defaultdict(list);growth_rows=read(ROOT/cfg['sources']['growth']['path'])
    if len(growth_rows)!=4312:raise ValueError('unexpected growth rows')
    for r in growth_rows:growth_raw[r['postal']].append((Decimal(r['year']),Decimal(r['value'])))
    growth={p:dict(v) for p,v in growth_raw.items()}
    pair=[r for r in read(ROOT/cfg['sources']['give_pair']['path']) if int(r['year'])>=2025]
    pulse=Decimal(str(cfg['give_target']['pulse_size_metric_tonnes_co2']));prices=cfg['sources']['price']['values'];deflator=Decimal(str(prices['2020']))/Decimal(str(prices['2015']))
    annual=[];totals=defaultdict(Decimal)
    for variant in cfg['model']['variants']:
      for gcm in cfg['model']['gcms']:
       for item in pair:
        year=int(item['year']);base_t=Decimal(item['base_conus_anomaly_c']);pulse_t=Decimal(item['pulse_conus_anomaly_c']);disc=Decimal(item['ramsey_discount_factor']);base=Decimal(0);modified=Decimal(0)
        for postal in growth:
            scale=scalar_at(growth[postal],year);c=curves[(postal,gcm,variant)]
            base+=linear(c,base_t)*scale;modified+=linear(c,pulse_t)*scale
        marginal=modified-base;discounted=marginal*deflator*disc
        for horizon in (2092,2300):
            if year<=horizon:totals[(horizon,gcm,variant)]+=discounted
        annual.append({'year':year,'gcm':gcm,'adaptation_variant':variant,'base_conus_anomaly_c':format(base_t,'f'),'pulse_conus_anomaly_c':format(pulse_t,'f'),'base_direct_cost_2015usd':format(base,'.12f'),'pulse_direct_cost_2015usd':format(modified,'.12f'),'marginal_direct_cost_2015usd':format(marginal,'.12f'),'discounted_marginal_direct_cost_2020usd':format(discounted,'.12f')})
    annual_path=ROOT/cfg['outputs']['annual'];write(annual_path,annual)
    by=[]
    for horizon in (2092,2300):
      for variant in cfg['model']['variants']:
       for gcm in cfg['model']['gcms']:
        by.append({'scope':'CONUS_48_plus_DC','support_years':f'2025-{horizon}','horizon':horizon,'adaptation_variant':variant,'gcm':gcm,'td_direct_cost_benchmark_2020usd_per_tco2':format(totals[(horizon,gcm,variant)]/pulse,'.12f'),'outage_welfare_included':'false','additive_to_give':'false'})
    by_path=ROOT/cfg['outputs']['by_gcm'];write(by_path,by)
    summary=[]
    for horizon in (2092,2300):
      for variant in cfg['model']['variants']:
        vals=sorted(Decimal(r['td_direct_cost_benchmark_2020usd_per_tco2']) for r in by if r['horizon']==horizon and r['adaptation_variant']==variant)
        summary.append({'scope':'CONUS_48_plus_DC','support_years':f'2025-{horizon}','horizon':horizon,'adaptation_variant':variant,'gcm_count':len(vals),'mean_2020usd_per_tco2':format(sum(vals)/Decimal(len(vals)),'.12f'),'median_2020usd_per_tco2':format((vals[2]+vals[3])/2,'.12f'),'min_2020usd_per_tco2':format(vals[0],'.12f'),'max_2020usd_per_tco2':format(vals[-1],'.12f'),'endpoint':'direct T&D repair/replacement costs; outages excluded','additive_to_give':'false'})
    summary_path=ROOT/cfg['outputs']['summary'];write(summary_path,summary)
    receipt={'schema':'grid_td_partial_scc_receipt/v1','created_at_utc':datetime.now(timezone.utc).isoformat(),'status':'PUBLISHED_CONUS_DIRECT_COST_BENCHMARK_NOT_ADDITIVE','inputs':{k:{'path':cfg['sources'][k]['path'],'sha256':cfg['sources'][k]['sha256']} for k in ('response','growth','give_pair','price')},'outputs':{n:{'path':str(p.relative_to(ROOT)),'sha256':digest(p),'rows':len(d)} for n,p,d in (('annual',annual_path,annual),('by_gcm',by_path,by),('summary',summary_path,summary))},'claim_scope':cfg['scope'],'peak_rss_mib':round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024*1024 if sys.platform=='darwin' else 1024),3)}
    receipt_path=ROOT/cfg['outputs']['receipt'];receipt_path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps({'summary':summary,'peak_rss_mib':receipt['peak_rss_mib']},indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
