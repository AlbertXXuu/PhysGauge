# PhysGauge v1 protocol

Protocol identifier: `physgauge-collision-calibration-v1`

Schema version: `1.0`

## Question

Given an error whose physical meaning and strength are known, does an evaluation metric:

1. return a non-zero signal when the state-grounded oracle fails; and
2. increase monotonically when a within-family violation becomes stronger?

The protocol separates an exact metric miss from low sensitivity. An exact miss means a dedicated
physics check fails while the metric error is at most `1e-10`. Low sensitivity means the metric error
is below 25% of a no-physics random baseline for the same rendered case. Low sensitivity is a scale
diagnostic, not proof that the metric is invalid.

## State contract

Each trajectory is a float array with shape `(steps, 8)`:

```text
[p1_x, p1_y, v1_x, v1_y, p2_x, p2_y, v2_x, v2_y]
```

Coordinates are normalized to a unit square. Both discs have equal unit mass. The fixed-step oracle
uses uniform free motion and the closed-form equal-mass collision impulse. Every generated oracle is
rejected unless it contains a collision and conserves kinetic energy and linear momentum within
floating-point tolerance.

## Frozen suite

The v1 evidence uses 24 deterministic cases, 48 rendered frames per trajectory, and seed `20260824`.
Each case varies collision axis, radius, closing speed, tangential common drift, and post-contact
duration while remaining away from the walls.

| family | levels | state-grounded expectation |
| --- | --- | --- |
| correct | 1 | no failure |
| inelastic | restitution 0.95, 0.80, 0.50 | relative energy drift |
| momentum kick | 0.025, 0.075, 0.150 | normalized momentum drift |
| collision dropout | 1 | wrong post-contact relative velocity sign |
| time reverse | 1 | wrong initial state and kinematic residual |
| random | 1 | large state-position error |

## Metrics

Visual/temporal error metrics (lower is better):

- `mse`: aligned pixel mean squared error.
- `ssim_error`: one minus mean global per-frame SSIM for the controlled grayscale fixtures.
- `pixel_frechet`: Fréchet distance between 32-dimensional downsampled pixel-feature distributions;
  it ignores frame order by construction and is not FID/FVD.
- `temporal_gradient_mse`: aligned MSE between consecutive-frame differences.

State-grounded diagnostics:

- position and velocity RMSE against the oracle;
- initial-condition error;
- maximum relative kinetic-energy drift;
- maximum normalized momentum drift;
- collision-event sign mismatch; and
- kinematic residual between finite-difference position and reported velocity.

## Acceptance criteria

The committed v1 bundle is accepted only when:

1. every oracle passes collision, energy, and momentum validation;
2. every injected error is detected by its dedicated state-grounded check in every case;
3. the correct control is pixel-identical and is not falsely flagged;
4. every visual/temporal metric is strictly monotonic over all adjacent severity levels in both
   continuous corruption families; and
5. `pixel_frechet` exactly misses the time-reversed frame set in every case.

## Interpretation

The protocol calibrates metrics under controlled perturbations. It does not estimate real-world
model quality, human preference, or model ranking. A user should combine it with broader datasets,
human judgments, and task-specific state extraction. The exact time-reversal result applies to any
frame-distribution metric that discards order; the numerical sensitivity results apply only to this
renderer and frozen suite.
