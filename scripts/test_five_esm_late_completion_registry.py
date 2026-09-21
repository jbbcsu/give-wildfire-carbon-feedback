import unittest

from compare_five_esm_maize_area_weather import ESMS
from compare_three_esm_maize_area_weather import SCENARIOS
from continue_five_esm_late_completion import CASES
from continue_isimip3b_global_maize_tiles import SOURCES


class FiveEsmLateRegistryTests(unittest.TestCase):
    def test_all_late_anchors_are_source_registered(self):
        expected = {(esm, scenario, 2092) for esm in ESMS for scenario in SCENARIOS}
        self.assertTrue(expected <= set(SOURCES))

    def test_completion_queue_is_exact_missing_matrix(self):
        self.assertEqual(
            set(CASES),
            {
                ("gfdl-esm4", "ssp370"),
                ("gfdl-esm4", "ssp585"),
                ("mri-esm2-0", "ssp126"),
                ("mri-esm2-0", "ssp370"),
            },
        )


if __name__ == "__main__":
    unittest.main()
