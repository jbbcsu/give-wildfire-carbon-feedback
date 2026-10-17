#!/usr/bin/env python3
"""Acquire the open response file and optionally reproduce the FrEDI population extraction."""
from __future__ import annotations
import argparse, hashlib, subprocess, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://raw.githubusercontent.com/USEPA/FrEDI_Data/b506a3e0085bb446f56acc8c7076a1aea599fbb6/inst/extdata/fredi/gcm/WinterRec_scaledimpacts.csv"
EXPECTED = "e220c29c901e9b35b756c6af9cafec0159f89a5f71a517e51b6f97c2c3b3478b"

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fredi-sysdata", type=Path, help="Path to FrEDI v4.1.1 R/sysdata.rda")
    args = parser.parse_args()
    target = ROOT / "data/reference/WinterRec_scaledimpacts.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(URL, target)
    if sha(target) != EXPECTED: raise ValueError("downloaded WinterRec response hash mismatch")
    if args.fredi_sysdata:
        out = ROOT / "data/reference/fredi_reg_pop_v4_1_1.csv"
        expression = (
            f'load("{args.fredi_sysdata}"); '
            'x<-subset(rDataList$stateData$data$df_mainScalars, scalarName=="reg_pop" & byState==1); '
            f'write.csv(x,"{out}",row.names=FALSE,na="")'
        )
        subprocess.run(["Rscript", "-e", expression], check=True)
        if sha(out) != "278cd0a0a85b5c39083ffb77a0989d7acd80834920e3f8ad9e66f3e9c7bbb627":
            raise ValueError("population extraction hash mismatch; verify exact FrEDI v4.1.1 runtime")
    print(f"verified {target}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
