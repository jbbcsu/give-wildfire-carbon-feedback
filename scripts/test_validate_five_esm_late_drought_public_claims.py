import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestPublicClaimsValidationContract(unittest.TestCase):
    def test_script_parses_and_binds_claims_to_validated_matrix(self):
        source = (ROOT / "scripts/validate_five_esm_late_drought_public_claims.py").read_text()
        ast.parse(source)
        self.assertIn('validation["matrix_sha256"] == digest(paths["matrix"])', source)
        self.assertIn('primary == evidence["primary_rainfed_season_spei3"]', source)
        self.assertIn('"yield_response": False', source)
        self.assertIn('"damage": False', source)
        self.assertIn('"scc": False', source)


if __name__ == "__main__":
    unittest.main()
