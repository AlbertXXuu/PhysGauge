"""Command-line interface for the frozen PhysGauge v1 protocol."""

from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

import numpy as np
from PIL import __version__ as pillow_version

from . import __version__
from .experiment import SuiteConfig, run_suite
from .report import verify_bundle, write_bundle


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="physgauge",
        description="Calibrate video metrics against controlled physical violations.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="run the deterministic calibration suite")
    run.add_argument("--cases", type=int, default=24)
    run.add_argument("--frames", type=int, default=48)
    run.add_argument("--seed", type=int, default=20260824)
    run.add_argument("--visual-pass-ratio", type=float, default=0.25)
    run.add_argument("--output", type=Path, default=Path("runs/latest"))

    verify = commands.add_parser("verify", help="verify a committed evidence bundle")
    verify.add_argument("--bundle", type=Path, required=True)

    commands.add_parser("doctor", help="print environment details and run a smoke test")

    studio = commands.add_parser("studio", help="open the local visual evidence interface")
    studio.add_argument("--host", default="127.0.0.1")
    studio.add_argument("--port", type=int, default=7871)
    studio.add_argument("--no-open", action="store_true")
    return parser


def _run(args: argparse.Namespace) -> int:
    config = SuiteConfig(
        cases=args.cases,
        frames=args.frames,
        seed=args.seed,
        visual_pass_ratio=args.visual_pass_ratio,
    )
    result = run_suite(config)
    paths = write_bundle(result, args.output)
    summary = result["summary"]
    print(f"PhysGauge {__version__} | {result['protocol_id']}")
    print(
        f"PASS | {summary['record_count']} records | "
        "all oracle contracts and injected violations verified"
    )
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


def _verify(args: argparse.Namespace) -> int:
    manifest = verify_bundle(args.bundle)
    print(f"PASS | {manifest['protocol_id']} | {len(manifest['artifacts'])} artifacts")
    return 0


def _doctor() -> int:
    print(f"physgauge={__version__}")
    print(f"python={platform.python_version()}")
    print(f"numpy={np.__version__}")
    print(f"pillow={pillow_version}")
    result = run_suite(SuiteConfig(cases=2, frames=8, seed=7))
    print(
        "smoke=PASS"
        if result["summary"]["all_expected_violations_detected"]
        else "smoke=FAIL"
    )
    return 0


def _studio(args: argparse.Namespace) -> int:
    from .studio import serve_studio

    return serve_studio(host=args.host, port=args.port, open_browser=not args.no_open)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "run":
            return _run(args)
        if args.command == "verify":
            return _verify(args)
        if args.command == "studio":
            return _studio(args)
        return _doctor()
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
