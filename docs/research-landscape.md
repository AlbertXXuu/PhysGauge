# Research landscape and project boundary

Last checked: 2026-08-24. This file records why PhysGauge is a metric calibration tool rather than a
claim to be the comprehensive physics benchmark for world models.

## Primary references

| Work | What it covers | Boundary relative to PhysGauge |
| --- | --- | --- |
| [WorldModelBench](https://github.com/WorldModelBench-Team/WorldModelBench) | 350 prompts across seven application domains with a learned judge | broader model ranking; much heavier evaluation stack |
| [Physics-IQ](https://github.com/google-deepmind/physics-IQ-benchmark) | real captured physical phenomena from multiple views | real-world coverage rather than metric unit tests |
| [WorldBench](https://arxiv.org/abs/2601.21282) | disentangled physical concepts and material properties | diagnostic benchmark across many concepts |
| [Morpheus](https://github.com/physics-from-video/Morpheus) | physics-informed evaluation on real physical systems | reconstructs and scores real model-generated videos |
| [CRONOS](https://arxiv.org/abs/2605.23699) | counterfactual consistency under scene, viewpoint, object, and appearance interventions | photorealistic model-level intervention benchmark |
| [PhyGround](https://arxiv.org/abs/2605.10806) | 13 laws, human annotations, and a specialized VLM judge | large criteria-grounded benchmark and judge |
| [Beyond FVD / JEDi](https://openreview.net/forum?id=cC3LxGZasH) | statistical and temporal limitations of FVD plus an alternative metric | metric research at benchmark scale |

## Decision

The field already has several large physics benchmarks. Releasing another small collision leaderboard
would add little. PhysGauge instead occupies a narrower engineering layer:

- zero-network, seconds-scale calibration before expensive model evaluation;
- analytical state truth and controlled, parameterized corruptions;
- explicit separation of exact invariance, low sensitivity, monotonic response, and physical failure;
- a small stable API suitable for metric CI and regression tests; and
- a hash-verified evidence bundle whose claims are deliberately narrower than the data.

## Non-goals

- ranking current text-to-video or interactive world models;
- replacing real-world, human, or VLM-judge benchmarks;
- inferring unobserved physical state from arbitrary video; or
- claiming novelty for simulator-based physics evaluation in general.

The next meaningful expansion should add a genuinely different analytical regime or an external
metric adapter only when it creates a new falsifiable test. Feature count alone is not a reason to
expand the suite.
