#!/usr/bin/env python3
"""Reacquire the two open, pinned EPA FrEDI electricity artifacts."""
import hashlib, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES={
 'ElecTD_scaledimpacts.csv':('https://raw.githubusercontent.com/USEPA/FrEDI_Data/b506a3e0085bb446f56acc8c7076a1aea599fbb6/inst/extdata/fredi/gcm/ElecTD_scaledimpacts.csv','c21409dc5e70a878f890bba8514742ab84054a0cb3bf3ece5763f433a05da3b4'),
 'Scalar_damageAdj_elecTD_growthFactor.csv':('https://raw.githubusercontent.com/USEPA/FrEDI_Data/b506a3e0085bb446f56acc8c7076a1aea599fbb6/inst/extdata/fredi/scalars/Scalar_damageAdj_elecTD_growthFactor.csv','a27c1d6828e081db6fa221dceb2863d0caec64b67da00c8c61ac3db916748353')}
def main():
 out=ROOT/'data/reference';out.mkdir(parents=True,exist_ok=True)
 for name,(url,expected) in FILES.items():
  path=out/name;urllib.request.urlretrieve(url,path)
  if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError(f'hash mismatch: {name}')
  print(f'verified {path}')
 return 0
if __name__=='__main__':raise SystemExit(main())
