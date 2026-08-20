#!/usr/bin/env python3
"""Validate the canonical V30 ledger and build reference-only website indexes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
ENRICHMENT = ROOT / "enrichment"
LEDGER_PATH = ENRICHMENT / "corpus_findings.json"


def canonical_digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def write(name: str, value: object) -> None:
    (ENRICHMENT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build() -> dict:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    registry = json.loads((ROOT / "data" / "semiology_data.json").read_text(encoding="utf-8"))
    registry_ids = {row["id"] for row in registry}
    rows = [row for source in ledger["sources"] for row in source["findings"]]
    refs = [row["source_finding_ref"] for row in rows]
    statistics = [row["source_statistic_id"] for row in rows if row["source_statistic_id"]]
    accounting = ledger["integration_accounting"]
    errors = []

    if ledger["registry_value_digest"] != canonical_digest(registry):
        errors.append("registry digest mismatch")
    if len(refs) != len(set(refs)):
        errors.append("duplicate source_finding_ref")
    if len(statistics) != len(set(statistics)):
        errors.append("duplicate source_statistic_id")
    if accounting["public_ledger_findings"] != len(rows):
        errors.append("public finding accounting mismatch")
    if accounting["source_reported_statistics"] != len(statistics):
        errors.append("source statistic accounting mismatch")

    by_sign: dict[str, dict[str, list[str]]] = {}
    sources = []
    for source in ledger["sources"]:
        if source["source_version_role"] == "ALTERNATE_REVIEWED_VERSION" and any(
            row["independent_evidence"] for row in source["findings"]
        ):
            errors.append(f"alternate version marked independent: {source['source_sha256']}")
        sources.append({
            "source_sha256": source["source_sha256"],
            "source_file": source["source_file"],
            "work_id": source["work_id"],
            "source_version_role": source["source_version_role"],
            "page_count": source["page_count"],
            "finding_count": len(source["findings"]),
            "statistic_count": sum(row["source_statistic_id"] is not None for row in source["findings"]),
        })
        for row in source["findings"]:
            ref = row["source_finding_ref"]
            expected_stat = None if row["measure"] == "NOT_QUANTITATIVE" else f"STAT:{ref}"
            if row["source_statistic_id"] != expected_stat:
                errors.append(f"statistic identity mismatch: {ref}")
            exact, related = row["exact_sign_ids"], row["related_sign_ids"]
            if set(exact + related) - registry_ids:
                errors.append(f"unknown sign_id: {ref}")
            if set(exact) & set(related):
                errors.append(f"overlapping exact/related mapping: {ref}")
            relation_ok = (
                (row["mapping_relation"] == "EXACT" and bool(exact) and not related)
                or (row["mapping_relation"] == "RELATED" and bool(related) and not exact)
                or (row["mapping_relation"] == "PROSPECTIVE" and not exact and not related and row["prospective_concept_id"])
                or (row["mapping_relation"] == "NOT_APPLICABLE" and not exact and not related)
            )
            if not relation_ok:
                errors.append(f"mapping cardinality mismatch: {ref}")
            if row["evidence_role"] not in {"PRIMARY_RESULT", "CASE_OBSERVATION"} and row["independent_evidence"]:
                errors.append(f"non-primary role marked independent: {ref}")
            for sign_id in exact:
                by_sign.setdefault(str(sign_id), {"exact": [], "related": []})["exact"].append(ref)
            for sign_id in related:
                by_sign.setdefault(str(sign_id), {"exact": [], "related": []})["related"].append(ref)

    if errors:
        raise ValueError("; ".join(errors[:20]))

    index = {
        "_doc": "Generated reference-only index. Scientific text and values remain solely in corpus_findings.json.",
        "schema_version": "v30-public-evidence-index-1.0.0",
        "source_ledger": "corpus_findings.json",
        "review_release": ledger["review_release"],
        "registry_value_digest": ledger["registry_value_digest"],
        "accounting": accounting,
        "by_sign_id": dict(sorted(by_sign.items(), key=lambda item: int(item[0]))),
        "sources": sources,
    }
    write("evidence_index.json", index)
    marker = {
        "_doc": "Legacy generated scientific-value path retired by V30 integration.",
        "status": "DEPRECATED",
        "canonical_ledger": "corpus_findings.json",
        "generated_index": "evidence_index.json",
    }
    write("enrichment.json", marker)
    write("meta_analysis.json", marker)
    write("review_flags.json", {
        "_doc": "Deterministic V30 ledger integrity receipt; no scientific values are copied here.",
        "schema_version": "v30-public-integrity-receipt-1.0.0",
        "status": "CLEAR",
        "source_ledger": "corpus_findings.json",
        "accounting": accounting,
        "checks": ["unique finding identities", "unique statistic identities", "registry-bound mappings", "non-independent evidence roles", "ledger accounting"],
    })
    print(f"V30 index: {len(sources)} sources, {len(rows)} findings, {len(statistics)} statistics, {len(by_sign)} linked sign IDs")
    return index


if __name__ == "__main__":
    try:
        build()
    except (KeyError, TypeError, ValueError) as exc:
        print(f"V30 evidence integrity failure: {exc}", file=sys.stderr)
        raise SystemExit(1)
