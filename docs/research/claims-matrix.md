# PhysGauge claims matrix

Snapshot date: `2026-08-28`

This matrix is the shortest source of truth for what the frozen v1 calibration
and R2 learned-model study do and do not support. Status terms mean:

- `established`: directly supported within the named protocol and evidence;
- `not established`: the available evidence does not meet the required gate or
  does not study the claimed scope; this is not proof that the claim is false;
- `unknown`: a live empirical question remains after applying the current
  evidence boundary.

## Claim ledger

| ID | Claim | Status | Evidence and bounded interpretation |
| --- | --- | --- | --- |
| C01 | Every one of the 24 frozen analytical oracle trajectories contains the required collision and satisfies the registered energy and momentum conservation tolerances. | `established` | The [v1 protocol acceptance criteria](../protocol.md#acceptance-criteria) and hash-bound [v1 report](../evidence/v1.0.0/report.md#result) record a valid oracle for every case; the [manifest](../evidence/v1.0.0/manifest.json) binds the artifacts. This applies to the frozen equal-mass, two-disc simulator. |
| C02 | The dedicated state-grounded check detects every injected v1 violation in all 24 cases, while the correct control is not falsely flagged. | `established` | Every injected family has 100% matching-oracle detection and the correct control has 0% detection in the [v1 result table](../evidence/v1.0.0/report.md#result). It establishes controlled sensitivity, not arbitrary real-world fault coverage. |
| C03 | MSE, SSIM error, Pixel Fréchet and temporal-gradient MSE respond monotonically across every adjacent severity level in the frozen inelastic and momentum-kick sweeps. | `established` | The [severity response](../evidence/v1.0.0/report.md#severity-response) is 100% for all four metrics in both registered families under the [protocol's monotonic criterion](../protocol.md#acceptance-criteria). Numerical sensitivity outside this renderer and severity range is not covered. |
| C04 | The current `pixel_frechet` is blind to the frozen frame-order reversal because it compares a permutation-invariant empirical distribution of per-frame features. | `established` | The [erratum](../ERRATA.md#pixel_frechet-distance-for-the-time-reverse-candidate) records 13/24 computed distances at `0.0`, a maximum near `5.76e-15`, and all 24 below the `1e-10` exact-miss tolerance. The candidate is a frame-order corruption, not a physical time reversal. |
| C05 | Every FID, MMD or FVD implementation is necessarily blind to frame order. | `not established` | The [erratum's boundary](../ERRATA.md#what-this-does-and-does-not-show) limits the result to distances over permutation-invariant empirical distributions of per-frame independent features. Temporal feature extractors such as FVD may encode order, and finite-sample MMD estimators require separate analysis. |
| C06 | The R2 experiment and artifact chain are internally valid under the registered protocol. | `established` | The frozen [R2 report](../evidence/r2/report.md#pre-registered-decision) records `Experiment valid: True`; the dedicated [R2 manifest](../evidence/r2/manifest.json) and [negative-result verification path](negative-result-r2.md#evidence-and-verification) bind four artifacts and the registered decision. |
| C07 | The three R2 learned predictors were capable enough to test a learned-model visual-metric blind spot. | `not established` | All seeds were classified `too-weak`, with 91.8%–99.6% partial-error rates, so the model-capability gate failed before visual interpretation. See the [observed capability table](negative-result-r2.md#observed-capability) and [preregistered gate](../r2-protocol.md#6-有效性与决策门). |
| C08 | R2 demonstrated that Pixel Fréchet or temporal-gradient MSE misses errors from a sufficiently capable learned dynamics model. | `not established` | The visual disagreements are preserved in the [R2 report](../evidence/r2/report.md#test-summary), but the registered outcome is `inconclusive-model`. The [negative-result boundary](negative-result-r2.md#claims-this-result-does-not-support) prohibits using those diagnostics as supporting learned-model evidence. |
| C09 | A future predictor that passes a preregistered capability gate will or will not show the same visual/state disagreement. | `unknown` | R2 cannot answer this because its predictors failed capability first. The [legitimate reopening design](negative-result-r2.md#legitimate-reopening-experiment) requires a new protocol and unseen test split rather than tuning on R2. |
| C10 | PhysGauge's controlled calibration results generalize to real generated video, pixels-only world models or OOD physical systems. | `not established` | The [v1 interpretation](../protocol.md#interpretation), [R2 scope](../r2-protocol.md#0-研究问题与边界) and [research non-goals](../research-landscape.md#non-goals) explicitly exclude those scopes. No real video generator or state-extraction pipeline was evaluated. |
| C11 | After independently validating state extraction, controlled PhysGauge failures will predict metric or human-judgment failures on real video. | `unknown` | This causal and external-validity question has not been run. The current [research landscape](../research-landscape.md#decision) positions PhysGauge as a small calibration layer before broader benchmarks rather than evidence of downstream prediction. |

## What would change a status

| Claim group | Minimum new evidence |
| --- | --- |
| Learned-model capability and disagreement (C07–C09) | A registered new protocol, new train/validation/test identities, a predictor selected without the new test split, at least three seeds, and capability-gate success before visual results are interpreted. |
| Temporal metric generalization (C05) | Direct controlled tests of each named metric implementation and feature extractor under order-preserving and order-breaking transformations; family names alone are insufficient. |
| Real-video generalization (C10–C11) | Independently validated state extraction or physical ground truth, named real or generated video systems, preregistered outcomes, broader benchmark and human comparison, and explicit tracking of extraction error as a separate variable. |

Changing a matrix status requires a new evidence link and a dated review. It
does not rewrite the frozen v1 or R2 bundles.
