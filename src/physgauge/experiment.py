"""Reproducible calibration-suite runner and aggregate diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .metrics import VISUAL_ERROR_METRICS, evaluate_trajectory
from .predictors import CandidateSpec, candidate_specs
from .render import render_trajectory
from .world import make_case, simulate, validate_oracle

PROTOCOL_ID = "physgauge-collision-calibration-v1"


@dataclass(frozen=True)
class SuiteConfig:
    cases: int = 24
    frames: int = 48
    seed: int = 20260824
    visual_pass_ratio: float = 0.25
    exact_miss_tolerance: float = 1e-10

    def validate(self) -> None:
        if self.cases < 2:
            raise ValueError("cases must be at least 2")
        if self.frames < 8:
            raise ValueError("frames must be at least 8")
        if not 0.0 < self.visual_pass_ratio < 1.0:
            raise ValueError("visual_pass_ratio must be in (0, 1)")
        if not 0.0 < self.exact_miss_tolerance < 1e-4:
            raise ValueError("exact_miss_tolerance must be in (0, 1e-4)")


_PHYSICS_THRESHOLDS = {
    "energy": ("energy_drift", 1e-4),
    "momentum": ("momentum_drift", 1e-4),
    "collision": ("collision_event_error", 0.5),
    "initial-condition": ("initial_condition_error", 1e-6),
    "state": ("position_rmse", 0.05),
}


def _physics_failed(spec: CandidateSpec, metrics: dict[str, float]) -> bool:
    if spec.expected_violation == "none":
        return False
    metric, threshold = _PHYSICS_THRESHOLDS[spec.expected_violation]
    return metrics[metric] > threshold


def _mean(records: list[dict[str, Any]], key: str) -> float:
    return float(np.mean([float(record[key]) for record in records]))


def _candidate_summary(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for candidate in sorted({str(record["candidate"]) for record in records}):
        selected = [record for record in records if record["candidate"] == candidate]
        first = selected[0]
        entry: dict[str, Any] = {
            "family": first["family"],
            "severity": first["severity"],
            "expected_violation": first["expected_violation"],
            "physics_detection_rate": _mean(selected, "physics_failed"),
            "mean_metrics": {
                key: _mean(selected, key)
                for key in (
                    *VISUAL_ERROR_METRICS,
                    "position_rmse",
                    "velocity_rmse",
                    "initial_condition_error",
                    "energy_drift",
                    "momentum_drift",
                    "collision_event_error",
                    "kinematic_residual",
                )
            },
            "low_sensitivity_rate": {
                metric: _mean(selected, f"low_sensitivity_{metric}")
                for metric in VISUAL_ERROR_METRICS
            },
            "exact_miss_rate": {
                metric: _mean(selected, f"exact_miss_{metric}")
                for metric in VISUAL_ERROR_METRICS
            },
        }
        summary[candidate] = entry
    return summary


def _monotonicity(candidate_summary: dict[str, dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for family in ("inelastic", "momentum-kick"):
        members = sorted(
            (
                (entry["severity"], name, entry)
                for name, entry in candidate_summary.items()
                if entry["family"] == family
            ),
            key=lambda item: item[0],
        )
        output[family] = {}
        for metric in VISUAL_ERROR_METRICS:
            values = [float(entry["mean_metrics"][metric]) for _, _, entry in members]
            comparisons = [
                right > left for left, right in zip(values, values[1:], strict=False)
            ]
            output[family][metric] = {
                "strict_pair_accuracy": float(np.mean(comparisons)),
                "values": values,
            }
    return output


def run_suite(config: SuiteConfig | None = None) -> dict[str, Any]:
    """Run the frozen v1 protocol and return JSON-serializable evidence."""

    config = config or SuiteConfig()
    config.validate()
    specs = candidate_specs()
    records: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []

    for case_index in range(config.cases):
        cfg = make_case(config.seed, case_index)
        oracle = simulate(cfg)
        validate_oracle(oracle, cfg)
        oracle_frames = render_trajectory(oracle, cfg, n_frames=config.frames)
        case_records: list[dict[str, Any]] = []

        for candidate_index, spec in enumerate(specs):
            candidate_seed = config.seed + case_index * 1009 + candidate_index
            prediction = spec.build(cfg, candidate_seed)
            prediction_frames = render_trajectory(
                prediction, cfg, n_frames=config.frames
            )
            measured = evaluate_trajectory(
                prediction,
                oracle,
                cfg,
                prediction_frames,
                oracle_frames,
            )
            case_records.append(
                {
                    "case_id": f"case-{case_index:03d}",
                    "candidate": spec.name,
                    "family": spec.family,
                    "severity": spec.severity,
                    "expected_violation": spec.expected_violation,
                    "physics_failed": float(_physics_failed(spec, measured)),
                    **measured,
                }
            )

        random_record = next(
            record for record in case_records if record["candidate"] == "random"
        )
        for record in case_records:
            for metric in VISUAL_ERROR_METRICS:
                denominator = max(float(random_record[metric]), 1e-12)
                ratio = float(record[metric]) / denominator
                record[f"ratio_to_random_{metric}"] = ratio
                visually_passed = ratio < config.visual_pass_ratio
                record[f"low_sensitivity_{metric}"] = float(
                    bool(record["physics_failed"]) and visually_passed
                )
                record[f"exact_miss_{metric}"] = float(
                    bool(record["physics_failed"])
                    and float(record[metric]) <= config.exact_miss_tolerance
                )
        records.extend(case_records)
        cases.append({"case_id": f"case-{case_index:03d}", **cfg.to_dict()})

    candidates = _candidate_summary(records)
    result = {
        "schema_version": "1.0",
        "protocol_id": PROTOCOL_ID,
        "config": asdict(config),
        "cases": cases,
        "records": records,
        "summary": {
            "candidate_count": len(specs),
            "record_count": len(records),
            "all_oracles_validated": True,
            "all_expected_violations_detected": all(
                entry["physics_detection_rate"] == 1.0
                for name, entry in candidates.items()
                if name != "correct"
            ),
            "candidates": candidates,
            "monotonicity": _monotonicity(candidates),
        },
    }
    return result
