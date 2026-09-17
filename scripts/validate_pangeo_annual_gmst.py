"""Independent saved-product audit of six raw-CMIP6 monthly-to-annual GMST runs."""
import argparse
from collections import defaultdict
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    if args.out_dir.exists():
        raise ValueError("fresh independent audit output required")
    rows, checks = [], 0
    for model in ("GFDL-ESM4", "IPSL-CM6A-LR"):
        area_dir = ROOT / f"data/interim/cmip6_{model.lower().replace('-', '_')}_native_area_20260917"
        ar = json.loads((area_dir / "result.json").read_text())
        if ar["status"] != "native_cell_area_verified" or ar["model"] != model:
            raise ValueError("native area gate not passed")
        for experiment in ("historical", "ssp585", "ssp126"):
            directory = ROOT / f"data/interim/pangeo_{model.lower().replace('-', '_')}_{experiment}_annual_gmst_20260917"
            path = directory / "result.json"
            result = json.loads(path.read_text())
            source = result["source"]
            if (result["status"] != "raw_cmip6_annual_gmst_built"
                    or (source["source_id"], source["experiment_id"], source["member_id"], source["variable_id"])
                    != (model, experiment, "r1i1p1f1", "tas")
                    or result["area_receipt_sha256"] != sha(area_dir / "result.json")
                    or result["area_output_sha256"] != ar["output_sha256"]
                    or any(not c["server_md5_verified"] for c in result["source_chunks"])):
                raise ValueError("source, area, or server-checksum binding differs")
            start, end = (1981, 2010) if experiment == "historical" else (2015, 2100)
            if result["years"] != [start, end]:
                raise ValueError("year contract differs")
            by_year = defaultdict(list)
            for r in result["monthly"]:
                by_year[r["year"]].append(r)
            if sorted(by_year) != list(range(start, end + 1)) or len(result["annual"]) != end-start+1:
                raise ValueError("saved monthly/annual year support differs")
            maximum = 0.0
            for saved in result["annual"]:
                year = saved["year"]
                records = sorted(by_year[year], key=lambda r: r["month"])
                if [r["month"] for r in records] != list(range(1, 13)):
                    raise ValueError("monthly support differs")
                with localcontext() as ctx:
                    ctx.prec = 50
                    denominator = sum(Decimal(str(r["seconds"])) for r in records)
                    numerator = sum(Decimal(str(r["seconds"])) * Decimal(str(r["gmst_month_k"]))
                                    for r in records)
                    reference = float(numerator / denominator)
                if saved["seconds"] != float(denominator) or not 150 < reference < 350:
                    raise ValueError("annual duration or physical support differs")
                error = abs(saved["gmst_value_k"]-reference)
                if error > 1e-11:
                    raise ValueError(f"annual GMST differs from independent Decimal sum: {model} {experiment} {year}")
                maximum = max(maximum, error)
                checks += 1
            rows.append(dict(model=model, experiment=experiment, years=[start, end],
                             annual_checks=end-start+1, maximum_absolute_reduction_error_k=maximum,
                             source_result_sha256=sha(path), source_chunks=len(result["source_chunks"]),
                             area_result_sha256=sha(area_dir / "result.json")))
    args.out_dir.mkdir(parents=True)
    output = dict(status="six_annual_gmst_saved_products_independently_audited",
                  annual_checks=checks, records=rows,
                  limitation="Checks saved monthly-to-annual reduction and identities; does not re-decode source climate chunks, fit rainfall, or validate SCC.")
    (args.out_dir / "result.json").write_text(json.dumps(output, indent=2))
    print(output["status"], checks, flush=True)


if __name__ == "__main__":
    main()
