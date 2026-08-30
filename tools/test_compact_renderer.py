#!/usr/bin/env python3
"""Focused regression checks for the compact classification browser."""

import hashlib
import json
import re
import runpy
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.get("children", []))


def weighted_axis_panel(html, axis):
    marker = f'<section class="weighted-axis-panel" data-axis-panel="{axis}"'
    return html.split(marker, 1)[1].split("</section>", 1)[0]


def weighted_rows(panel):
    rows = {}
    pattern = re.compile(
        r'<details class="lr-row"(?P<attrs>[^>]*)>\s*<summary class="lr-row-head">'
        r'<span class="lr-name">(?P<name>[^<]+)(?:<small>.*?</small>)?</span>'
        r'(?P<summary>.*?)</summary>',
        re.DOTALL,
    )
    for match in pattern.finditer(panel):
        rows.setdefault(match.group("name"), []).append(
            {"attrs": match.group("attrs"), "summary": match.group("summary")}
        )
    return rows


class CompactRendererTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.render = runpy.run_path(str(ROOT / "generator" / "gen_study.py"))

    def test_brodmann_renderer_uses_editor_label_positions(self):
        configured = json.loads((ROOT / "data" / "brodmann_map.json").read_text())
        expected = {
            (view_name, area["id"]): area["label"]
            for view_name, view in configured["views"].items()
            for area in view["areas"]
        }
        actual = {
            (view_name, area["id"]): area["label"]
            for view_name, view in self.render["BA"].VIEWS.items()
            for area in view["areas"]
            if (view_name, area["id"]) in expected
        }
        self.assertEqual(expected, actual)

    def test_brodmann_editor_can_hide_a_label_without_removing_anatomy(self):
        medial = re.search(
            r'<svg[^>]*data-view="medial"[^>]*>(.*?)</svg>',
            self.render["brain_fold"],
            re.DOTALL,
        ).group(1)
        self.assertNotIn('data-tile="48"', medial)
        self.assertIn("48", self.render["BA"].AREAS)
        self.assertIn("medial", self.render["BA"].views_with("48"))

    def test_brodmann_hover_clears_off_an_area_and_when_views_change(self):
        js = self.render["JS"]
        self.assertIn("function resetBrainHover()", js)
        self.assertIn("card.addEventListener('mouseleave',resetBrainHover);", js)
        self.assertRegex(
            js,
            r"if\(!hit\)\{resetBrainHover\(\);return;\}",
        )
        show_view = js.split("function showView(name){", 1)[1].split(
            "function curView()", 1
        )[0]
        self.assertIn("resetBrainHover();", show_view)

    def test_subcentral_area_is_not_interactive_on_the_medial_view(self):
        self.assertEqual(["lateral"], self.render["BA"].views_with("43"))
        medial = re.search(
            r'<svg[^>]*data-view="medial"[^>]*>(.*?)</svg>',
            self.render["brain_fold"],
            re.DOTALL,
        ).group(1)
        self.assertNotIn('data-tile="43"', medial)

    def test_footer_omits_named_schools_and_keeps_the_submission_link(self):
        self.assertNotIn("Schools referenced", self.render["h"])
        self.assertIn("Contribute a paper or correction", self.render["h"])

    def test_footer_identifies_owner_and_links_the_content_license(self):
        footer = self.render["h"].split('<div class="footer">', 1)[1].split(
            "</div>", 1
        )[0]
        self.assertEqual(footer.count("CM Kadipasaoglu, MD, PhD"), 1)
        self.assertRegex(
            footer,
            r'&copy; 2026 <span data-nosnippet>CM Kadipasaoglu, MD, PhD</span> &middot; Creator and maintainer\.',
        )
        self.assertEqual(footer.count("<p>"), 1)
        self.assertNotIn("<strong>", footer)
        self.assertNotIn("&copy; 2026 Seizure Semiology Atlas", footer)
        self.assertIn(
            "This atlas is independently created and maintained in a personal capacity.",
            footer,
        )
        self.assertRegex(
            footer,
            r'<a[^>]+href="https://creativecommons\.org/licenses/by-nc-sa/4\.0/"[^>]+rel="license noopener noreferrer"',
        )
        self.assertIn("CC BY-NC-SA 4.0", footer)
        self.assertIn("Full disclaimer", footer)
        self.assertNotIn("Results from different studies are not combined", footer)
        self.assertNotIn(
            "Real localization always integrates ictal EEG, imaging, neuropsychology, and history",
            footer,
        )

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
            ["Vertiginous aura / ictal vestibular sensation"],
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
        self.assertIn("classificationRegionCategories(regionIds,mode)", self.render["JS"])
        self.assertNotIn("ludersRegionCategories(regionIds).forEach", self.render["JS"])
        self.assertIn("appendRegionCategoryContent", self.render["JS"])
        groups = self.render["classification_trees"]["LUDERS_5D_2005"]["groups"]
        aura = next(node for node in groups if node["label"] == "Aura")
        self.assertTrue(aura["broad_sign_ids"])
        self.assertIn("Autonomic aura", {child["label"] for child in aura["children"]})

    def test_language_and_auditory_signs_use_canonical_scheme_placements(self):
        signs = {str(row["id"]): row["sign"] for row in self.render["data"]}

        def labels_for(tree, node_label):
            node = next(node for node in walk(tree["groups"]) if node["label"] == node_label)
            return {signs[str(sign_id)] for sign_id in node["all_sign_ids"]}

        ilae = self.render["classification_trees"]["ILAE_SEIZURE_2025"]
        self.assertTrue({
            "Alexia", "Aphasia (phase unspecified)", "Conduction aphasia", "Ictal anomia",
        }.issubset(labels_for(ilae, "Cognitive and language phenomena")))
        self.assertTrue({
            "Ictal auditory loss", "Ictal deafness / hypoacusis",
        }.issubset(labels_for(ilae, "Auditory")))

        luders = self.render["classification_trees"]["LUDERS_5D_2005"]
        self.assertTrue({
            "Alexia", "Aphasia (phase unspecified)", "Conduction aphasia", "Ictal anomia",
        }.issubset(labels_for(luders, "Aphasic seizure")))

    def test_canonical_classifications_are_identical_in_every_projection(self):
        bundle = json.loads((ROOT / "data" / "atlas_bundle.json").read_text())
        canonical = {
            (str(row["sign_id"]), row["node_id"], row["relation"])
            for row in bundle["classifications"]["sign_mappings"]
        }
        context = {
            (str(sign_id), row["node_id"], row["relation"])
            for row in bundle["evidence_context"]["relationships"]["classifications"]
            if row["subject_kind"] == "SIGN"
            for sign_id in row["public_sign_ids"]
        }
        self.assertEqual(canonical, context)

    def test_synthesis_replaces_repeated_generic_variable_sentence(self):
        sign_id = "SGRP:f39e29bedd8219a01713"
        filename = "sign-" + hashlib.sha256(sign_id.encode()).hexdigest()[:24] + ".html"
        fragment = self.render["detail_fragments"][filename]
        self.assertIn("No reliable lateralization", fragment)
        self.assertIn(">Frontal<", fragment)
        self.assertIn(">Temporal<", fragment)
        self.assertNotIn(
            "Localization depends on the described subtype or context.", fragment
        )
        self.assertNotIn("Predominant, with exceptions", fragment)
        self.assertNotIn("Open the evidence for the balance and exceptions", fragment)

    def test_late_forced_head_version_names_the_frontal_eye_field_network(self):
        filename = "sign-" + hashlib.sha256(b"12").hexdigest()[:24] + ".html"
        fragment = self.render["detail_fragments"][filename]
        self.assertIn(">Contralateral<", fragment)
        self.assertIn(">Frontal<", fragment)
        self.assertIn("contralateral frontal eye field", fragment.casefold())
        self.assertIn('data-ba="8"', fragment)

    def test_forced_eye_version_separates_network_from_onset_lobe(self):
        filename = "sign-" + hashlib.sha256(b"76").hexdigest()[:24] + ".html"
        fragment = self.render["detail_fragments"][filename]
        self.assertIn(">Contralateral<", fragment)
        self.assertIn(">Frontal<", fragment)
        self.assertIn(">Occipital<", fragment)
        self.assertIn('data-ba="8"', fragment)
        self.assertIn('data-ba="19"', fragment)
        self.assertNotIn("Localization depends on the described subtype or context", fragment)

    def test_singular_relationship_target_is_shown_as_clinical_direction(self):
        chips = self.render["lateralization_target_chips"](
            "SGRP:0644ef162d6917366ad7"
        )
        self.assertIn(">Right<", chips)

    def test_lateralization_filter_uses_every_shared_target_without_scalar_loss(self):
        expected = {
            str(target.get("key") or "").strip().casefold()
            for card in self.render["SYNTHESIS_CARDS"]
            if card.get("axis") == "LATERALIZATION"
            for target in (card.get("target_contract") or {}).get("reported_targets") or []
            if str(target.get("key") or "").strip()
        }
        expected.add("notreported")
        select = self.render["h"].split('<select id="filter-lat">', 1)[1].split(
            "</select>", 1
        )[0]
        options = set(re.findall(r'<option value="([^"]+)">', select)) - {""}
        self.assertEqual(expected, options)
        self.assertTrue(
            {"left", "right", "bilateral", "contra", "ipsi", "dominant",
             "nondominant", "nonassoc", "notreported"}.issubset(options)
        )
        self.assertIn('data-lat-targets="', self.render["h"])
        self.assertIn("item.dataset.latTargets", self.render["JS"])
        self.assertNotIn("item.dataset.latcode!==lat", self.render["JS"])

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

    def test_source_linked_spasm_regions_are_visible_in_localization(self):
        spasms = next(row for row in self.render["data"] if row["sign"] == "Epileptic spasms")
        display = self.render["localization_display"](spasms)
        for region in ("Frontal", "Temporal", "Occipital", "Parietal"):
            self.assertIn(f">{region}<", display)
        self.assertNotIn("No reported localization relationship", display)

    def test_reviewed_finding_keeps_its_source_region_without_canonical_sign_link(self):
        index = self.render["EvidenceContextIndex"].__new__(
            self.render["EvidenceContextIndex"]
        )
        index.locations_by_finding = {
            "F:source": [{
                "region_id": "REG:TEMPORAL",
                "major_region_id": "REG:TEMPORAL",
                "public_sign_ids": [],
            }]
        }
        index.axis_contexts_by_finding = {"F:source": []}
        self.assertEqual(["Temporal"], index.region_labels_for_findings(["F:source"]))

    def test_adjudicated_sign_link_reaches_reviewed_findings_and_statistics(self):
        finding_ref = (
            "c824399545b3427f14a20f00453bff7545f2ab64c291d7098ca60e4419a44ee4:F007"
        )
        statistic_ids = [
            "STAT2:2a98ee300976a26e7f9eae37",
            "STAT2:c259837e62e26b73ffc287a9",
        ]
        self.assertIn(
            "43", self.render["CONTEXT"].public_sign_ids_for_findings([finding_ref])
        )
        for statistic_id in statistic_ids:
            self.assertIn(
                "43",
                self.render["CONTEXT"].public_sign_ids_for_statistics([statistic_id]),
            )

    def test_every_adjudicated_sign_link_reaches_all_evidence_views(self):
        context = self.render["CONTEXT"]
        statistics_by_finding = {}
        for statistic_id, statistic in context.statistics.items():
            statistics_by_finding.setdefault(
                str(statistic.get("finding_ref") or ""), []
            ).append(statistic_id)
        for finding_ref, rows in context.axis_contexts_by_finding.items():
            expected = {
                str(sign_id)
                for row in rows
                if row.get("relationship_eligible")
                for sign_id in row.get("public_sign_ids") or []
            }
            if not expected:
                continue
            self.assertTrue(
                expected.issubset(
                    context.public_sign_ids_for_findings([finding_ref])
                ),
                finding_ref,
            )
            for statistic_id in statistics_by_finding.get(finding_ref, []):
                self.assertTrue(
                    expected.issubset(
                        context.public_sign_ids_for_statistics([statistic_id])
                    ),
                    statistic_id,
                )

    def test_spasm_browse_regions_match_the_shared_context(self):
        spasms = next(row for row in self.render["data"] if row["sign"] == "Epileptic spasms")
        self.assertEqual(
            set(spasms["regions"]),
            set(self.render["public_browse_regions"](spasms)),
        )
        self.assertNotIn("No localization stated", spasms["regions"])

    def test_region_color_legend_disclaims_evidence_strength(self):
        self.assertIn(
            "Region colors identify anatomy only; they do not indicate evidence strength",
            self.render["h"],
        )

    def test_every_public_axis_has_a_visible_specific_value(self):
        generic_labels = (
            "Consistent",
            "Depends on subtype or context",
            "Predominant, with exceptions",
            "Tendency, with uncertainty",
        )
        for sign in self.render["data"]:
            for axis, function in (
                ("lateralization", self.render["lateralization_display"]),
                ("localization", self.render["localization_display"]),
            ):
                text = re.sub(r"<[^>]+>", " ", function(sign)).strip()
                self.assertTrue(text, f"{sign['sign']} has a blank {axis} display")
                for label in generic_labels:
                    self.assertNotIn(label, text, f"{sign['sign']} exposes {label}")

    def test_deepest_banner_is_bounded_but_remains_readable(self):
        css = self.render["h"]
        self.assertIn(".browse-sign{width:100%", css)
        self.assertIn(
            ".browse-subsection>.browse-subbody>.browse-sign-wrap>.browse-sign",
            css,
        )
        self.assertIn("font-size:.75rem", css)
        self.assertNotRegex(css, r"\.browse-sign-name\{[^}]*font-size:\.(?:[0-5]\d)rem")

    def test_weighted_localization_rows_carry_their_evidence_region(self):
        rows = weighted_rows(weighted_axis_panel(self.render["h"], "LOCALIZATION"))
        self.assertRegex(rows["Fear aura"][0]["attrs"], r'data-group-regions="[^"]*Temporal')
        formed_name = next(
            name for name in rows
            if name.startswith("Formed semantic visual hallucinations")
        )
        self.assertRegex(
            rows[formed_name][0]["attrs"],
            r'data-group-regions="[^"]*Occipital',
        )
        self.assertIn(
            "Reported: Occipital",
            rows[formed_name][0]["summary"],
        )

    def test_single_source_targets_are_weighted_without_claiming_predominance(self):
        panel = weighted_axis_panel(self.render["h"], "LOCALIZATION")
        rows = weighted_rows(panel)
        self.assertIn("Prosopagnosia", rows)
        self.assertIn("Reported: Occipital", rows["Prosopagnosia"][0]["summary"])
        self.assertNotIn("Predominant:", rows["Prosopagnosia"][0]["summary"])
        self.assertIn("Seizure-associated aphasia", rows)
        self.assertIn("Temporal", rows["Seizure-associated aphasia"][0]["summary"])

    def test_study_results_render_every_atomic_statistic(self):
        index = json.loads(
            self.render["deferred_fragments"]["study-results-index.json"]
        )
        expected = self.render["CORPUS"]["integration_accounting"][
            "source_reported_statistics"
        ]
        self.assertEqual(expected, len(index["records"]))
        self.assertNotIn("record.kind==='grouped'", self.render["JS"])
        self.assertNotIn("record.kind==='additional'", self.render["JS"])
        self.assertIn("groupMarkup(matched,'study')", self.render["JS"])

    def test_weighted_rows_hide_internal_linkage_audit_text(self):
        panels = "".join(
            weighted_axis_panel(self.render["h"], axis)
            for axis in ("LATERALIZATION", "LOCALIZATION")
        )
        for internal_text in (
            "This public sign combines",
            "Linkage details",
            "Target scope and anatomy",
            "exact identity linkage needed",
            "exact sign linkage needed",
            "finding-wide only",
            "normalization needed",
            "provenance only",
            "source linked finding axis",
        ):
            self.assertNotIn(internal_text, panels)
        fear_filename = "sign-" + hashlib.sha256(b"2").hexdigest()[:24] + ".html"
        self.assertNotIn(
            "This public sign combines",
            self.render["detail_fragments"][fear_filename],
        )
        self.assertIn("Documented exceptions", panels)
        self.assertIn("Evidence by contributing manuscript", panels)

    def test_public_library_counts_use_canonical_manuscripts_only(self):
        accounting = self.render["CORPUS"]["integration_accounting"]
        manuscript_count = len(self.render["PAPERS"])
        self.assertIn(
            f'{accounting["public_ledger_findings"]:,} findings &middot; '
            f'{accounting["source_reported_statistics"]:,} reported results &middot; '
            f"{manuscript_count} manuscripts",
            self.render["evidence_library_html"],
        )
        self.assertNotIn("source files", self.render["evidence_library_html"])
        self.assertIn(
            f"<summary>Source Library &mdash; {manuscript_count} Manuscripts</summary>",
            self.render["h"],
        )

    def test_last_updated_uses_the_immutable_release_timestamp(self):
        release = self.render["EVIDENCE_SYNTHESIS"]["release"]
        self.assertEqual(
            release["updated_utc"],
            self.render["SITE_UPDATED_UTC"].isoformat(),
        )
        self.assertIn(
            f"datetime='{self.render['SITE_UPDATED_ISO']}'",
            self.render["h"],
        )

    def test_source_less_legacy_background_is_not_evidence_history(self):
        block, linked_count, search = self.render["ledger_evidence_block"](
            "__source_less__", "Legacy clinical note"
        )
        self.assertEqual(("", 0, ""), (block, linked_count, search))
        filename = "sign-" + hashlib.sha256(b"71").hexdigest()[:24] + ".html"
        self.assertNotIn(
            "evidence-history-shell", self.render["detail_fragments"][filename]
        )


if __name__ == "__main__":
    unittest.main()
