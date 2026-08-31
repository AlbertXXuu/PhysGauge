# Maintenance policy

Current public release: `v1.1.2`
Research/evidence baseline: immutable `v1.0.0`
Development mode: maintenance; preservation of closed research results

## Frozen release and research surface

The `v1.0.0` tag and GitHub Release are immutable. The following remain frozen:

- protocol `physgauge-collision-calibration-v1`, 24 seeded cases and 10 candidate identities;
- committed results, CSV, report, sensitivity matrix, manifest and artifact hashes;
- metric definitions, thresholds and bounded v1 claims;
- protocol `physgauge-learned-dynamics-r2-v2`, split identities, model seeds, gates and R2 evidence;
- the R2 outcome `inconclusive-model` and the frame-order-reversal erratum.

Neither an improved model nor a later interpretation replaces the published negative result.

## Accepted maintenance

- correctness, security, portability, CI and dependency-compatibility fixes;
- reproduction and documentation clarification;
- evidence validation improvements that do not rewrite frozen artifacts;
- contributor work tied to a falsifiable metric test or a documented defect.

## Cross-NumPy reproduction boundary

The v1.1.2 maintenance investigation reproduced the frozen v1 suite with NumPy `1.26.4`, `2.0.2`,
`2.1.3`, `2.2.6`, `2.3.3`, and `2.4.6` under the same Python, Pillow, and single-thread settings.
The rendered frames and squared-difference tensors were byte-identical in all six environments.
NumPy 1.26–2.2 nevertheless produced a different float32 reduction result from NumPy 2.3–2.4;
using a float64 accumulator removed that split. This localizes the difference to reduction order,
consistent with NumPy 2.3's documented [iterator and reduction changes][numpy-iterator-change] and
NumPy's warning that float32 [`mean` results can vary with accumulation precision][numpy-mean].

The frozen artifacts and metric implementations remain unchanged. Reproduction comparison permits
`rtol=1e-6` and `atol=1e-10` only for the numeric components of the generated `p1`, `p2`, `v1`, and
`v2` case vectors, continuous record metrics, candidate mean metrics, and measured values used by
monotonicity summaries. The case-vector allowlist was required by a one-ULP Windows/glibc `sin`
difference exposed by Linux CI. Scalar case parameters, schema and container types, configuration,
protocol/case/candidate identity, booleans, integers and counts, `severity`, `physics_failed`, every
`low_sensitivity_*` and `exact_miss_*` value, detection/rate decisions, and monotonicity decisions
remain exact. A new field is exact by default until the schema-aware comparator explicitly
classifies it as a continuous physical measurement.

## Research reopening gate

New physical systems, models, metrics, UI surfaces, dependencies or benchmark scale require a
specific external need or registered hypothesis. Reopening learned-model validation requires a new
protocol ID, a new unseen test split, a predeclared capability gate, cost/repetition limits and an
explanation of why R2's weak-model result will not be reused for tuning.

## Stop and escalation

Keep the current research line closed while no independent collaboration or new protocol justifies
it. Reject work whose purpose is to rescue R2, inflate scenario/model count, or generalize from the
synthetic two-disc world without evidence. Corrections use dated errata; hash-bound artifacts stay
unchanged.

[numpy-iterator-change]: https://numpy.org/doc/2.3/release/2.3.0-notes.html#changes-to-the-main-iterator-and-potential-numerical-changes
[numpy-mean]: https://numpy.org/doc/stable/reference/generated/numpy.mean.html
