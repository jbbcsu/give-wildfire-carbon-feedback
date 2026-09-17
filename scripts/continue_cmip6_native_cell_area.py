"""Acquire two exact public CMIP6 static area fields serially under guard."""
import hashlib
import json
from pathlib import Path
import sys

from continue_us_paired_regional_acquisition import fresh_job
from run_bounded_job import run

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if Path.cwd() != ROOT:
        raise ValueError("run from isolated precipitation project")
    for model in ("GFDL-ESM4", "IPSL-CM6A-LR"):
        slug = model.lower().replace("-", "_")
        dest = Path("data/interim") / f"cmip6_{slug}_native_area_20260917"
        if dest.exists():
            result = json.loads((dest / "result.json").read_text())
            if result["model"] != model or result["output_sha256"] != sha(dest / "native_cell_area.npz"):
                raise ValueError("existing static area is incomplete or changed")
            print("verified existing", model, flush=True)
            continue
        stem = f"cmip6_{slug}_native_area_20260917"
        receipt, log, scratch = fresh_job(stem)
        status = run([sys.executable, "scripts/acquire_cmip6_native_cell_area.py",
                      "--model", model, "--out-dir", str(dest),
                      "--dependency-dir", "data/interim/monthly_cloud_dependencies_20260908"],
                     receipt, log, 512, 130, max_log_mib=2,
                     write_paths=[dest], max_new_disk_mib=64, scratch_dir=scratch)
        print(model, status["status"], str(receipt), flush=True)
        if status["status"] != "completed":
            raise RuntimeError(f"bounded static-area acquisition failed; inspect {log}")
        result = json.loads((dest / "result.json").read_text())
        if result["model"] != model or result["output_sha256"] != sha(dest / "native_cell_area.npz"):
            raise ValueError("new static area did not pass output binding")


if __name__ == "__main__":
    main()
