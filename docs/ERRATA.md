# PhysGauge v1 Errata

Scope: `physgauge-collision-calibration-v1` (schema `1.0`). This errata clarifies the scientific
meaning of one candidate in the frozen v1 suite. It does **not** modify any published artifact
under `docs/evidence/v1.0.0/`; those hashes remain valid and `verify_bundle` must still pass.

## `time-reverse` is a frame-order reversal, not a physical time reversal

- **Legacy ID**: `time-reverse` is the historical candidate ID and is preserved for schema and
  evidence compatibility. It is not renamed.
- **Actual operation**: the builder reverses the state sequence without negating velocities:
  `simulate(cfg)[::-1]`. A true physical time reversal requires both position reversal and velocity
  negation, `q'(t) = q(T-t), v'(t) = -v(T-t)`.
- **Consequence**: the recorded velocity field contradicts the finite-difference position motion.
  The `kinematic_residual` diagnostic detects exactly this inconsistency. The candidate is therefore
  a *frame-order / trajectory-order reversal corruption* — **not** a valid Newtonian trajectory and
  **not** merely "wrong in initial condition and causality".

## `pixel_frechet` distance for the `time-reverse` candidate

- By construction the reversed sequence has the same empirical per-frame feature distribution as
  the original, so the underlying distributions are identical and the theoretical distance is zero.
- Computed distances are not bitwise zero because of floating-point matrix-square-root, covariance,
  and summation error: 13 of the 24 cases return `0.0`, the maximum is about `5.76e-15`, and all
  values are below the `1e-10` exact-miss tolerance.
- The correct statement is therefore "identical by construction; computed distances range from 0 to
  5.76e-15", **not** "exact bitwise-zero blindness".

## What this does and does not show

- **Does show**: any distance built on per-frame independent features whose empirical distribution
  is permutation-invariant cannot distinguish a sequence from any permutation of its frames,
  including full reversal.
- **Does not show**: that every FID / MMD / FVD variant is order-blind. Metrics that use temporal
  features (e.g. FVD) may carry order, and finite-sample MMD estimators must be considered
  separately.
