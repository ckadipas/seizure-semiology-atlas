#!/usr/bin/env python3
"""Validate the redacted, generated atlas bundle without private source access."""

import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "atlas_bundle.json"
CARD_STATES = {
    "EVIDENCE_BEARING_WEIGHTED", "TARGET_LINKAGE_NEEDED", "NO_SOURCE_TARGET",
}
SCHEME_ID = "WEIGHT:HISTORICAL_D5D9DD2"
SCHEME_STATUS = "HISTORICAL_RESTORED"
CLASS_BASE = {"I": 3.0, "II": 2.0, "III": 1.0}
DIRECTNESS_MULTIPLIERS = {
    "postop": 1.5, "seeg": 1.5, "intracranial_eeg": 1.35,
    "video_eeg": 1.2, "imaging_concordance": 1.15,
    "scalp_eeg": 1.1, "review": 1.0, "none": 0.9,
}
DIRECTNESS_ORDER = tuple(DIRECTNESS_MULTIPLIERS)
APPROVED_CLASS_II_DESIGNS = {
    "CASE_SERIES", "DIAGNOSTIC_STUDY", "RETROSPECTIVE_COHORT",
}
SYSTEMATIC_DESIGNS = {"SYSTEMATIC_REVIEW", "META_ANALYSIS"}
CASE_DESIGNS = {"CASE_REPORT", "CASE_OBSERVATION"}
RESTATEMENT_ROLES = {"CITED_STUDY_RESTATEMENT", "PRIMARY_RESULT_SAME_SOURCE_RESTATEMENT"}
CONTEXT_ROLES = {"EDUCATIONAL_STATEMENT", "SOURCE_CONTEXT"}
EXCLUDED_RELATIONSHIP_DISPOSITIONS = {"RESTATEMENT", "OVERLAP"}
SIZE_CAP = 2.0
REFERENCE_STANDARD_MAP = {
    "POSTOPERATIVE_SEIZURE_FREEDOM": "postop",
    "SEIZURE_FREE_POSTOPERATIVE_OUTCOME": "postop",
    "SEEG": "seeg", "STEREO_EEG": "seeg", "SEEG_OR_STEREO_EEG": "seeg",
    "INTRACRANIAL_EEG": "intracranial_eeg", "ECOG": "intracranial_eeg",
    "VIDEO_EEG": "video_eeg", "IMAGING_CONCORDANCE": "imaging_concordance",
    "LESION_CONCORDANCE": "imaging_concordance", "SCALP_ICTAL_EEG": "scalp_eeg",
}
LOCATION_LABELS = {
    "REG:TEMPORAL": "Temporal", "REG:FRONTAL": "Frontal",
    "REG:PARIETAL": "Parietal", "REG:OCCIPITAL": "Occipital",
    "REG:INSULAR": "Insular", "REG:LIMBIC": "Limbic",
    "REG:DEEP_SUBCORTICAL": "Deep/Subcortical",
    "REG:MULTIREGIONAL_PROPAGATION": "Multiregional/Propagation",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(values):
    return len(values) == len(set(values))


def normalized_target(axis, value):
    raw = str(value or "").strip()
    if axis == "LOCALIZATION":
        token = raw.upper().replace("-", "_").replace(" ", "_")
        if token in LOCATION_LABELS:
            return token, LOCATION_LABELS[token], "REGION"
        if token.startswith("BA:") and token[3:].isdigit():
            return token, f"Brodmann area {token[3:]}", "AREA"
        return None
    token = " ".join(part for part in "".join(
        character if character.isalnum() else " " for character in raw.casefold()
    ).split())
    if "non dominant" in token or "nondominant" in token:
        return "nondominant", "Non-dominant hemisphere", "LATERALITY"
    if token == "dominant" or "dominant hemisphere" in token:
        return "dominant", "Dominant hemisphere", "LATERALITY"
    if "contralateral" in token or token == "contra" or "opposite side" in token:
        return "contra", "Contralateral", "LATERALITY"
    if "ipsilateral" in token or token == "ipsi" or "same side" in token:
        return "ipsi", "Ipsilateral", "LATERALITY"
    if token in {"bilateral", "bilateral hemisphere", "bilateral hemispheres"}:
        return "bilateral", "Bilateral", "LATERALITY"
    if token in {"right", "right hemisphere"}:
        return "right", "Right hemisphere", "LATERALITY"
    if token in {"left", "left hemisphere"}:
        return "left", "Left hemisphere", "LATERALITY"
    if token in {"nonlat", "non lateralizing", "non lateralising", "does not lateralize", "does not lateralise"}:
        return "nonassoc", "Does not lateralize", "STATUS"
    return None


bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
require(
    set(bundle) == {
        "brodmann", "classifications", "corpus", "evidence_authority",
        "evidence_synthesis", "finding_locations", "schema_version",
        "semantic_digest", "signs", "source_digests",
    },
    "unexpected top-level bundle contract",
)
require(bundle["schema_version"] == "atlas-public-bundle-1.4.1", "unexpected bundle schema version")
require(re.fullmatch(r"[0-9a-f]{64}", bundle["semantic_digest"]) is not None, "invalid semantic digest")
digest_payload = dict(bundle)
digest_payload.pop("semantic_digest")
expected_digest = hashlib.sha256(
    json.dumps(digest_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
).hexdigest()
require(bundle["semantic_digest"] == expected_digest, "semantic digest mismatch")

corpus = bundle["corpus"]
sources = corpus["sources"]
findings = [finding for source in sources for finding in source["findings"]]
finding_refs = [finding["source_finding_ref"] for finding in findings]
statistics = [statistic for finding in findings for statistic in finding["statistics"]]
statistic_ids = [statistic["statistic_id"] for statistic in statistics]
sign_ids = [str(sign["id"]) for sign in bundle["signs"]]
finding_ref_set, statistic_id_set, sign_id_set = set(finding_refs), set(statistic_ids), set(sign_ids)
finding_work, statistic_finding = {}, {}
finding_by_ref, statistic_by_id = {}, {}
areas = bundle["brodmann"]["areas"]
classifications = bundle["classifications"]
classification_schemes = {row["scheme_id"] for row in classifications["schemes"]}
classification_nodes = {row["node_id"]: row for row in classifications["nodes"]}

require(unique(finding_refs), "duplicate finding identity")
require(unique(statistic_ids), "duplicate statistic identity")
require(unique(sign_ids), "duplicate sign identity")
require(len({source["source_sha256"] for source in sources}) == len(sources), "duplicate source identity")
require(len(sources) == 77, "current public source-report count changed")
require(len(finding_refs) == 4119, "current public finding count changed")
require(len(statistic_ids) == 4514, "current public statistic count changed")
require(classification_schemes == {"LUDERS_5D_2005", "ILAE_SEIZURE_2025"}, "classification schemes changed")
require(all(row["scheme_id"] in classification_schemes for row in classification_nodes.values()), "classification node references an absent scheme")
require(
    all(str(row["sign_id"]) in sign_id_set and row["node_id"] in classification_nodes for row in classifications["sign_mappings"]),
    "classification mapping references an absent sign or node",
)
for source in sources:
    sha, work_id = source["source_sha256"], str(source["work_id"])
    require(re.fullmatch(r"[0-9a-f]{64}", sha) is not None, "invalid source digest")
    require(re.fullmatch(r"[0-9a-f]{64}", source["source_report_sha256"]) is not None, "invalid report digest")
    for finding in source["findings"]:
        finding_ref = finding["source_finding_ref"]
        finding_work[finding_ref] = work_id
        finding_by_ref[finding_ref] = finding
        require(finding_ref.startswith(f"{sha}:"), "finding/source identity mismatch")
        require(bool(finding["locators"] and finding["evidence_text"]), "finding lacks a source locator or evidence text")
        require(unique([row["statistic_id"] for row in finding["statistics"]]), "finding duplicates a statistic")
        for statistic in finding["statistics"]:
            statistic_finding[statistic["statistic_id"]] = finding_ref
            statistic_by_id[statistic["statistic_id"]] = statistic
        for sign_id in finding["exact_sign_ids"] + finding["related_sign_ids"]:
            require(str(sign_id) in sign_id_set, "finding references an absent public sign")

accounting = corpus["integration_accounting"]
require(accounting["source_reports"] == len(sources), "source-report count mismatch")
require(accounting["public_ledger_findings"] == len(findings), "finding count mismatch")
require(accounting["source_reported_statistics"] == len(statistic_ids), "statistic count mismatch")
require(set(bundle["finding_locations"]) <= finding_ref_set, "location references an absent finding")
for location in bundle["finding_locations"].values():
    require(set(location) == {"regions", "areas"}, "location contains private or unexpected fields")
    require(unique(location["regions"]), "duplicate region link")
    require(unique(location["areas"]), "duplicate Brodmann link")
    require(all(str(area_id) in areas for area_id in location["areas"]), "unknown Brodmann link")

authority = bundle["evidence_authority"]
profiles = authority["profiles"]
profile_ids = [str(row["work_id"]) for row in profiles]
profile_by_id = {str(row["work_id"]): row for row in profiles}
require(unique(profile_ids), "duplicate canonical work profile")
require(authority["canonical_work_count"] == len(profiles) == 73, "canonical work count changed")
require(authority["source_report_count"] == len(sources) == 77, "source-report authority count changed")
require(set(finding_work.values()) <= set(profile_ids), "public finding work lacks an authority profile")
require(sum(row.get("metadata_status") == "DESIGN_NOT_RESOLVED" for row in profiles) == 27, "unclassified work count changed")
require(authority["scheme_id"] == SCHEME_ID, "wrong evidence-weight scheme")
require(authority["scheme_status"] == SCHEME_STATUS, "wrong evidence-weight source status")
require(authority["approval_basis"] == "OWNER_APPROVED_ACTIVE_TASK", "weight scheme lacks active-task approval binding")
require(authority["class_base"] == CLASS_BASE, "evidence class bases changed")
require(authority["ground_truth_multipliers"] == DIRECTNESS_MULTIPLIERS, "directness multipliers changed")
require(float(authority["size_cap"]) == SIZE_CAP, "size cap changed")
require(set(authority["class_ii_designs"]) == APPROVED_CLASS_II_DESIGNS, "class II design whitelist changed")
require(bool(authority.get("display_method")), "exported weighting method is missing")

synthesis = bundle["evidence_synthesis"]
release = synthesis["release"]
axes = synthesis["finding_axes"]
sign_axes = synthesis["sign_finding_axes"]
cards = synthesis["axis_summaries"]
families = synthesis["descriptive_families"]
owner_release_cards = [row for row in cards if not row.get("supplemental_projection")]
supplemental_cards = [row for row in cards if row.get("supplemental_projection")]
card_ids = [row["synthesis_id"] for row in cards]
family_ids = [row["analysis_id"] for row in families]
require(release["private_finding_count"] == 4121, "private synthesis finding count changed")
require(release["public_finding_count"] == len(findings) == 4119, "public synthesis finding count mismatch")
require(release["axis_count"] == len(axes) == 8238, "synthesis axis count mismatch")
require(release["owner_release_card_count"] == len(owner_release_cards) == 766, "owner release-card count mismatch")
require(release["supplemental_card_count"] == len(supplemental_cards) == 46, "supplemental DB-projection count mismatch")
require(release["synthesis_card_count"] == len(cards) == 812, "synthesis card count mismatch")
require(release["descriptive_family_count"] == len(families) == 1555, "descriptive-family count mismatch")
require(release["retained_artifact_count"] == 146, "retained-artifact count mismatch")
require(unique(card_ids), "duplicate synthesis-card identity")
require(unique(family_ids), "duplicate descriptive-family identity")
require(unique([(row["group_id"], row["axis"]) for row in cards]), "duplicate group-axis card")
require(
    all(row["synthesis_id"].startswith("SYNTH_SUPPLEMENTAL:") for row in supplemental_cards),
    "supplemental card lacks deterministic identity",
)
require(
    len({str(row["sign_id"]) for row in supplemental_cards}) == 23
    and all(
        {row["axis"] for row in supplemental_cards if str(row["sign_id"]) == sign_id}
        == {"LATERALIZATION", "LOCALIZATION"}
        for sign_id in {str(row["sign_id"]) for row in supplemental_cards}
    ),
    "supplemental DB projections do not cover both axes for every linked omitted sign",
)
expected_sign_axes = {
    (str(sign_id), axis)
    for sign_id in sign_ids
    for axis in ("LATERALIZATION", "LOCALIZATION")
}
actual_sign_axes = {(str(row["sign_id"]), row["axis"]) for row in cards}
require(
    actual_sign_axes <= expected_sign_axes,
    "release card contains an unknown public sign-axis identity",
)
require(unique([(row["finding_ref"], row["axis"]) for row in axes]), "duplicate finding-axis identity")
require(all(row["finding_ref"] in finding_ref_set for row in axes), "finding axis references an absent finding")
require(all(str(row["sign_id"]) in sign_id_set for row in cards), "synthesis card references an absent sign")
require(all(str(sign_id) in sign_id_set for row in families for sign_id in row["sign_ids"]), "descriptive family references an absent sign")
expected_cards_by_sign = {str(sign_id): [] for sign_id in sign_ids}
for card in cards:
    expected_cards_by_sign[str(card["sign_id"])].append(card["synthesis_id"])
require(synthesis["cards_by_sign"] == expected_cards_by_sign, "cards_by_sign is not exactly bidirectional with axis_summaries")
require(all(item_id in set(family_ids) for item_ids in synthesis["families_by_sign"].values() for item_id in item_ids), "sign references an absent descriptive family")
finding_axis_by_key = {(row["finding_ref"], row["axis"]): row for row in axes}
sign_axis_details = defaultdict(list)
for row in sign_axes:
    sign_axis_details[(row["group_id"], row["axis"])].extend(row["target_details"])

for card in cards:
    row_findings = card["row_finding_refs"]
    row_statistics = card["row_statistic_ids"]
    row_works = [str(value) for value in card["row_work_ids"]]
    declared_works = [str(value) for value in card["declared_source_work_ids"]]
    contributions = card["contributions"]
    lineage = card["row_lineage"]
    require(set(lineage) == {
        "supporting_finding_refs", "audit_cited_finding_refs",
        "ledger_group_finding_refs", "release_group_axis_finding_refs",
        "supplemental_exact_sign_finding_refs",
    }, "invalid row lineage contract")
    expected_row_findings = list(dict.fromkeys(
        value for key in (
            "supporting_finding_refs", "audit_cited_finding_refs",
            "ledger_group_finding_refs", "release_group_axis_finding_refs",
            "supplemental_exact_sign_finding_refs",
        ) for value in lineage[key]
    ))
    require(row_findings == expected_row_findings, "row findings differ from exact card-axis release lineage")
    require(unique(row_findings), "axis card duplicates a row finding")
    require(unique(row_statistics), "axis card duplicates a row statistic")
    require(unique(row_works), "axis card duplicates a row work")
    require(unique(declared_works), "axis card duplicates a declared work")
    require(set(row_findings) <= finding_ref_set, "axis card references an absent finding")
    require(set(row_statistics) <= statistic_id_set, "axis card references an absent statistic")
    require(all(statistic_finding[value] in set(row_findings) for value in row_statistics), "row statistic does not belong to a row finding")
    represented_works = {finding_work[value] for value in row_findings}
    represented_works.update(finding_work[statistic_finding[value]] for value in row_statistics)
    require(set(row_works) == represented_works | set(declared_works), "row work list differs from row provenance")
    require(set(row_works) <= set(profile_ids), "row work has no authority profile")
    require(card["row_finding_count"] == len(row_findings), "row finding count differs from its list")
    require(card["row_statistic_count"] == len(row_statistics), "row statistic count differs from its list")
    require(card["row_work_count"] == len(row_works), "row work count differs from its list")
    contribution_ids = [str(row["work_id"]) for row in contributions]
    require(unique(contribution_ids), "axis card duplicates a work contribution")
    require(set(contribution_ids) == set(row_works), "axis card work/contribution mismatch")
    for contribution in contributions:
        work_id = str(contribution["work_id"])
        work_findings = [value for value in row_findings if finding_work[value] == work_id]
        work_statistics = [
            value for value in row_statistics
            if finding_work[statistic_finding[value]] == work_id
        ]
        require(contribution["display_name"] == profile_by_id[work_id]["display_name"], "contribution does not use canonical work display name")
        require(contribution["row_finding_refs"] == work_findings, "contribution finding list is not exact")
        require(contribution["row_statistic_ids"] == work_statistics, "contribution statistic list is not exact")
        evidence_class = contribution["evidence_class"]
        components = contribution["weight_components"]
        require(evidence_class in {"I", "II", "III", "UNCLASSIFIED"}, "invalid contribution evidence class")
        require(set(components) == {"class_base", "directness_type", "directness_multiplier", "size_factor"}, "invalid contribution weight components")
        expected_weight = round(
            float(components["class_base"])
            * float(components["directness_multiplier"])
            * float(components["size_factor"]),
            3,
        )
        require(math.isclose(float(contribution["final_weight"]), expected_weight, abs_tol=1e-9), "contribution final weight differs from components")
        expected_base = CLASS_BASE.get(evidence_class, 0.0)
        require(float(components["class_base"]) == expected_base, "contribution class base differs from approved scheme")
        directness_type = components["directness_type"]
        require(directness_type in DIRECTNESS_MULTIPLIERS, "unknown contribution directness type")
        require(float(components["directness_multiplier"]) == DIRECTNESS_MULTIPLIERS[directness_type], "contribution directness multiplier differs from approved scheme")
        primary_input_ids = contribution["primary_input_statistic_ids"]
        exact_input_ids = contribution["exact_descriptive_input_statistic_ids"]
        primary_designs = set(contribution["primary_input_study_designs"])
        primary_standards = set(contribution["primary_input_reference_standards"])
        require(unique(exact_input_ids), "contribution duplicates an exact descriptive input")
        require(set(exact_input_ids) <= set(work_statistics), "exact descriptive input is outside row statistics")
        require(unique(primary_input_ids), "contribution duplicates an exact primary input")
        require(set(primary_input_ids) <= set(exact_input_ids), "exact primary input is outside axis/group inputs")
        canonical_primary_input_ids = [
            statistic_id for statistic_id in work_statistics
            if statistic_id in set(exact_input_ids)
            if str(statistic_by_id[statistic_id].get("evidence_role") or "").upper()
            == "PRIMARY_RESULT"
            and bool(statistic_by_id[statistic_id].get("independent_evidence"))
        ]
        require(
            primary_input_ids == canonical_primary_input_ids,
            "exact primary inputs differ from canonical statistic role/independence fields",
        )
        require(primary_designs <= set(contribution["study_designs"]), "primary design is outside exact-row input designs")
        require(contribution["independent_primary"] == bool(primary_input_ids), "independent-primary state differs from exact inputs")
        require(set(contribution["reference_standards"]) == primary_standards, "directness standards include a non-primary input")
        sample_size = contribution["sample_size_used"]
        canonical_denominators = [
            float(statistic_by_id[statistic_id]["denominator_value"])
            for statistic_id in primary_input_ids
            if statistic_by_id[statistic_id].get("denominator_value") not in (None, "")
            and float(statistic_by_id[statistic_id]["denominator_value"]) > 0
        ]
        expected_sample_size = max(canonical_denominators, default=None)
        if evidence_class == "I":
            expected_sample_size = None
        require(
            (sample_size is None and expected_sample_size is None)
            or (
                sample_size is not None and expected_sample_size is not None
                and math.isclose(float(sample_size), expected_sample_size, abs_tol=1e-9)
            ),
            "contribution sample size differs from canonical primary-statistic denominators",
        )
        expected_size = 1.0 if sample_size is None else round(min(SIZE_CAP, 1.0 + math.log10(float(sample_size)) / 2.0), 3)
        require(float(components["size_factor"]) == expected_size, "contribution size factor differs from exact primary input")
        if evidence_class == "UNCLASSIFIED":
            require(float(contribution["final_weight"]) == 0, "unclassified contribution has numerical weight")
        if not contribution["independent_primary"]:
            require(float(components["size_factor"]) == 1.0, "non-primary contribution inherited a size bonus")
            require(components["directness_type"] in {"review", "none"}, "non-primary contribution inherited direct confirmation")
        roles, designs = set(contribution["evidence_roles"]), set(contribution["study_designs"])
        canonical_roles = {
            str(record.get("evidence_role") or "").upper()
            for record in [
                *(finding_by_ref[value] for value in work_findings),
                *(statistic_by_id[value] for value in work_statistics),
            ]
        } - {"", "NOT_REPORTED", "NOT_RESOLVED"}
        require(roles == canonical_roles, "contribution evidence roles differ from canonical records")
        row_has_independent_primary_record = any(
            str(record.get("evidence_role") or "").upper() == "PRIMARY_RESULT"
            and bool(record.get("independent_evidence"))
            for record in [
                *(finding_by_ref[value] for value in work_findings),
                *(statistic_by_id[value] for value in work_statistics),
            ]
        )
        if "GUIDELINE_RECOMMENDATION" in roles:
            expected_class, expected_category = "I", "Society guideline or consensus"
        elif "REVIEW_SYNTHESIS" in roles and designs & SYSTEMATIC_DESIGNS:
            expected_class, expected_category = "I", "Systematic review or meta-analysis"
        elif contribution["independent_primary"] and primary_designs & APPROVED_CLASS_II_DESIGNS:
            expected_class, expected_category = "II", "Independent primary study"
        elif contribution["independent_primary"] and not primary_designs:
            expected_class, expected_category = "UNCLASSIFIED", "Structured design not resolved"
        elif row_has_independent_primary_record and not contribution["independent_primary"]:
            expected_class, expected_category = "UNCLASSIFIED", "Exact primary input metadata not resolved"
        elif primary_designs & CASE_DESIGNS or designs & CASE_DESIGNS or "CASE_OBSERVATION" in roles:
            expected_class, expected_category = "III", "Case report or observation"
        elif contribution["independent_primary"]:
            expected_class, expected_category = "UNCLASSIFIED", "Structured design outside approved Class II set"
        elif "NARRATIVE_REVIEW" in designs or roles & RESTATEMENT_ROLES or roles & CONTEXT_ROLES:
            expected_class, expected_category = "III", "Narrative, educational, or cited context"
        elif "PRIMARY_RESULT" in roles:
            expected_class, expected_category = "III", "Non-independent primary or overlapping context"
        else:
            expected_class, expected_category = "UNCLASSIFIED", "Structured design not resolved"
        require(
            (evidence_class, contribution["authority_category"])
            == (expected_class, expected_category),
            "contribution class/category differs from the complete exact-row authority truth table",
        )
        if evidence_class == "I":
            expected_directness = "review"
        elif evidence_class == "UNCLASSIFIED":
            expected_directness = "none"
        elif contribution["independent_primary"]:
            recognized = {
                REFERENCE_STANDARD_MAP[value]
                for value in primary_standards if value in REFERENCE_STANDARD_MAP
            }
            expected_directness = min(
                recognized or {"none"},
                key=lambda value: (-DIRECTNESS_MULTIPLIERS[value], DIRECTNESS_ORDER.index(value)),
            )
        elif (
            roles & {
                "CITED_STUDY_RESTATEMENT", "PRIMARY_RESULT_SAME_SOURCE_RESTATEMENT",
                "EDUCATIONAL_STATEMENT", "SOURCE_CONTEXT", "REVIEW_SYNTHESIS",
            }
            or "NARRATIVE_REVIEW" in designs
        ):
            expected_directness = "review"
        else:
            expected_directness = "none"
        require(directness_type == expected_directness, "directness type differs from exact independent-primary inputs")
        if evidence_class == "I":
            require(
                "GUIDELINE_RECOMMENDATION" in roles
                or ("REVIEW_SYNTHESIS" in roles and designs & {"SYSTEMATIC_REVIEW", "META_ANALYSIS"}),
                "class I contribution lacks exact-row guideline or review synthesis",
            )
            require(float(components["directness_multiplier"]) == 1.0, "class I review/guideline received a directness bonus")
            require(float(components["size_factor"]) == 1.0, "class I review/guideline received a size bonus")
        if evidence_class == "II":
            require(contribution["independent_primary"], "class II contribution is not exact-row independent primary")
            require(bool(primary_designs & APPROVED_CLASS_II_DESIGNS), "class II contribution lacks an approved primary-study design")
    target = card["target_contract"]
    require(set(target) == {
        "owner_cleared_raw_targets", "identity_group_finding_refs",
        "exact_group_finding_raw_targets",
        "additional_linkage_targets", "nonidentity_group_raw_targets",
        "nonidentity_group_finding_refs",
        "excluded_relationship_raw_targets", "reported_targets",
        "unresolved_raw_targets", "finding_wide_only_raw_targets",
        "true_nonassociation",
    }, "invalid target contract")
    require(unique(target["identity_group_finding_refs"]), "identity-group finding linkage is duplicated")
    require(
        set(target["identity_group_finding_refs"]) <= finding_ref_set,
        "identity-group finding linkage references an absent finding",
    )
    require(unique(target["nonidentity_group_finding_refs"]), "nonidentity finding linkage is duplicated")
    require(
        set(target["nonidentity_group_finding_refs"]) <= finding_ref_set,
        "nonidentity finding linkage references an absent finding",
    )
    if card["supplemental_projection"]:
        require(
            card["related_finding_refs"] == target["nonidentity_group_finding_refs"],
            "supplemental related-finding lineage differs from its target contract",
        )
    else:
        require(not lineage["supplemental_exact_sign_finding_refs"], "owner release card contains supplemental lineage")
    require(unique([row["key"] for row in target["reported_targets"]]), "axis card duplicates a reported target")
    identity_details = sign_axis_details[(card["group_id"], card["axis"])]
    expected_exact_details = [
        detail for detail in identity_details if detail["finding_ref"] in set(row_findings)
    ]
    expected_additional_details = [
        detail for detail in identity_details if detail["finding_ref"] not in set(row_findings)
    ]
    require(target["exact_group_finding_raw_targets"] == expected_exact_details, "exact-row sign targets differ from the sign-target inventory")
    actual_additional_details = [
        detail for item in target["additional_linkage_targets"]
        for detail in item["details"]
    ]
    require(
        sorted(json.dumps(row, sort_keys=True) for row in actual_additional_details)
        == sorted(json.dumps(row, sort_keys=True) for row in expected_additional_details),
        "sign targets outside row lineage were lost or weighted",
    )
    for reported in target["reported_targets"]:
        require(set(reported) == {
            "key", "label", "raw", "origins", "contexts", "scopes",
            "target_level", "details",
        }, "invalid reported-target fields")
        require(bool(reported["key"] and reported["label"] and reported["raw"] and reported["origins"]), "reported target lacks identity or provenance")
        require(unique(reported["raw"]), "reported target duplicates a raw value")
        require(unique(reported["origins"]), "reported target duplicates an origin")
        require(unique(reported["contexts"]), "reported target duplicates a context")
        require(unique(reported["scopes"]), "reported target duplicates a scope")
        for raw in reported["raw"]:
            normalized = normalized_target(card["axis"], raw)
            if reported["key"] == "nonassoc" and raw in {"NON_LOCALIZING", "NON_LATERALIZING"}:
                normalized = (
                    "nonassoc",
                    "Does not localize" if card["axis"] == "LOCALIZATION" else "Does not lateralize",
                    "STATUS",
                )
            require(
                normalized == (reported["key"], reported["label"], reported["target_level"]),
                "reported target key/label/raw identity mismatch",
            )
        for detail in reported["details"]:
            require(set(detail) == {
                "raw", "finding_ref", "region_id", "area_id", "location_key",
                "assertion_type", "assertion_scope", "assertion_text",
                "reviewed_assertion_text", "contexts", "scopes",
            }, "reported sign-target detail fields changed")
            require(detail["raw"] in reported["raw"], "reported detail raw value is not retained")
            require(set(detail["contexts"]) <= set(reported["contexts"]), "reported detail context was not retained")
            require(set(detail["scopes"]) <= set(reported["scopes"]), "reported detail scope was not retained")
    for relationship_target in target["owner_cleared_raw_targets"]:
        dispositions = set(relationship_target["dispositions"])
        require(
            not (dispositions & EXCLUDED_RELATIONSHIP_DISPOSITIONS)
            and (not dispositions or "SUPPORTED_EVIDENCE" in dispositions),
            "excluded relationship disposition became a clinical target",
        )
    for relationship_target in target["excluded_relationship_raw_targets"]:
        dispositions = set(relationship_target["dispositions"])
        require(
            bool(dispositions & EXCLUDED_RELATIONSHIP_DISPOSITIONS)
            or bool(dispositions and "SUPPORTED_EVIDENCE" not in dispositions),
            "eligible owner relationship was excluded",
        )

    expected_reported = []
    def merge_expected(detail, origin):
        normalized = normalized_target(card["axis"], detail["raw"])
        if normalized is None:
            return
        key, label, level = normalized
        item = next((row for row in expected_reported if row["key"] == key), None)
        if item is None:
            item = {
                "key": key, "label": label, "raw": [], "origins": [],
                "contexts": [], "scopes": [], "target_level": level, "details": [],
            }
            expected_reported.append(item)
        for field, values in (
            ("raw", [detail["raw"]]), ("origins", [origin]),
            ("contexts", detail.get("contexts") or []),
            ("scopes", detail.get("scopes") or []),
        ):
            item[field].extend(value for value in values if value and value not in item[field])
        if detail.get("finding_ref") and detail not in item["details"]:
            item["details"].append(detail)
    for raw_target in target["owner_cleared_raw_targets"]:
        merge_expected(raw_target, "OWNER_CLEARED")
    for raw_target in target["exact_group_finding_raw_targets"]:
        merge_expected(raw_target, "EXACT_ROW_SIGN_ASSERTION")
    if target["true_nonassociation"] and not any(
        row["key"] == "nonassoc" for row in expected_reported
    ):
        expected_reported.append({
            "key": "nonassoc",
            "label": "Does not localize" if card["axis"] == "LOCALIZATION" else "Does not lateralize",
            "raw": [card["pattern_status"]], "origins": ["OWNER_CLEARED_STATUS"],
            "contexts": [], "scopes": ["OWNER_CLEARED_STATUS"],
            "target_level": "STATUS", "details": [],
        })
    require(target["reported_targets"] == expected_reported, "reported targets differ from exact allowed provenance")

    expected_finding_wide = []
    for finding_ref in row_findings:
        finding_axis = finding_axis_by_key.get((finding_ref, card["axis"])) or {}
        exact_raw = {
            detail["raw"] for detail in expected_exact_details
            if detail["finding_ref"] == finding_ref
        }
        values = (
            [*(finding_axis.get("region_ids") or []), *(
                f"BA:{value}" for value in finding_axis.get("brodmann_ids") or []
            )]
            if card["axis"] == "LOCALIZATION"
            else [*(finding_axis.get("normalized_values") or [])]
        )
        values.extend(finding_axis.get("source_native_targets") or [])
        for raw in dict.fromkeys(str(value) for value in values if str(value or "").strip()):
            if raw and raw not in exact_raw:
                detail = {
                    "raw": raw, "finding_ref": finding_ref,
                    "region_id": "", "area_id": "", "location_key": "",
                    "assertion_type": "", "assertion_scope": "",
                    "assertion_text": "", "contexts": [],
                    "scopes": ["FINDING_WIDE_ONLY"],
                }
                if detail not in expected_finding_wide:
                    expected_finding_wide.append(detail)
    major_region_terms = {
        value.casefold() for value in LOCATION_LABELS.values()
        if value not in {"Deep/Subcortical", "Multiregional/Propagation"}
    }
    for finding_ref in target["identity_group_finding_refs"]:
        if finding_ref in set(row_findings):
            continue
        finding_axis = finding_axis_by_key.get((finding_ref, card["axis"])) or {}
        disposition = str(finding_axis.get("disposition") or "").upper()
        if disposition == "OUT_OF_SCOPE":
            continue
        values = (
            [*(finding_axis.get("region_ids") or []), *(
                f"BA:{value}" for value in finding_axis.get("brodmann_ids") or []
            )]
            if card["axis"] == "LOCALIZATION"
            else [*(finding_axis.get("normalized_values") or [])]
        )
        values.extend(
            value for value in finding_axis.get("source_native_targets") or []
            if disposition == "UNMAPPED"
            or (
                card["axis"] == "LOCALIZATION"
                and any(
                    re.search(rf"\b{re.escape(term)}\b", str(value), re.I)
                    for term in major_region_terms
                )
            )
        )
        exact_raw = {
            detail["raw"] for detail in expected_exact_details
            if detail["finding_ref"] == finding_ref
        }
        for raw in dict.fromkeys(str(value) for value in values if str(value or "").strip()):
            detail = {
                "raw": raw, "finding_ref": finding_ref,
                "region_id": "", "area_id": "", "location_key": "",
                "assertion_type": "", "assertion_scope": "",
                "assertion_text": "", "contexts": [],
                "scopes": ["IDENTITY_GROUP_FINDING_WIDE_ONLY"],
            }
            if raw not in exact_raw and detail not in expected_finding_wide:
                expected_finding_wide.append(detail)
    require(target["finding_wide_only_raw_targets"] == expected_finding_wide, "finding-wide target remainder was discarded or transferred")
    state = card["categorization_state"]
    require(state in CARD_STATES, "axis card has no valid categorization state")
    recorded_raw = bool(
        target["owner_cleared_raw_targets"]
        or target["exact_group_finding_raw_targets"]
        or target["additional_linkage_targets"]
        or target["nonidentity_group_raw_targets"]
        or target["nonidentity_group_finding_refs"]
        or target["excluded_relationship_raw_targets"]
        or target["unresolved_raw_targets"]
        or target["finding_wide_only_raw_targets"]
        or target["true_nonassociation"]
        or (card["supplemental_projection"] and row_findings)
    )
    expected_state = (
        "EVIDENCE_BEARING_WEIGHTED"
        if target["reported_targets"] and row_findings and row_works
        else "TARGET_LINKAGE_NEEDED"
        if recorded_raw or target["reported_targets"]
        else "NO_SOURCE_TARGET"
    )
    require(state == expected_state, "axis card categorization differs from its one expected state")
    require(not (state == "NO_SOURCE_TARGET" and (
        target["exact_group_finding_raw_targets"] or target["additional_linkage_targets"]
    )), "sign-scoped DB target was categorized as no source target")

cards_by_group_axis = {(card["group_id"], card["axis"]): card for card in cards}
for group_id, expected_keys in {
    "SGRP:39de1a04a4576f5c2378": {"REG:FRONTAL", "REG:TEMPORAL", "REG:PARIETAL", "REG:OCCIPITAL"},
    "SGRP:d680768b4cc9f60e69dd": {"REG:TEMPORAL", "REG:OCCIPITAL"},
    "SGRP:3193ea2c50ce2b91987b": {"REG:TEMPORAL", "REG:FRONTAL", "REG:PARIETAL", "REG:OCCIPITAL", "REG:INSULAR", "BA:40"},
}.items():
    tracer = cards_by_group_axis[(group_id, "LOCALIZATION")]
    contract = tracer["target_contract"]
    inventory = contract["reported_targets"] + contract["additional_linkage_targets"]
    inventory_keys = {row["key"] for row in inventory}
    inventory_keys.update(
        row["raw"] for row in contract["nonidentity_group_raw_targets"]
        if str(row["raw"]).startswith(("REG:", "BA:"))
    )
    inventory_keys.update(
        row["raw"] for row in (
            contract["finding_wide_only_raw_targets"] + contract["unresolved_raw_targets"]
        ) if str(row["raw"]).startswith(("REG:", "BA:"))
    )
    require(expected_keys <= inventory_keys, f"localization tracer targets missing for {group_id}")
    require(
        tracer["categorization_state"] == "EVIDENCE_BEARING_WEIGHTED",
        f"localization tracer is not evidence-bearing for {group_id}",
    )
figure_card = cards_by_group_axis[("SGRP:39de1a04a4576f5c2378", "LOCALIZATION")]
require(figure_card["categorization_state"] == "EVIDENCE_BEARING_WEIGHTED", "Figure-of-4 localization is not evidence-bearing")
require(figure_card["target_contract"]["true_nonassociation"], "Figure-of-4 owner-cleared non-specificity status was lost")
require(
    {"REG:FRONTAL", "REG:TEMPORAL", "nonassoc"}
    <= {row["key"] for row in figure_card["target_contract"]["reported_targets"]},
    "Figure-of-4 mixed reported/localization state was not preserved",
)
figure_inventory = figure_card["target_contract"]["reported_targets"] + figure_card["target_contract"]["additional_linkage_targets"]
figure_contexts = {context for row in figure_inventory for context in row["contexts"]}
figure_contexts.update(
    context for row in figure_card["target_contract"]["nonidentity_group_raw_targets"]
    for context in row["contexts"]
)
require({"SIGN_SPECIFIC", "PROPAGATION", "COHORT_CONTEXT"} <= figure_contexts, "Figure-of-4 assertion contexts were lost")

serialized = json.dumps(bundle, sort_keys=True).lower()
for private_marker in (
    '"owner_comment"', '"owner_decision"', '"resolution_json"', '"context_json"',
    '"adjudication_event"', '"private_pdf_path"', '"local_source_path"',
    '"owner_question"', '"review_origin"', '"review_status"',
):
    require(private_marker not in serialized, f"private field leaked: {private_marker}")

print(json.dumps({
    "source_reports": len(sources),
    "canonical_works": len(profiles),
    "findings": len(findings),
    "statistics": len(statistic_ids),
    "signs": len(sign_ids),
    "finding_axes": len(axes),
    "synthesis_cards": len(cards),
    "descriptive_families": len(families),
    "status": "PASS",
}, sort_keys=True))
