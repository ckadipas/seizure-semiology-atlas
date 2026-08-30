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
SCHEMA = "atlas-public-bundle-1.5.0"
CONTEXT_SCHEMA = "atlas-evidence-context-1.0.0"
CARD_STATES = {
    "EVIDENCE_BEARING_WEIGHTED", "EVIDENCE_LINKED_WEIGHT_PENDING",
    "EVIDENCE_LINKED_CONTEXT_ONLY", "TARGET_LINKAGE_NEEDED", "NO_SOURCE_TARGET",
}
CLASS_BASE = {"I": 3.0, "II": 2.0, "III": 1.0}
DIRECTNESS_MULTIPLIERS = {
    "postop": 1.5, "seeg": 1.5, "intracranial_eeg": 1.35,
    "video_eeg": 1.2, "imaging_concordance": 1.15,
    "scalp_eeg": 1.1, "review": 1.0, "none": 0.9,
}
ABSENT_TARGET_TERMS = {
    "", "n a", "none", "not reported", "not resolved", "unknown", "unspecified",
}
LOCATION_LABELS = {
    "REG:TEMPORAL": "Temporal", "REG:FRONTAL": "Frontal",
    "REG:PARIETAL": "Parietal", "REG:OCCIPITAL": "Occipital",
    "REG:INSULAR": "Insular", "REG:LIMBIC": "Limbic",
    "REG:DEEP_SUBCORTICAL": "Deep/Subcortical",
    "REG:MULTIREGIONAL_PROPAGATION": "Multiregional/Propagation",
}
TARGET_FIELDS = {
    "owner_cleared_raw_targets", "identity_group_finding_refs",
    "exact_group_finding_raw_targets", "additional_linkage_targets",
    "nonidentity_group_raw_targets", "nonidentity_group_finding_refs",
    "excluded_relationship_raw_targets", "reported_targets",
    "unresolved_raw_targets", "finding_wide_only_raw_targets",
    "true_nonassociation", "inherited_nonassociation_status",
    "promoted_linked_finding_refs", "source_explicit_linked_finding_targets",
    "context_only_finding_axis_targets",
}
def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(values):
    return len(values) == len(set(values))


def relationship_profile(contract):
    targets = contract.get("reported_targets") or []
    positive = [
        target for target in targets
        if str(target.get("target_level") or "").upper() != "STATUS"
        and str(target.get("key") or "").casefold() != "nonassoc"
    ]
    nonassociation = bool(contract.get("true_nonassociation")) or any(
        str(target.get("target_level") or "").upper() == "STATUS"
        or str(target.get("key") or "").casefold() == "nonassoc"
        for target in targets
    )
    return positive, nonassociation


def meaningful_unresolved_targets(values):
    """Ignore placeholders that explicitly mean no target was reported."""
    return [
        value for value in values or []
        if " ".join(re.findall(
            r"[a-z0-9]+", str((value or {}).get("raw") or "").casefold()
        )) not in ABSENT_TARGET_TERMS
    ]


def has_meaningful_recorded_target(contract):
    """Mirror the exporter's distinction between evidence and placeholders."""
    if contract.get("reported_targets") or contract.get("true_nonassociation"):
        return True
    if (contract.get("exact_group_finding_raw_targets")
            or contract.get("additional_linkage_targets")):
        return True
    if contract.get("adjudicated_unsupported"):
        return False
    return any(meaningful_unresolved_targets(contract.get(field)) for field in (
        "owner_cleared_raw_targets", "nonidentity_group_raw_targets",
        "excluded_relationship_raw_targets", "unresolved_raw_targets",
        "finding_wide_only_raw_targets",
    ))


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
finding_refs = [finding["source_finding_ref"] for finding in findings]
statistic_ids = [statistic["statistic_id"] for statistic in statistics]
sign_ids = [str(sign["id"]) for sign in signs]
finding_set, statistic_set, sign_set = set(finding_refs), set(statistic_ids), set(sign_ids)
statistic_by_id = {statistic["statistic_id"]: statistic for statistic in statistics}
statistic_finding = {
    statistic["statistic_id"]: finding["source_finding_ref"]
    for finding in findings
    for statistic in finding["statistics"]
}
finding_work = {}

require(len(sources) == 77, "current source-report count changed")
require(len(findings) == 4120 and unique(finding_refs), "public finding contract changed")
require(len(statistics) == 4518 and unique(statistic_ids), "public statistic contract changed")
require(bool(signs) and unique(sign_ids), "public sign identities are empty or duplicated")
require(unique([source["source_sha256"] for source in sources]), "duplicate source report")
for source in sources:
    sha, work_id = source["source_sha256"], str(source["work_id"])
    require(re.fullmatch(r"[0-9a-f]{64}", sha) is not None, "invalid source digest")
    require(re.fullmatch(r"[0-9a-f]{64}", source["source_report_sha256"]) is not None,
            "invalid report digest")
    for finding in source["findings"]:
        ref = finding["source_finding_ref"]
        finding_work[ref] = work_id
        require(ref.startswith(f"{sha}:"), "finding/source identity mismatch")
        require(bool(finding["locators"] and finding["evidence_text"]),
                "finding lacks source evidence or locator")
        require(unique([row["statistic_id"] for row in finding["statistics"]]),
                "finding duplicates a statistic")
        require(all(str(value) in sign_set for value in
                    finding["exact_sign_ids"] + finding["related_sign_ids"]),
                "finding references an absent sign")

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
require(len(profiles) == 73 and unique(profile_ids), "canonical-work contract changed")
require(set(finding_work.values()) <= set(profile_ids), "finding work lacks a profile")
require(authority["scheme_id"] == "WEIGHT:HISTORICAL_D5D9DD2", "weight scheme changed")
require(authority["scheme_status"] == "HISTORICAL_RESTORED", "weight source status changed")
require(authority["class_base"] == CLASS_BASE, "class bases changed")
require(authority["ground_truth_multipliers"] == DIRECTNESS_MULTIPLIERS,
        "directness multipliers changed")
require(float(authority["size_cap"]) == 2.0, "size cap changed")

context = bundle["evidence_context"]
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
context_by_finding = {str(row["finding_ref"]): row for row in finding_contexts}
context_ids = [str(row["context_id"]) for row in finding_contexts]
context_id_set = set(context_ids)
require(len(finding_contexts) == len(context_by_finding) == len(finding_set),
        "evidence context is not exactly one row per public finding")
require(set(context_by_finding) == finding_set and unique(context_ids),
        "evidence context finding identities differ from the public corpus")
source_report_ids = {str(source["source_sha256"]) for source in sources}
for finding_ref, row in context_by_finding.items():
    require(row["context_id"] == f"ECTX:{finding_ref}", "noncanonical context identity")
    require(str(row["source_report_id"]) in source_report_ids,
            "context references an absent source report")
    require(str(row["source_work_id"]) in profile_by_id,
            "context references an absent canonical work")
    require(all(str(link.get("public_sign_id")) in sign_set
                and str(link.get("relation")) in {"EXACT", "RELATED"}
                for link in row.get("sign_links") or []),
            "context has an invalid public-sign relationship")

assertions = context["assertions_by_id"]
statistics_context = context["statistics_by_id"]
require(set(statistics_context) == statistic_set,
        "atomic statistic context differs from the public statistic set")
for statistic_id, row in statistics_context.items():
    require(str(row["finding_ref"]) == statistic_finding[statistic_id],
            "statistic context points to the wrong finding")
    require(str(row["context_id"]) == context_by_finding[statistic_finding[statistic_id]]["context_id"],
            "statistic context points to the wrong evidence context")

relationships = context["relationships"]
location_links = relationships["finding_locations"]
lateralization_links = relationships["finding_lateralizations"]
sign_axis_context_links = relationships["sign_axis_contexts"]
sign_axis_summary_links = relationships["sign_axis_summaries"]
statistic_sign_links = relationships["statistic_signs"]
statistic_assertion_links = relationships["statistic_assertions"]
classification_links = relationships["classifications"]
location_by_id = {str(row["location_link_id"]): row for row in location_links}
lateralization_by_id = {
    str(row["lateralization_link_id"]): row for row in lateralization_links
}
classification_by_id = {
    str(row["classification_link_id"]): row for row in classification_links
}
known_context_region_ids = set(LOCATION_LABELS)
known_context_region_ids.update(
    str(value) for row in location_links
    for value in (row.get("region_id"), row.get("major_region_id"))
    if value
)
sign_axis_context_by_id = {
    str(row["sign_axis_context_link_id"]): row for row in sign_axis_context_links
}
sign_axis_summary_by_id = {
    str(row["sign_axis_summary_link_id"]): row for row in sign_axis_summary_links
}
require(len(location_by_id) == len(location_links), "duplicate finding-location relationship")
require(len(lateralization_by_id) == len(lateralization_links),
        "duplicate finding-lateralization relationship")
require(len(classification_by_id) == len(classification_links),
        "duplicate classification relationship")
require(len(sign_axis_context_by_id) == len(sign_axis_context_links),
        "duplicate sign-axis context relationship")
require(len(sign_axis_summary_by_id) == len(sign_axis_summary_links),
        "duplicate sign-axis summary relationship")
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
    require(all(link_id in sign_axis_context_by_id
                and str(sign_axis_context_by_id[link_id]["finding_ref"]) == finding_ref
                and str(sign_axis_context_by_id[link_id]["context_id"]) == row["context_id"]
                for link_id in row.get("sign_axis_context_link_ids") or []),
            "context has a dangling or cross-finding sign-axis relationship")
    require(all(str(assertion_id) in assertions
                for assertion_id in row.get("assertion_ids") or []),
            "context has a dangling axis assertion")
    require(set(row.get("statistic_ids") or []) == {
        statistic_id for statistic_id, statistic_row in statistics_context.items()
        if str(statistic_row["finding_ref"]) == finding_ref
    }, "context statistic membership differs from the atomic ledger")

for rows in (location_links, lateralization_links, sign_axis_context_links,
             sign_axis_summary_links, statistic_sign_links, classification_links):
    require(all(str(public_sign_id) in sign_set for row in rows
                for public_sign_id in row.get("public_sign_ids") or []),
            "context relationship references an absent public sign")
require(all(str(row["statistic_id"]) in statistic_set for row in statistic_sign_links),
        "statistic-sign relationship references an absent statistic")
require(all(str(row["statistic_id"]) in statistic_set
            and str(row["assertion_id"]) in assertions
            for row in statistic_assertion_links),
        "statistic-assertion relationship is dangling")
for row in sign_axis_context_links:
    finding_ref = str(row.get("finding_ref") or "")
    problems = []
    if finding_ref not in finding_set:
        problems.append("finding")
    elif str(row.get("context_id")) != context_by_finding[finding_ref]["context_id"]:
        problems.append("context")
    if str(row.get("axis")) not in {"LOCALIZATION", "LATERALIZATION"}:
        problems.append("axis")
    if any(str(region_id) not in known_context_region_ids
           for region_id in row.get("region_ids") or []):
        problems.append("region")
    if any(str(statistic_id) not in statistic_set
           for statistic_id in row.get("linked_statistic_ids") or []):
        problems.append("statistic")
    require(not problems,
            "invalid sign-axis context relationship "
            f'{row.get("sign_axis_context_link_id")}: {",".join(problems)}')
for row in sign_axis_summary_links:
    problems = []
    if str(row.get("axis")) not in {"LOCALIZATION", "LATERALIZATION"}:
        problems.append("axis")
    if len(row.get("public_sign_ids") or []) != 1:
        problems.append("public-sign")
    if any(str(region_id) not in LOCATION_LABELS
           for region_id in row.get("region_ids") or []):
        problems.append("region")
    if any(str(context_id) not in context_id_set
           for context_id in row.get("context_ids") or []):
        problems.append("context")
    require(not problems,
            "invalid sign-axis summary relationship "
            f'{row.get("sign_axis_summary_link_id")}: {",".join(problems)}')
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
expected_areas_by_sign = {sign_id: set() for sign_id in sign_ids}
for row in sign_axis_summary_links:
    if str(row.get("axis")) != "LOCALIZATION":
        continue
    for sign_id in row.get("public_sign_ids") or []:
        expected_regions_by_sign[str(sign_id)].update(
            LOCATION_LABELS[str(region_id)] for region_id in row.get("region_ids") or []
        )
        expected_areas_by_sign[str(sign_id)].update(
            str(area_id) for area_id in row.get("brodmann_area_ids") or []
        )
for sign in signs:
    sign_id = str(sign["id"])
    expected_regions = expected_regions_by_sign[sign_id] or {"No localization stated"}
    require(set(sign.get("regions") or []) == expected_regions,
            "browse-region membership differs from exact context relationships")
brodmann_by_sign = bundle["brodmann"]["mapping"]["by_sign"]
require(set(brodmann_by_sign) == {
    sign_id for sign_id, areas in expected_areas_by_sign.items() if areas
}, "Brodmann sign membership differs from evidence context")
require(all(set(brodmann_by_sign[sign_id]["areas"]) == areas
            for sign_id, areas in expected_areas_by_sign.items() if areas),
        "Brodmann areas differ from exact context relationships")

accounting_context = context["accounting"]
require(accounting_context == {
    "contexts": len(finding_set),
    "atomic_statistics": len(statistic_set),
    "assertions": len(assertions),
    "sign_axis_contexts": len(sign_axis_context_links),
    "sign_axis_summaries": len(sign_axis_summary_links),
    "source_reports": len(source_report_ids),
    "canonical_works": len(profile_ids),
    "dangling_references": 0,
}, "evidence-context accounting does not reconcile")

synthesis = bundle["evidence_synthesis"]
release = synthesis["release"]
axes = synthesis["finding_axes"]
cards = synthesis["axis_summaries"]
families = synthesis["descriptive_families"]
require(release["private_finding_count"] == 4122, "private finding count changed")
require(release["public_finding_count"] == 4120, "release finding count changed")
require(release["axis_count"] == len(axes) == 8238, "finding-axis count changed")
require(release["owner_release_card_count"] == 766, "source-release card count changed")
require(release["supplemental_card_count"] == 46, "supplemental card count changed")
require(release["group_axis_card_count"] == 812, "group-axis lineage count changed")
require(release["synthesis_card_count"] == len(cards) == len(signs) * 2,
        "current sign-axis coverage changed")
require(release["descriptive_family_count"] == len(families) == 1555,
        "descriptive-family count changed")
require(release["retained_artifact_count"] == 146, "retained artifact count changed")
require(unique([card["synthesis_id"] for card in cards]), "duplicate synthesis identity")
require(unique([family["analysis_id"] for family in families]), "duplicate family identity")
expected_pairs = {(sign_id, axis) for sign_id in sign_ids
                  for axis in ("LATERALIZATION", "LOCALIZATION")}
actual_pairs = {(str(card["sign_id"]), card["axis"]) for card in cards}
require(actual_pairs == expected_pairs and len(cards) == len(actual_pairs),
        "projection is not exactly one row per sign and axis")
summary_pairs = {
    (str(row["public_sign_ids"][0]), str(row["axis"]))
    for row in sign_axis_summary_links
}
require(summary_pairs == expected_pairs and len(sign_axis_summary_links) == len(summary_pairs),
        "sign-axis summaries are not exactly one row per sign and axis")
require(unique([(row["finding_ref"], row["axis"]) for row in axes]),
        "duplicate finding-axis identity")
require(all(row["finding_ref"] in finding_set for row in axes),
        "finding axis references an absent finding")
require(all(row.get("context_id") == context_by_finding[row["finding_ref"]]["context_id"]
            for row in axes), "finding-axis row points to the wrong evidence context")

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
weighted_works, linked_works = set(), set()
alignment_checks = 0
for card in cards:
    state, axis = card["categorization_state"], card["axis"]
    require(state in CARD_STATES, "unknown current categorization state")
    row_findings = card["row_finding_refs"]
    row_statistics = card["row_statistic_ids"]
    row_works = [str(value) for value in card["row_work_ids"]]
    require(set(card.get("context_ids") or []) == {
        context_by_finding[finding_ref]["context_id"] for finding_ref in row_findings
    }, "weighted row context differs from its linked findings")
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
    optional_target_fields = {
        "adjudicated_finding_refs", "adjudicated_unsupported",
    }
    require(
        TARGET_FIELDS <= set(contract)
        and set(contract) <= TARGET_FIELDS | optional_target_fields,
        "target contract fields changed",
    )
    targets = contract["reported_targets"]
    card_axis_links = [
        row for row in sign_axis_context_links
        if str(row["synthesis_id"]) == str(card["synthesis_id"])
    ]
    card_summary_links = [
        row for row in sign_axis_summary_links
        if str(row["synthesis_id"]) == str(card["synthesis_id"])
    ]
    require(len(card_summary_links) == 1
            and card_summary_links[0].get("public_sign_ids") == [str(card["sign_id"])]
            and str(card_summary_links[0].get("axis")) == axis,
            "weighted row lacks its canonical sign-axis summary")
    require(all(str(row["finding_ref"]) in set(row_findings)
                and str(row["axis"]) == axis
                and row.get("public_sign_ids") == [str(card["sign_id"])]
                for row in card_axis_links),
            "weighted row has an invalid sign-axis context relationship")
    if targets:
        context_target_keys = {
            str(value) for row in card_axis_links
            for value in row.get("reported_target_keys") or []
        }
        context_target_keys.update(
            str(value) for row in card_summary_links
            for value in row.get("reported_target_keys") or []
        )
        require({str(target["key"]) for target in targets} <= context_target_keys,
                "weighted row target is absent from its evidence-context relationships")
    require(unique([target["key"] for target in targets]), "duplicate reported target")
    for target in targets:
        required_target_fields = {
            "key", "label", "raw", "origins", "contexts", "scopes",
            "target_level", "details",
        }
        hierarchy_fields = {
            "region_id", "parent_region_id", "area_id", "brodmann_label",
        }
        require(
            required_target_fields <= set(target)
            and set(target) <= required_target_fields | hierarchy_fields,
            "reported-target fields changed",
        )
        require(bool(target["key"] and target["label"] and target["raw"]
                     and target["origins"]), "reported target lacks provenance")
        require(unique(target["raw"]) and unique(target["origins"])
                and unique(target["contexts"]) and unique(target["scopes"]),
                "reported target duplicates provenance")
        require(all(detail.get("finding_ref") in finding_set for detail in target["details"]),
                "reported target detail references an absent finding")

    positive, nonassociation = relationship_profile(contract)
    recorded = has_meaningful_recorded_target(contract)
    relationship_linked = bool(
        (positive or nonassociation) and row_findings and row_works
    )
    has_applied_weight = any(
        float(contribution.get("final_weight") or 0.0) > 0.0
        for contribution in contributions
    )
    context_only_projection = bool(contributions) and all(
        float(contribution.get("final_weight") or 0.0) == 0.0
        and bool(contribution.get("projection_disposition"))
        for contribution in contributions
    )
    unsupported_context = bool(
        card.get("terminal_classification") == "GENUINELY_UNSUPPORTED"
        and row_findings and row_works and not positive and not nonassociation
    )
    expected_state = (
        "EVIDENCE_BEARING_WEIGHTED"
        if relationship_linked and has_applied_weight
        else "EVIDENCE_LINKED_CONTEXT_ONLY"
        if relationship_linked and context_only_projection
        else "EVIDENCE_LINKED_CONTEXT_ONLY"
        if unsupported_context
        else "EVIDENCE_LINKED_WEIGHT_PENDING"
        if relationship_linked
        else "TARGET_LINKAGE_NEEDED" if recorded
        else "NO_SOURCE_TARGET"
    )
    require(
        state == expected_state,
        "card state differs from its source-target contract: "
        f"sign_id={card['sign_id']} axis={axis} state={state} expected={expected_state}",
    )
    status = card["pattern_status"]
    if positive and nonassociation:
        require(status == "GENUINELY_MIXED", "mixed evidence has a contradictory status")
    elif positive:
        require(status not in {"NOT_REPORTED", "NON_LOCALIZING", "NON_LATERALIZING"},
                "positive target has a contradictory status")
    elif nonassociation:
        require(status == ("NON_LOCALIZING" if axis == "LOCALIZATION"
                           else "NON_LATERALIZING"),
                "nonassociation status differs from its axis")
    else:
        require(status == "NOT_REPORTED", "target-free card has a relationship status")

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
            alignment_checks += 1
            regions = set(sign_by_id[str(card["sign_id"])].get("regions") or [])
            require(required_regions == regions,
                    "localized sign differs from its canonical browse regions")
            require("No localization stated" not in regions,
                    "localized sign remains classified only as unlocalized")

    for contribution in contributions:
        work_id = str(contribution["work_id"])
        require(work_id in profile_by_id, "contribution work lacks a profile")
        work_findings = [value for value in row_findings if finding_work[value] == work_id]
        work_statistics = [value for value in row_statistics
                           if finding_work[statistic_finding[value]] == work_id]
        projection_disposition = contribution.get("projection_disposition")
        if projection_disposition:
            selected = set(contribution["row_statistic_ids"])
            unselected = set(
                contribution.get("projection_unselected_statistic_ids") or []
            )
            require(selected.isdisjoint(unselected)
                    and selected | unselected == set(work_statistics),
                    "source projection does not partition its canonical-work statistics")
            require(set(contribution["row_finding_refs"]) == {
                statistic_finding[statistic_id] for statistic_id in selected
            }, "source projection findings differ from its selected statistics")
        else:
            require(contribution["row_finding_refs"] == work_findings
                    and contribution["row_statistic_ids"] == work_statistics,
                    "contribution evidence differs from its canonical work")
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
        if state in {
            "EVIDENCE_BEARING_WEIGHTED", "EVIDENCE_LINKED_WEIGHT_PENDING",
            "EVIDENCE_LINKED_CONTEXT_ONLY",
        }:
            linked_works.add(work_id)
        if projection_disposition:
            require(projection_disposition in {"SHARED_SOURCE_CATEGORY", "CITED_CONTEXT_ONLY"},
                    "unknown context-only projection disposition")
            require(float(contribution["final_weight"]) == 0.0,
                    "context-only source projection carries numerical weight")
            require(math.isclose(float(contribution.get("potential_weight") or 0.0),
                                 calculated, abs_tol=1e-9),
                    "context-only potential weight differs from components")
            require(bool(contribution.get("projection_reason")),
                    "context-only source projection lacks an explanation")
            expected_weight_status = (
                "NOT_APPLIED_SHARED_SOURCE_CATEGORY"
                if projection_disposition == "SHARED_SOURCE_CATEGORY"
                else "NOT_APPLIED_CITED_RESTATEMENT"
            )
            require(contribution.get("weight_status") == expected_weight_status,
                    "context-only source projection has the wrong weight status")
            if projection_disposition == "SHARED_SOURCE_CATEGORY":
                require(bool(contribution.get("counted_under_sign_id")
                             and contribution.get("counted_under_label")),
                        "shared source category lacks its counted-under sign")
            continue
        if state == "EVIDENCE_BEARING_WEIGHTED":
            require(contribution.get("weight_status")
                    == "APPLIED_TO_SOURCE_REPORTED_RELATIONSHIP",
                    "usable relationship lacks applied-weight status")
            require(math.isclose(float(contribution["final_weight"]), calculated,
                                 abs_tol=1e-9), "applied weight differs from components")
            if float(contribution["final_weight"]) > 0:
                weighted_works.add(work_id)
        elif state == "EVIDENCE_LINKED_WEIGHT_PENDING":
            require(float(contribution["final_weight"]) == 0.0,
                    "weight was applied while study weighting is pending")
            require(contribution.get("weight_status")
                    == "NOT_APPLIED_STUDY_WEIGHT_PENDING",
                    "pending study lacks pending-weight status")
            require(math.isclose(float(contribution.get("potential_weight") or 0.0),
                                 calculated, abs_tol=1e-9),
                    "pending potential weight differs from components")
        else:
            require(float(contribution["final_weight"]) == 0.0,
                    "weight was applied without a usable axis target")
            require(contribution.get("weight_status")
                    == "NOT_APPLIED_NO_USABLE_AXIS_TARGET",
                    "unusable relationship lacks unapplied-weight status")
            require(math.isclose(float(contribution.get("potential_weight") or 0.0),
                                 calculated, abs_tol=1e-9),
                    "unapplied potential weight differs from components")

accounting = authority["corpus_accounting"]
expected_accounting = {
    "source_reports": len(sources),
    "canonical_works": len(profiles),
    "contributes_weight": len(weighted_works),
    "linked_authority_pending": len(linked_works - weighted_works),
    "no_sign_axis_contribution": len(set(profile_ids) - linked_works),
}
require(all(accounting.get(key) == value for key, value in expected_accounting.items()),
        "current corpus accounting changed")
require(sum(expected_accounting[key] for key in (
    "contributes_weight", "linked_authority_pending", "no_sign_axis_contribution"
)) == len(profile_ids), "derived work coverage does not reconcile")

projection = authority["current_projection_audit"]
require(projection == {
    "status": "PASS", "sign_axis_rows": len(cards),
    "unique_sign_axis_pairs": len(actual_pairs),
    "localization_rows_checked_against_browse_regions": alignment_checks,
    "positive_weight_outside_weighted_rows": 0,
    "duplicate_work_contributions": 0,
    "browse_region_memberships_added_from_context":
        projection["browse_region_memberships_added_from_context"],
    "evidence_context_status": "PASS",
    "evidence_context_digest": context["semantic_digest"],
}, "current projection audit changed")

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
    "finding_axes": len(axes), "synthesis_cards": len(cards),
    "descriptive_families": len(families), "status": "PASS",
}, sort_keys=True))
