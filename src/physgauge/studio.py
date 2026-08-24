"""Loopback-only visual interface for PhysGauge calibration evidence."""

from __future__ import annotations

import hashlib
import json
import threading
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any

from .experiment import SuiteConfig, run_suite

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
DEFAULT_PORT = 7871
ASSET_SHA256 = {
    "assets/brand/alvenx-wordmark.svg": "8ae10e02c27091e29e0191a7934506118f144aae11898b20222d7f9d587e2662",
    "assets/brand/alvenx-monogram.svg": "45367ec933c2ed8565cdf9e683fd4b856057d375435b46c62acb4fbb2cbeef16",
    "assets/fonts/InstrumentSans-wdth-wght.woff2": "aa72922aafcc0dc18f36ec1d805b0212057dabe8b9d5b8b57f67035aea1b826d",
}
METRICS = ("mse", "ssim_error", "pixel_frechet", "temporal_gradient_mse")
METRIC_LABELS = {
    "mse": "MSE",
    "ssim_error": "SSIM error",
    "pixel_frechet": "Pixel Fréchet",
    "temporal_gradient_mse": "Temporal Δ",
}


@dataclass(frozen=True)
class StudioAddress:
    host: str = "127.0.0.1"
    port: int = DEFAULT_PORT

    def validate(self) -> None:
        if self.host not in LOOPBACK_HOSTS:
            raise ValueError("Studio is local-only; --host must be a loopback address")
        if not 0 <= self.port <= 65535:
            raise ValueError("--port must be between 0 and 65535")


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _calibration_view(result: dict[str, Any], *, source: str) -> dict[str, Any]:
    summary = result["summary"]
    candidates = summary["candidates"]
    rows: list[dict[str, Any]] = []
    for name, entry in candidates.items():
        if name in {"correct", "random"}:
            continue
        rows.append(
            {
                "name": name,
                "family": entry["family"],
                "violation": entry["expected_violation"],
                "physicsDetection": float(entry["physics_detection_rate"]),
                "lowSensitivity": {
                    metric: float(entry["low_sensitivity_rate"][metric])
                    for metric in METRICS
                },
            }
        )
    return {
        "source": source,
        "protocol": result["protocol_id"],
        "caseCount": int(result["config"]["cases"]),
        "recordCount": int(summary["record_count"]),
        "candidateCount": int(summary["candidate_count"]),
        "oraclesValid": bool(summary["all_oracles_validated"]),
        "violationsDetected": bool(summary["all_expected_violations_detected"]),
        "metricLabels": METRIC_LABELS,
        "rows": rows,
    }


def _learned_study_view(result: dict[str, Any]) -> dict[str, Any]:
    summary = result["summary"]
    decision = summary["decision"]
    seeds: list[dict[str, Any]] = []
    for seed, assessment in decision["seed_assessments"].items():
        candidate = summary["candidates"][f"learned-seed-{seed}"]
        seeds.append(
            {
                "seed": int(seed),
                "classification": assessment["classification"],
                "partialErrorRate": float(assessment["partial_error_rate"]),
                "collisionAccuracy": float(candidate["collision_event_accuracy"]),
                "positionRmse": float(candidate["median_position_rmse"]),
            }
        )
    across = summary["across_model_seeds"]
    return {
        "protocol": result["protocol_id"],
        "outcome": decision["outcome"],
        "classification": decision["consensus_classification"],
        "dryRunValid": bool(decision["dry_run_valid"]),
        "experimentValid": bool(decision["experiment_valid"]),
        "seedCount": int(across["seed_count"]),
        "partialErrorMean": float(across["metrics"]["partial_error_rate"]["mean"]),
        "collisionAccuracyMean": float(
            across["metrics"]["collision_event_accuracy"]["mean"]
        ),
        "seeds": seeds,
    }


def load_committed_evidence(root: Path | None = None) -> dict[str, Any]:
    repo = root or _repository_root()
    v1_path = repo / "docs/evidence/v1.0.0/results.json"
    learned_path = repo / "docs/evidence/r2/results.json"
    if not v1_path.is_file() or not learned_path.is_file():
        return json.loads(
            files("physgauge")
            .joinpath("assets/evidence/studio-v1.json")
            .read_text(encoding="utf-8")
        )
    v1 = json.loads(
        v1_path.read_text(encoding="utf-8")
    )
    learned = json.loads(
        learned_path.read_text(encoding="utf-8")
    )
    return {
        "calibration": _calibration_view(v1, source="Committed v1 evidence"),
        "learnedStudy": _learned_study_view(learned),
    }


def _asset_bytes(relative: str) -> bytes:
    payload = files("physgauge").joinpath(relative).read_bytes()
    if hashlib.sha256(payload).hexdigest() != ASSET_SHA256[relative]:
        raise RuntimeError(f"bundled AlvenX asset failed integrity check: {relative}")
    return payload


def _validated_smoke_config(cases: object, seed: object) -> tuple[int, int]:
    if isinstance(cases, bool) or not isinstance(cases, int) or not 1 <= cases <= 12:
        raise ValueError("cases must be an integer from 1 to 12")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 999_999:
        raise ValueError("seed must be an integer from 0 to 999999")
    return cases, seed


def run_smoke_calibration(*, cases: int = 4, seed: int = 7) -> dict[str, Any]:
    cases, seed = _validated_smoke_config(cases, seed)
    result = run_suite(SuiteConfig(cases=cases, frames=16, seed=seed))
    return _calibration_view(result, source="Fresh local smoke check")


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="color-scheme" content="light">
  <meta name="theme-color" content="#EEF6FF">
  <title>PhysGauge · AlvenX</title>
  <link rel="icon" href="/assets/monogram.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/studio.css">
  <script src="/studio.js" defer></script>
</head>
<body>
  <div class="page-frame">
    <header class="site-header liquid-surface">
      <a class="brand-link" href="#top" aria-label="PhysGauge home">
        <img src="/assets/wordmark.svg" alt="AlvenX">
      </a>
      <nav aria-label="Evidence views" role="tablist">
        <button class="nav-button active" id="calibration-tab" type="button" role="tab"
          aria-controls="calibration-view" aria-selected="true" data-view="calibration">Calibration</button>
        <button class="nav-button" id="learned-tab" type="button" role="tab"
          aria-controls="learned-view" aria-selected="false" data-view="learned">Learned-model study</button>
      </nav>
      <span class="local-badge"><i aria-hidden="true"></i>Local only</span>
    </header>

    <main id="top">
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow"><span></span>PHYSICS EVIDENCE · METRIC CALIBRATION</p>
          <h1>Test a metric<br><em>before trusting it.</em></h1>
          <p class="lede">Inject known violations into an analytically verified collision world,
            compare visual similarity with state-grounded checks, and expose the cases a metric
            treats as harmless.</p>
          <div class="hero-actions">
            <button class="liquid-button" id="run-smoke" type="button">
              <span>Run local smoke check</span><b aria-hidden="true">↗</b>
            </button>
            <label class="smoke-control" for="smoke-cases"><span>Cases</span>
              <select id="smoke-cases" aria-describedby="run-status">
                <option value="2">2</option><option value="4" selected>4</option>
                <option value="8">8</option><option value="12">12</option>
              </select>
            </label>
            <label class="smoke-control seed-control" for="smoke-seed"><span>Seed</span>
              <input id="smoke-seed" type="number" min="0" max="999999" step="1" value="7"
                inputmode="numeric" aria-describedby="run-status">
            </label>
            <button class="text-button" type="button" data-view="learned">Open learned-model study ↓</button>
          </div>
          <p class="run-status" id="run-status" role="status" aria-live="polite">
            CPU only · no API key · no model download · no evidence files changed
          </p>
        </div>
        <aside class="hero-visual" aria-label="Metric and physics comparison">
          <div class="visual-label"><span>ORACLE</span><strong id="oracle-status">Validated</strong></div>
          <div class="collision-field" aria-hidden="true">
            <span class="track one"></span><span class="track two"></span>
            <i class="disc blue"></i><i class="disc violet"></i><b class="contact"></b>
          </div>
          <div class="visual-scale"><span>pixel similarity</span><i></i><span>physical validity</span></div>
        </aside>
      </section>

      <section class="view-panel active" id="calibration-view" data-panel="calibration"
        role="tabpanel" aria-labelledby="calibration-tab" tabindex="-1">
        <header class="section-heading">
          <div><p class="eyebrow">FROZEN V1 CALIBRATION</p><h2>Known errors. Measured sensitivity.</h2></div>
          <code id="calibration-protocol">loading protocol…</code>
        </header>
        <div class="metric-grid">
          <article><strong id="metric-cases">—</strong><span>seeded collision cases</span></article>
          <article><strong id="metric-candidates">—</strong><span>candidate trajectories</span></article>
          <article><strong id="metric-records">—</strong><span>measured records</span></article>
          <article><strong id="metric-oracles">—</strong><span>oracle contracts</span></article>
        </div>
        <div class="matrix-wrap">
          <header><div><p class="eyebrow">LOW-SENSITIVITY MATRIX</p><h3>When physics fails but a visual metric barely reacts.</h3></div><span id="calibration-source">Committed v1 evidence</span></header>
          <div class="matrix" id="sensitivity-matrix"><p>Loading evidence…</p></div>
        </div>
      </section>

      <section class="view-panel" id="learned-view" data-panel="learned"
        role="tabpanel" aria-labelledby="learned-tab" tabindex="-1" hidden>
        <header class="section-heading">
          <div><p class="eyebrow">LEARNED-MODEL STUDY</p><h2>An honest inconclusive result.</h2></div>
          <span class="outcome-pill">Model capability gate failed</span>
        </header>
        <div class="study-summary">
          <article class="study-callout">
            <span>RESULT</span><strong id="study-outcome">Inconclusive</strong>
            <p>All predictors saw collisions in training, but none generalized inside the
              preregistered target-error band. Visual disagreements are therefore not promoted
              to a learned-model blind-spot claim.</p>
          </article>
          <div class="study-metrics">
            <article><span>Mean partial-error rate</span><strong id="study-error">—</strong></article>
            <article><span>Mean collision accuracy</span><strong id="study-collision">—</strong></article>
            <article><span>Training seeds</span><strong id="study-seeds">—</strong></article>
          </div>
        </div>
        <div class="seed-grid" id="seed-grid"></div>
        <details class="protocol-details">
          <summary>Technical protocol identifier</summary>
          <code id="learned-protocol">—</code>
          <p><strong>Why it contains R2:</strong> R2 means research milestone 2—learned-model
            validation after the R1 theoretical clarification. It is not the PhysGauge product
            version and is intentionally secondary in this interface.</p>
        </details>
      </section>
    </main>
    <footer><img src="/assets/monogram.svg" alt=""><span>PhysGauge · AlvenX open source</span></footer>
  </div>
</body>
</html>
"""


STUDIO_CSS = r"""@font-face{font-family:"Instrument Sans";src:url("/assets/font.woff2") format("woff2");font-style:normal;font-weight:400 700;font-display:swap}
:root{color-scheme:light;--canvas:#eef6ff;--primary:#0b1731;--reading:#334155;--muted:#52647a;--blue:#2563eb;--indigo:#4f46e5;--violet:#7c3aed;--glass:rgb(255 255 255 / 28%);--glass-hover:rgb(255 255 255 / 35%);--edge:rgb(255 255 255 / 68%);--highlight:rgb(255 255 255 / 72%);--ease:cubic-bezier(.22,1,.36,1)}
*{box-sizing:border-box}html{scroll-behavior:smooth;background:var(--canvas)}body{margin:0;min-width:320px;background:radial-gradient(circle at 12% 2%,#fff 0,transparent 35%),radial-gradient(circle at 90% 11%,rgb(204 218 255 / 58%),transparent 33%),linear-gradient(145deg,#fbfdff 0%,#f1f7ff 49%,#e7f1ff 100%);color:var(--primary);font-family:"Instrument Sans",Arial,sans-serif;text-rendering:optimizeLegibility}.page-frame{width:min(100%,1480px);margin:auto;padding:clamp(18px,3vw,44px) clamp(18px,5vw,74px) 30px}.site-header{position:sticky;z-index:10;top:14px;display:flex;min-height:70px;align-items:center;gap:28px;padding:12px 18px 12px 22px;border-radius:26px}.liquid-surface{border:1px solid var(--edge);background:rgb(255 255 255 / 26%);box-shadow:inset 0 1px 0 var(--highlight),inset 0 -1px 0 rgb(79 70 229 / 6%),0 24px 72px rgb(71 105 148 / 11%);-webkit-backdrop-filter:blur(18px) saturate(148%);backdrop-filter:blur(18px) saturate(148%)}.brand-link{display:flex;width:160px;border-radius:12px}.brand-link img{display:block;width:100%}.site-header nav{display:flex;gap:5px;margin-left:auto;padding:4px;border-radius:999px;background:rgb(255 255 255 / 28%)}.nav-button{padding:9px 13px;border:0;border-radius:999px;background:transparent;color:var(--muted);font:620 .73rem/1 "Instrument Sans";letter-spacing:.07em;text-transform:uppercase;cursor:pointer;transition:300ms var(--ease)}.nav-button.active,.nav-button:hover{background:rgb(255 255 255 / 72%);color:var(--primary);box-shadow:0 8px 20px rgb(71 105 148 / 8%)}.local-badge{display:flex;align-items:center;gap:8px;padding:9px 12px;border-radius:999px;background:rgb(255 255 255 / 42%);color:#315a88;font-size:.74rem;font-weight:620}.local-badge i{width:7px;height:7px;border-radius:50%;background:var(--blue);box-shadow:0 0 12px rgb(37 99 235 / 35%)}.hero{display:grid;min-height:min(760px,calc(100vh - 104px));grid-template-columns:minmax(0,1.35fr) minmax(340px,.65fr);align-items:center;gap:clamp(50px,7vw,110px);padding:clamp(80px,11vh,140px) 0}.eyebrow{margin:0 0 24px;color:#315a88;font-size:.76rem;font-weight:650;letter-spacing:.13em;text-transform:uppercase}.hero .eyebrow{display:flex;align-items:center;gap:10px}.hero .eyebrow span{width:7px;height:7px;border-radius:50%;background:var(--blue)}h1,h2,h3,p{font-variation-settings:"wdth" 100}.hero h1{margin:0;font-size:clamp(3.3rem,6.7vw,7rem);font-weight:570;letter-spacing:-.04em;line-height:.95}.hero h1 em{display:block;margin-top:.14em;background:linear-gradient(100deg,var(--blue),var(--indigo) 48%,var(--violet));background-clip:text;-webkit-background-clip:text;color:transparent;font-style:normal}.lede{max-width:700px;margin:36px 0 0;color:var(--reading);font-size:clamp(1.02rem,1.45vw,1.25rem);line-height:1.7}.hero-actions{display:flex;align-items:center;flex-wrap:wrap;gap:24px;margin-top:40px}.liquid-button{position:relative;display:inline-flex;min-height:58px;align-items:center;gap:14px;padding:0 25px 0 27px;overflow:hidden;border:1px solid var(--edge);border-radius:999px;outline:0;background-color:var(--glass);background-image:radial-gradient(circle at 24% -12%,rgb(255 255 255 / 76%),transparent 43%),linear-gradient(118deg,rgb(255 255 255 / 18%),transparent 58%,rgb(255 255 255 / 12%));box-shadow:inset 0 1px 0 var(--highlight),inset 0 -1px 0 rgb(79 70 229 / 8%),0 24px 72px rgb(71 105 148 / 14%);-webkit-backdrop-filter:blur(24px) saturate(148%);backdrop-filter:blur(24px) saturate(148%);color:var(--primary);font:620 .98rem/1 "Instrument Sans";cursor:pointer;transition:420ms var(--ease)}.liquid-button::before{content:"";position:absolute;inset:-2px auto -2px -45%;width:40%;background:linear-gradient(105deg,transparent 22%,rgb(255 255 255 / 58%) 49%,transparent 70%);transform:skewX(-16deg);transition:transform 620ms var(--ease)}.liquid-button:hover{border-color:rgb(255 255 255 / 84%);background-color:var(--glass-hover);transform:translateY(-3px);box-shadow:inset 0 1px 0 rgb(255 255 255 / 80%),0 30px 80px rgb(71 105 148 / 17%)}.liquid-button:hover::before{transform:translateX(380%) skewX(-16deg)}.liquid-button:active{transform:translateY(-1px) scale(.985)}.liquid-button:focus-visible,.text-button:focus-visible,.nav-button:focus-visible,a:focus-visible{outline:3px solid rgb(37 99 235 / 45%);outline-offset:4px}.liquid-button:disabled{cursor:wait;opacity:.62;transform:none}.text-button{border:0;background:transparent;color:var(--reading);font:600 .98rem "Instrument Sans";cursor:pointer}.run-status{min-height:1.5em;margin:18px 0 0;color:var(--muted);font-size:.82rem}.hero-visual{padding:30px;border:1px solid rgb(255 255 255 / 82%);border-radius:32px;background:rgb(255 255 255 / 48%);box-shadow:inset 0 1px 0 #fff,0 30px 90px rgb(71 105 148 / 12%)}.visual-label{display:flex;justify-content:space-between;color:#315a88;font-size:.72rem;font-weight:650;letter-spacing:.1em}.visual-label strong{padding:7px 10px;border-radius:999px;background:#edfdf5;color:#18744b;letter-spacing:0}.collision-field{position:relative;min-height:260px;margin:24px 0;overflow:hidden;border-radius:20px;background:linear-gradient(145deg,rgb(255 255 255 / 45%),rgb(219 231 255 / 48%))}.track{position:absolute;top:50%;height:1px;background:rgb(79 70 229 / 18%);transform-origin:center}.track.one{left:8%;width:84%;transform:rotate(20deg)}.track.two{left:9%;width:82%;transform:rotate(-20deg)}.disc{position:absolute;top:50%;width:74px;aspect-ratio:1;border-radius:50%;transform:translateY(-50%)}.disc.blue{left:19%;background:radial-gradient(circle at 28% 22%,#93c5fd,var(--blue) 62%,var(--indigo));box-shadow:0 18px 40px rgb(37 99 235 / 22%)}.disc.violet{right:19%;background:radial-gradient(circle at 28% 22%,#c4b5fd,var(--violet) 68%,#4c1d95);box-shadow:0 18px 40px rgb(124 58 237 / 22%)}.contact{position:absolute;top:50%;left:50%;width:17px;height:17px;border:2px solid rgb(79 70 229 / 35%);border-radius:50%;transform:translate(-50%,-50%);box-shadow:0 0 28px rgb(79 70 229 / 28%)}.visual-scale{display:flex;align-items:center;gap:12px;color:var(--muted);font-size:.7rem}.visual-scale i{height:2px;flex:1;background:linear-gradient(90deg,var(--blue),var(--violet))}.view-panel{padding:clamp(70px,9vw,126px) 0}.view-panel[hidden]{display:none}.section-heading{display:flex;align-items:flex-end;justify-content:space-between;gap:30px;margin-bottom:38px}.section-heading .eyebrow{margin-bottom:12px}.section-heading h2{max-width:790px;margin:0;font-size:clamp(2.1rem,4.2vw,4.5rem);font-weight:560;letter-spacing:-.035em;line-height:1.02}.section-heading code{max-width:360px;padding:9px 12px;border-radius:10px;background:rgb(255 255 255 / 42%);color:var(--muted);font-size:.72rem;overflow-wrap:anywhere}.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid rgb(71 105 148 / 18%);border-bottom:1px solid rgb(71 105 148 / 18%)}.metric-grid article{min-height:165px;padding:30px 26px;border-right:1px solid rgb(71 105 148 / 18%)}.metric-grid article:last-child{border:0}.metric-grid strong{display:block;font-size:clamp(2.5rem,4vw,4.3rem);font-weight:560;letter-spacing:-.04em}.metric-grid span{color:var(--muted);font-size:.88rem}.matrix-wrap{margin-top:80px;padding:clamp(22px,3vw,38px);border:1px solid rgb(255 255 255 / 78%);border-radius:28px;background:rgb(255 255 255 / 46%);box-shadow:inset 0 1px 0 #fff,0 16px 48px rgb(71 105 148 / 8%);overflow:hidden}.matrix-wrap>header{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;margin-bottom:28px}.matrix-wrap .eyebrow{margin-bottom:8px}.matrix-wrap h3{margin:0;font-size:clamp(1.35rem,2.3vw,2.1rem);font-weight:570}.matrix-wrap>header>span{color:var(--muted);font-size:.76rem}.matrix{display:grid;grid-template-columns:minmax(175px,1.35fr) repeat(5,minmax(90px,1fr));overflow:auto}.matrix-cell{min-height:58px;padding:14px 12px;border-top:1px solid rgb(71 105 148 / 12%);display:flex;align-items:center}.matrix-cell.heading{min-height:44px;border:0;color:var(--muted);font-size:.69rem;font-weight:650;letter-spacing:.06em;text-transform:uppercase}.matrix-cell.name{font-size:.78rem;font-weight:620}.matrix-cell.value{justify-content:center;margin:4px;border:0;border-radius:12px;background:color-mix(in srgb,var(--violet) calc(var(--value)*16%),white);font-size:.78rem;font-weight:650}.outcome-pill{padding:9px 12px;border-radius:999px;background:#fff7ed;color:#9a3412;font-size:.76rem;font-weight:650}.study-summary{display:grid;grid-template-columns:1.2fr .8fr;gap:18px}.study-callout,.study-metrics article,.seed-card{border:1px solid rgb(255 255 255 / 78%);background:rgb(255 255 255 / 46%);box-shadow:inset 0 1px 0 #fff,0 16px 48px rgb(71 105 148 / 8%)}.study-callout{padding:clamp(28px,4vw,54px);border-radius:28px}.study-callout>span{color:#9a3412;font-size:.72rem;font-weight:700;letter-spacing:.1em}.study-callout>strong{display:block;margin-top:20px;font-size:clamp(2.5rem,5vw,5.5rem);font-weight:560;letter-spacing:-.045em}.study-callout p{max-width:690px;margin:28px 0 0;color:var(--reading);line-height:1.7}.study-metrics{display:grid;gap:12px}.study-metrics article{display:flex;align-items:center;justify-content:space-between;padding:24px;border-radius:20px}.study-metrics span{max-width:130px;color:var(--muted);font-size:.8rem}.study-metrics strong{font-size:1.7rem;font-weight:570}.seed-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:18px}.seed-card{padding:24px;border-radius:22px}.seed-card>span{color:#315a88;font-size:.72rem;font-weight:650;letter-spacing:.08em}.seed-card h3{margin:36px 0 22px;font-size:1.5rem}.seed-facts{display:grid;gap:10px}.seed-facts div{display:flex;justify-content:space-between;padding-top:10px;border-top:1px solid rgb(71 105 148 / 12%);color:var(--muted);font-size:.76rem}.seed-facts strong{color:var(--primary)}.protocol-details{margin-top:22px;padding:20px 24px;border-radius:20px;background:rgb(255 255 255 / 40%);color:var(--reading)}.protocol-details summary{cursor:pointer;font-weight:620}.protocol-details code{display:block;margin-top:16px;overflow-wrap:anywhere}.protocol-details p{max-width:800px;line-height:1.65}footer{display:flex;align-items:center;gap:14px;padding:24px 0;color:var(--muted);font-size:.78rem}footer img{width:34px;height:34px;border-radius:9px}
@media(max-width:930px){.site-header nav{display:none}.hero{grid-template-columns:1fr;min-height:auto;padding-block:100px}.hero-visual{width:min(100%,560px)}.metric-grid{grid-template-columns:repeat(2,1fr)}.metric-grid article:nth-child(2){border-right:0}.metric-grid article:nth-child(-n+2){border-bottom:1px solid rgb(71 105 148 / 18%)}.section-heading,.matrix-wrap>header{align-items:flex-start;flex-direction:column}.study-summary{grid-template-columns:1fr}.seed-grid{grid-template-columns:1fr}}
@media(max-width:560px){.page-frame{padding-inline:14px}.site-header{top:8px;min-height:62px;border-radius:22px}.brand-link{width:132px}.local-badge{margin-left:auto;padding:8px 10px}.hero{padding-block:76px}.hero h1{font-size:clamp(2.9rem,14vw,4.3rem)}.hero-actions{align-items:flex-start;flex-direction:column}.metric-grid article{min-height:125px;padding:22px 16px}.matrix{grid-template-columns:minmax(150px,1.3fr) repeat(5,90px)}.study-callout{padding:28px 22px}}
body{line-height:1.62}.hero h1{overflow:visible;line-height:1.02}.hero h1 em{margin-top:.12em;padding-bottom:.08em}.hero-actions{gap:18px}.smoke-control{display:grid;gap:5px;color:var(--muted);font-size:.72rem;font-weight:620}.smoke-control select,.smoke-control input{min-height:44px;padding:0 12px;border:1px solid rgb(71 105 148 / 18%);border-radius:14px;background:rgb(255 255 255 / 68%);color:var(--primary);font:600 .86rem/1.55 "Instrument Sans",sans-serif}.smoke-control select{min-width:82px}.smoke-control input{width:104px}.smoke-control select:focus-visible,.smoke-control input:focus-visible{outline:3px solid rgb(37 99 235 / 45%);outline-offset:3px}.view-panel{scroll-margin-top:112px;opacity:1;transform:translateY(0);transition:opacity 420ms var(--ease),transform 420ms var(--ease)}.view-panel.view-enter{opacity:0;transform:translateY(14px)}.metric-grid{border:1px solid rgb(71 105 148 / 18%)}.metric-grid article:last-child{border-right:0}
.matrix-cell.value.v0{--value:0}.matrix-cell.value.v1{--value:.1}.matrix-cell.value.v2{--value:.2}.matrix-cell.value.v3{--value:.3}.matrix-cell.value.v4{--value:.4}.matrix-cell.value.v5{--value:.5}.matrix-cell.value.v6{--value:.6}.matrix-cell.value.v7{--value:.7}.matrix-cell.value.v8{--value:.8}.matrix-cell.value.v9{--value:.9}.matrix-cell.value.v10{--value:1}
@media(max-width:930px){.site-header nav{display:flex}.local-badge{display:none}}
@media(max-width:560px){.site-header{flex-wrap:wrap;padding:10px 12px}.brand-link{width:112px}.site-header nav{order:3;width:100%;justify-content:center;margin:0}.nav-button{padding:8px 10px;font-size:.66rem}.view-panel{scroll-margin-top:150px}}
body{background:radial-gradient(circle at 12% 5%,rgb(147 197 253 / 42%),transparent 34%),radial-gradient(circle at 84% 7%,rgb(167 139 250 / 28%),transparent 36%),radial-gradient(circle at 68% 88%,rgb(79 70 229 / 14%),transparent 38%),linear-gradient(145deg,#fbfdff 0%,#f1f7ff 49%,#e7f1ff 100%);background-attachment:fixed}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.liquid-button,.liquid-button::before,.nav-button{transition:none}}
"""


STUDIO_JS = r"""const $=s=>document.querySelector(s),$$=s=>document.querySelectorAll(s),pct=v=>`${Math.round(v*100)}%`;
function show(name,{scroll=true,updateHash=true}={}){const target=$(`#${name}-view`);if(!target)return;$$('[data-panel]').forEach(panel=>{const active=panel===target;panel.hidden=!active;panel.classList.toggle('active',active);if(active){panel.classList.add('view-enter');requestAnimationFrame(()=>requestAnimationFrame(()=>panel.classList.remove('view-enter')));}});$$('[role="tab"][data-view]').forEach(button=>{const active=button.dataset.view===name;button.classList.toggle('active',active);button.setAttribute('aria-selected',String(active));});if(updateHash)history.replaceState(null,'',`#${name}-view`);if(scroll)target.scrollIntoView({behavior:'smooth',block:'start'});}
function valueCell(v){const band=Math.max(0,Math.min(10,Math.round(v*10)));return `<div class="matrix-cell value v${band}">${pct(v)}</div>`;}
function renderCalibration(d){$('#metric-cases').textContent=d.caseCount;$('#metric-candidates').textContent=d.candidateCount;$('#metric-records').textContent=d.recordCount;$('#metric-oracles').textContent=d.oraclesValid&&d.violationsDetected?'100%':'Check';$('#calibration-protocol').textContent=d.protocol;$('#calibration-source').textContent=d.source;const headers=['Candidate','Physics caught',...Object.values(d.metricLabels)];let html=headers.map(h=>`<div class="matrix-cell heading">${h}</div>`).join('');for(const row of d.rows){html+=`<div class="matrix-cell name">${row.name}</div>${valueCell(row.physicsDetection)}`;for(const key of Object.keys(d.metricLabels)){html+=valueCell(row.lowSensitivity[key]);}}$('#sensitivity-matrix').innerHTML=html;}
function renderStudy(d){$('#study-outcome').textContent=d.outcome==='inconclusive-model'?'Inconclusive':'Review result';$('#study-error').textContent=pct(d.partialErrorMean);$('#study-collision').textContent=pct(d.collisionAccuracyMean);$('#study-seeds').textContent=d.seedCount;$('#learned-protocol').textContent=d.protocol;$('#seed-grid').innerHTML=d.seeds.map(s=>`<article class="seed-card"><span>SEED ${s.seed}</span><h3>${s.classification}</h3><div class="seed-facts"><div><span>Partial-error rate</span><strong>${pct(s.partialErrorRate)}</strong></div><div><span>Collision accuracy</span><strong>${pct(s.collisionAccuracy)}</strong></div><div><span>Median position RMSE</span><strong>${s.positionRmse.toFixed(4)}</strong></div></div></article>`).join('');}
async function load(){const response=await fetch('/api/evidence');if(!response.ok)throw new Error('Evidence unavailable');const data=await response.json();renderCalibration(data.calibration);renderStudy(data.learnedStudy);}
async function run(){const button=$('#run-smoke'),status=$('#run-status'),cases=Number($('#smoke-cases').value),seed=Number($('#smoke-seed').value);button.disabled=true;status.textContent=`Running ${cases} seeded cases and ${cases*10} candidate trajectories…`;try{const response=await fetch('/api/smoke',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cases,seed})});const data=await response.json();if(!response.ok)throw new Error(data.error||'Smoke check failed');renderCalibration(data);status.textContent=`PASS · ${data.recordCount} fresh records · seed ${seed} · all oracle contracts and injected violations verified`;$('#oracle-status').textContent='Fresh pass';show('calibration');}catch(error){status.textContent=`Unable to run: ${error.message}`;}finally{button.disabled=false;}}
window.addEventListener('DOMContentLoaded',()=>{load().catch(error=>{$('#run-status').textContent=error.message});const initial=location.hash==='#learned-view'?'learned':'calibration';show(initial,{scroll:false,updateHash:false});$$('[data-view]').forEach(button=>button.addEventListener('click',()=>show(button.dataset.view)));window.addEventListener('hashchange',()=>{if(location.hash==='#learned-view'||location.hash==='#calibration-view')show(location.hash==='#learned-view'?'learned':'calibration',{scroll:true,updateHash:false});});$('#run-smoke').addEventListener('click',run);});
"""


class _StudioHandler(BaseHTTPRequestHandler):
    server: StudioHTTPServer

    def log_message(self, format: str, *args: object) -> None:
        del format, args

    def _send(self, payload: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self'; font-src 'self'; "
            "style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, value: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self._send(payload, "application/json; charset=utf-8", status)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        routes = {
            "/": (INDEX_HTML.encode(), "text/html; charset=utf-8"),
            "/studio.css": (STUDIO_CSS.encode(), "text/css; charset=utf-8"),
            "/studio.js": (STUDIO_JS.encode(), "text/javascript; charset=utf-8"),
        }
        if self.path in routes:
            self._send(*routes[self.path])
            return
        assets = {
            "/assets/wordmark.svg": ("assets/brand/alvenx-wordmark.svg", "image/svg+xml"),
            "/assets/monogram.svg": ("assets/brand/alvenx-monogram.svg", "image/svg+xml"),
            "/assets/font.woff2": ("assets/fonts/InstrumentSans-wdth-wght.woff2", "font/woff2"),
        }
        if self.path in assets:
            relative, content_type = assets[self.path]
            self._send(_asset_bytes(relative), content_type)
            return
        if self.path == "/api/evidence":
            self._json(self.server.committed_evidence)
            return
        self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path != "/api/smoke":
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= 1_024:
                raise ValueError("request body is too large")
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            cases, seed = _validated_smoke_config(
                payload.get("cases", 4), payload.get("seed", 7)
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if not self.server.run_lock.acquire(blocking=False):
            self._json({"error": "a smoke check is already running"}, HTTPStatus.CONFLICT)
            return
        try:
            self._json(run_smoke_calibration(cases=cases, seed=seed))
        except Exception as exc:  # UI boundary: return a concise local error.
            self._json({"error": " ".join(str(exc).split())[:500]}, HTTPStatus.INTERNAL_SERVER_ERROR)
        finally:
            self.server.run_lock.release()


class StudioHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: StudioAddress, root: Path | None = None) -> None:
        address.validate()
        self.committed_evidence = load_committed_evidence(root)
        self.run_lock = threading.Lock()
        super().__init__((address.host, address.port), _StudioHandler)


def serve_studio(
    *, host: str = "127.0.0.1", port: int = DEFAULT_PORT, open_browser: bool = True
) -> int:
    server = StudioHTTPServer(StudioAddress(host, port))
    actual_port = int(server.server_address[1])
    display_host = "127.0.0.1" if host == "::1" else host
    url = f"http://{display_host}:{actual_port}/"
    print(f"PhysGauge Studio: {url}")
    print("Local-only interface. Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
