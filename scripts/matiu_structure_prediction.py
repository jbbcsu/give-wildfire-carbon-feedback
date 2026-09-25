"""Country-held-out nonlinear temperature-moisture prediction benchmark."""
from __future__ import annotations
import argparse, gc, json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from build_spei_master_band import ROOT, sha, verify, key_hash
from spei_master_support import KEYS, heat_columns, country_fold
from spei_historical_associations import MANIFEST, AUDIT
from global_continuous_geographic_cluster_audit import fit_beta

PROTOCOL = ROOT / "MATIU_STRUCTURE_PREDICTION_PROTOCOL_20260925.md"
SCALES = (1, 3, 6)


def level_features(frame, crop):
    heat = heat_columns({"maize": "mai", "soy": "soy"}[crop])
    temp = frame[heat[:3]].mean(axis=1).to_numpy(dtype=np.float64)
    hot = frame[heat[3:]].sum(axis=1).to_numpy(dtype=np.float64)
    moisture = {"quantity": frame["log1p_precip_mm"].to_numpy(dtype=np.float64)}
    moisture.update({f"spei_{k}": frame[f"spei_{k}_season"].to_numpy(dtype=np.float64) for k in SCALES})
    out = {"temp": temp, "hot": hot}
    for name, wet in moisture.items():
        out[name] = wet
        out[name + "_temp2"] = temp ** 2
        out[name + "_wet2"] = wet ** 2
        out[name + "_interaction"] = temp * wet
    return pd.DataFrame(out)


def specs():
    answer = {}
    for family in ("quantity", "spei_1", "spei_3", "spei_6"):
        answer[family + "_linear"] = ["temp", "hot", family]
        answer[family + "_nonlinear"] = ["temp", "hot", family,
                                           family + "_temp2", family + "_wet2",
                                           family + "_interaction"]
    return answer


def load_pairs(crop):
    audit = json.loads(AUDIT.read_text()); verify(MANIFEST, audit["input_sha256"])
    manifest = json.loads(MANIFEST.read_text()); pieces = []
    heat = heat_columns({"maize": "mai", "soy": "soy"}[crop])
    cols = KEYS + ["yield_t_ha", "country_label"] + heat + ["log1p_precip_mm"] + [f"spei_{k}_season" for k in SCALES]
    for rec in manifest["records"]:
        if rec["crop"] != crop or not rec["outputs"]["levels"]["rows"]: continue
        source = ROOT / rec["outputs"]["levels"]["path"]; verify(source, rec["outputs"]["levels"]["sha256"])
        ledger_path = ROOT / rec["outputs"]["ledger"]["path"]; verify(ledger_path, rec["outputs"]["ledger"]["sha256"])
        frame = pq.read_table(source, columns=cols).to_pandas().sort_values(KEYS).reset_index(drop=True)
        ledger = pq.read_table(ledger_path, columns=KEYS + ["primary_pair_train", "primary_pair_terminal", "primary_pair_purge"]).to_pandas()
        transformed = level_features(frame, crop)
        group_cols = [frame[c] for c in KEYS[:3]]
        delta = transformed.groupby(group_cols, sort=False).diff()
        dy = np.log(frame.yield_t_ha).groupby(group_cols, sort=False).diff()
        consecutive = frame.groupby(KEYS[:3], sort=False).harvest_year.diff().eq(1)
        pair = frame.loc[consecutive, KEYS + ["country_label"]].reset_index(drop=True)
        dx = delta.loc[consecutive].reset_index(drop=True); y = dy.loc[consecutive].to_numpy(dtype=np.float64)
        flags = ledger.loc[ledger.primary_pair_train | ledger.primary_pair_terminal | ledger.primary_pair_purge,
                           KEYS + ["primary_pair_train", "primary_pair_terminal", "primary_pair_purge"]].reset_index(drop=True)
        selected = pair.merge(flags, on=KEYS, how="inner", validate="one_to_one")
        loc = pd.MultiIndex.from_frame(pair[KEYS]).get_indexer(pd.MultiIndex.from_frame(selected[KEYS]))
        if (loc < 0).any(): raise ValueError("Pair/ledger mismatch")
        pieces.append(dict(keys=selected[KEYS], country=selected.country_label.to_numpy(),
                           x=dx.iloc[loc].to_numpy(dtype=np.float64), y=y[loc],
                           train=selected.primary_pair_train.to_numpy(), terminal=selected.primary_pair_terminal.to_numpy(),
                           purge=selected.primary_pair_purge.to_numpy(), names=list(dx.columns)))
        del frame, ledger, transformed, delta; gc.collect()
    names = pieces[0]["names"]
    if any(p["names"] != names for p in pieces): raise ValueError("Feature order mismatch")
    out = {k: np.concatenate([p[k] for p in pieces]) for k in ("country", "x", "y", "train", "terminal", "purge")}
    out["keys"] = pd.concat([p["keys"] for p in pieces], ignore_index=True); out["names"] = names
    if not np.isfinite(out["x"]).all() or not np.isfinite(out["y"]).all(): raise ValueError("Nonfinite pairs")
    return out


def design(data):
    year = (data["keys"].harvest_year.to_numpy(dtype=float) - 2000.) / 10.
    return np.column_stack([np.ones(len(year)), year, year ** 2, data["x"]])


def metrics(country_stats, names):
    out = {}
    for name in names:
        values = np.array([country_stats[c][name] for c in sorted(country_stats)], dtype=float)
        out[name] = {"pooled_rmse": float(np.sqrt(values[:, 0].sum() / values[:, 1].sum())),
                     "equal_country_rmse": float(np.sqrt(np.mean(values[:, 0] / values[:, 1]))),
                     "pairs": int(values[:, 1].sum()), "countries": len(values)}
    return out


def bootstrap(country_stats, comparisons, names, replicates=5000):
    countries = sorted(country_stats); groups = [[i for i,c in enumerate(countries) if country_fold(c) == f] for f in range(5)]
    if any(len(g) < 2 for g in groups): return {"status": "unsupported_scoring_country_count", "replicates": 0}
    sse = np.array([[country_stats[c][m][0] for m in names] for c in countries]); n = np.array([country_stats[c][names[0]][1] for c in countries])
    rng = np.random.Generator(np.random.PCG64(20260925)); draws = {w:{k:[] for k in comparisons} for w in ("pooled_rmse", "equal_country_rmse")}
    for _ in range(replicates):
        pick = np.concatenate([np.asarray(g)[rng.integers(0, len(g), len(g))] for g in groups])
        loss = {"pooled_rmse": np.sqrt(sse[pick].sum(0) / n[pick].sum()),
                "equal_country_rmse": np.sqrt((sse[pick] / n[pick,None]).mean(0))}
        for w, values in loss.items():
            for label,(left,right) in comparisons.items(): draws[w][label].append(float(values[names.index(left)] - values[names.index(right)]))
    return {"status":"conditional_country_bootstrap", "replicates":replicates, "seed":20260925,
            "intervals":{w:{k:list(map(float,np.quantile(v,[.025,.5,.975]))) for k,v in d.items()} for w,d in draws.items()}}


def main():
    p=argparse.ArgumentParser(); p.add_argument("--crop", choices=["maize","soy"], required=True); p.add_argument("--out-dir", type=Path, required=True); a=p.parse_args()
    if a.out_dir.exists(): raise ValueError("Fresh output required")
    data=load_pairs(a.crop); x=design(data); feature_names=["intercept","year","year_squared"]+data["names"]
    model_specs=specs(); names=list(model_specs); folds=np.array([country_fold(c) for c in data["country"]], dtype=np.int8)
    betas={}; fits=[]
    for held in range(5):
        train=data["train"] & (folds != held)
        for name, cols in model_specs.items():
            idx=[feature_names.index(c) for c in ["intercept","year","year_squared"]+cols]
            selected=x[train][:,idx]; outcome=data["y"][train]
            gram=np.einsum("ni,nj->ij",selected,selected,optimize=False)
            cross=np.einsum("ni,n->i",selected,outcome,optimize=False)
            yy=float(np.einsum("n,n->",outcome,outcome,optimize=False))
            beta, condition=fit_beta((gram,cross,yy,int(train.sum())))
            check,_,rank,_=np.linalg.lstsq(selected,outcome,rcond=None)
            error=float(np.max(np.abs(beta-check)))
            if rank!=len(idx) or not np.allclose(beta,check,rtol=1e-7,atol=1e-10): raise ValueError("Fit check failed")
            full=np.zeros(x.shape[1]); full[idx]=beta; betas[held,name]=full
            fits.append({"fold":held,"model":name,"training_pairs":int(train.sum()),"parameters":len(idx),"scaled_gram_condition":condition,"independent_beta_max_abs_difference":error})
    stats={}; fold_scores={}
    for country in sorted(set(data["country"])):
        mask=data["terminal"] & (data["country"]==country)
        if not mask.any(): continue
        held=country_fold(country); row={}
        for name in names:
            predicted=np.einsum("ni,i->n",x[mask],betas[held,name],optimize=False)
            residual=data["y"][mask]-predicted
            row[name]=[float(np.einsum("n,n->",residual,residual,optimize=False)),int(mask.sum())]
        stats[country]=row
    summary=metrics(stats,names)
    comparisons={f"{f}_nonlinear_minus_linear":(f"{f}_nonlinear",f"{f}_linear") for f in ("quantity","spei_1","spei_3","spei_6")}
    differences={w:{k:summary[l][w]-summary[r][w] for k,(l,r) in comparisons.items()} for w in ("pooled_rmse","equal_country_rmse")}
    for held in range(5):
        subset={c:v for c,v in stats.items() if country_fold(c)==held}; m=metrics(subset,names)
        fold_scores[str(held)]={k:{w:m[l][w]-m[r][w] for w in ("pooled_rmse","equal_country_rmse")} for k,(l,r) in comparisons.items()}
    uncertainty=bootstrap(stats,comparisons,names)
    promotion={}
    for label in comparisons:
        stable=sum(fold_scores[str(f)][label]["pooled_rmse"]<0 for f in range(5))>=4
        interval=uncertainty.get("intervals",{}).get("pooled_rmse",{}).get(label,[np.nan]*3)
        promotion[label]={"both_aggregate_weightings_improve":all(differences[w][label]<0 for w in differences),"at_least_four_fold_pooled_improvements":bool(stable),"pooled_interval_excludes_zero_below":bool(interval[2]<0),"passes_exploratory_rule":bool(all(differences[w][label]<0 for w in differences) and stable and interval[2]<0)}
    a.out_dir.mkdir(parents=True)
    result={"status":"completed","role":"exploratory_matiu_structure_prediction","crop":a.crop,"training_pairs":int(data["train"].sum()),"terminal_pairs":int(data["terminal"].sum()),"purged_pairs":int(data["purge"].sum()),"models":names,"metrics":summary,"comparisons":comparisons,"rmse_differences":differences,"fold_differences":fold_scores,"uncertainty":uncertainty,"promotion":promotion,"fits":fits,"training_key_sha256":key_hash(data["keys"].loc[data["train"]]),"terminal_key_sha256":key_hash(data["keys"].loc[data["terminal"]]),"manifest_sha256":sha(MANIFEST),"support_audit_sha256":sha(AUDIT),"protocol_sha256":sha(PROTOCOL),"code_sha256":sha(Path(__file__)),"new_untouched_holdout":False,"production_model_selected":False,"causal_or_scc_result":False,"coefficient_arrays_exported":False,"row_predictions_exported":False,"limitation":"Already-exposed terminal years; Matiu-inspired structure, not replication. Conditional prediction only."}
    (a.out_dir/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False))


if __name__=="__main__":
    np.seterr(invalid="raise",divide="raise",over="raise"); main()
