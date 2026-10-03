import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "audit_official_catalog.py"
SPEC = importlib.util.spec_from_file_location("loca2_catalog_audit", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CatalogAuditTests(unittest.TestCase):
    def test_zmetadata_summary_keeps_only_required_daily_variables(self):
        metadata = {".zattrs": {"title": "x"}}
        for variable in ("pr", "tasmin", "tasmax", "lat"):
            metadata[f"{variable}/.zattrs"] = {"units": "u"}
            metadata[f"{variable}/.zarray"] = {"shape": [2, 3], "chunks": [1, 3], "dtype": "<f4"}
        result = MODULE.zmetadata_summary({"metadata": metadata})
        self.assertEqual(result["variables"], ["pr", "tasmax", "tasmin"])
        self.assertNotIn("lat", result["arrays"])

    def test_sciencebase_summary_preserves_sizes(self):
        payload = {
            "id": "id",
            "title": "title",
            "rights": "CC0",
            "hasChildren": False,
            "files": [{"name": "a.nc", "size": 12, "url": "https://example/a"}],
        }
        result = MODULE.sciencebase_summary(payload)
        self.assertEqual(result["total_file_bytes"], 12)
        self.assertEqual(result["files"][0]["bytes"], 12)

    def test_metadata_endpoint_keys_are_unique(self):
        keys = set(MODULE.SCIENCEBASE) | set(MODULE.STAC)
        prefixed = {f"zmetadata_{key}" for key in MODULE.ZMETADATA}
        self.assertEqual(len(keys) + len(prefixed), 7)
        self.assertTrue(keys.isdisjoint(prefixed))


if __name__ == "__main__":
    unittest.main()
