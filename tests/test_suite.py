import copy
import json
import tempfile
import unittest
from pathlib import Path

from physgauge.experiment import SuiteConfig, run_suite
from physgauge.report import verify_bundle, write_bundle


class SuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_suite(SuiteConfig(cases=3, frames=12, seed=41))

    def test_protocol_acceptance_criteria_hold(self):
        summary = self.result["summary"]
        self.assertTrue(summary["all_oracles_validated"])
        self.assertTrue(summary["all_expected_violations_detected"])
        self.assertEqual(summary["record_count"], 30)

    def test_frame_order_reversal_is_an_exact_distribution_metric_miss(self):
        reverse = self.result["summary"]["candidates"]["time-reverse"]
        self.assertEqual(reverse["exact_miss_rate"]["pixel_frechet"], 1.0)
        self.assertEqual(reverse["exact_miss_rate"]["mse"], 0.0)

    def test_severity_sweeps_are_monotonic(self):
        monotonicity = self.result["summary"]["monotonicity"]
        for family in ("inelastic", "momentum-kick"):
            for result in monotonicity[family].values():
                self.assertEqual(result["strict_pair_accuracy"], 1.0)

    def test_bundle_hashes_and_semantics_verify(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_bundle(self.result, temp_dir)
            manifest = verify_bundle(temp_dir)
            self.assertEqual(len(manifest["artifacts"]), 4)
            self.assertTrue(paths["report.md"].is_file())

    def test_report_derives_reversal_range_and_tolerance_from_result(self):
        result = copy.deepcopy(self.result)
        reverse_records = [
            record
            for record in result["records"]
            if record["candidate"] == "time-reverse"
        ]
        for record, distance in zip(
            reverse_records,
            (1.25e-16, 4.5e-15, 7.5e-15),
            strict=True,
        ):
            record["pixel_frechet"] = distance
        result["config"]["exact_miss_tolerance"] = 1e-9

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = write_bundle(result, temp_dir)["report.md"]
            report = report_path.read_text(encoding="utf-8")

        self.assertIn("distances range from 1.25e-16 to 7.5e-15", report)
        self.assertIn("`1e-09` exact-miss tolerance", report)

    def test_tampered_bundle_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            write_bundle(self.result, temp_dir)
            path = Path(temp_dir) / "results.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["schema_version"] = "tampered"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                verify_bundle(temp_dir)

    def test_unknown_manifest_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            write_bundle(self.result, temp_dir)
            path = Path(temp_dir) / "manifest.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["schema_version"] = "unknown"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "manifest schema"):
                verify_bundle(temp_dir)

    def test_manifest_artifact_set_must_be_exact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            write_bundle(self.result, temp_dir)
            path = Path(temp_dir) / "manifest.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["artifacts"]["unused.txt"] = "0" * 64
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "manifest artifact set"):
                verify_bundle(temp_dir)

    def test_manifest_artifacts_must_be_an_object(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            write_bundle(self.result, temp_dir)
            path = Path(temp_dir) / "manifest.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["artifacts"] = None
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "artifacts must be a JSON object"):
                verify_bundle(temp_dir)


if __name__ == "__main__":
    unittest.main()
