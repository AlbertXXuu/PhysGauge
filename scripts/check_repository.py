"""Fail CI when release-critical repository invariants drift."""

from __future__ import annotations

import hashlib
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
    "docs/V1.1.2_RELEASE_SOURCE_VALIDATION.md",
    "docs/ROADMAP.md",
    "docs/protocol.md",
    "docs/studio.md",
    "docs/assets/alvenx-wordmark.svg",
    "docs/assets/alvenx-lockup.svg",
    "scripts/check_home_navigation.js",
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

    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    if "include scripts/check_home_navigation.js" not in manifest:
        errors.append("source distribution must include the browser acceptance check")

    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = metadata["project"]["version"]
    if declared != physgauge.__version__:
        errors.append(f"version mismatch: pyproject={declared}, package={physgauge.__version__}")
    release_markers = {
        "README.md": f"git clone --branch v{declared} --depth 1",
        "README.zh-CN.md": f"git clone --branch v{declared} --depth 1",
        "CHANGELOG.md": f"## [{declared}] - ",
        "docs/MAINTENANCE.md": f"Current public release: `v{declared}`",
        "src/physgauge/studio.py": f"Studio v{declared} · Calibration evidence v1.0.0",
    }
    for relative, marker in release_markers.items():
        source = (ROOT / relative).read_text(encoding="utf-8")
        if marker not in source:
            errors.append(f"release identity mismatch in {relative}: expected {marker!r}")

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

    wordmark = (ROOT / "docs/assets/alvenx-wordmark.svg").read_text(encoding="utf-8")
    if hashlib.sha256(wordmark.encode("utf-8")).hexdigest() != (
        "6cc422fb2ed289bee723f1c6e6d19baec63c18d988616eb5b90d8332a30b7b1e"
    ):
        errors.append("README wordmark differs from the canonical AlvenX asset")
    lockup = (ROOT / "docs/assets/alvenx-lockup.svg").read_text(encoding="utf-8")
    for fragment in (
        'viewBox="0 0 430 150"',
        "AlvenX — Physics Evidence",
        'id="tag-P"',
        'id="tag-H"',
        'id="tag-S"',
        'transform="translate(43.128 126) scale(.018 -.018)"',
    ):
        if fragment not in lockup:
            errors.append(f"Preserved project lockup is missing: {fragment}")
    readme_header = (
        '<p align="center">\n'
        '  <img src="docs/assets/alvenx-wordmark.svg" width="320" alt="AlvenX">\n'
        "  <br>\n"
        "  <sub>PHYSICS EVIDENCE</sub>\n"
        "</p>\n"
    )
    for relative in ("README.md", "README.zh-CN.md"):
        source = (ROOT / relative).read_text(encoding="utf-8")
        if not source.startswith(readme_header):
            errors.append(f"{relative} must use the canonical wordmark and separate subtitle")

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
