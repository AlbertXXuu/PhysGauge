"""PhysGauge: deterministic stress tests for physics-aware video metrics."""

from .experiment import PROTOCOL_ID, SuiteConfig, run_suite
from .metrics import evaluate_trajectory
from .report import verify_bundle, write_bundle
from .world import WorldConfig, make_case, simulate, validate_oracle

__all__ = [
    "PROTOCOL_ID",
    "SuiteConfig",
    "WorldConfig",
    "evaluate_trajectory",
    "make_case",
    "run_suite",
    "simulate",
    "validate_oracle",
    "verify_bundle",
    "write_bundle",
]

__version__ = "1.1.0"
