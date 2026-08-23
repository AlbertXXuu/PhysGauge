"""Dependency-light visual, temporal, and state-grounded physics metrics."""

from __future__ import annotations

import numpy as np
from PIL import Image

from .world import WorldConfig, first_contact_index, total_energy, total_momentum

VISUAL_ERROR_METRICS = (
    "mse",
    "ssim_error",
    "pixel_frechet",
    "temporal_gradient_mse",
)


def _validate_pair(prediction: np.ndarray, oracle: np.ndarray) -> None:
    if prediction.shape != oracle.shape:
        raise ValueError("prediction and oracle must have the same shape")
    if prediction.ndim != 2 or prediction.shape[1] != 8:
        raise ValueError("trajectories must have shape (steps, 8)")
    if not np.isfinite(prediction).all() or not np.isfinite(oracle).all():
        raise ValueError("trajectories must contain only finite values")


def position_rmse(prediction: np.ndarray, oracle: np.ndarray) -> float:
    delta = prediction[:, [0, 1, 4, 5]] - oracle[:, [0, 1, 4, 5]]
    return float(np.sqrt(np.mean(delta**2)))


def velocity_rmse(prediction: np.ndarray, oracle: np.ndarray) -> float:
    delta = prediction[:, [2, 3, 6, 7]] - oracle[:, [2, 3, 6, 7]]
    return float(np.sqrt(np.mean(delta**2)))


def initial_condition_error(prediction: np.ndarray, oracle: np.ndarray) -> float:
    return float(np.sqrt(np.mean((prediction[0] - oracle[0]) ** 2)))


def energy_drift(trajectory: np.ndarray) -> float:
    initial = total_energy(trajectory[0])
    values = np.array([total_energy(state) for state in trajectory])
    return float(np.max(np.abs(values - initial)) / max(initial, 1e-12))


def momentum_drift(trajectory: np.ndarray) -> float:
    initial = total_momentum(trajectory[0])
    speed_scale = float(
        np.linalg.norm(trajectory[0, 2:4]) + np.linalg.norm(trajectory[0, 6:8])
    )
    values = np.array([total_momentum(state) for state in trajectory])
    return float(np.max(np.linalg.norm(values - initial, axis=1)) / max(speed_scale, 1e-12))


def collision_event_error(
    prediction: np.ndarray, oracle: np.ndarray, cfg: WorldConfig
) -> float:
    """Return one when the predicted relative normal velocity fails to separate."""

    contact = first_contact_index(oracle, cfg)
    if not 1 <= contact < len(oracle) - 1:
        return 1.0
    normal = oracle[contact, 4:6] - oracle[contact, 0:2]
    normal /= max(float(np.linalg.norm(normal)), 1e-12)
    oracle_after = float((oracle[contact + 1, 2:4] - oracle[contact + 1, 6:8]) @ normal)
    prediction_after = float(
        (prediction[contact + 1, 2:4] - prediction[contact + 1, 6:8]) @ normal
    )
    return float(np.signbit(oracle_after) != np.signbit(prediction_after))


def kinematic_residual(trajectory: np.ndarray, cfg: WorldConfig) -> float:
    positions = trajectory[:, [0, 1, 4, 5]]
    velocities = trajectory[:, [2, 3, 6, 7]]
    inferred = np.diff(positions, axis=0) / cfg.dt
    return float(np.sqrt(np.mean((inferred - velocities[:-1]) ** 2)))


def physics_metrics(
    prediction: np.ndarray, oracle: np.ndarray, cfg: WorldConfig
) -> dict[str, float]:
    _validate_pair(prediction, oracle)
    return {
        "position_rmse": position_rmse(prediction, oracle),
        "velocity_rmse": velocity_rmse(prediction, oracle),
        "initial_condition_error": initial_condition_error(prediction, oracle),
        "energy_drift": energy_drift(prediction),
        "momentum_drift": momentum_drift(prediction),
        "collision_event_error": collision_event_error(prediction, oracle, cfg),
        "kinematic_residual": kinematic_residual(prediction, cfg),
    }


def mse(prediction: np.ndarray, oracle: np.ndarray) -> float:
    return float(np.mean((prediction - oracle) ** 2))


def psnr(prediction: np.ndarray, oracle: np.ndarray) -> float:
    error = mse(prediction, oracle)
    return 120.0 if error <= 1e-12 else float(10.0 * np.log10(1.0 / error))


def ssim(prediction: np.ndarray, oracle: np.ndarray) -> float:
    """Mean global SSIM over frames, suitable for these controlled fixtures."""

    c1, c2 = 0.01**2, 0.03**2
    x = prediction.reshape(len(prediction), -1).astype(np.float64)
    y = oracle.reshape(len(oracle), -1).astype(np.float64)
    ux, uy = x.mean(axis=1), y.mean(axis=1)
    vx, vy = x.var(axis=1), y.var(axis=1)
    covariance = ((x - ux[:, None]) * (y - uy[:, None])).mean(axis=1)
    numerator = (2.0 * ux * uy + c1) * (2.0 * covariance + c2)
    denominator = (ux**2 + uy**2 + c1) * (vx + vy + c2)
    return float(np.mean(numerator / np.maximum(denominator, 1e-12)))


def _symmetric_sqrt(matrix: np.ndarray) -> np.ndarray:
    values, vectors = np.linalg.eigh(0.5 * (matrix + matrix.T))
    return (vectors * np.sqrt(np.clip(values, 0.0, None))) @ vectors.T


def _features(frames: np.ndarray, size: tuple[int, int] = (8, 4)) -> np.ndarray:
    width, height = size
    features = np.empty((len(frames), width * height), dtype=np.float64)
    for index, frame in enumerate(frames):
        image = Image.fromarray(np.uint8(np.clip(frame, 0.0, 1.0) * 255.0))
        resized = image.resize((width, height), Image.Resampling.BILINEAR)
        features[index] = np.asarray(resized, dtype=np.float64).ravel() / 255.0
    return features


def pixel_frechet(prediction: np.ndarray, oracle: np.ndarray) -> float:
    """Order-invariant Fréchet distance over tiny pixel features, not FID/FVD."""

    first, second = _features(prediction), _features(oracle)
    mu_first, mu_second = first.mean(axis=0), second.mean(axis=0)
    cov_first = np.cov(first, rowvar=False) + 1e-8 * np.eye(first.shape[1])
    cov_second = np.cov(second, rowvar=False) + 1e-8 * np.eye(second.shape[1])
    root_first = _symmetric_sqrt(cov_first)
    middle = root_first @ cov_second @ root_first
    trace_root = float(np.trace(_symmetric_sqrt(middle)))
    distance = float(
        np.sum((mu_first - mu_second) ** 2)
        + np.trace(cov_first)
        + np.trace(cov_second)
        - 2.0 * trace_root
    )
    return max(distance, 0.0)


def temporal_gradient_mse(prediction: np.ndarray, oracle: np.ndarray) -> float:
    return mse(np.diff(prediction, axis=0), np.diff(oracle, axis=0))


def visual_metrics(prediction: np.ndarray, oracle: np.ndarray) -> dict[str, float]:
    if prediction.shape != oracle.shape or prediction.ndim != 3:
        raise ValueError("frame arrays must have matching (frames, height, width) shapes")
    similarity = ssim(prediction, oracle)
    return {
        "mse": mse(prediction, oracle),
        "psnr": psnr(prediction, oracle),
        "ssim": similarity,
        "ssim_error": max(0.0, 1.0 - similarity),
        "pixel_frechet": pixel_frechet(prediction, oracle),
        "temporal_gradient_mse": temporal_gradient_mse(prediction, oracle),
    }


def evaluate_trajectory(
    prediction: np.ndarray,
    oracle: np.ndarray,
    cfg: WorldConfig,
    prediction_frames: np.ndarray,
    oracle_frames: np.ndarray,
) -> dict[str, float]:
    """Stable v1 API for scoring one state-grounded prediction."""

    return {
        **physics_metrics(prediction, oracle, cfg),
        **visual_metrics(prediction_frames, oracle_frames),
    }
