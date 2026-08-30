# PhysGauge v1.1.0 final release audit

- Status: **CANDIDATE — Linux CI required before PASS**
- Audit date: `2026-08-30` (`Asia/Shanghai`)
- Audited source commit: `cb0e7453d764b35ab35eb69e85fe6e9914547e7e`
- Target release: `v1.1.0`

## Release meaning

`v1.1.0` is the presentation and maintenance closure release built on the unchanged `v1.0.0`
research/evidence baseline. It adds the evidence-driven Studio presentation, shared AlvenX brand,
documentation, packaging, responsive/accessibility work, and explicit version identity. It does
not add a physics world, candidate, metric, model, experiment, or research conclusion. The R2
result remains `inconclusive-model`.

## Environment and method

The source commit was cloned into a separate local directory and audited with its source path
explicitly selected. Windows validation used Windows NT `10.0.26200.0`, PowerShell `7.6.4`, Python
`3.11.0`, NumPy `2.4.6`, Pillow `12.3.0`, and Chromium `151.0.7922.34`. Built distributions were
installed in two new isolated environments, one from the wheel and one from the source distribution.

Linux is not inferred from the Windows result. This audit remains a candidate until the complete
pull-request head passes the repository's GitHub Actions matrix on Ubuntu.

## Readiness checklist

| Surface | Result | Evidence |
| --- | --- | --- |
| Separate fresh clone | PASS | Clone HEAD exactly matched `cb0e7453d764b35ab35eb69e85fe6e9914547e7e`; worktree was clean before ignored build output. |
| Package/runtime identity | PASS | Project/import metadata, `physgauge --version`, Studio, README files, and changelog identify software `1.1.0`; calibration remains evidence `v1.0.0`, and R2 remains a research milestone. |
| Source distribution | PASS | Built and installed in a new environment with dependencies; metadata and CLI both reported `1.1.0`. |
| Wheel | PASS | Built and installed in a new environment; `pip check`, CLI identity, doctor, deterministic run, and frozen-bundle verification passed. |
| Windows/local tests | PASS | `34` unittest tests passed. Ruff passed. |
| Repository checker | PASS | Version `1.1.0` and `66` tracked files validated. |
| Deterministic evidence paths | PASS | Fresh installed-package run produced `240` passing records and four hash-verified artifacts; frozen v1 verification passed `240` records and R2 verification passed its four artifacts. |
| Linux CI | PENDING | Required on the complete `closure/v1.1.0` pull-request head before this audit may become PASS. |
| README / README.zh-CN | PASS | Both are present, coherent with the `1.1.0` candidate identity, and preserve the frozen calibration/reproduction boundary. |
| CHANGELOG / MAINTENANCE | PASS | `CHANGELOG.md` and `docs/MAINTENANCE.md` are present and define the bounded closure release plus maintenance-only follow-up. |
| PORTFOLIO | PASS | Problem, original decisions, difficult failure modes, results, negative R2 result, evidence limits, and individual contribution are recorded. |
| LICENSE / SECURITY / CITATION | PASS | `LICENSE`, `NOTICE`, `SECURITY.md`, and `CITATION.cff` are present and packaged where applicable. |
| Studio | PASS | Calibration and Learned study remain reachable; severity-response uses only frozen measured points; sensitivity matrix remains present; `inconclusive-model` remains the learned-study primary result. |
| Responsive/accessibility | PASS | Chromium at 900/1024/1280/1440/1600 px found no page overflow; critical targets are at least 44 px, keyboard focus is visible, and shared header geometry/styles match. |
| Version labels | PASS | `Studio v1.1.0`, `Calibration evidence v1.0.0`, and `R2 research milestone` are deliberately separate. |
| Evidence and documentation links | PASS | Repository-local links passed the checker; dated README/portfolio external links returned HTTP 200. |
| Historical v1 integrity | PASS | Annotated tag, peeled commit, and frozen evidence tree match the closure baseline below. |
| Website links | PASS with publication sequencing | `https://alvenx.com` and repository links return HTTP 200; the local production website candidate's project route and repository links passed its P9 browser audit and are deployed in P11. |
| OG/social | P2 accepted for P10 | GitHub currently generates a valid 1200×600 social card. The existing canonical AlvenX 1280×640 asset is used for publication-time repository metadata normalization; no new visual is required. |

## Distribution artifacts

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `physgauge-1.1.0-py3-none-any.whl` | 143,339 | `5d1455fb7cd53bf556abf25b02c164a0a914f023c0892439a9cb4da51bad49e7` |
| `physgauge-1.1.0.tar.gz` | 5,006,491 | `0e020923d41896cc87ecbe8d9958a2f9a5120a3accf711f4a737e5f2f334ee56` |

Archive inspection confirmed Python source, CLI entry point, LICENSE/NOTICE, and packaged Studio
brand/font/evidence assets. The source archive also contains all five Studio screenshots and their
viewport audit.

## Frozen v1.0.0 anchors

| Anchor | Expected and observed object ID |
| --- | --- |
| Annotated `refs/tags/v1.0.0` | `3ec0be0874b847022258c18688f1feddc99ccf85` |
| Peeled v1.0.0 commit | `53b84f49cfe44ef5d2c30247ec7d97dc795e9e00` |
| `docs/evidence/v1.0.0` tree | `416b3a3808bd1f3d509339c18439ab536bcc2f30` |

All expected IDs equal the objects reachable from the audited candidate. No historical ref,
calibration result, R2 result, or frozen evidence object changed.

## Findings and disposition

- **P0 blockers:** `0` locally; final count is contingent on Linux CI.
- **P1 blockers:** `0` locally; final count is contingent on Linux CI.
- **P2 accepted:** the old concept-hero selectors remain as unreachable declarations inside the
  existing minified CSS literal, but the corresponding DOM and animation are absent. Removing
  isolated tokens from that large generated-like literal immediately before release carries more
  regression risk than value and cannot affect runtime behavior.
- **P2 accepted:** sdist creation prints normal `MANIFEST.in` exclusions for bytecode and
  `__pycache__`; neither file class enters the archive.
- **P2 scheduled for publication metadata:** the current automatic GitHub social card is valid but
  is not the canonical 1280×640 AlvenX preview. P11 can upload the already-generated canonical
  asset without changing source or making a new claim.

## Gate decision

Local release readiness is **PASS**. Overall P10 readiness remains **PENDING** until the exact
pull-request head passes every Linux CI job. No tag or release may be created from this candidate
before that evidence exists.
