#!/usr/bin/env python3
"""Prevent stale or unprofessional public operational guidance."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ROOT / "AGENTS.md",
    ROOT / ".github" / "workflows" / "intake.yml",
    ROOT / ".github" / "workflows" / "intake-ack.yml",
)
BLOCKED_STEMS = (
    "fu" + "ck",
    "sh" + "it",
    "cu" + "nt",
    "ass" + "hole",
    "b" + "itch",
    "dumb" + "ass",
    "dip" + "sh" + "it",
    "dick" + "head",
    "jack" + "ass",
    "god" + "damn",
    "stu" + "pid",
    "clau" + "de",
    "chat" + "gpt",
    "open" + "ai",
    "anthro" + "pic",
    "gem" + "ini",
    "artificial " + "intelligence",
    "language " + "model",
)


class PublicGovernanceTests(unittest.TestCase):
    def test_operational_guidance_is_professional(self) -> None:
        matches = []
        for path in FILES:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                lowered = line.casefold()
                if any(stem in lowered for stem in BLOCKED_STEMS):
                    matches.append(f"{path.relative_to(ROOT)}:{number}")
        self.assertEqual([], matches)

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


if __name__ == "__main__":
    unittest.main()
