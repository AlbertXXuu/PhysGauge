import json
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

    def test_studio_uses_brand_tokens_and_secondary_r2_label(self):
        self.assertIn("rgb(255 255 255 / 28%)", STUDIO_CSS)
        self.assertIn("blur(24px)", STUDIO_CSS)
        self.assertIn("cubic-bezier(.22,1,.36,1)", STUDIO_CSS)
        self.assertIn('id="run-smoke"', INDEX_HTML)
        self.assertIn('aria-live="polite"', INDEX_HTML)
        self.assertNotIn("R2", INDEX_HTML.split("Technical protocol identifier")[0])
        self.assertIn('role="tablist"', INDEX_HTML)
        self.assertIn('id="smoke-cases"', INDEX_HTML)
        self.assertIn('id="smoke-seed"', INDEX_HTML)
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
        self.assertIn("width:calc(min(100%,1480px)", STUDIO_CSS)

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
                self.assertIn(b"Test a metric", response.read())
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
