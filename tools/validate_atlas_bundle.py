#!/usr/bin/env python3
"""Validate the redacted current-corpus atlas bundle without private sources."""

import hashlib
import json
import math
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "atlas_bundle.json"
SCHEMA = "atlas-public-bundle-1.4.3"
CARD_STATES = {
    "EVIDENCE_BEARING_WEIGHTED", "EVIDENCE_LINKED_WEIGHT_PENDING",
    "TARGET_LINKAGE_NEEDED", "NO_SOURCE_TARGET",
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
    return any(meaningful_unresolved_targets(contract.get(field)) for field in (
        "owner_cleared_raw_targets", "nonidentity_group_raw_targets",
        "excluded_relationship_raw_targets", "unresolved_raw_targets",
        "finding_wide_only_raw_targets",
    ))


bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
require(set(bundle) == {
    "brodmann", "classifications", "corpus", "evidence_authority",
    "evidence_synthesis", "finding_locations", "schema_version",
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
require(len(findings) == 4119 and unique(finding_refs), "public finding contract changed")
require(len(statistics) == 4514 and unique(statistic_ids), "public statistic contract changed")
require(len(signs) == 383 and unique(sign_ids), "public sign contract changed")
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

synthesis = bundle["evidence_synthesis"]
release = synthesis["release"]
axes = synthesis["finding_axes"]
cards = synthesis["axis_summaries"]
families = synthesis["descriptive_families"]
require(release["private_finding_count"] == 4121, "private finding count changed")
require(release["public_finding_count"] == 4119, "release finding count changed")
require(release["axis_count"] == len(axes) == 8238, "finding-axis count changed")
require(release["owner_release_card_count"] == 766, "source-release card count changed")
require(release["supplemental_card_count"] == 46, "supplemental card count changed")
require(release["group_axis_card_count"] == 812, "group-axis lineage count changed")
require(release["synthesis_card_count"] == len(cards) == 766,
        "current sign-axis count changed")
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
require(unique([(row["finding_ref"], row["axis"]) for row in axes]),
        "duplicate finding-axis identity")
require(all(row["finding_ref"] in finding_set for row in axes),
        "finding axis references an absent finding")

cards_by_sign = {sign_id: [] for sign_id in sign_ids}
for card in cards:
    cards_by_sign[str(card["sign_id"])].append(card["synthesis_id"])
require(synthesis["cards_by_sign"] == cards_by_sign, "cards_by_sign contract changed")
family_ids = {family["analysis_id"] for family in families}
require(all(str(sign_id) in sign_set for family in families for sign_id in family["sign_ids"]),
        "family references an absent sign")
require(all(value in family_ids for values in synthesis["families_by_sign"].values()
            for value in values), "sign references an absent family")

sign_by_id = {str(sign["id"]): sign for sign in signs}
weighted_works, linked_works = set(), set()
alignment_checks = 0
for card in cards:
    state, axis = card["categorization_state"], card["axis"]
    require(state in CARD_STATES, "unknown current categorization state")
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
    require(set(contract) == TARGET_FIELDS, "target contract fields changed")
    targets = contract["reported_targets"]
    require(unique([target["key"] for target in targets]), "duplicate reported target")
    for target in targets:
        require(set(target) == {
            "key", "label", "raw", "origins", "contexts", "scopes",
            "target_level", "details",
        }, "reported-target fields changed")
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
    expected_state = (
        "EVIDENCE_BEARING_WEIGHTED"
        if relationship_linked and has_applied_weight
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
        required_regions = {
            LOCATION_LABELS[str(target["key"])] for target in positive
            if str(target["key"]) in LOCATION_LABELS
        }
        if required_regions:
            alignment_checks += 1
            regions = set(sign_by_id[str(card["sign_id"])].get("regions") or [])
            require(required_regions <= regions, "localized sign is missing a browse region")
            require("No localization stated" not in regions,
                    "localized sign remains classified only as unlocalized")

    for contribution in contributions:
        work_id = str(contribution["work_id"])
        require(work_id in profile_by_id, "contribution work lacks a profile")
        work_findings = [value for value in row_findings if finding_work[value] == work_id]
        work_statistics = [value for value in row_statistics
                           if finding_work[statistic_finding[value]] == work_id]
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
        if state in {"EVIDENCE_BEARING_WEIGHTED", "EVIDENCE_LINKED_WEIGHT_PENDING"}:
            linked_works.add(work_id)
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
    "source_reports": 77, "canonical_works": 73, "contributes_weight": 65,
    "linked_authority_pending": 2, "no_sign_axis_contribution": 6,
}
require(all(accounting.get(key) == value for key, value in expected_accounting.items()),
        "current corpus accounting changed")
require(len(weighted_works) == 65 and len(linked_works - weighted_works) == 2
        and len(set(profile_ids) - linked_works) == 6,
        "derived work coverage does not reconcile to corpus accounting")

projection = authority["current_projection_audit"]
require(projection == {
    "status": "PASS", "sign_axis_rows": 766, "unique_sign_axis_pairs": 766,
    "localization_rows_checked_against_browse_regions": alignment_checks,
    "positive_weight_outside_weighted_rows": 0,
    "duplicate_work_contributions": 0,
    "browse_region_memberships_added_from_source_targets": 31,
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
