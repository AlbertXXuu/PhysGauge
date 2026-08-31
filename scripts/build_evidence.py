"""Build the PhysGauge v1 bundle or reproduce its complete scientific result."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from physgauge.experiment import SuiteConfig, run_suite  # noqa: E402
from physgauge.report import verify_bundle, write_bundle  # noqa: E402

DEFAULT_OUTPUT = ROOT / "docs" / "evidence" / "v1.0.0"

REPRODUCTION_RTOL = 1e-6
REPRODUCTION_ATOL = 1e-10
CONTINUOUS_METRICS = frozenset(
    {
        "collision_event_error",
        "energy_drift",
        "initial_condition_error",
        "kinematic_residual",
        "momentum_drift",
        "mse",
        "pixel_frechet",
        "position_rmse",
        "psnr",
        "ratio_to_random_mse",
        "ratio_to_random_pixel_frechet",
        "ratio_to_random_ssim_error",
        "ratio_to_random_temporal_gradient_mse",
        "ssim",
        "ssim_error",
        "temporal_gradient_mse",
        "velocity_rmse",
    }
)


def _is_continuous_metric_path(segments: tuple[str | int, ...]) -> bool:
    """Return whether a schema path contains a continuous measured value."""

    if (
        len(segments) == 3
        and segments[0] == "records"
        and isinstance(segments[1], int)
        and segments[2] in CONTINUOUS_METRICS
    ):
        return True
    if (
        len(segments) == 5
        and segments[:2] == ("summary", "candidates")
        and segments[3] == "mean_metrics"
        and segments[4] in CONTINUOUS_METRICS
    ):
        return True
    return (
        len(segments) == 6
        and segments[:2] == ("summary", "monotonicity")
        and segments[3] in CONTINUOUS_METRICS
        and segments[4] == "values"
        and isinstance(segments[5], int)
    )


def _assert_reproduced(expected: Any, actual: Any, path: str = "result") -> None:
    """Compare a reproduced result using schema-aware scientific semantics."""

    _assert_reproduced_at(expected, actual, (), path)


def _assert_reproduced_at(
    expected: Any,
    actual: Any,
    segments: tuple[str | int, ...],
    path: str,
) -> None:
    """Recurse through the result while keeping machine-readable schema context."""

    if isinstance(expected, dict):
        if type(actual) is not dict or set(expected) != set(actual):
            raise ValueError(f"reproduction key mismatch at {path}")
        for key in expected:
            _assert_reproduced_at(expected[key], actual[key], (*segments, key), f"{path}.{key}")
        return
    if isinstance(expected, list):
        if type(actual) is not list or len(expected) != len(actual):
            raise ValueError(f"reproduction length mismatch at {path}")
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual, strict=True)):
            _assert_reproduced_at(
                expected_item,
                actual_item,
                (*segments, index),
                f"{path}[{index}]",
            )
        return
    if isinstance(expected, float) and _is_continuous_metric_path(segments):
        if type(actual) is not float:
            raise ValueError(f"reproduction numeric type mismatch at {path}")
        try:
            np.testing.assert_allclose(
                expected,
                actual,
                rtol=REPRODUCTION_RTOL,
                atol=REPRODUCTION_ATOL,
            )
        except AssertionError as exc:
            raise ValueError(f"reproduction numeric mismatch at {path}") from exc
        return
    if type(expected) is not type(actual) or expected != actual:
        raise ValueError(f"reproduction value mismatch at {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if not args.verify:
        result = run_suite(SuiteConfig())
        write_bundle(result, args.output)
        print(f"evidence=WRITTEN path={args.output}")
        return 0

    verify_bundle(args.output)
    expected = json.loads((args.output / "results.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temp_dir:
        actual = run_suite(SuiteConfig(**expected["config"]))
        write_bundle(actual, temp_dir)
        reproduced = json.loads((Path(temp_dir) / "results.json").read_text(encoding="utf-8"))
    _assert_reproduced(expected, reproduced)
    print(f"evidence=PASS protocol={actual['protocol_id']} records={len(actual['records'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
