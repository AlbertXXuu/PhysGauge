"""Deterministic antialiased rendering for state trajectories."""

from __future__ import annotations

import numpy as np

from .world import WorldConfig


def render_frame(
    state: np.ndarray,
    cfg: WorldConfig,
    size: tuple[int, int] = (96, 96),
) -> np.ndarray:
    """Render two discs as a grayscale float image in [0, 1]."""

    width, height = size
    if width < 16 or height < 16:
        raise ValueError("render size must be at least 16x16")
    image = np.ones((height, width), dtype=np.float32)
    yy, xx = np.mgrid[0:height, 0:width]
    for x, y in ((state[0], state[1]), (state[4], state[5])):
        cx, cy = float(x) * width, float(y) * height
        dx = (xx - cx) / width
        dy = (yy - cy) / height
        distance = np.sqrt(dx**2 + dy**2)
        pixel_radius = 1.0 / min(width, height)
        coverage = np.clip((cfg.radius - distance) / pixel_radius + 0.5, 0.0, 1.0)
        image *= 1.0 - coverage
    return image


def render_trajectory(
    trajectory: np.ndarray,
    cfg: WorldConfig,
    *,
    n_frames: int = 48,
    size: tuple[int, int] = (96, 96),
) -> np.ndarray:
    if n_frames < 2:
        raise ValueError("n_frames must be at least 2")
    indices = np.linspace(0, len(trajectory) - 1, n_frames).round().astype(int)
    return np.stack([render_frame(trajectory[index], cfg, size) for index in indices])
