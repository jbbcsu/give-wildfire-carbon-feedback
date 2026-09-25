"""Independent structural checks for the Matiu-inspired prediction benchmark."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
from build_spei_master_band import ROOT, sha


def main():
    p=argparse.ArgumentParser(); p.add_argument("--maize",type=Path,required=True); p.add_argument("--soy",type=Path,required=True); p.add_argument("--out",type=Path,required=True); a=p.parse_args()
    checks=[]; crops={}
    for crop,path in (("maize",a.maize),("soy",a.soy)):
        r=json.loads(path.read_text()); checks.extend([r["status"]=="completed",r["crop"]==crop,
            r["training_pairs"]>0,r["terminal_pairs"]>0,not r["new_untouched_holdout"],
            not r["production_model_selected"],not r["causal_or_scc_result"],
            not r["coefficient_arrays_exported"],not r["row_predictions_exported"],
            r["protocol_sha256"]==sha(ROOT/"MATIU_STRUCTURE_PREDICTION_PROTOCOL_20260925.md"),
            r["code_sha256"]==sha(ROOT/"scripts/matiu_structure_prediction.py")])
        for label,(left,right) in r["comparisons"].items():
            for weighting in ("pooled_rmse","equal_country_rmse"):
                expected=r["metrics"][left][weighting]-r["metrics"][right][weighting]
                checks.append(np.isclose(expected,r["rmse_differences"][weighting][label],rtol=0,atol=1e-15))
            stable=sum(r["fold_differences"][str(f)][label]["pooled_rmse"]<0 for f in range(5))>=4
            checks.append(stable==r["promotion"][label]["at_least_four_fold_pooled_improvements"])
            checks.append(not r["promotion"][label]["passes_exploratory_rule"])
        crops[crop]={"input_sha256":sha(path),"training_pairs":r["training_pairs"],"terminal_pairs":r["terminal_pairs"],"promotion_passes":sum(v["passes_exploratory_rule"] for v in r["promotion"].values())}
    answer={"status":"passed" if all(checks) else "failed","checks":len(checks),"failed_checks":sum(not x for x in checks),"crops":crops,"validator_sha256":sha(Path(__file__))}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(answer,indent=2,allow_nan=False))
    if answer["status"]!="passed": raise SystemExit("Validation failed")


if __name__=="__main__": main()
