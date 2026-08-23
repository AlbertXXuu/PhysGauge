import unittest

import numpy as np

from physgauge.world import (
    WorldConfig,
    first_contact_index,
    make_case,
    simulate,
    step,
    total_energy,
    total_momentum,
    validate_oracle,
)


class WorldTests(unittest.TestCase):
    def test_default_oracle_satisfies_contract(self):
        cfg = WorldConfig()
        trajectory = simulate(cfg)
        validate_oracle(trajectory, cfg)
        self.assertLess(first_contact_index(trajectory, cfg), cfg.n_steps)
        self.assertAlmostEqual(total_energy(trajectory[0]), total_energy(trajectory[-1]))
        np.testing.assert_allclose(
            total_momentum(trajectory[0]), total_momentum(trajectory[-1]), atol=1e-12
        )

    def test_generated_cases_are_reproducible_and_valid(self):
        for index in range(32):
            first = make_case(20260824, index)
            second = make_case(20260824, index)
            self.assertEqual(first, second)
            validate_oracle(simulate(first), first)

    def test_different_case_indices_change_geometry(self):
        self.assertNotEqual(make_case(4, 0).p1, make_case(4, 1).p1)

    def test_invalid_restitution_is_rejected(self):
        cfg = WorldConfig()
        with self.assertRaisesRegex(ValueError, "restitution"):
            step(simulate(cfg)[0], cfg, restitution=1.1)

    def test_invalid_world_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "diameter"):
            WorldConfig(radius=0.6).validate()


if __name__ == "__main__":
    unittest.main()
