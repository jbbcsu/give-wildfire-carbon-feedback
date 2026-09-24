#!/usr/bin/env python3

from __future__ import annotations

import unittest

import pandas as pd

from build_hultgren_country_maize_value_weights_common_price import (
    OUTPUT_VALUE,
    SOURCE_VALUE,
    common_price_weights,
)


class CommonPriceWeightsTests(unittest.TestCase):
    def test_total_value_and_country_identity_are_preserved(self) -> None:
        frame = pd.DataFrame({
            "iso3": ["AAA", "BBB"],
            "native_lat_index": [1, 2],
            "native_lon_index": [3, 4],
            "matched_maize_production_mt": [2.0, 6.0],
            SOURCE_VALUE: [10.0, 30.0],
        })
        output, price = common_price_weights(frame)
        self.assertEqual(price, 5.0)
        self.assertEqual(output["iso3"].tolist(), ["AAA", "BBB"])
        self.assertEqual(output[OUTPUT_VALUE].tolist(), [10.0, 30.0])
        self.assertAlmostEqual(output[OUTPUT_VALUE].sum(), frame[SOURCE_VALUE].sum())

    def test_heterogeneous_source_prices_are_removed(self) -> None:
        frame = pd.DataFrame({
            "iso3": ["AAA", "BBB"],
            "native_lat_index": [1, 2],
            "native_lon_index": [3, 4],
            "matched_maize_production_mt": [1.0, 3.0],
            SOURCE_VALUE: [20.0, 20.0],
        })
        output, price = common_price_weights(frame)
        self.assertEqual(price, 10.0)
        self.assertEqual(output[OUTPUT_VALUE].tolist(), [10.0, 30.0])

    def test_nonpositive_source_is_rejected(self) -> None:
        frame = pd.DataFrame({
            "iso3": ["AAA"],
            "native_lat_index": [1],
            "native_lon_index": [2],
            "matched_maize_production_mt": [0.0],
            SOURCE_VALUE: [1.0],
        })
        with self.assertRaises(ValueError):
            common_price_weights(frame)


if __name__ == "__main__":
    unittest.main()
