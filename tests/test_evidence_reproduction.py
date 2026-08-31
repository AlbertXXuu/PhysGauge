import unittest

from scripts.build_evidence import _assert_reproduced


class EvidenceReproductionTests(unittest.TestCase):
    def test_small_continuous_metric_drift_is_accepted(self):
        expected = {
            "records": [{"mse": 1.0}],
            "summary": {
                "candidates": {"correct": {"mean_metrics": {"mse": 1.0}}},
                "monotonicity": {"inelastic": {"mse": {"values": [1.0]}}},
            },
        }
        actual = {
            "records": [{"mse": 1.0 + 5e-7}],
            "summary": {
                "candidates": {"correct": {"mean_metrics": {"mse": 1.0 + 5e-7}}},
                "monotonicity": {"inelastic": {"mse": {"values": [1.0 + 5e-7]}}},
            },
        }

        _assert_reproduced(expected, actual)

    def test_continuous_metric_drift_over_threshold_is_rejected(self):
        expected = {"records": [{"mse": 1.0}]}
        actual = {"records": [{"mse": 1.0 + 2e-6}]}

        with self.assertRaisesRegex(ValueError, r"numeric mismatch at result\.records\[0\]\.mse"):
            _assert_reproduced(expected, actual)

    def test_decision_values_require_exact_equality(self):
        cases = (
            (
                {"records": [{"physics_failed": 1.0}]},
                {"records": [{"physics_failed": 1.0 - 1e-9}]},
            ),
            (
                {"records": [{"low_sensitivity_mse": 1.0}]},
                {"records": [{"low_sensitivity_mse": 1.0 - 1e-9}]},
            ),
            (
                {"records": [{"exact_miss_mse": 1.0}]},
                {"records": [{"exact_miss_mse": 1.0 - 1e-9}]},
            ),
            (
                {"summary": {"candidates": {"correct": {"physics_detection_rate": 1.0}}}},
                {"summary": {"candidates": {"correct": {"physics_detection_rate": 1.0 - 1e-9}}}},
            ),
            (
                {"summary": {"candidates": {"correct": {"low_sensitivity_rate": {"mse": 1.0}}}}},
                {
                    "summary": {
                        "candidates": {"correct": {"low_sensitivity_rate": {"mse": 1.0 - 1e-9}}}
                    }
                },
            ),
            (
                {"summary": {"candidates": {"correct": {"exact_miss_rate": {"mse": 1.0}}}}},
                {"summary": {"candidates": {"correct": {"exact_miss_rate": {"mse": 1.0 - 1e-9}}}}},
            ),
            (
                {
                    "summary": {
                        "monotonicity": {"inelastic": {"mse": {"strict_pair_accuracy": 1.0}}}
                    }
                },
                {
                    "summary": {
                        "monotonicity": {"inelastic": {"mse": {"strict_pair_accuracy": 1.0 - 1e-9}}}
                    }
                },
            ),
        )

        for expected, actual in cases:
            with self.subTest(actual=actual), self.assertRaisesRegex(ValueError, "value mismatch"):
                _assert_reproduced(expected, actual)

    def test_counts_config_and_identity_require_exact_equality(self):
        cases = (
            ({"summary": {"record_count": 240}}, {"summary": {"record_count": 241}}),
            ({"summary": {"record_count": 240}}, {"summary": {"record_count": 240.0}}),
            (
                {"config": {"visual_pass_ratio": 0.25}},
                {"config": {"visual_pass_ratio": 0.250000001}},
            ),
            (
                {"summary": {"all_oracles_validated": True}},
                {"summary": {"all_oracles_validated": 1}},
            ),
            ({"records": [{"severity": 0.5}]}, {"records": [{"severity": 0.500000001}]}),
            ({"protocol_id": "protocol-v1"}, {"protocol_id": "protocol-v2"}),
            (
                {"records": [{"case_id": "case-000", "candidate": "correct"}]},
                {"records": [{"case_id": "case-000", "candidate": "random"}]},
            ),
        )

        for expected, actual in cases:
            with self.subTest(actual=actual), self.assertRaisesRegex(ValueError, "value mismatch"):
                _assert_reproduced(expected, actual)

    def test_structure_requires_exact_keys_and_container_types(self):
        cases = (
            ({"records": []}, {"records": [], "extra": None}),
            ({"records": [{"mse": 1.0}]}, {"records": []}),
            ({"records": []}, {"records": ()}),
        )

        for expected, actual in cases:
            with (
                self.subTest(actual=actual),
                self.assertRaisesRegex(ValueError, "(key|length) mismatch"),
            ):
                _assert_reproduced(expected, actual)

    def test_unclassified_future_metric_is_exact_by_default(self):
        expected = {
            "summary": {"monotonicity": {"inelastic": {"future_metric": {"values": [1.0]}}}}
        }
        actual = {
            "summary": {"monotonicity": {"inelastic": {"future_metric": {"values": [1.0 + 5e-7]}}}}
        }

        with self.assertRaisesRegex(ValueError, "value mismatch"):
            _assert_reproduced(expected, actual)


if __name__ == "__main__":
    unittest.main()
