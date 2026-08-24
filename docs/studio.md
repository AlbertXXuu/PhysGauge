# PhysGauge Studio

PhysGauge Studio is a local visual surface for two existing evidence sets:

1. the deterministic v1 metric calibration;
2. the preregistered learned-model study.

```bash
python -m pip install -e .
physgauge studio
```

The interface opens at `http://127.0.0.1:7871/`. Use `--no-open` to select a browser yourself, or
`--port 0` to ask the operating system for a free loopback port.

The initial calibration view reads the committed evidence bundle and displays the state-grounded
detection rate beside each visual metric's low-sensitivity rate. **Run local smoke check** evaluates
four fresh seeded cases and 40 candidate trajectories in memory. It does not modify a committed
bundle; use `physgauge run --output ...` for durable evidence.

The public second view is named **Learned-model study**. The term `R2` is preserved only in the
expandable protocol identifier because it means *research milestone 2*: learned-model validation
after the R1 theoretical clarification. It is not a product version. The interface reports the
frozen `inconclusive-model` result and the failed model-capability gate before showing any visual
metric disagreement.

The server accepts loopback hosts only. It serves the approved AlvenX masters and Instrument Sans
locally, sends a same-origin content security policy, and does not use telemetry or network APIs.
