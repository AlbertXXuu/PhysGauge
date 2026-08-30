# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use semantic versioning.

## [1.1.0] - Unreleased

### Added

- Frozen the pre-training R2 learned-dynamics validation protocol v2, including a small-data/
  small-capacity model, aggregate decision rules, target error band, and baseline dry-run.
- Added the dependency-free NumPy R2 training/evaluation path, deterministic three-seed execution,
  case-level 95% Wilson intervals, cross-seed summaries, and hash-verified evidence bundle.
- Added a dependency-free, loopback-only `studio` command with the AlvenX product design language,
  visual v1 calibration, an explicitly bounded learned-model study, and a fresh smoke-check control.
- Bundled integrity-checked AlvenX masters, Instrument Sans, and a compact evidence fallback so the
  Studio remains functional from an installed wheel.
- Replaced the split README heading with one outlined `AlvenX — Physics Evidence` project lockup.

### Research result

- Recorded the frozen R2 outcome as `inconclusive-model`: all three predictors were `too-weak`, so
  observed visual disagreement rates are not treated as learned-model evidence.

### Fixed

- Clarified that the legacy `time-reverse` candidate is a frame-order reversal, not a physical
  time reversal, without changing the hash-verified v1 evidence bundle.
- Made future reports derive the frame-order-reversal distance range and tolerance from their own
  result data instead of embedding v1 constants.
- Included the referenced protocols, evidence, bilingual documentation, and verification scripts in
  the source distribution.

### Changed

- Normalize current software, runtime, Studio, and documentation identity as the `v1.1.0`
  presentation and maintenance closure candidate while preserving the unchanged `v1.0.0`
  calibration evidence and the separate R2 `inconclusive-model` research milestone.

## [1.0.0] - 2026-08-24

### Added

- Frozen 24-case analytical collision calibration protocol.
- Parameterized energy, momentum, collision, time-order, and random-state corruptions.
- MSE, SSIM error, Pixel Fréchet, temporal-gradient, and state-grounded metrics.
- Exact-miss, low-sensitivity, and monotonic-response diagnostics.
- `run`, `verify`, and `doctor` CLI commands plus a stable Python API.
- Hash-verified JSON, CSV, Markdown, and SVG evidence bundle.
- Python 3.11–3.13 CI, wheel smoke tests, repository checks, and bilingual documentation.

### Changed

- Reframed the incubator prototype from an unsupported universal leaderboard claim into a scoped,
  falsifiable metric-calibration tool.

[1.1.0]: https://github.com/AlbertXXuu/PhysGauge/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/AlbertXXuu/PhysGauge/releases/tag/v1.0.0
