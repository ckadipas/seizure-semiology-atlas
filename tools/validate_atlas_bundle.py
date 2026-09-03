#!/usr/bin/env python3
"""Validate the redacted current-corpus atlas bundle without private sources."""

import hashlib
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "atlas_bundle.json"
SCHEMA = "atlas-public-bundle-1.6.0"
CONTEXT_SCHEMA = "atlas-evidence-context-1.0.0"
EVIDENCE_CONTEXT_FIELDS = {
    "schema_version", "authority", "contexts", "assertions_by_id",
    "statistics_by_id", "sequence_components_by_id", "relationships",
    "accounting", "semantic_digest",
}
EVIDENCE_CONTEXT_ROW_FIELDS = {
    "context_id", "finding_ref", "source_report_id", "source_work_id", "phase",
    "sign_links", "assertion_ids", "axis_modifiers", "location_link_ids",
    "lateralization_link_ids", "classification_link_ids",
    "sequence_component_ids", "statistic_ids",
}
EVIDENCE_CONTEXT_RELATIONSHIP_FIELDS = {
    "finding_locations", "finding_lateralizations", "sign_axis_summaries",
    "statistic_signs", "statistic_assertions", "classifications",
}
FINDING_LOCATION_FIELDS = {
    "location_link_id", "finding_ref", "source_sign_id", "public_sign_ids",
    "region_id", "major_region_id", "brodmann_area_id", "assertion_id",
    "assertion_type", "assertion_text",
}
FINDING_LATERALIZATION_FIELDS = {
    "lateralization_link_id", "finding_ref", "source_sign_id",
    "public_sign_ids", "assertion_id", "laterality_code", "assertion_scope",
    "assertion_text",
}
STATISTIC_SIGN_FIELDS = {"statistic_id", "source_sign_id", "public_sign_ids"}
STATISTIC_ASSERTION_FIELDS = {"statistic_id", "assertion_id", "relation"}
CLASSIFICATION_LINK_FIELDS = {
    "classification_link_id", "subject_kind", "subject_id", "finding_ref",
    "source_sign_id", "public_sign_ids", "node_id", "relation",
    "mapping_status",
}
AXIS_ASSERTION_FIELDS = {
    "assertion_id", "finding_ref", "axis", "normalized_value",
    "assertion_scope", "reviewed_assertion_text", "locators", "support_page",
    "support_excerpt", "support_status",
}
STATISTIC_CONTEXT_FIELDS = {
    "statistic_id", "context_id", "finding_ref", "sign_links",
    "assertion_links", "family_ids",
}
SEQUENCE_COMPONENT_FIELDS = {
    "component_id", "finding_ref", "sign_id", "phase", "component_ordinal",
    "public_sign_ids",
}
CLASS_BASE = {"I": 3.0, "II": 2.0, "III": 1.0}
DIRECTNESS_MULTIPLIERS = {
    "postop": 1.5, "seeg": 1.5, "intracranial_eeg": 1.35,
    "video_eeg": 1.2, "imaging_concordance": 1.15,
    "scalp_eeg": 1.1, "review": 1.0, "none": 0.9,
}
LOCATION_LABELS = {
    "REG:TEMPORAL": "Temporal", "REG:FRONTAL": "Frontal",
    "REG:PARIETAL": "Parietal", "REG:OCCIPITAL": "Occipital",
    "REG:INSULAR": "Insular", "REG:LIMBIC": "Limbic",
    "REG:DEEP_SUBCORTICAL": "Deep/Subcortical",
}
TARGET_REQUIRED_FIELDS = {"reported_targets"}
TARGET_OPTIONAL_FIELDS = {"modifiers"}
TARGET_MODIFIER_FIELDS = {
    "key", "label", "modifier_type", "raw", "origins", "finding_refs",
    "assertion_ids",
}
BRODMANN_TARGET_LINK_FIELDS = {
    "area_id", "relation", "provenance", "projects_evidence",
}
PROJECTABLE_BRODMANN_RELATIONS = {"EXACT", "EQUIVALENT"}
CONTEXT_MODIFIER_FIELDS = {
    "modifier_reference_id", "assertion_id", "finding_ref", "axis", "key",
    "label", "modifier_type", "normalized_value", "source_sign_ids",
    "public_sign_ids", "brain_regions",
}
CONTEXT_MODIFIER_BRAIN_REGION_FIELDS = {"atlas", "source_term", "label"}
SIGN_AXIS_SUMMARY_FIELDS = {
    "sign_axis_summary_link_id", "synthesis_id", "axis", "public_sign_ids",
    "context_ids", "region_ids", "brodmann_area_ids", "reported_target_keys",
    "modifiers",
}
PROPAGATION_REGION_ID = "REG:MULTIREGIONAL_PROPAGATION"
PROPAGATION_MODIFIER_KEY = "PROPAGATION"
PRIVATE_SYNTHESIS_FIELDS = {
    "finding_axes", "sign_finding_axes",
    "terminal_classification_manifest", "terminal_classification_profile",
}
PRIVATE_CARD_FIELDS = {
    "categorization_state", "terminal_classification", "terminal_reason",
    "terminal_reason_text", "missing_relationship", "supplemental_projection",
    "child_group_evidence", "exceptions",
}
PRIVATE_CONTRIBUTION_FIELDS = {
    "projection_disposition", "counted_under_sign_id", "counted_under_label",
    "projection_reason", "projection_unselected_statistic_ids",
    "weight_status", "potential_weight",
}
REQUIRED_LOCALIZATION_REGRESSIONS = {
    "SGRP:b2d45c8a9bd12b5bcf07": "Ictal tonic head version",
    "SGRP:1834989c017725d8d64a": "Paroxysmal speech disturbance",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(values):
    return len(values) == len(set(values))


def normalized_token(value):
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))


def is_propagation_value(value):
    if isinstance(value, (list, tuple, set)):
        return any(is_propagation_value(item) for item in value)
    return normalized_token(value) in {
        "propagation", "multiregional propagation",
        "reg multiregional propagation",
    }


def public_display_prose(bundle):
    """Yield only prose fields that the public renderer may display."""
    for card in (bundle.get("evidence_synthesis") or {}).get("axis_summaries") or []:
        yield "axis_summaries.plain_summary", card.get("plain_summary")
        for value in card.get("exceptions") or []:
            yield "axis_summaries.exceptions", value
        for child in card.get("child_group_evidence") or []:
            yield "child_group_evidence.plain_summary", child.get("plain_summary")
        for target in (card.get("target_contract") or {}).get("reported_targets") or []:
            yield "reported_targets.label", target.get("label")
    for value in (bundle.get("evidence_authority") or {}).get("display_method") or []:
        yield "evidence_authority.display_method", value


def validate_public_display_prose(bundle):
    markers = ("limit this packet", "do not assign")
    finding_id = re.compile(r"(?<![A-Za-z0-9])F\d{3}(?![A-Za-z0-9])")
    for path, value in public_display_prose(bundle):
        text = str(value or "")
        require(
            not any(marker in text.casefold() for marker in markers)
            and finding_id.search(text) is None,
            f"public display prose contains internal audit text: {path}",
        )


def relationship_profile(contract):
    targets = contract.get("reported_targets") or []
    positive = [
        target for target in targets
        if str(target.get("target_level") or "").upper() != "STATUS"
        and str(target.get("key") or "").casefold() != "nonassoc"
        and " ".join(re.findall(
            r"[a-z0-9]+", str(target.get("key") or "").casefold()
        )) != "reg multiregional propagation"
    ]
    nonassociation = any(
        str(target.get("target_level") or "").upper() == "STATUS"
        or str(target.get("key") or "").casefold() == "nonassoc"
        for target in targets
    )
    return positive, nonassociation


bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
require(set(bundle) == {
    "brodmann", "classifications", "corpus", "evidence_authority",
    "evidence_context", "evidence_synthesis", "finding_locations", "schema_version",
    "semantic_digest", "signs", "source_digests",
}, "unexpected top-level bundle contract")
require(bundle["schema_version"] == SCHEMA, "unexpected bundle schema version")
require(re.fullmatch(r"[0-9a-f]{64}", bundle["semantic_digest"]) is not None,
        "invalid semantic digest")
digest_payload = dict(bundle)
digest_payload.pop("semantic_digest")
expected_digest = hashlib.sha256(json.dumps(
    digest_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
).encode("utf-8")).hexdigest()
require(bundle["semantic_digest"] == expected_digest, "semantic digest mismatch")
validate_public_display_prose(bundle)

release = (bundle.get("evidence_synthesis") or {}).get("release") or {}
updated_utc = str(release.get("updated_utc") or "")
try:
    parsed_updated_utc = datetime.fromisoformat(updated_utc.replace("Z", "+00:00"))
except ValueError as exc:
    raise ValueError("invalid release update timestamp") from exc
require(parsed_updated_utc.tzinfo is not None, "release update timestamp has no timezone")

sources = bundle["corpus"]["sources"]
findings = [finding for source in sources for finding in source["findings"]]
statistics = [statistic for finding in findings for statistic in finding["statistics"]]
signs = bundle["signs"]
source_ids = [str(source["source_sha256"]) for source in sources]
source_by_id = {str(source["source_sha256"]): source for source in sources}
source_work_ids = {str(source["work_id"]) for source in sources}
finding_refs = [finding["source_finding_ref"] for finding in findings]
statistic_ids = [statistic["statistic_id"] for statistic in statistics]
sign_ids = [str(sign["id"]) for sign in signs]
finding_set, statistic_set, sign_set = set(finding_refs), set(statistic_ids), set(sign_ids)
statistic_finding = {
    statistic["statistic_id"]: finding["source_finding_ref"]
    for finding in findings
    for statistic in finding["statistics"]
}
finding_source = {}
finding_work = {}

require(bool(source_ids) and all(source_ids) and unique(source_ids),
        "source report identities are empty or duplicated")
require(unique(finding_refs), "public finding identities are duplicated")
require(unique(statistic_ids), "public statistic identities are duplicated")
require(bool(signs) and unique(sign_ids), "public sign identities are empty or duplicated")
for source in sources:
    sha, work_id = source["source_sha256"], str(source["work_id"])
    require(re.fullmatch(r"[0-9a-f]{64}", sha) is not None, "invalid source digest")
    require(re.fullmatch(r"[0-9a-f]{64}", source["source_report_sha256"]) is not None,
            "invalid report digest")
    require(bool(work_id), "source report lacks a canonical work")
    for finding in source["findings"]:
        ref = finding["source_finding_ref"]
        finding_source[ref] = str(sha)
        finding_work[ref] = work_id
        require(ref.startswith(f"{sha}:"), "finding/source identity mismatch")
        require(bool(finding["locators"] and finding["evidence_text"]),
                "finding lacks source evidence or locator")
        require(unique([row["statistic_id"] for row in finding["statistics"]]),
                "finding duplicates a statistic")
        require(
            "sign_ids" in finding
            and {"exact_sign_ids", "related_sign_ids"}.isdisjoint(finding),
            "finding sign membership must use sign_ids only",
        )
        finding_sign_ids = [str(value) for value in finding["sign_ids"]]
        require(unique(finding_sign_ids), "finding duplicates a sign membership")
        require(all(value in sign_set for value in finding_sign_ids),
                "finding references an absent sign")

require(set(finding_source) == finding_set
        and all(source_id in source_by_id for source_id in finding_source.values()),
        "finding references an absent source report")
require(all(
    statistic_finding[statistic_id] in finding_source
    for statistic_id in statistic_set
), "statistic references an absent finding or source report")
corpus_accounting = bundle["corpus"].get("integration_accounting")
if corpus_accounting is not None:
    require(isinstance(corpus_accounting, dict),
            "corpus integration accounting is not an object")
    for key, actual in {
        "source_reports": len(source_ids),
        "public_ledger_findings": len(finding_set),
        "source_reported_statistics": len(statistic_set),
    }.items():
        if key in corpus_accounting:
            require(corpus_accounting[key] == actual,
                    f"corpus accounting {key} does not reconcile")

locations = bundle["finding_locations"]
require(set(locations) <= finding_set, "location references an absent finding")
for location in locations.values():
    require(set(location) == {"regions", "areas"}, "unexpected location fields")
    require(unique(location["regions"]) and unique(location["areas"]),
            "duplicate location link")

authority = bundle["evidence_authority"]
profiles = authority["profiles"]
profile_ids = [str(profile["work_id"]) for profile in profiles]
profile_by_id = {str(profile["work_id"]): profile for profile in profiles}
require(bool(profile_ids) and all(profile_ids) and unique(profile_ids),
        "canonical-work identities are empty or duplicated")
require(set(finding_work.values()) <= set(profile_ids)
        and source_work_ids <= set(profile_ids),
        "source report or finding work lacks a profile")
require(authority["scheme_id"] == "WEIGHT:HISTORICAL_D5D9DD2", "weight scheme changed")
require(authority["scheme_status"] == "HISTORICAL_RESTORED", "weight source status changed")
require(authority["class_base"] == CLASS_BASE, "class bases changed")
require(authority["ground_truth_multipliers"] == DIRECTNESS_MULTIPLIERS,
        "directness multipliers changed")
require(float(authority["size_cap"]) == 2.0, "size cap changed")

context = bundle["evidence_context"]
require(set(context) == EVIDENCE_CONTEXT_FIELDS,
        "evidence-context top-level fields changed")
require(context["schema_version"] == CONTEXT_SCHEMA,
        "unexpected evidence-context schema version")
require(re.fullmatch(r"[0-9a-f]{64}", context["semantic_digest"]) is not None,
        "invalid evidence-context digest")
context_digest_payload = dict(context)
context_digest_payload.pop("semantic_digest")
require(context["semantic_digest"] == hashlib.sha256(json.dumps(
    context_digest_payload, sort_keys=True, separators=(",", ":"),
    ensure_ascii=False,
).encode("utf-8")).hexdigest(), "evidence-context digest mismatch")

finding_contexts = context["contexts"]
require(all(set(row) == EVIDENCE_CONTEXT_ROW_FIELDS for row in finding_contexts),
        "evidence-context row fields changed")
context_by_finding = {str(row["finding_ref"]): row for row in finding_contexts}
context_ids = [str(row["context_id"]) for row in finding_contexts]
assertions = context["assertions_by_id"]
require(all(set(row) == AXIS_ASSERTION_FIELDS for row in assertions.values()),
        "axis-assertion fields changed")
require(all(
    str(assertion_id) == str(row["assertion_id"])
    and str(row["finding_ref"]) in finding_set
    and str(row["axis"]) in {"LOCALIZATION", "LATERALIZATION"}
    for assertion_id, row in assertions.items()
), "axis assertion identity or reference changed")
require(len(finding_contexts) == len(context_by_finding) == len(finding_set),
        "evidence context is not exactly one row per public finding")
require(set(context_by_finding) == finding_set and unique(context_ids),
        "evidence context finding identities differ from the public corpus")
source_report_ids = {str(source["source_sha256"]) for source in sources}
context_modifier_rows = []
for finding_ref, row in context_by_finding.items():
    require(row["context_id"] == f"ECTX:{finding_ref}", "noncanonical context identity")
    require(str(row["source_report_id"]) in source_report_ids,
            "context references an absent source report")
    require(str(row["source_work_id"]) in profile_by_id,
            "context references an absent canonical work")
    require(all(
        set(link) == {"public_sign_id"}
        and str(link["public_sign_id"]) in sign_set
        for link in row.get("sign_links") or []
    ), "sign link must be a neutral active membership")
    linked_public_sign_ids = [
        str(link["public_sign_id"]) for link in row.get("sign_links") or []
    ]
    require(unique(linked_public_sign_ids), "context duplicates a public sign link")
    for modifier in row.get("axis_modifiers") or []:
        require(set(modifier) == CONTEXT_MODIFIER_FIELDS,
                "finding-context modifier fields changed")
        require(
            modifier["key"] == modifier["modifier_type"]
            == PROPAGATION_MODIFIER_KEY
            and modifier["label"] == "Propagation"
            and modifier["normalized_value"] == PROPAGATION_REGION_ID,
            "unknown finding-context modifier",
        )
        modifier_brain_regions = modifier["brain_regions"]
        require(
            isinstance(modifier_brain_regions, list)
            and all(
                set(target) == CONTEXT_MODIFIER_BRAIN_REGION_FIELDS
                and all(str(target[field]) for field in target)
                for target in modifier_brain_regions
            )
            and unique([
                (str(target["atlas"]), str(target["source_term"]),
                 str(target["label"]))
                for target in modifier_brain_regions
            ]),
            "finding-context modifier brain regions are not source-linked targets",
        )
        assertion_id = str(modifier["assertion_id"])
        require(
            modifier["modifier_reference_id"] == f"AXIS_MODIFIER:{assertion_id}",
            "noncanonical finding-context modifier identity",
        )
        require(str(modifier["finding_ref"]) == finding_ref,
                "finding-context modifier points to another finding")
        require(str(modifier["axis"]) in {"LOCALIZATION", "LATERALIZATION"},
                "finding-context modifier has an invalid axis")
        require(
            unique([str(value) for value in modifier["source_sign_ids"]])
            and unique([str(value) for value in modifier["public_sign_ids"]])
            and [str(value) for value in modifier["public_sign_ids"]]
            == linked_public_sign_ids,
            "finding-context modifier public signs differ from active membership",
        )
        assertion = assertions.get(assertion_id) or {}
        require(
            str(assertion.get("finding_ref") or "") == finding_ref
            and str(assertion.get("axis") or "") == str(modifier["axis"])
            and str(assertion.get("normalized_value") or "")
            == PROPAGATION_REGION_ID,
            "finding-context modifier lacks its structured propagation assertion",
        )
        context_modifier_rows.append(modifier)

structured_propagation_assertion_ids = {
    str(assertion_id)
    for assertion_id, assertion in assertions.items()
    if str(assertion.get("normalized_value") or "") == PROPAGATION_REGION_ID
}
context_modifier_assertion_ids = [
    str(row["assertion_id"]) for row in context_modifier_rows
]
require(
    unique(context_modifier_assertion_ids)
    and set(context_modifier_assertion_ids) == structured_propagation_assertion_ids,
    "structured propagation finding-context modifiers are incomplete or duplicated",
)

statistics_context = context["statistics_by_id"]
require(all(set(row) == STATISTIC_CONTEXT_FIELDS
            for row in statistics_context.values()),
        "statistic-context fields changed")
require(set(statistics_context) == statistic_set,
        "atomic statistic context differs from the public statistic set")
for statistic_id, row in statistics_context.items():
    require(str(row["finding_ref"]) == statistic_finding[statistic_id],
            "statistic context points to the wrong finding")
    require(str(row["context_id"]) == context_by_finding[statistic_finding[statistic_id]]["context_id"],
            "statistic context points to the wrong evidence context")

relationships = context["relationships"]
require(set(relationships) == EVIDENCE_CONTEXT_RELATIONSHIP_FIELDS,
        "evidence-context relationship fields changed")
location_links = relationships["finding_locations"]
lateralization_links = relationships["finding_lateralizations"]
statistic_sign_links = relationships["statistic_signs"]
statistic_assertion_links = relationships["statistic_assertions"]
classification_links = relationships["classifications"]
sign_axis_summary_links = relationships["sign_axis_summaries"]
require(all(set(row) == FINDING_LOCATION_FIELDS for row in location_links),
        "finding-location fields changed")
require(all(set(row) == FINDING_LATERALIZATION_FIELDS
            for row in lateralization_links),
        "finding-lateralization fields changed")
require(all(set(row) == STATISTIC_SIGN_FIELDS for row in statistic_sign_links),
        "statistic-sign fields changed")
require(all(set(row) == STATISTIC_ASSERTION_FIELDS
            for row in statistic_assertion_links),
        "statistic-assertion fields changed")
require(all(set(row) == CLASSIFICATION_LINK_FIELDS
            for row in classification_links),
        "classification-link fields changed")
require(all(
    str(link["assertion_id"]) not in set(context_modifier_assertion_ids)
    for link in location_links
), "finding-context modifiers leaked into direct localization")
location_by_id = {str(row["location_link_id"]): row for row in location_links}
lateralization_by_id = {
    str(row["lateralization_link_id"]): row for row in lateralization_links
}
classification_by_id = {
    str(row["classification_link_id"]): row for row in classification_links
}
summary_ids = [
    str(row.get("sign_axis_summary_link_id") or "")
    for row in sign_axis_summary_links
]
summary_synthesis_ids = [
    str(row.get("synthesis_id") or "") for row in sign_axis_summary_links
]
require(
    all(set(row) == SIGN_AXIS_SUMMARY_FIELDS for row in sign_axis_summary_links),
    "sign-axis summary fields changed",
)
require(unique(summary_ids) and unique(summary_synthesis_ids),
        "duplicate sign-axis summary")
require(all(
    row["sign_axis_summary_link_id"]
    == f'SIGN_AXIS_SUMMARY:{row["synthesis_id"]}'
    for row in sign_axis_summary_links
), "noncanonical sign-axis summary identity")
require(all(
    row["axis"] in {"LOCALIZATION", "LATERALIZATION"}
    and len(row["public_sign_ids"]) == 1
    and str(row["public_sign_ids"][0]) in sign_set
    and unique([str(value) for value in row["context_ids"]])
    and set(str(value) for value in row["context_ids"]) <= set(context_ids)
    and unique([str(value) for value in row["region_ids"]])
    and set(str(value) for value in row["region_ids"]) <= set(LOCATION_LABELS)
    and unique([str(value) for value in row["brodmann_area_ids"]])
    and unique([str(value) for value in row["reported_target_keys"]])
    for row in sign_axis_summary_links
), "sign-axis summary has an invalid public reference")
require(len(location_by_id) == len(location_links), "duplicate finding-location relationship")
require(len(lateralization_by_id) == len(lateralization_links),
        "duplicate finding-lateralization relationship")
require(len(classification_by_id) == len(classification_links),
        "duplicate classification relationship")
for finding_ref, row in context_by_finding.items():
    require(all(link_id in location_by_id
                and str(location_by_id[link_id]["finding_ref"]) == finding_ref
                for link_id in row.get("location_link_ids") or []),
            "context has a dangling or cross-finding location relationship")
    require(all(link_id in lateralization_by_id
                and str(lateralization_by_id[link_id]["finding_ref"]) == finding_ref
                for link_id in row.get("lateralization_link_ids") or []),
            "context has a dangling or cross-finding lateralization relationship")
    require(all(link_id in classification_by_id
                and str(classification_by_id[link_id].get("finding_ref")) == finding_ref
                for link_id in row.get("classification_link_ids") or []),
            "context has a dangling or cross-finding classification relationship")
    require("sign_axis_context_link_ids" not in row,
            "obsolete sign-axis context links remain on a finding context")
    require(
        unique([str(value) for value in row.get("assertion_ids") or []])
        and set(str(value) for value in row.get("assertion_ids") or []) == {
            str(assertion_id)
            for assertion_id, assertion in assertions.items()
            if str(assertion["finding_ref"]) == finding_ref
        },
        "context axis-assertion membership differs from the assertion index",
    )
    require(set(row.get("statistic_ids") or []) == {
        statistic_id for statistic_id, statistic_row in statistics_context.items()
        if str(statistic_row["finding_ref"]) == finding_ref
    }, "context statistic membership differs from the atomic ledger")

sequence_components = context["sequence_components_by_id"]
require(all(set(row) == SEQUENCE_COMPONENT_FIELDS
            for row in sequence_components.values()),
        "sequence-component fields changed")
require(all(
    str(component_id) == str(row["component_id"])
    and str(row["finding_ref"]) in finding_set
    and all(str(public_sign_id) in sign_set
            for public_sign_id in row["public_sign_ids"])
    for component_id, row in sequence_components.items()
), "sequence-component identity or reference changed")
for finding_ref, row in context_by_finding.items():
    require(
        unique([str(value) for value in row["sequence_component_ids"]])
        and set(str(value) for value in row["sequence_component_ids"]) == {
            str(component_id)
            for component_id, component in sequence_components.items()
            if str(component["finding_ref"]) == finding_ref
        },
        "context sequence-component membership differs from the component index",
    )

for rows in (location_links, lateralization_links, statistic_sign_links,
             classification_links):
    require(all(str(public_sign_id) in sign_set for row in rows
                for public_sign_id in row.get("public_sign_ids") or []),
            "context relationship references an absent public sign")
require(all(str(row["statistic_id"]) in statistic_set for row in statistic_sign_links),
        "statistic-sign relationship references an absent statistic")
require(all(str(row["statistic_id"]) in statistic_set
            and str(row["assertion_id"]) in assertions
            for row in statistic_assertion_links),
        "statistic-assertion relationship is dangling")
node_ids = {str(row["node_id"]) for row in bundle["classifications"]["nodes"]}
require(all(str(row["node_id"]) in node_ids for row in classification_links),
        "context classification references an absent node")
bundle_sign_classifications = {
    (str(row["sign_id"]), str(row["node_id"]), str(row["relation"]))
    for row in bundle["classifications"]["sign_mappings"]
}
context_sign_classifications = {
    (str(sign_id), str(row["node_id"]), str(row["relation"]))
    for row in classification_links if row["subject_kind"] == "SIGN"
    for sign_id in row.get("public_sign_ids") or []
}
require(bundle_sign_classifications == context_sign_classifications,
        "canonical sign classifications differ between public projections")

expected_regions_by_sign = {sign_id: set() for sign_id in sign_ids}
require(all(
    str(target.get("key") or "") != PROPAGATION_REGION_ID
    for card in bundle["evidence_synthesis"]["axis_summaries"]
    for target in (card.get("target_contract") or {}).get("reported_targets") or []
), "propagation context leaked into direct localization targets")
for card in bundle["evidence_synthesis"]["axis_summaries"]:
    if str(card.get("axis")) != "LOCALIZATION":
        continue
    sign_id = str(card["sign_id"])
    for target in (card.get("target_contract") or {}).get("reported_targets") or []:
        if (str(target.get("target_level") or "").upper() == "STATUS"
                or str(target.get("key") or "").casefold() == "nonassoc"):
            continue
        region_id = next((
            str(value) for value in (
                target.get("region_id"), target.get("parent_region_id"),
                target.get("key"),
            ) if str(value or "") in LOCATION_LABELS
        ), "")
        if region_id:
            expected_regions_by_sign[sign_id].add(LOCATION_LABELS[region_id])
for sign in signs:
    sign_id = str(sign["id"])
    expected_regions = expected_regions_by_sign[sign_id] or {"No localization stated"}
    require(set(sign.get("regions") or []) == expected_regions,
            "browse-region membership differs from exact context relationships")
brodmann_by_sign = bundle["brodmann"]["mapping"]["by_sign"]
context_ids_by_finding = {
    str(row["finding_ref"]): str(row["context_id"])
    for row in context["contexts"]
}
locations_by_sign_and_finding = {}
for location in context["relationships"]["finding_locations"]:
    finding_ref = str(location["finding_ref"])
    for sign_id in location["public_sign_ids"]:
        locations_by_sign_and_finding.setdefault(
            (str(sign_id), finding_ref), []
        ).append(location)
require(all(
    set(entry) == {"sign", "areas", "map_links"}
    and set(entry["areas"]) == {
        str(link.get("area_id") or "") for link in entry["map_links"]
    }
    for entry in brodmann_by_sign.values()
), "Brodmann areas must be represented by exact map links")
for sign_id, entry in brodmann_by_sign.items():
    for link in entry["map_links"]:
        require(
            set(link) == {
                "area_id", "provenance", "target_key", "target_label",
                "finding_refs", "context_ids",
            }
            and str(link["provenance"]) in {
                "EXPLICIT_BA", "ANATOMICAL_CROSSWALK",
            }
            and (
                str(link["provenance"]) != "ANATOMICAL_CROSSWALK"
                or (str(link["target_key"]), str(link["area_id"]))
                in projectable_brodmann_targets
            )
            and link["finding_refs"]
            and link["context_ids"]
            and all(
                context_ids_by_finding.get(str(finding_ref)) in link["context_ids"]
                for finding_ref in link["finding_refs"]
            ), "Brodmann map link lacks its exact supporting context")
        for finding_ref in link["finding_refs"]:
            locations = locations_by_sign_and_finding.get(
                (str(sign_id), str(finding_ref)), []
            )
            if link["provenance"] == "EXPLICIT_BA":
                require(any(
                    str(location.get("brodmann_area_id") or "")
                    == str(link["area_id"])
                    for location in locations
                ), "explicit Brodmann map link lacks a matching finding location")
            else:
                require(any(
                    str(location.get("region_id") or "")
                    == str(link["target_key"])
                    for location in locations
                ), "crosswalk Brodmann map link lacks a matching finding location")

accounting_context = context["accounting"]
expected_context_accounting = {
    "contexts": len(finding_set),
    "atomic_statistics": len(statistic_set),
    "assertions": len(assertions),
    "sign_axis_summaries": len(sign_axis_summary_links),
    "source_reports": len(source_report_ids),
    "canonical_works": len(source_work_ids),
    "dangling_references": 0,
}
require(
    set(accounting_context) == {*expected_context_accounting, "structured_propagation"}
    and all(accounting_context.get(key) == value
            for key, value in expected_context_accounting.items()),
        "evidence-context accounting does not reconcile")
structured_propagation_accounting = accounting_context.get(
    "structured_propagation"
)
require(set(structured_propagation_accounting) == {
    "structured_inputs", "finding_context_modifier_references",
    "mapped_sign_modifier_references_expected",
    "mapped_sign_modifier_references_generated",
    "reported_target_contamination", "placement_contribution_leakage",
}, "structured propagation accounting fields changed")
expected_mapped_modifier_count = sum(
    len(row["public_sign_ids"]) for row in context_modifier_rows
)
require(
    structured_propagation_accounting["structured_inputs"]
    == len(structured_propagation_assertion_ids)
    and structured_propagation_accounting[
        "finding_context_modifier_references"
    ] == len(context_modifier_rows)
    and structured_propagation_accounting[
        "mapped_sign_modifier_references_expected"
    ] == expected_mapped_modifier_count
    and structured_propagation_accounting["reported_target_contamination"] == 0
    and structured_propagation_accounting["placement_contribution_leakage"] == 0,
    "structured propagation accounting does not reconcile",
)

synthesis = bundle["evidence_synthesis"]
for obsolete_field in PRIVATE_SYNTHESIS_FIELDS:
    require(obsolete_field not in synthesis,
            f"obsolete synthesis field is present: {obsolete_field}")
release = synthesis["release"]
cards = synthesis["axis_summaries"]
families = synthesis["descriptive_families"]
require(release["public_finding_count"] == len(findings),
        "release finding count differs from the public corpus")
require(release["synthesis_card_count"] == len(cards) == len(signs) * 2,
        "current sign-axis coverage changed")
require(release["descriptive_family_count"] == len(families),
        "descriptive-family count differs from the public families")
require(unique([card["synthesis_id"] for card in cards]), "duplicate synthesis identity")
require(unique([family["analysis_id"] for family in families]), "duplicate family identity")
expected_pairs = {(sign_id, axis) for sign_id in sign_ids
                  for axis in ("LATERALIZATION", "LOCALIZATION")}
actual_pairs = {(str(card["sign_id"]), card["axis"]) for card in cards}
require(actual_pairs == expected_pairs and len(cards) == len(actual_pairs),
        "projection is not exactly one row per sign and axis")

cards_by_sign = {sign_id: [] for sign_id in sign_ids}
for card in cards:
    cards_by_sign[str(card["sign_id"])].append(card["synthesis_id"])
require(synthesis["cards_by_sign"] == cards_by_sign, "cards_by_sign contract changed")
family_ids = {family["analysis_id"] for family in families}
require(all(str(sign_id) in sign_set for family in families for sign_id in family["sign_ids"]),
        "family references an absent sign")
require(all(value in family_ids for values in synthesis["families_by_sign"].values()
            for value in values), "sign references an absent family")
for family in families:
    family_statistics = set(str(value) for value in family.get("statistic_ids") or [])
    family_statistics.update(
        str(row["statistic_id"]) for row in family.get("exact_estimates") or []
        if row.get("statistic_id")
    )
    require(set(family.get("context_ids") or []) == {
        statistics_context[statistic_id]["context_id"]
        for statistic_id in family_statistics if statistic_id in statistics_context
    }, "source-defined result group differs from its atomic evidence contexts")

sign_by_id = {str(sign["id"]): sign for sign in signs}
cards_by_pair = {
    (str(card["sign_id"]), str(card["axis"])): card for card in cards
}
summary_by_synthesis = {
    str(row["synthesis_id"]): row for row in sign_axis_summary_links
}
require(
    set(summary_by_synthesis) == {str(card["synthesis_id"]) for card in cards}
    and {
        (str(row["public_sign_ids"][0]), str(row["axis"]))
        for row in sign_axis_summary_links
    } == expected_pairs,
    "sign-axis summaries are not exactly one row per public sign and axis",
)
for sign_id, label in REQUIRED_LOCALIZATION_REGRESSIONS.items():
    require(sign_id in sign_by_id and sign_by_id[sign_id].get("sign") == label,
            f"required public sign identity changed: {sign_id}")
    localization_card = cards_by_pair.get((sign_id, "LOCALIZATION")) or {}
    temporal_targets = [
        target
        for target in (localization_card.get("target_contract") or {}).get(
            "reported_targets"
        ) or []
        if "REG:TEMPORAL" in {
            str(target.get("key") or ""), str(target.get("region_id") or ""),
            str(target.get("parent_region_id") or ""),
        } and str(target.get("label") or "") == "Temporal"
    ]
    require(temporal_targets,
            f"required Temporal localization is absent: {label}")

card_modifier_pairs = []
known_brodmann_area_ids = {str(area_id) for area_id in bundle["brodmann"]["areas"]}
projectable_brodmann_targets = set()
for card in cards:
    require(PRIVATE_CARD_FIELDS.isdisjoint(card),
            "obsolete public axis-card field is present")
    axis = card["axis"]
    row_findings = card["row_finding_refs"]
    row_statistics = card["row_statistic_ids"]
    row_works = [str(value) for value in card["row_work_ids"]]
    require(unique(row_findings) and unique(row_statistics) and unique(row_works),
            "row duplicates finding, statistic, or work identity")
    require(set(row_findings) <= finding_set and set(row_statistics) <= statistic_set,
            "row references absent evidence")
    require(all(statistic_finding[value] in set(row_findings)
                for value in row_statistics), "row statistic is outside row findings")
    require(card["row_finding_count"] == len(row_findings)
            and card["row_statistic_count"] == len(row_statistics)
            and card["row_work_count"] == len(row_works), "row counts differ from row IDs")
    contributions = card["contributions"]
    contribution_ids = [str(item["work_id"]) for item in contributions]
    require(unique(contribution_ids) and set(contribution_ids) == set(row_works),
            "row work contributions are duplicated or incomplete")

    contract = card["target_contract"]
    require(
        TARGET_REQUIRED_FIELDS <= set(contract)
        and set(contract) <= TARGET_REQUIRED_FIELDS | TARGET_OPTIONAL_FIELDS,
        "target contract fields changed",
    )
    targets = contract["reported_targets"]
    modifiers = contract.get("modifiers") or []
    require(not targets or (row_findings and contributions),
            "reported target lacks source contribution rows")
    require(unique([target["key"] for target in targets]), "duplicate reported target")
    target_finding_refs = set()
    for target in targets:
        required_target_fields = {
            "key", "label", "raw", "origins", "finding_refs", "target_level",
        }
        hierarchy_fields = {
            "region_id", "parent_region_id", "area_id", "brodmann_label",
            "brodmann_area_ids", "brodmann_links",
        }
        require(
            required_target_fields <= set(target)
            and set(target) <= required_target_fields | hierarchy_fields,
            "reported-target fields changed",
        )
        require(bool(target["key"] and target["label"] and target["raw"]
                     and target["origins"] and target["finding_refs"]),
                "reported target lacks provenance")
        require(unique(target["raw"]) and unique(target["origins"])
                and unique(target["finding_refs"]),
                "reported target duplicates provenance")
        if "brodmann_area_ids" in target:
            require(
                isinstance(target["brodmann_area_ids"], list)
                and bool(target["brodmann_area_ids"])
                and unique([str(value) for value in target["brodmann_area_ids"]]),
                "reported target has invalid Brodmann relationships",
            )
        if "brodmann_links" in target:
            brodmann_links = target["brodmann_links"]
            require(
                isinstance(brodmann_links, list)
                and bool(brodmann_links)
                and all(
                    set(link) == BRODMANN_TARGET_LINK_FIELDS
                    and str(link["area_id"]) in known_brodmann_area_ids
                    and bool(str(link["relation"]))
                    and bool(str(link["provenance"]))
                    and isinstance(link["projects_evidence"], bool)
                    and link["projects_evidence"] == (
                        str(link["relation"]).upper()
                        in PROJECTABLE_BRODMANN_RELATIONS
                    )
                    for link in brodmann_links
                )
                and unique([
                    (str(link["area_id"]), str(link["relation"]),
                     str(link["provenance"]))
                    for link in brodmann_links
                ])
                and "brodmann_area_ids" in target
                and set(str(link["area_id"]) for link in brodmann_links)
                == set(str(value) for value in target["brodmann_area_ids"]),
                "reported target has invalid Brodmann link metadata",
            )
            projectable_brodmann_targets.update(
                (str(target["key"]), str(link["area_id"]))
                for link in brodmann_links
                if link["projects_evidence"]
            )
        require(set(target["finding_refs"]) <= set(row_findings),
                "reported target provenance is outside its source contribution rows")
        require(all(finding_ref in context_by_finding
                    for finding_ref in target["finding_refs"]),
                "reported target provenance lacks an evidence context")
        require(not any(is_propagation_value(target.get(field))
                        for field in ("key", "label", "raw")),
                "propagation is not a reported target")
        target_finding_refs.update(str(value) for value in target["finding_refs"])

    require(unique([str(modifier.get("key") or "") for modifier in modifiers]),
            "duplicate target modifier")
    modifier_finding_refs = set()
    for modifier in modifiers:
        require(set(modifier) == TARGET_MODIFIER_FIELDS,
                "modifier fields changed")
        require(
            modifier["key"] == modifier["modifier_type"]
            == PROPAGATION_MODIFIER_KEY
            and modifier["label"] == "Propagation",
            "unknown target modifier",
        )
        for field in ("raw", "origins", "finding_refs", "assertion_ids"):
            require(
                isinstance(modifier[field], list) and bool(modifier[field])
                and unique([str(value) for value in modifier[field]])
                and all(str(value).strip() for value in modifier[field]),
                "target modifier lacks unique structured provenance",
            )
        finding_refs_for_modifier = {
            str(value) for value in modifier["finding_refs"]
        }
        require(finding_refs_for_modifier <= finding_set,
                "target modifier references an absent finding")
        require(all(
            str(card["sign_id"]) in {
                str(link["public_sign_id"])
                for link in context_by_finding[finding_ref].get("sign_links") or []
            }
            for finding_ref in finding_refs_for_modifier
        ), "target modifier is not mapped to its public sign")
        for assertion_id_value in modifier["assertion_ids"]:
            assertion_id = str(assertion_id_value)
            assertion = assertions.get(assertion_id) or {}
            require(
                str(assertion.get("normalized_value") or "")
                == PROPAGATION_REGION_ID
                and str(assertion.get("axis") or "") == axis
                and str(assertion.get("finding_ref") or "")
                in finding_refs_for_modifier,
                "target modifier lacks its exact structured assertion",
            )
            card_modifier_pairs.append((
                assertion_id, str(card["sign_id"]), axis,
            ))
        modifier_finding_refs.update(finding_refs_for_modifier)

    modifier_only_finding_refs = modifier_finding_refs - target_finding_refs
    require(modifier_only_finding_refs.isdisjoint(row_findings),
            "modifier-only finding entered placement counts")
    placement_work_ids = {
        finding_work[finding_ref] for finding_ref in target_finding_refs
    }
    modifier_only_work_ids = {
        finding_work[finding_ref] for finding_ref in modifier_only_finding_refs
    } - placement_work_ids
    require(modifier_only_work_ids.isdisjoint(row_works),
            "modifier-only work entered placement weight")
    expected_card_context_ids = {
        context_by_finding[finding_ref]["context_id"]
        for finding_ref in {*row_findings, *modifier_finding_refs}
    }
    require(
        unique([str(value) for value in card.get("context_ids") or []])
        and set(card.get("context_ids") or []) == expected_card_context_ids,
        "axis-card contexts differ from placement and modifier lineage",
    )
    positive, _ = relationship_profile(contract)

    target_keys = sorted({str(target["key"]) for target in targets})
    summary_area_ids = {
        value[3:] for value in target_keys if value.startswith("BA:")
    }
    summary_area_ids.update(
        str(area_id)
        for target in targets
        for area_id in target.get("brodmann_area_ids") or []
    )
    summary_region_ids = set()
    if axis == "LOCALIZATION":
        for target in positive:
            region_id = next((
                str(value) for value in (
                    target.get("key"), target.get("region_id"),
                    target.get("parent_region_id"),
                ) if str(value or "") in LOCATION_LABELS
            ), "")
            if region_id:
                summary_region_ids.add(region_id)
    expected_summary = {
        "sign_axis_summary_link_id": f'SIGN_AXIS_SUMMARY:{card["synthesis_id"]}',
        "synthesis_id": str(card["synthesis_id"]),
        "axis": axis,
        "public_sign_ids": [str(card["sign_id"])],
        "context_ids": list(card.get("context_ids") or []),
        "region_ids": sorted(summary_region_ids),
        "brodmann_area_ids": sorted(
            summary_area_ids,
            key=lambda value: (
                not value.isdigit(), int(value) if value.isdigit() else value
            ),
        ),
        "reported_target_keys": target_keys,
        "modifiers": modifiers,
    }
    require(
        summary_by_synthesis[str(card["synthesis_id"])] == expected_summary,
        "sign-axis summary differs from its referenced card",
    )

    if axis == "LOCALIZATION" and positive:
        required_regions = set()
        for target in positive:
            major_region_id = next((
                str(value) for value in (
                    target.get("key"), target.get("region_id"),
                    target.get("parent_region_id"),
                )
                if str(value) in LOCATION_LABELS
            ), "")
            if major_region_id:
                required_regions.add(LOCATION_LABELS[major_region_id])
        if required_regions:
            regions = set(sign_by_id[str(card["sign_id"])].get("regions") or [])
            require(required_regions == regions,
                    "localized sign differs from its canonical browse regions")
            require("No localization stated" not in regions,
                    "localized sign remains classified only as unlocalized")

    for contribution in contributions:
        require(PRIVATE_CONTRIBUTION_FIELDS.isdisjoint(contribution),
                "obsolete public contribution field is present")
        work_id = str(contribution["work_id"])
        require(work_id in profile_by_id, "contribution work lacks a profile")
        work_findings = [value for value in row_findings if finding_work[value] == work_id]
        work_statistics = [value for value in row_statistics
                           if finding_work[statistic_finding[value]] == work_id]
        require(set(contribution["row_finding_refs"]) <= set(work_findings)
                and set(contribution["row_statistic_ids"]) <= set(work_statistics),
                "contribution evidence is outside its canonical work")
        require(all(statistic_finding[statistic_id]
                    in set(contribution["row_finding_refs"])
                    for statistic_id in contribution["row_statistic_ids"]),
                "contribution statistic is outside its direct finding provenance")
        evidence_class = contribution["evidence_class"]
        components = contribution["weight_components"]
        require(evidence_class in {"I", "II", "III", "UNCLASSIFIED"},
                "invalid evidence class")
        require(set(components) == {
            "class_base", "directness_type", "directness_multiplier", "size_factor",
        }, "weight-component fields changed")
        require(float(components["class_base"]) == CLASS_BASE.get(evidence_class, 0.0),
                "contribution class base changed")
        directness = components["directness_type"]
        require(directness in DIRECTNESS_MULTIPLIERS
                and float(components["directness_multiplier"])
                == DIRECTNESS_MULTIPLIERS[directness], "directness multiplier changed")
        require(1.0 <= float(components["size_factor"]) <= 2.0,
                "size factor is outside the approved range")
        calculated = round(
            float(components["class_base"])
            * float(components["directness_multiplier"])
            * float(components["size_factor"]), 3,
        )
        final_weight = float(contribution["final_weight"])
        require(final_weight >= 0.0, "contribution has a negative public weight")
        if final_weight > 0.0:
            require(bool(targets), "weight was applied without a reported target")
            require(math.isclose(final_weight, calculated,
                                 abs_tol=1e-9), "applied weight differs from components")

expected_card_modifier_pairs = [
    (
        str(modifier["assertion_id"]), str(public_sign_id),
        str(modifier["axis"]),
    )
    for modifier in context_modifier_rows
    for public_sign_id in modifier["public_sign_ids"]
]
require(
    unique(card_modifier_pairs)
    and set(card_modifier_pairs) == set(expected_card_modifier_pairs),
    "mapped propagation modifiers differ between contexts and axis cards",
)
require(
    structured_propagation_accounting[
        "mapped_sign_modifier_references_generated"
    ] == len(card_modifier_pairs),
    "structured propagation generated count does not reconcile",
)

serialized = json.dumps(bundle, sort_keys=True).lower()
for private_marker in (
    '"owner_comment"', '"owner_decision"', '"resolution_json"', '"context_json"',
    '"adjudication_event"', '"private_pdf_path"', '"local_source_path"',
    '"owner_question"', '"review_origin"', '"review_status"',
):
    require(private_marker not in serialized, f"private field leaked: {private_marker}")

print(json.dumps({
    "source_reports": len(sources), "canonical_works": len(profiles),
    "findings": len(findings), "statistics": len(statistics), "signs": len(signs),
    "reported_targets": sum(len(card["target_contract"]["reported_targets"])
                            for card in cards),
    "synthesis_cards": len(cards),
    "descriptive_families": len(families), "status": "PASS",
}, sort_keys=True))
