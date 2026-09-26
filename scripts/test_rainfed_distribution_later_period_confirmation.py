#!/usr/bin/env python3
"""Contract checks for the frozen later-period confirmation family."""
from __future__ import annotations

import unittest

from evaluate_rainfed_distribution_later_period_confirmation import (
    CONFIG_DEFAULT,
    load_config,
    resolve,
)


class LaterConfirmationTests(unittest.TestCase):
    def test_frozen_family_and_unavailable_spring_wheat(self) -> None:
        config, _, models = load_config(CONFIG_DEFAULT)
        frozen = {(row["crop"], row["candidate_model"]) for row in config["confirmations"]}
        self.assertEqual(
            frozen,
            {
                ("mai", "quantity_plus_timing_concentration"),
                ("soy", "quantity_plus_all_distribution"),
            },
        )
        self.assertTrue(all(model in models for _, model in frozen))
        unavailable = config["unavailable"][0]
        self.assertEqual(unavailable["crop"], "swh")
        self.assertFalse(resolve(unavailable["expected_source_path"]).exists())


if __name__ == "__main__":
    unittest.main()
