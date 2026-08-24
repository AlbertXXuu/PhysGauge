# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use semantic versioning.

## [Unreleased]

### Added

- Frozen, pre-training R2 learned-dynamics validation protocol and milestone tracking.

### Fixed

- Clarified that the legacy `time-reverse` candidate is a frame-order reversal, not a physical
  time reversal, without changing the hash-verified v1 evidence bundle.
- Made future reports derive the frame-order-reversal distance range and tolerance from their own
  result data instead of embedding v1 constants.
- Included the referenced protocols, evidence, bilingual documentation, and verification scripts in
  the source distribution.

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

[Unreleased]: https://github.com/AlbertXXuu/PhysGauge/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/AlbertXXuu/PhysGauge/releases/tag/v1.0.0
