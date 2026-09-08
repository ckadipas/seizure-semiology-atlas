"""Pure public 1.6 clinical sign-card projection."""

from __future__ import annotations
from collections import OrderedDict
import re

_EMPTY = {"", "NONE", "NOT_REPORTED", "NOT_APPLICABLE", "NULL"}
_REGION = {"REG:TEMPORAL":"Temporal", "REG:FRONTAL":"Frontal", "REG:PARIETAL":"Parietal", "REG:OCCIPITAL":"Occipital", "REG:INSULAR":"Insular", "REG:LIMBIC":"Limbic", "REG:DEEP_SUBCORTICAL":"Deep/Subcortical"}
_PHASE = {"AURA":"Aura", "ICTAL":"Ictal", "POST_ICTAL":"Post ictal", "PERIICTAL":"Periictal", "STIMULATION_INDUCED":"Stimulation induced", "OTHER":"Other"}
_LUDERS = {"LUDERS_SSC_1998", "LUDERS_5D_2005"}
_MODIFIER = {("PROPAGATION","PROPAGATION"):"Propagation noted in source context.", ("COHORT_CONTEXT","COHORT_CONTEXT"):"Cohort context noted in source.", ("COHORT","COHORT"):"Cohort context noted in source."}
_GENERIC_FILENAME_TOKENS = {"a", "an", "the", "study", "review", "article", "paper", "chapter", "book", "handbook", "guideline", "consensus", "semiology", "epilepsy"}

def _unique(values): return list(OrderedDict.fromkeys(value for value in values if value))
def _text(value):
    value = str(value or "").strip()
    return "" if value.upper() in _EMPTY else value

def normalize_phase(sign):
    wording = _text(sign.get("phase")); structured = sign.get("normalized_phase_category") or sign.get("phase_category")
    values = structured if isinstance(structured, list) else [structured]
    categories = [value for value in (_PHASE.get(str(value or "").upper()) for value in values) if value]
    if not categories:
        raw = wording.casefold()
        categories = (["Stimulation induced"] if any(value in raw for value in ("stimulation", "stimulat", "electrical", "electrically", "evoked", "mapping")) else ["Post ictal"] if any(value in raw for value in ("post-ictal", "post ictal", "postictal")) else ["Periictal"] if any(value in raw for value in ("peri-ictal", "peri ictal", "periictal")) else ["Aura"] if "aura" in raw else ["Ictal"] if "ictal" in raw or "seizure onset" in raw else ["Other"])
    return {"categories": _unique(categories), "source_wording": wording}

def _targets(summary):
    return [{key: target.get(key) for key in ("key","label","raw","origins","finding_refs","target_level","region_id","parent_region_id","area_id","brodmann_label")} for target in ((summary.get("target_contract") or {}).get("reported_targets") or []) if _text(target.get("key")) and _text(target.get("label")) and _text(target.get("key")).casefold() != "reg:multiregional_propagation"]

def _axis(summaries, axis):
    choices = [row for row in summaries if str(row.get("axis") or "").upper() == axis]
    if not choices: return {"targets": [], "modifiers": [], "status": "", "summary": ""}
    row = max(choices, key=lambda row: (bool(_targets(row)), len(row.get("row_finding_refs") or []), len(row.get("row_statistic_ids") or []), len(row.get("row_work_ids") or []), str(row.get("synthesis_id") or "")))
    targets = _targets(row)
    modifiers = _unique(_MODIFIER.get((str(item.get("key") or ""),str(item.get("modifier_type") or ""))) for item in ((row.get("target_contract") or {}).get("modifiers") or []))
    if any(
        origin in {"COHORT_CONTEXT_ASSERTION", "OWNER_APPROVED_DOCUMENT_COHORT_AXIS"}
        for target in targets for origin in target.get("origins") or []
    ):
        modifiers = _unique([*modifiers, "Cohort context noted in source."])
    return {"targets":targets, "modifiers":modifiers, "status":_text(row.get("pattern_status")), "summary":_text(row.get("plain_summary"))}

def _major_region(target, parents):
    current = str(target.get("region_id") or target.get("key") or target.get("parent_region_id") or "")
    seen = set()
    while current and current not in seen:
        seen.add(current)
        if current in _REGION: return _REGION[current]
        current = parents.get(current, "")
    return ""

def _filename_short_label(label):
    label = _text(label)
    basename = re.split(r"[\\/]", label)[-1]
    if not re.search(r"\.[A-Za-z0-9]{2,5}$", basename): return ""
    token = re.match(r"^([A-Za-z]{3,})(?=[^A-Za-z]|$)", basename)
    years = re.findall(r"(?<!\d)((?:18|19|20)\d{2})(?!\d)", basename)
    if not token or token.group(1).casefold() in _GENERIC_FILENAME_TOKENS or len(years) != 1: return ""
    return f"{token.group(1)[:1].upper()}{token.group(1)[1:]} · {years[0]}"

def _label(source, rows, profiles):
    cites = _unique(_text(row.get("citation")) for row in rows)
    if len(cites) == 1: return cites[0]
    label = _text((profiles.get(str(source.get("work_id") or "")) or {}).get("display_name")) or _text(source.get("source_file"))
    return _filename_short_label(label) or label

def _classes(sign_id, nodes, mappings, schemes):
    def ancestor(candidate, node_id):
        parent = (nodes.get(node_id) or {}).get("parent_node_id")
        while parent:
            if parent == candidate: return True
            parent = (nodes.get(parent) or {}).get("parent_node_id")
        return False
    values_by_scheme = OrderedDict()
    for row in mappings:
        node_id = str(row.get("node_id") or ""); node = nodes.get(node_id) or {}
        scheme = str(node.get("scheme_id") or "")
        if str(row.get("sign_id") or "") == sign_id and scheme in schemes:
            values_by_scheme.setdefault(scheme, set()).add(node_id)
    scheme_order = ("LUDERS_SSC_1998", "LUDERS_5D_2005") if set(schemes) == _LUDERS else sorted(schemes)
    labels = []
    for scheme in scheme_order:
        values = values_by_scheme.get(scheme, set())
        terms = {node_id for node_id in values if (nodes.get(node_id) or {}).get("node_kind") == "TERM"}
        values = terms or values
        labels.extend(_text((nodes.get(node_id) or {}).get("label")) for node_id in sorted((node_id for node_id in values if not any(node_id != other and ancestor(node_id, other) for other in values)), key=lambda node_id: ((nodes.get(node_id) or {}).get("ordinal") or 9999, _text((nodes.get(node_id) or {}).get("label")).casefold())))
    return _unique(label for label in labels if label.casefold() not in {"seizure", "seizures"})

def project_clinical_sign_cards(bundle):
    """Return the exact source-backed clinical card DTOs for bundle 1.6."""
    if str(bundle.get("schema_version") or "") != "atlas-public-bundle-1.6.0": raise ValueError("clinical sign cards require atlas-public-bundle-1.6.0")
    findings = {}
    for source in (bundle.get("corpus") or {}).get("sources") or []:
        for row in source.get("findings") or []:
            if reference := str(row.get("source_finding_ref") or ""): findings[reference] = (source,row)
    by_sign = {}; region_parents = {}
    for row in (bundle.get("evidence_synthesis") or {}).get("axis_summaries") or []:
        by_sign.setdefault(str(row.get("sign_id") or ""),[]).append(row)
        region_parents.update({str(target.get("region_id")): str(target.get("parent_region_id")) for target in _targets(row) if _text(target.get("region_id")) and _text(target.get("parent_region_id"))})
    profiles = {str(row.get("work_id") or ""):row for row in (bundle.get("evidence_authority") or {}).get("profiles") or []}
    classification = bundle.get("classifications") or {}; nodes = {str(row.get("node_id") or ""):row for row in classification.get("nodes") or []}; mappings = classification.get("sign_mappings") or []
    cards = []
    for sign in bundle.get("signs") or []:
        sign_id = str(sign.get("id") or ""); summaries = by_sign.get(sign_id,[]); refs = _unique(str(ref) for summary in summaries for ref in summary.get("row_finding_refs") or [] if str(ref) in findings)
        if not refs: continue
        groups = OrderedDict()
        for reference in refs:
            source,row = findings[reference]; work_id = str(source.get("work_id") or source.get("source_sha256") or source.get("source_file") or "")
            groups.setdefault(work_id,{"work_id":work_id,"source":source,"findings":[]})["findings"].append(row)
        source_groups_by_class = OrderedDict((value, []) for value in ("I", "II", "III", ""))
        summary = []
        for work_id,group in groups.items():
            label = _label(group["source"], group["findings"], profiles)
            finding_by_ref = {str(row.get("source_finding_ref") or ""): row for row in group["findings"]}
            refs_by_class = OrderedDict((value, []) for value in ("I", "II", "III", ""))
            for contribution in (
                contribution for summary_row in summaries
                for contribution in summary_row.get("contributions") or []
                if str(contribution.get("work_id") or "") == work_id
            ):
                evidence_class = str(contribution.get("evidence_class") or "")
                evidence_class = evidence_class if evidence_class in {"I", "II", "III"} else ""
                refs_by_class[evidence_class].extend(
                    str(reference) for reference in contribution.get("row_finding_refs") or []
                    if str(reference) in finding_by_ref
                )
            classified_refs = set()
            for evidence_class in ("I", "II", "III"):
                refs_by_class[evidence_class] = _unique(refs_by_class[evidence_class])
                classified_refs.update(refs_by_class[evidence_class])
            refs_by_class[""] = _unique([
                *refs_by_class[""],
                *(reference for reference in finding_by_ref if reference not in classified_refs),
            ])
            for evidence_class, group_refs in refs_by_class.items():
                rows = [finding_by_ref[reference] for reference in group_refs]
                if rows:
                    source_groups_by_class[evidence_class].append({
                        **group, "source_group_id": f"{work_id}:{evidence_class or 'UNCLASSIFIED'}",
                        "findings": rows, "label": label, "evidence_class": evidence_class,
                        "finding_refs": group_refs,
                        "statistic_ids": _unique(str(item.get("statistic_id") or "") for row in rows for item in row.get("statistics") or []),
                    })
            if label:
                summary.append({"label": label, "claims": _unique(_text(row.get("claim")) for row in group["findings"])})
        source_groups = [group for evidence_class in ("I", "II", "III", "") for group in source_groups_by_class[evidence_class]]
        axes={"localization":_axis(summaries,"LOCALIZATION"),"lateralization":_axis(summaries,"LATERALIZATION")}
        regions=_unique(_major_region(target, region_parents) for target in axes["localization"]["targets"]) or ["No localization stated"]
        classified={"ilae":_classes(sign_id,nodes,mappings,{"ILAE_SEIZURE_2025"}),"luders":_classes(sign_id,nodes,mappings,_LUDERS)}; phase=normalize_phase(sign)
        search=" ".join(str(value or "") for value in (sign.get("sign"),sign.get("phase"),sign.get("region"),sign.get("sub"),sign.get("loc"),*regions,*classified["ilae"],*classified["luders"],*(group["label"] for group in source_groups),*(row.get("source_term") for group in source_groups for row in group["findings"]),*(row.get("claim") for group in source_groups for row in group["findings"]))).casefold().replace('"',"")
        cards.append({"sign_id":sign_id,"sign":_text(sign.get("sign")),"raw_sign":sign,"browse_regions":regions,"subsections_by_region":sign.get("subsections_by_region") or {},"subs_by_region":sign.get("subs_by_region") or {},"subsection":_text(sign.get("sub")),"axes":axes,"classifications":classified,"phase":phase,"source_groups":source_groups,"summary_manuscripts":summary,"finding_refs":refs,"search_text":search})
    by_sign_id={card["sign_id"]:card for card in cards}
    return {"cards":cards,"by_sign_id":by_sign_id,"browse_sign_ids":set(by_sign_id)}
