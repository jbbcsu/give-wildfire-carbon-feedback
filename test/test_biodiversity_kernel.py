import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "python"))

from biodiversity_kernel import (  # noqa: E402
    climate_deficit,
    country_damage,
    next_biodiversity,
    no_climate_biodiversity,
    per_capita_wtp,
)


class BiodiversityKernelTests(unittest.TestCase):
    def test_species_stock(self):
        self.assertAlmostEqual(next_biodiversity(1, 0, theta=0.001, phi=0), 0.999)
        self.assertLess(next_biodiversity(1, 2, theta=0.001, phi=0.01), 0.999)
        self.assertAlmostEqual(no_climate_biodiversity(1, 2, theta=0.001), 0.999**2)
        self.assertAlmostEqual(climate_deficit(0.9, 0.8), 0.1)
        self.assertEqual(climate_deficit(0.8, 0.9), 0)

    def test_valuation(self):
        self.assertEqual(per_capita_wtp(100, 0.8, 0, beta=2), 0)
        self.assertGreater(per_capita_wtp(100, 0.8, 0.1, beta=2), 0)
        self.assertEqual(per_capita_wtp(100, 0.8, 0.1, beta=0), 0)
        self.assertAlmostEqual(
            country_damage(10, 100, 0.8, 0.1, beta=2),
            10 * per_capita_wtp(100, 0.8, 0.1, beta=2),
        )

    def test_domains(self):
        with self.assertRaises(ValueError):
            next_biodiversity(1, 10, theta=0.1, phi=0.1)
        with self.assertRaises(ValueError):
            per_capita_wtp(100, 0, 0.1, beta=1)


if __name__ == "__main__":
    unittest.main()
