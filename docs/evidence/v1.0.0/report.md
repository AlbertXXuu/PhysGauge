# PhysGauge v1 calibration evidence

Protocol: `physgauge-collision-calibration-v1` · cases: 24 · frames/case: 48 · seed: `20260824`.

## Result

Every injected violation was detected by its matching state-grounded oracle check. At the same time, one or more image/distribution metrics treated several controlled violations as close to the correct rollout relative to the random baseline.

| candidate | expected violation | oracle detection | MSE exact miss | SSIM exact miss | Pixel Fréchet exact miss | temporal-gradient exact miss |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `collision-dropout` | collision | 100% | 0% | 0% | 0% | 0% |
| `correct` | none | 0% | 0% | 0% | 0% | 0% |
| `inelastic-0.50` | energy | 100% | 0% | 0% | 0% | 0% |
| `inelastic-0.80` | energy | 100% | 0% | 0% | 0% | 0% |
| `inelastic-0.95` | energy | 100% | 0% | 0% | 0% | 0% |
| `momentum-kick-0.025` | momentum | 100% | 0% | 0% | 0% | 0% |
| `momentum-kick-0.075` | momentum | 100% | 0% | 0% | 0% | 0% |
| `momentum-kick-0.150` | momentum | 100% | 0% | 0% | 0% | 0% |
| `random` | state | 100% | 0% | 0% | 0% | 0% |
| `time-reverse` | initial-condition | 100% | 0% | 0% | 100% | 0% |

## Severity response

| corruption family | MSE | SSIM error | Pixel Fréchet | temporal-gradient MSE |
| --- | ---: | ---: | ---: | ---: |
| inelastic | 100% | 100% | 100% | 100% |
| momentum-kick | 100% | 100% | 100% | 100% |

An **exact miss** requires a failed state-grounded check and metric error at or below `1e-10`. The SVG separately shows **low sensitivity**: metric error below 25% of the no-physics random baseline.

## Interpretation boundary

This controlled calibration result shows that a metric can miss known physical or causal corruptions in this analytical collision world. It does **not** measure a learned world model, establish real-world model rankings, or prove that every public leaderboard has the same failure. PhysGauge is a metric unit test to run before broader benchmarks and human studies.

`pixel_frechet` is an intentionally dependency-light Fréchet distance over tiny pixel features. It is not Inception FID or FVD. Its exact blindness to a time-reversed frame set demonstrates the consequence of discarding temporal order.
