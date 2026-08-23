"""Evidence-bundle rendering and integrity verification."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from .metrics import VISUAL_ERROR_METRICS

ARTIFACT_NAMES = ("results.json", "metrics.csv", "report.md", "sensitivity-matrix.svg")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def validate_result(result: dict[str, Any]) -> None:
    """Validate the frozen v1 scientific and structural acceptance criteria."""

    if result.get("schema_version") != "1.0":
        raise ValueError("unsupported evidence schema")
    summary = result.get("summary", {})
    if not summary.get("all_oracles_validated"):
        raise ValueError("one or more oracle cases failed validation")
    if not summary.get("all_expected_violations_detected"):
        raise ValueError("a controlled physical violation escaped its oracle metric")
    candidates = summary.get("candidates", {})
    if "correct" not in candidates or "time-reverse" not in candidates:
        raise ValueError("required controls are missing")
    correct = candidates["correct"]
    if correct["physics_detection_rate"] != 0.0:
        raise ValueError("correct control was falsely flagged")
    if correct["mean_metrics"]["mse"] > 1e-12:
        raise ValueError("correct control is not pixel-identical to the oracle")
    reverse_miss = candidates["time-reverse"]["exact_miss_rate"]["pixel_frechet"]
    if reverse_miss < 0.99:
        raise ValueError("order-invariant metric did not expose the expected time-order blind spot")


def _markdown(result: dict[str, Any]) -> str:
    config = result["config"]
    candidates = result["summary"]["candidates"]
    lines = [
        "# PhysGauge v1 calibration evidence",
        "",
        f"Protocol: `{result['protocol_id']}` · cases: {config['cases']} · "
        f"frames/case: {config['frames']} · seed: `{config['seed']}`.",
        "",
        "## Result",
        "",
        "Every injected violation was detected by its matching state-grounded oracle check. "
        "At the same time, one or more image/distribution metrics treated several controlled "
        "violations as close to the correct rollout relative to the random baseline.",
        "",
        "| candidate | expected violation | oracle detection | MSE exact miss | "
        "SSIM exact miss | Pixel Fréchet exact miss | temporal-gradient exact miss |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, entry in candidates.items():
        missed = entry["exact_miss_rate"]
        lines.append(
            f"| `{name}` | {entry['expected_violation']} | "
            f"{entry['physics_detection_rate']:.0%} | {missed['mse']:.0%} | "
            f"{missed['ssim_error']:.0%} | {missed['pixel_frechet']:.0%} | "
            f"{missed['temporal_gradient_mse']:.0%} |"
        )
    lines += [
        "",
        "## Severity response",
        "",
        "| corruption family | MSE | SSIM error | Pixel Fréchet | temporal-gradient MSE |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    monotonicity = result["summary"]["monotonicity"]
    for family in ("inelastic", "momentum-kick"):
        values = monotonicity[family]
        lines.append(
            f"| {family} | {values['mse']['strict_pair_accuracy']:.0%} | "
            f"{values['ssim_error']['strict_pair_accuracy']:.0%} | "
            f"{values['pixel_frechet']['strict_pair_accuracy']:.0%} | "
            f"{values['temporal_gradient_mse']['strict_pair_accuracy']:.0%} |"
        )
    lines += [
        "",
        "An **exact miss** requires a failed state-grounded check and metric error at or below "
        f"`{config['exact_miss_tolerance']:.0e}`. The SVG separately shows **low sensitivity**: "
        f"metric error below {config['visual_pass_ratio']:.0%} of the no-physics random baseline.",
        "",
        "## Interpretation boundary",
        "",
        "This controlled calibration result shows that a metric can miss known physical or "
        "causal corruptions in this analytical collision world. It does **not** measure a "
        "learned world model, establish real-world model rankings, or prove that every public "
        "leaderboard has the same failure. PhysGauge is a metric unit test to run before broader "
        "benchmarks and human studies.",
        "",
        "`pixel_frechet` is an intentionally dependency-light Fréchet distance over tiny pixel "
        "features. It is not Inception FID or FVD. Its exact blindness to a time-reversed frame "
        "set demonstrates the consequence of discarding temporal order.",
        "",
    ]
    return "\n".join(lines)


def _svg(result: dict[str, Any]) -> str:
    candidates = [
        (name, entry)
        for name, entry in result["summary"]["candidates"].items()
        if name not in {"correct", "random"}
    ]
    labels = {
        "mse": "MSE",
        "ssim_error": "SSIM",
        "pixel_frechet": "Pixel Fréchet",
        "temporal_gradient_mse": "Temporal Δ",
    }
    left, top, cell_w, cell_h = 210, 80, 128, 42
    width = left + cell_w * len(VISUAL_ERROR_METRICS) + 24
    height = top + cell_h * len(candidates) + 54
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'font-family="Arial, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        '<text x="20" y="30" font-size="19" font-weight="700" fill="#10182b">'
        "Low-sensitivity rate by controlled corruption</text>",
        '<text x="20" y="52" font-size="11" fill="#53627a">relative to each case\'s random baseline</text>',
    ]
    for column, metric in enumerate(VISUAL_ERROR_METRICS):
        x = left + column * cell_w + cell_w / 2
        parts.append(
            f'<text x="{x:.1f}" y="70" text-anchor="middle" font-size="11" '
            f'fill="#34445d">{labels[metric]}</text>'
        )
    for row, (name, entry) in enumerate(candidates):
        y = top + row * cell_h
        parts.append(
            f'<text x="{left - 12}" y="{y + 26}" text-anchor="end" font-size="11" '
            f'fill="#34445d">{name}</text>'
        )
        for column, metric in enumerate(VISUAL_ERROR_METRICS):
            value = float(entry["low_sensitivity_rate"][metric])
            red = round(239 - 75 * value)
            green = round(244 - 173 * value)
            blue = round(255 - 12 * value)
            x = left + column * cell_w
            parts.append(
                f'<rect x="{x + 3}" y="{y + 3}" width="{cell_w - 6}" '
                f'height="{cell_h - 6}" rx="8" fill="rgb({red},{green},{blue})"/>'
            )
            parts.append(
                f'<text x="{x + cell_w / 2:.1f}" y="{y + 26}" text-anchor="middle" '
                f'font-size="12" font-weight="700" fill="#10182b">{value:.0%}</text>'
            )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _csv(result: dict[str, Any]) -> str:
    records = result["records"]
    columns = list(records[0].keys())
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_bundle(result: dict[str, Any], output_dir: str | Path) -> dict[str, Path]:
    validate_result(result)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    payloads = {
        "results.json": _canonical_json(result),
        "metrics.csv": _csv(result),
        "report.md": _markdown(result),
        "sensitivity-matrix.svg": _svg(result),
    }
    paths: dict[str, Path] = {}
    for name, payload in payloads.items():
        path = destination / name
        path.write_text(payload, encoding="utf-8", newline="\n")
        paths[name] = path
    manifest = {
        "schema_version": "1.0",
        "protocol_id": result["protocol_id"],
        "artifacts": {name: _sha256(path) for name, path in paths.items()},
    }
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(_canonical_json(manifest), encoding="utf-8", newline="\n")
    paths["manifest.json"] = manifest_path
    return paths


def verify_bundle(bundle_dir: str | Path) -> dict[str, Any]:
    directory = Path(bundle_dir)
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"missing manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_files = {*ARTIFACT_NAMES, "manifest.json"}
    actual_files = {path.name for path in directory.iterdir() if path.is_file()}
    if actual_files != expected_files:
        raise ValueError(
            f"bundle file set mismatch: expected {sorted(expected_files)}, "
            f"found {sorted(actual_files)}"
        )
    for name in ARTIFACT_NAMES:
        path = directory / name
        if not path.is_file():
            raise ValueError(f"missing artifact: {path}")
        expected = manifest.get("artifacts", {}).get(name)
        actual = _sha256(path)
        if actual != expected:
            raise ValueError(f"hash mismatch for {name}")
    result = json.loads((directory / "results.json").read_text(encoding="utf-8"))
    validate_result(result)
    if manifest.get("protocol_id") != result.get("protocol_id"):
        raise ValueError("manifest protocol does not match results")
    return manifest
