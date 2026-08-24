"""Run or verify the frozen PhysGauge R2 learned-dynamics experiment."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from physgauge.r2 import (  # noqa: E402
    R2Config,
    run_r2_experiment,
    verify_r2_bundle,
    write_r2_bundle,
)

DEFAULT_OUTPUT = ROOT / "docs" / "evidence" / "r2"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if args.verify:
        manifest = verify_r2_bundle(args.output, expected_config=R2Config())
        print(
            f"r2-evidence=PASS protocol={manifest['protocol_id']} "
            f"artifacts={len(manifest['artifacts'])}"
        )
        return 0

    result, split_manifest = run_r2_experiment(R2Config(), progress=print)
    paths = write_r2_bundle(result, split_manifest, args.output)
    print(f"r2-evidence=WRITTEN outcome={result['summary']['decision']['outcome']}")
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
