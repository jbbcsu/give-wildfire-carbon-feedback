"""Resume six fixed raw-CMIP6 annual-GMST reductions one guarded job at a time."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from continue_us_paired_regional_acquisition import fresh_job
from run_bounded_job import run

ROOT = Path(__file__).resolve().parents[1]
CASES = [(model, experiment)
         for model in ("GFDL-ESM4", "IPSL-CM6A-LR")
         for experiment in ("historical", "ssp585", "ssp126")]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max-stores", type=int, default=1)
    args = p.parse_args()
    if Path.cwd() != ROOT or not 1 <= args.max_stores <= 6:
        raise ValueError("isolated project directory and bounded case count required")
    launched = 0
    for model, experiment in CASES:
        slug = model.lower().replace("-", "_")
        name = f"pangeo_{slug}_{experiment}_annual_gmst_20260917"
        dest = Path("data/interim") / name
        if dest.exists():
            result = json.loads((dest / "result.json").read_text())
            if result["status"] != "raw_cmip6_annual_gmst_built" or (result["source"]["source_id"], result["source"]["experiment_id"]) != (model, experiment):
                raise ValueError("existing annual GMST output incomplete")
            print("verified existing", model, experiment, flush=True)
            continue
        if launched >= args.max_stores:
            break
        receipt, log, scratch = fresh_job(name)
        status = run([sys.executable, "scripts/build_pangeo_annual_gmst.py",
                      "--model", model, "--experiment", experiment,
                      "--out-dir", str(dest),
                      "--dependency-dir", "data/interim/monthly_cloud_dependencies_20260908"],
                     receipt, log, 512, 130, max_log_mib=2,
                     write_paths=[dest], max_new_disk_mib=64, scratch_dir=scratch)
        print(model, experiment, status["status"], str(receipt), flush=True)
        if status["status"] != "completed":
            raise RuntimeError(f"bounded annual GMST reduction failed; inspect {log}")
        result = json.loads((dest / "result.json").read_text())
        if result["status"] != "raw_cmip6_annual_gmst_built" or len(result["annual"]) not in (30, 86):
            raise ValueError("new annual GMST output invalid")
        launched += 1
    print("new completed stores", launched, flush=True)


if __name__ == "__main__":
    main()
