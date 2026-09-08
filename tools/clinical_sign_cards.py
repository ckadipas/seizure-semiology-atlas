"""Pure public 1.15 clinical sign-card projection."""

from __future__ import annotations
from collections import OrderedDict
import importlib.util
import json
from pathlib import Path
import re

try:
    from public_relationship_graph import PublicRelationshipGraph
except ModuleNotFoundError as error:
    if error.name != "public_relationship_graph":
        raise
    helper_path = Path(__file__).with_name("public_relationship_graph.py")
    helper_spec = importlib.util.spec_from_file_location(
        "semiology_public_relationship_graph", helper_path
    )
    if helper_spec is None or helper_spec.loader is None:
        raise RuntimeError("public relationship reader is unavailable") from error
    helper_module = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper_module)
    PublicRelationshipGraph = helper_module.PublicRelationshipGraph

_EMPTY = {"", "NONE", "NOT_REPORTED", "NOT_APPLICABLE", "NULL"}

def _unique(values): return list(OrderedDict.fromkeys(value for value in values if value))
def _text(value):
    value = str(value or "").strip()
    return "" if value.upper() in _EMPTY else value


def public_evidence_class(value):
    """Return the public I/II/III label for the canonical CLASS_* enum."""
    value = _text(value).upper()
    if value.startswith("CLASS_"):
        value = value.removeprefix("CLASS_")
    return value if value in {"I", "II", "III"} else ""


def public_reader_text(value):
    """Return public human text, never a path, payload, hash, or internal ID."""
    if isinstance(value, (dict, list, tuple, set)):
        return ""
    value = _text(value)
    if (
        "\\" in value or value.startswith(("/", "file:"))
        or re.search(
            r"\.(?:csv|db|docx?|html?|json|pdf|sqlite3?|tsv|txt|ya?ml)$",
            value,
            flags=re.IGNORECASE,
        )
        or (value[:1] in "[{" and value[-1:] in "]}")
        or re.search(r"\b[0-9a-f]{32,64}\b", value, flags=re.IGNORECASE)
        or re.search(
            r"\b(?:ANATOMY|ANAT-REL|ART|AXIS|ECTX|FINDING|OCCURRENCE|"
            r"PLACEMENT|PUBLIC_PLACEMENT|REPORT|SHA-?256|SOURCE|SRC|SGRP|"
            r"STAT(?:2|_INTAKE)?|WORK):[A-Za-z0-9:_-]+",
            value,
            flags=re.IGNORECASE,
        )
    ):
        return ""
    return value


def public_source_locator(value):
    """Render an exact locator through a public-safe structured allowlist."""
    raw = _text(value)
    if not raw:
        return ""
    if raw[:1] not in "[{":
        # A normalized source-field path is ownership metadata, not a reader
        # locator.  Preserve the canonical null/unknown state by omitting it.
        if re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+",
            raw,
        ):
            return ""
        safe = public_reader_text(raw)
        if not safe:
            raise ValueError("A source locator contains a private or internal value.")
        return safe
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("A structured source locator is not valid JSON.") from error
    entries = payload if isinstance(payload, list) else [payload]
    if not entries:
        raise ValueError("A structured source locator has no public human location.")
    allowed_fields = {"artifact_id", "excerpt", "object", "page", "position"}
    labels = []
    for entry in entries:
        if not isinstance(entry, dict) or not set(entry).issubset(allowed_fields):
            raise ValueError("A structured source locator has unsupported fields.")
        parts = []
        for key in ("object", "page", "position"):
            source_value = _text(entry.get(key))
            if not source_value:
                continue
            safe = public_reader_text(source_value)
            if not safe:
                raise ValueError("A structured source locator contains an internal value.")
            if key == "page" and not safe.casefold().startswith(("p.", "page ")):
                safe = f"p. {safe}"
            parts.append(safe)
        if not parts:
            raise ValueError("A structured source locator has no public human location.")
        labels.append(" · ".join(parts))
    return "; ".join(_unique(labels))


def compact_author_citation(relationship):
    """Return a compact structured first-author/year citation."""
    raw_authors = relationship.get("work_authors") or []
    if isinstance(raw_authors, dict):
        authors = [raw_authors]
    elif isinstance(raw_authors, str):
        authors = [part.strip() for part in raw_authors.split(";") if part.strip()]
    elif isinstance(raw_authors, list):
        authors = raw_authors
    else:
        authors = []

    family_names = []
    for author in authors:
        if isinstance(author, dict):
            family = public_reader_text(
                author.get("family_name") or author.get("display_name")
            )
        else:
            family = public_reader_text(author)
        if family:
            family_names.append(family)
    author_label = ""
    if family_names:
        author_label = family_names[0] + (" et al." if len(family_names) > 1 else "")
    year = public_reader_text(relationship.get("work_publication_year"))
    return (
        f"{author_label} ({year})" if author_label and year
        else author_label or year
    )


def cited_work_citation_texts(relationship):
    """Return exact, public-safe cited-work text without touching host identity."""
    return _unique(
        public_reader_text(
            citation.get("work_citation_text")
            or citation.get("citation_as_printed")
        )
        for citation in relationship.get("cited_work_occurrences") or []
        if isinstance(citation, dict)
    )


def source_identity_search_terms(relationship):
    """Index host and cited source identities independently of map eligibility."""
    terms = []
    for source in [relationship, *(relationship.get("cited_work_occurrences") or [])]:
        if not isinstance(source, dict):
            continue
        terms.extend(public_reader_text(source.get(key)) for key in (
            "work_title", "work_publication_year", "work_citation_text",
            "citation_as_printed",
        ))
        authors = source.get("work_authors") or []
        if isinstance(authors, (str, dict)):
            authors = [authors]
        for author in authors:
            if isinstance(author, dict):
                terms.extend(public_reader_text(author.get(key)) for key in (
                    "family_name", "given_name", "display_name",
                ))
            else:
                terms.append(public_reader_text(author))
    return _unique(terms)


def _compact_exact_citation(citation_text):
    """Compact only an unambiguous first-author/multi-author/year citation."""
    exact = public_reader_text(citation_text)
    if not exact:
        return ""
    candidate = re.sub(
        r"^\s*REF(?:ERENCE)?S?\s*(?:\[[^\]]+\]|[0-9,\s\-\u2013\u2014]+)\s*[:.]?\s*",
        "", exact, flags=re.IGNORECASE,
    )
    years = _unique(re.findall(r"\b(?:18|19|20)\d{2}\b", candidate))
    author = re.match(
        r"(?P<family>[^\W\d_][\w'\u2019.-]*)(?:\s+[A-Z][A-Za-z.-]*)?(?P<rest>.*)",
        candidate,
    )
    if not author or len(years) != 1:
        return exact
    before_year = author.group("rest").split(years[0], 1)[0]
    explicitly_multiple = bool(
        re.search(r"\bet\s+al\.?\b|\band\b", before_year, re.IGNORECASE)
        or re.match(
            r"\s*,\s*[^\W\d_][\w'\u2019.-]+(?:\s+[A-Z][A-Za-z.-]*)?(?:\s*,|\s|$)",
            before_year,
        )
    )
    if not explicitly_multiple:
        return exact
    return f"{author.group('family')} et al. ({years[0]})"


def compact_publication_label(relationship):
    """Return cited-work identity for background, otherwise host-work identity."""
    if relationship.get("evidence_partition") == "BACKGROUND_LITERATURE":
        cited_labels = []
        for citation in relationship.get("cited_work_occurrences") or []:
            if not isinstance(citation, dict):
                continue
            lead = compact_author_citation(citation)
            title = public_reader_text(citation.get("work_title"))
            exact = public_reader_text(
                citation.get("work_citation_text")
                or citation.get("citation_as_printed")
            )
            cited_labels.append(
                " · ".join(value for value in (lead, title) if value)
                or _compact_exact_citation(exact)
            )
        if labels := _unique(cited_labels):
            return "; ".join(labels)
    lead = compact_author_citation(relationship)
    title = public_reader_text(relationship.get("work_title"))
    return " · ".join(value for value in (lead, title) if value)

def _axis(graph, sign_id, axis):
    return {
        "targets": graph.axis_targets_for_sign(sign_id, axis),
        "modifiers": graph.context_notes_for_sign(sign_id, axis),
        "status": "",
        "summary": "",
    }

def _label(rows):
    for row in rows:
        if label := compact_publication_label(row):
            return label
    return ""

def _classes(sign_id, graph, schemes):
    rows = [
        graph.classifications[node_id]
        for node_id in graph.classification_node_ids_for_sign(sign_id, schemes)
        if node_id in graph.classifications
    ]
    rows.sort(key=lambda row: (
        str(row.get("scheme_id") or ""), row.get("ordinal") or 9999,
        _text(row.get("label")).casefold(), str(row.get("classification_node_id") or ""),
    ))
    return _unique(_text(row.get("label")) for row in rows)

def project_clinical_sign_cards(bundle, graph=None):
    """Return the exact source-backed clinical card DTOs for bundle 1.15."""
    if str(bundle.get("schema_version") or "") != "atlas-public-bundle-1.17.0":
        raise ValueError(
            "clinical sign cards require atlas-public-bundle-1.17.0"
        )
    graph = graph or PublicRelationshipGraph(bundle.get("scientific_relationship_graph"))
    classification_scheme_ids = {
        "ilae": graph.single_active_classification_scheme_id("ILAE"),
        "luders": graph.single_active_classification_scheme_id("LUDERS"),
    }
    raw_signs = {str(row.get("id") or ""): row for row in bundle.get("signs") or []}
    statistic_signs = {
        statistic_id: set(graph.sign_ids_for_statistics([statistic_id]))
        for statistic_id in graph.statistics
    }
    statistic_referenced_sign_ids = {
        sign_id for sign_ids in statistic_signs.values() for sign_id in sign_ids
    }
    cards = []
    for sign_id, sign_node in graph.signs.items():
        sign = raw_signs.get(sign_id) or {"id": sign_id, "sign": sign_node.get("label")}
        relationships = list(graph.relationships_by_sign.get(sign_id, ()))
        groups = OrderedDict()
        for row in relationships:
            work_id = str(row.get("work_id") or "")
            report_id = str(row.get("report_id") or "")
            if not work_id or not report_id:
                raise ValueError("A public sign relationship lacks work/report identity.")
            group = groups.setdefault(work_id, {
                "work_id": work_id, "relationships": [],
                "reports": OrderedDict(),
            })
            group["relationships"].append(row)
            report = group["reports"].setdefault(report_id, {
                "report_id": report_id, "relationships": [],
            })
            report["relationships"].append(row)
        summary = []
        source_groups = []
        for work_id,group in groups.items():
            label = _label(group["relationships"])
            classes_by_axis = {
                axis: sorted({
                    evidence_class
                    for row in group["relationships"]
                    if str(row.get("axis") or "") == axis
                    and (
                        evidence_class := public_evidence_class(
                            row.get("report_evidence_class")
                        )
                    )
                })
                for axis in ("LATERALIZATION", "LOCALIZATION")
            }
            contribution_classes = {
                value for values in classes_by_axis.values() for value in values
            }
            evidence_class = next(iter(contribution_classes)) if len(contribution_classes) == 1 else ""
            statistic_ids = _unique(
                statistic_id
                for row in group["relationships"]
                for statistic_id in row.get("statistic_ids") or []
                if sign_id in statistic_signs.get(statistic_id, set())
            )
            source_groups.append({
                **group,
                "source_group_id": work_id,
                "label": label,
                "evidence_class": evidence_class,
                "evidence_classes_by_axis": classes_by_axis,
                "statistic_ids": statistic_ids,
                "reports": list(group["reports"].values()),
            })
            if label:
                summary.append({
                    "label": label,
                    "claims": _unique(
                        _text(row.get("source_native_relationship_term"))
                        for row in group["relationships"]
                    ),
                })
        source_groups.sort(key=lambda group: (
            {"I": 0, "II": 1, "III": 2}.get(group["evidence_class"], 3),
            str(group["label"]).casefold(), group["source_group_id"],
        ))
        axes={"localization":_axis(graph,sign_id,"LOCALIZATION"),"lateralization":_axis(graph,sign_id,"LATERALIZATION")}
        regions = _unique(region for context in graph.browse_contexts_for_sign(sign_id)
                          for region in context["regions"])
        subsections_by_region = OrderedDict()
        for target in axes["localization"]["targets"]:
            for region_id in target.get("display_region_ids") or []:
                region = graph.display_region_labels.get(str(region_id))
                if region:
                    subsections_by_region.setdefault(region, []).append(
                        str(target.get("label") or "")
                    )
        subsections_by_region = {
            region: _unique(labels) for region, labels in subsections_by_region.items()
        }
        classified = {
            name: _classes(sign_id, graph, {scheme_id})
            for name, scheme_id in classification_scheme_ids.items()
        }
        occurrence_classification_labels = _unique(
            _text((graph.classifications.get(
                str(row.get("dictionary_item_id") or "")
            ) or {}).get("label"))
            for row in relationships
            if str(row.get("relationship_kind") or "")
            == "OCCURRENCE_CLASSIFICATION"
        )
        phase_ids = graph.phase_ids_for_sign(sign_id)
        phase = {
            "ids": phase_ids,
            "categories": graph.phase_labels(phase_ids),
            "source_wording": "; ".join(graph.phase_source_values_for_sign(sign_id)),
        }
        source_native_variants = graph.source_native_terms_for_sign(sign_id)
        base_search=" ".join(str(value or "") for value in (sign.get("sign"),*source_native_variants,phase["source_wording"],*phase["categories"],*classified["ilae"],*classified["luders"],*occurrence_classification_labels)).casefold().replace('"',"")
        search_values = (
            base_search, *regions,
            *(group["label"] for group in source_groups),
            *(
                value
                for group in source_groups
                for row in group["relationships"]
                for value in (
                    *source_identity_search_terms(row),
                    row.get("source_native_sign_term"),
                    row.get("source_native_relationship_term"),
                    public_source_locator(row.get("source_locator")),
                    row.get("source_excerpt"),
                )
            ),
        )
        search=" ".join(
            value.strip() for value in search_values
            if isinstance(value, str) and value.strip()
        ).casefold().replace('"',"")
        has_retained_evidence = bool(
            relationships
            or sign_id in statistic_referenced_sign_ids
        )
        cards.append({"sign_id":sign_id,"sign":_text(sign.get("sign") or sign_node.get("label")),"raw_sign":sign,"source_native_variants":source_native_variants,"browse_regions":regions,"subsections_by_region":subsections_by_region,"subs_by_region":{},"subsection":"","axes":axes,"classifications":classified,"phase":phase,"source_groups":source_groups,"summary_manuscripts":summary,"relationship_ids":[str(row["relationship_id"]) for row in relationships],"base_search_text":base_search,"search_text":search,"has_retained_evidence":has_retained_evidence})
    by_sign_id={card["sign_id"]:card for card in cards}
    return {
        "cards": cards,
        "by_sign_id": by_sign_id,
        "classification_scheme_ids": classification_scheme_ids,
        "browse_sign_ids": {
            card["sign_id"] for card in cards if card["has_retained_evidence"]
        },
    }
