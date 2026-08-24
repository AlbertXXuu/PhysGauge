# PhysGauge R2 learned-dynamics evidence

Protocol: `physgauge-learned-dynamics-r2-v2` · train/validation/test: 128/128/256 · model seeds: `[11, 29, 47]`.

## Training

| seed | epochs | best validation loss | runtime (s) | checkpoint SHA-256 |
|---:|---:|---:|---:|---|
| 11 | 200 | 7.8464 | 3.653 | `882e86a7c5eada1969af69228e04fc11266dc4ee57a01bf2be1a336c642e0037` |
| 29 | 200 | 7.80953 | 7.317 | `8059eab31dbc80c6dd3570e2df169ce158b58c8f3b4f07e90b8baa7f42445775` |
| 47 | 200 | 7.89516 | 7.334 | `87e166252835d21ff750e95ce94defe925f8a510e46be5bb7197524aced7e335` |

Execution: Python 3.11.0, NumPy 2.4.6, CPU only, 122.553 s total.

## Test summary

| candidate | state failure | partial error | collision accuracy | median position RMSE | median velocity RMSE | MSE disagreement | SSIM disagreement | Pixel Fréchet disagreement | temporal-gradient disagreement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `analytic-oracle` | 0.0% | 0.0% | 100.0% | 0 | 0 | 0.0% | 0.0% | 0.0% | 0.0% |
| `learned-seed-11` | 100.0% | 99.6% | 44.1% | 0.0513225 | 2.03353 | 1.2% | 1.2% | 89.8% | 100.0% |
| `learned-seed-29` | 100.0% | 98.0% | 45.3% | 0.0355905 | 1.31274 | 4.7% | 4.7% | 79.7% | 100.0% |
| `learned-seed-47` | 100.0% | 91.8% | 81.6% | 0.0314537 | 1.27442 | 14.5% | 14.5% | 85.5% | 100.0% |
| `linear-extrapolation` | 100.0% | 100.0% | 0.0% | 0.050821 | 0.780732 | 0.0% | 0.0% | 100.0% | 100.0% |
| `persistence` | 100.0% | 100.0% | 0.0% | 0.0314928 | 0.780732 | 0.0% | 0.0% | 100.0% | 100.0% |

## Across-seed aggregate

Each entry is the mean ± sample standard deviation across the registered model seeds.

| metric | mean ± standard deviation |
|---|---:|
| `state_failure_rate` | 1 ± 0 |
| `partial_error_rate` | 0.964844 ± 0.0413399 |
| `collision_event_accuracy` | 0.570312 ± 0.213204 |
| `median_position_rmse` | 0.0394556 ± 0.0104831 |
| `median_velocity_rmse` | 1.54023 ± 0.427638 |
| `disagreement_mse` | 6.8% ± 6.9% |
| `disagreement_ssim_error` | 6.8% ± 6.9% |
| `disagreement_pixel_frechet` | 85.0% ± 5.1% |
| `disagreement_temporal_gradient_mse` | 100.0% ± 0.0% |

All case-level proportions and their 95% Wilson intervals are stored under `summary.candidates.*.proportion_intervals_95` in `results.json`.

## Pre-registered decision

- Experiment valid: **True**
- Consensus model class: **`too-weak`**
- Supporting visual metrics: **['pixel_frechet', 'temporal_gradient_mse']**
- Outcome: **`inconclusive-model`**

The registered model-capability gate failed before the visual-disagreement gate. The listed supporting metrics therefore do not constitute learned-model evidence.

This result applies only to the frozen small-data/small-capacity predictor and IID two-disc test split. It is not evidence about video generators, OOD generalization, or all visual metrics.
