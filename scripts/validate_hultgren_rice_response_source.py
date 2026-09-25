"""Validate the pinned published Hultgren rice estimate export without redistributing it."""
from __future__ import annotations
import argparse, csv, hashlib, json, subprocess, tomllib
from pathlib import Path
import numpy as np


def digest(path, algorithm="sha256"):
    h=hashlib.new(algorithm)
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
    return h.hexdigest()


def metadata(path):
    out={}
    for line in path.read_text().splitlines():
        key,value=line.split("=",1); out[key]=value.strip()
    return out


def main():
    p=argparse.ArgumentParser(); p.add_argument("--config",type=Path,required=True); p.add_argument("--coefficients",type=Path,required=True); p.add_argument("--covariance",type=Path,required=True); p.add_argument("--metadata",type=Path,required=True); p.add_argument("--out",type=Path,required=True); a=p.parse_args()
    root=Path(__file__).resolve().parents[1]; cfg=tomllib.loads(a.config.read_text()); estimate=root/cfg["local_raw_directory"]/cfg["estimate_local_filename"]
    checks={}
    checks["estimate_bytes"]=estimate.stat().st_size==cfg["estimate_bytes"]
    checks["estimate_sha256"]=digest(estimate)==cfg["estimate_sha256"]
    checks["estimate_git_blob_sha1"]=subprocess.check_output(["git","hash-object",str(estimate)],text=True).strip()==cfg["estimate_git_blob_sha1"]
    with a.coefficients.open(newline="") as f: coeff=list(csv.DictReader(f))
    with a.covariance.open(newline="") as f: cov=list(csv.DictReader(f))
    meta=metadata(a.metadata); n=cfg["coefficient_count"]
    terms=[r["term"] for r in coeff]; beta=np.array([float(r["estimate"]) for r in coeff])
    matrix=np.full((n,n),np.nan)
    for r in cov: matrix[int(r["row_index"])-1,int(r["column_index"])-1]=float(r["covariance"])
    checks.update(coefficient_count=len(coeff)==n==int(meta["coefficient_count"]),covariance_count=len(cov)==n*n,
                  coefficient_indices=[int(r["index"]) for r in coeff]==list(range(1,n+1)),finite_coefficients=bool(np.isfinite(beta).all()),
                  finite_covariance=bool(np.isfinite(matrix).all()),covariance_symmetric=bool(np.allclose(matrix,matrix.T,rtol=0,atol=1e-15)),
                  covariance_nonnegative_diagonal=bool((np.diag(matrix)>=0).all()),dependent_variable=meta["depvar"]=="ln_yield",
                  estimator=meta["cmd"]=="reghdfe",cluster_variables=meta["clustvar"]=="adm0_year adm1_fact",
                  fixed_effects=meta["absvars"]=="uid i.adm1_fact##c.(time time_sqr) adm0_year",
                  observations=int(meta["N"])==cfg["estimation_observations"],full_observations=int(meta["N_full"])==cfg["full_observations"],
                  country_year_clusters=int(meta["N_clust1"])==cfg["country_year_clusters"],adm1_clusters=int(meta["N_clust2"])==cfg["adm1_clusters"])
    base=["gdd","kdd"]+[f"prcp_poly_{power}_bin{phase}" for power in (1,2) for phase in (1,2,3)]+["tmin"]
    modifiers=["ln_gdppc","irrigated_share","lr_tmax_crop"]
    expected=[]
    for variable in base:
        expected.append(variable); expected += [f"c.{variable}#c.{m}" for m in modifiers]
        expected.append(f"c.{variable}#c.pbarcut_{'prcp' if variable.startswith('prcp') else variable}")
    expected.append("_cons")
    checks["ordered_terms"]=terms==expected
    checks["future_gates_closed"]=not any(cfg[x] for x in ("future_weather_ready","damage_ready","scc_ready"))
    answer={"status":"passed" if all(checks.values()) else "failed","checks":checks,"passed_checks":sum(checks.values()),"total_checks":len(checks),
            "source":{"repository":cfg["source_repository"],"commit":cfg["source_commit"],"repository_path":cfg["estimate_repository_path"],"estimate_sha256":cfg["estimate_sha256"],"estimate_git_blob_sha1":cfg["estimate_git_blob_sha1"]},
            "estimate":{"coefficient_count":n,"observations":int(meta["N"]),"full_observations":int(meta["N_full"]),"country_year_clusters":int(meta["N_clust1"]),"adm1_clusters":int(meta["N_clust2"]),"r2":float(meta["r2"]),"within_r2":float(meta["r2_within"]),"precipitation_phases":3,"precipitation_polynomial_order":2,"includes_tmin":True,"weather_moderators":["log GDP per capita","irrigated share","long-run crop temperature","capped long-run precipitation"]},
            "export_hashes":{"coefficients_sha256":digest(a.coefficients),"covariance_sha256":digest(a.covariance),"metadata_sha256":digest(a.metadata)},
            "raw_source_redistributed":False,"published_response_available":True,"future_weather_ready":False,"damage_ready":False,"scc_ready":False,"validator_sha256":digest(Path(__file__))}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(answer,indent=2,allow_nan=False))
    if answer["status"]!="passed": raise SystemExit("Rice response validation failed")


if __name__=="__main__": main()
