# Contributing

PhysGauge accepts changes that add a falsifiable metric test, fix a correctness issue, or improve
reproducibility without expanding the maintenance surface unnecessarily.

Before opening a pull request:

```bash
python -m pip install -e ".[dev]"
ruff check .
python -m unittest discover -s tests -v
python scripts/check_repository.py
python scripts/build_evidence.py --verify
python -m build
```

A new corruption must name its expected physical violation, provide at least two strengths when
monotonicity is meaningful, and include a test that would fail if the oracle or diagnosis regressed.
A new metric must state whether it preserves time order and must not reuse a standard metric name
for a proxy implementation.

Do not commit model weights, generated `runs/`, virtual environments, caches, or secrets. Please use
GitHub Issues for bugs and narrowly scoped proposals.
