#!/usr/bin/env python3
"""Focused contract tests for the owner-reviewed V30 public evidence ledger."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "enrichment" / "corpus_findings.json"
EXCLUDED = "0e7aef2f494877ca4d7698305008de3f23489f26d2dffda02f58391171923e8d:F045"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_digest(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class V30EvidenceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = load(LEDGER)
        cls.rows = [row for source in cls.ledger.get("sources", []) for row in source["findings"]]

    def test_owner_review_universe_is_conserved_once(self):
        accounting = self.ledger["integration_accounting"]
        self.assertEqual(accounting["owner_reviewed_findings"], 1711)
        self.assertEqual(accounting["public_ledger_findings"], 1710)
        self.assertEqual(self.ledger["excluded_finding_refs"], [EXCLUDED])
        refs = [row["source_finding_ref"] for row in self.rows]
        self.assertEqual(len(refs), 1710)
        self.assertEqual(len(set(refs)), 1710)
        self.assertNotIn(EXCLUDED, refs)

    def test_statistics_and_sign_links_are_single_source(self):
        registry = load(ROOT / "data" / "semiology_data.json")
        registry_ids = {row["id"] for row in registry}
        self.assertEqual(self.ledger["registry_value_digest"], canonical_digest(registry))
        statistic_ids = []
        for row in self.rows:
            expected = None if row["measure"] == "NOT_QUANTITATIVE" else f'STAT:{row["source_finding_ref"]}'
            self.assertEqual(row["source_statistic_id"], expected)
            if expected:
                statistic_ids.append(expected)
            mapped = row["exact_sign_ids"] + row["related_sign_ids"]
            self.assertTrue(set(mapped).issubset(registry_ids))
            self.assertFalse(set(row["exact_sign_ids"]) & set(row["related_sign_ids"]))
        self.assertEqual(len(statistic_ids), 1216)
        self.assertEqual(len(set(statistic_ids)), 1216)

    def test_legacy_scientific_value_stores_are_retired(self):
        observations = load(ROOT / "enrichment" / "observations.json")
        self.assertEqual(observations.get("status"), "DEPRECATED")
        self.assertEqual(observations.get("canonical_ledger"), "corpus_findings.json")
        self.assertFalse({"weighting", "studies", "signs"} & set(observations))
        index = load(ROOT / "enrichment" / "evidence_index.json")
        self.assertEqual(index["source_ledger"], "corpus_findings.json")
        self.assertEqual(index["accounting"], self.ledger["integration_accounting"])
        self.assertNotIn("pooled", json.dumps(index).lower())
        self.assertNotIn("weight", json.dumps(index).lower())
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertNotIn("enrichment/build_enrichment.py", makefile)
        self.assertNotIn("tools/meta_analysis.py", makefile)
        self.assertIn("tools/adversarial_review.py --strict", makefile)
        self.assertIn("RETIRED", (ROOT / "enrichment" / "build_enrichment.py").read_text(encoding="utf-8"))
        self.assertIn("RETIRED", (ROOT / "tools" / "meta_analysis.py").read_text(encoding="utf-8"))

    def test_render_exposes_all_evidence_without_pooled_claims(self):
        html = (ROOT / "docs" / "seizure_semiology_localization.html").read_text(encoding="utf-8")
        lower = html.lower()
        self.assertIn("1,711 owner-reviewed findings", html)
        self.assertIn("1,710 public evidence rows", html)
        self.assertIn("1,216 source-reported statistics", html)
        self.assertIn("d66043e5db58e4ecaaf4a9a3379a7e349737ddb2c9a45284aa758adda06b9f77:F001", html)
        self.assertIn("not highly reliable", lower)
        self.assertNotIn(EXCLUDED, html)
        self.assertNotIn("<summary>weighted meta-analysis", lower)
        self.assertNotIn("pooled lateralization &amp; sources", lower)


if __name__ == "__main__":
    unittest.main()
