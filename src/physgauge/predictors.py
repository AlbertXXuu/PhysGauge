"""Controlled trajectory corruptions used to calibrate evaluation metrics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .world import WorldConfig, initial_state, simulate


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    family: str
    severity: float
    expected_violation: str
    build: Callable[[WorldConfig, int], np.ndarray]


def _correct(cfg: WorldConfig, seed: int) -> np.ndarray:
    del seed
    return simulate(cfg)


def _inelastic(restitution: float) -> Callable[[WorldConfig, int], np.ndarray]:
    def build(cfg: WorldConfig, seed: int) -> np.ndarray:
        del seed
        return simulate(cfg, restitution=restitution)

    return build


def _momentum_kick(kick: float) -> Callable[[WorldConfig, int], np.ndarray]:
    def build(cfg: WorldConfig, seed: int) -> np.ndarray:
        del seed
        return simulate(cfg, tangential_kick=kick)

    return build


def _collision_dropout(cfg: WorldConfig, seed: int) -> np.ndarray:
    del seed
    return simulate(cfg, collide=False)


def _time_reverse(cfg: WorldConfig, seed: int) -> np.ndarray:
    del seed
    return simulate(cfg)[::-1].copy()


def _random(cfg: WorldConfig, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    trajectory = np.empty((cfg.n_steps, 8), dtype=np.float64)
    for index in range(cfg.n_steps):
        state = initial_state(cfg)
        state[[0, 1, 4, 5]] = rng.uniform(
            [cfg.radius, cfg.radius, cfg.radius, cfg.radius],
            [
                cfg.width - cfg.radius,
                cfg.height - cfg.radius,
                cfg.width - cfg.radius,
                cfg.height - cfg.radius,
            ],
        )
        state[[2, 3, 6, 7]] = rng.uniform(-1.0, 1.0, 4)
        trajectory[index] = state
    return trajectory


def candidate_specs() -> tuple[CandidateSpec, ...]:
    """Return the frozen v1 calibration suite."""

    return (
        CandidateSpec("correct", "correct", 0.0, "none", _correct),
        CandidateSpec("inelastic-0.95", "inelastic", 0.05, "energy", _inelastic(0.95)),
        CandidateSpec("inelastic-0.80", "inelastic", 0.20, "energy", _inelastic(0.80)),
        CandidateSpec("inelastic-0.50", "inelastic", 0.50, "energy", _inelastic(0.50)),
        CandidateSpec(
            "momentum-kick-0.025",
            "momentum-kick",
            0.025,
            "momentum",
            _momentum_kick(0.025),
        ),
        CandidateSpec(
            "momentum-kick-0.075",
            "momentum-kick",
            0.075,
            "momentum",
            _momentum_kick(0.075),
        ),
        CandidateSpec(
            "momentum-kick-0.150",
            "momentum-kick",
            0.150,
            "momentum",
            _momentum_kick(0.150),
        ),
        CandidateSpec("collision-dropout", "collision-dropout", 1.0, "collision", _collision_dropout),
        CandidateSpec("time-reverse", "time-reverse", 1.0, "initial-condition", _time_reverse),
        CandidateSpec("random", "random", 1.0, "state", _random),
    )


def build_candidates(cfg: WorldConfig, seed: int) -> dict[str, np.ndarray]:
    return {spec.name: spec.build(cfg, seed) for spec in candidate_specs()}
