"""Frozen R2 learned-dynamics experiment and evidence bundle."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import re
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from io import StringIO
from pathlib import Path
from typing import Any

import numpy as np

from .metrics import VISUAL_ERROR_METRICS, evaluate_trajectory
from .render import render_trajectory
from .world import WorldConfig, first_contact_index, initial_state, make_case, simulate

R2_PROTOCOL_ID = "physgauge-learned-dynamics-r2-v2"
R2_ARTIFACT_NAMES = (
    "split-manifest.json",
    "results.json",
    "metrics.csv",
    "report.md",
)

_STATE_THRESHOLDS = {
    "position_rmse": 0.05,
    "velocity_rmse": 0.05,
    "energy_drift": 1e-4,
    "momentum_drift": 1e-4,
    "collision_event_error": 0.5,
    "kinematic_residual": 0.05,
}

_ACROSS_SEED_METRICS = (
    "state_failure_rate",
    "partial_error_rate",
    "collision_event_accuracy",
    "median_position_rmse",
    "median_velocity_rmse",
)


@dataclass(frozen=True)
class R2Config:
    """Pre-registered R2 configuration; smaller values are allowed only for tests."""

    train_base_seed: int = 20260825
    validation_base_seed: int = 20260826
    test_base_seed: int = 20260827
    train_cases: int = 128
    validation_cases: int = 128
    test_cases: int = 256
    model_seeds: tuple[int, ...] = (11, 29, 47)
    frames: int = 48
    hidden_width: int = 32
    batch_size: int = 256
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    beta1: float = 0.9
    beta2: float = 0.999
    epsilon: float = 1e-8
    max_epochs: int = 200
    patience: int = 20
    minimum_improvement: float = 1e-6
    visual_pass_ratio: float = 0.25
    exact_miss_tolerance: float = 1e-10
    collision_accuracy_minimum: float = 0.75
    partial_error_threshold: float = 0.02
    target_error_rate_minimum: float = 0.10
    target_error_rate_maximum: float = 0.70
    disagreement_rate_minimum: float = 0.05

    def validate(self) -> None:
        if min(self.train_cases, self.validation_cases, self.test_cases) < 2:
            raise ValueError("each R2 split must contain at least two cases")
        if not self.model_seeds or len(set(self.model_seeds)) != len(self.model_seeds):
            raise ValueError("model seeds must be non-empty and unique")
        if self.frames < 8 or self.hidden_width < 2 or self.batch_size < 2:
            raise ValueError("R2 frame, hidden-width, or batch-size setting is too small")
        if self.max_epochs < 1 or self.patience < 1:
            raise ValueError("R2 epochs and patience must be positive")
        if not 0.0 < self.target_error_rate_minimum <= self.target_error_rate_maximum < 1.0:
            raise ValueError("invalid R2 target error band")


@dataclass(frozen=True)
class TransitionDataset:
    inputs: np.ndarray
    targets: np.ndarray
    collision_window: np.ndarray


@dataclass(frozen=True)
class Normalization:
    input_mean: np.ndarray
    input_std: np.ndarray
    target_mean: np.ndarray
    target_std: np.ndarray


@dataclass(frozen=True)
class TrainedModel:
    seed: int
    params: dict[str, np.ndarray]
    normalization: Normalization
    epochs_trained: int
    best_validation_loss: float
    checkpoint_sha256: str
    runtime_seconds: float


def _canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def build_split_manifest(config: R2Config) -> dict[str, Any]:
    """Build the auditable split manifest before training."""

    config.validate()
    split_specs = {
        "train": (config.train_base_seed, config.train_cases),
        "validation": (config.validation_base_seed, config.validation_cases),
        "test": (config.test_base_seed, config.test_cases),
    }
    splits: dict[str, Any] = {}
    seen: set[tuple[int, int]] = set()
    for split_name, (base_seed, count) in split_specs.items():
        cases = []
        for case_index in range(count):
            identifier = (base_seed, case_index)
            if identifier in seen:
                raise ValueError(f"R2 split leakage at {identifier}")
            seen.add(identifier)
            cfg = make_case(base_seed, case_index)
            cases.append(
                {
                    "case_id": f"{split_name}-{case_index:04d}",
                    "base_seed": base_seed,
                    "case_index": case_index,
                    "world": cfg.to_dict(),
                }
            )
        splits[split_name] = {"base_seed": base_seed, "count": count, "cases": cases}
    return {"schema_version": "1.0", "protocol_id": R2_PROTOCOL_ID, "splits": splits}


def build_transition_dataset(base_seed: int, cases: int) -> TransitionDataset:
    """Create one-step state-delta supervision with a fixed contact window."""

    inputs: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    collision_windows: list[np.ndarray] = []
    for case_index in range(cases):
        cfg = make_case(base_seed, case_index)
        trajectory = simulate(cfg)
        contact = first_contact_index(trajectory, cfg)
        case_inputs = np.column_stack(
            (
                trajectory[:-1],
                np.full(len(trajectory) - 1, cfg.radius, dtype=np.float64),
            )
        )
        transition_end = np.arange(1, len(trajectory))
        inputs.append(case_inputs)
        targets.append(np.diff(trajectory, axis=0))
        collision_windows.append(np.abs(transition_end - contact) <= 2)
    return TransitionDataset(
        inputs=np.concatenate(inputs).astype(np.float32),
        targets=np.concatenate(targets).astype(np.float32),
        collision_window=np.concatenate(collision_windows),
    )


def _safe_std(values: np.ndarray) -> np.ndarray:
    standard_deviation = values.std(axis=0).astype(np.float32)
    return np.where(standard_deviation > 1e-12, standard_deviation, 1.0).astype(np.float32)


def _normalization(dataset: TransitionDataset) -> Normalization:
    return Normalization(
        input_mean=dataset.inputs.mean(axis=0).astype(np.float32),
        input_std=_safe_std(dataset.inputs),
        target_mean=dataset.targets.mean(axis=0).astype(np.float32),
        target_std=_safe_std(dataset.targets),
    )


def _silu(value: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    sigmoid = 1.0 / (1.0 + np.exp(-np.clip(value, -30.0, 30.0)))
    return value * sigmoid, sigmoid


def _initialize_params(seed: int, hidden_width: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)

    def weight(fan_in: int, fan_out: int) -> np.ndarray:
        limit = math.sqrt(6.0 / (fan_in + fan_out))
        return rng.uniform(-limit, limit, (fan_in, fan_out)).astype(np.float32)

    return {
        "w1": weight(9, hidden_width),
        "b1": np.zeros(hidden_width, dtype=np.float32),
        "w2": weight(hidden_width, hidden_width),
        "b2": np.zeros(hidden_width, dtype=np.float32),
        "w3": weight(hidden_width, 8),
        "b3": np.zeros(8, dtype=np.float32),
    }


def _forward(
    params: dict[str, np.ndarray], inputs: np.ndarray
) -> tuple[np.ndarray, tuple[np.ndarray, ...]]:
    z1 = inputs @ params["w1"] + params["b1"]
    a1, sigmoid1 = _silu(z1)
    z2 = a1 @ params["w2"] + params["b2"]
    a2, sigmoid2 = _silu(z2)
    output = a2 @ params["w3"] + params["b3"]
    return output, (inputs, z1, sigmoid1, a1, z2, sigmoid2, a2)


def _loss_and_gradients(
    params: dict[str, np.ndarray], inputs: np.ndarray, targets: np.ndarray
) -> tuple[float, dict[str, np.ndarray]]:
    prediction, cache = _forward(params, inputs)
    error = prediction - targets
    loss = float(np.mean(error**2))
    derivative = (2.0 / error.size) * error
    batch_inputs, z1, sigmoid1, a1, z2, sigmoid2, a2 = cache
    gradients: dict[str, np.ndarray] = {}
    gradients["w3"] = a2.T @ derivative
    gradients["b3"] = derivative.sum(axis=0)
    derivative_a2 = derivative @ params["w3"].T
    derivative_z2 = derivative_a2 * sigmoid2 * (1.0 + z2 * (1.0 - sigmoid2))
    gradients["w2"] = a1.T @ derivative_z2
    gradients["b2"] = derivative_z2.sum(axis=0)
    derivative_a1 = derivative_z2 @ params["w2"].T
    derivative_z1 = derivative_a1 * sigmoid1 * (1.0 + z1 * (1.0 - sigmoid1))
    gradients["w1"] = batch_inputs.T @ derivative_z1
    gradients["b1"] = derivative_z1.sum(axis=0)
    return loss, {name: value.astype(np.float32) for name, value in gradients.items()}


def _weighted_validation_loss(
    params: dict[str, np.ndarray], inputs: np.ndarray, targets: np.ndarray, mask: np.ndarray
) -> float:
    prediction, _ = _forward(params, inputs)
    per_sample = np.mean((prediction - targets) ** 2, axis=1)
    return float(0.5 * per_sample[mask].mean() + 0.5 * per_sample[~mask].mean())


def _checkpoint_hash(params: dict[str, np.ndarray], normalization: Normalization) -> str:
    digest = hashlib.sha256()
    arrays = {
        **params,
        "input_mean": normalization.input_mean,
        "input_std": normalization.input_std,
        "target_mean": normalization.target_mean,
        "target_std": normalization.target_std,
    }
    for name in sorted(arrays):
        value = np.asarray(arrays[name], dtype="<f4")
        digest.update(name.encode("utf-8"))
        digest.update(str(value.shape).encode("ascii"))
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def train_model(
    config: R2Config,
    seed: int,
    train: TransitionDataset,
    validation: TransitionDataset,
) -> TrainedModel:
    """Train the one frozen small MLP with balanced collision/free-motion epochs."""

    started_at = time.perf_counter()
    normalization = _normalization(train)
    train_inputs = (train.inputs - normalization.input_mean) / normalization.input_std
    train_targets = (train.targets - normalization.target_mean) / normalization.target_std
    validation_inputs = (
        validation.inputs - normalization.input_mean
    ) / normalization.input_std
    validation_targets = (
        validation.targets - normalization.target_mean
    ) / normalization.target_std
    train_inputs = train_inputs.astype(np.float32)
    train_targets = train_targets.astype(np.float32)
    validation_inputs = validation_inputs.astype(np.float32)
    validation_targets = validation_targets.astype(np.float32)

    collision_indices = np.flatnonzero(train.collision_window)
    free_indices = np.flatnonzero(~train.collision_window)
    if not len(collision_indices) or len(free_indices) < len(collision_indices):
        raise ValueError("R2 transition groups cannot form a balanced epoch")

    rng = np.random.default_rng(seed)
    params = _initialize_params(seed, config.hidden_width)
    first_moment = {name: np.zeros_like(value) for name, value in params.items()}
    second_moment = {name: np.zeros_like(value) for name, value in params.items()}
    best_params = {name: value.copy() for name, value in params.items()}
    best_loss = math.inf
    stale_epochs = 0
    update_step = 0
    epochs_trained = 0

    for epoch in range(1, config.max_epochs + 1):
        selected_free = rng.choice(free_indices, size=len(collision_indices), replace=False)
        selected = np.concatenate((collision_indices, selected_free))
        rng.shuffle(selected)
        for start in range(0, len(selected), config.batch_size):
            batch = selected[start : start + config.batch_size]
            _, gradients = _loss_and_gradients(
                params, train_inputs[batch], train_targets[batch]
            )
            update_step += 1
            for name, parameter in params.items():
                gradient = gradients[name]
                first_moment[name] = (
                    config.beta1 * first_moment[name] + (1.0 - config.beta1) * gradient
                )
                second_moment[name] = (
                    config.beta2 * second_moment[name]
                    + (1.0 - config.beta2) * gradient**2
                )
                corrected_first = first_moment[name] / (1.0 - config.beta1**update_step)
                corrected_second = second_moment[name] / (1.0 - config.beta2**update_step)
                parameter -= config.learning_rate * (
                    corrected_first / (np.sqrt(corrected_second) + config.epsilon)
                    + config.weight_decay * parameter
                )

        validation_loss = _weighted_validation_loss(
            params,
            validation_inputs,
            validation_targets,
            validation.collision_window,
        )
        epochs_trained = epoch
        if validation_loss < best_loss - config.minimum_improvement:
            best_loss = validation_loss
            best_params = {name: value.copy() for name, value in params.items()}
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= config.patience:
                break

    return TrainedModel(
        seed=seed,
        params=best_params,
        normalization=normalization,
        epochs_trained=epochs_trained,
        best_validation_loss=float(best_loss),
        checkpoint_sha256=_checkpoint_hash(best_params, normalization),
        runtime_seconds=time.perf_counter() - started_at,
    )


def rollout_model(model: TrainedModel, cfg: WorldConfig) -> np.ndarray:
    """Autoregress from the exact initial state without physical post-processing."""

    trajectory = np.empty((cfg.n_steps, 8), dtype=np.float64)
    trajectory[0] = initial_state(cfg)
    for index in range(1, cfg.n_steps):
        model_input = np.array([*trajectory[index - 1], cfg.radius], dtype=np.float32)
        normalized_input = (
            model_input - model.normalization.input_mean
        ) / model.normalization.input_std
        normalized_delta, _ = _forward(model.params, normalized_input[None, :])
        delta = (
            normalized_delta[0] * model.normalization.target_std
            + model.normalization.target_mean
        )
        trajectory[index] = trajectory[index - 1] + delta.astype(np.float64)
        if not np.isfinite(trajectory[index]).all():
            raise ValueError(f"non-finite R2 rollout for seed {model.seed} at step {index}")
    return trajectory


def _persistence(oracle: np.ndarray) -> np.ndarray:
    return np.repeat(oracle[:1], len(oracle), axis=0)


def _linear_extrapolation(cfg: WorldConfig) -> np.ndarray:
    trajectory = np.empty((cfg.n_steps, 8), dtype=np.float64)
    trajectory[0] = initial_state(cfg)
    for index in range(1, cfg.n_steps):
        state = trajectory[index - 1].copy()
        state[0:2] += state[2:4] * cfg.dt
        state[4:6] += state[6:8] * cfg.dt
        trajectory[index] = state
    return trajectory


def _random_trajectory(cfg: WorldConfig, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    trajectory = np.empty((cfg.n_steps, 8), dtype=np.float64)
    for index in range(cfg.n_steps):
        state = initial_state(cfg)
        state[[0, 1, 4, 5]] = rng.uniform(
            [cfg.radius] * 4,
            [cfg.width - cfg.radius, cfg.height - cfg.radius] * 2,
        )
        state[[2, 3, 6, 7]] = rng.uniform(-1.0, 1.0, 4)
        trajectory[index] = state
    return trajectory


def _post_contact_position_rmse(
    prediction: np.ndarray, oracle: np.ndarray, cfg: WorldConfig
) -> float:
    contact = first_contact_index(oracle, cfg)
    delta = prediction[contact:, [0, 1, 4, 5]] - oracle[contact:, [0, 1, 4, 5]]
    return float(np.sqrt(np.mean(delta**2)))


def _evaluate_prediction(
    *,
    candidate: str,
    model_seed: int | None,
    case_index: int,
    config: R2Config,
    cfg: WorldConfig,
    prediction: np.ndarray,
    oracle: np.ndarray,
    oracle_frames: np.ndarray,
    random_metrics: dict[str, float],
) -> dict[str, Any]:
    frames = (
        oracle_frames
        if candidate == "analytic-oracle"
        else render_trajectory(prediction, cfg, n_frames=config.frames)
    )
    measured = evaluate_trajectory(prediction, oracle, cfg, frames, oracle_frames)
    failures = {
        name: bool(measured[name] > threshold)
        for name, threshold in _STATE_THRESHOLDS.items()
    }
    state_failure = any(failures.values())
    post_contact = _post_contact_position_rmse(prediction, oracle, cfg)
    record: dict[str, Any] = {
        "case_id": f"test-{case_index:04d}",
        "case_index": case_index,
        "candidate": candidate,
        "model_seed": model_seed,
        "state_failure": state_failure,
        "post_contact_position_rmse": post_contact,
        "partial_error": bool(post_contact > config.partial_error_threshold),
        **{f"failed_{name}": failed for name, failed in failures.items()},
        **measured,
    }
    for metric in VISUAL_ERROR_METRICS:
        ratio = float(measured[metric]) / max(float(random_metrics[metric]), 1e-12)
        record[f"ratio_to_random_{metric}"] = ratio
        record[f"disagreement_{metric}"] = bool(
            state_failure and ratio < config.visual_pass_ratio
        )
        record[f"exact_miss_{metric}"] = bool(
            state_failure and float(measured[metric]) <= config.exact_miss_tolerance
        )
    return record


def _candidate_summary(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for candidate in sorted({str(record["candidate"]) for record in records}):
        selected = [record for record in records if record["candidate"] == candidate]
        proportions: dict[str, list[bool]] = {
            "state_failure": [bool(row["state_failure"]) for row in selected],
            "partial_error": [bool(row["partial_error"]) for row in selected],
            "collision_event_accuracy": [
                bool(row["collision_event_error"] <= 0.5) for row in selected
            ],
        }
        for metric in VISUAL_ERROR_METRICS:
            proportions[f"disagreement_{metric}"] = [
                bool(row[f"disagreement_{metric}"]) for row in selected
            ]
            proportions[f"exact_miss_{metric}"] = [
                bool(row[f"exact_miss_{metric}"]) for row in selected
            ]
        output[candidate] = {
            "cases": len(selected),
            "model_seed": selected[0]["model_seed"],
            "state_failure_rate": float(np.mean([row["state_failure"] for row in selected])),
            "partial_error_rate": float(np.mean([row["partial_error"] for row in selected])),
            "collision_event_accuracy": 1.0
            - float(np.mean([row["collision_event_error"] for row in selected])),
            "median_position_rmse": float(
                np.median([row["position_rmse"] for row in selected])
            ),
            "median_velocity_rmse": float(
                np.median([row["velocity_rmse"] for row in selected])
            ),
            "p95_position_rmse": float(
                np.quantile([row["position_rmse"] for row in selected], 0.95)
            ),
            "p95_velocity_rmse": float(
                np.quantile([row["velocity_rmse"] for row in selected], 0.95)
            ),
            "max_initial_condition_error": float(
                np.max([row["initial_condition_error"] for row in selected])
            ),
            "disagreement_rate": {
                metric: float(np.mean([row[f"disagreement_{metric}"] for row in selected]))
                for metric in VISUAL_ERROR_METRICS
            },
            "exact_miss_rate": {
                metric: float(np.mean([row[f"exact_miss_{metric}"] for row in selected]))
                for metric in VISUAL_ERROR_METRICS
            },
            "proportion_intervals_95": {
                name: _wilson_interval(sum(values), len(values))
                for name, values in proportions.items()
            },
        }
    return output


def _wilson_interval(successes: int, total: int) -> dict[str, float | int]:
    if total < 1 or not 0 <= successes <= total:
        raise ValueError("invalid inputs for Wilson interval")
    z = 1.959963984540054
    estimate = successes / total
    denominator = 1.0 + z**2 / total
    center = (estimate + z**2 / (2.0 * total)) / denominator
    margin = z / denominator * math.sqrt(
        estimate * (1.0 - estimate) / total + z**2 / (4.0 * total**2)
    )
    return {
        "successes": successes,
        "total": total,
        "estimate": estimate,
        "low": max(0.0, center - margin),
        "high": min(1.0, center + margin),
    }


def _mean_std(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(array.mean()),
        "standard_deviation": float(array.std(ddof=1)) if len(array) > 1 else 0.0,
    }


def _across_seed_summary(
    config: R2Config, candidates: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    learned = [candidates[f"learned-seed-{seed}"] for seed in config.model_seeds]
    return {
        "seed_count": len(learned),
        "metrics": {
            name: _mean_std([float(entry[name]) for entry in learned])
            for name in _ACROSS_SEED_METRICS
        },
        "disagreement_rate": {
            metric: _mean_std(
                [float(entry["disagreement_rate"][metric]) for entry in learned]
            )
            for metric in VISUAL_ERROR_METRICS
        },
    }


def _execution_environment() -> dict[str, str]:
    return {
        "implementation": "NumPy manual MLP and AdamW",
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "platform": platform.platform(),
        "machine": platform.machine() or "unknown",
        "processor": platform.processor() or "unknown",
        "device": "CPU",
        "accelerator": "none",
    }


def _decision(config: R2Config, candidates: dict[str, dict[str, Any]]) -> dict[str, Any]:
    required_seeds = math.ceil(2 * len(config.model_seeds) / 3)
    linear = candidates["linear-extrapolation"]
    seed_assessments: dict[str, Any] = {}
    for seed in config.model_seeds:
        name = f"learned-seed-{seed}"
        summary = candidates[name]
        learned_collision = bool(
            summary["median_position_rmse"] < linear["median_position_rmse"]
            and summary["median_velocity_rmse"] < linear["median_velocity_rmse"]
            and summary["collision_event_accuracy"] >= config.collision_accuracy_minimum
        )
        error_rate = float(summary["partial_error_rate"])
        if not learned_collision or error_rate > config.target_error_rate_maximum:
            classification = "too-weak"
        elif error_rate < config.target_error_rate_minimum:
            classification = "too-strong"
        else:
            classification = "target-band"
        seed_assessments[str(seed)] = {
            "learned_collision": learned_collision,
            "partial_error_rate": error_rate,
            "classification": classification,
        }

    counts = {
        label: sum(
            assessment["classification"] == label
            for assessment in seed_assessments.values()
        )
        for label in ("too-weak", "too-strong", "target-band")
    }
    consensus = next(
        (label for label, count in counts.items() if count >= required_seeds),
        "seed-unstable",
    )
    supporting_metrics = [
        metric
        for metric in VISUAL_ERROR_METRICS
        if sum(
            candidates[f"learned-seed-{seed}"]["disagreement_rate"][metric]
            >= config.disagreement_rate_minimum
            for seed in config.model_seeds
        )
        >= required_seeds
    ]

    oracle = candidates["analytic-oracle"]
    weak_baselines = [candidates["persistence"], candidates["linear-extrapolation"]]
    dry_run_valid = bool(
        oracle["state_failure_rate"] == 0.0
        and all(
            entry["state_failure_rate"] == 1.0
            and any(
                rate >= config.disagreement_rate_minimum
                for rate in entry["disagreement_rate"].values()
            )
            for entry in weak_baselines
        )
    )
    initial_conditions_valid = all(
        candidates[f"learned-seed-{seed}"]["max_initial_condition_error"] <= 1e-6
        for seed in config.model_seeds
    )
    experiment_valid = dry_run_valid and initial_conditions_valid
    if not experiment_valid:
        outcome = "invalid-experiment"
    elif consensus in {"too-weak", "seed-unstable"}:
        outcome = "inconclusive-model"
    elif consensus == "too-strong":
        outcome = "expand"
    elif supporting_metrics:
        outcome = "continue-r3"
    else:
        outcome = "stop-current-line"
    return {
        "experiment_valid": experiment_valid,
        "dry_run_valid": dry_run_valid,
        "initial_conditions_valid": initial_conditions_valid,
        "required_seed_count": required_seeds,
        "seed_assessments": seed_assessments,
        "classification_counts": counts,
        "consensus_classification": consensus,
        "supporting_visual_metrics": supporting_metrics,
        "outcome": outcome,
    }


def run_r2_experiment(
    config: R2Config | None = None,
    *,
    progress: Callable[[str], None] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Train the frozen models, run all baselines, and return auditable evidence."""

    started_at = time.perf_counter()
    config = config or R2Config()
    config.validate()
    notify = progress or (lambda _message: None)
    split_manifest = build_split_manifest(config)
    notify("building train and validation transitions")
    train = build_transition_dataset(config.train_base_seed, config.train_cases)
    validation = build_transition_dataset(
        config.validation_base_seed, config.validation_cases
    )
    models: list[TrainedModel] = []
    for seed in config.model_seeds:
        notify(f"training model seed={seed}")
        model = train_model(config, seed, train, validation)
        models.append(model)
        notify(
            f"trained seed={seed} epochs={model.epochs_trained} "
            f"validation={model.best_validation_loss:.6g}"
        )

    notify("evaluating autoregressive test rollouts and baselines")
    records: list[dict[str, Any]] = []
    for case_index in range(config.test_cases):
        cfg = make_case(config.test_base_seed, case_index)
        oracle = simulate(cfg)
        oracle_frames = render_trajectory(oracle, cfg, n_frames=config.frames)
        random_trajectory = _random_trajectory(
            cfg, config.test_base_seed + case_index * 1009 + 9
        )
        random_frames = render_trajectory(
            random_trajectory, cfg, n_frames=config.frames
        )
        random_metrics = evaluate_trajectory(
            random_trajectory, oracle, cfg, random_frames, oracle_frames
        )
        predictions: list[tuple[str, int | None, np.ndarray]] = [
            ("analytic-oracle", None, oracle),
            ("persistence", None, _persistence(oracle)),
            ("linear-extrapolation", None, _linear_extrapolation(cfg)),
        ]
        predictions.extend(
            (f"learned-seed-{model.seed}", model.seed, rollout_model(model, cfg))
            for model in models
        )
        for candidate, model_seed, prediction in predictions:
            records.append(
                _evaluate_prediction(
                    candidate=candidate,
                    model_seed=model_seed,
                    case_index=case_index,
                    config=config,
                    cfg=cfg,
                    prediction=prediction,
                    oracle=oracle,
                    oracle_frames=oracle_frames,
                    random_metrics=random_metrics,
                )
            )
        if (case_index + 1) % max(1, config.test_cases // 4) == 0:
            notify(f"evaluated {case_index + 1}/{config.test_cases} test cases")

    candidates = _candidate_summary(records)
    decision = _decision(config, candidates)
    result = {
        "schema_version": "1.0",
        "protocol_id": R2_PROTOCOL_ID,
        "config": asdict(config),
        "training": [
            {
                "seed": model.seed,
                "epochs_trained": model.epochs_trained,
                "best_validation_loss": model.best_validation_loss,
                "checkpoint_sha256": model.checkpoint_sha256,
                "runtime_seconds": model.runtime_seconds,
            }
            for model in models
        ],
        "records": records,
        "summary": {
            "candidates": candidates,
            "across_model_seeds": _across_seed_summary(config, candidates),
            "decision": decision,
        },
        "execution": {
            "environment": _execution_environment(),
            "total_runtime_seconds": time.perf_counter() - started_at,
        },
    }
    notify(f"decision={decision['outcome']}")
    return result, split_manifest


def _metrics_csv(result: dict[str, Any]) -> str:
    records = result["records"]
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=sorted(records[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def _report_markdown(result: dict[str, Any]) -> str:
    config = result["config"]
    summary = result["summary"]
    decision = summary["decision"]
    model_seeds = ", ".join(str(seed) for seed in config["model_seeds"])
    lines = [
        "# PhysGauge R2 learned-dynamics evidence",
        "",
        f"Protocol: `{result['protocol_id']}` · train/validation/test: "
        f"{config['train_cases']}/{config['validation_cases']}/{config['test_cases']} · "
        f"model seeds: `[{model_seeds}]`.",
        "",
        "## Training",
        "",
        "| seed | epochs | best validation loss | runtime (s) | checkpoint SHA-256 |",
        "|---:|---:|---:|---:|---|",
    ]
    for training in result["training"]:
        lines.append(
            f"| {training['seed']} | {training['epochs_trained']} | "
            f"{training['best_validation_loss']:.6g} | "
            f"{training['runtime_seconds']:.3f} | "
            f"`{training['checkpoint_sha256']}` |"
        )
    environment = result["execution"]["environment"]
    lines += [
        "",
        f"Execution: Python {environment['python']}, NumPy {environment['numpy']}, "
        f"{environment['device']} only, {result['execution']['total_runtime_seconds']:.3f} s total.",
        "",
        "## Test summary",
        "",
        "| candidate | state failure | partial error | collision accuracy | median position "
        "RMSE | median velocity RMSE | MSE disagreement | SSIM disagreement | Pixel Fréchet "
        "disagreement | temporal-gradient disagreement |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for candidate in sorted(summary["candidates"]):
        entry = summary["candidates"][candidate]
        rates = entry["disagreement_rate"]
        lines.append(
            f"| `{candidate}` | {entry['state_failure_rate']:.1%} | "
            f"{entry['partial_error_rate']:.1%} | "
            f"{entry['collision_event_accuracy']:.1%} | "
            f"{entry['median_position_rmse']:.6g} | "
            f"{entry['median_velocity_rmse']:.6g} | "
            f"{rates['mse']:.1%} | {rates['ssim_error']:.1%} | "
            f"{rates['pixel_frechet']:.1%} | {rates['temporal_gradient_mse']:.1%} |"
        )
    across = summary["across_model_seeds"]
    lines += [
        "",
        "## Across-seed aggregate",
        "",
        "Each entry is the mean ± sample standard deviation across the registered model seeds.",
        "",
        "| metric | mean ± standard deviation |",
        "|---|---:|",
    ]
    for name in _ACROSS_SEED_METRICS:
        statistic = across["metrics"][name]
        lines.append(
            f"| `{name}` | {statistic['mean']:.6g} ± "
            f"{statistic['standard_deviation']:.6g} |"
        )
    for metric in VISUAL_ERROR_METRICS:
        statistic = across["disagreement_rate"][metric]
        lines.append(
            f"| `disagreement_{metric}` | {statistic['mean']:.1%} ± "
            f"{statistic['standard_deviation']:.1%} |"
        )
    lines += [
        "",
        "All case-level proportions and their 95% Wilson intervals are stored under "
        "`summary.candidates.*.proportion_intervals_95` in `results.json`.",
    ]
    lines += [
        "",
        "## Pre-registered decision",
        "",
        f"- Experiment valid: **{decision['experiment_valid']}**",
        f"- Consensus model class: **`{decision['consensus_classification']}`**",
        f"- Supporting visual metrics: **{decision['supporting_visual_metrics']}**",
        f"- Outcome: **`{decision['outcome']}`**",
        "",
    ]
    if decision["outcome"] == "inconclusive-model":
        lines += [
            "The registered model-capability gate failed before the visual-disagreement gate. "
            "The listed supporting metrics therefore do not constitute learned-model evidence.",
            "",
        ]
    lines += [
        "This result applies only to the frozen small-data/small-capacity predictor and IID "
        "two-disc test split. It is not evidence about video generators, OOD generalization, or "
        "all visual metrics.",
        "",
    ]
    return "\n".join(lines)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_r2_bundle(
    result: dict[str, Any], split_manifest: dict[str, Any], output_dir: str | Path
) -> dict[str, Path]:
    """Write the R2 evidence and its exact artifact manifest."""

    if result.get("protocol_id") != R2_PROTOCOL_ID:
        raise ValueError("unsupported R2 result protocol")
    if split_manifest.get("protocol_id") != R2_PROTOCOL_ID:
        raise ValueError("unsupported R2 split protocol")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    payloads = {
        "split-manifest.json": _canonical_json(split_manifest),
        "results.json": _canonical_json(result),
        "metrics.csv": _metrics_csv(result),
        "report.md": _report_markdown(result),
    }
    paths: dict[str, Path] = {}
    for name, payload in payloads.items():
        path = destination / name
        path.write_text(payload, encoding="utf-8", newline="\n")
        paths[name] = path
    manifest = {
        "schema_version": "1.0",
        "protocol_id": R2_PROTOCOL_ID,
        "artifacts": {name: _sha256(path) for name, path in paths.items()},
    }
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(_canonical_json(manifest), encoding="utf-8", newline="\n")
    paths["manifest.json"] = manifest_path
    return paths


def _validate_result_structure(config: R2Config, result: dict[str, Any]) -> None:
    training = result.get("training")
    if not isinstance(training, list) or len(training) != len(config.model_seeds):
        raise ValueError("R2 training metadata does not match model seeds")
    if [entry.get("seed") for entry in training if isinstance(entry, dict)] != list(
        config.model_seeds
    ):
        raise ValueError("R2 training seed order mismatch")
    for entry in training:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("epochs_trained"), int)
            or not 1 <= entry["epochs_trained"] <= config.max_epochs
            or not math.isfinite(float(entry.get("best_validation_loss", math.nan)))
            or not math.isfinite(float(entry.get("runtime_seconds", math.nan)))
            or float(entry["runtime_seconds"]) < 0.0
            or not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("checkpoint_sha256", "")))
        ):
            raise ValueError("invalid R2 training metadata")

    execution = result.get("execution")
    if not isinstance(execution, dict) or not isinstance(execution.get("environment"), dict):
        raise ValueError("missing R2 execution metadata")
    runtime = execution.get("total_runtime_seconds")
    if not isinstance(runtime, int | float) or not math.isfinite(runtime) or runtime < 0.0:
        raise ValueError("invalid R2 execution runtime")

    records = result.get("records")
    if not isinstance(records, list):
        raise ValueError("missing R2 case records")
    expected_candidates = {
        "analytic-oracle": None,
        "persistence": None,
        "linear-extrapolation": None,
        **{f"learned-seed-{seed}": seed for seed in config.model_seeds},
    }
    expected_pairs = {
        (case_index, candidate)
        for case_index in range(config.test_cases)
        for candidate in expected_candidates
    }
    actual_pairs: set[tuple[int, str]] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("invalid R2 case record")
        case_index = record.get("case_index")
        candidate = record.get("candidate")
        if (
            not isinstance(case_index, int)
            or not isinstance(candidate, str)
            or record.get("case_id") != f"test-{case_index:04d}"
            or candidate not in expected_candidates
            or record.get("model_seed") != expected_candidates[candidate]
        ):
            raise ValueError("invalid R2 case identity")
        pair = (case_index, candidate)
        if pair in actual_pairs:
            raise ValueError("duplicate R2 case record")
        actual_pairs.add(pair)
    if actual_pairs != expected_pairs:
        raise ValueError("R2 case record set is incomplete")


def verify_r2_bundle(
    bundle_dir: str | Path, *, expected_config: R2Config | None = None
) -> dict[str, Any]:
    """Verify R2 artifact hashes, protocol IDs, and the registered decision."""

    directory = Path(bundle_dir)
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"missing R2 manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0":
        raise ValueError("unsupported R2 manifest schema")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(R2_ARTIFACT_NAMES):
        raise ValueError("R2 manifest artifact set mismatch")
    expected_files = {*R2_ARTIFACT_NAMES, "manifest.json"}
    actual_files = {path.name for path in directory.iterdir() if path.is_file()}
    if actual_files != expected_files:
        raise ValueError("R2 bundle file set mismatch")
    for name in R2_ARTIFACT_NAMES:
        if _sha256(directory / name) != artifacts[name]:
            raise ValueError(f"R2 hash mismatch for {name}")
    result = json.loads((directory / "results.json").read_text(encoding="utf-8"))
    split_manifest = json.loads(
        (directory / "split-manifest.json").read_text(encoding="utf-8")
    )
    if (
        manifest.get("protocol_id") != R2_PROTOCOL_ID
        or result.get("protocol_id") != R2_PROTOCOL_ID
        or split_manifest.get("protocol_id") != R2_PROTOCOL_ID
    ):
        raise ValueError("R2 protocol mismatch")
    if (
        result.get("schema_version") != "1.0"
        or split_manifest.get("schema_version") != "1.0"
    ):
        raise ValueError("unsupported R2 result schema")
    config_payload = result.get("config")
    if not isinstance(config_payload, dict):
        raise ValueError("missing R2 configuration")
    reproduced_config = R2Config(
        **{
            **config_payload,
            "model_seeds": tuple(config_payload.get("model_seeds", ())),
        }
    )
    reproduced_config.validate()
    if expected_config is not None and _canonical_json(
        asdict(reproduced_config)
    ) != _canonical_json(asdict(expected_config)):
        raise ValueError("R2 configuration does not match the frozen official protocol")
    if _canonical_json(split_manifest) != _canonical_json(
        build_split_manifest(reproduced_config)
    ):
        raise ValueError("R2 split manifest does not match the frozen configuration")
    _validate_result_structure(reproduced_config, result)
    records = result["records"]
    candidates = _candidate_summary(records)
    expected_summary = {
        "candidates": candidates,
        "across_model_seeds": _across_seed_summary(reproduced_config, candidates),
        "decision": _decision(reproduced_config, candidates),
    }
    if result.get("summary") != expected_summary:
        raise ValueError("R2 summary is inconsistent with case records")
    if (directory / "metrics.csv").read_text(encoding="utf-8") != _metrics_csv(result):
        raise ValueError("R2 CSV is inconsistent with case records")
    if (directory / "report.md").read_text(encoding="utf-8") != _report_markdown(result):
        raise ValueError("R2 report is inconsistent with results")
    if result.get("summary", {}).get("decision", {}).get("outcome") not in {
        "invalid-experiment",
        "inconclusive-model",
        "expand",
        "continue-r3",
        "stop-current-line",
    }:
        raise ValueError("invalid R2 decision outcome")
    return manifest
