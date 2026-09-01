#!/usr/bin/env python3
"""Focused regression checks for the compact classification browser."""

import hashlib
import importlib.util
import inspect
import json
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AtlasBundleValidatorTest(unittest.TestCase):
    @staticmethod
    def neutral_membership_bundle():
        bundle = json.loads((ROOT / "data" / "atlas_bundle.json").read_text())
        bundle["schema_version"] = "atlas-public-bundle-1.6.0"
        for source in bundle["corpus"]["sources"]:
            for finding in source["findings"]:
                legacy_sign_ids = [
                    str(sign_id)
                    for field in ("exact_sign_ids", "related_sign_ids")
                    for sign_id in finding.get(field) or []
                ]
                finding["sign_ids"] = list(dict.fromkeys(
                    legacy_sign_ids or finding.get("sign_ids") or []
                ))
                finding.pop("exact_sign_ids", None)
                finding.pop("related_sign_ids", None)
        context = bundle["evidence_context"]
        for row in context["contexts"]:
            row["sign_links"] = [
                {"public_sign_id": public_sign_id}
                for public_sign_id in dict.fromkeys(
                    str(link["public_sign_id"])
                    for link in row.get("sign_links") or []
                )
            ]
        context_payload = dict(context)
        context_payload.pop("semantic_digest")
        context["semantic_digest"] = hashlib.sha256(json.dumps(
            context_payload, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False,
        ).encode()).hexdigest()
        bundle["evidence_authority"]["current_projection_audit"][
            "evidence_context_digest"
        ] = context["semantic_digest"]
        payload = dict(bundle)
        payload.pop("semantic_digest")
        bundle["semantic_digest"] = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode()).hexdigest()
        return bundle

    @staticmethod
    def new_contract_bundle():
        bundle = AtlasBundleValidatorTest.neutral_membership_bundle()
        location_labels = {
            "REG:TEMPORAL": "Temporal", "REG:FRONTAL": "Frontal",
            "REG:PARIETAL": "Parietal", "REG:OCCIPITAL": "Occipital",
            "REG:INSULAR": "Insular", "REG:LIMBIC": "Limbic",
            "REG:DEEP_SUBCORTICAL": "Deep/Subcortical",
        }
        context = bundle["evidence_context"]
        context["relationships"].pop("sign_axis_contexts", None)
        for row in context["relationships"].get("statistic_signs") or []:
            row.pop("relation", None)
        context["accounting"].pop("sign_axis_contexts", None)
        for row in context["contexts"]:
            row.pop("sign_axis_context_link_ids", None)
            row["axis_modifiers"] = []
        context_by_finding = {
            str(row["finding_ref"]): row for row in context["contexts"]
        }
        propagation_assertions = [
            row for row in context["assertions_by_id"].values()
            if str(row.get("normalized_value") or "")
            == "REG:MULTIREGIONAL_PROPAGATION"
        ]
        for assertion in propagation_assertions:
            finding_ref = str(assertion["finding_ref"])
            finding_context = context_by_finding[finding_ref]
            finding_context.setdefault("axis_modifiers", []).append({
                "modifier_reference_id": f'AXIS_MODIFIER:{assertion["assertion_id"]}',
                "assertion_id": str(assertion["assertion_id"]),
                "finding_ref": finding_ref,
                "axis": str(assertion["axis"]),
                "key": "PROPAGATION",
                "label": "Propagation",
                "modifier_type": "PROPAGATION",
                "normalized_value": "REG:MULTIREGIONAL_PROPAGATION",
                "source_sign_ids": [],
                "public_sign_ids": [
                    str(link["public_sign_id"])
                    for link in finding_context.get("sign_links") or []
                ],
            })
        mapped_modifier_count = sum(
            len(row.get("public_sign_ids") or [])
            for context_row in context["contexts"]
            for row in context_row.get("axis_modifiers") or []
        )
        context["accounting"]["structured_propagation"] = {
            "structured_inputs": len(propagation_assertions),
            "finding_context_modifier_references": len(propagation_assertions),
            "mapped_sign_modifier_references_expected": mapped_modifier_count,
            "mapped_sign_modifier_references_generated": 0,
            "reported_target_contamination": 0,
            "placement_contribution_leakage": 0,
        }
        synthesis = bundle["evidence_synthesis"]
        for field in (
            "finding_axes", "sign_finding_axes",
            "terminal_classification_manifest", "terminal_classification_profile",
        ):
            synthesis.pop(field, None)
        target_fields = {
            "key", "label", "raw", "origins", "finding_refs", "target_level",
            "region_id", "parent_region_id", "area_id", "brodmann_label",
        }

        def minimal_target(target, allowed_finding_refs):
            projected = {
                field: value for field, value in target.items() if field in target_fields
            }
            projected["raw"] = [
                value for value in projected.get("raw") or []
                if " ".join(re.findall(
                    r"[a-z0-9]+", str(value or "").casefold()
                )) not in {
                    "propagation", "multiregional propagation",
                    "reg multiregional propagation",
                }
            ]
            allowed = {str(value) for value in allowed_finding_refs}
            finding_refs = list(dict.fromkeys(
                str(value) for value in (
                    target.get("finding_refs")
                    or [row.get("finding_ref") for row in target.get("details") or []]
                ) if value and str(value) in allowed
            ))
            projected["finding_refs"] = finding_refs or list(allowed)
            return projected

        for card in synthesis["axis_summaries"]:
            for field in (
                "categorization_state", "terminal_classification",
                "terminal_reason", "terminal_reason_text", "missing_relationship",
                "supplemental_projection", "child_group_evidence", "exceptions",
            ):
                card.pop(field, None)
            reported_targets = [
                minimal_target(target, card.get("row_finding_refs") or [])
                for target in card["target_contract"].get("reported_targets") or []
                if " ".join(re.findall(
                    r"[a-z0-9]+", str(target.get("key") or "").casefold()
                )) != "reg multiregional propagation"
            ]
            card["target_contract"] = {
                "reported_targets": reported_targets,
                "modifiers": list(card["target_contract"].get("modifiers") or []),
            }
            if "limit this packet" in str(card.get("plain_summary") or "").casefold():
                card["plain_summary"] = (
                    "In the cited 49-case cohort, EEG abnormalities were left-sided "
                    "in 38 cases, right-sided in 2, and unclear in 9."
                )
            card["plain_summary"] = re.sub(
                r"(?<![A-Za-z0-9])F\d{3}(?![A-Za-z0-9])", "reviewed finding",
                str(card.get("plain_summary") or ""),
            ).replace("do not assign", "does not include")
            for contribution in card.get("contributions") or []:
                for field in (
                    "projection_disposition", "counted_under_sign_id",
                    "counted_under_label", "projection_reason",
                    "projection_unselected_statistic_ids", "weight_status",
                    "potential_weight",
                ):
                    contribution.pop(field, None)

        cards_by_pair = {
            (str(card["sign_id"]), str(card["axis"])): card
            for card in synthesis["axis_summaries"]
        }
        head_id = "SGRP:b2d45c8a9bd12b5bcf07"
        head_localization = cards_by_pair[(head_id, "LOCALIZATION")]
        head_source = cards_by_pair[(head_id, "LATERALIZATION")]
        for field in (
            "context_ids", "contributions", "declared_source_work_ids",
            "related_finding_refs", "row_finding_count", "row_finding_refs",
            "row_lineage", "row_statistic_count", "row_statistic_ids",
            "row_work_count", "row_work_ids",
        ):
            if field in head_source:
                head_localization[field] = json.loads(json.dumps(head_source[field]))
        required_localizations = {
            head_id: "The source cohort designates temporal localization for this semiology.",
            "SGRP:1834989c017725d8d64a": (
                "The source cohort designates temporal localization for this "
                "paroxysmal speech disturbance."
            ),
        }
        for sign_id, summary in required_localizations.items():
            card = cards_by_pair[(sign_id, "LOCALIZATION")]
            card["plain_summary"] = summary
            card["target_contract"] = {
                "reported_targets": [{
                    "key": "REG:TEMPORAL",
                    "label": "Temporal",
                    "raw": ["REG:TEMPORAL"],
                    "origins": ["SOURCE_COHORT_DESIGNATION"],
                    "finding_refs": [str(card["row_finding_refs"][0])],
                    "target_level": "REGION",
                    "region_id": "REG:TEMPORAL",
                }],
                "modifiers": list(card["target_contract"].get("modifiers") or []),
            }
            sign = next(row for row in bundle["signs"] if str(row["id"]) == sign_id)
            sign["regions"] = ["Temporal"]
            sign["region"] = sign["loc"] = "Temporal"
            sign["sub"] = "Source-reported localization in linked evidence"
            sign["subs_by_region"] = {
                "Temporal": "Source-reported localization in linked evidence"
            }
        regions_by_sign = {str(sign["id"]): [] for sign in bundle["signs"]}
        areas_by_sign = {str(sign["id"]): [] for sign in bundle["signs"]}
        for card in synthesis["axis_summaries"]:
            if card.get("axis") != "LOCALIZATION":
                continue
            sign_id = str(card["sign_id"])
            for target in card["target_contract"]["reported_targets"]:
                if (str(target.get("target_level") or "").upper() == "STATUS"
                        or str(target.get("key") or "").casefold() == "nonassoc"):
                    continue
                region_id = next((
                    str(value) for value in (
                        target.get("region_id"), target.get("parent_region_id"),
                        target.get("key"),
                    ) if str(value or "") in location_labels
                ), "")
                if region_id and location_labels[region_id] not in regions_by_sign[sign_id]:
                    regions_by_sign[sign_id].append(location_labels[region_id])
                area_id = str(target.get("area_id") or "").removeprefix("BA:")
                if area_id and area_id not in areas_by_sign[sign_id]:
                    areas_by_sign[sign_id].append(area_id)
        by_sign = bundle["brodmann"]["mapping"]["by_sign"]
        for sign in bundle["signs"]:
            sign_id = str(sign["id"])
            regions = regions_by_sign[sign_id] or ["No localization stated"]
            sign["regions"] = regions
            sign["region"] = "; ".join(regions)
            sign["loc"] = sign["region"]
            if areas_by_sign[sign_id]:
                by_sign[sign_id] = {
                    "areas": areas_by_sign[sign_id], "sign": sign["sign"],
                }
            else:
                by_sign.pop(sign_id, None)
        bundle["evidence_authority"]["current_projection_audit"][
            "localization_rows_checked_against_browse_regions"
        ] = sum(bool(value) for value in regions_by_sign.values())
        context["accounting"]["structured_propagation"][
            "mapped_sign_modifier_references_generated"
        ] = sum(
            len(modifier.get("assertion_ids") or [])
            for card in synthesis["axis_summaries"]
            for modifier in card["target_contract"].get("modifiers") or []
        )
        AtlasBundleValidatorTest.sync_sign_axis_summaries(bundle)
        context_payload = dict(context)
        context_payload.pop("semantic_digest")
        context["semantic_digest"] = hashlib.sha256(json.dumps(
            context_payload, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False,
        ).encode()).hexdigest()
        bundle["evidence_authority"]["current_projection_audit"][
            "evidence_context_digest"
        ] = context["semantic_digest"]
        payload = dict(bundle)
        payload.pop("semantic_digest")
        bundle["semantic_digest"] = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode()).hexdigest()
        return bundle

    @staticmethod
    def sync_sign_axis_summaries(bundle):
        location_ids = {
            "REG:TEMPORAL", "REG:FRONTAL", "REG:PARIETAL", "REG:OCCIPITAL",
            "REG:INSULAR", "REG:LIMBIC", "REG:DEEP_SUBCORTICAL",
        }
        relationships = bundle["evidence_context"]["relationships"]
        existing = {
            str(row["synthesis_id"]): row
            for row in relationships.get("sign_axis_summaries") or []
        }
        summaries = []
        for card in bundle["evidence_synthesis"]["axis_summaries"]:
            synthesis_id = str(card["synthesis_id"])
            targets = card["target_contract"]["reported_targets"]
            target_keys = sorted({
                str(target["key"]) for target in targets if target.get("key")
            })
            region_ids = set()
            if str(card["axis"]) == "LOCALIZATION":
                for target in targets:
                    if (
                        str(target.get("target_level") or "").upper() == "STATUS"
                        or str(target.get("key") or "").casefold() == "nonassoc"
                    ):
                        continue
                    region_id = next((
                        str(value) for value in (
                            target.get("key"), target.get("region_id"),
                            target.get("parent_region_id"),
                        ) if str(value or "") in location_ids
                    ), "")
                    if region_id:
                        region_ids.add(region_id)
            summaries.append({
                "sign_axis_summary_link_id": str(
                    existing.get(synthesis_id, {}).get("sign_axis_summary_link_id")
                    or f"SIGN_AXIS_SUMMARY:{synthesis_id}"
                ),
                "synthesis_id": synthesis_id,
                "axis": str(card["axis"]),
                "public_sign_ids": [str(card["sign_id"])],
                "context_ids": list(card.get("context_ids") or []),
                "region_ids": sorted(region_ids),
                "brodmann_area_ids": sorted(
                    {
                        value[3:]
                        for value in target_keys
                        if value.startswith("BA:")
                    },
                    key=lambda value: (
                        not value.isdigit(),
                        int(value) if value.isdigit() else value,
                    ),
                ),
                "reported_target_keys": target_keys,
                "modifiers": list(card["target_contract"].get("modifiers") or []),
            })
        relationships["sign_axis_summaries"] = summaries
        bundle["evidence_context"]["accounting"]["sign_axis_summaries"] = len(
            summaries
        )

    @staticmethod
    def run_validator(bundle):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "atlas_bundle.json"
            path.write_text(json.dumps(bundle), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(ROOT / "tools" / "validate_atlas_bundle.py"), str(path)],
                capture_output=True,
                text=True,
            )

    @staticmethod
    def refresh_digests(bundle):
        context = bundle["evidence_context"]
        context_payload = dict(context)
        context_payload.pop("semantic_digest")
        context["semantic_digest"] = hashlib.sha256(json.dumps(
            context_payload, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False,
        ).encode()).hexdigest()
        bundle["evidence_authority"]["current_projection_audit"][
            "evidence_context_digest"
        ] = context["semantic_digest"]
        payload = dict(bundle)
        payload.pop("semantic_digest")
        bundle["semantic_digest"] = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode()).hexdigest()

    @classmethod
    def bundle_with_mapped_propagation_modifier(cls):
        bundle = cls.new_contract_bundle()
        card = next(
            row for row in bundle["evidence_synthesis"]["axis_summaries"]
            if row["target_contract"]["reported_targets"] and row["contributions"]
        )
        sign_id = str(card["sign_id"])
        placement_refs = set(card["row_finding_refs"])
        modifier_context = next(
            row for row in bundle["evidence_context"]["contexts"]
            if str(row["finding_ref"]) not in placement_refs
            and str(row["source_work_id"]) not in set(card["row_work_ids"])
            and not row.get("sign_links")
            and not row.get("axis_modifiers")
        )
        modifier_ref = str(modifier_context["finding_ref"])
        modifier_context["sign_links"] = [
            *modifier_context.get("sign_links", []), {"public_sign_id": sign_id},
        ]
        finding = next(
            row
            for source in bundle["corpus"]["sources"]
            for row in source["findings"]
            if str(row["source_finding_ref"]) == modifier_ref
        )
        finding["sign_ids"] = list(dict.fromkeys([
            *finding.get("sign_ids", []), sign_id,
        ]))
        assertion_id = "AXIS:public-modifier-contract-test"
        bundle["evidence_context"]["assertions_by_id"][assertion_id] = {
            "assertion_id": assertion_id,
            "axis": str(card["axis"]),
            "finding_ref": modifier_ref,
            "normalized_value": "REG:MULTIREGIONAL_PROPAGATION",
            "assertion_scope": "FINDING",
            "reviewed_assertion_text": "",
            "locators": "",
            "support_page": None,
            "support_excerpt": "",
            "support_status": "SUPPORTED",
        }
        modifier_context["assertion_ids"] = list(dict.fromkeys([
            *modifier_context.get("assertion_ids", []), assertion_id,
        ]))
        modifier_context.setdefault("axis_modifiers", []).append({
            "modifier_reference_id": f"AXIS_MODIFIER:{assertion_id}",
            "assertion_id": assertion_id,
            "finding_ref": modifier_ref,
            "axis": str(card["axis"]),
            "key": "PROPAGATION",
            "label": "Propagation",
            "modifier_type": "PROPAGATION",
            "normalized_value": "REG:MULTIREGIONAL_PROPAGATION",
            "source_sign_ids": [],
            "public_sign_ids": [sign_id],
        })
        bundle["evidence_context"]["accounting"]["assertions"] = len(
            bundle["evidence_context"]["assertions_by_id"]
        )
        modifier = {
            "key": "PROPAGATION",
            "label": "Propagation",
            "modifier_type": "PROPAGATION",
            "raw": ["REG:MULTIREGIONAL_PROPAGATION"],
            "origins": ["STRUCTURED_SOURCE_AXIS_ASSERTION"],
            "finding_refs": [modifier_ref],
            "assertion_ids": [assertion_id],
        }
        card["target_contract"]["modifiers"] = [modifier]
        card["context_ids"] = list(dict.fromkeys([
            *card.get("context_ids", []), str(modifier_context["context_id"]),
        ]))
        propagation_accounting = bundle["evidence_context"]["accounting"][
            "structured_propagation"
        ]
        propagation_accounting["structured_inputs"] += 1
        propagation_accounting["finding_context_modifier_references"] += 1
        propagation_accounting["mapped_sign_modifier_references_expected"] += 1
        propagation_accounting["mapped_sign_modifier_references_generated"] += 1
        cls.sync_sign_axis_summaries(bundle)
        cls.refresh_digests(bundle)
        return bundle, card, modifier, modifier_context

    def test_validator_accepts_minimal_target_contract(self):
        bundle = self.new_contract_bundle()
        self.assertEqual("atlas-public-bundle-1.6.0", bundle["schema_version"])
        synthesis = bundle["evidence_synthesis"]
        self.assertNotIn("terminal_classification_manifest", synthesis)
        self.assertNotIn("terminal_classification_profile", synthesis)
        self.assertNotIn("finding_axes", synthesis)
        self.assertNotIn("sign_finding_axes", synthesis)
        for card in synthesis["axis_summaries"]:
            self.assertTrue({
                "categorization_state", "terminal_classification", "terminal_reason",
                "terminal_reason_text", "missing_relationship",
                "supplemental_projection", "child_group_evidence", "exceptions",
            }.isdisjoint(card))
            self.assertEqual(
                {"reported_targets", "modifiers"}, set(card["target_contract"])
            )
            self.assertTrue(all(
                set(target) <= {
                    "key", "label", "raw", "origins", "finding_refs", "target_level",
                    "region_id", "parent_region_id", "area_id", "brodmann_label",
                }
                and "details" not in target
                and "contexts" not in target
                and "scopes" not in target
                for target in card["target_contract"]["reported_targets"]
            ))
            self.assertTrue(all(
                " ".join(re.findall(
                    r"[a-z0-9]+", str(target.get("key") or "").casefold()
                )) != "reg multiregional propagation"
                for target in card["target_contract"]["reported_targets"]
            ))
            for contribution in card.get("contributions") or []:
                self.assertTrue({
                    "projection_disposition", "counted_under_sign_id",
                    "counted_under_label", "projection_reason",
                    "projection_unselected_statistic_ids", "weight_status",
                    "potential_weight",
                }.isdisjoint(contribution))
        self.assertTrue(all(
            set(link) == {"public_sign_id"}
            for row in bundle["evidence_context"]["contexts"]
            for link in row.get("sign_links") or []
        ))
        self.assertTrue(all(
            "sign_ids" in finding
            and "exact_sign_ids" not in finding
            and "related_sign_ids" not in finding
            and len(finding["sign_ids"]) == len(set(finding["sign_ids"]))
            for source in bundle["corpus"]["sources"]
            for finding in source["findings"]
        ))
        result = self.run_validator(bundle)
        self.assertEqual(0, result.returncode, result.stderr)
        bundle["schema_version"] = "atlas-public-bundle-1.5.0"
        result = self.run_validator(bundle)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("unexpected bundle schema version", result.stderr)

    def test_required_groups_expose_temporal_localization_without_internal_prose(self):
        bundle = self.new_contract_bundle()
        sign_labels = {str(sign["id"]): sign["sign"] for sign in bundle["signs"]}
        required = {
            "SGRP:b2d45c8a9bd12b5bcf07": "Ictal tonic head version",
            "SGRP:1834989c017725d8d64a": "Paroxysmal speech disturbance",
        }
        cards = {
            (str(card["sign_id"]), card["axis"]): card
            for card in bundle["evidence_synthesis"]["axis_summaries"]
        }
        for sign_id, label in required.items():
            self.assertEqual(label, sign_labels[sign_id])
            card = cards[(sign_id, "LOCALIZATION")]
            self.assertIn(
                "Temporal",
                {target["label"] for target in card["target_contract"]["reported_targets"]},
            )
            self.assertNotRegex(
                card["plain_summary"],
                r"(?i)limit this packet|do not assign|(?<![A-Za-z0-9])F\d{3}(?![A-Za-z0-9])",
            )
            self.assertNotIn("exceptions", card)

        result = self.run_validator(bundle)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_validator_accepts_mapped_modifier_without_count_or_weight_effect(self):
        bundle, card, modifier, _context = (
            self.bundle_with_mapped_propagation_modifier()
        )
        self.assertTrue(set(modifier["finding_refs"]).isdisjoint(
            card["row_finding_refs"]
        ))
        self.assertEqual(card["row_finding_count"], len(card["row_finding_refs"]))
        self.assertEqual(card["row_work_count"], len(card["contributions"]))

        result = self.run_validator(bundle)

        self.assertEqual(0, result.returncode, result.stderr)

    def test_validator_rejects_uncontracted_evidence_context_fields(self):
        def add_sequence_component_private_field(context):
            component_id = "SEQCOMP:public-contract-test"
            finding_context = context["contexts"][0]
            context["sequence_components_by_id"][component_id] = {
                "component_id": component_id,
                "finding_ref": str(finding_context["finding_ref"]),
                "sign_id": "SRC:public-contract-test",
                "phase": "ICTAL",
                "component_ordinal": 1,
                "public_sign_ids": [],
                "private_audit_note": "must not cross the public boundary",
            }
            finding_context["sequence_component_ids"].append(component_id)

        cases = {
            "top level": (
                lambda context: context.__setitem__(
                    "private_release_audit", {"owner_only": True}
                ),
                "evidence-context top-level fields changed",
            ),
            "context row": (
                lambda context: context["contexts"][0].__setitem__(
                    "private_audit_note", "must not cross the public boundary"
                ),
                "evidence-context row fields changed",
            ),
            "relationship collection": (
                lambda context: context["relationships"].__setitem__(
                    "private_review_links", []
                ),
                "evidence-context relationship fields changed",
            ),
            "finding-location row": (
                lambda context: context["relationships"][
                    "finding_locations"
                ][0].__setitem__("private_audit_note", "owner only"),
                "finding-location fields changed",
            ),
            "classification row": (
                lambda context: context["relationships"][
                    "classifications"
                ][0].__setitem__("private_audit_note", "owner only"),
                "classification-link fields changed",
            ),
            "assertion row": (
                lambda context: next(iter(
                    context["assertions_by_id"].values()
                )).__setitem__("private_audit_note", "owner only"),
                "axis-assertion fields changed",
            ),
            "statistic row": (
                lambda context: next(iter(
                    context["statistics_by_id"].values()
                )).__setitem__("private_audit_note", "owner only"),
                "statistic-context fields changed",
            ),
            "sequence-component row": (
                add_sequence_component_private_field,
                "sequence-component fields changed",
            ),
            "accounting": (
                lambda context: context["accounting"].__setitem__(
                    "private_audit_count", 1
                ),
                "evidence-context accounting does not reconcile",
            ),
        }
        for label, (mutate, expected) in cases.items():
            with self.subTest(label=label):
                bundle = self.new_contract_bundle()
                mutate(bundle["evidence_context"])
                self.refresh_digests(bundle)

                result = self.run_validator(bundle)

                self.assertNotEqual(0, result.returncode)
                self.assertIn(expected, result.stderr)

    def test_validator_rejects_invalid_or_placement_driving_modifiers(self):
        cases = {
            "unexpected field": (
                lambda _bundle, _card, modifier, _context:
                modifier.__setitem__("details", []),
                "modifier fields changed",
            ),
            "unknown type": (
                lambda _bundle, _card, modifier, _context:
                modifier.__setitem__("modifier_type", "PLACEMENT"),
                "unknown target modifier",
            ),
            "count leakage": (
                lambda _bundle, card, modifier, context: (
                    card["row_finding_refs"].append(modifier["finding_refs"][0]),
                    card["context_ids"].append(context["context_id"]),
                    card.__setitem__("row_finding_count", card["row_finding_count"] + 1),
                ),
                "modifier-only finding entered placement counts",
            ),
            "weight leakage": (
                lambda _bundle, card, _modifier, context: (
                    card["row_work_ids"].append(str(context["source_work_id"])),
                    card["contributions"].append({
                        "work_id": str(context["source_work_id"]),
                    }),
                    card.__setitem__("row_work_count", card["row_work_count"] + 1),
                ),
                "modifier-only work entered placement weight",
            ),
        }
        for label, (mutate, expected) in cases.items():
            with self.subTest(label=label):
                bundle, card, modifier, context = (
                    self.bundle_with_mapped_propagation_modifier()
                )
                mutate(bundle, card, modifier, context)
                self.refresh_digests(bundle)
                result = self.run_validator(bundle)
                self.assertNotEqual(0, result.returncode)
                self.assertIn(expected, result.stderr)

    def test_validator_rejects_propagation_hidden_in_reported_target_payload(self):
        bundle = self.new_contract_bundle()
        card = next(
            row for row in bundle["evidence_synthesis"]["axis_summaries"]
            if row["target_contract"]["reported_targets"]
        )
        card["target_contract"]["reported_targets"].append({
            "key": "RAW:propagation-context",
            "label": "Propagation",
            "raw": ["REG:MULTIREGIONAL_PROPAGATION"],
            "origins": ["STRUCTURED_SOURCE_AXIS_ASSERTION"],
            "finding_refs": [card["row_finding_refs"][0]],
            "target_level": "UNRESOLVED",
        })
        self.refresh_digests(bundle)

        result = self.run_validator(bundle)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("propagation is not a reported target", result.stderr)

    def test_validator_rejects_sign_axis_summary_divergence(self):
        mutations = {
            "targets": lambda summary: summary["reported_target_keys"].append(
                "REG:OCCIPITAL"
            ),
            "contexts": lambda summary: summary.__setitem__("context_ids", []),
            "modifiers": lambda summary: summary.__setitem__("modifiers", []),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                bundle, card, _modifier, _context = (
                    self.bundle_with_mapped_propagation_modifier()
                )
                summary = next(
                    row for row in bundle["evidence_context"]["relationships"][
                        "sign_axis_summaries"
                    ]
                    if str(row["synthesis_id"]) == str(card["synthesis_id"])
                )
                mutate(summary)
                self.refresh_digests(bundle)
                result = self.run_validator(bundle)
                self.assertNotEqual(0, result.returncode)
                self.assertIn(
                    "sign-axis summary differs from its referenced card",
                    result.stderr,
                )

    def test_validator_rejects_duplicate_summary_and_inexact_accounting(self):
        bundle = self.new_contract_bundle()
        summaries = bundle["evidence_context"]["relationships"][
            "sign_axis_summaries"
        ]
        summaries.append(json.loads(json.dumps(summaries[0])))
        bundle["evidence_context"]["accounting"]["sign_axis_summaries"] += 1
        self.refresh_digests(bundle)
        duplicate = self.run_validator(bundle)
        self.assertNotEqual(0, duplicate.returncode)
        self.assertIn("duplicate sign-axis summary", duplicate.stderr)

        bundle = self.new_contract_bundle()
        bundle["evidence_context"]["accounting"]["sign_axis_summaries"] += 1
        self.refresh_digests(bundle)
        accounting = self.run_validator(bundle)
        self.assertNotEqual(0, accounting.returncode)
        self.assertIn("evidence-context accounting does not reconcile", accounting.stderr)

        bundle = self.new_contract_bundle()
        bundle["evidence_context"]["accounting"].pop("structured_propagation")
        self.refresh_digests(bundle)
        missing = self.run_validator(bundle)
        self.assertNotEqual(0, missing.returncode)
        self.assertIn("evidence-context accounting does not reconcile", missing.stderr)

    def test_validator_rejects_axis_summary_exceptions_field(self):
        bundle = self.new_contract_bundle()
        bundle["evidence_synthesis"]["axis_summaries"][0]["exceptions"] = [
            "Clinically clean prose still belongs outside the public card contract."
        ]
        payload = dict(bundle)
        payload.pop("semantic_digest")
        bundle["semantic_digest"] = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode()).hexdigest()
        result = self.run_validator(bundle)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("obsolete public axis-card field is present", result.stderr)

    def test_validator_rejects_semantic_relation_on_active_sign_link(self):
        bundle = self.new_contract_bundle()
        link = next(
            link
            for row in bundle["evidence_context"]["contexts"]
            for link in row.get("sign_links") or []
        )
        link["relation"] = "EXACT"
        context = bundle["evidence_context"]
        context_payload = dict(context)
        context_payload.pop("semantic_digest")
        context["semantic_digest"] = hashlib.sha256(json.dumps(
            context_payload, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False,
        ).encode()).hexdigest()
        payload = dict(bundle)
        payload.pop("semantic_digest")
        bundle["semantic_digest"] = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode()).hexdigest()

        result = self.run_validator(bundle)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("sign link must be a neutral active membership", result.stderr)

    def test_validator_rejects_legacy_finding_sign_membership_fields(self):
        bundle = self.new_contract_bundle()
        finding = bundle["corpus"]["sources"][0]["findings"][0]
        finding["related_sign_ids"] = []
        payload = dict(bundle)
        payload.pop("semantic_digest")
        bundle["semantic_digest"] = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode()).hexdigest()

        result = self.run_validator(bundle)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("finding sign membership must use sign_ids only", result.stderr)

    def test_validator_rejects_internal_markers_in_public_summary_prose(self):
        bundle = self.new_contract_bundle()
        bundle["evidence_synthesis"]["axis_summaries"][0]["plain_summary"] = (
            "Limit this packet to F019; do not assign this relationship."
        )
        payload = dict(bundle)
        payload.pop("semantic_digest")
        bundle["semantic_digest"] = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode()).hexdigest()
        result = self.run_validator(bundle)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("public display prose", result.stderr)


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


class _SourcePanelDom(HTMLParser):
    """Collect source-panel structure without depending on formatting strings."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.paper_labels = []
        self.paper_groups_in_class = []
        self.finding_count = 0
        self.source_family_lists = 0
        self.nested_family_scrolls = 0
        self._paper_label = None

    def handle_starttag(self, tag, attrs):
        classes = set(dict(attrs).get("class", "").split())
        ancestors = [item[1] for item in self.stack]
        if tag == "li" and "ev-paper-group" in classes:
            self.paper_groups_in_class.append(any(
                "ev-class-group" in values for values in ancestors
            ))
        if tag == "article" and "reviewed-card-evidence" in classes:
            self.finding_count += 1
        if tag == "span" and "ev-paper-file" in classes:
            self._paper_label = []
        if "source-family-list" in classes:
            self.source_family_lists += 1
        if "syn-family-scroll" in classes:
            self.nested_family_scrolls += 1
        self.stack.append((tag, classes))

    def handle_data(self, data):
        if self._paper_label is not None:
            self._paper_label.append(data)

    def handle_endtag(self, tag):
        if (
            tag == "span" and self.stack
            and "ev-paper-file" in self.stack[-1][1]
        ):
            self.paper_labels.append("".join(self._paper_label).strip())
            self._paper_label = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


class NeutralMembershipRendererTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="semiology-neutral-membership."
        )
        cls.root = Path(cls.temporary.name) / "public"
        shutil.copytree(
            ROOT,
            cls.root,
            ignore=shutil.ignore_patterns(".git", "docs", "__pycache__", "*.pyc"),
        )
        (cls.root / "data" / "atlas_bundle.json").write_text(
            json.dumps(AtlasBundleValidatorTest.neutral_membership_bundle()),
            encoding="utf-8",
        )
        saved_modules = {
            name: sys.modules.pop(name, None)
            for name in ("brain_atlas", "clinical_sign_cards")
        }
        try:
            cls.render = runpy.run_path(
                str(cls.root / "generator" / "gen_study.py")
            )
        finally:
            for name, module in saved_modules.items():
                sys.modules.pop(name, None)
                if module is not None:
                    sys.modules[name] = module

    @classmethod
    def tearDownClass(cls):
        generator_path = str(cls.root / "generator")
        while generator_path in sys.path:
            sys.path.remove(generator_path)
        cls.temporary.cleanup()

    def test_every_active_sign_link_reaches_all_evidence_views(self):
        context = self.render["CONTEXT"]
        statistics_by_finding = {}
        for statistic_id, statistic in context.statistics.items():
            statistics_by_finding.setdefault(
                str(statistic.get("finding_ref") or ""), []
            ).append(statistic_id)
        for finding_ref, finding_context in context.contexts_by_ref.items():
            expected = {
                str(link["public_sign_id"])
                for link in finding_context.get("sign_links") or []
            }
            if not expected:
                continue
            self.assertEqual(
                expected,
                set(context.public_sign_ids_for_findings([finding_ref])),
                finding_ref,
            )
            for statistic_id in statistics_by_finding.get(finding_ref, []):
                self.assertTrue(
                    expected.issubset(
                        context.public_sign_ids_for_statistics([statistic_id])
                    ),
                    statistic_id,
                )

    def test_renderer_consumes_the_shared_clinical_card_projection(self):
        projection = self.render["CLINICAL_CARD_PROJECTION"]
        self.assertEqual(
            {str(row["id"]) for row in self.render["BROWSE_SIGNS"]},
            projection["browse_sign_ids"],
        )
        self.assertEqual(set(projection["by_sign_id"]), projection["browse_sign_ids"])

    def test_former_component_mapping_is_discoverable_without_identity_semantics(self):
        finding_ref = (
            "005b726587cb0812d005e9166b1191028be677a82ffd02c74d947a1f0718f85a:F037"
        )
        component_sign_id = "SGRP:fd24c9d1269173ceb2ed"
        context = self.render["CONTEXT"]
        links = context.contexts_by_ref[finding_ref]["sign_links"]
        component_link = next(
            link for link in links
            if str(link["public_sign_id"]) == component_sign_id
        )
        self.assertEqual({"public_sign_id": component_sign_id}, component_link)
        self.assertIn(
            component_sign_id,
            context.public_sign_ids_for_findings([finding_ref]),
        )
        source_finding = self.render["ledger_by_ref"][finding_ref]["finding"]
        self.assertIn(component_sign_id, {
            str(sign_id) for sign_id in source_finding["sign_ids"]
        })
        self.assertNotIn("exact_sign_ids", source_finding)
        self.assertNotIn("related_sign_ids", source_finding)

        cards = self.render["SYNTHESIS_CARDS_BY_SIGN"][component_sign_id]
        self.assertTrue(all(
            card["preferred_label"] == "Tonic arm posturing"
            and "oculomotor-onset evolving motor phenotype" not in {
                str(value).casefold() for value in card.get("identity_labels") or []
            }
            for card in cards
        ))
        self.assertNotRegex(
            json.dumps(component_link, sort_keys=True),
            r"(?i)exact|synonym|identity|relation",
        )
        filename = "sign-" + hashlib.sha256(
            component_sign_id.encode()
        ).hexdigest()[:24] + ".html"
        fragment = self.render["detail_fragments"][filename]
        self.assertNotIn('class="ev-map', fragment)
        self.assertNotIn(">Direct match<", fragment)
        self.assertNotIn(">Related finding<", fragment)

    def test_mapped_propagation_modifier_renders_only_as_unobtrusive_note(self):
        sign_id = "SRC:836d398e94802e9afbf4"
        filename = "sign-" + hashlib.sha256(sign_id.encode()).hexdigest()[:24] + ".html"
        fragment = self.render["detail_fragments"][filename]
        self.assertEqual(1, fragment.count("Propagation noted in source context."))
        self.assertIn('class="axis-modifier-note"', fragment)
        self.assertNotIn(">Propagation<", fragment)

    def test_sign_card_uses_only_the_owner_approved_clinical_fields(self):
        sign_id = "SGRP:a1e45e058d9faedf71f8"
        filename = "sign-" + hashlib.sha256(sign_id.encode()).hexdigest()[:24] + ".html"
        fragment = self.render["detail_fragments"][filename]
        labels = re.findall(r'<span class="d-label">([^<]+)</span>', fragment)
        self.assertEqual(
            [
                "Brain Region / Localization", "Lateralization",
                "Phase of Seizure", "ILAE Classification",
                "Lüders Classification", "Brief Summary",
            ],
            labels[:6],
        )
        self.assertIn('>Source<', fragment)
        self.assertNotIn("Brodmann areas", fragment)
        self.assertNotIn("Evidence basis", fragment)
        self.assertNotIn("Source review pending", fragment)

    def test_sign_card_uses_the_approved_four_row_desktop_layout(self):
        html = self.render["h"]
        self.assertIn(
            ".detail-inner{display:grid;grid-template-columns:repeat(6,minmax(0,1fr))",
            html,
        )
        self.assertIn(".d-loc,.d-lat,.d-phase{grid-column:span 2}", html)
        self.assertIn(".d-classification{grid-column:span 3}", html)
        self.assertIn(
            ".evidence-overview,.card-source-shell{grid-column:1/-1}", html
        )

    def test_expanded_sign_banners_inherit_the_parent_group_color(self):
        html = self.render["h"]
        self.assertRegex(
            html,
            r'class="region-section"[^>]+style="--group-color:#[0-9a-f]{6}"',
        )
        self.assertIn("background:var(--group-color,var(--navy));color:#fff", html)
        self.assertRegex(html, r'class="pill"[^>]+style="--rc:#[0-9a-f]{6}"')
        self.assertIn("background:var(--rc,var(--navy));color:#fff", html)
        self.assertNotIn("background:#f4f7fa;color:var(--navy)", html)
        self.assertIn(
            "background:color-mix(in srgb,var(--group-color,var(--navy)) 72%,#111827);color:#fff",
            html,
        )
        self.assertNotIn("background:rgba(255,255,255,.88)", html)
        self.assertNotIn("General or source-wide", html)

    def test_phase_display_normalizes_the_category_and_keeps_source_wording(self):
        display = self.render["phase_of_seizure_display"]({
            "phase": "Electrical stimulation; not an ictal/postictal seizure phase",
            "phase_values": [
                "Electrical stimulation; not an ictal/postictal seizure phase"
            ],
        })
        self.assertIn("Stimulation induced", display)
        self.assertNotIn(">Ictal<", display)
        self.assertNotIn("Post ictal</span>", display)
        self.assertIn(
            "Electrical stimulation; not an ictal/postictal seizure phase", display
        )

    def test_phase_display_prefers_a_structured_normalized_category(self):
        display = self.render["phase_of_seizure_display"]({
            "phase": "Ictal observation during stimulation",
            "normalized_phase_category": "STIMULATION_INDUCED",
        })
        self.assertIn(">Stimulation induced<", display)
        self.assertNotIn(">Ictal<", display)

    def test_axis_modifier_uses_plain_cohort_context_language(self):
        display = self.render["axis_modifier_note"]({
            "target_contract": {"modifiers": [{
                "key": "COHORT_CONTEXT", "modifier_type": "COHORT_CONTEXT",
            }]},
        })
        self.assertEqual(
            '<span class="axis-modifier-note">Cohort context noted in source.</span>',
            display,
        )

    def test_source_history_groups_only_actual_evidence_classes(self):
        cards = self.render["SYNTHESIS_CARDS"]
        card = next(
            row for row in cards
            if any(
                str(item.get("evidence_class") or "") in {"I", "II", "III"}
                for item in row.get("contributions") or []
            ) and self.render["ledger_evidence_by_cardid"].get(row["sign_id"])
        )
        expected_classes = {
            str(item["evidence_class"])
            for item in card.get("contributions") or []
            if str(item.get("evidence_class") or "") in {"I", "II", "III"}
        }
        html, linked_count, _ = self.render["ledger_evidence_block"](card["sign_id"])
        self.assertGreater(linked_count, 0)
        self.assertTrue(any(f"Class {value}" in html for value in expected_classes))
        self.assertIn(
            '<details class="history-results ev-class-group" open>', html
        )
        self.assertNotIn("Class UNCLASSIFIED", html)

        statistical_card = next(
            row for row in cards
            if any(
                finding.get("statistics")
                for source in self.render["source_groups_for_sign"](row["sign_id"]).values()
                for finding, _relation in source["findings"]
            )
        )
        statistical_html, _, _ = self.render["ledger_evidence_block"](
            statistical_card["sign_id"]
        )
        self.assertRegex(
            statistical_html,
            r"Result reported in this paper:|results reported in this paper",
        )

    def test_source_history_contains_unclassified_manuscripts_without_losing_data(self):
        sign_id = "SGRP:0cfcf10847ac2585d07e"  # Tonic motor phenomenon
        groups = self.render["source_groups_for_sign"](sign_id)
        roh = next(group for group in groups.values() if group["label"] == "Roh · 1996")
        self.assertEqual("", str(roh.get("evidence_class") or ""))

        html, linked_count, _ = self.render["ledger_evidence_block"](sign_id)
        parsed = _SourcePanelDom()
        parsed.feed(html)

        self.assertGreater(linked_count, 0)
        self.assertCountEqual(
            [group["label"] for group in groups.values()], parsed.paper_labels,
        )
        self.assertEqual(len(groups), len(parsed.paper_groups_in_class))
        self.assertTrue(all(parsed.paper_groups_in_class))
        self.assertEqual(
            sum(len(group["findings"]) for group in groups.values()),
            parsed.finding_count,
        )
        self.assertIn("Other sources", html)
        self.assertNotIn("Class UNCLASSIFIED", html)

    def test_source_panel_has_one_scroll_owner(self):
        html, _, _ = self.render["ledger_evidence_block"](
            "SGRP:0cfcf10847ac2585d07e"
        )
        parsed = _SourcePanelDom()
        parsed.feed(html)

        self.assertEqual(1, parsed.source_family_lists)
        self.assertEqual(0, parsed.nested_family_scrolls)

    def test_default_browser_excludes_source_less_signs(self):
        visible_names = {row["sign"] for row in self.render["BROWSE_SIGNS"]}
        self.assertNotIn("Pallesthesia / vibratory aura (rare)", visible_names)
        self.assertNotIn("Alien limb phenomenon (ictal)", visible_names)
        self.assertIn("Pallesthesia / vibratory aura (rare)", {row["sign"] for row in self.render["data"]})
        self.assertTrue(all(
            self.render["ledger_evidence_by_cardid"].get(row["id"])
            for row in self.render["BROWSE_SIGNS"]
        ))

    def test_propagation_is_context_not_a_browse_region(self):
        sign = next(
            row for row in self.render["data"]
            if row["id"] == "SRC:836d398e94802e9afbf4"
        )
        self.assertEqual(
            ["Parietal"], self.render["public_browse_regions"](sign)
        )

    def test_luders_card_merges_the_two_classification_schemes_without_root_repetition(self):
        sign = next(row for row in self.render["data"] if row["sign"] == "Fear aura")
        display = self.render["classification_card_display"](
            sign["id"], ("LUDERS_SSC_1998", "LUDERS_5D_2005"),
        )
        self.assertNotIn("Seizure &gt; Seizure", display)
        self.assertNotEqual("Seizure", display)

    def test_luders_finding_groups_merge_ssc_and_5d(self):
        context = self.render["CONTEXT"]
        term_id = next(
            row["node_id"] for row in self.render["CLASSIFICATIONS"]["nodes"]
            if row["scheme_id"] == "LUDERS_5D_2005" and row.get("node_kind") == "TERM"
        )
        original = context.classification_nodes_for_findings
        calls = []
        context.classification_nodes_for_findings = lambda _refs, scheme: calls.append(scheme) or [term_id]
        try:
            labels = self.render["finding_classification_labels"](
                ["fixture"], ("LUDERS_SSC_1998", "LUDERS_5D_2005"),
            )
        finally:
            context.classification_nodes_for_findings = original
        self.assertEqual(["LUDERS_SSC_1998", "LUDERS_5D_2005"], calls)
        self.assertEqual(1, len(labels))

    def test_reader_facing_browse_and_organizer_vocabulary_is_approved(self):
        output = self.render["h"] + "".join(self.render["deferred_fragments"].values())
        self.assertIn("Sign A&ndash;Z", output)
        self.assertIn("Sign Z&ndash;A", output)
        self.assertIn("L&uuml;ders Classification", output)
        self.assertNotIn("Semiology A&ndash;Z", output)
        self.assertNotIn("L&uuml;ders 5D", output)

    def test_brief_summary_groups_claims_once_per_manuscript(self):
        sign_id = "SGRP:a1e45e058d9faedf71f8"
        summary = self.render["source_readable_summary"](sign_id)
        labels = re.findall(r'class="summary-manuscript">([^<]+)</span>', summary)
        self.assertTrue(labels)
        self.assertEqual(len(labels), len(set(labels)))
        source_html, _linked_count, _search = self.render["ledger_evidence_block"](sign_id)
        source_labels = re.findall(r'class="ev-paper-file">([^<]+)</span>', source_html)
        self.assertEqual(labels, source_labels)
        self.assertNotIn("The reviewed evidence", summary)
        self.assertNotIn("the source", summary.casefold())


class CanonicalV16SourceBackedSignTest(unittest.TestCase):
    def test_shared_projection_test_loads_the_shipped_public_projector(self):
        source = inspect.getsource(self.test_shared_clinical_card_projection_contract)
        self.assertIn('ROOT / "tools" / "clinical_sign_cards.py"', source)
        self.assertNotIn("CANONICAL_WEBSITE", source)

    def test_shared_clinical_card_projection_contract(self):
        module_path = ROOT / "tools" / "clinical_sign_cards.py"
        self.assertTrue(module_path.is_file())
        spec = importlib.util.spec_from_file_location("clinical_sign_cards", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        bundle = json.loads((ROOT / "data" / "atlas_bundle.json").read_text())
        projection = module.project_clinical_sign_cards(bundle)
        cards = projection["cards"]
        self.assertEqual(1073, len(cards))
        by_id = projection["by_sign_id"]
        self.assertNotIn("66", by_id)
        self.assertNotIn("71", by_id)
        fear = next(card for card in cards if card["sign"] == "Fear aura")
        self.assertTrue(fear["source_groups"])
        self.assertIn("phase", fear)
        self.assertIn("luders", fear["classifications"])
        self.assertTrue(fear["summary_manuscripts"])
        cohort = by_id["SRC:836d398e94802e9afbf4"]
        self.assertIn(
            "Cohort context noted in source.",
            cohort["axes"]["localization"]["modifiers"],
        )

    def test_current_v16_bundle_has_1073_source_backed_browser_signs(self):
        bundle_path = ROOT / "data" / "atlas_bundle.json"
        bundle = json.loads(bundle_path.read_text())
        self.assertEqual("atlas-public-bundle-1.6.0", str(bundle["schema_version"]))
        linked_sign_ids = {
            str(summary["sign_id"])
            for summary in bundle["evidence_synthesis"]["axis_summaries"]
            if summary.get("row_finding_refs")
        }
        names_by_id = {str(row["id"]): row["sign"] for row in bundle["signs"]}
        self.assertEqual(1073, len(linked_sign_ids))
        self.assertNotIn("66", linked_sign_ids)
        self.assertNotIn("71", linked_sign_ids)
        self.assertEqual("Pallesthesia / vibratory aura (rare)", names_by_id["66"])
        self.assertEqual("Alien limb phenomenon (ictal)", names_by_id["71"])

    def test_canonical_browser_groups_every_source_backed_sign(self):
        public_root = ROOT
        with tempfile.TemporaryDirectory(prefix="semiology-public-browser.") as directory:
            copied_root = Path(directory) / "website"
            shutil.copytree(
                public_root, copied_root,
                ignore=shutil.ignore_patterns(".git", "docs", "__pycache__", "*.pyc"),
            )
            generator_path = str(copied_root / "generator")
            saved_brain_atlas = sys.modules.pop("brain_atlas", None)
            saved_clinical_sign_cards = sys.modules.pop("clinical_sign_cards", None)
            try:
                render = runpy.run_path(str(copied_root / "generator" / "gen_study.py"))
            finally:
                sys.modules.pop("brain_atlas", None)
                sys.modules.pop("clinical_sign_cards", None)
                if saved_brain_atlas is not None:
                    sys.modules["brain_atlas"] = saved_brain_atlas
                if saved_clinical_sign_cards is not None:
                    sys.modules["clinical_sign_cards"] = saved_clinical_sign_cards
                while generator_path in sys.path:
                    sys.path.remove(generator_path)
        browse_ids = {str(row["id"]) for row in render["BROWSE_SIGNS"]}
        grouped_ids = {
            str(row["id"])
            for region_groups in render["grouped"].values()
            for signs in region_groups.values()
            for row in signs
        }
        for region, region_groups in render["grouped"].items():
            rendered_ids = [
                str(row["id"])
                for signs in region_groups.values()
                for row in signs
            ]
            self.assertEqual(
                len(rendered_ids), len(set(rendered_ids)),
                f"sign repeated within {region}",
            )
        self.assertEqual(1073, len(browse_ids))
        self.assertEqual(grouped_ids, browse_ids)
        self.assertNotIn("66", grouped_ids)
        self.assertNotIn("71", grouped_ids)


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

    def test_brodmann_renderer_embeds_reference_plate_images(self):
        for view_name in self.render["BA"].VIEWS:
            view = re.search(
                rf'<svg[^>]*data-view="{re.escape(view_name)}"[^>]*>(.*?)</svg>',
                self.render["brain_fold"],
                re.DOTALL,
            )
            self.assertIsNotNone(view, view_name)
            self.assertIn('<image class="brain-photo"', view.group(1), view_name)

    def test_compound_brodmann_relationship_reaches_all_explicit_areas(self):
        sign_id = 76  # Ictal contralateral tonic eye deviation
        source_sign_id = str(sign_id)
        expected = {"24", "25", "32"}
        summary = next(
            row for row in self.render["ATLAS"]["evidence_context"]
            ["relationships"]["sign_axis_summaries"]
            if str(row["axis"]) == "LOCALIZATION"
            and source_sign_id in {
                str(value) for value in row["public_sign_ids"]
            }
        )
        self.assertTrue(expected.issubset({
            str(value) for value in summary["brodmann_area_ids"]
        }))
        self.assertTrue(expected.issubset(set(
            self.render["SIGN_LOCATION_BY_ID"][sign_id]["areas"]
        )))
        area_lobe = self.render["BA"].AREAS["25"]["lobe"]
        self.assertIn(source_sign_id, {
            str(row["id"])
            for row in self.render["area_signs_by_region"][area_lobe].get("25", [])
        })

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

    def test_brodmann_map_honors_nonregion_filters_and_organization(self):
        js = self.render["JS"]
        brain = js.split("/* ---------- Brodmann map ---------- */", 1)[1].split(
            "const searchInput=", 1
        )[0]
        state_match = re.search(
            r"function brainMapState\(\)\{(?P<body>.*?)\n  \}",
            brain,
            re.DOTALL,
        )
        self.assertIsNotNone(
            state_match,
            "generated map has no shared state for top filters and organization",
        )
        state = state_match.group("body")
        for control in (
            "appliedQuery", "fPhase.value", "fLat.value", "fEvid.value",
            "browseMode.value",
        ):
            self.assertIn(control, state)
        self.assertNotIn("fRegion", state)
        self.assertNotIn("regionOrderMode", state)

        render = brain.split("function render(tid){", 1)[1].split(
            "function esc", 1
        )[0]
        self.assertIn("visibleBrainSigns(t", render)
        self.assertNotIn("const n=t.signs.length", render)
        self.assertNotIn("list.innerHTML=t.signs.map", render)
        density = re.search(
            r"function refreshBrainDensity\(\).*?visibleBrainSigns",
            brain,
            re.DOTALL,
        )
        self.assertIsNotNone(density)
        trace = brain.split("function traceSign(sid,scroll){", 1)[1].split(
            "/* clicking an area */", 1
        )[0]
        self.assertIn("brainSignIsVisible", trace)
        self.assertIn("organizeBrainSigns", brain)
        filter_all = js.split("function filterAll(){", 1)[1].split(
            "function setBrowseMode", 1
        )[0]
        self.assertIn("refreshBrainMap();", filter_all)
        self.assertEqual(
            ["Stimulation induced"],
            self.render["phase_filter_categories"](
                {
                    "normalized_phase_category": ["STIMULATION_INDUCED"],
                    "phase": "ictal stimulation wording",
                    "phase_values": ["Ictal"],
                }
            ),
        )

    def test_brodmann_map_filter_indicator_is_accessible_compact_and_shared(self):
        indicator = re.search(
            r'<[^>]+id="brain-filter-indicator"[^>]*>',
            self.render["brain_fold"],
        )
        self.assertIsNotNone(
            indicator,
            "generated Brodmann map has no visible active-filter indicator",
        )
        tag = indicator.group(0)
        self.assertIn("hidden", tag)
        self.assertRegex(tag, r'aria-(?:label|live)="[^"]+"')
        style = re.search(
            r"\.brain-filter-indicator\{(?P<body>[^}]*)\}",
            self.render["CSS"],
        )
        self.assertIsNotNone(style)
        for property_name in ("font-size:", "padding:", "border-radius:"):
            self.assertIn(property_name, style.group("body"))
        brain = self.render["JS"].split(
            "/* ---------- Brodmann map ---------- */", 1
        )[1].split("const searchInput=", 1)[0]
        self.assertIn("function refreshBrainFilterIndicator(){", brain)
        indicator_update = brain.split(
            "function refreshBrainFilterIndicator(){", 1
        )[1].split("\n  }", 1)[0]
        self.assertIn("brainMapState()", indicator_update)
        self.assertIn(
            'id="search-clear" type="button" aria-label="Clear search and Brodmann map selection">'
            "Clear</button>",
            self.render["h"],
        )
        self.assertNotIn(".search-clear{display:none}", self.render["CSS"])
        self.assertIn(
            ".search-wrap{flex:1 1 100%;max-width:none}", self.render["CSS"]
        )
        self.assertIn("document.addEventListener('atlas:clear-map',clear)", brain)
        self.assertIn(
            "document.dispatchEvent(new Event('atlas:clear-map'))",
            self.render["JS"],
        )

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
        self.assertNotIn(">Citation</a>", footer)
        self.assertNotIn("CITATION.cff", footer)
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

    def test_broad_aura_reports_remain_discoverable_in_the_aura_group(self):
        groups = self.render["classification_trees"]["LUDERS_5D_2005"]["groups"]
        aura = next(node for node in groups if node["label"] == "Aura")
        signs = {str(row["id"]): row["sign"] for row in self.render["data"]}
        broad_labels = {signs[str(sign_id)] for sign_id in aura["broad_sign_ids"]}
        all_labels = {signs[str(sign_id)] for sign_id in aura["all_sign_ids"]}
        self.assertTrue({"Aura", "Aura present"}.issubset(broad_labels))
        self.assertTrue(broad_labels.issubset(all_labels))

    def test_sign_fragment_prioritizes_compact_summary_and_closed_source_panel(self):
        sign_id = "SGRP:a1e45e058d9faedf71f8"
        filename = "sign-" + hashlib.sha256(sign_id.encode()).hexdigest()[:24] + ".html"
        fragment = self.render["detail_fragments"][filename]
        self.assertRegex(fragment, r'class="[^"]*\bevidence-overview\b[^"]*"')
        self.assertIn('class="summary-manuscript"', fragment)
        self.assertIn('class="d-row card-source-shell"', fragment)
        self.assertNotIn("The embedded evidence", fragment)
        self.assertNotIn("REG:TEMPORAL", fragment)
        self.assertNotRegex(fragment, r'<details class="[^"]*card-source-shell[^"]*" open')

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

    def test_synthesis_uses_the_shared_lateralization_target(self):
        sign_id = "SGRP:f39e29bedd8219a01713"
        filename = "sign-" + hashlib.sha256(sign_id.encode()).hexdigest()[:24] + ".html"
        fragment = self.render["detail_fragments"][filename]
        self.assertIn(">Does not lateralize<", fragment)
        self.assertIn(">Frontal<", fragment)
        self.assertIn(">Temporal<", fragment)
        self.assertNotIn(
            "Localization depends on the described subtype or context.", fragment
        )
        self.assertNotIn("Predominant, with exceptions", fragment)
        self.assertNotIn("Open the evidence for the balance and exceptions", fragment)

    def test_late_forced_head_version_names_the_frontal_eye_field_without_map_metadata(self):
        filename = "sign-" + hashlib.sha256(b"12").hexdigest()[:24] + ".html"
        fragment = self.render["detail_fragments"][filename]
        self.assertIn(">Contralateral<", fragment)
        self.assertIn(">Frontal<", fragment)
        self.assertIn("contralateral frontal eye field", fragment.casefold())
        self.assertNotIn('data-ba="8"', fragment)

    def test_forced_eye_version_separates_network_from_onset_lobe_without_map_metadata(self):
        filename = "sign-" + hashlib.sha256(b"76").hexdigest()[:24] + ".html"
        fragment = self.render["detail_fragments"][filename]
        self.assertIn(">Contralateral<", fragment)
        self.assertIn(">Frontal<", fragment)
        self.assertIn(">Occipital<", fragment)
        self.assertNotIn('data-ba="8"', fragment)
        self.assertNotIn('data-ba="19"', fragment)
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
            for target in self.render["public_reported_targets"](card)
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

    def test_reported_targets_render_without_legacy_card_state_fields(self):
        cards = json.loads(json.dumps(self.render["SYNTHESIS_CARDS"]))
        for card in cards:
            card.pop("exceptions", None)
            for field in (
                "categorization_state", "terminal_classification",
                "terminal_reason", "terminal_reason_text", "missing_relationship",
            ):
                card.pop(field, None)
        target_card = next(
            card for card in cards
            if (card.get("target_contract") or {}).get("reported_targets")
            and card.get("contributions")
        )
        html = self.render["build_weighted_evidence"](cards)
        self.assertRegex(
            html,
            rf'<details class="lr-row"[^>]+data-card-id="{re.escape(target_card["synthesis_id"])}"',
        )
        self.assertNotIn("Evidence linked; study weight pending", html)
        self.assertNotIn("Background evidence (not counted twice)", html)
        self.assertNotIn("Needs source review", html)
        self.assertNotIn("data-card-state=", html)
        self.assertNotIn('class="lr-exceptions"', html)

    def test_propagation_is_not_rendered_as_a_target_label(self):
        html = self.render["build_weighted_evidence"](
            json.loads(json.dumps(self.render["SYNTHESIS_CARDS"]))
        )
        self.assertNotIn(">Multiregional/Propagation<", html)

    def test_context_dependent_summary_uses_the_linked_source_claim(self):
        sign_id = "SGRP:76a39c9569c7472d08d2"
        filename = "sign-" + hashlib.sha256(sign_id.encode()).hexdigest()[:24] + ".html"
        fragment = self.render["detail_fragments"][filename]
        self.assertIn(
            "Table 2 associates mydriasis with mesial frontal and mesial "
            "temporal/insular cortex",
            fragment,
        )
        self.assertIn("Contralateral", fragment)
        self.assertIn("Ipsilateral", fragment)
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
        self.assertEqual(["Temporal"], index.region_labels_for_findings(["F:source"]))

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
        for sign in self.render["BROWSE_SIGNS"]:
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
            "Occipital",
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
            "Limit this packet",
            "do not assign",
            "F019",
        ):
            self.assertNotIn(internal_text, panels)
        fear_filename = "sign-" + hashlib.sha256(b"2").hexdigest()[:24] + ".html"
        self.assertNotIn(
            "This public sign combines",
            self.render["detail_fragments"][fear_filename],
        )
        self.assertNotIn("Documented exceptions", panels)
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

    def test_weighted_evidence_uses_the_library_banner_contract(self):
        weighted = self.render["meta_fold"]
        self.assertRegex(
            weighted,
            r'<div class="lib weighted-evidence-section">\s*'
            r'<details class="[^\"]*\blib-details\b[^\"]*\breliability-fold\b[^\"]*">',
        )
        self.assertNotRegex(
            self.render["CSS"],
            r"\.reliability-fold>summary\{[^}]*background:linear-gradient",
        )
        self.assertIn(
            ".weighted-evidence-section>.reliability-fold{max-width:none",
            self.render["CSS"],
        )
        self.assertIn(
            ".weighted-evidence-section>.reliability-fold>summary{"
            "background:transparent;border:none;border-radius:0}",
            self.render["CSS"],
        )

    def test_last_updated_uses_the_site_repository_commit_timestamp(self):
        committed = subprocess.run(
            ["git", "-C", str(ROOT), "log", "-1", "--format=%cI"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        expected = datetime.fromisoformat(committed).astimezone(timezone.utc)
        self.assertEqual(
            expected,
            self.render["SITE_UPDATED_UTC"],
        )
        self.assertIn(
            f"datetime='{self.render['SITE_UPDATED_ISO']}'",
            self.render["h"],
        )

    def test_collapsed_desktop_toolbar_button_clears_update_timestamp(self):
        updated_top = int(
            re.search(r"\.last-updated\{[^}]*top:(\d+)px", self.render["CSS"]).group(1)
        )
        desktop_rule = re.search(
            r"@media\(min-width:901px\)\{\.tb-fab\{[^}]*top:(\d+)px",
            self.render["CSS"],
        )
        self.assertIsNotNone(desktop_rule)
        self.assertGreaterEqual(int(desktop_rule.group(1)), updated_top + 22)

    def test_publication_changelog_is_compact_and_below_terminology(self):
        updates = re.search(
            r'<details class="lib-details atlas-updates-details">(.*?)</details>',
            self.render["h"],
            re.DOTALL,
        )
        self.assertIsNotNone(updates)
        block = updates.group(0)
        self.assertNotRegex(block.split(">", 1)[0], r"\bopen\b")
        self.assertIn("Publication changelog", block)
        self.assertIn("v1.4.8 data", block)
        self.assertIn("<strong>v1.4</strong>", block)
        self.assertIn("<strong>v1.0&ndash;1.3</strong>", block)
        self.assertNotIn("Meaningful changes", block)
        self.assertNotIn("Small display and maintenance changes", block)
        visible_entries = [
            re.sub(r"<[^>]+>", " ", item).casefold()
            for item in re.findall(r"<li>(.*?)</li>", block, re.DOTALL)
        ]
        visible_map_filter = next(
            (
                item for item in visible_entries
                if "brodmann" in item and "filter" in item
            ),
            "",
        )
        repository = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = repository.split("## [Unreleased]", 1)[1].split(
            "\n## [", 1
        )[0]
        repository_map_filter = next(
            (
                item.casefold() for item in re.split(r"\n(?=- \*\*)", unreleased)
                if "brodmann" in item.casefold() and "filter" in item.casefold()
            ),
            "",
        )
        self.assertTrue(
            visible_map_filter and repository_map_filter,
            "map-filter change must appear in both changelogs "
            f"(visible={bool(visible_map_filter)}, repository={bool(repository_map_filter)})",
        )
        for entry in (visible_map_filter, repository_map_filter):
            for term in ("organization", "region"):
                self.assertIn(term, entry)
            self.assertTrue("indicator" in entry or "icon" in entry)
        self.assertEqual(block.count("<li>"), 6)
        for term in ("classifications", "lateralization", "localization", "anatomical regions"):
            self.assertIn(term, block)
        terminology = self.render["h"].index('<div class="abbrev">')
        changelog = self.render["h"].index('<div class="lib atlas-updates">')
        footer = self.render["h"].index('<div class="footer">')
        self.assertLess(terminology, changelog)
        self.assertLess(changelog, footer)

    def test_atlas_updates_do_not_expose_internal_implementation_terms(self):
        block = re.search(
            r'<details class="lib-details atlas-updates-details">(.*?)</details>',
            self.render["h"],
            re.DOTALL,
        ).group(0).casefold()
        for term in (
            "sqlite",
            "database",
            "ledger",
            "sign_id",
            "projection",
            "pipeline",
            "canonical",
            "provenance",
            "source-linked",
            "internal identifier",
        ):
            self.assertNotIn(term, block)

    def test_source_less_legacy_background_is_not_evidence_history(self):
        block, linked_count, search = self.render["ledger_evidence_block"](
            "__source_less__", "Legacy clinical note"
        )
        self.assertEqual(("", 0, ""), (block, linked_count, search))
        filename = "sign-" + hashlib.sha256(b"71").hexdigest()[:24] + ".html"
        self.assertNotIn(filename, self.render["detail_fragments"])


if __name__ == "__main__":
    unittest.main()
