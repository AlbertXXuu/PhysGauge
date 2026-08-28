# R2 negative result: the model-capability gate failed

Status: closed, hash-verified result under protocol
`physgauge-learned-dynamics-r2-v2`.

This note explains why a valid experiment produced an inconclusive learned-model
result. It does not modify the frozen protocol or any artifact under
[`docs/evidence/r2/`](../evidence/r2/report.md).

## Initial question and hypothesis

R2 asked whether a trained dynamics predictor in the analytical two-disc world
would make errors that PhysGauge's state checks detect while at least one
prelisted visual metric remains relatively insensitive. The intended positive
case required a predictor that had learned collisions but retained a bounded
amount of post-contact error. A weak predictor was not an acceptable source of
evidence for a visual-metric blind spot.

The protocol therefore fixed the decision order before training:

1. the experiment and evidence chain must be valid;
2. at least two of three seeds must beat linear extrapolation on both median
   position and velocity RMSE and reach at least 75% collision-event accuracy;
3. at least two seeds must fall inside the 10%–70% post-contact partial-error
   band;
4. only then can a prelisted visual metric with at least 5% disagreement in the
   same two or more seeds support `continue-r3`.

Failure of the second gate, or a partial-error rate above 70%, classifies a seed
as `too-weak`. A two-seed consensus of `too-weak` makes the registered outcome
`inconclusive-model`, regardless of later visual-metric values.

## Frozen setup

| Item | Frozen value |
| --- | --- |
| Train / validation / test cases | 128 / 128 / 256 mutually exclusive IID configurations |
| Base seeds | `20260825` / `20260826` / `20260827` |
| Model seeds | `11`, `29`, `47` |
| Predictor | `Linear(9,32) → SiLU → Linear(32,32) → SiLU → Linear(32,8)` |
| Training | float32 AdamW, batch 256, at most 200 epochs, validation early stopping |
| Evaluation | autoregressive eight-state rollout from exact initial state; 48 rendered frames |
| Baselines | analytic oracle, persistence and linear extrapolation on all 256 test cases |
| Execution | Python 3.11.0, NumPy 2.4.6, CPU, 122.553 seconds total |

The predictor consumed state and radius directly. No detector, tracker, identity
matching, occlusion recovery, velocity estimator or video generator was present,
so visual-tracking error was not a competing cause in this experiment.

## Observed capability

The experiment-validity gate passed: the baseline dry-run, split integrity,
initial-condition contract, result consistency and evidence hashes all passed.
The learned predictors nevertheless failed the next gate.

| Seed | Collision accuracy | Partial-error rate | Median position RMSE | Median velocity RMSE | Classification |
| ---: | ---: | ---: | ---: | ---: | --- |
| 11 | 44.1% | 99.6% | 0.0513225 | 2.03353 | `too-weak` |
| 29 | 45.3% | 98.0% | 0.0355905 | 1.31274 | `too-weak` |
| 47 | 81.6% | 91.8% | 0.0314537 | 1.27442 | `too-weak` |
| Linear extrapolation | 0.0% | 100.0% | 0.050821 | 0.780732 | fixed weak baseline |

All three learned seeds had a 100% state-failure rate. Seed 47 crossed the 75%
collision threshold, but none beat linear extrapolation on both median RMSE
measures, and every seed's partial-error rate exceeded the 70% upper bound. The
three-seed consensus was therefore `too-weak`; the frozen outcome is
`inconclusive-model`, and R3 was not triggered.

For completeness, Pixel Fréchet disagreement was 89.8%, 79.7% and 85.5% across
seeds 11, 29 and 47; temporal-gradient disagreement was 100.0% for every seed.
Those are preserved diagnostics, not supporting learned-model evidence, because
the capability gate failed first.

## What the result establishes

- The registered R2 pipeline can train, roll out and independently evaluate
  three deterministic learned predictors while retaining complete case-level
  evidence.
- Under this exact small-data, small-capacity configuration, all three predictors
  were too weak for the planned comparison between state-grounded and visual
  metrics.
- Stopping before R3 is the preregistered result, not missing work. Further tuning
  on the observed R2 test split would weaken the evidence.

## Claims this result does not support

- PhysGauge has demonstrated a learned-model visual blind spot.
- Pixel Fréchet or temporal-gradient MSE missed the errors of a sufficiently
  capable learned model in R2.
- Small neural predictors, learned dynamics systems or video generators cannot
  learn collisions in general.
- PhysGauge is useful or useless for real generated video, OOD physics, other
  physical systems or market adoption.
- The R2 result applies to all visual metrics, FVD, human judgment or real-world
  video evaluation.

## Threats to validity

- **Internal:** preregistration, deterministic splits, direct state outputs and
  hash verification reduce researcher degrees of freedom. One NumPy MLP
  implementation and three seeds still leave implementation-specific effects.
- **Construct:** collision accuracy and the 10%–70% partial-error band are
  engineering gates for whether the model can answer R2; they are not universal
  definitions of learned physics.
- **External:** all test cases are IID samples from one synthetic equal-mass,
  two-disc world. There is no evidence here about OOD configurations, pixels-only
  systems or real video.
- **Statistical:** each case-level proportion uses 256 configurations and stored
  Wilson intervals, but across-model variation is represented by only three
  registered seeds.

## Legitimate reopening experiment

A future run may reopen learned-model validation only for a new, registered
hypothesis—not to rescue R2. A valid candidate would keep the direct-state
two-disc problem so model capacity remains the main changed variable, select a
capacity-justified predictor using only new train and validation splits, and
evaluate once on a new unseen test split under a new protocol ID.

Before execution it must freeze the architecture, optimizer, three or more model
seeds, capability and target-band gates, per-case evidence, a no-paid-API budget
and a bounded CPU/GPU-hour cap. The old R2 test results cannot select the model or
hyperparameters. The capability gate must again be evaluated before any visual
disagreement: another `too-weak` result closes the run as inconclusive, while a
`too-strong` result motivates a separately registered harder setting rather than
post-hoc corruption of the same test.

## Evidence and verification

- [Preregistered protocol](../r2-protocol.md)
- [Frozen report](../evidence/r2/report.md)
- [Machine-readable results](../evidence/r2/results.json)
- [Artifact manifest](../evidence/r2/manifest.json)
- [Split manifest](../evidence/r2/split-manifest.json)

Verify the dedicated R2 bundle from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\run_r2.py --verify
```

The expected result is
`r2-evidence=PASS protocol=physgauge-learned-dynamics-r2-v2 artifacts=4`.
