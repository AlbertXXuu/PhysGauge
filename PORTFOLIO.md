# PhysGauge portfolio evidence

## Problem

Before a video metric is used to interpret world-model output, its response to known physical errors
should be calibrated. PhysGauge injects controlled violations into an analytically verified
two-disc world and measures whether state-grounded and visual metrics detect them monotonically.

## Why it was difficult

The suite must distinguish metric insensitivity from simulator error, initial-condition drift,
weak-model failure and visual tracking confounds. Claims must also stay inside a narrow synthetic
protocol while preserving hash-bound evidence and preregistered decision gates.

## Project-specific decisions

- Validate the analytic oracle before interpreting metric behavior.
- Compare visual metrics with state-grounded physical checks under controlled corruptions.
- Treat permutation invariance as a known property and record the frame-order result as a bounded
  counterexample, not a new theorem.
- Gate learned-model interpretation on model capability before examining visual disagreement.
- Preserve `inconclusive-model` instead of tuning on the frozen test split.

See [the v1 protocol](docs/protocol.md), [R2 protocol](docs/r2-protocol.md) and
[roadmap](docs/ROADMAP.md).

## Most demanding correction

The legacy `time-reverse` candidate reverses frame order without negating velocities; calling it a
physical time reversal was too strong. The correction was appended in [ERRATA.md](docs/ERRATA.md)
and future wording was fixed without modifying the hash-bound v1 bundle.

## Verified result

All 24 oracle rollouts satisfied the registered conservation/collision checks. State-grounded
metrics detected every injected violation; included visual metrics were monotonic on the frozen
severity sweeps. Pixel Fréchet produced distances from `0` to `5.76e-15` for frame-order reversal
while the kinematic residual was large.

## Negative result and limits

R2 trained three small predictors, but post-contact partial-error rates were `91.8%–99.6%`; all were
classified `too-weak`, so the preregistered outcome is `inconclusive-model`. The work does not
establish that the metrics reliably evaluate learned world models or that the method generalizes to
real video. See [the R2 evidence](docs/evidence/r2/report.md).

## External use

As of `2026-08-28`, this repository contains no qualifying independent metric-maintainer run. The
research line remains closed unless external use or a new protocol with an unseen split supplies a
new reason to reopen it.

## Personal contribution

The repository history shows AlbertXXuu as the sole human contributor. The owner is responsible for
the research question, analytic-world and corruption design, metric interpretation, preregistration,
implementation acceptance, negative-result boundary and release approval.
