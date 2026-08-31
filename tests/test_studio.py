import hashlib
import json
import struct
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen

from physgauge.studio import (
    INDEX_HTML,
    STUDIO_CSS,
    STUDIO_JS,
    StudioAddress,
    StudioHTTPServer,
    _validated_smoke_config,
    load_committed_evidence,
    run_smoke_calibration,
)


class StudioTests(unittest.TestCase):
    def test_committed_views_preserve_scientific_boundaries(self):
        evidence = load_committed_evidence()
        calibration = evidence["calibration"]
        study = evidence["learnedStudy"]

        self.assertEqual(calibration["caseCount"], 24)
        self.assertEqual(calibration["recordCount"], 240)
        self.assertTrue(calibration["oraclesValid"])
        response = calibration["severityResponse"]
        self.assertEqual(response["family"], "inelastic")
        self.assertEqual(response["aggregation"], "Mean over 24 seeded cases")
        self.assertEqual(
            [series["metric"] for series in response["series"]],
            ["mse", "ssim_error", "pixel_frechet", "temporal_gradient_mse"],
        )
        ssim = response["series"][1]
        self.assertEqual(
            [(point["severity"], point["value"]) for point in ssim["points"]],
            [
                (0.05, 0.004063380593280652),
                (0.2, 0.04446974082173242),
                (0.5, 0.1467203469417201),
            ],
        )
        self.assertEqual(study["outcome"], "inconclusive-model")
        self.assertEqual(study["classification"], "too-weak")
        self.assertEqual(study["seedCount"], 3)

    def test_packaged_fallback_matches_repository_evidence(self):
        self.assertEqual(load_committed_evidence(Path("missing")), load_committed_evidence())

    def test_smoke_calibration_runs_real_suite(self):
        view = run_smoke_calibration()

        self.assertEqual(view["caseCount"], 4)
        self.assertEqual(view["recordCount"], 40)
        self.assertTrue(view["oraclesValid"])
        self.assertTrue(view["violationsDetected"])

    def test_smoke_configuration_is_user_editable_but_bounded(self):
        self.assertEqual(_validated_smoke_config(12, 999_999), (12, 999_999))
        for cases, seed in ((0, 7), (13, 7), (4, -1), (True, 7), (4, "7")):
            with self.subTest(cases=cases, seed=seed), self.assertRaises(ValueError):
                _validated_smoke_config(cases, seed)

    def test_committed_viewport_audit_matches_screenshots(self):
        studio_assets = Path(__file__).parents[1] / "docs" / "assets" / "studio"
        audit = json.loads(
            (studio_assets / "viewport-audit.json").read_text(encoding="utf-8")
        )

        self.assertEqual(
            [view["width_px"] for view in audit["viewports"]],
            [900, 1024, 1280, 1440, 1600],
        )
        self.assertTrue(
            all(not view["horizontal_overflow"] for view in audit["viewports"])
        )
        self.assertTrue(
            all(
                view["minimum_critical_target_height_px"] >= 44
                for view in audit["viewports"]
            )
        )
        self.assertEqual(
            audit["severity_response"]["source"],
            "docs/evidence/v1.0.0/results.json",
        )
        self.assertFalse(audit["severity_response"]["intermediate_values_claimed"])
        self.assertEqual(audit["learned_study"]["outcome"], "inconclusive-model")

        for view in audit["viewports"]:
            screenshot = studio_assets / view["screenshot"]
            payload = screenshot.read_bytes()
            self.assertEqual(payload[:8], b"\x89PNG\r\n\x1a\n")
            width, height = struct.unpack(">II", payload[16:24])
            self.assertEqual(width, view["width_px"])
            self.assertEqual(height, view["screenshot_height_px"])
            self.assertEqual(
                hashlib.sha256(payload).hexdigest(), view["screenshot_sha256"]
            )

    def test_studio_uses_brand_tokens_and_secondary_r2_label(self):
        self.assertIn("rgb(255 255 255 / 28%)", STUDIO_CSS)
        self.assertIn("blur(24px)", STUDIO_CSS)
        self.assertIn("cubic-bezier(.22,1,.36,1)", STUDIO_CSS)
        self.assertIn('id="run-smoke"', INDEX_HTML)
        self.assertIn('aria-live="polite"', INDEX_HTML)
        self.assertIn("Calibrate a metric", INDEX_HTML)
        self.assertIn("4 seeded cases", INDEX_HTML)
        self.assertNotIn("R2", INDEX_HTML.split("Technical protocol identifier")[0])
        self.assertIn('role="tablist"', INDEX_HTML)
        self.assertIn('id="smoke-cases"', INDEX_HTML)
        self.assertIn('id="smoke-seed"', INDEX_HTML)
        self.assertIn("Studio v1.1.2 · Calibration evidence v1.0.0", INDEX_HTML)
        self.assertIn("Calibration evidence v1.0.0", INDEX_HTML)
        self.assertIn("R2 · research milestone", INDEX_HTML)
        self.assertIn("line-height:1.02", STUDIO_CSS)
        self.assertIn(
            "radial-gradient(circle at 12% 5%,rgb(147 197 253 / 42%),transparent 34%)",
            STUDIO_CSS,
        )
        self.assertIn("scroll-margin-top:112px", STUDIO_CSS)
        self.assertIn("matrix-cell value v${band}", STUDIO_JS)
        self.assertNotIn('style="--value:', STUDIO_JS)
        self.assertIn("location.hash==='#calibration-view'", STUDIO_JS)
        self.assertIn(".site-header{position:fixed", STUDIO_CSS)
        self.assertIn(".site-header{position:fixed;z-index:100", STUDIO_CSS)
        self.assertIn(".site-header nav{display:flex;gap:5px;margin-left:auto;padding:0", STUDIO_CSS)
        self.assertIn("width:calc(min(100%,1480px)", STUDIO_CSS)
        self.assertIn("0 24px 72px rgb(71 105 148 / 12%)", STUDIO_CSS)
        self.assertIn('id="response-plot"', INDEX_HTML)
        self.assertIn("Severity → metric response", INDEX_HTML)
        self.assertIn("renderResponse(d.severityResponse)", STUDIO_JS)
        self.assertIn("divided by its own observed maximum", STUDIO_JS)
        self.assertIn(".response-line.s3", STUDIO_CSS)
        self.assertNotIn('class="collision-field"', INDEX_HTML)
        self.assertNotIn("@keyframes blue-collision", STUDIO_CSS)
        self.assertIn("body{min-width:0}", STUDIO_CSS)
        self.assertIn("@media(max-width:1100px)", STUDIO_CSS)
        self.assertIn(".nav-button{min-height:44px", STUDIO_CSS)
        self.assertIn(".text-button{min-height:44px", STUDIO_CSS)

    def test_non_loopback_host_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "local-only"):
            StudioAddress("0.0.0.0", 7871).validate()

    def test_page_assets_and_evidence_are_served(self):
        server = StudioHTTPServer(StudioAddress(port=0))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with urlopen(f"{base}/", timeout=3) as response:  # noqa: S310 - loopback test
                self.assertEqual(response.status, 200)
                self.assertIn(b"Calibrate a metric", response.read())
            with urlopen(f"{base}/api/evidence", timeout=3) as response:  # noqa: S310
                payload = json.load(response)
                self.assertEqual(payload["calibration"]["caseCount"], 24)
            with urlopen(f"{base}/assets/monogram.svg", timeout=3) as response:  # noqa: S310
                self.assertEqual(response.headers["Content-Type"], "image/svg+xml")
                self.assertTrue(response.read().lstrip().startswith(b"<svg"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
