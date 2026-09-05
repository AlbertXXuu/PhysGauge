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
four fresh seeded cases and 40 candidate trajectories in memory. Use `physgauge run --output ...`
for a durable evidence bundle.

The public second view is named **Learned-model study**. The expandable protocol identifier defines
`R2` as *research milestone 2*: learned-model validation after the R1 theoretical clarification.
The interface reports the frozen `inconclusive-model` result and model-capability classification
before showing visual metric disagreements.

The server accepts loopback hosts only. It serves the approved AlvenX masters and Instrument Sans
locally and sends a same-origin content security policy.

The README and Studio use the same pure wordmark with canvas alignment revision `2026-09-04.1`:
its visible outline is centered within the unchanged `330 × 100` canvas. The glyph and color
baseline remains `2026-08-22.4`, and the AX brand baseline remains `2026-08-24.1`. The original
project lockup is retained separately as `docs/assets/alvenx-lockup.svg`.

Header home-navigation revision `2026-09-04.1` makes the AlvenX logo a **Back to top**
button. It preserves the current evidence view, URL, history, configuration, and results;
reduced-motion preferences use an instant scroll. At narrow viewport widths, the two evidence
tabs move into the compact **Views** menu so the wordmark remains at its canonical `160px` width.

With Playwright CLI installed, maintainers can verify that behavior against an isolated local
Studio. The check runs two fresh seeded cases, switches evidence views, and verifies pointer,
Enter, and Space activation with normal and reduced motion:

```bash
playwright-cli open http://127.0.0.1:7871/
playwright-cli run-code --filename scripts/check_home_navigation.js
playwright-cli close
```
