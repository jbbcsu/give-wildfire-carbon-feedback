#!/usr/bin/env python3
"""Acquire hash-pinned public EPA crime inputs without silent replacement."""
import hashlib, json, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    c=json.loads((ROOT/"config/conflict_crime_benchmark_v1.json").read_text()); base=f"https://raw.githubusercontent.com/USEPA/FrEDI_Data/{c['sources']['commit']}"
    paths={
      "response":"inst/extdata/fredi/gcm/CILCrime_scaledimpacts.csv",
      "property_cost":"inst/extdata/fredi/scalars/Scalar_econScalar_property_crime_costs_usd.csv",
      "violent_cost":"inst/extdata/fredi/scalars/Scalar_econScalar_violent_crime_costs_usd.csv"}
    for key,upstream in paths.items():
        spec=c["sources"][key]; target=ROOT/spec["path"]
        if target.exists():
            if sha(target)!=spec["sha256"]: raise ValueError(f"wrong hash: {target}")
            print(f"verified {target}"); continue
        with urllib.request.urlopen(f"{base}/{upstream}",timeout=60) as response: payload=response.read()
        if hashlib.sha256(payload).hexdigest()!=spec["sha256"]: raise ValueError("download hash mismatch")
        target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(payload); print(f"downloaded {target}")
    return 0

if __name__=="__main__": raise SystemExit(main())

