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


def _assert_reproduced(expected: Any, actual: Any, path: str = "result") -> None:
    """Compare the full result while tolerating cross-platform floating-point noise."""

    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(expected) != set(actual):
            raise ValueError(f"reproduction key mismatch at {path}")
        for key in expected:
            _assert_reproduced(expected[key], actual[key], f"{path}.{key}")
        return
    if isinstance(expected, list | tuple):
        if not isinstance(actual, list | tuple) or len(expected) != len(actual):
            raise ValueError(f"reproduction length mismatch at {path}")
        for index, (expected_item, actual_item) in enumerate(
            zip(expected, actual, strict=True)
        ):
            _assert_reproduced(expected_item, actual_item, f"{path}[{index}]")
        return
    if isinstance(expected, bool | str) or expected is None:
        if expected != actual:
            raise ValueError(f"reproduction value mismatch at {path}")
        return
    if isinstance(expected, int | float):
        try:
            np.testing.assert_allclose(expected, actual, rtol=1e-8, atol=1e-10)
        except AssertionError as exc:
            raise ValueError(f"reproduction numeric mismatch at {path}") from exc
        return
    if expected != actual:
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
    _assert_reproduced(expected, actual)
    print(f"evidence=PASS protocol={actual['protocol_id']} records={len(actual['records'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
