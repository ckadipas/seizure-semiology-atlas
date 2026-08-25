#!/usr/bin/env python3
"""Focused regression checks for the compact classification browser."""

import hashlib
import re
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
        self.assertIn("No reliable lateralization", fragment)
        self.assertIn(
            "Evidence is context-dependent rather than establishing one predominant localizer",
            fragment,
        )
        self.assertIn("posterior-frontal localization", fragment)
        self.assertNotIn(
            "Localization depends on the described subtype or context.", fragment
        )
        self.assertNotIn("Predominant, with exceptions", fragment)
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

    def test_singular_relationship_target_is_shown_as_clinical_direction(self):
        chips = self.render["lateralization_target_chips"](
            "SGRP:0644ef162d6917366ad7"
        )
        self.assertIn(">Right<", chips)

    def test_internal_synthesis_labels_are_not_the_public_axis_value(self):
        rapid_recovery = next(
            row for row in self.render["data"] if row["sign"] == "Rapid postictal recovery"
        )
        display = self.render["lateralization_display"](rapid_recovery)
        self.assertIn(">Right<", display)
        self.assertNotIn("Consistent", display)

    def test_context_dependent_summary_uses_the_specific_source_relationship(self):
        sign_id = "SGRP:76a39c9569c7472d08d2"
        filename = "sign-" + hashlib.sha256(sign_id.encode()).hexdigest()[:24] + ".html"
        fragment = self.render["detail_fragments"][filename]
        self.assertIn("contralateral lateralization for mesial frontal cortex", fragment)
        self.assertIn("mesial temporal/insular cortex", fragment)
        self.assertNotIn("depends on the described subtype or context", fragment)

    def test_nonlocalizing_card_does_not_show_context_regions_as_localizers(self):
        spasms = next(row for row in self.render["data"] if row["sign"] == "Epileptic spasms")
        display = self.render["localization_display"](spasms)
        self.assertIn("No reliable localization", display)
        self.assertNotIn(">Temporal<", display)
        self.assertNotIn(">Occipital<", display)
        self.assertNotIn(">Deep/Subcortical<", display)

    def test_nonlocalizing_sign_is_browsed_only_as_unlocalized(self):
        spasms = next(row for row in self.render["data"] if row["sign"] == "Epileptic spasms")
        self.assertEqual(
            ["No localization stated"],
            self.render["public_browse_regions"](spasms),
        )

    def test_region_color_legend_disclaims_evidence_strength(self):
        self.assertIn(
            "Region colors identify anatomy only; they do not indicate evidence strength",
            self.render["h"],
        )

    def test_every_public_axis_has_a_visible_specific_value(self):
        for sign in self.render["data"]:
            for axis, function in (
                ("lateralization", self.render["lateralization_display"]),
                ("localization", self.render["localization_display"]),
            ):
                text = re.sub(r"<[^>]+>", " ", function(sign)).strip()
                self.assertTrue(text, f"{sign['sign']} has a blank {axis} display")


if __name__ == "__main__":
    unittest.main()
