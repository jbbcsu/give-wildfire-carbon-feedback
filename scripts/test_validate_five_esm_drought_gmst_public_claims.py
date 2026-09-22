import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestDroughtGmstPublicClaimsContract(unittest.TestCase):
    def test_validator_parses_and_keeps_gates_closed(self):
        source = (ROOT / "scripts/validate_five_esm_drought_gmst_public_claims.py").read_text()
        ast.parse(source)
        self.assertIn('validation["result_sha256"] == digest(paths["result"])', source)
        self.assertIn('"transient_climate_response": False', source)
        self.assertIn('"yield_response": False', source)
        self.assertIn('"damage": False', source)
        self.assertIn('"scc": False', source)


if __name__ == "__main__":
    unittest.main()
