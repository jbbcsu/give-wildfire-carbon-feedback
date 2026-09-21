import unittest

from export_five_esm_maize_area_weather_public import build_public
from test_render_five_esm_maize_area_weather_report import FiveEsmReportTests


class FiveEsmPublicExportTests(unittest.TestCase):
    def test_export_keeps_contrasts_and_drops_annual_panels(self):
        result, audit = FiveEsmReportTests().fixture()
        result.update({
            "crop": "mai", "irrigation": "noirr", "weight_year": 2000,
            "weights_sha256": "weights", "years": list(range(2092, 2100)),
            "original_positive_area_cells": 30821,
            "original_positive_area_ha": 108086337.0,
            "matched_area_ha": 108038665.0,
            "annual_panels": ["must not be public"],
        })
        resource = {
            "status": "completed", "returncode": 0, "max_mib": 512,
            "min_free_gib": 130, "sampled_peak_group_rss_bytes": 10,
            "sampled_peak_new_disk_bytes": 20,
        }
        public = build_public(result, audit, resource, resource, "primary", "audit")
        self.assertNotIn("annual_panels", public)
        self.assertFalse(public["annual_panels_in_public_receipt"])
        self.assertEqual(public["scenario_minus_ssp126"], result["scenario_minus_ssp126"])

    def test_failed_resource_receipt_fails(self):
        result, audit = FiveEsmReportTests().fixture()
        result.update({
            "crop": "mai", "irrigation": "noirr", "weight_year": 2000,
            "weights_sha256": "weights", "years": list(range(2092, 2100)),
            "original_positive_area_cells": 30821,
            "original_positive_area_ha": 1.0, "matched_area_ha": 1.0,
        })
        failed = {"status": "failed", "returncode": 1, "max_mib": 512,
                  "min_free_gib": 130, "sampled_peak_group_rss_bytes": 1,
                  "sampled_peak_new_disk_bytes": 0}
        with self.assertRaises(ValueError):
            build_public(result, audit, failed, failed, "primary", "audit")


if __name__ == "__main__":
    unittest.main()
