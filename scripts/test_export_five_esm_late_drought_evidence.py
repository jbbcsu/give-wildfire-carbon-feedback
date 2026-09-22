import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestEvidenceExportContract(unittest.TestCase):
    def test_script_parses_and_keeps_downstream_gates_closed(self):
        path = ROOT / "scripts/export_five_esm_late_drought_evidence.py"
        source = path.read_text()
        ast.parse(source)
        self.assertIn('validation["matrix_sha256"] == digest(matrix_path)', source)
        self.assertIn('"source_cases": validation["source_cases"]', source)
        self.assertIn('"yield_response": False', source)
        self.assertIn('"damage": False', source)
        self.assertIn('"scc": False', source)
        self.assertIn('"season", 3, "noirr"', source)


if __name__ == "__main__":
    unittest.main()
