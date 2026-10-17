import importlib.util,unittest
from decimal import Decimal
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'scripts/run_grid_td_benchmark.py';s=importlib.util.spec_from_file_location('m',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class TestGrid(unittest.TestCase):
 def test_curve(self):self.assertEqual(m.curve([(Decimal(1),Decimal(2)),(Decimal(2),Decimal(5))])[Decimal(30)],89)
 def test_linear(self):self.assertEqual(m.linear({Decimal(0):Decimal(0),Decimal(2):Decimal(4)},Decimal(1)),2)
 def test_scalar_interpolation(self):self.assertEqual(m.scalar_at({Decimal(2090):Decimal(2),Decimal(2100):Decimal(4)},2095),3)
 def test_support_gate(self):
  with self.assertRaises(ValueError):m.linear({Decimal(0):Decimal(0),Decimal(1):Decimal(1)},Decimal(-1))
if __name__=='__main__':unittest.main()
