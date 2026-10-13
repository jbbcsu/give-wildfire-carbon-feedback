import csv
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_agriculture_replacement_stage import validate


class AgricultureReplacementStageTests(unittest.TestCase):
    def make_stage(self, parent: Path, rows=None, draws=3) -> Path:
        stage = parent / f"pulse2025_n{draws}_seed24523438"
        stage.mkdir()
        if rows is None:
            rows = [
                ["legacy", "10", "1", "8", "10", "12", str(draws)],
                ["updated", "20", "2", "15", "20", "25", str(draws)],
            ]
        summary = stage / "agriculture_replacement_summary.csv"
        with summary.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["version", "expected_scc_2020usd_per_tco2", "se_expected_scc", "q05", "median", "q95", "draws"])
            writer.writerows(rows)
        for version in ("legacy", "updated"):
            with (stage / f"{version}_agriculture_draws_2020usd_per_tco2.csv").open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["trial", "scc_2020usd_per_tco2"])
                writer.writerows((index, index * 1.0) for index in range(1, draws + 1))
        return summary

    def test_valid_stage_is_not_promoted(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            result = validate(self.make_stage(Path(directory)))
        self.assertEqual(result["updated_minus_legacy_mean_2020usd_per_tco2"], 10)
        self.assertFalse(result["inference"]["mean_delta_promoted"])
        self.assertFalse(result["inference"]["draw_level_delta_allowed"])

    def test_wrong_pulse_year_fails(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            summary = self.make_stage(Path(directory))
            renamed = summary.parent.with_name("pulse2020_n3_seed24523438")
            summary.parent.rename(renamed)
            with self.assertRaisesRegex(ValueError, "pulse year"):
                validate(renamed / summary.name)

    def test_missing_version_fails(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            rows = [["legacy", "10", "1", "8", "10", "12", "3"]]
            summary = self.make_stage(Path(directory), rows=rows)
            with self.assertRaisesRegex(ValueError, "two version"):
                validate(summary)

    def test_mismatched_draw_file_fails(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            summary = self.make_stage(Path(directory))
            draw_file = summary.parent / "legacy_agriculture_draws_2020usd_per_tco2.csv"
            draw_file.write_text("trial,scc_2020usd_per_tco2\n1,1\n")
            with self.assertRaisesRegex(ValueError, "draw file length"):
                validate(summary)

    def test_quantile_order_fails(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            rows = [
                ["legacy", "10", "1", "11", "10", "12", "3"],
                ["updated", "20", "2", "15", "20", "25", "3"],
            ]
            summary = self.make_stage(Path(directory), rows=rows)
            with self.assertRaisesRegex(ValueError, "quantile order"):
                validate(summary)

    def test_memory_cap_violation_fails(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            summary = self.make_stage(Path(directory))
            (summary.parent / "run_metadata.csv").write_text(
                "julia_version,julia_threads,pulse_year,pulse_size,seed,draws,process_peak_rss_bytes,max_rss_bytes\n"
                "1.12.5,1,2025,0.0001,24523438,3,536870913,536870912\n"
            )
            with self.assertRaisesRegex(ValueError, "memory cap exceeded"):
                validate(summary)


if __name__ == "__main__":
    unittest.main()
