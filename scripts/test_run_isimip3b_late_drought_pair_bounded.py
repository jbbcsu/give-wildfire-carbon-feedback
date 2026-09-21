#!/usr/bin/env python3
from pathlib import Path
import unittest


class TestLateDroughtPairGuard(unittest.TestCase):
    def test_declared_resource_contract(self):
        source = (Path(__file__).resolve().parent/"run_isimip3b_late_drought_pair_bounded.py").read_text()
        self.assertIn("max_mib=512", source)
        self.assertIn("min_free_gib=130", source)
        self.assertIn("max_new_disk_mib=128", source)
        self.assertIn("write_paths=[out_dir]", source)


if __name__ == "__main__":
    unittest.main()
