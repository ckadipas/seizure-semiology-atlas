#!/usr/bin/env python3
"""Focused regression checks for the compact classification browser."""

import hashlib
import runpy
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.get("children", []))


class CompactRendererTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.render = runpy.run_path(str(ROOT / "generator" / "gen_study.py"))

    def test_nonidentical_leaf_classification_term_remains_a_visible_family(self):
        groups = self.render["classification_trees"]["LUDERS_5D_2005"]["groups"]
        leaf_terms = {
            node["label"]: node
            for node in walk(groups)
            if node.get("node_kind") == "TERM" and not node.get("is_family")
        }
        self.assertIn("Vestibular aura", leaf_terms)
        signs = {str(row["id"]): row["sign"] for row in self.render["data"]}
        self.assertEqual(
            ["Vertiginous aura"],
            [signs[str(sign_id)] for sign_id in leaf_terms["Vestibular aura"]["all_sign_ids"]],
        )

    def test_broad_aura_reports_are_bucketed_without_compound_motor_leakage(self):
        groups = self.render["classification_trees"]["LUDERS_5D_2005"]["groups"]
        aura = next(node for node in groups if node["label"] == "Aura")
        signs = {str(row["id"]): row["sign"] for row in self.render["data"]}
        broad_labels = {signs[str(sign_id)] for sign_id in aura["broad_sign_ids"]}
        all_labels = {signs[str(sign_id)] for sign_id in aura["all_sign_ids"]}
        self.assertTrue({"Aura", "Aura present"}.issubset(broad_labels))
        self.assertNotIn("Focal motor signs", all_labels)

    def test_sign_fragment_prioritizes_compact_summary_and_closed_history(self):
        sign_id = "SGRP:a1e45e058d9faedf71f8"
        filename = "sign-" + hashlib.sha256(sign_id.encode()).hexdigest()[:24] + ".html"
        fragment = self.render["detail_fragments"][filename]
        self.assertRegex(fragment, r'class="[^"]*\bevidence-overview\b[^"]*"')
        self.assertRegex(fragment, r'class="[^"]*\bevidence-counts\b[^"]*"')
        self.assertIn(
            "<p>Patient-level results reported in the reviewed sources favor right-sided onset.</p>",
            fragment,
        )
        self.assertIn('class="d-row d-ev evidence-history-shell"', fragment)
        self.assertNotIn("The embedded evidence", fragment)
        self.assertNotIn("REG:TEMPORAL", fragment)
        self.assertNotRegex(fragment, r'<details class="[^"]*evidence-history-shell[^"]*" open')

    def test_aura_filter_uses_all_group_member_phases(self):
        fear = next(row for row in self.render["data"] if row["sign"] == "Fear aura")
        self.assertIn("aura / ictal", {value.casefold() for value in fear["phase_values"]})
        self.assertIn('data-phase-search="', self.render["h"])
        self.assertIn("item.dataset.phaseSearch", self.render["JS"])

    def test_region_view_uses_semilogy_hierarchy_before_signs(self):
        self.assertIn('id="region-order-mode"', self.render["h"])
        self.assertIn("function buildRegionBrowseView", self.render["JS"])
        self.assertIn("['Aura','Seizure','Lateralizing signs','Diagnostic signs']", self.render["JS"])
        self.assertIn("appendRegionCategoryContent", self.render["JS"])
        groups = self.render["classification_trees"]["LUDERS_5D_2005"]["groups"]
        aura = next(node for node in groups if node["label"] == "Aura")
        self.assertTrue(aura["broad_sign_ids"])
        self.assertIn("Autonomic aura", {child["label"] for child in aura["children"]})

    def test_synthesis_replaces_repeated_generic_variable_sentence(self):
        sign_id = "SGRP:f39e29bedd8219a01713"
        filename = "sign-" + hashlib.sha256(sign_id.encode()).hexdigest()[:24] + ".html"
        fragment = self.render["detail_fragments"][filename]
        self.assertIn("Does not lateralize", fragment)
        self.assertIn("Predominant, with exceptions", fragment)
        self.assertNotIn("Open the evidence for the balance and exceptions", fragment)

    def test_late_forced_head_version_names_the_frontal_eye_field_network(self):
        filename = "sign-" + hashlib.sha256(b"12").hexdigest()[:24] + ".html"
        fragment = self.render["detail_fragments"][filename]
        self.assertIn("Late forced head version is predominantly contralateral", fragment)
        self.assertIn("contralateral frontal eye field", fragment.casefold())
        self.assertIn("Brodmann 8", fragment)
        self.assertNotIn("No reliable anatomical localization", fragment)
        self.assertNotIn("Does not localize", fragment)

    def test_forced_eye_version_separates_network_from_onset_lobe(self):
        filename = "sign-" + hashlib.sha256(b"76").hexdigest()[:24] + ".html"
        fragment = self.render["detail_fragments"][filename]
        self.assertIn("Forced or tonic eye version is predominantly contralateral", fragment)
        self.assertIn("contralateral", fragment.casefold())
        self.assertIn("frontal eye field", fragment.casefold())
        self.assertIn("occipital eye field", fragment.casefold())
        self.assertNotIn("Localization depends on the described subtype or context", fragment)


if __name__ == "__main__":
    unittest.main()
