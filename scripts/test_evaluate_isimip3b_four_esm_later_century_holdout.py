#!/usr/bin/env python3
"""Contract failures for the four-ESM later-century holdout."""

from __future__ import annotations

import copy
import tomllib
from pathlib import Path

from evaluate_isimip3b_four_esm_later_century_holdout import validate_config


ROOT = Path(__file__).resolve().parents[1]
for name, period in (("isimip3b_four_esm_midcentury_holdout_v1.toml", "midcentury"), ("isimip3b_four_esm_endcentury_holdout_v1.toml", "endcentury")):
    config = tomllib.loads((ROOT / "config" / name).read_text(encoding="utf-8"))
    validate_config(config)
    assert config["selection"]["period"] == period

five_config = tomllib.loads(
    (ROOT / "config/isimip3b_five_esm_midcentury_holdout_v1.toml").read_text(encoding="utf-8")
)
assert validate_config(five_config)["complete"] is True
assert len(five_config["training_products"]) == 5
five_end_config = tomllib.loads(
    (ROOT / "config/isimip3b_five_esm_endcentury_holdout_v1.toml").read_text(encoding="utf-8")
)
assert validate_config(five_end_config)["complete"] is True
assert five_end_config["selection"]["period"] == "endcentury"

bad = copy.deepcopy(config)
bad["limitations"]["damage_or_scc_authorized"] = True
try:
    validate_config(bad)
except ValueError:
    pass
else:
    raise AssertionError("opened SCC gate passed")

bad = copy.deepcopy(config)
bad["training_products"].pop()
try:
    validate_config(bad)
except ValueError:
    pass
else:
    raise AssertionError("incomplete ESM product passed")

print("four-ESM later-century holdout contract tests passed")
