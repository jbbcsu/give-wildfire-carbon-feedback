#!/usr/bin/env python3
from validate_september19_evidence_bundle import validate


result = validate()
assert result["status"] == "passed"
assert result["required_artifact_count"] == 13
assert result["future_spei_validation_checks"] == 1_066_451
assert result["four_corner_validation_checks"] == 3_081
assert result["fixed_support_validation_checks"] == 1_929
assert result["empirical_damage_authorized"] is False
assert result["give_export_authorized"] is False
assert result["scc_authorized"] is False
print("September 19 evidence-bundle tests passed")
