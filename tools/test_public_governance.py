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

    def test_public_ci_runs_governance_build_and_ui_regressions(self) -> None:
        validate = (ROOT / ".github" / "workflows" / "validate.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("python3 tools/test_public_governance.py", validate)
        self.assertIn("python3 tools/validate_atlas_bundle.py", validate)
        self.assertIn("python3 tools/test_compact_renderer.py", validate)
        self.assertIn("python3 generator/gen_study.py", validate)

    def test_obsolete_github_pages_workflow_is_not_restored(self) -> None:
        self.assertFalse(
            (ROOT / ".github" / "workflows" / "build-deploy.yml").exists()
        )


if __name__ == "__main__":
    unittest.main()
