#!/usr/bin/env python3
"""Validate current public operational guidance."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ROOT / "AGENTS.md",
    ROOT / ".github" / "workflows" / "intake.yml",
    ROOT / ".github" / "workflows" / "intake-ack.yml",
)
class PublicGovernanceTests(unittest.TestCase):
    def test_intake_acknowledges_registration_without_promising_extraction(self) -> None:
        text = (ROOT / ".github" / "workflows" / "intake-ack.yml").read_text(encoding="utf-8")
        lowered = text.casefold()
        self.assertIn("private gate a", lowered)
        self.assertNotIn("starts the extraction", lowered)
        self.assertNotIn("prepared as a pull request", lowered)

    def test_public_ci_runs_this_check(self) -> None:
        for workflow in ("validate.yml", "build-deploy.yml"):
            text = (ROOT / ".github" / "workflows" / workflow).read_text(encoding="utf-8")
            self.assertIn("python3 tools/test_public_governance.py", text)

    def test_public_ci_runs_ui_regressions_and_live_hash_verification(self) -> None:
        validate = (ROOT / ".github" / "workflows" / "validate.yml").read_text(
            encoding="utf-8"
        )
        deploy = (ROOT / ".github" / "workflows" / "build-deploy.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("python3 tools/test_compact_renderer.py", validate)
        self.assertIn("python3 tools/test_compact_renderer.py", deploy)
        self.assertIn("sha256sum docs/index.html", deploy)
        self.assertIn("Live release hash matches generated index", deploy)


if __name__ == "__main__":
    unittest.main()
