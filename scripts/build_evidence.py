"""Build or reproduce the frozen PhysGauge v1 evidence bundle."""

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


def _assert_reproduced(expected: dict[str, Any], actual: dict[str, Any]) -> None:
    for key in ("schema_version", "protocol_id", "config"):
        if expected[key] != actual[key]:
            raise ValueError(f"reproduction mismatch in {key}")
    expected_summary, actual_summary = expected["summary"], actual["summary"]
    for key in (
        "candidate_count",
        "record_count",
        "all_oracles_validated",
        "all_expected_violations_detected",
    ):
        if expected_summary[key] != actual_summary[key]:
            raise ValueError(f"reproduction mismatch in summary.{key}")
    for name, expected_candidate in expected_summary["candidates"].items():
        actual_candidate = actual_summary["candidates"][name]
        if (
            expected_candidate["family"] != actual_candidate["family"]
            or expected_candidate["expected_violation"]
            != actual_candidate["expected_violation"]
        ):
            raise ValueError(f"candidate metadata mismatch: {name}")
        for group in (
            "mean_metrics",
            "low_sensitivity_rate",
            "exact_miss_rate",
        ):
            keys = sorted(expected_candidate[group])
            if keys != sorted(actual_candidate[group]):
                raise ValueError(f"metric key mismatch: {name}.{group}")
            np.testing.assert_allclose(
                [expected_candidate[group][key] for key in keys],
                [actual_candidate[group][key] for key in keys],
                rtol=1e-8,
                atol=1e-10,
            )


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
    _assert_reproduced(expected, actual)
    print(f"evidence=PASS protocol={actual['protocol_id']} records={len(actual['records'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
