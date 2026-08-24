import unittest

import numpy as np

from physgauge.metrics import (
    collision_event_error,
    energy_drift,
    evaluate_trajectory,
    kinematic_residual,
    momentum_drift,
    pixel_frechet,
    temporal_gradient_mse,
    visual_metrics,
)
from physgauge.predictors import candidate_specs
from physgauge.render import render_trajectory
from physgauge.world import WorldConfig, make_case, simulate


class MetricTests(unittest.TestCase):
    def setUp(self):
        self.cfg = WorldConfig()
        self.oracle = simulate(self.cfg)
        self.frames = render_trajectory(self.oracle, self.cfg, n_frames=24)

    def test_identity_is_exact(self):
        metrics = visual_metrics(self.frames, self.frames)
        self.assertEqual(metrics["mse"], 0.0)
        self.assertAlmostEqual(metrics["ssim"], 1.0)
        self.assertLess(metrics["pixel_frechet"], 1e-10)
        self.assertEqual(metrics["temporal_gradient_mse"], 0.0)

    def test_order_invariant_metric_misses_frame_order_reversal(self):
        reversed_frames = self.frames[::-1]
        self.assertLess(pixel_frechet(reversed_frames, self.frames), 1e-10)
        self.assertGreater(temporal_gradient_mse(reversed_frames, self.frames), 0.0)

    def test_r2_kinematic_threshold_covers_frozen_test_oracles(self):
        maximum = max(
            kinematic_residual(simulate(cfg), cfg)
            for cfg in (make_case(20260827, index) for index in range(256))
        )
        self.assertLess(maximum, 0.05)

    def test_each_controlled_family_triggers_its_oracle_check(self):
        specs = {spec.name: spec for spec in candidate_specs()}
        inelastic = specs["inelastic-0.95"].build(self.cfg, 0)
        kicked = specs["momentum-kick-0.025"].build(self.cfg, 0)
        dropped = specs["collision-dropout"].build(self.cfg, 0)
        self.assertGreater(energy_drift(inelastic), 1e-4)
        self.assertGreater(momentum_drift(kicked), 1e-4)
        self.assertEqual(collision_event_error(dropped, self.oracle, self.cfg), 1.0)

    def test_public_pair_evaluator_rejects_shape_mismatch(self):
        with self.assertRaisesRegex(ValueError, "same shape"):
            evaluate_trajectory(
                self.oracle[:-1], self.oracle, self.cfg, self.frames, self.frames
            )

    def test_public_pair_evaluator_returns_both_metric_families(self):
        measured = evaluate_trajectory(
            self.oracle, self.oracle, self.cfg, self.frames, self.frames
        )
        self.assertIn("energy_drift", measured)
        self.assertIn("pixel_frechet", measured)
        self.assertTrue(np.isfinite(list(measured.values())).all())


if __name__ == "__main__":
    unittest.main()
