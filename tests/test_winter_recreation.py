import importlib.util, unittest
from decimal import Decimal
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts/run_winter_recreation_benchmark.py"
spec = importlib.util.spec_from_file_location("benchmark", PATH); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class TestBenchmark(unittest.TestCase):
    def test_curve_adds_zero_and_linear_extension(self):
        c = mod.make_curve([(Decimal(1), Decimal(2)), (Decimal(2), Decimal(5))])
        self.assertEqual(c[Decimal(0)], 0); self.assertEqual(c[Decimal(30)], 89)
    def test_linear(self):
        self.assertEqual(mod.linear({Decimal(0): Decimal(0), Decimal(2): Decimal(4)}, Decimal(1)), 2)
    def test_snapshot(self):
        self.assertEqual(mod.snapshot_value(Decimal(10), Decimal(90), 2050), 50)
        self.assertEqual(mod.snapshot_value(Decimal(10), Decimal(90), 2200), 90)
    def test_outside_support_fails(self):
        with self.assertRaises(ValueError): mod.linear({Decimal(0): Decimal(0), Decimal(1): Decimal(1)}, Decimal(-1))

if __name__ == "__main__": unittest.main()
