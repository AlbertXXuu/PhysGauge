"""Fail CI when release-critical repository invariants drift."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import physgauge  # noqa: E402
from physgauge.r2 import R2Config, verify_r2_bundle  # noqa: E402
from physgauge.report import verify_bundle  # noqa: E402

REQUIRED = (
    "README.md",
    "README.zh-CN.md",
    "LICENSE",
    "MANIFEST.in",
    "CHANGELOG.md",
    "CITATION.cff",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "pyproject.toml",
    ".github/workflows/ci.yml",
    "docs/ERRATA.md",
    "docs/ROADMAP.md",
    "docs/protocol.md",
    "docs/studio.md",
    "docs/assets/alvenx-wordmark.svg",
    "src/physgauge/assets/brand/alvenx-wordmark.svg",
    "src/physgauge/assets/brand/alvenx-monogram.svg",
    "src/physgauge/assets/evidence/studio-v1.json",
    "src/physgauge/assets/fonts/InstrumentSans-wdth-wght.woff2",
    "docs/r2-protocol.md",
    "docs/research-landscape.md",
    "docs/evidence/v1.0.0/manifest.json",
    "docs/evidence/r2/manifest.json",
)
FORBIDDEN_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".venv", "build", "dist"}


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = metadata["project"]["version"]
    if declared != physgauge.__version__:
        errors.append(
            f"version mismatch: pyproject={declared}, package={physgauge.__version__}"
        )

    tracked = []
    try:
        import subprocess

        output = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        tracked = [Path(line) for line in output.splitlines()]
    except (OSError, subprocess.CalledProcessError) as exc:
        errors.append(f"cannot inspect tracked files: {exc}")
    for path in tracked:
        if FORBIDDEN_PARTS.intersection(path.parts):
            errors.append(f"generated path is tracked: {path.as_posix()}")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if re.search(r"all .*leaderboard|every .*metric fails", readme, flags=re.IGNORECASE):
        errors.append("README contains an unsupported universal claim")

    lockup = (ROOT / "docs/assets/alvenx-wordmark.svg").read_text(encoding="utf-8")
    for fragment in (
        'viewBox="0 0 430 150"',
        "AlvenX — Physics Evidence",
        'id="tag-P"',
        'id="tag-H"',
        'id="tag-S"',
        'transform="translate(43.128 126) scale(.018 -.018)"',
    ):
        if fragment not in lockup:
            errors.append(f"README project lockup is missing: {fragment}")
    for relative in ("README.md", "README.zh-CN.md"):
        source = (ROOT / relative).read_text(encoding="utf-8")
        if "<strong>PHYSICS EVIDENCE</strong>" in source:
            errors.append(f"{relative} must use the single-SVG project lockup")

    evidence = ROOT / "docs" / "evidence" / "v1.0.0"
    if evidence.is_dir():
        try:
            verify_bundle(evidence)
        except (OSError, ValueError) as exc:
            errors.append(f"evidence verification failed: {exc}")

    r2_evidence = ROOT / "docs" / "evidence" / "r2"
    if r2_evidence.is_dir():
        try:
            verify_r2_bundle(r2_evidence, expected_config=R2Config())
        except (OSError, ValueError) as exc:
            errors.append(f"R2 evidence verification failed: {exc}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"repository=PASS version={declared} tracked_files={len(tracked)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
