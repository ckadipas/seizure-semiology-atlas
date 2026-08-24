#!/usr/bin/env python3
"""Validate the redacted, generated atlas bundle without private source access."""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "data" / "atlas_bundle.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
require(
    set(bundle) == {"brodmann", "classifications", "corpus", "evidence_synthesis", "finding_locations", "schema_version", "semantic_digest", "signs", "source_digests", "weighted_analysis"},
    "unexpected top-level bundle contract",
)
require(bundle["schema_version"] == "atlas-public-bundle-1.2.0", "unexpected bundle schema version")
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
areas = bundle["brodmann"]["areas"]
classifications = bundle["classifications"]
classification_schemes = {row["scheme_id"] for row in classifications["schemes"]}
classification_nodes = {row["node_id"]: row for row in classifications["nodes"]}

require(len(finding_refs) == len(set(finding_refs)), "duplicate finding identity")
require(len(statistic_ids) == len(set(statistic_ids)), "duplicate statistic identity")
require(len(sign_ids) == len(set(sign_ids)), "duplicate sign identity")
require(len({source["source_sha256"] for source in sources}) == len(sources), "duplicate source identity")
require(classification_schemes == {"LUDERS_5D_2005", "ILAE_SEIZURE_2025"}, "classification schemes changed")
require(all(row["scheme_id"] in classification_schemes for row in classification_nodes.values()), "classification node references an absent scheme")
require(
    all(str(row["sign_id"]) in set(sign_ids) and row["node_id"] in classification_nodes for row in classifications["sign_mappings"]),
    "classification mapping references an absent sign or node",
)
for source in sources:
    sha = source["source_sha256"]
    require(re.fullmatch(r"[0-9a-f]{64}", sha) is not None, "invalid source digest")
    require(re.fullmatch(r"[0-9a-f]{64}", source["source_report_sha256"]) is not None, "invalid report digest")
    for finding in source["findings"]:
        require(finding["source_finding_ref"].startswith(f"{sha}:"), "finding/source identity mismatch")
        require(bool(finding["locators"] and finding["evidence_text"]), "finding lacks a source locator or evidence text")
        require(len(finding["statistics"]) == len({statistic["statistic_id"] for statistic in finding["statistics"]}), "finding duplicates a statistic")
        for sign_id in finding["exact_sign_ids"] + finding["related_sign_ids"]:
            require(str(sign_id) in set(sign_ids), "finding references an absent public sign")

accounting = corpus["integration_accounting"]
require(accounting["source_reports"] == len(sources), "source count mismatch")
require(accounting["public_ledger_findings"] == len(findings), "finding count mismatch")
require(accounting["source_reported_statistics"] == len(statistic_ids), "statistic count mismatch")
require(set(bundle["finding_locations"]) <= set(finding_refs), "location references an absent finding")
for location in bundle["finding_locations"].values():
    require(set(location) == {"regions", "areas"}, "location contains private or unexpected fields")
    require(len(location["regions"]) == len(set(location["regions"])), "duplicate region link")
    require(len(location["areas"]) == len(set(location["areas"])), "duplicate Brodmann link")
    require(all(str(area_id) in areas for area_id in location["areas"]), "unknown Brodmann link")

weighted = bundle["weighted_analysis"]
require(weighted["n_signs"] == len(weighted["by_sign"]), "weighted-analysis count mismatch")
require(bool(weighted["method_explanation"]), "weighting method is missing")
for analysis in weighted["by_sign"]:
    require(analysis["contributions"], "weighted analysis has no contribution")
    require(all(contribution.get("weight", 0) > 0 for contribution in analysis["contributions"]), "invalid study weight")

synthesis = bundle["evidence_synthesis"]
release = synthesis["release"]
axes = synthesis["finding_axes"]
cards = synthesis["axis_summaries"]
families = synthesis["descriptive_families"]
card_ids = {row["synthesis_id"] for row in cards}
family_ids = {row["analysis_id"] for row in families}
require(release["finding_count"] == len(findings) == 4119, "synthesis finding count mismatch")
require(release["axis_count"] == len(axes) == 8238, "synthesis axis count mismatch")
require(release["synthesis_card_count"] == len(cards) == 766, "synthesis card count mismatch")
require(release["descriptive_family_count"] == len(families) == 1555, "descriptive-family count mismatch")
require(release["retained_artifact_count"] == 146, "retained-artifact count mismatch")
require(len(card_ids) == len(cards), "duplicate synthesis-card identity")
require(len(family_ids) == len(families), "duplicate descriptive-family identity")
require(len({(row["finding_ref"], row["axis"]) for row in axes}) == len(axes), "duplicate finding-axis identity")
require(all(row["finding_ref"] in set(finding_refs) for row in axes), "finding axis references an absent finding")
require(all(str(row["sign_id"]) in set(sign_ids) for row in cards), "synthesis card references an absent sign")
require(all(str(sign_id) in set(sign_ids) for row in families for sign_id in row["sign_ids"]), "descriptive family references an absent sign")
require(all(item_id in card_ids for item_ids in synthesis["cards_by_sign"].values() for item_id in item_ids), "sign references an absent synthesis card")
require(all(item_id in family_ids for item_ids in synthesis["families_by_sign"].values() for item_id in item_ids), "sign references an absent descriptive family")

serialized = json.dumps(bundle, sort_keys=True).lower()
for private_marker in (
    '"owner_comment"', '"owner_decision"', '"resolution_json"', '"context_json"',
    '"adjudication_event"', '"private_pdf_path"', '"local_source_path"',
    '"owner_question"', '"review_origin"', '"review_status"',
):
    require(private_marker not in serialized, f"private field leaked: {private_marker}")

print(json.dumps({
    "sources": len(sources),
    "findings": len(findings),
    "statistics": len(statistic_ids),
    "signs": len(sign_ids),
    "weighted_analyses": len(weighted["by_sign"]),
    "finding_axes": len(axes),
    "synthesis_cards": len(cards),
    "descriptive_families": len(families),
    "status": "PASS",
}, sort_keys=True))
