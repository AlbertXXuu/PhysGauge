# Maintenance policy

Current public release: `v1.1.0`
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
