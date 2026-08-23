"""Deterministic two-disc collision worlds with state-level ground truth."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import cos, sin
from typing import Any

import numpy as np


@dataclass(frozen=True)
class WorldConfig:
    """Configuration for one equal-mass, elastic two-disc collision."""

    width: float = 1.0
    height: float = 1.0
    radius: float = 0.045
    dt: float = 0.001
    t_end: float = 0.22
    p1: tuple[float, float] = (0.38, 0.50)
    v1: tuple[float, float] = (0.80, 0.00)
    p2: tuple[float, float] = (0.62, 0.50)
    v2: tuple[float, float] = (-0.80, 0.00)

    @property
    def n_steps(self) -> int:
        return int(round(self.t_end / self.dt)) + 1

    def validate(self) -> None:
        if self.width <= 0 or self.height <= 0 or self.radius <= 0:
            raise ValueError("world dimensions and radius must be positive")
        if self.dt <= 0 or self.t_end <= 0:
            raise ValueError("dt and t_end must be positive")
        if 2 * self.radius >= min(self.width, self.height):
            raise ValueError("disc diameter must fit inside the world")
        for point in (self.p1, self.p2):
            if not (
                self.radius <= point[0] <= self.width - self.radius
                and self.radius <= point[1] <= self.height - self.radius
            ):
                raise ValueError("initial disc center lies outside the world")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_case(seed: int, index: int) -> WorldConfig:
    """Create a reproducible collision case that stays away from the walls."""

    if index < 0:
        raise ValueError("index must be non-negative")
    rng = np.random.default_rng(np.random.SeedSequence([seed, index]))
    angle = float(rng.uniform(0.0, 2.0 * np.pi))
    normal = np.array([cos(angle), sin(angle)], dtype=np.float64)
    tangent = np.array([-normal[1], normal[0]], dtype=np.float64)
    radius = float(rng.uniform(0.036, 0.050))
    separation = float(rng.uniform(0.22, 0.27))
    closing_speed = float(rng.uniform(0.62, 0.92))
    common_drift = float(rng.uniform(-0.08, 0.08)) * tangent
    center = np.array([0.5, 0.5], dtype=np.float64)

    p1 = center - 0.5 * separation * normal
    p2 = center + 0.5 * separation * normal
    v1 = common_drift + closing_speed * normal
    v2 = common_drift - closing_speed * normal
    contact_time = (separation - 2.0 * radius) / (2.0 * closing_speed)
    cfg = WorldConfig(
        radius=radius,
        t_end=float(contact_time + rng.uniform(0.10, 0.13)),
        p1=(float(p1[0]), float(p1[1])),
        v1=(float(v1[0]), float(v1[1])),
        p2=(float(p2[0]), float(p2[1])),
        v2=(float(v2[0]), float(v2[1])),
    )
    cfg.validate()
    return cfg


def initial_state(cfg: WorldConfig) -> np.ndarray:
    cfg.validate()
    return np.array([*cfg.p1, *cfg.v1, *cfg.p2, *cfg.v2], dtype=np.float64)


def total_energy(state: np.ndarray, mass: float = 1.0) -> float:
    return 0.5 * mass * (
        float(state[2:4] @ state[2:4]) + float(state[6:8] @ state[6:8])
    )


def total_momentum(state: np.ndarray, mass: float = 1.0) -> np.ndarray:
    return mass * (state[2:4] + state[6:8])


def step(
    state: np.ndarray,
    cfg: WorldConfig,
    *,
    restitution: float = 1.0,
    tangential_kick: float = 0.0,
    collide: bool = True,
) -> np.ndarray:
    """Advance one step; the default is the elastic oracle."""

    if not 0.0 <= restitution <= 1.0:
        raise ValueError("restitution must be in [0, 1]")
    s = np.asarray(state, dtype=np.float64).copy()
    if s.shape != (8,):
        raise ValueError("state must have shape (8,)")
    s[0:2] += s[2:4] * cfg.dt
    s[4:6] += s[6:8] * cfg.dt

    for offset in (0, 4):
        for axis, limit in ((0, cfg.width), (1, cfg.height)):
            position = offset + axis
            velocity = offset + 2 + axis
            lo, hi = cfg.radius, limit - cfg.radius
            if s[position] < lo:
                s[position] = 2.0 * lo - s[position]
                s[velocity] *= -1.0
            elif s[position] > hi:
                s[position] = 2.0 * hi - s[position]
                s[velocity] *= -1.0

    delta = s[4:6] - s[0:2]
    distance = float(np.linalg.norm(delta))
    if collide and 0.0 < distance < 2.0 * cfg.radius:
        normal = delta / distance
        relative_normal = float((s[2:4] - s[6:8]) @ normal)
        if relative_normal > 0.0:
            impulse = 0.5 * (1.0 + restitution) * relative_normal
            s[2:4] -= impulse * normal
            s[6:8] += impulse * normal
            if tangential_kick:
                tangent = np.array([-normal[1], normal[0]], dtype=np.float64)
                s[2:4] += tangential_kick * tangent
                s[6:8] += tangential_kick * tangent

        overlap = 2.0 * cfg.radius - distance
        s[0:2] -= 0.5 * overlap * normal
        s[4:6] += 0.5 * overlap * normal
    return s


def simulate(cfg: WorldConfig, **step_kwargs: float | bool) -> np.ndarray:
    state = initial_state(cfg)
    trajectory = np.empty((cfg.n_steps, 8), dtype=np.float64)
    trajectory[0] = state
    for index in range(1, cfg.n_steps):
        state = step(state, cfg, **step_kwargs)
        trajectory[index] = state
    return trajectory


def contact_mask(trajectory: np.ndarray, cfg: WorldConfig, eps: float = 1e-6) -> np.ndarray:
    distance = np.linalg.norm(trajectory[:, 4:6] - trajectory[:, 0:2], axis=1)
    return distance <= 2.0 * cfg.radius + eps


def first_contact_index(trajectory: np.ndarray, cfg: WorldConfig) -> int:
    mask = contact_mask(trajectory, cfg)
    hits = np.flatnonzero(mask)
    return int(hits[0]) if len(hits) else len(trajectory)


def validate_oracle(trajectory: np.ndarray, cfg: WorldConfig) -> None:
    """Raise if a generated oracle violates its analytical contract."""

    if trajectory.shape != (cfg.n_steps, 8):
        raise ValueError("oracle trajectory shape does not match the configuration")
    contact = first_contact_index(trajectory, cfg)
    if not 1 <= contact < cfg.n_steps - 1:
        raise ValueError("configured case does not contain an observable collision")
    energies = np.array([total_energy(state) for state in trajectory])
    momenta = np.array([total_momentum(state) for state in trajectory])
    if not np.allclose(energies, energies[0], rtol=1e-10, atol=1e-12):
        raise ValueError("oracle does not conserve energy")
    if not np.allclose(momenta, momenta[0], rtol=1e-10, atol=1e-12):
        raise ValueError("oracle does not conserve momentum")
