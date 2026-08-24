import json
import tempfile
import unittest
from dataclasses import replace

import numpy as np

from physgauge import r2 as r2_module
from physgauge.r2 import (
    R2Config,
    build_split_manifest,
    build_transition_dataset,
    rollout_model,
    run_r2_experiment,
    train_model,
    verify_r2_bundle,
    write_r2_bundle,
)
from physgauge.world import make_case


class R2Tests(unittest.TestCase):
    def setUp(self):
        self.config = R2Config(
            train_cases=2,
            validation_cases=2,
            test_cases=2,
            model_seeds=(11,),
            frames=8,
            batch_size=32,
            max_epochs=2,
            patience=1,
        )

    def test_split_manifest_is_disjoint_and_complete(self):
        manifest = build_split_manifest(self.config)
        identifiers = []
        for split in manifest["splits"].values():
            identifiers.extend(
                (entry["base_seed"], entry["case_index"])
                for entry in split["cases"]
            )
        self.assertEqual(len(identifiers), 6)
        self.assertEqual(len(set(identifiers)), 6)

    def test_training_is_deterministic_and_rollout_starts_exactly(self):
        train = build_transition_dataset(
            self.config.train_base_seed, self.config.train_cases
        )
        validation = build_transition_dataset(
            self.config.validation_base_seed, self.config.validation_cases
        )
        first = train_model(self.config, 11, train, validation)
        second = train_model(self.config, 11, train, validation)
        self.assertEqual(first.checkpoint_sha256, second.checkpoint_sha256)
        cfg = make_case(self.config.test_base_seed, 0)
        trajectory = rollout_model(first, cfg)
        np.testing.assert_array_equal(trajectory[0], [*cfg.p1, *cfg.v1, *cfg.p2, *cfg.v2])
        self.assertTrue(np.isfinite(trajectory).all())

    def test_manual_backpropagation_matches_a_numeric_gradient(self):
        rng = np.random.default_rng(101)
        inputs = rng.normal(size=(4, 9)).astype(np.float32)
        targets = rng.normal(size=(4, 8)).astype(np.float32)
        params = r2_module._initialize_params(17, 3)
        _, gradients = r2_module._loss_and_gradients(params, inputs, targets)
        epsilon = 1e-3
        original = float(params["w1"][0, 0])
        params["w1"][0, 0] = original + epsilon
        high, _ = r2_module._loss_and_gradients(params, inputs, targets)
        params["w1"][0, 0] = original - epsilon
        low, _ = r2_module._loss_and_gradients(params, inputs, targets)
        params["w1"][0, 0] = original
        numeric = (high - low) / (2.0 * epsilon)
        self.assertAlmostEqual(float(gradients["w1"][0, 0]), numeric, delta=2e-4)

    def test_evidence_comparison_tolerates_only_numeric_noise(self):
        self.assertTrue(r2_module._values_equivalent({"x": 1.0}, {"x": 1.0 + 1e-13}))
        self.assertFalse(r2_module._values_equivalent({"x": 1.0}, {"x": 1.001}))

    def test_small_r2_bundle_verifies_and_rejects_tampering(self):
        result, split_manifest = run_r2_experiment(self.config)
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_r2_bundle(result, split_manifest, temp_dir)
            manifest = verify_r2_bundle(temp_dir)
            self.assertEqual(len(manifest["artifacts"]), 4)
            with self.assertRaisesRegex(ValueError, "frozen official protocol"):
                verify_r2_bundle(temp_dir, expected_config=R2Config())
            payload = json.loads(paths["results.json"].read_text(encoding="utf-8"))
            payload["summary"]["decision"]["outcome"] = "expand"
            write_r2_bundle(payload, split_manifest, temp_dir)
            with self.assertRaisesRegex(ValueError, "summary is inconsistent"):
                verify_r2_bundle(temp_dir)

            paths = write_r2_bundle(result, split_manifest, temp_dir)
            payload = json.loads(paths["results.json"].read_text(encoding="utf-8"))
            payload["schema_version"] = "tampered"
            paths["results.json"].write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                verify_r2_bundle(temp_dir)

    def test_invalid_target_band_is_rejected(self):
        config = replace(self.config, target_error_rate_minimum=0.8)
        with self.assertRaisesRegex(ValueError, "target error band"):
            config.validate()


if __name__ == "__main__":
    unittest.main()
