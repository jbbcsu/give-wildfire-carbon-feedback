#!/usr/bin/env python3
from pathlib import Path
import unittest


class TestLateDroughtEvictionContract(unittest.TestCase):
    def test_deletion_is_exact_and_fail_closed(self):
        source = (Path(__file__).resolve().parent/"evict_validated_late_drought_extrema_pair.py").read_text()
        self.assertIn('validation.get("status") == "passed"', source)
        self.assertIn('{"tasmin", "tasmax"}', source)
        self.assertIn('digest(path, "sha512")', source)
        self.assertIn("path.unlink()", source)
        self.assertNotIn("rmtree", source)
        self.assertNotIn("glob(\"*\")", source)


if __name__ == "__main__":
    unittest.main()
