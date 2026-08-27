<p align="center">
  <img src="docs/assets/alvenx-wordmark.svg" width="320" alt="AlvenX">
</p>

# PhysGauge

[简体中文](README.zh-CN.md) · [Protocol](docs/protocol.md) · [Errata](docs/ERRATA.md) ·
[Roadmap](docs/ROADMAP.md) · [learned-model protocol (R2)](docs/r2-protocol.md) ·
[v1 evidence](docs/evidence/v1.0.0/report.md) ·
[learned-model evidence](docs/evidence/r2/report.md)

PhysGauge is a local, deterministic stress-test suite for video evaluation metrics. It injects
known violations into an analytically verified two-disc collision world, then measures whether an
evaluation metric notices the error and responds monotonically as the violation becomes stronger.

It calibrates video metrics against controlled physical violations before those metrics are used
to interpret model outputs.

## What the v1 evidence establishes

- All 24 seeded oracle rollouts conserve energy and momentum and contain an observable collision.
- Dedicated state-grounded checks detect every injected energy, momentum, collision, initial-state,
  and random-state violation.
- MSE, SSIM error, Pixel Fréchet, and temporal-gradient MSE increase monotonically across the frozen
  inelastic and momentum-kick severity sweeps.
- The order-invariant Pixel Fréchet metric has a frame-order blind spot: reversing the frame
  sequence without negating velocities (a frame-order reversal, not a physical time reversal)
  yields computed distances from 0 to 5.76e-15 even though the kinematic residual is large.
  See [Errata](docs/ERRATA.md).

These statements are checked by tests and by the committed, hash-verified
[`v1.0.0` evidence bundle](docs/evidence/v1.0.0/manifest.json). The evidence applies to the frozen
synthetic collision protocol and its included metrics; learned-model results are reported separately.

## Learned-model study result

The pre-registered research-milestone R2 experiment trained three small state-dynamics predictors
oracle/persistence/linear pipeline dry-run. All three predictors were classified as `too-weak`:
their post-contact partial-error rates were 91.8%–99.6%, so the frozen outcome is
`inconclusive-model`. Some visual metrics showed disagreements, but the model-capability gate failed
first; the preregistered interpretation therefore remains `inconclusive-model`. See the
[learned-model report](docs/evidence/r2/report.md) and [protocol](docs/r2-protocol.md). Here, `R2`
identifies **research milestone 2**.

## Quick start

Python 3.11–3.13 is supported.

```bash
git clone --branch v1.0.0 --depth 1 https://github.com/AlbertXXuu/PhysGauge.git
cd PhysGauge

python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .

physgauge doctor
physgauge run --output runs/my-calibration
physgauge verify --bundle docs/evidence/v1.0.0
physgauge studio
```

The run command uses the deterministic CPU collision suite and writes five reviewable files: full
JSON records, flat CSV metrics, a Markdown report, an SVG sensitivity matrix, and a SHA-256 manifest.

`studio` opens a loopback visual interface in the AlvenX product design language. It presents the
committed v1 calibration, the preregistered learned-model outcome, and a four-case local smoke check
from one liquid glass control. See
[Studio usage](docs/studio.md).

## Stable Python API

```python
from physgauge import SuiteConfig, run_suite, write_bundle

result = run_suite(SuiteConfig(cases=24, frames=48, seed=20260824))
write_bundle(result, "runs/example")
```

For a model or simulator that exposes the same eight-value state contract, use
`physgauge.evaluate_trajectory(...)` directly. See [the protocol](docs/protocol.md) for the state
layout, metric definitions, thresholds, and interpretation boundary.

## Why this is separate from larger physics benchmarks

WorldModelBench, Physics-IQ, WorldBench, Morpheus, CRONOS, and PhyGround evaluate models across much
broader prompts, real scenes, or physical laws. PhysGauge serves an earlier engineering step: a fast
unit test that verifies the behavior of an evaluation metric against controlled counterexamples
before spending compute on a large benchmark. The current comparison is documented in
[research landscape](docs/research-landscape.md).

## Reproduce the repository evidence

```bash
python -m pip install -e ".[dev]"
ruff check .
python -m unittest discover -s tests -v
python scripts/check_repository.py
python scripts/build_evidence.py --verify
python scripts/run_r2.py --verify
python -m build
```

## Scope and limits

- v1 covers equal-mass, two-dimensional rigid-disc collision dynamics only.
- `pixel_frechet` uses its own tiny grayscale pixel feature space, distinct from Inception FID and FVD.
- State-grounded checks require simulator/model state; video-only outputs can use the visual metrics
  but cannot receive the law-specific guarantees.
- The random baseline provides a scale reference for the included metric responses.

Apache-2.0 licensed. PhysGauge is an [AlvenX](https://alvenx.com) open-source project.
