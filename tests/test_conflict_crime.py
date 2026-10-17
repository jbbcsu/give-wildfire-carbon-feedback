import csv, json, subprocess, sys, unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_crime_benchmark import linear


class ConflictCrimeTests(unittest.TestCase):
    def test_interpolation(self):
        c={Decimal(0):Decimal(0),Decimal(1):Decimal(10),Decimal(2):Decimal(30)}
        self.assertEqual(linear(c,Decimal(".5")),Decimal(5)); self.assertEqual(linear(c,Decimal("2.5")),Decimal(40))

    def test_sources(self):
        with (ROOT/"data/reference/CILCrime_scaledimpacts.csv").open() as f: r=list(csv.DictReader(f))
        self.assertEqual(len(r),3038); self.assertEqual({x["impactType"] for x in r},{"Property","Violent"}); self.assertEqual(len({x["postal"] for x in r}),49)

    def test_scope(self):
        c=json.loads((ROOT/"config/conflict_crime_benchmark_v1.json").read_text())
        self.assertFalse(c["scope"]["additivity_to_give_authorized"]); self.assertEqual(c["scope"]["organized_armed_conflict"],"BLOCKED_NO_SCC")

    def test_validator(self):
        subprocess.run([sys.executable,str(ROOT/"scripts/validate_outputs.py")],check=True,capture_output=True)


if __name__ == "__main__": unittest.main()

