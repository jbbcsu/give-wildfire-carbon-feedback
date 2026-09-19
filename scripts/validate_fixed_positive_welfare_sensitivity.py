#!/usr/bin/env python3
"""Independent audit of fixed-positive partial-support welfare sensitivity."""
from __future__ import annotations

import argparse, hashlib, json, math
from collections import defaultdict
from pathlib import Path
import tomllib
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[1]
PHYSICAL=ROOT/'data/interim/epic_caraib_global_comparison_20260908/result.json'
CELLS=ROOT/'data/interim/epic_caraib_geography_20260908/country_cell_production.parquet'
AREA=ROOT/'data/interim/epic_caraib_global_comparison_20260908/common_area_support.parquet'
BASELINE=ROOT/'data/interim/welfare_baseline_ledger_20260914_v2/result.json'
COVERAGE=ROOT/'data/interim/fixed_positive_crop_support_20260919/result.json'
FULL=ROOT/'data/interim/four_corner_welfare_attribution_20260919/result.json'
PRICE=ROOT/'config/price_basis_registry.toml'
PROTOCOL=ROOT/'FIXED_POSITIVE_WELFARE_SENSITIVITY_PROTOCOL_20260919.md'
BUILDER=ROOT/'scripts/build_fixed_positive_welfare_sensitivity.py'
RESULT=ROOT/'data/interim/fixed_positive_welfare_sensitivity_20260919/result.json'
DEFAULT_OUTPUT=ROOT/'data/interim/fixed_positive_welfare_sensitivity_validation_20260919/result.json'
CORNERS=('y00','y10','y01','y11')

def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def close(a,b,label,checks):
 if a is None or b is None:
  if a is not b: raise AssertionError(f'{label}: {a!r}!={b!r}')
 elif not math.isclose(float(a),float(b),rel_tol=3e-12,abs_tol=1e-6):
  raise AssertionError(f'{label}: {a!r}!={b!r}')
 checks.append(label)

def benefit(v,es,ed,supply):
 h=math.log(supply);z=-(1-ed)*h/(es+ed);r=math.expm1(z)/z if z else 1.
 return v*h/(1+es)*r

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=DEFAULT_OUTPUT);a=ap.parse_args()
 physical=json.loads(PHYSICAL.read_text());baseline=json.loads(BASELINE.read_text())
 coverage=json.loads(COVERAGE.read_text());full=json.loads(FULL.read_text());result=json.loads(RESULT.read_text())
 with PRICE.open('rb') as f:scalar=float(tomllib.load(f)['central_scalar'])
 ledgers=sorted({r['ledger_path']:{'path':r['ledger_path'],'sha256':r['ledger_sha256']} for r in physical['summaries']}.values(),key=lambda x:x['path'])
 bindings={'physical_result_sha256':digest(PHYSICAL),'country_cell_production_sha256':digest(CELLS),
 'common_area_support_sha256':digest(AREA),'baseline_value_ledger_sha256':digest(BASELINE),
 'fixed_support_audit_sha256':digest(COVERAGE),'full_support_attribution_sha256':digest(FULL),
 'price_registry_sha256':digest(PRICE),'market_code_sha256':digest(ROOT/'src/constant_elasticity_market.py'),
 'protocol_sha256':digest(PROTOCOL),'builder_sha256':digest(BUILDER),'physical_ledgers':ledgers}
 checks=[]
 if result['source_bindings']!=bindings:raise AssertionError('source bindings differ')
 checks.append('source_bindings')
 if result['case_count']!=96 or len(result['cases'])!=96:raise AssertionError('case count')
 checks.append('case_count')
 for flag in ('crop_model_repaired','empirical_damage_authorized','agriculture_replacement_authorized','give_export_authorized','scc_authorized'):
  if result[flag] is not False:raise AssertionError(flag)
  checks.append(flag)
 if result['partial_support_only'] is not True:raise AssertionError('partial flag')
 checks.append('partial_support_only')

 area=pq.read_table(AREA).to_pandas();area=area.loc[area.common_response,['latitude','longitude','regime']]
 keys=list(area.itertuples(index=False,name=None));retain={k:True for k in keys}
 for s in physical['summaries']:
  f=pq.read_table(ROOT/s['ledger_path'],columns=['latitude','longitude',*CORNERS]).to_pydict()
  lookup={(lat,lon):tuple(f[c][i] for c in CORNERS) for i,(lat,lon) in enumerate(zip(f['latitude'],f['longitude']))}
  for k in keys:
   if k[2]!=s['regime']:continue
   vals=lookup[(k[0],k[1])];retain[k]&=all(math.isfinite(x) and x>0 for x in vals)
 cells=pq.read_table(CELLS).to_pandas();cells=cells.loc[cells.common_response&(cells.production_mt>0)]
 original=cells.groupby(['country','regime']).production_mt.sum().to_dict()
 cells['retain']=[retain[(r.latitude,r.longitude,r.regime)] for r in cells.itertuples()]
 cells=cells.loc[cells.retain]
 values={(r['country'],r['regime']):r for r in baseline['country_regime_rows']}
 grouped=defaultdict(list)
 for s in physical['summaries']:grouped[(s['crop_model'],s['climate_model'],s['scenario'],s['calendar'])].append(s)
 states={}
 for case4,sums in grouped.items():
  rows=[];missing=0.
  for s in sums:
   f=pq.read_table(ROOT/s['ledger_path'],columns=['latitude','longitude',*CORNERS]).to_pandas()
   j=cells.loc[cells.regime==s['regime']].merge(f,on=['latitude','longitude'],validate='many_to_one')
   for country,g in j.groupby('country',sort=True):
    key=(country,s['regime']);prod=math.fsum(g.production_mt.tolist())
    raw=values[key]['common_response_value_proxy_thousand_constant_2014_2016_USD']
    if raw is None:missing+=prod;continue
    rec={'country':country,'regime':s['regime'],'value':float(raw)*scalar*prod/original[key]}
    for c in CORNERS:rec[c]=math.fsum((g.production_mt*g[c]/g.y00).tolist())/prod
    rows.append(rec)
  states[case4]=(rows,missing)
 fullmap={(r['crop_model'],r['climate_model'],r['scenario'],r['calendar'],r['elasticity_id'],r['yield_to_supply_mapping']):r for r in full['cases']}
 outmap={(r['crop_model'],r['climate_model'],r['scenario'],r['calendar'],r['elasticity_id'],r['yield_to_supply_mapping']):r for r in result['cases']}
 for case4,(rows,missing) in states.items():
  total=math.fsum(r['value'] for r in rows)
  for eid,es,ed in (('hultgren_pair_008_002',.08,.02),('hultgren_pair_010_004',.1,.04),('hultgren_pair_050_006',.5,.06)):
   for mapping in ('horizontal_output','fixed_input_cost'):
    key=case4+(eid,mapping);out=outmap[key];power=1 if mapping=='horizontal_output' else 1+es
    supply={c:math.fsum(r['value']/total*r[c]**power for r in rows) for c in CORNERS}
    b={c:benefit(total,es,ed,supply[c]) for c in CORNERS}
    p=-.5*((b['y01']-b['y00'])+(b['y11']-b['y10']))
    t=-.5*((b['y10']-b['y00'])+(b['y11']-b['y01']));j=-(b['y11']-b['y00']);cl=p+t-j
    prior=fullmap[key]
    comp={'valued_retained_support_thousand_USD2005':total,
    'missing_value_proxy_retained_production_mt_not_dollars':missing,
    'precipitation_shapley_damage_thousand_USD2005':p,'temperature_shapley_damage_thousand_USD2005':t,
    'joint_damage_thousand_USD2005':j,'shapley_closure_error_thousand_USD2005':cl,
    'full_support_precipitation_damage_thousand_USD2005':prior['precipitation_shapley_damage_thousand_USD2005'],
    'full_support_temperature_damage_thousand_USD2005':prior['temperature_shapley_damage_thousand_USD2005'],
    'full_support_joint_damage_thousand_USD2005':prior['joint_damage_thousand_USD2005'],
    'restricted_minus_full_precipitation_damage_thousand_USD2005':p-prior['precipitation_shapley_damage_thousand_USD2005'] if prior['precipitation_shapley_damage_thousand_USD2005'] is not None else None,
    'restricted_minus_full_temperature_damage_thousand_USD2005':t-prior['temperature_shapley_damage_thousand_USD2005'] if prior['temperature_shapley_damage_thousand_USD2005'] is not None else None,
    'restricted_minus_full_joint_damage_thousand_USD2005':j-prior['joint_damage_thousand_USD2005'] if prior['joint_damage_thousand_USD2005'] is not None else None}
    for n,e in comp.items():close(out[n],e,f'{key}:{n}',checks)
    for c in CORNERS:close(out['corner_supply_multipliers'][c],supply[c],f'{key}:{c}',checks)
    for n,e in {'country_regime_count':len(rows),'mechanically_admissible':True,'partial_support_only':True,'structural_damage_interpretation_authorized':False}.items():
     if out[n]!=e:raise AssertionError(f'{key}:{n}')
     checks.append(f'{key}:{n}')
 cov=next(r for r in coverage['summaries'] if r['mask']=='both_models_positive' and r['regime']=='all')
 if result['coverage']!=cov:raise AssertionError('coverage binding')
 checks.append('coverage_binding')
 audit={'status':'passed','check_count':len(checks),'case_count':len(outmap),
 'validated_result_sha256':digest(RESULT),'validator_sha256':digest(Path(__file__)),'source_bindings':bindings,
 'partial_support_only':True,'give_export_authorized':False,'scc_authorized':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(audit,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':main()
