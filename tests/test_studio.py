import json
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen

from physgauge.studio import (
    INDEX_HTML,
    STUDIO_CSS,
    StudioAddress,
    StudioHTTPServer,
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

    def test_studio_uses_brand_tokens_and_secondary_r2_label(self):
        self.assertIn("rgb(255 255 255 / 28%)", STUDIO_CSS)
        self.assertIn("blur(24px)", STUDIO_CSS)
        self.assertIn("cubic-bezier(.22,1,.36,1)", STUDIO_CSS)
        self.assertIn('id="run-smoke"', INDEX_HTML)
        self.assertIn('aria-live="polite"', INDEX_HTML)
        self.assertNotIn("R2", INDEX_HTML.split("Technical protocol identifier")[0])

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
