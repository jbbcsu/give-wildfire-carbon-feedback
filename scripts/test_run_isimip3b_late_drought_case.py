#!/usr/bin/env python3
from pathlib import Path
import unittest


class TestLateDroughtCaseContract(unittest.TestCase):
    def test_case_is_sequential_and_fail_closed(self):
        source = (Path(__file__).resolve().parent/"run_isimip3b_late_drought_case.py").read_text()
        self.assertIn('== {"tasmin", "tasmax"}', source)
        self.assertIn("MIN_FREE+needed+DOWNLOAD_HEADROOM", source)
        self.assertIn('digest(partial) == record["sha512"]', source)
        self.assertIn('"--retry-all-errors"', source)
        self.assertIn('"--retry", "50"', source)
        self.assertIn('"--speed-limit", "1024", "--speed-time", "120"', source)
        self.assertIn("max_mib=512", source)
        self.assertIn("max_new_disk_mib=128", source)
        self.assertIn('json.loads(validation.read_text())["status"] == "passed"', source)
        self.assertIn("evict_validated_late_drought_extrema_pair.py", source)
        self.assertIn("summarize_isimip3b_late_drought_crop_windows.py", source)
        self.assertIn("validate_isimip3b_late_drought_crop_windows.py", source)


if __name__ == "__main__":
    unittest.main()
