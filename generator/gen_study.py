import hashlib, json, math, re, os, shutil, sys
def _find_root(start):
    d = os.path.dirname(os.path.abspath(start))
    while True:
        if os.path.exists(os.path.join(d, ".atlas-root")): return d
        p = os.path.dirname(d)
        if p == d: return os.path.dirname(os.path.abspath(start))
        d = p
ROOT = _find_root(__file__)
DOCS = os.path.join(ROOT, "docs"); os.makedirs(DOCS, exist_ok=True)
from collections import OrderedDict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain_atlas as BA

with open(os.path.join(ROOT,"data","atlas_bundle.json"), encoding="utf-8") as f:
    ATLAS = json.load(f)
data = ATLAS["signs"]
CORPUS = ATLAS["corpus"]
CLASSIFICATIONS = ATLAS.get("classifications") or {"nodes": [], "sign_mappings": []}
ACCOUNTING = CORPUS["integration_accounting"]
EVID = {}; NEW_SIGNS = []; LATERAL = []
ROLE_LABEL = {
    "PRIMARY_RESULT": "Original study result",
    "REVIEW_SYNTHESIS": "Review summary",
    "CITED_STUDY_RESTATEMENT": "Result summarized from another study",
    "EDUCATIONAL_STATEMENT": "Teaching reference",
    "GUIDELINE_RECOMMENDATION": "Guideline",
    "CASE_OBSERVATION": "Case report",
}

EVIDENCE_INDEX = {}
META = ATLAS.get("weighted_analysis") or None
EVIDENCE_SYNTHESIS = ATLAS.get("evidence_synthesis") or {}
SYNTHESIS_CARDS = EVIDENCE_SYNTHESIS.get("axis_summaries") or []
FINDING_AXES = EVIDENCE_SYNTHESIS.get("finding_axes") or []
FINDING_AXIS_BY_REF = {
    (str(row.get("finding_ref") or ""), str(row.get("axis") or "").upper()): row
    for row in FINDING_AXES
}
SYNTHESIS_CARD_BY_ID = {row["synthesis_id"]: row for row in SYNTHESIS_CARDS}
SYNTHESIS_CARDS_BY_SIGN = {
    str(sign_id): [SYNTHESIS_CARD_BY_ID[item_id] for item_id in item_ids]
    for sign_id, item_ids in (EVIDENCE_SYNTHESIS.get("cards_by_sign") or {}).items()
}
DESCRIPTIVE_FAMILIES = EVIDENCE_SYNTHESIS.get("descriptive_families") or []
DESCRIPTIVE_FAMILY_BY_ID = {row["analysis_id"]: row for row in DESCRIPTIVE_FAMILIES}
DESCRIPTIVE_FAMILIES_BY_SIGN = {
    str(sign_id): [DESCRIPTIVE_FAMILY_BY_ID[item_id] for item_id in item_ids]
    for sign_id, item_ids in (EVIDENCE_SYNTHESIS.get("families_by_sign") or {}).items()
}
FLAGS = None

PAPERS = []
ledger_by_ref = {}
ledger_evidence_by_cardid = {}
STATISTIC_CONTEXT_BY_ID = {}
for _source in CORPUS["sources"]:
    _nstat = sum(len(_row.get("statistics", [])) for _row in _source["findings"])
    PAPERS.append((
        _source["source_file"],
        f'{_source["page_count"]} pages',
        _source["source_report_summary"],
        f'{len(_source["findings"])} findings; {_nstat} source-reported statistics; '
        + _source["source_version_role"].replace("_", " ").lower(),
    ))
    for _row in _source["findings"]:
        _entry = {"source": _source, "finding": _row}
        ledger_by_ref[_row["source_finding_ref"]] = _entry
        for _statistic in _row.get("statistics", []):
            _statistic_id = str(_statistic.get("statistic_id") or "")
            if _statistic_id:
                STATISTIC_CONTEXT_BY_ID[_statistic_id] = {
                    "source": _source, "finding": _row, "statistic": _statistic,
                }
        for _cid in _row["exact_sign_ids"]:
            ledger_evidence_by_cardid.setdefault(_cid, []).append((_entry, "EXACT"))
        for _cid in _row["related_sign_ids"]:
            ledger_evidence_by_cardid.setdefault(_cid, []).append((_entry, "RELATED"))

# A reported number can support more than one descriptive result group, but it
# must have one visible home in the library. Preserve every relationship here,
# then assign the number to the first canonical family in release order. Any
# additional memberships remain visible as cross-links on that same number.
_FAMILY_BY_STRING_ID = {
    str(_family["analysis_id"]): _family for _family in DESCRIPTIVE_FAMILIES
}
STATISTIC_FAMILY_IDS = {}
for _family in DESCRIPTIVE_FAMILIES:
    _family_id = str(_family["analysis_id"])
    _family_statistic_ids = list(_family.get("statistic_ids") or [])
    _family_statistic_ids.extend(
        _item.get("statistic_id") for _item in (_family.get("exact_estimates") or [])
    )
    for _statistic_id in _family_statistic_ids:
        _statistic_id = str(_statistic_id or "")
        if _statistic_id:
            _memberships = STATISTIC_FAMILY_IDS.setdefault(_statistic_id, [])
            if _family_id not in _memberships:
                _memberships.append(_family_id)

FAMILY_PRIMARY_STATISTIC_IDS = {
    str(_family["analysis_id"]): [] for _family in DESCRIPTIVE_FAMILIES
}
FAMILY_LINKED_STATISTIC_IDS = {
    str(_family["analysis_id"]): [] for _family in DESCRIPTIVE_FAMILIES
}
PRIMARY_FAMILY_BY_STATISTIC_ID = {}
UNASSIGNED_STATISTIC_IDS = []
for _statistic_id in STATISTIC_CONTEXT_BY_ID:
    _family_ids = [
        _family_id for _family_id in STATISTIC_FAMILY_IDS.get(_statistic_id, [])
        if _family_id in _FAMILY_BY_STRING_ID
    ]
    for _family_id in _family_ids:
        FAMILY_LINKED_STATISTIC_IDS[_family_id].append(_statistic_id)
    if _family_ids:
        _primary_family_id = _family_ids[0]
        PRIMARY_FAMILY_BY_STATISTIC_ID[_statistic_id] = _primary_family_id
        FAMILY_PRIMARY_STATISTIC_IDS[_primary_family_id].append(_statistic_id)
    else:
        UNASSIGNED_STATISTIC_IDS.append(_statistic_id)

# The completed axis audit identified source findings that supported a synthesis
# card but were absent from its visible source history. Link those existing
# findings to the public sign without changing their source-native mappings.
for _card in SYNTHESIS_CARDS:
    _raw_sid = str(_card.get("sign_id") or "")
    _sid = int(_raw_sid) if _raw_sid.isdigit() else _raw_sid
    _linked = ledger_evidence_by_cardid.setdefault(_sid, [])
    _seen_refs = {entry["finding"]["source_finding_ref"] for entry, _ in _linked}
    for _finding_ref in _card.get("audit_cited_finding_refs") or []:
        if _finding_ref in ledger_by_ref and _finding_ref not in _seen_refs:
            _linked.append((ledger_by_ref[_finding_ref], "EXACT"))
            _seen_refs.add(_finding_ref)

# assign ids to new signs and append
_nextid = max(int(x["id"]) for x in data if str(x["id"]).isdigit()) + 1
for ns in NEW_SIGNS:
    ns.setdefault("id", _nextid); _nextid += 1
    data.append(ns)

# attach evidence to each sign by matching its name (lowercased) against evidence keys
for d in data:
    name = d["sign"].lower()
    ev = list(d.get("_ev", []))
    seen = {(e["p"], e["f"]) for e in ev}
    for key, findings in EVID.items():
        if key in name:
            for fnd in findings:
                if (fnd["p"], fnd["f"]) not in seen:
                    ev.append(fnd); seen.add((fnd["p"], fnd["f"]))
    d["_ev"] = ev

latcolor = {"contra":"#c0392b","ipsi":"#2471a3","dominant":"#8e44ad","nondominant":"#1a7a4a","right":"#d35400","left":"#2471a3","bilateral":"#5b6472","nonlat":"#6b7280","variable":"#95691a","notreported":"#6b7280"}
latbg    = {"contra":"#fdf2f2","ipsi":"#eaf4fb","dominant":"#f5f0fb","nondominant":"#eafaf1","right":"#fef5ee","left":"#eef5fb","bilateral":"#f3f4f6","nonlat":"#f3f4f6","variable":"#fdf8ee","notreported":"#f3f4f6"}
latlabel = {"contra":"CONTRA","ipsi":"IPSI","dominant":"DOM","nondominant":"NON-DOM","right":"RIGHT","left":"LEFT","bilateral":"BILATERAL","nonlat":"NON-LAT","variable":"VARIABLE","notreported":"NOT STATED"}
evidcolor= {"I":"#1a7a4a","II":"#c47a00","III":"#c0392b","SRC":"#0e9db0"}

region_order = ["Temporal","Frontal","Parietal","Occipital","Insular","Limbic","Deep/Subcortical","Multiregional/Propagation","No localization stated"]
region_short = {"Temporal":"Temporal","Frontal":"Frontal","Parietal":"Parietal","Occipital":"Occipital","Insular":"Insular","Limbic":"Limbic","Deep/Subcortical":"Deep","Multiregional/Propagation":"Multiregional","No localization stated":"Unlocalized"}
region_colors= {"Temporal":"#1a3a6b","Frontal":"#2d4a1e","Parietal":"#4a1e3d","Occipital":"#1e3d4a","Insular":"#4a3a1e","Limbic":"#51375c","Deep/Subcortical":"#3d2a0a","Multiregional/Propagation":"#1e1e4a","No localization stated":"#5f6878"}

def esc(s):
    text = "" if s is None else str(s)
    for old, new in (
        ("NOT_APPLICABLE", "Not applicable"),
        ("NOT_REPORTED", "Not reported"),
        ("NOT_QUANTITATIVE", "Not a numerical result"),
        ("NONE_REQUIRES_VISION", "text-only"),
        ("Source-native", "The source's own"),
        ("source-native", "the source's own"),
        ("V30 ", ""),
        ("V30", ""),
    ):
        text = text.replace(old, new)
    return text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def cited_source_line(row):
    """Show an actual secondary citation; never present NONE as missing evidence."""
    citation = str(row.get("citation") or "").strip()
    if citation.upper() in {"", "NONE", "NOT_REPORTED", "NOT_APPLICABLE"}:
        return ""
    return f'<div><strong>Cited source:</strong> {esc(citation)}</div>'

def finding_statistics(row):
    return row.get("statistics", [])

def statistic_value(statistic):
    return statistic.get("value_text") or statistic.get("measure") or "Reported statistical result"

def statistic_search_text(row):
    fields = []
    for statistic in finding_statistics(row):
        fields.extend(statistic.get(key) for key in (
            "metric_type", "value_text", "measure", "numerator", "denominator", "analysis_unit",
            "comparator", "uncertainty", "population", "subgroup", "timepoint", "endpoint", "phase",
            "anatomy_laterality_context", "citation", "source_locator", "source_excerpt",
        ))
    return " ".join(str(value or "") for value in fields)

_EMPTY_STAT_DETAIL = {"", "none", "null", "not_applicable", "not reported", "not_reported", "{}", "[]"}
_STAT_DETAIL_LABEL = {
    "confidence_interval": "Confidence interval", "p_value": "P value", "p_values": "P values",
    "standard_deviation": "Standard deviation", "standard_error": "Standard error",
    "test_statistic": "Test statistic", "heterogeneity_test": "Heterogeneity test",
    "multiplicity_adjustment": "Multiple-comparison adjustment", "related_occurrence": "Related value",
    "source_significance_convention": "Significance rule used by the paper",
}

def _clean_stat_detail(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value.lower() in _EMPTY_STAT_DETAIL:
            return None
        if value[:1] in "[{":
            try:
                return _clean_stat_detail(json.loads(value))
            except json.JSONDecodeError:
                pass
        return value
    if isinstance(value, dict):
        cleaned = {key: item for key, raw in value.items() if (item := _clean_stat_detail(raw)) is not None}
        return cleaned or None
    if isinstance(value, list):
        cleaned = [item for raw in value if (item := _clean_stat_detail(raw)) is not None]
        return cleaned or None
    return value

def _format_stat_detail(value):
    if isinstance(value, dict):
        return "; ".join(
            f'{_STAT_DETAIL_LABEL.get(key, key.replace("_", " ").capitalize())}: {_format_stat_detail(item)}'
            for key, item in value.items()
        )
    if isinstance(value, list):
        return ", ".join(_format_stat_detail(item) for item in value)
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)

def statistic_detail_text(statistic):
    raw = statistic["uncertainty_json"] if "uncertainty_json" in statistic else statistic.get("uncertainty")
    cleaned = _clean_stat_detail(raw)
    return _format_stat_detail(cleaned) if cleaned is not None else ""

def statistic_block(row):
    statistics = finding_statistics(row)
    if not statistics:
        return ""
    items = []
    for statistic in statistics:
        metric = str(statistic.get("metric_type") or "reported result").replace("_", " ").lower()
        context = []
        for label, key in (
            ("Subgroup", "subgroup"), ("Time", "timepoint"), ("Outcome", "endpoint"),
            ("What was counted", "analysis_unit"), ("Compared with", "comparator"),
        ):
            value = statistic.get(key)
            if value and str(value).upper() not in {"NONE", "NOT_APPLICABLE", "NOT_REPORTED"}:
                context.append(f'<span><strong>{label}:</strong> {esc(value)}</span>')
        numerator, denominator = statistic.get("numerator"), statistic.get("denominator")
        has_counts = all(
            value is not None and str(value).strip().upper() not in {
                "", "NONE", "NOT_APPLICABLE", "NOT_REPORTED",
            }
            for value in (numerator, denominator)
        )
        if has_counts:
            context.append(f'<span><strong>Counts:</strong> {esc(numerator)} / {esc(denominator)}</span>')
        detail = statistic_detail_text(statistic)
        if detail:
            context.append(f'<span><strong>Statistical detail:</strong> {esc(detail)}</span>')
        items.append(
            f'<li><strong>{esc(statistic_value(statistic))}</strong> '
            f'<span class="ev-meta">{esc(metric)}</span>'
            + (f'<div class="ev-stat-context">{"".join(context)}</div>' if context else "")
            + '</li>'
        )
    if len(items) == 1:
        return f'<div class="ev-measure"><strong>Result reported in this paper:</strong><ul class="ev-stat-list">{items[0]}</ul></div>'
    return (
        f'<details class="ev-stats"><summary>{len(items)} results reported in this paper</summary>'
        f'<ol class="ev-stat-list">{"".join(items)}</ol></details>'
    )

def slug(s):
    return re.sub(r'[^a-z0-9]+','-', s.lower()).strip('-')


def public_browse_regions(d):
    localization_card = next(
        (
            card for card in SYNTHESIS_CARDS_BY_SIGN.get(str(d.get("id")), [])
            if card.get("axis") == "LOCALIZATION"
        ),
        None,
    )
    if str((localization_card or {}).get("pattern_status") or "") in {
        "NOT_REPORTED", "NON_LOCALIZING"
    }:
        return ["No localization stated"]
    return list(OrderedDict.fromkeys(d.get("regions") or [d.get("region")]))

# Resolve each sign's location relationship once by immutable sign id.  Every
# presentation below (cards, regional search references, and map) consumes this
# same joined view; none of them carries an independently edited location copy.
SIGN_LOCATION_BY_ID = OrderedDict()
for d in data:
    mapping = BA.mapping_for_sign(d)
    lobes = []
    for aid in mapping["areas"]:
        lobe = BA.AREAS[aid]["lobe"]
        if lobe not in lobes:
            lobes.append(lobe)
    SIGN_LOCATION_BY_ID[d["id"]] = {**mapping, "lobes": lobes}

# The canonical sign appears once in its primary regional section.  Additional
# anatomical locations are generated below as references to that same sign id.
grouped = OrderedDict()
for r in region_order:
    grouped[r] = OrderedDict()
for d in data:
    for region in public_browse_regions(d):
        if region not in grouped:
            continue
        sub_values = d.get("subsections_by_region", {}).get(region)
        if not sub_values:
            combined = d.get("subs_by_region", {}).get(region, d["sub"])
            sub_values = [part.strip() for part in str(combined).split(";") if part.strip()]
        for sub in dict.fromkeys(sub_values):
            grouped[region].setdefault(sub, []).append(d)

area_signs_by_region = OrderedDict((r, OrderedDict()) for r in region_order)
for d in data:
    for aid in SIGN_LOCATION_BY_ID[d["id"]]["areas"]:
        lobe = BA.AREAS[aid]["lobe"]
        if lobe in area_signs_by_region:
            area_signs_by_region[lobe].setdefault(aid, []).append(d)

def sign_search_text(d, area_ids=None):
    mapping = SIGN_LOCATION_BY_ID[d["id"]]
    area_terms = []
    for aid in mapping["areas"] if area_ids is None else area_ids:
        area = BA.AREAS[aid]
        area_terms.extend([area["label"], area["name"], area["lobe"]])
    evidence_terms = []
    for entry, _relation in ledger_evidence_by_cardid.get(d["id"], []):
        row = entry["finding"]
        evidence_terms.extend([
            row["source_term"], row["citation"], row["laterality_localization"],
            entry["source"]["source_file"],
        ])
    return " ".join(str(x or "") for x in [
        d["sign"], d["phase"], d["region"], d["sub"], d["loc"], d["notes"], d["cite"],
        *area_terms, *evidence_terms,
    ]).lower().replace('"', "")

SIGN_BASE_SEARCH_BY_ID = {d["id"]: sign_search_text(d, []) for d in data}
SIGN_SEARCH_BY_ID = {d["id"]: sign_search_text(d) for d in data}
sign_search_json = json.dumps(
    {str(sign_id): value for sign_id, value in SIGN_SEARCH_BY_ID.items()},
    ensure_ascii=False,
    separators=(",", ":"),
)
region_counts = {r: sum(len(v) for v in grouped[r].values()) for r in region_order}

classification_nodes = {row["node_id"]: row for row in CLASSIFICATIONS["nodes"]}
sign_labels_by_id = {str(row["id"]): row["sign"] for row in data}
classification_roots = {
    "ILAE_SEIZURE_2025": "ILAE2025:DESC",
    "LUDERS_5D_2005": "LUDERS5D:D2",
}

def classification_tree(scheme_id, root_id):
    children = {}
    for node in CLASSIFICATIONS["nodes"]:
        if node["scheme_id"] == scheme_id:
            children.setdefault(node.get("parent_node_id"), []).append(node["node_id"])
    included = set()
    pending = [root_id]
    excluded_roots = {"ILAE2025:DESC:OBSERVABILITY", "ILAE2025:DESC:SOMATOTOPIC"}
    while pending:
        node_id = pending.pop()
        if node_id in included or node_id in excluded_roots:
            continue
        included.add(node_id)
        pending.extend(children.get(node_id, []))

    mapped_by_sign = {}
    for mapping in CLASSIFICATIONS["sign_mappings"]:
        node_id = mapping["node_id"]
        if node_id in included:
            mapped_by_sign.setdefault(str(mapping["sign_id"]), set()).add(node_id)

    def is_ancestor(candidate, node_id):
        parent = classification_nodes[node_id].get("parent_node_id")
        while parent in included:
            if parent == candidate:
                return True
            parent = classification_nodes[parent].get("parent_node_id")
        return False

    direct = {node_id: [] for node_id in included}
    for sign_id, mapped_nodes in mapped_by_sign.items():
        # The registry retains both broad category links and the more specific
        # term link.  The browser should use the specific term when one exists;
        # showing every retained parent link duplicates a sign across unrelated
        # branches without changing any underlying mapping.
        term_nodes = {
            node_id for node_id in mapped_nodes
            if classification_nodes[node_id].get("node_kind") == "TERM"
        }
        if term_nodes:
            mapped_nodes = term_nodes
        deepest = {
            node_id for node_id in mapped_nodes
            if not any(node_id != other and is_ancestor(node_id, other) for other in mapped_nodes)
        }
        for node_id in deepest:
            direct[node_id].append(sign_id)

    def build(node_id):
        row = classification_nodes[node_id]
        child_rows = [build(child_id) for child_id in sorted(
            (child for child in children.get(node_id, []) if child in included),
            key=lambda child: (
                classification_nodes[child].get("ordinal") or 9999,
                classification_nodes[child]["label"].casefold(),
            ),
        )]
        child_rows = [child for child in child_rows if child["all_sign_ids"]]
        visible_children = []
        node_sign_ids = list(direct[node_id]) if row.get("node_kind") == "TERM" else []
        broad_sign_ids = [] if row.get("node_kind") == "TERM" else list(direct[node_id])
        for child in child_rows:
            child_ids = child["all_sign_ids"]
            exact_single_leaf = (
                child["node_kind"] == "TERM"
                and not child["is_family"]
                and len(child_ids) == 1
                and sign_labels_by_id.get(str(child_ids[0]), "").casefold() == child["label"].casefold()
            )
            if exact_single_leaf:
                node_sign_ids.extend(child["all_sign_ids"])
            else:
                visible_children.append(child)
        child_rows = visible_children
        node_sign_ids = list(OrderedDict.fromkeys(node_sign_ids))
        broad_sign_ids = list(OrderedDict.fromkeys(broad_sign_ids))
        all_sign_ids = list(OrderedDict.fromkeys(
            node_sign_ids + broad_sign_ids
            + [sign_id for child in child_rows for sign_id in child["all_sign_ids"]]
        ))
        return {
            "node_id": node_id,
            "label": row["label"],
            "node_kind": row.get("node_kind", ""),
            "is_family": bool([child for child in children.get(node_id, []) if child in included]),
            "sign_ids": node_sign_ids,
            "broad_sign_ids": broad_sign_ids,
            "all_sign_ids": all_sign_ids,
            "children": child_rows,
        }

    root = build(root_id)
    return {"root_id": root_id, "root_label": root["label"], "groups": root["children"]}

classification_trees = OrderedDict(
    (scheme_id, classification_tree(scheme_id, root_id))
    for scheme_id, root_id in classification_roots.items()
)
classification_trees_json = json.dumps(classification_trees, ensure_ascii=False, separators=(",", ":"))

def is_lobe_level_subsection(label):
    value = str(label).casefold()
    return "lobe-level localization" in value or "reviewed source findings assigned to" in value

# ---- build region-jump pills ----
pills = []
for r in region_order:
    pills.append(f'<button class="pill" data-target="sec-{slug(r)}"><span class="pill-name">{esc(region_short[r])}</span><span class="pill-count" data-region="{esc(r)}">{region_counts[r]}</span></button>')
pills_html = "\n".join(pills)

# ---- SINGLE SOURCE OF TRUTH: link each curated card to its meta-analysis ledger
# entry (by explicit id, not fragile substring), so the card renders the SAME
# pooled lateralization figure and the SAME per-study source list as the top plot.
meta_by_cardid = {}
if META:
    for ms in META.get("by_sign", []):
        for cid in ms.get("sign_ids", []) or []:
            meta_by_cardid[cid] = ms
_gtname = {"seeg":"SEEG","postop":"post-op sz-freedom","intracranial_eeg":"intracranial EEG",
           "video_eeg":"video-EEG","scalp_eeg":"scalp EEG","imaging_concordance":"imaging concordance",
           "review":"review","none":"none"}
_dirword = {"contra":"Contralateral","ipsi":"Ipsilateral","dominant":"Dominant hemisphere","nondominant":"Non-dominant hemisphere"}
_certword = {"well_supported":"well supported","moderate":"moderate","single_source":"single source"}

def pooled_block_for(ms):
    """The card's lateralization evidence, rendered from the shared meta ledger."""
    if not ms:
        return "", 0
    items = []
    for c in ms.get("contributions", []):
        val = (f'{c["value"]:g}%' if "value" in c else esc(c.get("qualitative","supportive")))
        meta = f'{c.get("eclass") or "?"} / {_gtname.get(c.get("ground_truth"), c.get("ground_truth") or "-")}'
        items.append('<li><span class="ev-src">'+esc(c.get("cite", c["study"]))+'</span>'
                     + ((' <span class="ev-pg" title="Source page">'+esc(c["pg"])+'</span>') if c.get("pg") else '')
                     + ' <strong>'+val+'</strong> <span class="ev-meta">('+esc(meta)+')</span>'
                     + ((' &mdash; '+esc(c["note"])) if c.get("note") else '') + '</li>')
    nsent = ms.get("n_studies", 0) + ms.get("n_qualitative", 0)   # same count the top plot shows
    if ms.get("pooled") is not None:
        head = (f'<span class="pooled-hd"><strong>{ms["pooled"]:g}% {esc(_dirword.get(ms["direction"], ms["direction"]))}</strong> '
                f'&middot; range {ms["low"]:g}&#8211;{ms["high"]:g}% &middot; {nsent} '
                f'stud{"y" if nsent==1 else "ies"} &middot; {_certword.get(ms.get("certainty"),"?")}</span>')
    else:
        head = f'<span class="pooled-hd"><strong>{esc(_dirword.get(ms["direction"], ms["direction"]))}</strong> &middot; direction-only (no pooled %)</span>'
    contested = ('<div class="pooled-warn">&#9888;&#65039; '+esc(ms["contested"])+'</div>') if ms.get("contested") else ''
    block = ('<div class="d-row d-ev d-pooled"><span class="d-label">&#128218; Pooled lateralization &amp; sources (meta-analysis)</span>'
             + head + contested + '<ul class="ev-list">'+"".join(items)+'</ul></div>')
    return block, len([c for c in ms.get("contributions", []) if "value" in c])

# ---- SINGLE SOURCE OF TRUTH (cont.): predictive-value figures come from the SAME
# corpus_findings ledger the source-figures explorer renders, surfaced on the card
# via the finding's explicit card_ids link (assigned by exact phenomenon match, not
# fuzzy). Population-specific, so listed per source rather than pooled into one number.
ppv_by_cardid = {}
if CORPUS:
    for _p in CORPUS.get("papers", []):
        _cite = (_p.get("cite") or "?").split(".")[0][:46]
        for _f in _p.get("findings", []):
            if _f.get("metric") != "ppv":
                continue
            for _cid in _f.get("card_ids", []) or []:
                ppv_by_cardid.setdefault(_cid, []).append({
                    "value_text": _f.get("value_text") or (f'{_f["value"]:g}%' if isinstance(_f.get("value"), (int, float)) else ""),
                    "direction": _f.get("direction") or "",
                    "population": _f.get("population") or "",
                    "cite": _cite, "locator": _f.get("locator") or "", "quote": _f.get("quote") or "",
                })

def ppv_block_for(cid):
    """Predictive-value figures for a card, rendered from the shared corpus ledger."""
    rows = ppv_by_cardid.get(cid)
    if not rows:
        return ""
    items = []
    for r in rows:
        dchip = (f' <span class="ev-dir">{esc(r["direction"])}</span>' if r["direction"] and r["direction"] not in ("none","") else "")
        pop = (f' <span class="ev-pop">{esc(r["population"])}</span>' if r["population"] else "")
        items.append('<li><span class="ev-src">'+esc(r["cite"])+'</span>'
                     + ((' <span class="ev-pg" title="Source locator">'+esc(r["locator"])+'</span>') if r["locator"] else '')
                     + ' <strong>'+esc(r["value_text"])+'</strong>'+dchip+pop
                     + ((' <span class="ev-quote" title="'+esc(r["quote"])+'">&ldquo;&hellip;&rdquo;</span>') if r["quote"] else '')
                     + '</li>')
    return ('<div class="d-row d-ev d-ppv"><span class="d-label">&#127919; Predictive value in the source corpus</span>'
            '<ul class="ev-list">'+"".join(items)+'</ul></div>')

# ---- SINGLE SOURCE OF TRUTH (cont.): sensitivity = P(sign | localization), computed
# by the meta engine from the ledger's tagged frequency-within-a-group findings and
# read back here by card id, so the card, the descriptive-stats report, and the
# explorer all show the same numbers.
sens_by_cardid = (META.get("sensitivity", {}) or {}).get("by_card", {}) if META else {}

def sens_block_for(cid):
    blk = sens_by_cardid.get(str(cid))
    if not blk:
        return ""
    items = []
    for c in blk["conditions"]:
        s0 = c["sources"][0]
        kmeta = (f' <span class="ev-meta">(k={c["k"]}, mean of {c["k"]})</span>' if c["k"] > 1 else
                 f' <span class="ev-meta">({esc(s0["cite"])})</span>')
        rng = (f' <span class="ev-pop">range {c["low"]:g}&#8211;{c["high"]:g}%</span>' if c["k"] > 1 else "")
        q = (f' <span class="ev-quote" title="'+esc(s0["quote"])+'">&ldquo;&hellip;&rdquo;</span>') if s0.get("quote") else ""
        items.append(f'<li><strong>{c["mean"]:g}%</strong> in <span class="ev-src">{esc(c["cond"])}</span>{kmeta}{rng}{q}</li>')
    return ('<div class="d-row d-ev d-sens"><span class="d-label">&#128200; Sensitivity by localization &mdash; P(sign | group), computed from the corpus</span>'
            '<ul class="ev-list">'+"".join(items)+'</ul></div>')

def top_sens(cid):
    """Highest computed sensitivity for the compact metric tile, or None."""
    blk = sens_by_cardid.get(str(cid))
    if not blk:
        return None
    best = max(blk["conditions"], key=lambda c: c["high"])
    return f'{best["mean"]:g}% in {best["cond"]}'

def ledger_evidence_block(cid, notes=""):
    """Render source history behind one compact sign summary."""
    linked = ledger_evidence_by_cardid.get(cid, [])
    families = DESCRIPTIVE_FAMILIES_BY_SIGN.get(str(cid), [])
    informative_notes = str(notes or "").strip()
    if informative_notes == "Reviewed source evidence is shown below.":
        informative_notes = ""
    if not linked and not families and not informative_notes:
        return "", 0, ""
    papers, search = {}, []
    for entry, relation in linked:
        source, row = entry["source"], entry["finding"]
        paper = papers.setdefault(source["source_file"], {"source": source, "findings": []})
        paper["findings"].append((row, relation))
        search.extend([row["source_term"], row["claim"], statistic_search_text(row), row["citation"],
                       row["evidence_text"], row["source_finding_ref"]])
    paper_blocks = []
    for paper in papers.values():
        finding_blocks = []
        for row, relation in paper["findings"]:
            measure = statistic_block(row)
            source_role = ROLE_LABEL.get(row["evidence_role"], "Source information")
            relation_label = "Direct match" if relation == "EXACT" else "Related finding"
            finding_blocks.append(
                '<article class="reviewed-card-evidence">'
                f'<div class="ev-finding"><span class="ev-map ev-map-{relation.lower()}">{relation_label}</span> '
                f'<strong>{esc(row["source_term"])}</strong> &mdash; {esc(row["claim"])}</div>'
                f'{measure}'
                '<details class="ev-trace"><summary>Source text and study details</summary>'
                f'<div><strong>Location in paper:</strong> {esc(row["locators"])}</div>'
                f'{cited_source_line(row)}'
                f'<div><strong>Relevant source text:</strong> {esc(row["evidence_text"])}</div>'
                f'<div><strong>Who was studied:</strong> {esc(row["population"])}</div>'
                f'<div><strong>Source type:</strong> {esc(source_role)}</div>'
                '</details></article>')
        paper_blocks.append(
            '<li class="ev-paper-group">'
            '<div class="ev-paper">'
            f'<strong>Reviewed paper:</strong> <span class="ev-paper-file">{esc(paper["source"]["source_file"])}</span>'
            f'<span class="ev-paper-count">{len(paper["findings"])} finding{"s" if len(paper["findings"]) != 1 else ""}</span>'
            '</div>'
            f'{"".join(finding_blocks)}</li>')
    family_block = ""
    if families:
        family_rows = "".join(descriptive_family_row(row) for row in families)
        family_block = (
            '<details class="history-results">'
            f'<summary>Reported study results <span>{len(families)} groups</span></summary>'
            f'<div class="syn-family-scroll">{family_rows}</div></details>'
        )
    note_block = (
        f'<div class="history-note"><strong>Clinical context</strong><span>{esc(informative_notes)}</span></div>'
        if informative_notes else ""
    )
    counts = []
    if papers:
        counts.append(f'{len(papers)} paper{"s" if len(papers) != 1 else ""}')
    if linked:
        counts.append(f'{len(linked)} finding{"s" if len(linked) != 1 else ""}')
    if families:
        counts.append(f'{len(families)} result group{"s" if len(families) != 1 else ""}')
    count_label = " · ".join(counts) or "Background"
    return (
        '<details class="d-row d-ev evidence-history-shell">'
        f'<summary><span>Evidence history</span><span class="reviewed-evidence-count">{count_label}</span></summary>'
        '<div class="reviewed-evidence-panel">'
        '<div class="ev-toolbar"><button type="button" data-ev-action="expand">Expand source details</button>'
        '<button type="button" data-ev-action="collapse">Collapse source details</button></div>'
        f'{note_block}'
        '<div class="reviewed-evidence-scroll">'
        f'<ul class="ev-list">{"".join(paper_blocks)}</ul>{family_block}</div></div></details>',
        len(linked),
        " ".join(search),
    )

def readable_term(value):
    replacements = {
        "nondominant": "non-dominant",
        "contra": "contralateral",
        "ipsi": "ipsilateral",
        "NOT_REPORTED": "not reported",
    }
    text = replacements.get(str(value), str(value))
    return text.replace("_", " ").strip()


METRIC_LABELS = OrderedDict([
    ("PERCENTAGE", "Percentage"), ("PROPORTION", "Proportion"), ("COUNT", "Count"),
    ("P_VALUE", "P value"), ("RATE", "Rate"), ("RATE_RANGE", "Rate range"),
    ("RATIO", "Ratio"), ("RANGE", "Range"), ("MEAN", "Mean"),
    ("MEDIAN", "Median"), ("KAPPA", "Kappa"), ("DURATION", "Duration"),
    ("THRESHOLD", "Threshold"), ("ODDS_RATIO", "Odds ratio"),
    ("HAZARD_RATIO", "Hazard ratio"), ("FREQUENCY", "Frequency"),
    ("SENSITIVITY", "Sensitivity"), ("SPECIFICITY", "Specificity"),
    ("PPV", "Positive predictive value"), ("NPV", "Negative predictive value"),
    ("CORRELATION", "Correlation"), ("UPPER_BOUND_PERCENTAGE", "Upper-bound percentage"),
    ("OTHER", "Other reported result"),
])
PROPORTION_METRICS = {"PERCENTAGE", "PROPORTION", "SENSITIVITY", "SPECIFICITY", "PPV", "NPV"}
_MISSING_PUBLIC_VALUES = {
    "", "NONE", "NULL", "NOT_APPLICABLE", "NOT_REPORTED", "NONE_REPORTED", "NOT_QUANTITATIVE",
}
PUBLIC_SIGN_BY_ID = {str(row["id"]): row for row in data}


def public_value(value, fallback=""):
    if value is None:
        return fallback
    text = str(value).strip()
    return fallback if text.upper() in _MISSING_PUBLIC_VALUES else text


def public_context_value(value, fallback=""):
    text = public_value(value, fallback)
    if text and re.fullmatch(r"[A-Z][A-Z0-9_/-]*", text) and "_" in text:
        return readable_term(text).capitalize()
    return text


def metric_label(value):
    key = str(value or "OTHER").upper()
    return METRIC_LABELS.get(key, readable_term(key).title())


def family_sign_labels(family):
    labels = []
    for sign_id in family.get("sign_ids") or []:
        sign = PUBLIC_SIGN_BY_ID.get(str(sign_id))
        label = public_value((sign or {}).get("sign"))
        if label and label not in labels:
            labels.append(label)
    return labels


def statistic_ratio(statistic):
    for numerator_key, denominator_key in (
        ("numerator", "denominator"), ("numerator_numeric", "denominator_numeric"),
    ):
        numerator, denominator = statistic.get(numerator_key), statistic.get(denominator_key)
        if all(
            value is not None and str(value).strip().upper() not in _MISSING_PUBLIC_VALUES
            for value in (numerator, denominator)
        ):
            return f"{numerator}/{denominator}"
    return ""


def estimate_context(item):
    context = STATISTIC_CONTEXT_BY_ID.get(str(item.get("statistic_id") or "")) or {}
    return context, context.get("source") or {}, context.get("finding") or {}, context.get("statistic") or {}


def estimate_citation(item):
    _context, _source, finding, statistic = estimate_context(item)
    return public_value(statistic.get("citation")) or public_value(finding.get("citation"))


def estimate_search_text(item):
    _context, source, finding, statistic = estimate_context(item)
    return " ".join(str(value or "") for value in (
        item.get("value_text"), statistic_ratio(statistic),
        metric_label(statistic.get("metric_type")), estimate_citation(item),
        item.get("source_file") or source.get("source_file"),
        statistic.get("source_locator") or finding.get("locators"),
        finding.get("source_term"), statistic.get("population") or finding.get("population"),
        statistic.get("subgroup"), statistic.get("comparator"),
        statistic.get("phase") or finding.get("phase"), statistic.get("analysis_unit"),
    ))


def statistic_item(statistic_id):
    context = STATISTIC_CONTEXT_BY_ID.get(str(statistic_id)) or {}
    source = context.get("source") or {}
    statistic = context.get("statistic") or {}
    return {
        "statistic_id": str(statistic_id),
        "value_text": statistic_value(statistic),
        "source_file": source.get("source_file"),
        "work_id": source.get("work_id"),
    }


def family_reference_label(family):
    axis = readable_term(family.get("axis") or "result").title()
    signs = family_sign_labels(family)
    semiology = "; ".join(signs) if signs else "General or contextual result"
    endpoint = public_value(family.get("endpoint"), "Reported outcome")
    return f"{axis} · {semiology} · {endpoint}"


def descriptive_estimate_row(item, family):
    _context, source, finding, statistic = estimate_context(item)
    statistic_id = str(item.get("statistic_id") or "")
    value = public_value(item.get("value_text")) or public_value(statistic_value(statistic), "Reported value")
    metric = metric_label(statistic.get("metric_type") or family.get("metric_type"))
    ratio = statistic_ratio(statistic)
    population = public_context_value(statistic.get("population")) or public_context_value(finding.get("population"))
    subgroup = public_context_value(statistic.get("subgroup")) or public_context_value(family.get("subgroup"))
    comparator = public_context_value(statistic.get("comparator")) or public_context_value(family.get("comparator"))
    phase = public_context_value(statistic.get("phase")) or public_context_value(finding.get("phase")) or public_context_value(family.get("phase"))
    analysis_unit = public_context_value(statistic.get("analysis_unit")) or public_context_value(family.get("analysis_unit"))
    citation = estimate_citation(item)
    source_file = public_value(item.get("source_file")) or public_value(source.get("source_file"), "Source file not reported")
    locator = public_value(statistic.get("source_locator")) or public_value(finding.get("locators"), "Locator not reported")
    quote = public_value(statistic.get("source_excerpt")) or public_value(finding.get("evidence_text"))
    limitations = public_value(finding.get("limitations"))
    uncertainty = statistic_detail_text(statistic)
    chips = []
    if ratio:
        chips.append(f'<span><strong>n/N</strong> {esc(ratio)}</span>')
    for label, value_text in (
        ("Population", population), ("Subgroup", subgroup), ("Comparator", comparator),
        ("Phase", phase), ("Analysis unit", analysis_unit),
    ):
        if value_text:
            chips.append(f'<span><strong>{label}</strong> {esc(value_text)}</span>')
    provenance = []
    if quote:
        provenance.append(f'<div><strong>Source passage:</strong> &ldquo;{esc(quote)}&rdquo;</div>')
    if uncertainty:
        provenance.append(f'<div><strong>Uncertainty or statistical detail:</strong> {esc(uncertainty)}</div>')
    if limitations:
        provenance.append(f'<div><strong>Limitations:</strong> {esc(limitations)}</div>')
    linked_family_labels = []
    primary_family_id = PRIMARY_FAMILY_BY_STATISTIC_ID.get(statistic_id)
    for family_id in STATISTIC_FAMILY_IDS.get(statistic_id, []):
        if family_id == primary_family_id:
            continue
        linked_family = _FAMILY_BY_STRING_ID.get(family_id)
        if linked_family:
            label = family_reference_label(linked_family)
            if label not in linked_family_labels:
                linked_family_labels.append(label)
    if linked_family_labels:
        provenance.append(
            '<div><strong>Also linked to:</strong> '
            + esc("; ".join(linked_family_labels)) + '</div>'
        )
    provenance_block = (
        '<details class="evidence-stat-provenance"><summary>Quote, uncertainty, and provenance</summary>'
        + "".join(provenance) + '</details>'
        if provenance else ""
    )
    return f'''<div class="evidence-statistic" data-statistic-id="{esc(statistic_id)}">
  <div class="evidence-statistic-head"><strong>{esc(value)}</strong><span>{esc(metric)}</span></div>
  {f'<div class="evidence-stat-chips">{"".join(chips)}</div>' if chips else ''}
  {f'<div class="evidence-stat-citation"><strong>Citation:</strong> {esc(citation)}</div>' if citation else ''}
  <div class="evidence-stat-source"><strong>Source file:</strong> {esc(source_file)} <span>&middot;</span> <strong>Locator:</strong> {esc(locator)}</div>
  {provenance_block}
</div>'''


def descriptive_family_row(family, statistic_ids=None, count_as_family=True):
    family_id = str(family.get("analysis_id") or "")
    endpoint = public_value(family.get("endpoint"), "Reported outcome")
    metric_key = str(family.get("metric_type") or "OTHER").upper()
    metric = metric_label(metric_key)
    phase = public_context_value(family.get("phase"))
    population = public_context_value(family.get("population"))
    comparator = public_context_value(family.get("comparator"))
    subgroup = public_context_value(family.get("subgroup"))
    analysis_unit = public_context_value(family.get("analysis_unit"))
    reference_standard = public_context_value(family.get("reference_standard"))
    sign_labels = family_sign_labels(family)
    assigned_statistic_ids = (
        FAMILY_PRIMARY_STATISTIC_IDS.get(family_id, [])
        if statistic_ids is None else list(statistic_ids)
    )
    exact = [statistic_item(statistic_id) for statistic_id in assigned_statistic_ids]
    linked_statistic_ids = (
        FAMILY_LINKED_STATISTIC_IDS.get(family_id, [])
        if statistic_ids is None else assigned_statistic_ids
    )
    cross_linked_elsewhere = max(0, len(linked_statistic_ids) - len(exact))
    studies = OrderedDict()
    for item in exact:
        context, source, _finding, _statistic = estimate_context(item)
        work_id = public_value(item.get("work_id")) or public_value(source.get("work_id"))
        source_file = public_value(item.get("source_file")) or public_value(source.get("source_file"))
        citation = estimate_citation(item)
        study_key = work_id or source_file or citation or f"study-{len(studies) + 1}"
        study = studies.setdefault(study_key, {"citation": citation, "source_file": source_file, "items": []})
        if not study["citation"] and citation:
            study["citation"] = citation
        if not study["source_file"] and source_file:
            study["source_file"] = source_file
        study["items"].append(item)
    study_rows = []
    for study in studies.values():
        study_label = study["citation"] or study["source_file"] or "Catalogued study"
        statistic_word = "result" if len(study["items"]) == 1 else "results"
        study_rows.append(
            '<details class="evidence-study"><summary><span>{}</span><span>{} {}</span></summary><div>{}</div></details>'.format(
                esc(study_label), len(study["items"]), statistic_word,
                "".join(descriptive_estimate_row(item, family) for item in study["items"]),
            )
        )
    estimate_block = (
        f'<div class="evidence-study-list">{"".join(study_rows)}</div>' if study_rows else
        '<p class="syn-empty">No separate reported number was assigned to this result group.</p>'
    )
    cross_link_note = (
        '<p class="syn-cross-link-note">'
        f'{cross_linked_elsewhere:,} additional reported '
        f'{"number is" if cross_linked_elsewhere == 1 else "numbers are"} cross-linked to this group '
        'and shown once under their primary result group.</p>'
        if cross_linked_elsewhere else ""
    )
    summary = family.get("descriptive_proportion_summary") or {}
    range_text = ""
    if metric_key in PROPORTION_METRICS and summary.get("estimate_count"):
        values = [summary.get("minimum"), summary.get("median"), summary.get("maximum")]
        if all(value is not None for value in values):
            range_text = (
                f'<div class="syn-range"><strong>Study-reported range:</strong> {values[0] * 100:.1f}%–'
                f'{values[2] * 100:.1f}% (median {values[1] * 100:.1f}%). This is descriptive, not a pooled estimate.</div>'
            )
    context_rows = []
    for label, value in (
        ("Axis", readable_term(family.get("axis") or "" ).title()),
        ("Linked semiology", "; ".join(sign_labels)), ("Phase", phase),
        ("Population", population), ("Subgroup", subgroup), ("Comparator", comparator),
        ("Analysis unit", analysis_unit), ("Reference standard", reference_standard),
    ):
        if value:
            context_rows.append(f'<div><strong>{esc(label)}:</strong> {esc(value)}</div>')
    searchable = " ".join(str(value or "") for value in [
        endpoint, metric, family.get("axis"), phase, population, comparator, subgroup,
        analysis_unit, reference_standard, *sign_labels,
        *[estimate_search_text(item) for item in exact],
        *[
            family_reference_label(_FAMILY_BY_STRING_ID[linked_family_id])
            for statistic_id in FAMILY_PRIMARY_STATISTIC_IDS.get(family_id, [])
            for linked_family_id in STATISTIC_FAMILY_IDS.get(statistic_id, [])
            if linked_family_id in _FAMILY_BY_STRING_ID
        ],
    ]).lower()
    sign_ids = "|".join(sorted(str(sign_id) for sign_id in (family.get("sign_ids") or [])))
    study_count = family.get("source_work_count") or len(studies)
    study_word = "study" if study_count == 1 else "studies"
    number_count = len(exact)
    if number_count:
        number_meta = f'{number_count} {"number" if number_count == 1 else "numbers"}'
    elif cross_linked_elsewhere:
        number_meta = f'{cross_linked_elsewhere} cross-linked {"number" if cross_linked_elsewhere == 1 else "numbers"}'
    else:
        number_meta = "No separate number"
    summary_context_parts = []
    for value in (phase, subgroup, comparator):
        if value and value.casefold() not in {item.casefold() for item in summary_context_parts}:
            summary_context_parts.append(value)
        if len(summary_context_parts) == 2:
            break
    summary_context = " · ".join(summary_context_parts)
    title_markup = (
        f'<span class="syn-family-title"><strong>{esc(endpoint)}</strong>'
        + (f'<small>{esc(summary_context)}</small>' if summary_context else "")
        + '</span>'
    )
    count_attribute = "true" if count_as_family else "false"
    return f'''<details class="syn-family fx-row" data-count-item="{count_attribute}" data-metric="{esc(metric_key)}" data-sign-ids="{esc(sign_ids)}" data-fq="{esc(searchable)}">
  <summary>{title_markup}<span class="syn-family-meta">{esc(metric)} &middot; {study_count} {study_word} &middot; {number_meta}</span></summary>
  <div class="syn-family-body">
    <div class="syn-family-context">{"".join(context_rows)}</div>
    <p class="syn-no-pool">Source-specific descriptive results; no pooled estimate is implied.</p>
    {range_text}
    {cross_link_note}
    {estimate_block}
  </div>
</details>'''


def limited_sentences(value, limit=2):
    sentences = [part.strip() for part in re.split(r'(?<=[.!?])\s+', str(value or "").strip()) if part.strip()]
    return " ".join(sentences[:limit])


def concise_axis_sentence(card):
    text = limited_sentences(card.get("plain_summary"), 1)
    axis = str(card.get("axis") or "finding").lower()
    status = card.get("pattern_status")
    if status == "PREDOMINANT_WITH_EXCEPTIONS":
        if re.search(r"\bpredominantly\b", text, flags=re.I):
            return text
        match = re.search(r':\s*(.+?)[.]?$', text)
        if match:
            value = re.sub(r'\b(?:relationship|localization)\b', '', match.group(1), flags=re.I).strip(' .')
            return f"Predominantly {value}."
    if status == "NON_LATERALIZING":
        return "No reliable hemispheric lateralization."
    if status == "NON_LOCALIZING":
        return "No reliable anatomical localization."
    return text.replace("The embedded evidence ", "The reviewed evidence ")


def relationship_targets(card):
    values = []
    for relation in (card or {}).get("primary_relationships") or []:
        raw_targets = relation.get("targets")
        if raw_targets is None:
            raw_targets = [relation.get("target")]
        elif not isinstance(raw_targets, list):
            raw_targets = [raw_targets]
        for target in raw_targets:
            value = str(target or "").strip()
            if value and value not in values:
                values.append(value)
    return values


def lateralization_target_chips(sign_id):
    labels = {
        "right": "Right", "left": "Left", "dominant": "Dominant",
        "nondominant": "Non-dominant", "non-dominant": "Non-dominant",
        "contra": "Contralateral", "contralateral": "Contralateral",
        "ipsi": "Ipsilateral", "ipsilateral": "Ipsilateral",
        "bilateral": "Bilateral", "same-side": "Same side",
        "same side": "Same side", "nonlat": "No reliable lateralization",
        "non-lateralizing": "No reliable lateralization",
    }
    values = []
    for card in SYNTHESIS_CARDS_BY_SIGN.get(str(sign_id), []):
        if card.get("axis") != "LATERALIZATION":
            continue
        for target in relationship_targets(card):
            key = target.lower().replace("_", "-")
            if key in labels and labels[key] not in values:
                values.append(labels[key])
    visible = values[:5]
    chips = "".join(f'<span class="axis-chip">{esc(value)}</span>' for value in visible)
    if len(values) > len(visible):
        chips += f'<span class="axis-chip axis-chip-more">+{len(values) - len(visible)}</span>'
    return f'<span class="axis-chips">{chips}</span>' if chips else ""


def axis_synthesis(sign_id, axis):
    candidates = [
        card for card in SYNTHESIS_CARDS_BY_SIGN.get(str(sign_id), [])
        if card.get("axis") == axis
    ]
    if not candidates:
        return None
    # Multiple source-native groups may intentionally resolve to one public sign.
    # Use the best-supported card for the compact public summary; all group-level
    # cards and their provenance remain available in the private ledger.
    return max(
        candidates,
        key=lambda card: (
            len(card.get("supporting_finding_refs") or []),
            len(card.get("supporting_statistic_ids") or []),
            int(card.get("source_document_count") or 0),
            str(card.get("synthesis_id") or ""),
        ),
    )


def axis_pattern_badge(d, axis):
    card = axis_synthesis(d.get("id"), axis)
    if card:
        status = str(card.get("pattern_status") or "").strip()
        labels = {
            "NOT_REPORTED": f'No reported {axis.lower()} relationship',
            "NON_LATERALIZING": "No reliable lateralization",
            "NON_LOCALIZING": "No reliable localization",
        }
        label = labels.get(status)
        if label:
            return f'<span class="axis-state">{esc(label)}</span>'
    return ""


def lateralization_display(d):
    card = axis_synthesis(d.get("id"), "LATERALIZATION")
    state = axis_pattern_badge(d, "LATERALIZATION")
    status = str((card or {}).get("pattern_status") or "")
    if status in {"NOT_REPORTED", "NON_LATERALIZING"}:
        return state
    targets = lateralization_target_chips(d.get("id"))
    note = "" if card else f'<span class="axis-note">{esc(d.get("lat", ""))}</span>'
    display = f'{targets}{state}{note}'
    if not display and card:
        summary = limited_sentences(card.get("plain_summary"), 1)
        display = f'<span class="axis-note">{esc(summary)}</span>'
    return display


def localization_display(d):
    card = axis_synthesis(d.get("id"), "LOCALIZATION")
    state = axis_pattern_badge(d, "LOCALIZATION")
    status = str((card or {}).get("pattern_status") or "")
    if status in {"NOT_REPORTED", "NON_LOCALIZING"}:
        return state
    region_labels = {
        "reg:temporal": "Temporal", "temporal": "Temporal",
        "reg:frontal": "Frontal", "frontal": "Frontal",
        "reg:parietal": "Parietal", "parietal": "Parietal",
        "reg:occipital": "Occipital", "occipital": "Occipital",
        "reg:insular": "Insular", "insular": "Insular",
        "reg:limbic": "Limbic", "limbic": "Limbic",
        "reg:deep_subcortical": "Deep/Subcortical",
        "deep/subcortical": "Deep/Subcortical",
        "reg:multiregional": "Multiregional",
    }
    regions = []
    if card:
        for target in relationship_targets(card):
            region = region_labels.get(target.strip().lower())
            if region and region not in regions:
                regions.append(region)
    else:
        regions = list(OrderedDict.fromkeys(d.get("regions") or [d.get("region")]))
        if len(regions) > 1:
            regions = [region for region in regions if region != "No localization stated"]
    chips = "".join(
        f'<span class="region-chip" style="--region-chip:{region_colors.get(region, "#7b8494")}">{esc(region)}</span>'
        for region in regions if region
    )
    loc_text = "" if card else str(d.get("loc") or "").strip()
    listed = [part.strip() for part in loc_text.split(";") if part.strip()]
    if listed and all(part in set(regions) | {"No localization stated"} for part in listed):
        loc_text = ""
    text = f'<span class="location-note">{esc(loc_text)}</span>' if loc_text else ""
    region_block = f'<span class="region-chips">{chips}</span>' if chips else ""
    display = f'{region_block}{state}{text}'
    if not display and card:
        summary = limited_sentences(card.get("plain_summary"), 1)
        display = f'<span class="axis-note">{esc(summary)}</span>'
    return display


def compact_evidence_overview(d):
    cards = SYNTHESIS_CARDS_BY_SIGN.get(str(d["id"]), [])
    sources = set()
    findings = set()
    statistics = set()
    for card in cards:
        sources.update(card.get("source_files") or [])
        findings.update(card.get("supporting_finding_refs") or [])
        statistics.update(card.get("supporting_statistic_ids") or [])
    raw_summary = limited_sentences(d.get("evidence_summary"), 2)
    summary = raw_summary
    if d.get("support_items") and raw_summary:
        first_sentence = limited_sentences(raw_summary, 1)
        if ":" in first_sentence:
            lead = first_sentence.split(":", 1)[0].strip()
            if len(lead.split()) >= 5:
                summary = lead.rstrip(".") + "."
        elif ";" in first_sentence:
            summary = first_sentence.split(";", 1)[0].rstrip(".") + "."
    if not summary:
        summaries = [concise_axis_sentence(card) for card in sorted(cards, key=lambda row: row.get("axis", ""))]
        summary = " ".join(OrderedDict.fromkeys(value for value in summaries if value))
    if not summary:
        summary = limited_sentences(d.get("notes"), 2)
    count_items = [
        (len(sources), "paper"),
        (len(findings), "finding"),
        (len(statistics), "reported result"),
    ]
    counts = "".join(
        f'<span><strong>{count}</strong> {label}{"s" if count != 1 else ""}</span>'
        for count, label in count_items if count
    )
    basis = "Reviewed sources" if d.get("evid") == "SRC" else f'Evidence level {d.get("evid")}'
    counts += f'<span class="evidence-basis-chip">{esc(basis)}</span>'
    key_numbers = [
        str(item.get("display") or "").strip()
        for item in d.get("support_items") or []
        if str(item.get("display") or "").strip()
    ][:2]
    numbers = "".join(f'<li>{esc(value)}</li>' for value in key_numbers)
    numbers_block = f'<ul class="key-numbers">{numbers}</ul>' if numbers else ""
    return (
        '<div class="d-row evidence-overview"><span class="d-label">Summary</span>'
        f'<p>{esc(summary)}</p><div class="evidence-counts">{counts}</div>{numbers_block}</div>'
    )


def support_summary_block(d):
    """Render a compact, reader-facing synthesis without replacing source rows."""
    summary = str(d.get("evidence_summary") or "").strip()
    basis = str(d.get("evidence_basis") or "").strip()
    items = d.get("support_items") or []
    if not summary and not basis and not items:
        return ""
    item_html = "".join(
        f'<li>{esc(item.get("display", ""))}</li>'
        for item in items if str(item.get("display") or "").strip()
    )
    basis_html = f'<div class="support-basis">{esc(basis)}</div>' if basis else ""
    list_html = f'<ul class="support-list">{item_html}</ul>' if item_html else ""
    return (
        '<div class="d-row d-support">'
        '<span class="d-label">Overall pattern in the reviewed evidence</span>'
        f'{basis_html}<div class="support-summary">{esc(summary)}</div>{list_html}'
        '</div>'
    )

def evidence_metric_block(ec):
    if ec == "SRC":
        return (
            '<div class="metric"><span class="d-label">Evidence basis</span>'
            '<span class="metric-val source-evidence-value">Reviewed sources</span></div>'
        )
    return (
        '<div class="metric"><span class="d-label">Strength of evidence</span>'
        f'<span class="metric-val"><span class="evid-badge" style="background:{evidcolor.get(ec,"#888")}">{esc(ec)}</span></span></div>'
    )

def evidence_header_chip(ec):
    if ec == "SRC":
        return '<span class="chip source-evidence-chip" title="Evidence summarized from reviewed sources">Reviewed sources</span>'
    return f'<span class="chip evid-dot" style="background:{evidcolor.get(ec,"#888")}" title="Evidence level {esc(ec)}">{esc(ec)}</span>'

def area_reference_blocks(region):
    """Regional sign cards generated from the same sign-id location join as the map."""
    blocks = []
    for aid, signs in area_signs_by_region[region].items():
        area = BA.AREAS[aid]
        title = f'{area["name"]} (Brodmann {area["label"]})'
        refs = []
        for d in signs:
            lc, ec = d["latcode"], d["evid"]
            ref_search = f'{area["name"]} {area["label"]} {area["lobe"]}'.lower()
            detail_name = "sign-" + hashlib.sha256(str(d["id"]).encode("utf-8")).hexdigest()[:24] + ".html"
            _nsrc = len(ledger_evidence_by_cardid.get(d.get("id"), []))
            lib_chip = (f'<span class="chip lib-chip" title="Reviewed source findings">&#128218; {_nsrc}</span>'
                        if _nsrc else '')
            evid_chip = evidence_header_chip(ec)
            phase_search = "|".join(d.get("phase_values") or [d["phase"]])
            refs.append(f'''<div class="sign" id="area-sign-{slug(region)}-{aid}-{d['id']}"
    data-area-ref="true" data-id="{d['id']}" data-ba="{esc(aid)}" data-region="{esc(region)}"
    data-regions="{esc('|'.join(public_browse_regions(d)))}"
    data-phase="{esc(d['phase'])}" data-phase-search="{esc(phase_search)}" data-latcode="{esc(lc)}" data-evid="{esc(ec)}"
    data-search="{esc(ref_search)}" style="--accent:{latcolor.get(lc,'#999')}">
  <button class="sign-head" aria-expanded="false">
    <span class="chevron">&#8250;</span>
    <span class="sign-name">{esc(d['sign'])}</span>
    <span class="head-chips">
      <span class="chip phase-badge phase-{slug(d['phase'].split('/')[0])}">{esc(d['phase'])}</span>
      <span class="chip lat-chip" style="color:{latcolor.get(lc,'#333')};background:{latbg.get(lc,'#f7f7f7')};border-color:{latcolor.get(lc,'#333')}">{latlabel.get(lc,'?')}</span>
      {evid_chip}
      {lib_chip}
    </span>
  </button>
  <div class="detail" data-detail-path="fragments/{detail_name}">
    <div class="detail-loading">Loading details&hellip;</div>
  </div>
</div>''')
        blocks.append(f'''<div class="sub-block area-map-block collapsed" data-sub="{esc(title)}" data-map-area="{esc(aid)}">
  <button class="sub-toggle" aria-expanded="false">
    <span class="sub-chev">&#9656;</span>
    <span class="sub-name">{esc(title)}</span>
    <span class="sub-count">{len(signs)}</span>
  </button>
  <div class="sub-body">
{chr(10).join(refs)}
  </div>
</div>''')
    return blocks

# ---- build sections ----
detail_fragments = {}
sections = []
for r in region_order:
    rc = region_colors[r]
    lobe_level_blocks = []
    sub_blocks = []
    for sub, signs in sorted(grouped[r].items(), key=lambda item: (not is_lobe_level_subsection(item[0]), str(item[0]).casefold())):
        rows = []
        for d in signs:
            lc, ec = d["latcode"], d["evid"]
            accent = latcolor.get(lc,"#999")
            _bmap = SIGN_LOCATION_BY_ID[d["id"]]
            map_row = ""
            if _bmap["areas"]:
                _why = f'Show where {d["sign"]} localizes'
                _chips = "".join(
                    f'<button class="ba-chip{" bc-deep" if BA.AREAS[a].get("buried") else ""}" '
                    f'data-ba="{a}" title="{esc(BA.AREAS[a]["name"])}">{BA.AREAS[a]["label"]}</button>'
                    for a in _bmap["areas"])
                map_row = (f'<div class="d-row d-map"><span class="d-label">Brodmann areas</span>'
                           f'<span class="d-value"><span class="ba-chips">{_chips}</span>'
                           f'<button class="map-jump" data-sign="{d["id"]}" '
                           f'title="{esc(_why)}">Show on map &#8599;</button></span></div>')
            ev_block, _nsrc, ev_text = ledger_evidence_block(d.get("id"), d.get("notes"))
            lib_chip = (f'<span class="chip lib-chip" title="Reviewed source findings">&#128218; {_nsrc}</span>'
                        if _nsrc else '')
            evid_chip = evidence_header_chip(ec)
            overview_block = compact_evidence_overview(d)
            lat_targets = lateralization_target_chips(d.get("id"))
            loc_display = localization_display(d)
            source_status_block = ('' if _nsrc else '''<div class="d-row d-cite source-review-pending">
        <span class="d-label">Source review pending</span>
        <span class="d-value">This summary does not yet have an individually reviewed paper linked to it.</span>
      </div>''')
            search_str = ""
            ppv_block = sens_block = ""
            detail_name = "sign-" + hashlib.sha256(str(d["id"]).encode("utf-8")).hexdigest()[:24] + ".html"
            detail_path = "fragments/" + detail_name
            if detail_name not in detail_fragments:
                detail_fragments[detail_name] = f'''<div class="detail-inner">
      <div class="d-row d-lat">
        <span class="d-label">Lateralization</span>
        <span class="d-value">{lateralization_display(d)}</span>
      </div>
      <div class="d-row d-loc">
        <span class="d-label">Anatomical localization</span>
        <span class="d-value">{loc_display}</span>
      </div>
      {map_row}
      {overview_block}
      {source_status_block}
      {ev_block}
      {sens_block}
      {ppv_block}
    </div>'''
            phase_search = "|".join(d.get("phase_values") or [d["phase"]])
            rows.append(f'''<div class="sign" id="sign-{slug(r)}-{d['id']}" data-id="{d['id']}" data-region="{esc(r)}" data-regions="{esc('|'.join(public_browse_regions(d)))}" data-phase="{esc(d['phase'])}" data-phase-search="{esc(phase_search)}" data-latcode="{lc}" data-evid="{ec}" data-search="{esc(search_str)}" style="--accent:{accent}">
  <button class="sign-head" aria-expanded="false">
    <span class="chevron">&#8250;</span>
    <span class="sign-name">{esc(d['sign'])}</span>
    <span class="head-chips">
      <span class="chip phase-badge phase-{slug(d['phase'].split('/')[0])}">{esc(d['phase'])}</span>
      <span class="chip lat-chip" style="color:{latcolor.get(lc,'#333')};background:{latbg.get(lc,'#f7f7f7')};border-color:{latcolor.get(lc,'#333')}">{latlabel.get(lc,'?')}</span>
      {evid_chip}
      {lib_chip}
    </span>
  </button>
  <div class="detail" data-detail-path="{detail_path}">
    <div class="detail-loading">Loading details&hellip;</div>
  </div>
</div>''')
        block = f'''<div class="sub-block collapsed" data-sub="{esc(sub)}">
  <button class="sub-toggle" aria-expanded="false">
    <span class="sub-chev">&#9656;</span>
    <span class="sub-name">{esc(sub)}</span>
    <span class="sub-count">{len(signs)}</span>
  </button>
  <div class="sub-body">
{chr(10).join(rows)}
  </div>
</div>'''
        (lobe_level_blocks if is_lobe_level_subsection(sub) else sub_blocks).append(block)
    sections.append(f'''<section class="region-section" id="sec-{slug(r)}" data-region="{esc(r)}">
  <button class="region-toggle" style="--rc:{rc}" aria-expanded="true">
    <span class="region-chev">&#9662;</span>
    <span class="region-name">{esc(r).upper()}</span>
    <span class="region-count"><span data-region="{esc(r)}">{region_counts[r]}</span></span>
  </button>
  <div class="region-body">
{chr(10).join(lobe_level_blocks + area_reference_blocks(r) + sub_blocks)}
  </div>
</section>''')
sections_html = "\n".join(sections)

# ---------- Lateralizing-reliability chart (Loddenkemper & Kotagal 2005, Table 1) ----------
def build_lateral(rows):
    dirs=[("contra","Contralateral to the seizure focus"),
          ("ipsi","Ipsilateral to the focus"),
          ("dominant","Dominant hemisphere"),
          ("nondominant","Non-dominant hemisphere")]
    W=760; labelW=290; padR=52; padT=30; rowH=31; headH=25; grpGap=9; padB=26
    plotL=labelW; plotR=W-padR; plotW=plotR-plotL
    def X(p): return plotL + p/100.0*plotW
    # height
    H=padT
    for dc,_ in dirs:
        g=[r for r in rows if r["dir"]==dc]
        if g: H+=headH+rowH*len(g)+grpGap
    H+=padB
    s=[f'<svg class="forest-svg" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI,Arial,sans-serif">']
    # vertical gridlines 0..100
    for t in [0,25,50,75,100]:
        x=X(t)
        s.append(f'<line x1="{x:.1f}" y1="{padT-4}" x2="{x:.1f}" y2="{H-padB}" stroke="#e7ebf2" stroke-width="1" {"" if t==0 else "stroke-dasharray=\"3 3\""}/>')
        s.append(f'<text x="{x:.1f}" y="{padT-8}" font-size="9" fill="#9aa3b2" text-anchor="middle">{t}%</text>')
    y=padT
    for dc,dname in dirs:
        g=sorted([r for r in rows if r["dir"]==dc], key=lambda r:-r["pct"])
        if not g: continue
        col=latcolor[dc]
        s.append(f'<text x="6" y="{y+15:.0f}" font-size="10.5" font-weight="800" fill="{col}" letter-spacing="0.05em">{esc(dname.upper())}</text>')
        y+=headH
        for r in g:
            yc=y+rowH/2
            s.append(f'<text x="{labelW-12}" y="{yc-2:.1f}" font-size="10.5" fill="#243244" text-anchor="end">{esc(r["sign"])}</text>')
            s.append(f'<text x="{labelW-12}" y="{yc+9:.1f}" font-size="8.5" fill="#9198a6" text-anchor="end">{esc(r["freq"])}</text>')
            s.append(f'<rect x="{plotL}" y="{yc-7:.1f}" width="{plotW:.1f}" height="14" rx="3" fill="#eef1f6"/>')
            bw=X(r["pct"])-plotL
            s.append(f'<rect x="{plotL}" y="{yc-7:.1f}" width="{bw:.1f}" height="14" rx="3" fill="{col}"/>')
            s.append(f'<text x="{X(r["pct"])+7:.1f}" y="{yc+3.5:.1f}" font-size="10" font-weight="700" fill="{col}">{r["pct"]}%</text>')
            y+=rowH
        y+=grpGap
    s.append(f'<text x="{plotL+plotW/2:.0f}" y="{H-7}" font-size="9.5" fill="#8a93a5" text-anchor="middle">proportion of cases lateralizing in the stated direction</text>')
    s.append('</svg>')
    return "\n".join(s)
lateral_svg = build_lateral(LATERAL)

# ---------- Evidence-weighted lateralizing reliability ----------
# Renders the deterministic output of tools/meta_analysis.py as two dense, compact,
# directly-labelled nested views (by region; by semiology) with per-study
# traceability one click away, plus a concise conflicting-evidence panel.
def build_meta(meta, flags):
    if not meta or not meta.get("by_sign"):
        return ""
    dirlabel = {"contra":"CONTRA","ipsi":"IPSI","dominant":"DOMINANT","nondominant":"NON-DOM"}
    certpips = {"well_supported":3, "moderate":2, "single_source":1}
    certname = {"well_supported":"well supported", "moderate":"moderate", "single_source":"single source"}
    gtname = {"seeg":"SEEG","postop":"post-op sz-freedom","intracranial_eeg":"intracranial EEG",
              "video_eeg":"video-EEG","scalp_eeg":"scalp EEG","imaging_concordance":"imaging concordance",
              "review":"review","none":"none"}
    # global max weight -> consistent weight-bar scale across every sign
    maxw = 1.0
    for s in meta["by_sign"]:
        for c in s["contributions"]:
            maxw = max(maxw, c.get("weight", 0))

    # index review flags by sign name
    flag_by_sign = {}
    for fl in (flags or {}).get("flags", []):
        flag_by_sign.setdefault(fl["sign"], []).append(fl)

    def strip(s):
        col = latcolor.get(s["direction"], "#666")
        W, H, padL, padR, y = 208, 20, 6, 8, 11
        trackW = W - padL - padR
        def X(p):
            p = max(50.0, min(100.0, p))
            return padL + (p-50.0)/50.0*trackW
        g = [f'<svg class="mstrip-svg" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">']
        g.append(f'<rect x="{padL}" y="{y-3}" width="{trackW}" height="6" rx="3" fill="#eef1f6"/>')
        # 75% reference tick
        g.append(f'<line x1="{X(75):.1f}" y1="{y-5}" x2="{X(75):.1f}" y2="{y+5}" stroke="#d7dde6" stroke-width="1" stroke-dasharray="2 2"/>')
        if s.get("pooled") is None:
            g.append(f'<text x="{padL+trackW/2:.0f}" y="{y+3.5:.0f}" font-size="8.5" fill="#9aa3b2" text-anchor="middle" font-style="italic">qualitative &#8212; no pooled %</text>')
            g.append('</svg>')
            return "".join(g)
        lo, hi, pooled = s["low"], s["high"], s["pooled"]
        # range bar low->high
        if hi > lo:
            g.append(f'<rect x="{X(lo):.1f}" y="{y-3}" width="{X(hi)-X(lo):.1f}" height="6" rx="3" fill="{col}" fill-opacity="0.28"/>')
            for v in (lo, hi):
                g.append(f'<line x1="{X(v):.1f}" y1="{y-4}" x2="{X(v):.1f}" y2="{y+4}" stroke="{col}" stroke-width="1" stroke-opacity="0.55"/>')
        # pooled marker (native hover tooltip via <title>)
        r = 3.2 + certpips.get(s.get("certainty"),1)*0.7
        tip = f'{s["sign"]} — pooled {pooled:g}% {s["direction"]}; range {lo:g}-{hi:g}%; {s["n_studies"]} stud{"y" if s["n_studies"]==1 else "ies"}'
        g.append(f'<circle cx="{X(pooled):.1f}" cy="{y}" r="{r:.1f}" fill="{col}" stroke="#fff" stroke-width="1.4"><title>{esc(tip)}</title></circle>')
        g.append('</svg>')
        return "".join(g)

    def contrib_table(s):
        rows = []
        rows.append('<div class="mc-head"><span>Study</span><span>Value</span><span>Weight</span><span>Class</span><span>Ground truth</span><span>N</span><span>Pg</span></div>')
        for c in s["contributions"]:
            w = c.get("weight",0)
            barw = max(3, round(w/maxw*100))
            val = (str(c["value"])+'%') if "value" in c else ('<span class="mc-qual">'+esc(c.get("qualitative","qual."))+'</span>')
            wp = c.get("weight_parts",{})
            wtitle = f'{wp.get("class_base","?")} (class) x {wp.get("ground_truth_mult","?")} (ground truth) x {wp.get("size_factor","?")} (size) = {w}'
            rows.append(
                '<div class="mc-row">'
                + '<span class="mc-cite">'+esc(c.get("cite",c["study"]))+'</span>'
                + '<span class="mc-val">'+val+'</span>'
                + '<span class="mc-wt" title="'+esc(wtitle)+'"><span class="mc-bar" style="width:'+str(barw)+'%;background:'+latcolor.get(s["direction"],"#888")+'"></span><span class="mc-wn">'+f'{w:.2f}'+'</span></span>'
                + '<span class="mc-cl">'+esc(c.get("eclass") or "?")+'</span>'
                + '<span class="mc-gt">'+esc(gtname.get(c.get("ground_truth"),c.get("ground_truth") or "-"))+'</span>'
                + '<span class="mc-n">'+(str(c["n"]) if c.get("n") else "&#8212;")+'</span>'
                + '<span class="mc-pg">'+(esc(c["pg"]) if c.get("pg") else "&#8212;")+'</span>'
                + '</div>')
            if c.get("note"):
                rows.append('<div class="mc-note">'+esc(c["note"])+'</div>')
        return "".join(rows)

    def caveats(s):
        if s.get("contested"):
            return '<div class="mcav mcav-warn"><strong>Contested.</strong> '+esc(s["contested"])+'</div>'
        return ""

    _rid = [0]
    def row(s, view):
        _rid[0]+=1
        rid = f'm{view}-{_rid[0]}'
        col = latcolor.get(s["direction"],"#666")
        bg = latbg.get(s["direction"],"#f5f5f5")
        pooled_txt = (f'{s["pooled"]:g}%' if s.get("pooled") is not None else '&#8212;')
        rng = (f'<span class="mrange">{s["low"]:g}&#8211;{s["high"]:g}</span>' if s.get("pooled") is not None and s["high"]>s["low"] else '')
        pips = certpips.get(s.get("certainty"),1)
        pip_html = "".join('<i class="'+("on" if k<pips else "off")+'"></i>' for k in range(3))
        contested_mark = ' <span class="mflag" title="contested">&#9888;&#65039;</span>' if s.get("contested") else ''
        nsent = s["n_studies"] + s.get("n_qualitative",0)
        summ = ''
        if s.get("pooled") is not None:
            summ = (f'pooled <strong>{s["pooled"]:g}%</strong> &middot; range {s["low"]:g}&#8211;{s["high"]:g}% '
                    f'&middot; weighted SD {s.get("wsd",0):g} &middot; &Sigma;weight {s.get("total_weight",0):g} '
                    f'&middot; {nsent} stud{"y" if nsent==1 else "ies"} &middot; {certname.get(s.get("certainty"),"?")}')
        else:
            summ = f'direction-only ({nsent} qualitative source{"s" if nsent!=1 else ""}); no comparable percentage to pool'
        sortp = s["pooled"] if s.get("pooled") is not None else -1
        return (
        f'<div class="msign" data-dir="{s["direction"]}" data-pooled="{sortp:g}" data-cert="{pips}" '
        f'data-weight="{s.get("total_weight",0):g}" data-order="{_rid[0]}" data-name="{esc(s["sign"].lower())}">'
        f'<button class="msign-head" aria-expanded="false" data-tgt="{rid}">'
        f'<span class="mchev">&#8250;</span>'
        f'<span class="mdir" style="color:{col};background:{bg};border-color:{col}">{dirlabel.get(s["direction"],"?")}</span>'
        f'<span class="mname">{esc(s["sign"])}{contested_mark}<span class="mba">{esc(s["lobe"])} &middot; {esc(s.get("gyrus",""))}{(" &middot; "+esc(s["ba"])) if s.get("ba") else ""}</span></span>'
        f'<span class="mstrip">{strip(s)}</span>'
        f'<span class="mval" style="color:{col}">{pooled_txt}</span>'
        f'<span class="mcert" title="{certname.get(s.get("certainty"),"?")}: {pips} evidence-support point{("s" if pips != 1 else "")}">{pip_html}</span>'
        f'</button>'
        f'<div class="mdetail" id="{rid}"><div class="mdetail-in">'
        f'<div class="msumm">{summ}</div>'
        f'{caveats(s)}'
        f'<div class="mctab">{contrib_table(s)}</div>'
        f'</div></div>'
        f'</div>')

    # view (i): by region -> gyrus/BA subgroup -> sign
    reg_blocks = []
    for reg in meta["by_region"]:
        rc = region_colors.get(reg["lobe"], "#333")
        grp = []
        for group_order, g in enumerate(reg["groups"]):
            head = esc(g["gyrus"]) + ((' &middot; ' + esc(g["ba"])) if g.get("ba") else '')
            grp.append(f'<div class="mgrp" data-order="{group_order}"><div class="mgrp-h">{head}</div>'
                       + "".join(row(s,"r") for s in g["signs"]) + '</div>')
        reg_blocks.append(f'<div class="mreg"><div class="mreg-h" style="--rc:{rc}">{esc(reg["lobe"]).upper()}</div>'
                          + "".join(grp) + '</div>')
    view_region = "".join(reg_blocks)

    # view (ii): by semiology alphabetical
    view_sign = "".join(row(s,"s") for s in meta["by_sign"])

    return f'''<details class="frontpage-fold meta-fold historical-meta-fold">
<summary>Historical weighted analysis &mdash; {len(meta["by_sign"])} selected signs</summary>
<div class="meta-wrap"><div class="meta-card">
  <div class="meta-head">
    <p><strong>Historical analysis retained for provenance.</strong> This separately curated panel predates the current master ledger. It remains available here without being presented as comprehensive ledger coverage.</p>
    <p>{esc(meta.get("method_explanation", ""))} The dot shows the weighted result, the pale bar shows the reported range, and the points show how much supporting evidence contributed. Tap a row to see every study value and its weight.</p>
    <p><strong>Evidence-support points:</strong> When studies report comparable percentages, 3 points means at least 3 such studies or a total weight of at least 6; 2 points means 2 studies or a total weight of at least 3; 1 point means less support. For direction-only results, the same cutoffs use the direction-only sources. These cutoffs are specific to this atlas, not a standard medical evidence grade.</p>
  </div>
  <div class="meta-tabs">
    <button class="mtab on" data-view="region">By region &rarr; gyrus (Brodmann) &rarr; sign</button>
    <button class="mtab" data-view="sign">By semiology (A&ndash;Z) &rarr; region</button>
    <label class="msort msort-region"><span>sort</span>
      <select id="meta-sort-region">
        <option value="original">regional order</option>
        <option value="pooled">reliability &darr;</option>
        <option value="cert">evidence support &darr;</option>
        <option value="name">sign A&ndash;Z</option>
        <option value="dir">direction</option>
      </select>
    </label>
    <label class="msort msort-sign" hidden><span>sort</span>
      <select id="meta-sort-sign">
        <option value="name">A&ndash;Z</option>
        <option value="pooled">reliability &darr;</option>
        <option value="cert">evidence support &darr;</option>
        <option value="dir">direction</option>
      </select>
    </label>
    <span class="meta-axis"><span class="ma-lab">reliability</span><span class="ma-scale"><i>50%</i><i>75%</i><i>100%</i></span></span>
  </div>
  <div class="meta-legend">
    <span><span class="ml-dot" style="background:{latcolor['contra']}"></span>Contralateral</span>
    <span><span class="ml-dot" style="background:{latcolor['ipsi']}"></span>Ipsilateral</span>
    <span><span class="ml-dot" style="background:{latcolor['dominant']}"></span>Dominant</span>
    <span><span class="ml-dot" style="background:{latcolor['nondominant']}"></span>Non-dominant</span>
    <span class="ml-cert"><i class="on"></i><i class="on"></i><i class="on"></i> evidence support (studies &amp; weight)</span>
  </div>
  <div class="meta-view" id="meta-view-region">{view_region}</div>
  <div class="meta-view" id="meta-view-sign" hidden>{view_sign}</div>
</div></div>
</details>'''

deferred_fragments = {}

def defer_details_body(html, filename):
    """Keep a fold's banner in the main page and load its large body on demand."""
    summary_end = html.index("</summary>") + len("</summary>")
    details_end = html.rfind("</details>")
    deferred_fragments[filename] = html[summary_end:details_end]
    shell = html[:summary_end] + '<div class="lazy-fragment">Open this section to load its contents.</div>' + html[details_end:]
    return shell.replace("<details ", f'<details data-fragment="fragments/{filename}" ', 1)


def build_unassigned_statistic_section(statistic_ids):
    if not statistic_ids:
        return ""
    sign_groups = {}
    for statistic_id in statistic_ids:
        context = STATISTIC_CONTEXT_BY_ID.get(str(statistic_id)) or {}
        source = context.get("source") or {}
        finding = context.get("finding") or {}
        statistic = context.get("statistic") or {}
        endpoint = public_value(finding.get("source_term"), "General or contextual result")
        metric_key = str(statistic.get("metric_type") or "OTHER").upper()
        sign_ids = []
        sign_labels = []
        for sign_id in [*(finding.get("exact_sign_ids") or []), *(finding.get("related_sign_ids") or [])]:
            sign_id = str(sign_id)
            label = public_value((PUBLIC_SIGN_BY_ID.get(sign_id) or {}).get("sign"))
            if label and sign_id not in sign_ids:
                sign_ids.append(sign_id)
                sign_labels.append(label)
        if len(sign_labels) == 1:
            sign_group_key = (0, sign_labels[0].casefold(), sign_labels[0])
        elif len(sign_labels) > 1:
            sign_group_key = (1, "multiple linked semiologies", "Multiple linked semiologies")
        else:
            sign_group_key = (2, "general or contextual outcomes", "General or contextual outcomes")
        sign_group = sign_groups.setdefault(sign_group_key, {"groups": {}, "statistic_count": 0})
        sign_group["statistic_count"] += 1
        group = sign_group["groups"].setdefault(
            (endpoint.casefold(), metric_key),
            {"endpoint": endpoint, "metric_type": metric_key, "statistic_ids": [], "sign_ids": [], "works": set()},
        )
        group["statistic_ids"].append(str(statistic_id))
        for sign_id in sign_ids:
            if sign_id not in group["sign_ids"]:
                group["sign_ids"].append(sign_id)
        work_key = public_value(source.get("work_id")) or public_value(source.get("source_file"))
        if work_key:
            group["works"].add(work_key)
    sign_sections = []
    for sign_group_key in sorted(sign_groups):
        sign_group = sign_groups[sign_group_key]
        rows = []
        for group_key in sorted(sign_group["groups"]):
            group = sign_group["groups"][group_key]
            pseudo_family = {
                "analysis_id": "",
                "axis": "",
                "endpoint": group["endpoint"],
                "metric_type": group["metric_type"],
                "sign_ids": group["sign_ids"],
                "source_work_count": len(group["works"]),
            }
            rows.append(
                descriptive_family_row(
                    pseudo_family,
                    statistic_ids=group["statistic_ids"],
                    count_as_family=False,
                )
            )
        outcome_word = "outcome" if len(rows) == 1 else "outcomes"
        number_count = sign_group["statistic_count"]
        number_word = "number" if number_count == 1 else "numbers"
        sign_sections.append(
            '<details class="evidence-sign-group" data-fx-group>'
            f'<summary><span>{esc(sign_group_key[2])}</span>'
            f'<span>{len(rows):,} {outcome_word} &middot; {number_count:,} {number_word}</span></summary>'
            f'<div class="evidence-sign-results">{"".join(rows)}</div>'
            '</details>'
        )
    number_word = "number" if len(statistic_ids) == 1 else "numbers"
    return (
        '<section class="evidence-axis-group evidence-contextual-results" data-fx-group>'
        '<div class="evidence-axis-heading"><span>General or contextual results</span>'
        f'<span>{len(statistic_ids):,} reported {number_word}</span></div>'
        f'{"".join(sign_sections)}</section>'
    )


def build_descriptive_family_panel(families):
    if not families:
        return ""
    counts = {}
    for family in families:
        metric = str(family.get("metric_type") or "OTHER").upper()
        counts[metric] = counts.get(metric, 0) + 1
    buttons = [f'<button class="fxb on" data-f="all">All <i>{len(families):,}</i></button>']
    for metric, count in sorted(counts.items()):
        buttons.append(
            f'<button class="fxb" data-f="{esc(metric)}">{esc(metric_label(metric))} <i>{count:,}</i></button>'
        )
    families_by_axis = OrderedDict((axis, []) for axis in ("LATERALIZATION", "LOCALIZATION"))
    for family in families:
        axis = str(family.get("axis") or "OTHER").upper()
        families_by_axis.setdefault(axis, []).append(family)
    axis_sections = []
    for axis, axis_families in families_by_axis.items():
        if not axis_families:
            continue
        sign_groups = {}
        for family in axis_families:
            labels = family_sign_labels(family)
            if len(labels) == 1:
                group_key = (0, labels[0].casefold(), labels[0])
            elif len(labels) > 1:
                group_key = (1, "multiple linked semiologies", "Multiple linked semiologies")
            else:
                group_key = (2, "general or contextual outcomes", "General or contextual outcomes")
            sign_groups.setdefault(group_key, []).append(family)
        sign_sections = []
        for group_key in sorted(sign_groups):
            group_label = group_key[2]
            group_families = sorted(sign_groups[group_key], key=lambda family: (
                str(family.get("endpoint") or "").casefold(),
                str(family.get("metric_type") or "").casefold(),
                str(family.get("phase") or "").casefold(),
                str(family.get("analysis_id") or ""),
            ))
            outcome_word = "outcome" if len(group_families) == 1 else "outcomes"
            sign_sections.append(
                '<details class="evidence-sign-group" data-fx-group>'
                f'<summary><span>{esc(group_label)}</span><span><i data-fx-group-count>{len(group_families):,}</i> {outcome_word}</span></summary>'
                f'<div class="evidence-sign-results">{"".join(descriptive_family_row(family) for family in group_families)}</div>'
                '</details>'
            )
        axis_label = readable_term(axis).title()
        axis_sections.append(
            '<details class="evidence-axis-group" data-fx-group>'
            f'<summary class="evidence-axis-heading"><span>{esc(axis_label)}</span><span><i data-fx-group-count>{len(axis_families):,}</i> result groups</span></summary>'
            f'{"".join(sign_sections)}</details>'
        )
    rendered_statistic_ids = [
        statistic_id
        for family in families
        for statistic_id in FAMILY_PRIMARY_STATISTIC_IDS.get(str(family.get("analysis_id") or ""), [])
    ] + list(UNASSIGNED_STATISTIC_IDS)
    if (
        len(rendered_statistic_ids) != len(set(rendered_statistic_ids))
        or set(rendered_statistic_ids) != set(STATISTIC_CONTEXT_BY_ID)
    ):
        raise RuntimeError("The evidence library must render every reported number exactly once.")
    unassigned_section = build_unassigned_statistic_section(UNASSIGNED_STATISTIC_IDS)
    method_note = (EVIDENCE_SYNTHESIS.get("release") or {}).get("method_note") or ""
    method_details = (
        '<details class="evidence-method-note"><summary>How result groups were constructed</summary>'
        f'<p>{esc(method_note)}</p></details>' if public_value(method_note) else ""
    )
    return f'''<div class="fx-wrap study-results-panel" data-item-label="result groups" data-global-sign-filter="true">
  <div class="fx-intro">Result groups and their exact reported numbers are organized together: axis &rarr; semiology &rarr; outcome &rarr; study &rarr; reported number. Values remain source-specific and are not pooled. Ungrouped values remain under <strong>General or contextual results</strong>. {method_details}</div>
  <div class="fx-tools"><input type="text" class="fx-search" placeholder="Search signs, outcomes, populations, values, or sources&hellip;"><button type="button" class="fx-reset">Reset</button><div class="fx-btns">{"".join(buttons)}</div></div>
  <div class="evidence-result-counts"><span class="fx-count"></span><span class="fx-secondary-count"></span></div>
  <div class="fx-table syn-global-table">{"".join(axis_sections)}{unassigned_section}</div>
</div>'''


def build_reviewed_findings_panel(corpus):
    """Render every reviewed finding once in reader-facing language."""
    role_color = {
        "PRIMARY_RESULT": "#1a7a4a", "REVIEW_SYNTHESIS": "#2471a3",
        "CITED_STUDY_RESTATEMENT": "#6b7280", "EDUCATIONAL_STATEMENT": "#8e44ad",
        "GUIDELINE_RECOMMENDATION": "#0a7a8a", "CASE_OBSERVATION": "#95691a",
    }
    rows, counts = [], {}
    for source in corpus["sources"]:
        for row in source["findings"]:
            role = row["evidence_role"]
            counts[role] = counts.get(role, 0) + 1
            statistics = finding_statistics(row)
            if len(statistics) == 1:
                row_value = statistic_value(statistics[0])
            elif statistics:
                row_value = f'{len(statistics)} reported results'
            else:
                row_value = ""
            citation = public_value(row.get("citation"))
            sign_ids = list(OrderedDict.fromkeys(
                str(sign_id) for sign_id in [
                    *(row.get("exact_sign_ids") or []), *(row.get("related_sign_ids") or []),
                ]
            ))
            search = " ".join(str(x or "") for x in [
                row["source_term"], row["claim"], statistic_search_text(row), row["citation"], row["locators"],
                row["evidence_text"], row["population"], row["laterality_localization"],
                source["source_file"], ROLE_LABEL.get(role, ""),
            ]).lower().replace('"', "")
            measure = statistic_block(row)
            rows.append(
                f'<div class="fx-row evidence-row" data-metric="{role}" data-sign-ids="{esc("|".join(sign_ids))}" data-fq="{esc(search)}">'
                f'<span class="fx-m" style="background:{role_color.get(role,"#6b7280")}">{esc(ROLE_LABEL.get(role,"Source information"))}</span>'
                f'<span class="fx-ph">{esc(row["source_term"])}<span class="fx-reg">{esc(row["phase"])}</span></span>'
                f'<span class="fx-val">{esc(row_value)}</span>'
                f'<span class="fx-src">{f"<strong>{esc(citation)}</strong><br>" if citation else ""}{esc(source["source_file"])}<br>{esc(row["locators"] or "Locator not reported")}</span>'
                f'<span class="fx-q"><strong>{esc(row["claim"])}</strong>{measure}</span>'
                '<details class="fx-context"><summary>Source and study details</summary>'
                f'<div><strong>Relevant source text:</strong> {esc(row["evidence_text"])}</div>'
                f'<div><strong>Who was studied:</strong> {esc(row["population"])}</div>'
                f'<div><strong>What the finding suggests:</strong> {esc(row["laterality_localization"])}</div>'
                f'<div><strong>Important cautions:</strong> {esc(row["limitations"])}</div>'
                f'{cited_source_line(row)}'
                '</details></div>')
    total = len(rows)
    buttons = [f'<button class="fxb on" data-f="all">All <i>{total}</i></button>']
    for role in ROLE_LABEL:
        if counts.get(role):
            buttons.append(f'<button class="fxb" data-f="{role}">{esc(ROLE_LABEL[role])} <i>{counts[role]}</i></button>')
    return f'''<div class="fx-wrap" data-item-label="findings" data-global-sign-filter="true">
  <div class="fx-intro">Every reviewed finding appears once with its claim, exact citation when catalogued, source filename, locator, and expandable source context.</div>
  <div class="fx-tools"><input type="text" class="fx-search" placeholder="Search signs, claims, measures, sources, locators&hellip;"><button type="button" class="fx-reset">Reset</button><div class="fx-btns">{"".join(buttons)}</div></div>
  <div class="fx-count"></div>
  <div class="fx-table">{chr(10).join(rows)}</div>
</div>'''


def build_evidence_library(corpus):
    accounting = corpus["integration_accounting"]
    finding_count = accounting["public_ledger_findings"]
    family_count = len(DESCRIPTIVE_FAMILIES)
    statistic_count = accounting["source_reported_statistics"]
    source_count = accounting["source_reports"]
    return f'''<div class="lib evidence-library">
<details class="lib-details evidence-library-details">
  <summary><span>Reviewed Evidence Library</span><span class="evidence-library-summary">{finding_count:,} findings &middot; {family_count:,} study-result groups &middot; {statistic_count:,} reported numbers &middot; {source_count} source files</span></summary>
  <div class="evidence-library-body">
    <p class="evidence-library-overview">Two connected views of the same canonical ledger. Study results contain their exact reported numbers, citations, and source locations; no new pooling, mapping, or interpretation is added.</p>
    <div class="evidence-view-tabs" role="tablist" aria-label="Reviewed evidence views">
      <button type="button" class="evidence-view-tab on" role="tab" aria-selected="true" data-evidence-view="findings">Reviewed findings <i>{finding_count:,}</i></button>
      <button type="button" class="evidence-view-tab" role="tab" aria-selected="false" data-evidence-view="studies">Study results <i>{family_count:,} groups &middot; {statistic_count:,} numbers</i></button>
    </div>
    <section class="evidence-view-panel" role="tabpanel" data-evidence-panel="findings" data-fragment="fragments/reviewed-findings.html"><div class="lazy-fragment">Loading reviewed findings&hellip;</div></section>
    <section class="evidence-view-panel" role="tabpanel" data-evidence-panel="studies" data-fragment="fragments/study-results.html" hidden><div class="lazy-fragment">Open this view to load study results.</div></section>
  </div>
</details>
</div>'''

deferred_fragments["reviewed-findings.html"] = build_reviewed_findings_panel(CORPUS)
deferred_fragments["study-results.html"] = build_descriptive_family_panel(DESCRIPTIVE_FAMILIES)
evidence_library_html = defer_details_body(build_evidence_library(CORPUS), "evidence-library.html")


# ---------- Evidence-weighted lateralization and localization ----------
# Every eligible card is derived from the current ledger. One canonical work
# contributes once per sign/axis, and a work's weight is divided across multiple
# reported targets so a manuscript cannot inflate itself by listing more places
# or directions. Source-specific numeric estimates remain unpooled.
def build_weighted_evidence(cards):
    axis_config = {
        "LATERALIZATION": {
            "tab": "Lateralization", "reported": "Direction reported",
            "nonassoc": "Does not lateralize", "missing": "No lateralization relationship reported",
            "placeholder": "Search semiology, direction, summary, or manuscript…",
        },
        "LOCALIZATION": {
            "tab": "Localization", "reported": "Region reported",
            "nonassoc": "Does not localize", "missing": "No localization relationship reported",
            "placeholder": "Search semiology, region, summary, or manuscript…",
        },
    }
    reference_weight = {
        "SEEG": 1.50, "STEREO_EEG": 1.50, "SURGICAL_OUTCOME": 1.50,
        "INTRACRANIAL_EEG": 1.35, "ECOG": 1.35, "VIDEO_EEG": 1.20,
        "IMAGING": 1.15, "LESION_LOCATION": 1.15, "ICTAL_EEG": 1.10,
        "CLINICAL_SEMIOLOGY": 1.00, "NOT_REPORTED": 1.00,
    }
    location_labels = {
        "REG:TEMPORAL": "Temporal", "REG:FRONTAL": "Frontal",
        "REG:PARIETAL": "Parietal", "REG:OCCIPITAL": "Occipital",
        "REG:INSULAR": "Insular", "REG:LIMBIC": "Limbic",
        "REG:DEEP_SUBCORTICAL": "Deep/Subcortical",
        "REG:MULTIREGIONAL_PROPAGATION": "Multiregional/Propagation",
    }

    def status_of(card):
        return str(card.get("pattern_status") or card.get("pattern_label") or "NOT_REPORTED").upper()

    def count_value(card, field, fallback):
        try:
            value = card.get(field)
            return int(value) if value is not None else int(fallback)
        except (TypeError, ValueError):
            return int(fallback)

    def unique_strings(values):
        return list(OrderedDict.fromkeys(str(value) for value in values or [] if str(value or "").strip()))

    def display_sign_label(value):
        return re.sub(r"^Focal\s+", "", public_value(value, "Unnamed semiology"), flags=re.IGNORECASE)

    def flatten_values(value):
        if isinstance(value, dict):
            flattened = []
            for item in value.values():
                flattened.extend(flatten_values(item))
            return flattened
        if isinstance(value, (list, tuple, set)):
            flattened = []
            for item in value:
                flattened.extend(flatten_values(item))
            return flattened
        text = str(value or "").strip()
        if text.startswith("[") and text.endswith("]"):
            try:
                return flatten_values(json.loads(text))
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        return [text] if text else []

    def lateral_target(value):
        raw = public_value(value)
        token = re.sub(r"[^a-z0-9]+", " ", raw.casefold()).strip()
        if not token:
            return None
        if "non dominant" in token or "nondominant" in token:
            return ("nondominant", "Non-dominant hemisphere")
        if token == "dominant" or "dominant hemisphere" in token:
            return ("dominant", "Dominant hemisphere")
        if "contralateral" in token or token == "contra" or "opposite side" in token:
            return ("contra", "Contralateral")
        if "ipsilateral" in token or token == "ipsi" or "same side" in token:
            return ("ipsi", "Ipsilateral")
        if token in {"bilateral", "bilateral hemisphere", "bilateral hemispheres"}:
            return ("bilateral", "Bilateral")
        if token in {"right", "right hemisphere"}:
            return ("right", "Right hemisphere")
        if token in {"left", "left hemisphere"}:
            return ("left", "Left hemisphere")
        if token in {"nonlat", "non lateralizing", "non lateralising", "does not lateralize", "does not lateralise"}:
            return ("nonassoc", "Does not lateralize")
        return None

    def localization_target(value):
        raw = public_value(value)
        if not raw:
            return None
        if raw in location_labels:
            return (raw, location_labels[raw])
        token = raw.upper().replace("-", "_").replace(" ", "_")
        if token in location_labels:
            return (token, location_labels[token])
        if raw.startswith("REG:"):
            return (raw, readable_term(raw[4:]).title())
        return None

    def target_from_value(axis, value):
        return lateral_target(value) if axis == "LATERALIZATION" else localization_target(value)

    def nonassociation_target(axis):
        return ("nonassoc", axis_config[axis]["nonassoc"])

    def card_targets(card, axis):
        status = status_of(card)
        if status in {"NON_LATERALIZING", "NON_LOCALIZING"}:
            return [nonassociation_target(axis)]
        targets = []
        for relationship in card.get("primary_relationships") or []:
            dispositions = [str(value).upper() for value in relationship.get("evidence_dispositions") or []]
            if dispositions and "SUPPORTED_EVIDENCE" not in dispositions:
                continue
            for value in relationship.get("targets") or []:
                if isinstance(value, dict):
                    value = value.get("label") or value.get("name") or value.get("target")
                target = target_from_value(axis, value)
                if target and target not in targets:
                    targets.append(target)
        return targets

    def axis_targets_for_finding(finding_ref, axis):
        row = FINDING_AXIS_BY_REF.get((finding_ref, axis)) or {}
        if str(row.get("disposition") or "").upper() != "SUPPORTED_EVIDENCE":
            return []
        values = (
            row.get("normalized_values") or []
            if axis == "LATERALIZATION"
            else row.get("region_ids") or []
        )
        targets = []
        for value in values:
            target = target_from_value(axis, value)
            if target and target not in targets:
                targets.append(target)
        return targets

    def family_targets_for_work(card, axis, work_id):
        targets = []
        sign_id = str(card.get("sign_id") or "")
        for family in DESCRIPTIVE_FAMILIES_BY_SIGN.get(sign_id, []):
            if str(family.get("axis") or "").upper() != axis:
                continue
            if work_id not in [str(value) for value in family.get("source_work_ids") or []]:
                continue
            axis_targets = family.get("axis_targets") or {}
            if isinstance(axis_targets, dict):
                values = (
                    axis_targets.get("normalized_values") or []
                    if axis == "LATERALIZATION"
                    else axis_targets.get("region_ids") or []
                )
                values = values or axis_targets.get("source_native_targets") or []
            else:
                values = axis_targets
            for value in flatten_values(values):
                target = target_from_value(axis, value)
                if target and target not in targets:
                    targets.append(target)
        return targets

    def source_groups(card):
        groups = OrderedDict()

        def group_for(source):
            source_file = public_value(source.get("source_file"), "Source file not named")
            return groups.setdefault(source_file, {"source": source, "findings": OrderedDict(), "statistics": OrderedDict()})

        for finding_ref in unique_strings(card.get("supporting_finding_refs")):
            context = ledger_by_ref.get(finding_ref) or {}
            source, finding = context.get("source") or {}, context.get("finding") or {}
            if source or finding:
                group_for(source)["findings"][finding_ref] = finding
        for statistic_id in unique_strings(card.get("supporting_statistic_ids")):
            context = STATISTIC_CONTEXT_BY_ID.get(statistic_id) or {}
            source, finding, statistic = context.get("source") or {}, context.get("finding") or {}, context.get("statistic") or {}
            if source or statistic:
                group_for(source)["statistics"][statistic_id] = (finding, statistic)
        return groups

    def work_groups(card):
        groups = OrderedDict()

        def group_for(source):
            key = public_value(source.get("work_id")) or public_value(source.get("source_sha256")) or public_value(source.get("source_file"))
            return groups.setdefault(key, {"source": source, "finding_refs": OrderedDict(), "statistics": OrderedDict()})

        for finding_ref in unique_strings(card.get("supporting_finding_refs")):
            context = ledger_by_ref.get(finding_ref) or {}
            source, finding = context.get("source") or {}, context.get("finding") or {}
            if source or finding:
                group_for(source)["finding_refs"][finding_ref] = finding
        for statistic_id in unique_strings(card.get("supporting_statistic_ids")):
            context = STATISTIC_CONTEXT_BY_ID.get(statistic_id) or {}
            source, finding, statistic = context.get("source") or {}, context.get("finding") or {}, context.get("statistic") or {}
            if source or statistic:
                group_for(source)["statistics"][statistic_id] = (finding, statistic)
        return groups

    def exact_denominator(statistic):
        for key in ("denominator_numeric", "denominator"):
            value = statistic.get(key)
            if value is None:
                continue
            try:
                number = float(str(value).replace(",", "").strip())
                if number > 0:
                    return number
            except (TypeError, ValueError):
                continue
        return None

    def work_weight(card, axis, work_id, group):
        standards = []
        for family in DESCRIPTIVE_FAMILIES_BY_SIGN.get(str(card.get("sign_id") or ""), []):
            if str(family.get("axis") or "").upper() != axis:
                continue
            if work_id not in [str(value) for value in family.get("source_work_ids") or []]:
                continue
            standards.extend(flatten_values(family.get("reference_standard")))
        normalized_standards = [
            str(value).upper().replace("-", "_").replace(" ", "_")
            for value in standards if str(value or "").strip()
        ]
        standard_multiplier = max(
            [reference_weight.get(value, 1.0) for value in normalized_standards] or [1.0]
        )
        denominators = [
            exact_denominator(statistic) for _finding, statistic in group["statistics"].values()
        ]
        denominators = [value for value in denominators if value is not None]
        denominator = max(denominators) if denominators else None
        size_multiplier = min(2.0, 1.0 + math.log10(denominator) / 2.0) if denominator else 1.0
        return standard_multiplier * size_multiplier, standard_multiplier, size_multiplier, denominator

    def weighted_distribution(card, axis):
        status = status_of(card)
        fallback_targets = card_targets(card, axis)
        totals, works_by_target, contributions = OrderedDict(), {}, []
        for work_id, group in work_groups(card).items():
            targets = []
            if status in {"NON_LATERALIZING", "NON_LOCALIZING"}:
                targets = [nonassociation_target(axis)]
            else:
                for finding_ref in group["finding_refs"]:
                    for target in axis_targets_for_finding(finding_ref, axis):
                        if target not in targets:
                            targets.append(target)
                if not targets:
                    targets = family_targets_for_work(card, axis, work_id)
                if not targets and len(fallback_targets) == 1:
                    targets = fallback_targets
            if not targets:
                continue
            weight, standard_multiplier, size_multiplier, denominator = work_weight(card, axis, work_id, group)
            divided_weight = weight / len(targets)
            for key, label in targets:
                totals.setdefault(key, {"key": key, "label": label, "weight": 0.0, "first": len(totals)})
                totals[key]["weight"] += divided_weight
                works_by_target.setdefault(key, set()).add(work_id)
            contributions.append({
                "work_id": work_id, "weight": weight, "targets": targets,
                "standard_multiplier": standard_multiplier, "size_multiplier": size_multiplier,
                "denominator": denominator,
            })
        total_weight = sum(item["weight"] for item in totals.values())
        if not total_weight:
            return {"targets": [], "total_weight": 0.0, "work_count": 0, "contributions": []}
        preferred_order = {target[0]: index for index, target in enumerate(fallback_targets)}
        targets = sorted(
            totals.values(),
            key=lambda item: (
                item["key"] == "nonassoc",
                -item["weight"],
                preferred_order.get(item["key"], 10**6),
                item["first"],
            ),
        )
        for item in targets:
            item["share"] = item["weight"] / total_weight * 100.0
            item["work_count"] = len(works_by_target.get(item["key"], set()))
        return {
            "targets": targets, "total_weight": total_weight,
            "work_count": len(contributions), "contributions": contributions,
        }

    def source_manuscript_label(source_file, group):
        findings = list(group["findings"].values())
        statistics = list(group["statistics"].values())
        citation = next((public_value(row.get("citation")) for row in findings if public_value(row.get("citation"))), "")
        if not citation:
            citation = next((public_value(stat.get("citation")) for _finding, stat in statistics if public_value(stat.get("citation"))), "")
        citation_text = re.sub(r"^\s*(?:REF(?:ERENCE)?S?\s*)?(?:\[[^\]]+\]\s*)+", "", citation, flags=re.IGNORECASE)
        return citation if re.search(r"[A-Za-z]", citation_text) else source_file

    def source_manuscript_sort_key(source_file, group):
        label = source_manuscript_label(source_file, group)
        label = re.sub(r"^\s*(?:REF(?:ERENCE)?S?\s*)?(?:\[[^\]]+\]\s*)+", "", label, flags=re.IGNORECASE)
        label = re.sub(r"^\s*References?\s+[0-9,\sand\-–—]+:\s*", "", label, flags=re.IGNORECASE)
        return label.casefold()

    def source_block(source_file, group):
        source = group["source"]
        findings = list(group["findings"].values())
        statistics = list(group["statistics"].values())
        manuscript = source_manuscript_label(source_file, group)
        finding_rows = []
        for finding in findings:
            label = public_value(finding.get("source_term"), "Reviewed finding")
            claim = public_value(finding.get("claim"))
            locator = public_value(finding.get("locators"), "Source location not stated")
            finding_rows.append(
                '<li><span class="lr-item-title">'+esc(label)+'</span>'
                +(f'<span class="lr-item-text">{esc(claim)}</span>' if claim and claim != label else '')
                +f'<span class="lr-locator">{esc(locator)}</span></li>'
            )
        statistic_rows = []
        for finding, statistic in statistics:
            value = statistic_value(statistic) or "Reported result"
            endpoint = public_value(finding.get("source_term"), "Study result")
            locator = public_value(statistic.get("source_locator")) or public_value(finding.get("locators"), "Source location not stated")
            ratio = statistic_ratio(statistic)
            context = " · ".join(filter(None, [
                public_context_value(statistic.get("population")),
                public_context_value(statistic.get("subgroup")),
                public_context_value(statistic.get("phase") or finding.get("phase")),
            ]))
            statistic_rows.append(
                '<li><span class="lr-stat-value">'+esc(value)+'</span>'
                +f'<span class="lr-item-title">{esc(endpoint)}</span>'
                +f'<span class="lr-stat-meta">{esc(metric_label(statistic.get("metric_type")))}{(" · n/N " + esc(ratio)) if ratio else ""}{(" · " + esc(context)) if context else ""}</span>'
                +f'<span class="lr-locator">{esc(locator)}</span></li>'
            )
        counts = []
        if findings:
            counts.append(f'{len(findings)} finding{"s" if len(findings) != 1 else ""}')
        if statistics:
            counts.append(f'{len(statistics)} reported result{"s" if len(statistics) != 1 else ""}')
        source_context = public_value(source.get("source_report_methods_population"))
        return (
            '<details class="lr-source"><summary><span>'+esc(manuscript)+'</span>'
            +f'<span>{esc(" · ".join(counts) or "Linked evidence")}</span></summary>'
            +f'<div class="lr-source-file">{esc(source_file)}</div>'
            +(f'<div class="lr-source-context">{esc(source_context)}</div>' if source_context else '')
            +(f'<div class="lr-source-section"><strong>Reviewed findings</strong><ul>{"".join(finding_rows)}</ul></div>' if finding_rows else '')
            +(f'<div class="lr-source-section"><strong>Reported study results</strong><ul>{"".join(statistic_rows)}</ul></div>' if statistic_rows else '')
            +'</details>'
        )

    def family_target_labels(family, axis):
        targets = family.get("axis_targets") or {}
        if isinstance(targets, dict):
            values = targets.get("normalized_values") if axis == "LATERALIZATION" else targets.get("region_ids")
            values = values or targets.get("source_native_targets") or []
        else:
            values = targets
        labels = []
        for value in flatten_values(values):
            target = target_from_value(axis, value)
            label = target[1] if target else public_context_value(value)
            if label and label not in labels:
                labels.append(label)
        return labels

    def family_block(card, axis, statistic_ids):
        families = []
        for family in DESCRIPTIVE_FAMILIES_BY_SIGN.get(str(card.get("sign_id") or ""), []):
            if str(family.get("axis") or "").upper() != axis:
                continue
            family_statistics = set(unique_strings(family.get("statistic_ids")))
            family_statistics.update(
                str(item.get("statistic_id")) for item in family.get("exact_estimates") or [] if item.get("statistic_id")
            )
            if statistic_ids and family_statistics and not statistic_ids.intersection(family_statistics):
                continue
            families.append(family)
        if not families:
            return ""
        rows = []
        for family in families:
            title = " / ".join(family_target_labels(family, axis)) or public_context_value(family.get("endpoint"), "Source-defined result group")
            proportion = family.get("descriptive_proportion_summary") or {}
            minimum, maximum, median = proportion.get("minimum"), proportion.get("maximum"), proportion.get("median")
            observed = "Source-defined values retained separately"
            if minimum is not None and maximum is not None:
                if float(minimum) == float(maximum):
                    observed = f'Observed proportion {float(minimum) * 100:.1f}%'
                else:
                    observed = f'Observed proportion range {float(minimum) * 100:.1f}–{float(maximum) * 100:.1f}%'
                    if median is not None:
                        observed += f' (median {float(median) * 100:.1f}%)'
            context = " · ".join(filter(None, [
                public_context_value(family.get("subgroup")),
                public_context_value(family.get("comparator")),
                public_context_value(family.get("analysis_unit")),
            ]))
            input_count = count_value(family, "input_count", len(family.get("statistic_ids") or []))
            work_count = count_value(family, "source_work_count", 0)
            rows.append(
                '<div class="lr-family"><strong>'+esc(title)+'</strong>'
                +f'<span>{esc(observed)}</span>'
                +(f'<small>{esc(context)}</small>' if context else '')
                +f'<small>{work_count} manuscript{"s" if work_count != 1 else ""} · {input_count} reported result{"s" if input_count != 1 else ""} · not pooled</small></div>'
            )
        return (
            '<details class="lr-families"><summary>Source-defined result groups '
            +f'<span>{len(rows)}</span></summary><div>{"".join(rows)}</div></details>'
        )

    def share_text(value):
        return f"{value:.1f}".rstrip("0").rstrip(".")

    def evidence_support_points(analysis):
        work_count = analysis["work_count"]
        total_weight = analysis["total_weight"]
        if work_count >= 3 or total_weight >= 6:
            return 3
        if work_count >= 2 or total_weight >= 3:
            return 2
        return 1

    def target_color(axis, target):
        if target["key"] == "nonassoc":
            return "#6b7280"
        if axis == "LATERALIZATION":
            return latcolor.get(target["key"], "#0e9db0")
        return region_colors.get(target["label"], "#0e9db0")

    def bucket_of(card):
        status = status_of(card)
        if status in {"NON_LATERALIZING", "NON_LOCALIZING"}:
            return "nonassoc"
        if status in {"CONTEXT_SUBTYPE_DEPENDENT", "GENUINELY_MIXED"}:
            return "mixed"
        return "association"

    def card_row(card, axis, analysis, order):
        source_label = public_value(card.get("preferred_label"), "Unnamed semiology")
        label = display_sign_label(source_label)
        sign_id = str(card.get("sign_id") or "")
        finding_refs = unique_strings(card.get("supporting_finding_refs"))
        statistic_ids = set(unique_strings(card.get("supporting_statistic_ids")))
        manuscripts = analysis["work_count"]
        findings = count_value(card, "supported_finding_count", len(finding_refs))
        statistics = len(statistic_ids)
        groups = source_groups(card)
        summary = public_value(card.get("plain_summary"), "Reviewed evidence summary available below.")
        nonassociation_only = all(target["key"] == "nonassoc" for target in analysis["targets"])
        chips, segments = [], []
        for index, target in enumerate(analysis["targets"]):
            is_nonassoc = target["key"] == "nonassoc"
            prefix = ("" if nonassociation_only else "Also reported: ") if is_nonassoc else ("Predominant: " if index == 0 else "Also reported: ")
            chip_class = "lr-nonassoc" if is_nonassoc else ("lr-primary" if index == 0 else "lr-secondary")
            percent = share_text(target["share"])
            color = target_color(axis, target)
            chip_value = "" if nonassociation_only else f" <b>{percent}%</b>"
            chips.append(
                f'<span class="lr-direction {chip_class}" style="color:{color};border-color:{color}">{esc(prefix + target["label"])}{chip_value}</span>'
            )
            segments.append(
                f'<span class="{chip_class}" style="width:{target["share"]:.4f}%;background:{color};opacity:{1 if index == 0 else .56}" '
                f'title="{esc(target["label"])}: {percent}% of weighted evidence"></span>'
            )
        ordered_sources = sorted(
            groups.items(),
            key=lambda item: source_manuscript_sort_key(item[0], item[1]),
        )
        source_html = "".join(source_block(source_file, group) for source_file, group in ordered_sources)
        exceptions = card.get("exceptions") or []
        if isinstance(exceptions, str):
            exceptions = [exceptions]
        exception_rows = [esc(value) for value in exceptions if isinstance(value, str) and value.strip()]
        exception_html = (
            '<details class="lr-exceptions"><summary>Documented exceptions '
            +f'<span>{len(exception_rows)}</span></summary><ul>'
            +"".join(f'<li>{value}</li>' for value in exception_rows)+'</ul></details>'
            if exception_rows else ""
        )
        weighted_units = f'{analysis["total_weight"]:.2f}'.rstrip("0").rstrip(".")
        source_count = len(groups)
        leading_target = analysis["targets"][0]
        reliability = -1.0 if nonassociation_only else leading_target["share"]
        reliability_text = share_text(reliability)
        reliability_color = target_color(axis, leading_target)
        reliability_marker = min(98.0, max(2.0, reliability))
        support_points = evidence_support_points(analysis)
        support_pips = "".join(
            f'<i class="{"on" if index < support_points else "off"}"></i>'
            for index in range(3)
        )
        reliability_html = (
            '<span class="lr-reliability lr-no-directional" style="--rel-color:#6b7280" '
            f'title="All weighted evidence reports no {"lateralizing" if axis == "LATERALIZATION" else "localizing"} association; this is not a directional reliability score.">'
            '<span class="lr-no-directional-label">No directional estimate</span>'
            f'<span class="lr-cert">{support_pips}</span></span>'
            if nonassociation_only else
            f'<span class="lr-reliability" style="--rel-color:{reliability_color};--rel-position:{reliability_marker:.2f}%" '
            f'title="{esc(leading_target["label"])}: {reliability_text}% predominant weighted share; {support_points} evidence-support point{"s" if support_points != 1 else ""}">'
            '<span class="lr-rel-track"><i class="lr-rel-fill"></i><i class="lr-rel-dot"></i></span>'
            f'<b class="lr-rel-value">{reliability_text}%</b><span class="lr-cert">{support_pips}</span></span>'
        )
        sources_html = (
            '<details class="lr-sources"><summary>Evidence by contributing manuscript '
            +f'<span>{source_count}</span></summary><p>Alphabetical by manuscript citation.</p><div>{source_html}</div></details>'
            if source_html else '<p class="lr-empty">No source linkage is available for this synthesis record.</p>'
        )
        search_text = " ".join([
            source_label, label, summary, " ".join(target["label"] for target in analysis["targets"]),
            " ".join(groups.keys()), axis,
        ]).casefold()
        return (
            f'<details class="lr-row" data-sign-id="{esc(sign_id)}" data-bucket="{bucket_of(card)}" data-name="{esc(label.casefold())}" '
            f'data-weight="{analysis["total_weight"]:.6f}" data-reliability="{reliability:.6f}" data-cert="{support_points}" data-manuscripts="{manuscripts}" '
            f'data-findings="{findings}" data-statistics="{statistics}" data-order="{order}" '
            f'data-search="{esc(search_text)}">'
            '<summary class="lr-row-head"><span class="lr-name">'+esc(label)+'</span>'
            +f'<span class="lr-directions">{"".join(chips)}</span>'
            +reliability_html
            +f'<span class="lr-evidence-counts"><b>{analysis["work_count"]}</b> weighted manuscript{"s" if analysis["work_count"] != 1 else ""} <i>·</i> <b>{findings}</b> direct finding{"s" if findings != 1 else ""} <i>·</i> <b>{statistics}</b> reported result{"s" if statistics != 1 else ""}</span></summary>'
            +'<div class="lr-row-body">'
            +'<div class="lr-weighted"><div><strong>Weighted evidence distribution</strong>'
            +f'<span>{weighted_units} weighted units across {analysis["work_count"]} manuscript{"s" if analysis["work_count"] != 1 else ""}</span></div>'
            +f'<div class="lr-weightbar">{"".join(segments)}</div></div>'
            +f'<p class="lr-summary">{esc(summary)}</p>'
            +family_block(card, axis, statistic_ids)
            +exception_html
            +sources_html
            +f'<div class="lr-linkage-note">{source_count} linked manuscript record{"s" if source_count != 1 else ""}; source-defined numbers remain separate and are not pooled.</div>'
            +'</div></details>'
        )

    def axis_panel(axis):
        config = axis_config[axis]
        axis_cards = [card for card in cards if str(card.get("axis") or "").upper() == axis]
        weighted_cards, omitted_cards = [], []
        for card in axis_cards:
            analysis = weighted_distribution(card, axis)
            if analysis["targets"]:
                weighted_cards.append((card, analysis))
            else:
                omitted_cards.append(card)
        weighted_cards.sort(key=lambda item: (
            bucket_of(item[0]) == "nonassoc",
            -item[1]["targets"][0]["share"],
            -evidence_support_points(item[1]), -item[1]["work_count"],
            public_value(item[0].get("preferred_label")).casefold(),
        ))
        rows = "".join(card_row(card, axis, analysis, order) for order, (card, analysis) in enumerate(weighted_cards))
        association_count = sum(bucket_of(card) == "association" for card, _analysis in weighted_cards)
        mixed_count = sum(bucket_of(card) == "mixed" for card, _analysis in weighted_cards)
        nonassoc_count = sum(bucket_of(card) == "nonassoc" for card, _analysis in weighted_cards)
        omitted_rows = "".join(
            f'<span class="lr-unreported-sign" data-search="{esc((display_sign_label(card.get("preferred_label")) + " " + status_of(card)).casefold())}">'
            f'{esc(display_sign_label(card.get("preferred_label")))}</span>'
            for card in sorted(omitted_cards, key=lambda row: public_value(row.get("preferred_label")).casefold())
        )
        hidden = "" if axis == "LATERALIZATION" else " hidden"
        return f'''<section class="weighted-axis-panel" data-axis-panel="{axis}"{hidden}>
<div class="lr-wrap" data-axis="{axis}">
  <div class="lr-intro"><strong>{len(weighted_cards):,} evidence-weighted summaries.</strong> Each canonical manuscript contributes once per sign and axis. Its weight is divided across multiple reported targets. Percentages show the distribution of weighted evidence, not pooled sensitivity, specificity, or diagnostic accuracy.</div>
  <details class="lr-method"><summary>How weighting works</summary><div>
    <p>Reference-standard multipliers preserve the prior atlas method: SEEG or surgical outcome 1.50; intracranial EEG 1.35; video-EEG 1.20; imaging or lesion location 1.15; ictal EEG 1.10; other or unreported 1.00. An exact denominator adds the existing capped size factor (maximum 2.00). Restatements and overlap records remain visible but do not add another independent manuscript.</p>
    <p>When one manuscript reports several directions or regions, its single weight is divided among them. Incompatible study percentages remain source-specific and are never pooled.</p>
  </div></details>
  <div class="lr-tools">
    <input class="lr-search" type="search" placeholder="{esc(config["placeholder"])}" aria-label="Search {axis.casefold()} evidence">
    <button type="button" class="lr-reset">Reset</button>
    <div class="lr-filters" role="group" aria-label="Filter {axis.casefold()} summaries">
      <button type="button" class="lr-filter on" data-filter="all">All weighted <i>{len(weighted_cards):,}</i></button>
      <button type="button" class="lr-filter" data-filter="association">{esc(config["reported"])} <i>{association_count:,}</i></button>
      <button type="button" class="lr-filter" data-filter="mixed">Mixed or context-specific <i>{mixed_count:,}</i></button>
      <button type="button" class="lr-filter" data-filter="nonassoc">{esc(config["nonassoc"])} <i>{nonassoc_count:,}</i></button>
    </div>
    <label class="lr-sort-label">Order
      <select class="lr-sort"><option value="page">Match page organization</option><option value="reliability">Reliability (directional share) &darr;</option><option value="certainty">Evidence support (certainty) &darr;</option><option value="name">Semiology A&ndash;Z</option><option value="manuscripts">Most manuscripts</option><option value="statistics">Most reported results</option></select>
    </label>
  </div>
  <div class="lr-visual-legend"><span><strong>Directional reliability</strong> = predominant directional weighted share</span><span class="lr-legend-scale"><i>0%</i><i>50%</i><i>100%</i></span><span class="lr-legend-pips"><i class="on"></i><i class="on"></i><i class="on"></i> evidence support (manuscripts &amp; weight)</span><span class="lr-neutral-note">Nonassociation is shown separately, not as a 100% directional score.</span></div>
  <div class="lr-visible-count"></div>
  <div class="lr-list">{rows}</div>
  <details class="lr-unreported">
    <summary>Not included in the weighted distribution <span class="lr-unreported-count">{len(omitted_cards):,}</span></summary>
    <p>{esc(config["missing"])} or the reviewed evidence does not contain a usable source-level target. These signs remain visible and are not treated as evidence for absence.</p>
    <div class="lr-unreported-grid">{omitted_rows}</div>
  </details>
</div></section>'''

    tabs = "".join(
        f'<button type="button" class="weighted-axis-tab{" on" if axis == "LATERALIZATION" else ""}" '
        f'data-axis-tab="{axis}" aria-selected="{"true" if axis == "LATERALIZATION" else "false"}">{config["tab"]}</button>'
        for axis, config in axis_config.items()
    )
    return f'''<details class="frontpage-fold reliability-fold">
<summary>Weighted-Evidence Summary</summary>
<div class="weighted-evidence-shell">
  <div class="weighted-axis-tabs" role="tablist" aria-label="Weighted evidence axis">{tabs}</div>
  {"".join(axis_panel(axis) for axis in axis_config)}
</div>
</details>'''


meta_fold = build_weighted_evidence(SYNTHESIS_CARDS)


# ---------- Descriptive statistics: sensitivity by seizure-onset group ----------
# Auto-generated from meta_analysis.json["sensitivity"], which the meta engine computes
# from the ledger's tagged frequency-within-a-group findings. Tag another finding in the
# ledger and this section, the cards, and the coverage counts all update on the next build.
def build_sensitivity_report(meta):
    sens = (meta or {}).get("sensitivity")
    if not sens or not sens.get("by_card"):
        return ""
    name_by_id = {d["id"]: d["sign"] for d in data}
    cov = sens["coverage"]
    trows = []
    for cid, blk in sorted(sens["by_card"].items(), key=lambda x: int(x[0])):
        nm = name_by_id.get(int(cid), f"#{cid}")
        for i, c in enumerate(blk["conditions"]):
            s0 = c["sources"][0]
            val = (f'{c["mean"]:g}%' + (f' <span class="ds-rng">({c["low"]:g}&#8211;{c["high"]:g})</span>' if c["k"] > 1 else ''))
            srcs = "; ".join(sorted({s["cite"] for s in c["sources"]}))
            signcell = (f'<td class="ds-sign" rowspan="{len(blk["conditions"])}">{esc(nm)}</td>' if i == 0 else "")
            trows.append(
                f'<tr>{signcell}<td class="ds-cond">{esc(c["cond"])}</td>'
                f'<td class="ds-val">{val}</td><td class="ds-k">{c["k"]}</td>'
                f'<td class="ds-src" title="{esc(s0.get("quote",""))}">{esc(srcs)}</td></tr>')
    return f'''<details class="frontpage-fold ds-fold">
<summary>Descriptive statistics &mdash; sensitivity by seizure-onset group ({cov["cards_with_sensitivity"]} signs)</summary>
<div class="ds-wrap">
  <p class="ds-method">{esc(sens["method"])}</p>
  <div class="ds-tablewrap"><table class="ds-table">
    <thead><tr><th>Sign</th><th>Onset group &mdash; as the source defined it</th><th>Sensitivity &mdash; P(sign&nbsp;|&nbsp;onset&nbsp;group)</th><th>k</th><th>Source(s)</th></tr></thead>
    <tbody>{"".join(trows)}</tbody>
  </table></div>
  <p class="ds-spec">&#9888;&#65039; <strong>Specificity is not computed.</strong> {esc(sens["note_specificity"])}</p>
</div>
</details>'''
sens_report_fold = build_sensitivity_report(META)


import base64

def _b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# ---------- Interactive Brodmann map ----------
# All curation (areas, geometry, label positions, sign->area rules) comes from
# data/brodmann_map.json via brain_atlas; this only renders it.
def build_brain(signs):
    tiles = {}
    for aid, info in BA.AREAS.items():
        tiles[aid] = {"label": info["label"], "name": info["name"], "lobe": info["lobe"],
                      "bas": info["bas"], "buried": bool(info.get("buried")),
                      "views": BA.views_with(aid), "signs": []}
    _evrank = {"I": 0, "II": 1, "III": 2}
    unplaced = []
    index = {}          # the same mapping read backwards: sign -> its areas + why
    for d in signs:
        m = SIGN_LOCATION_BY_ID[d["id"]]
        index[str(d["id"])] = {"n": d["sign"], "areas": m["areas"], "via": m["via"],
                               "rule": m["rule"], "lc": d.get("latcode", "nonlat"),
                               "loc": d.get("loc", "")}
        al = m["areas"]
        if not al:
            unplaced.append(d["sign"]); continue
        for a in al:
            tiles[a]["signs"].append({
                "id": d["id"], "n": d["sign"], "ph": d["phase"], "lc": d.get("latcode", "nonlat"),
                "lat": d.get("lat", ""), "ev": d.get("evid", "III"), "rg": d["region"],
                "loc": d.get("loc", "")})
    for t in tiles.values():
        t["signs"].sort(key=lambda s: (_evrank.get(s["ev"], 3), s["n"]))

    first_view = "lateral"

    def render_view(name):
        """
        A view is the reference plate with its numerals on top. Nothing else is
        drawn over the cortex: the area outlines are in the data but no longer
        rendered, because an outline traced off a plate never fits the anatomy
        well enough to sit on it, and it got in the way of the numbers. Only a
        numeral is highlighted, and only a numeral is clickable.
        """
        v = BA.VIEWS[name]
        vw, vh = v["viewBox"][2], v["viewBox"][3]
        mirrored = v.get("mirror")

        img = ""
        if v.get("image"):
            f = os.path.join(BA.ASSETS, v["image"]["file"])
            if os.path.exists(f):
                i = v["image"]
                img = (f'<image class="brain-photo" x="{i["x"]}" y="{i["y"]}" width="{i["w"]}" '
                       f'height="{i["h"]}" preserveAspectRatio="none" '
                       f'href="data:image/jpeg;base64,{_b64(f)}"/>')

        labels, rlabels = [], []
        for area in v["areas"]:
            aid = area["id"]
            lab = area.get("label")
            if not lab:
                continue
            lx, ly = lab
            n = len(tiles.get(aid, {}).get("signs", []))
            txt = BA.AREAS[aid]["label"]
            cls = "ba-num ba-num-sm" if len(txt) > 2 else "ba-num"
            r = 13 if len(txt) <= 2 else 15

            def marks(x, mx):
                # disc first, numeral second: the disc is the hit target and the
                # highlight, and has to sit behind the digits it belongs to
                return (f'<circle class="ba-hit" data-tile="{aid}" data-n="{n}" '
                        f'data-lobe="{BA.AREAS[aid]["lobe"]}" cx="{x}" cy="{ly}" r="{r}" '
                        f'data-mx="{mx}" tabindex="0" role="button" '
                        f'aria-label="Brodmann area {txt}">'
                        f'<title>{esc(BA.AREAS[aid]["name"])}</title></circle>'
                        f'<text class="{cls}" data-tile="{aid}" x="{x}" y="{ly}" '
                        f'data-mx="{mx}">{txt}</text>')

            labels.append(marks(lx, vw - lx))
            if mirrored:
                rlabels.append(marks(vw - lx, lx))

        if mirrored:
            lab_g = (f'<g class="ba-labels lab-L">{"".join(labels)}</g>'
                     f'<g class="ba-labels lab-R">{"".join(rlabels)}</g>')
            orient = (f'<text class="brain-orient" x="{vw/2}" y="{v["image"]["y"]-14:.0f}" '
                      f'text-anchor="middle">anterior</text>')
        else:
            lab_g = f'<g class="ba-labels">{"".join(labels)}</g>'
            orient = (f'<text class="brain-orient" x="150" y="{vh-24}" text-anchor="middle" '
                      f'data-mx="{vw-150}">anterior</text>')

        # the plate lives in its own group so the hemisphere switch can mirror it
        # with a plain SVG transform attribute, which every browser honours
        visible = " show" if name == first_view else ""
        return (f'<svg class="brain-svg{visible}" data-view="{name}" viewBox="0 0 {vw} {vh}" role="group" '
                f'aria-label="{name.capitalize()} surface, Brodmann areas">'
                f'<g class="plate">{img}</g>{lab_g}{orient}</svg>')

    views_html = "".join(render_view(v) for v in BA.VIEWS)
    view_btns = "".join(
        f'<button class="seg-b{" active" if v == first_view else ""}" data-view="{v}" role="tab" '
        f'aria-selected="{"true" if v == first_view else "false"}">{v.capitalize()}</button>'
        for v in BA.VIEWS)

    buried = [a for a, i in BA.AREAS.items() if i.get("buried")]
    buried_chips = "".join(
        f'<button class="deep-chip" data-tile="{t}"><span class="dc-lab">{BA.AREAS[t]["label"]}</span>'
        f'<span class="dc-name">{esc(BA.AREAS[t]["name"].split("(")[0].strip())}</span>'
        f'<span class="dc-n">{len(tiles[t]["signs"])}</span></button>' for t in buried)

    note = ""

    payload = ("<script>const BRAIN_TILES=" + json.dumps(tiles, separators=(",", ":")) +
               ";const BRAIN_SIGNS=" + json.dumps(index, separators=(",", ":")) + ";</script>")
    return payload + f'''<details class="frontpage-fold brain-fold" open>
<summary>Brodmann map &mdash; where each semiology localizes</summary>
<div class="brain-card">
  <div class="brain-bar">
    <div class="seg" role="tablist" aria-label="Surface view">{view_btns}</div>
    <div class="seg seg-hemi" role="group" aria-label="Hemisphere">
      <button class="seg-b active" data-hemi="L">Left</button>
      <button class="seg-b" data-hemi="R">Right</button>
    </div>
    <label class="brain-shade"><input type="checkbox" id="brain-density"> Shade by density</label>
    <span class="dens-key"><span class="dk-n">0</span><i class="dk-bar"></i>
      <span class="dk-n" id="dk-max"></span>&nbsp;signs per area</span>
  </div>
  <div class="brain-grid">
    <div class="brain-stage">
      <div class="brain-views">{views_html}</div>
      <div class="brain-caption"><span id="brain-hover">Select a numbered area</span>{note}</div>
      <div class="deep-row"><span class="deep-lab">Not on a surface &mdash;</span>{buried_chips}</div>
    </div>
    <aside class="brain-panel" id="brain-panel" aria-live="polite">
      <div class="bp-empty">
        <div class="bp-empty-mark">BA</div>
        <p>Tap any Brodmann number to see the semiology this atlas localizes there &mdash; with its phase, lateralizing value and evidence tier.</p>
        <p class="bp-hint">Or go the other way: open any sign below and press <strong>Show on map</strong> to light up every area it localizes to. Areas with no shading carry no sign in the current dataset.</p>
      </div>
      <div class="bp-body" hidden>
        <div class="bp-head">
          <div class="bp-num" id="bp-num">4</div>
          <div class="bp-id"><h3 id="bp-name">Primary motor cortex</h3>
            <div class="bp-meta"><span class="bp-lobe" id="bp-lobe"></span><span id="bp-count"></span>
              <button class="bp-back" id="bp-back" hidden></button></div></div>
          <button class="bp-close" id="bp-close" aria-label="Close">&times;</button>
        </div>
        <div class="bp-list" id="bp-list"></div>
      </div>
      <div class="bp-trace" hidden>
        <div class="bp-head">
          <div class="bp-num bp-tnum" aria-hidden="true">&#9678;</div>
          <div class="bp-id"><h3 id="bt-name">Sign</h3>
            <div class="bp-meta"><span id="bt-count"></span></div></div>
          <button class="bp-close" id="bt-close" aria-label="Close">&times;</button>
        </div>
        <div class="bp-list" id="bt-list"></div>
        <p class="bp-why" id="bt-why"></p>
      </div>
    </aside>
  </div>
</div>
</details>'''

brain_fold = build_brain(data)

forest_html = f'''<div class="forest-wrap">
  <div class="forest-card">
    <div class="forest-head">
      <h2>Lateralizing reliability of the classic bedside signs</h2>
      <p>How often each sign points to the correct <em>side</em>, from Loddenkemper &amp; Kotagal 2005 (<em>Epilepsy &amp; Behavior</em>), Table&nbsp;1 &mdash; a single primary review compiling named source studies. These figures answer <strong>which hemisphere</strong> (and how reliably), not which lobe. The most dependable are near-deterministic: forced version, unilateral dystonic posturing, and hemifield visual auras are contralateral in ~100%, while postictal dysphasia is dominant-hemisphere in 100%. Bar length = % lateralizing in the stated direction; small grey text = reported frequency in the cited population.</p>
    </div>
    <div class="forest-body">{lateral_svg}</div>
    <div class="forest-legend">
      <span><span class="fl-dot" style="background:{latcolor['contra']}"></span>Contralateral</span>
      <span><span class="fl-dot" style="background:{latcolor['ipsi']}"></span>Ipsilateral</span>
      <span><span class="fl-dot" style="background:{latcolor['dominant']}"></span>Dominant hemisphere</span>
      <span><span class="fl-dot" style="background:{latcolor['nondominant']}"></span>Non-dominant hemisphere</span>
    </div>
  </div>
</div>'''

callout_html = '''<div class="callout"><div class="callout-inner">
<span class="tag">Framework</span><strong>Semiology is a network phenomenon, not a single spot.</strong> The French anatomo-electro-clinical school (Bancaud, Talairach, Chauvel, Bartolomei, McGonigal) frames each sign as the output of a dynamically interacting network that unfolds over time &mdash; the epileptogenic zone plus its early-spread network &mdash; rather than one fixed &ldquo;symptomatogenic&rdquo; locus. Read the chronology of a seizure (aura &#8594; first objective sign &#8594; sequence) as a trajectory through connected nodes; the <em>order</em> of signs often localizes better than any one sign alone (Chauvel &amp; McGonigal 2014; Bartolomei/Isnard SEEG guidelines 2018). A practical corollary from Marashly 2015: when two independent &ldquo;reliable&rdquo; signs point the same way, lateralization approaches 100%.
</div></div>'''

# wrap the reliability chart and the framework callout in collapsed-by-default
# disclosures so they don't wall off the sign index on landing
forest_fold = ('<details class="frontpage-fold">\n'
    '<summary>Lateralizing-reliability chart &mdash; Loddenkemper &amp; Kotagal 2005</summary>\n'
    + forest_html + '\n</details>')
callout_fold = ('<details class="frontpage-fold">\n'
    '<summary>Framework &mdash; semiology as a dynamic network</summary>\n'
    + callout_html + '\n</details>')

papers_html = "\n".join(
    f'<div class="paper"><div class="p-cite">{esc(c)}</div><div class="p-jrnl">{esc(j)}</div>'
    f'<div class="p-title">{esc(t)}</div><div class="p-contrib">{esc(k)}</div></div>'
    for (c,j,t,k) in PAPERS)
n_ev_signs = sum(1 for d in data if d.get("_ev"))

CSS = r"""
:root{
  --navy:#12234a; --navy2:#1a2f5e; --teal:#0e9db0; --teal-d:#0a7a8a;
  --bg:#f5f7fb; --panel:#ffffff; --ink:#1a1d2e; --muted:#6b7280; --line:#e3e8f0; --line2:#eef1f6;
}

/* ---------- BRODMANN MAP ---------- */
.brain-fold>summary{background:#e9eef6;border-color:#d8e0ec}
.brain-card{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:14px 16px 12px}
.brain-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.seg{display:inline-flex;background:#f1f4f9;border:1px solid var(--line);border-radius:8px;padding:2px;gap:2px}
.seg-b{border:none;background:none;font-family:inherit;font-size:.76rem;font-weight:700;color:#6d7789;
  padding:5px 13px;border-radius:6px;cursor:pointer;transition:all .13s}
.seg-b:hover{color:var(--navy)}
.seg-b.active{background:#fff;color:var(--navy);box-shadow:0 1px 3px rgba(15,30,61,.13)}
.seg-hemi .seg-b.active{color:var(--teal-d)}
.brain-shade{display:inline-flex;align-items:center;gap:6px;font-size:.72rem;font-weight:600;color:var(--muted);
  cursor:pointer;margin-left:auto;user-select:none}
.brain-shade input{accent-color:var(--teal);width:14px;height:14px}

.brain-grid{display:grid;grid-template-columns:1fr;gap:14px}
@media(min-width:900px){.brain-grid{grid-template-columns:minmax(0,1.55fr) minmax(290px,1fr);gap:20px}}
.brain-stage{min-width:0}
.brain-views{position:relative;display:flex;justify-content:center;align-items:center;min-height:270px}
.brain-svg{display:none;width:100%;height:auto;max-height:400px;overflow:visible}
.brain-svg.show{display:block}
.brain-svg[data-view="dorsal"],.brain-svg[data-view="ventral"]{max-height:430px}

/* classic Brodmann-plate convention: dashed boundaries inside a lobe,
   solid boundaries between lobes, every area carrying its number */
.brain-photo{pointer-events:none}
/* label editor (opt-in via #edit-labels) */
/* The disc is the drag handle. It used to be the glyph, wearing a fat white
   stroke as its fingertip target — which, once the disc became the numeral's
   background, painted straight over the digits and left white blobs. */
body.lbledit .ba-hit{pointer-events:all;cursor:grab;r:19px;
  /* stop the browser panning the page when a finger drags a numeral */
  touch-action:none;-webkit-user-select:none;user-select:none}
body.lbledit .ba-num{pointer-events:none}
body.lbledit .ba-hit:hover{fill:#cdeff5;stroke:var(--teal-d)}
body.lbledit .ba-hit.drag{cursor:grabbing;fill:var(--teal);stroke:var(--teal-d);stroke-width:2}
body.lbledit .ba-hit.drag+.ba-num{fill:#fff}
#lbl-out{width:100%;height:70px;margin-top:7px;font-family:'SF Mono',Consolas,monospace;
  font-size:.62rem;border:1px solid var(--line);border-radius:6px;padding:5px}
.lbl-editor{position:fixed;right:12px;bottom:12px;z-index:400;background:rgba(255,255,255,.97);
  border:1px solid var(--line);border-radius:12px;padding:9px 11px;backdrop-filter:blur(6px);
  box-shadow:0 8px 28px rgba(15,30,61,.20);font-size:.76rem;width:290px;line-height:1.4}
.lbl-editor.folded .le-body{display:none}
.le-row{display:flex;gap:6px;align-items:center;margin-top:6px}
.le-row:first-child{margin-top:0}
#le-pick{flex:1;min-width:0;border:1px solid var(--line);border-radius:7px;padding:7px 8px;
  font-family:inherit;font-size:.8rem;background:#fff;color:var(--ink)}
#le-fold{flex:0 0 auto;width:30px;height:30px;border:1px solid var(--line);background:#fff;
  border-radius:7px;cursor:pointer;font-size:.7rem;color:var(--navy)}
.lbl-editor.folded #le-fold{transform:rotate(180deg)}
.le-modes{display:flex;gap:3px;background:#f1f4f9;border:1px solid var(--line);
  border-radius:8px;padding:2px;margin-top:6px}
.le-modes button{flex:1;border:none;background:none;border-radius:6px;padding:6px 4px;
  font-family:inherit;font-size:.72rem;font-weight:700;color:#6d7789;cursor:pointer}
.le-modes button.on{background:#fff;color:var(--teal-d);box-shadow:0 1px 3px rgba(15,30,61,.13)}
.le-zoom button{flex:0 0 auto;min-width:34px;height:30px;border:1px solid var(--line);
  background:#fff;border-radius:7px;font-size:.9rem;font-weight:700;color:var(--navy);cursor:pointer}
.le-zoom #le-fit{font-size:.72rem;padding:0 9px}
#le-z{flex:1;text-align:center;font-family:'SF Mono',Consolas,monospace;font-size:.72rem;color:var(--muted)}
.lbl-editor .le-row:last-child button{flex:1;border:1px solid var(--line);background:#fff;
  border-radius:7px;padding:6px 8px;font-family:inherit;font-size:.73rem;font-weight:700;
  color:var(--navy);cursor:pointer}
.lbl-editor .le-row:last-child button:hover{border-color:var(--teal);color:var(--teal-d)}
#lbl-read{margin-top:6px;font-family:'SF Mono',Consolas,monospace;font-size:.7rem;color:var(--teal-d)}
.ba-hit.edit-sel{fill:#bdeef6!important;stroke:var(--teal-d)!important;stroke-width:2!important}
/* focus mode: only the numeral being moved is live; the others fade back so they
   neither block the pointer nor clutter the anatomy underneath */
body.lbledit.focusing .ba-num,body.lbledit.focusing .ba-hit{opacity:.12;pointer-events:none;transition:opacity .15s}
body.lbledit.focusing .ba-num.edit-sel{opacity:1}
body.lbledit.focusing .ba-hit.edit-sel{opacity:1;pointer-events:all}
body.lbledit .ba-num,body.lbledit .ba-hit{transition:opacity .15s}
#le-done{background:var(--teal)!important;border-color:var(--teal-d)!important;color:#fff!important}
body.lbl-place .brain-svg{cursor:crosshair}
/* D-pad: thumb-reachable, translucent, never covers the middle of the figure */
.dpad{position:fixed;left:12px;bottom:12px;z-index:400;display:grid;width:132px;height:132px;
  grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(3,1fr);gap:3px;
  background:rgba(255,255,255,.86);backdrop-filter:blur(6px);border:1px solid var(--line);
  border-radius:14px;padding:5px;box-shadow:0 8px 28px rgba(15,30,61,.20);touch-action:none}
.dpad button{border:1px solid var(--line);background:#fff;border-radius:9px;font-size:.9rem;
  color:var(--navy);cursor:pointer;touch-action:none;-webkit-user-select:none;user-select:none}
.dpad button:active{background:var(--teal);color:#fff;border-color:var(--teal-d)}
.dpad [data-d="u"]{grid-area:1/2}.dpad [data-d="l"]{grid-area:2/1}
.dpad [data-d="c"]{grid-area:2/2;border:none;background:none;color:#c3cedd;font-size:.6rem;cursor:default}
.dpad [data-d="r"]{grid-area:2/3}.dpad [data-d="d"]{grid-area:3/2}
@media(max-width:760px){
  .lbl-editor{left:8px;right:8px;bottom:8px;width:auto}
  .dpad{left:auto;right:10px;bottom:190px;width:118px;height:118px}
}
#lbl-out{width:100%;height:70px;margin-top:7px;font-family:'SF Mono',Consolas,monospace;
  font-size:.62rem;border:1px solid var(--line);border-radius:6px;padding:5px}
.lbl-editor{position:fixed;right:14px;bottom:14px;z-index:400;background:#fff;
  border:1px solid var(--line);border-radius:10px;padding:11px 13px;
  box-shadow:0 8px 28px rgba(15,30,61,.20);font-size:.76rem;max-width:290px;line-height:1.45}
.lbl-editor h4{font-size:.8rem;color:var(--navy);margin-bottom:4px}
.lbl-editor p{color:var(--muted);margin-bottom:7px}
.lbl-editor code{background:#eef2f7;border-radius:3px;padding:0 4px;font-size:.72rem}
.lbl-editor .row{display:flex;gap:6px;margin-top:7px}
.lbl-editor button{flex:1;border:1px solid var(--line);background:#fff;border-radius:6px;
  padding:5px 8px;font-family:inherit;font-size:.74rem;font-weight:700;color:var(--navy);cursor:pointer}
.lbl-editor button:hover{border-color:var(--teal);color:var(--teal-d);background:#f0fbfd}
#lbl-read{font-family:'SF Mono',Consolas,monospace;font-size:.72rem;color:var(--teal-d)}
/* Nothing is drawn over the cortex. The disc behind each numeral is the whole
   of the interface: it is the hit target, and it is the highlight. */
.ba-hit{fill:rgba(255,255,255,.80);stroke:#b9c4d4;stroke-width:1;pointer-events:all;
  cursor:pointer;transition:fill .13s,stroke .13s}
.ba-hit.has{fill:rgba(255,255,255,.92);stroke:#8d9cb2}
.ba-hit:hover{fill:#cdeff5;stroke:var(--teal-d)}
.ba-hit.sel{fill:var(--teal);stroke:var(--teal-d);stroke-width:2}
.ba-hit:focus{outline:none}
.ba-hit:focus-visible{stroke:var(--teal-d);stroke-width:2.5;stroke-dasharray:3 3}
/* Density ramp: blue -> red, lightness strictly decreasing (0.87 -> 0.47 OKLCH)
   so it reads as magnitude rather than as two colours, and never through green.
   Counts are skewed (median 4, max 30), so the scale is square-rooted; the key
   prints the real counts at both ends and the midpoint. */
.brain-card.dens .ba-hit{fill:var(--dens,rgba(255,255,255,.85));stroke:rgba(30,42,61,.35)}
.brain-card.dens .ba-num{fill:var(--densink,#1e2a3d)}
.brain-card.dens .ba-hit.sel{fill:var(--teal);stroke:var(--teal-d)}
.brain-card.dens .ba-hit.sel+.ba-num{fill:#fff}
.dens-key{display:none;align-items:center;gap:7px;margin-left:auto;font-size:.66rem;color:var(--muted)}
.brain-card.dens .dens-key{display:inline-flex}
.dk-bar{width:104px;height:9px;border-radius:5px;display:block;border:1px solid rgba(30,42,61,.18);
  background:linear-gradient(90deg,#b3daff 0%,#adb6fa 4%,#b48edf 16%,#bb66b0 36%,#b93c71 64%,#ac011a 100%)}
.dk-n{font-variant-numeric:tabular-nums;font-weight:700;color:#5a6478}
.ba-num{font-family:'Segoe UI',Arial,sans-serif;font-size:15px;font-weight:800;fill:#1e2a3d;
  text-anchor:middle;dominant-baseline:central;pointer-events:all;cursor:pointer;user-select:none}
.ba-num.has{fill:#0d1626}
.ba-num.sel{fill:#fff;stroke:none}
.ba-num-sm{font-size:12px}
.ba-num-ins{font-size:13px;letter-spacing:.08em;fill:var(--teal-d)}
.ba-num-ins.sel{fill:#fff}
.brain-orient{font-size:12px;fill:#aab3c2;letter-spacing:.1em;text-transform:uppercase;pointer-events:none}
.brain-svg .lab-R{display:none}
.brain-svg.show-R .lab-R{display:block}
.brain-svg.show-R .lab-L{display:none}

.brain-caption{text-align:center;font-size:.76rem;color:var(--muted);margin-top:6px;min-height:19px}
#brain-hover{font-weight:600;color:#54627a}
.brain-note{display:block;font-size:.68rem;font-style:italic;opacity:.8;margin-top:2px}
.deep-row{display:flex;align-items:center;gap:6px;flex-wrap:wrap;justify-content:center;margin-top:9px;
  padding-top:9px;border-top:1px dashed var(--line)}
.deep-lab{font-size:.66rem;font-weight:700;color:#9aa3b2;text-transform:uppercase;letter-spacing:.05em}
.deep-chip{display:inline-flex;align-items:center;gap:6px;border:1px dashed #b9cfd8;background:#f7fcfd;
  border-radius:20px;padding:3px 10px;font-family:inherit;font-size:.72rem;cursor:pointer;transition:all .12s}
.deep-chip:hover{border-color:var(--teal);background:#eef9fc}
.deep-chip.sel{background:var(--teal);border-style:solid;border-color:var(--teal-d)}
.deep-chip.sel .dc-lab,.deep-chip.sel .dc-name{color:#fff}
.deep-chip.sel .dc-n{background:rgba(255,255,255,.28);color:#fff}
.dc-lab{font-weight:800;color:var(--teal-d)}
.dc-name{color:#5a6478}
.dc-n{background:#e6eef2;color:#6b7280;border-radius:9px;padding:0 6px;font-size:.64rem;font-weight:700}

.brain-panel{border:1px solid var(--line);border-radius:10px;background:#fbfcfe;min-height:200px;
  display:flex;flex-direction:column;overflow:hidden}
.bp-empty{padding:26px 20px;text-align:center;color:var(--muted);font-size:.8rem;line-height:1.55;margin:auto}
.bp-empty-mark{font-size:1.6rem;font-weight:800;color:#dbe3ec;letter-spacing:.08em;margin-bottom:6px}
.bp-hint{font-size:.7rem;font-style:italic;opacity:.75;margin-top:7px}
.bp-head{display:flex;align-items:flex-start;gap:11px;padding:12px 13px 10px;border-bottom:1px solid var(--line2);background:#fff}
.bp-num{flex:0 0 auto;min-width:44px;height:44px;padding:0 8px;border-radius:9px;background:var(--teal);color:#fff;
  font-size:1.15rem;font-weight:800;display:flex;align-items:center;justify-content:center}
.bp-id{flex:1;min-width:0}
.bp-id h3{font-size:.88rem;font-weight:700;color:var(--navy);line-height:1.3}
.bp-meta{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin-top:3px;font-size:.68rem;color:var(--muted)}
.bp-lobe{background:#eef2f7;border-radius:4px;padding:1px 7px;font-weight:700;color:#5a6478}
.bp-back{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border:none;
  background:#fdf3e4;color:#8a5209;border-radius:4px;padding:1px 7px;font-family:inherit;
  font-size:.65rem;font-weight:700;cursor:pointer}
.bp-back:hover{background:#f6e2c4}
.bp-close{margin-left:auto;border:none;background:none;font-size:1.3rem;line-height:1;color:#b6bfcd;cursor:pointer;padding:0 2px}
.bp-close:hover{color:var(--navy)}
.bp-list{overflow-y:auto;max-height:330px;padding:5px 0}
.bp-row{width:100%;display:flex;align-items:flex-start;gap:8px;background:none;border:none;border-bottom:1px solid var(--line2);
  padding:8px 13px;text-align:left;font-family:inherit;cursor:pointer;transition:background .11s}
.bp-row:hover{background:#f0f8fa}
.bp-row:last-child{border-bottom:none}
.bp-row.off{opacity:.42}
.bp-rname{flex:1;font-size:.79rem;font-weight:600;color:var(--navy);line-height:1.35}
.bp-chips{display:flex;gap:4px;align-items:center;flex-wrap:wrap;margin-top:3px}
.bp-chip{font-size:.6rem;font-weight:800;padding:1px 5px;border-radius:3px;letter-spacing:.02em}
.bp-side{font-size:.65rem;color:var(--muted);font-style:italic;margin-top:2px;display:block}
.bp-ev{flex:0 0 auto;width:19px;height:19px;border-radius:5px;color:#fff;font-size:.62rem;font-weight:800;
  display:flex;align-items:center;justify-content:center;margin-top:1px}

/* ---- the map read backwards: one sign, every area it localizes to ----
   amber, so a traced set never reads as the teal "selected area" state */
.ba-hit.trace{fill:#f2a63c;stroke:#8a5209;stroke-width:2}
.brain-card.dens .ba-hit.trace{fill:#f2a63c}
.ba-num.trace{fill:#3d2200}
.deep-chip.trace{background:#fdf3e4;border-style:solid;border-color:#e0a75a}
.deep-chip.trace .dc-lab{color:#8a5209}
.brain-card.tracing .ba-num:not(.trace),.brain-card.tracing .ba-hit:not(.trace){opacity:.22}
.ba-num{transition:opacity .15s}
.seg-b.has-trace::after{content:"";display:inline-block;width:6px;height:6px;border-radius:50%;
  background:#e08a1e;margin-left:5px;vertical-align:middle}
.bp-tnum{background:#e08a1e}
.bp-why{padding:9px 13px 11px;border-top:1px solid var(--line2);font-size:.67rem;color:var(--muted);line-height:1.5}
.bp-why b{color:#5a6478;font-weight:700}
.bt-row{width:100%;display:flex;align-items:center;gap:9px;background:none;border:none;
  border-bottom:1px solid var(--line2);padding:8px 13px;text-align:left;font-family:inherit;
  cursor:pointer;transition:background .11s}
.bt-row:hover{background:#fdf6ec}
.bt-row:last-child{border-bottom:none}
.bt-num{flex:0 0 auto;min-width:30px;height:26px;padding:0 6px;border-radius:6px;background:#fdf3e4;
  color:#8a5209;border:1px solid #e8c79a;font-size:.76rem;font-weight:800;
  display:flex;align-items:center;justify-content:center}
.bt-name{flex:1;font-size:.76rem;color:var(--navy);line-height:1.35}
.bt-where{display:block;font-size:.63rem;color:var(--muted);font-style:italic;margin-top:1px}
.bt-n{flex:0 0 auto;background:#eef2f7;color:#6b7280;border-radius:9px;padding:1px 7px;font-size:.63rem;font-weight:700}

/* the same mapping, surfaced on the sign card itself */
.d-map .d-value{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.ba-chips{display:flex;gap:4px;flex-wrap:wrap}
.ba-chip{border:1px solid #e8c79a;background:#fdf3e4;color:#8a5209;border-radius:5px;padding:1px 7px;
  font-family:inherit;font-size:.72rem;font-weight:800;cursor:pointer;transition:all .12s}
.ba-chip:hover{background:#f6e2c4;border-color:#cf9a4d}
.ba-chip.bc-deep{border-style:dashed}
.map-jump{border:1px solid var(--line);background:#fff;color:var(--navy);border-radius:6px;padding:2px 9px;
  font-family:inherit;font-size:.7rem;font-weight:700;cursor:pointer;transition:all .12s}
.map-jump:hover{border-color:#e0a75a;color:#8a5209;background:#fdf8f1}
@media(max-width:760px){
  .brain-card{padding:11px 10px}
  .brain-svg{max-height:320px}
  /* numerals are in SVG user units, so scale them up for the small canvas */
  .ba-num{font-size:20px}
  .ba-num-sm{font-size:16px}
  .ba-hit{r:18px}
  body.lbledit .ba-hit{r:26px}
  .bp-list{max-height:430px}
  .brain-bar{gap:7px}
  .brain-shade{margin-left:0;width:100%}
}
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;background:var(--bg);color:var(--ink);font-size:15px;line-height:1.5}

/* ---------- TITLE ---------- */
.site-header{background:linear-gradient(135deg,var(--navy) 0%,var(--navy2) 55%,#0a4a5a 100%);color:#fff;padding:16px 26px 14px}
.site-header h1{font-size:1.5rem;font-weight:800;letter-spacing:.01em;margin-bottom:5px}
.site-header p{font-size:.82rem;opacity:.92;max-width:80ch;line-height:1.5}
.edu-inline{color:#ffe4a3;font-weight:600}
.edu-note{margin-top:12px;display:inline-flex;align-items:center;gap:8px;background:rgba(255,220,120,.16);border:1px solid rgba(255,220,120,.4);color:#ffe9b0;font-size:.76rem;font-weight:600;padding:5px 12px;border-radius:20px}
.header-meta{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
.header-badge{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.24);border-radius:5px;padding:3px 10px;font-size:.72rem;font-weight:600}

/* ---------- STICKY HEAD ---------- */
.sticky-head{position:sticky;top:0;z-index:100;background:#fff;box-shadow:0 2px 10px rgba(15,30,61,.09);border-bottom:1px solid var(--line)}
/* The toolbar is a third of a landscape phone. It collapses out of the way to a
   puck that stays put while the page scrolls, and brings everything back on a tap. */
.tb-state{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
.tb-state:checked~.sticky-head{display:none}
.tb-state:checked~.tb-fab{display:inline-flex}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.tb-toggle{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;
  border:1px solid var(--line);background:#fff;color:#9aa3b2;border-radius:8px;font-size:.6rem;
  cursor:pointer;flex:0 0 auto;font-family:inherit}
.tb-toggle:hover{border-color:var(--teal);color:var(--teal-d);background:#f0fbfd}
body.tb-collapsed .sticky-head{display:none}
.tb-fab{display:none;position:fixed;top:9px;right:11px;z-index:220;width:42px;height:42px;
  align-items:center;justify-content:center;border-radius:50%;border:1px solid var(--line);
  background:rgba(255,255,255,.95);backdrop-filter:blur(7px);font-size:1rem;cursor:pointer;
  box-shadow:0 4px 16px rgba(15,30,61,.20)}
.tb-fab:hover{border-color:var(--teal)}
body.tb-collapsed .tb-fab{display:inline-flex}
.tb-dot{position:absolute;top:5px;right:5px;width:9px;height:9px;border-radius:50%;
  background:var(--teal);border:2px solid #fff;display:none}
/* a collapsed toolbar must never hide the fact that a filter is on */
body.filtering .tb-dot{display:block}
.region-nav{display:flex;gap:6px;overflow-x:auto;padding:6px 14px;-webkit-overflow-scrolling:touch;border-bottom:1px solid var(--line2);scrollbar-width:thin}
.region-nav::-webkit-scrollbar{height:5px}
.region-nav::-webkit-scrollbar-thumb{background:#cfd6e2;border-radius:3px}
.pill{flex:0 0 auto;display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);background:#fff;color:var(--navy);border-radius:20px;padding:4px 11px;font-size:.75rem;font-weight:700;cursor:pointer;transition:all .12s;white-space:nowrap}
.pill:hover{border-color:var(--teal);color:var(--teal-d);background:#f0fbfd}
.pill-count{background:#eef1f6;color:var(--muted);border-radius:10px;padding:0 6px;font-size:.66rem;font-weight:700}

.toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:7px 14px}
.search-wrap{position:relative;display:flex;gap:5px;align-items:center;flex:1 1 330px;max-width:560px}
.search-icon{position:absolute;left:9px;top:50%;transform:translateY(-50%);color:#9aa3b2;font-size:.8rem;pointer-events:none}
#search-input{min-width:90px;flex:1 1 auto;width:auto;border:1px solid var(--line);border-radius:7px;padding:7px 10px 7px 30px;font-size:.84rem;color:var(--ink);outline:none;background:#fff}
#search-input:focus{border-color:var(--teal);box-shadow:0 0 0 3px rgba(14,157,176,.13)}
.search-btn{border:1px solid var(--teal-d);background:var(--teal);color:#fff;border-radius:7px;padding:7px 11px;font-size:.76rem;font-weight:800;cursor:pointer}
.search-btn:hover{background:var(--teal-d)}
.search-clear{border-color:var(--line);background:#fff;color:var(--navy)}
.search-clear:hover{border-color:var(--teal);background:#f0fbfd;color:var(--teal-d)}
.browse-mode-field{display:flex;flex-direction:column;gap:2px;min-width:170px}
.browse-mode-field select{border:1px solid var(--line);border-radius:6px;padding:5px 8px;font-size:.8rem;color:var(--ink);background:#fff;outline:none}
.browse-mode-field select:focus{border-color:var(--teal)}
body.alt-browse .region-nav{display:none}
.filter-toggle{display:none;align-items:center;gap:6px;border:1px solid var(--line);background:#fff;color:var(--navy);border-radius:7px;padding:8px 12px;font-size:.84rem;font-weight:700;cursor:pointer}
.filter-toggle .chev{font-size:.6rem;transition:transform .15s}
.filter-toggle.open .chev{transform:rotate(180deg)}
.filter-panel{display:flex;gap:9px;flex-wrap:wrap;align-items:center}
.filter-field{display:flex;flex-direction:column;gap:2px}
.ctrl-label{font-size:.6rem;font-weight:800;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.filter-field select{border:1px solid var(--line);border-radius:6px;padding:5px 8px;font-size:.8rem;color:var(--ink);background:#fff;outline:none}
.filter-field select:focus{border-color:var(--teal)}
.tool-actions{display:flex;gap:6px;align-items:center;margin-left:auto;flex-wrap:wrap}
.act-btn{border:1px solid var(--line);background:#fff;color:var(--navy);border-radius:7px;padding:5px 10px;font-size:.74rem;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px;transition:all .12s}
.act-btn:hover{border-color:var(--teal);color:var(--teal-d);background:#f0fbfd}
.quiz-toggle{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);border-radius:7px;padding:4px 10px;font-size:.74rem;font-weight:700;color:var(--navy);cursor:pointer;user-select:none}
.quiz-toggle input{display:none}
.quiz-switch{width:34px;height:18px;border-radius:10px;background:#cbd3e0;position:relative;transition:background .15s;flex:0 0 auto}
.quiz-switch::after{content:"";position:absolute;top:2px;left:2px;width:14px;height:14px;border-radius:50%;background:#fff;transition:transform .15s;box-shadow:0 1px 2px rgba(0,0,0,.25)}
.quiz-toggle input:checked + .quiz-switch{background:var(--teal)}
.quiz-toggle input:checked + .quiz-switch::after{transform:translateX(16px)}
#result-count{font-size:.68rem;color:var(--muted);font-style:italic;margin-left:auto;padding:0 2px;white-space:nowrap}

/* ---------- MAIN ---------- */
main{padding:16px 20px 48px;max-width:1180px;margin:0 auto}
/* A landscape tablet puts an overlay scrollbar - and the collapsed-toolbar puck -
   straight over the right edge of the text. Hold the content off both. */
main,.frontpage-fold,.callout{
  padding-left:max(20px,env(safe-area-inset-left));
  padding-right:max(20px,env(safe-area-inset-right))}
@media (min-width:761px){
  body.tb-collapsed main,body.tb-collapsed .frontpage-fold,body.tb-collapsed .callout{
    padding-right:max(62px,calc(env(safe-area-inset-right) + 46px))}
}
.region-section{margin-bottom:11px;scroll-margin-top:118px}
.region-toggle{width:100%;display:flex;align-items:center;gap:9px;background:var(--rc);color:#fff;border:none;border-left:3px solid color-mix(in srgb,var(--rc) 60%,#000);border-radius:6px;padding:6px 12px;font-size:.74rem;font-weight:800;letter-spacing:.06em;cursor:pointer;text-align:left}
.region-chev{font-size:.66rem;transition:transform .18s;opacity:.8}
.region-section.collapsed .region-chev{transform:rotate(-90deg)}
.region-name{flex:1}
.region-count{font-size:.64rem;font-weight:700;opacity:.9;background:rgba(255,255,255,.2);padding:1px 7px;border-radius:9px;min-width:18px;text-align:center}
.region-body{padding:7px 0 2px}
.region-section.collapsed .region-body{display:none}

#semiology-view[hidden],#region-view[hidden],#region-order-field[hidden],#source-sign-store{display:none!important}
.browse-note{font-size:.76rem;line-height:1.5;color:#526077;background:#f4f8fb;border:1px solid var(--line);border-radius:8px;padding:8px 11px;margin:0 0 10px}
.browse-section{margin-bottom:8px}
.browse-toggle{width:100%;display:flex;align-items:center;gap:9px;background:var(--navy);color:#fff;border:none;border-left:3px solid var(--teal-d);border-radius:6px;padding:7px 12px;font-family:inherit;font-size:.76rem;font-weight:800;cursor:pointer;text-align:left}
.browse-chev{font-size:.66rem;transition:transform .18s;opacity:.85}
.browse-section.collapsed .browse-chev{transform:rotate(-90deg)}
.browse-name{flex:1}
.browse-count{font-size:.64rem;background:rgba(255,255,255,.2);padding:1px 7px;border-radius:9px}
.browse-body{padding:5px 0 2px}
.browse-section.collapsed .browse-body{display:none}
.browse-subsection{margin:6px 0 6px 14px;border-left:2px solid #d8e1eb;padding-left:8px}
.browse-subtoggle{width:100%;display:flex;align-items:center;gap:8px;background:#f4f7fa;color:var(--navy);border:1px solid var(--line);border-radius:6px;padding:6px 9px;font-family:inherit;font-size:.72rem;font-weight:800;cursor:pointer;text-align:left}
.browse-subtoggle:hover{border-color:var(--teal);background:#f0fbfd}
.browse-subsection.collapsed>.browse-subbody{display:none}
.browse-subsection.collapsed>.browse-subtoggle .browse-chev{transform:rotate(-90deg)}
.browse-subtoggle .browse-count{margin-left:auto;background:#e1e7ef;color:#536078}
.browse-subbody{padding-top:1px}
.region-category{margin:7px 0 9px 8px;border-left-width:3px}
.region-category>.browse-subtoggle{background:#eef3f8;font-size:.76rem}
.region-category>.browse-subbody{padding:2px 0 2px 4px}
.browse-sign-wrap{margin:6px 0;border-radius:8px}
.browse-sign{width:100%;display:flex;align-items:center;gap:10px;background:#fff;border:1px solid var(--line);border-left:4px solid var(--accent,#8ca0b8);border-radius:8px;padding:9px 12px;text-align:left;font-family:inherit;cursor:pointer}
.browse-sign:hover{border-color:var(--teal);box-shadow:0 2px 9px rgba(15,30,61,.08)}
.browse-sign-wrap.open .browse-sign{border-color:var(--teal);border-radius:8px 8px 0 0}
.browse-arrow{color:var(--teal-d);font-size:1rem}
.browse-sign-name{flex:1;color:var(--navy);font-size:.86rem;font-weight:700;line-height:1.3}
.browse-meta{display:flex;align-items:center;justify-content:flex-end;gap:4px;flex-wrap:wrap;font-size:.64rem;color:var(--muted)}
.browse-meta-chip{display:inline-flex;align-items:center;background:#f2f5f8;border:1px solid #dce3eb;border-radius:999px;padding:2px 7px;white-space:nowrap}
.browse-meta-chip.region{color:#0a6472;background:#edf8fa;border-color:#c4e5e9}
.browse-subsection>.browse-subbody>.browse-sign-wrap{margin:4px 8px 4px 10px;border-radius:6px}
.browse-subsection>.browse-subbody>.browse-sign-wrap>.browse-sign{gap:7px;border-left-width:3px;border-radius:6px;padding:4px 8px}
.browse-subsection>.browse-subbody>.browse-sign-wrap>.browse-sign .browse-arrow{font-size:.82rem}
.browse-subsection>.browse-subbody>.browse-sign-wrap>.browse-sign .browse-sign-name{font-size:.75rem;line-height:1.25}
.browse-subsection>.browse-subbody>.browse-sign-wrap>.browse-sign .browse-meta{font-size:.6rem}
.browse-subsection>.browse-subbody>.browse-sign-wrap>.browse-sign .browse-meta-chip{padding:1px 5px}
.browse-detail{background:#fff;border:1px solid var(--teal);border-top:0;border-radius:0 0 8px 8px;padding:0 12px 10px}
.browse-detail>.detail{max-height:none!important;overflow:visible;padding-top:7px}

.sub-block{margin:6px 0 8px}
.sub-toggle{width:100%;display:flex;align-items:center;gap:9px;background:transparent;border:none;border-bottom:1px solid var(--line);border-radius:0;padding:5px 4px;cursor:pointer;text-align:left;font-family:inherit;font-size:.7rem;font-weight:700;letter-spacing:.03em;text-transform:uppercase;color:#7a8598;transition:color .12s}
.sub-toggle:hover{color:var(--navy)}
.sub-chev{font-size:.64rem;color:var(--teal-d);transition:transform .18s;flex:0 0 auto;line-height:1}
.sub-block:not(.collapsed) .sub-chev{transform:rotate(90deg)}
.sub-name{flex:1;letter-spacing:.03em}
.sub-count{font-size:.64rem;font-weight:800;color:var(--muted);background:#eef1f6;border-radius:9px;padding:1px 7px}
.sub-body{padding:4px 0 2px}
.sub-block.collapsed .sub-body{display:none}
.area-map-block{display:none}
.area-map-block .sub-toggle{color:var(--navy);text-transform:none;font-size:.76rem;letter-spacing:0}

/* ---------- COLLAPSIBLE FRONT-PAGE FOLDS (chart + framework) ---------- */
.frontpage-fold{max-width:1180px;margin:0 auto 12px;padding:0 16px}
.frontpage-fold>summary{list-style:none;cursor:pointer;background:#eef2f7;border:1px solid var(--line);border-radius:9px;padding:8px 14px;font-size:.78rem;font-weight:700;color:#3f4a5e;display:flex;align-items:center;gap:9px}
.frontpage-fold>summary::-webkit-details-marker{display:none}
.frontpage-fold>summary::before{content:"\25B8";font-size:.72rem;color:var(--teal-d);transition:transform .15s}
.frontpage-fold[open]>summary::before{transform:rotate(90deg)}
.frontpage-fold[open]>summary{margin-bottom:8px}
.frontpage-fold .forest-wrap,.frontpage-fold .callout{max-width:none;margin:0;padding:0}

/* ---------- SIGN (collapsed row) ---------- */
.sign{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:9px;margin:7px 0;overflow:hidden;transition:box-shadow .12s,border-color .12s}
.sign:hover{box-shadow:0 2px 10px rgba(15,30,61,.08)}
.sign.open{box-shadow:0 3px 14px rgba(15,30,61,.10)}
.sign.match{border-color:var(--teal);box-shadow:0 0 0 2px rgba(14,157,176,.18)}
.sign-head{width:100%;display:flex;align-items:center;gap:11px;background:none;border:none;padding:12px 14px;cursor:pointer;text-align:left;font-family:inherit}
.chevron{font-size:1.1rem;color:#9aa3b2;transition:transform .2s;flex:0 0 auto;line-height:1}
.sign.open .chevron{transform:rotate(90deg);color:var(--teal-d)}
.sign-name{flex:1;font-size:.94rem;font-weight:700;color:var(--navy);line-height:1.3}
.head-chips{display:flex;gap:6px;align-items:center;flex-wrap:wrap;justify-content:flex-end}
.chip{font-size:.64rem;font-weight:800;padding:2px 7px;border-radius:4px;letter-spacing:.03em;white-space:nowrap}
.lat-chip{border:1px solid currentColor}
.evid-dot{color:#fff;min-width:20px;text-align:center;border-radius:5px}
.source-evidence-chip{color:#0a6472;background:#e7f6f8;border:1px solid #9ed8df}
.phase-badge.phase-aura{background:#e8f4fb;color:#0a5278}
.phase-badge.phase-ictal{background:#fdf2f2;color:#7b1c1c}
.phase-badge.phase-postictal{background:#eafaf1;color:#0e5a32}
.phase-badge.phase-interictal{background:#fdf6ee;color:#7a3e0a}
.phase-badge.phase-peri-ictal{background:#f5f0fb;color:#4a1a6b}

/* ---------- DETAIL (expandable) ---------- */
.detail{max-height:0;overflow:hidden;transition:max-height .28s ease}
.detail-loading,.lazy-fragment{padding:12px 16px;color:var(--muted);font-size:.78rem}
.detail-inner{padding:4px 16px 16px 30px;border-top:1px solid var(--line2);background:#fbfcfe}
.d-row{padding:9px 0;border-bottom:1px solid var(--line2)}
.d-row:last-child{border-bottom:none}
.d-label{display:block;font-size:.62rem;font-weight:800;text-transform:uppercase;letter-spacing:.07em;color:#8a93a5;margin-bottom:4px}
.d-value{font-size:.86rem;color:var(--ink);line-height:1.5}
.lat-badge{display:inline-block;font-size:.66rem;font-weight:800;padding:2px 7px;border-radius:4px;border:1px solid currentColor;letter-spacing:.03em;vertical-align:middle}
.axis-chips,.region-chips{display:inline-flex;gap:5px;align-items:center;flex-wrap:wrap;margin-left:7px}
.axis-chip,.region-chip{display:inline-flex;align-items:center;border-radius:999px;padding:2px 8px;font-size:.66rem;font-weight:750;line-height:1.35;white-space:nowrap}
.axis-state{display:inline-flex;align-items:center;border-radius:999px;padding:3px 9px;color:#5f6878;background:#f3f5f8;border:1px solid #cdd4df;font-size:.67rem;font-weight:750;line-height:1.35}
.axis-chip{color:#475569;background:#eef2f7;border:1px solid #d7dee8}
.axis-chip-more{color:#0a6472;background:#e7f6f8;border-color:#b3dfe5}
.region-chip{color:var(--region-chip);background:color-mix(in srgb,var(--region-chip) 10%,white);border:1px solid color-mix(in srgb,var(--region-chip) 45%,white)}
.axis-display-note{max-width:1180px;margin:0 auto 8px;padding:0 18px;color:#6b7280;font-size:.68rem;text-align:right}
.axis-note,.location-note{display:block;margin-top:6px;color:#334155;font-size:.8rem;line-height:1.42}
.d-metrics{display:flex;gap:10px;padding:11px 0;border-bottom:1px solid var(--line2);flex-wrap:wrap}
.metric{flex:1;min-width:110px;background:#fff;border:1px solid var(--line);border-radius:8px;padding:8px 11px}
.metric .d-label{margin-bottom:5px}
.metric-val{font-size:.9rem;font-weight:700;color:var(--navy);font-family:'SF Mono','Consolas',monospace}
.source-evidence-value{font-family:inherit;color:#0a6472}
.evid-badge{display:inline-block;color:#fff;font-size:.72rem;font-weight:800;padding:2px 9px;border-radius:5px}
.cite{color:var(--teal-d);font-style:italic;font-size:.82rem}
.d-help{display:block;margin-top:5px;color:var(--muted);font-size:.74rem;line-height:1.4}
.d-support{background:#f5f9fc;border:1px solid #d8e5ee;border-radius:9px;padding:10px 12px;margin-top:6px}
.d-support .d-label{color:#365d78}
.support-basis{font-size:.7rem;font-weight:800;color:#0a6472;margin-bottom:4px}
.support-summary{font-size:.82rem;line-height:1.5;color:#334155}
.support-list{margin:7px 0 0;padding-left:18px;display:grid;gap:3px;color:#475569;font-size:.76rem;line-height:1.4}
.evidence-overview{background:#f5f9fc;border:1px solid #d8e5ee;border-radius:9px;padding:10px 12px;margin-top:7px}
.evidence-overview .d-label{color:#365d78}
.evidence-overview p{margin:0;color:#334155;font-size:.82rem;line-height:1.45}
.evidence-counts{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-top:8px}
.evidence-counts>span{display:inline-flex;align-items:center;gap:3px;background:#fff;border:1px solid #d8e5ee;border-radius:999px;padding:3px 8px;color:#526276;font-size:.68rem}
.evidence-counts strong{color:#17314f}
.evidence-counts .evidence-basis-chip{color:#0a6472;background:#e7f6f8;border-color:#b3dfe5;font-weight:750}
.key-numbers{display:flex;flex-wrap:wrap;gap:5px;margin:8px 0 0;padding:0;list-style:none}
.key-numbers li{max-width:100%;background:#fff8e8;border:1px solid #ecd6a8;border-radius:6px;padding:4px 7px;color:#6e4b12;font-size:.7rem;line-height:1.35}
.syn-summary{display:block}
.syn-axis-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:8px}
.syn-axis-card{background:#fff;border:1px solid #d8e5ee;border-radius:8px;padding:9px 10px}
.syn-axis-head{display:flex;align-items:center;justify-content:space-between;gap:8px;color:#17314f;font-size:.78rem}
.syn-axis-head span{font-size:.68rem;color:#0a6472;background:#e7f6f8;border-radius:12px;padding:2px 8px;text-align:right}
.syn-axis-card p{margin:7px 0;font-size:.8rem;line-height:1.48;color:#334155}
.syn-counts{font-size:.68rem;color:#64748b;margin-top:6px}
.syn-relationships{margin:5px 0;padding-left:18px;font-size:.72rem;line-height:1.4;color:#475569}
.syn-sources{margin-top:7px;font-size:.7rem;color:#475569}
.syn-sources summary{cursor:pointer;color:#0a6472;font-weight:700}
.syn-sources ul{margin:5px 0 0;padding-left:18px}
.syn-family-shell{grid-column:1/-1;padding:0!important;overflow:hidden;background:#fff;border:1px solid #d8e5ee;border-radius:9px;margin-top:7px}
.syn-family-shell>summary{list-style:none;cursor:pointer;display:flex;justify-content:space-between;gap:10px;padding:9px 11px;font-size:.74rem;font-weight:800;color:#365d78}
.syn-family-shell>summary::-webkit-details-marker{display:none}
.syn-family-shell>summary::before{content:'\25B6';font-size:.6rem;color:var(--teal-d);transition:transform .15s}
.syn-family-shell[open]>summary::before{transform:rotate(90deg)}
.syn-family-shell>summary span:first-of-type{margin-right:auto;text-transform:uppercase;letter-spacing:.04em}
.syn-family-panel{padding:0 9px 9px;border-top:1px solid #d8e5ee}
.syn-family-scroll{max-height:clamp(260px,45vh,520px);overflow-y:auto;overscroll-behavior:contain;scrollbar-gutter:stable;padding:6px 2px}
.syn-family{display:block!important;background:#fff;border:1px solid var(--line);border-radius:7px;margin:6px 0;padding:0}
.syn-family>summary{list-style:none;cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:10px;min-height:40px;box-sizing:border-box;padding:8px 10px;font-size:.78rem;font-weight:750;color:#17314f}
.syn-family>summary::-webkit-details-marker{display:none}
.syn-family>summary::before{content:'\25B8';font-size:.6rem;color:var(--teal-d)}
.syn-family[open]>summary::before{transform:rotate(90deg)}
.syn-family>summary>span:first-of-type{margin-right:auto}
.syn-family-title{display:grid;gap:2px;min-width:0}
.syn-family-title strong{font-size:inherit;overflow-wrap:anywhere}
.syn-family-title small{color:#64748b;font-size:.68rem;font-weight:600;line-height:1.3;overflow-wrap:anywhere}
.syn-family-meta{font-size:.68rem;color:#64748b;font-weight:650;text-align:right}
.syn-family-body{display:grid;gap:5px;padding:9px 12px 11px;border-top:1px solid var(--line2);font-size:.73rem;line-height:1.45;color:#475569}
.syn-estimates{margin:4px 0 0;padding:0;list-style:none;display:grid;gap:4px}
.syn-estimates li{display:grid;grid-template-columns:minmax(150px,1fr) minmax(160px,1fr);gap:8px;padding:5px 7px;background:#f8fafc;border-radius:5px}
.syn-estimates li span{color:#64748b;text-align:right;overflow-wrap:anywhere}
.syn-range{font-weight:700;color:#0a6472}
.syn-empty{margin:3px 0;color:#64748b;font-style:italic}
.syn-global-table{padding:6px 9px;max-height:65vh;overflow-y:auto;scrollbar-gutter:stable}
.syn-family-context{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px 12px}
.syn-no-pool{margin:5px 0;padding:5px 7px;border-left:3px solid var(--teal);background:#f2fafb;color:#365d78;font-weight:650}
.syn-cross-link-note{margin:4px 0;padding:5px 7px;border-radius:5px;background:#f8fafc;color:#526276}
.evidence-axis-group{margin:7px 0 12px;border:1px solid #d5e0eb;border-radius:9px;overflow:hidden;background:#f8fafc}
.evidence-axis-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:9px 11px;background:linear-gradient(120deg,#17314f,#1a5262);color:#fff;font-size:.82rem;font-weight:800;letter-spacing:.035em;text-transform:uppercase}
.evidence-axis-heading span:last-child{font-size:.68rem;font-weight:650;letter-spacing:0;text-transform:none;opacity:.86}
.evidence-axis-heading i,.evidence-sign-group>summary i{font-style:normal}
.evidence-axis-group>summary.evidence-axis-heading{list-style:none;cursor:pointer}
.evidence-axis-group>summary.evidence-axis-heading::-webkit-details-marker{display:none}
.evidence-axis-group>summary.evidence-axis-heading::before{content:'\25B8';font-size:.62rem;color:#a7e3ec;transition:transform .15s}
.evidence-axis-group[open]>summary.evidence-axis-heading::before{transform:rotate(90deg)}
.evidence-axis-group>summary.evidence-axis-heading>span:first-of-type{margin-right:auto}
.evidence-sign-group{margin:7px;background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden}
.evidence-sign-group>summary{list-style:none;cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:40px;box-sizing:border-box;padding:8px 10px;color:#17314f;font-size:.8rem;font-weight:750}
.evidence-sign-group>summary::-webkit-details-marker{display:none}
.evidence-sign-group>summary::before{content:'\25B8';font-size:.62rem;color:var(--teal-d);transition:transform .15s}
.evidence-sign-group[open]>summary::before{transform:rotate(90deg)}
.evidence-sign-group>summary>span:first-of-type{margin-right:auto}
.evidence-sign-group>summary>span:last-child{color:#64748b;font-size:.68rem;font-weight:650}
.evidence-sign-results{padding:1px 7px 7px;border-top:1px solid var(--line2)}
.evidence-study-list{display:grid;gap:6px;margin-top:3px}
.evidence-study{border:1px solid #dbe4ee;border-radius:7px;background:#fff;overflow:hidden}
.evidence-study>summary{list-style:none;cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:10px;min-height:38px;box-sizing:border-box;padding:7px 9px;color:#17314f;font-size:.74rem;font-weight:750}
.evidence-study>summary::-webkit-details-marker{display:none}
.evidence-study>summary::before{content:'\25B8';color:var(--teal-d);font-size:.6rem}
.evidence-study[open]>summary::before{transform:rotate(90deg)}
.evidence-study>summary>span:first-of-type{margin-right:auto;overflow-wrap:anywhere}
.evidence-study>summary>span:last-child{color:#64748b;white-space:nowrap;font-weight:650}
.evidence-study>div{border-top:1px solid var(--line2)}
.evidence-statistic{padding:8px 10px;background:#fbfcfe}
.evidence-statistic+.evidence-statistic{border-top:1px solid var(--line2)}
.evidence-statistic-head{display:flex;justify-content:space-between;gap:10px;color:#17314f}
.evidence-statistic-head>strong{font-size:.82rem;font-variant-numeric:tabular-nums}
.evidence-statistic-head>span{font-size:.67rem;color:#0a6472;background:#e7f6f8;border:1px solid #b3dfe5;border-radius:999px;padding:2px 7px;white-space:nowrap}
.evidence-stat-chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}
.evidence-stat-chips span{font-size:.67rem;color:#526276;background:#fff;border:1px solid #dbe4ee;border-radius:999px;padding:2px 7px}
.evidence-stat-citation,.evidence-stat-source{margin-top:5px;color:#526276;font-size:.69rem;line-height:1.45;overflow-wrap:anywhere}
.evidence-stat-source span{padding:0 3px;color:#9aa3b2}
.evidence-stat-provenance{margin-top:6px;border-top:1px dotted #dbe4ee;padding-top:5px;color:#526276;font-size:.69rem}
.evidence-result-counts{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:0 16px 8px;color:#64748b;font-size:.7rem}
.evidence-result-counts .fx-count{padding:0}
.evidence-contextual-results{border-color:#dccda8}
.evidence-contextual-results>.evidence-axis-heading{background:linear-gradient(120deg,#5b4a2d,#78643d)}
.evidence-stat-provenance>summary{cursor:pointer;color:#0a6472;font-weight:750}
.evidence-stat-provenance>div{margin-top:5px;line-height:1.45}

@media (min-width:760px){
  .detail-inner{display:grid;grid-template-columns:1fr 1fr;grid-template-areas:"lat loc" "map map" "overview overview" "cite cite" "ev ev";gap:0 20px;column-gap:24px}
  .d-lat{grid-area:lat}
  .d-loc{grid-area:loc}
  .d-map{grid-area:map}
  .evidence-overview{grid-area:overview}
  .d-cite{grid-area:cite}
  .d-ev{grid-area:ev}
}

/* ---------- QUIZ MODE ---------- */
body.quiz .lat-chip,body.quiz .evid-dot,body.quiz .source-evidence-chip{display:none}
body.quiz .sign{border-left-color:#cbd3e0}
.quiz-hint{display:none;background:#f0fbfd;border:1px solid #b8e6ee;color:#0a5b68;font-size:.78rem;padding:8px 14px;border-radius:8px;margin:0 0 12px}
body.quiz .quiz-hint{display:block}

/* library evidence chip + block */
.lib-chip{background:#fff4e6;color:#a15c00;border:1px solid #e8b878;display:inline-flex;align-items:center;gap:3px}
body.quiz .lib-chip{display:none}
.d-ev{background:#fffaf2;border:1px solid #f0dcbd;border-radius:9px;padding:10px 12px !important;margin-top:6px}
.d-ev .d-label{color:#a15c00;margin-bottom:7px}
.evidence-history-shell{padding:0!important;overflow:hidden}
.evidence-history-shell>summary{list-style:none;cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 12px;color:#8a4b00;font-size:.78rem;font-weight:800}
.evidence-history-shell>summary::-webkit-details-marker{display:none}
.evidence-history-shell>summary::before{content:'\25B6';font-size:.64rem;color:#b66c0a;transition:transform .15s}
.evidence-history-shell[open]>summary::before{transform:rotate(90deg)}
.evidence-history-shell[open]>summary{border-bottom:1px solid #f0dcbd}
.evidence-history-shell>summary>span:first-of-type{margin-right:auto;text-transform:uppercase;letter-spacing:.05em}
.reviewed-evidence-count{color:#6b7280;font-size:.7rem;font-weight:700;text-transform:none;letter-spacing:0;text-align:right}
.reviewed-evidence-panel{padding:0 10px 10px}
.history-note{display:grid;grid-template-columns:minmax(90px,auto) 1fr;gap:8px;padding:8px 3px;border-bottom:1px solid #f4e5cd;color:#5c4b32;font-size:.74rem;line-height:1.4}
.history-note strong{color:#8a4b00}
.history-results{margin-top:10px;border:1px solid #ecd6b4;border-radius:7px;background:#fff}
.history-results>summary{display:flex;justify-content:space-between;gap:10px;list-style:none;cursor:pointer;padding:8px 10px;color:#8a4b00;font-size:.72rem;font-weight:800}
.history-results>summary::-webkit-details-marker{display:none}
.history-results>summary::before{content:'\25B8';font-size:.62rem;margin-right:6px}
.history-results[open]>summary::before{transform:rotate(90deg)}
.history-results>summary span{margin-left:auto;color:#64748b}
.ev-toolbar{position:sticky;top:0;z-index:2;display:flex;gap:7px;justify-content:flex-end;padding:8px 2px;background:#fffaf2;border-bottom:1px solid #f4e5cd}
.ev-toolbar button{border:1px solid #d7ad70;background:#fff;color:#8a4b00;border-radius:6px;padding:5px 8px;font-family:inherit;font-size:.68rem;font-weight:700;cursor:pointer}
.ev-toolbar button:hover{background:#fff1dc;border-color:#b87927}
.reviewed-evidence-scroll{max-height:clamp(280px,48vh,560px);overflow-y:auto;overscroll-behavior:contain;padding:8px 5px 4px 2px;scrollbar-gutter:stable}
.ev-paper-group{padding-left:0!important;border-left:0!important}
.ev-paper{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.ev-paper-file{overflow-wrap:anywhere}
.ev-paper-count{margin-left:auto;font-size:.68rem;font-weight:800;color:#0a6472;background:#e7f6f8;border-radius:999px;padding:2px 7px;white-space:nowrap}
.reviewed-card-evidence{padding-left:10px;border-left:2px solid #e8b878}
.ev-list{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px}
.ev-list li{font-size:.82rem;line-height:1.5;color:#3a3a3a;padding-left:12px;border-left:2px solid #e8b878}
.ev-src{font-weight:800;color:#8a4b00;display:inline-block;margin-right:4px}
.ev-pg{font-size:.68rem;font-weight:700;color:#8a4b00;background:#fff0d9;border:1px solid #e8b878;border-radius:4px;padding:0 5px;margin-right:3px;white-space:nowrap;vertical-align:baseline}
.pooled-hd{display:block;font-size:.84rem;color:var(--navy);margin-bottom:8px;font-variant-numeric:tabular-nums}
.pooled-hd strong{color:#8a4b00}
.pooled-warn{font-size:.76rem;background:#fff6e9;border:1px solid #f0cf8f;color:#7a4a06;border-radius:7px;padding:6px 10px;margin-bottom:8px;line-height:1.45}
.ev-meta{font-size:.72rem;color:#a15c00;font-weight:700}
.est-tag{font-size:.56rem;font-weight:800;letter-spacing:.03em;color:#8a93a5;background:#eef1f6;border:1px solid #d5dbe6;border-radius:4px;padding:0 4px;margin-left:4px;text-transform:none;cursor:help;vertical-align:middle}
.src-tag{font-size:.56rem;font-weight:800;letter-spacing:.03em;color:#1a6b4a;background:#e8f7ef;border:1px solid #a9dcc3;border-radius:4px;padding:0 4px;margin-left:4px;text-transform:none;cursor:help;vertical-align:middle}
/* sensitivity block: green accent (distinct from amber lateralization + teal PPV) */
.d-sens{background:#f2faf5;border-color:#c2e6d3}
.d-sens .d-label{color:#1a6b4a}
.d-sens .ev-list li{border-left-color:#5cc08a}
.d-sens .ev-src{color:#1a6b4a}
.d-sens .ev-meta{color:#1a6b4a}
/* predictive-value block: same layout as the evidence block, teal accent to set it apart */
.d-ppv{background:#f1fafb;border-color:#bfe3e8}
.d-ppv .d-label{color:#0a6472}
.d-ppv .ev-list li{border-left-color:#5cc0cd}
.d-ppv .ev-src{color:#0a6472}
.d-ppv .ev-pg{color:#0a6472;background:#e0f4f6;border-color:#a7dbe1}
.ev-dir{font-size:.66rem;font-weight:800;text-transform:uppercase;letter-spacing:.04em;color:#0a6472;background:#e0f4f6;border-radius:4px;padding:0 5px;margin-left:2px}
.ev-pop{font-size:.72rem;color:#5a6472;font-style:italic;margin-left:3px}
.ev-quote{color:#0a6472;cursor:help;font-weight:800}

/* framework callout */
.callout{max-width:1180px;margin:0 auto 14px;padding:0 16px}
.callout-inner{background:linear-gradient(120deg,#0f2540,#123a52);color:#e6f0f6;border-radius:12px;padding:15px 18px;font-size:.86rem;line-height:1.55;border:1px solid #1c4a63}
.callout-inner strong{color:#7fd4e6}
.callout-inner .tag{display:inline-block;background:#0e9db0;color:#04212a;font-size:.62rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;padding:2px 8px;border-radius:5px;margin-right:8px;vertical-align:middle}

/* ---------- WEIGHTED META-ANALYSIS (top foldable plot) ---------- */
.meta-fold>summary{background:linear-gradient(120deg,#0c2036,#123a52);color:#eaf3f8;border-color:#123a52}
.meta-fold>summary::before{color:#7fd4e6}
.meta-wrap{max-width:1180px;margin:0}
.meta-card{background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}
.meta-head{background:#f6f8fb;color:#54607a;padding:8px 16px;border-bottom:1px solid var(--line2)}
.meta-head p{font-size:.72rem;line-height:1.5;max-width:96ch}
.meta-head code{background:rgba(255,255,255,.14);border-radius:4px;padding:1px 5px;font-size:.9em}
.meta-tabs{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:11px 16px 4px}
.mtab{border:1px solid var(--line);background:#fff;color:var(--navy);border-radius:20px;padding:6px 13px;font-size:.76rem;font-weight:700;cursor:pointer;transition:all .12s}
.mtab:hover{border-color:var(--teal);color:var(--teal-d)}
.mtab.on{background:var(--navy);color:#fff;border-color:var(--navy)}
.msort{display:inline-flex;align-items:center;gap:5px;font-size:.64rem;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:#8a93a5}
.msort[hidden]{display:none}
.msort select{border:1px solid var(--line);border-radius:6px;padding:4px 7px;font-size:.74rem;font-weight:700;color:var(--navy);background:#fff;outline:none;cursor:pointer}
.msort select:focus{border-color:var(--teal)}
.meta-axis{margin-left:auto;display:flex;align-items:center;gap:7px;font-size:.62rem;color:#9aa3b2}
.meta-axis .ma-lab{text-transform:uppercase;letter-spacing:.06em;font-weight:800}
.ma-scale{position:relative;width:208px;display:flex;justify-content:space-between}
.ma-scale i{font-style:normal}
.meta-legend{display:flex;gap:15px;flex-wrap:wrap;padding:4px 18px 10px;font-size:.71rem;color:#5a6478;border-bottom:1px solid var(--line2)}
.meta-legend span{display:inline-flex;align-items:center;gap:5px}
.ml-dot{width:10px;height:10px;border-radius:50%}
.ml-cert i,.mcert i,.ml-cert .on,.mcert .on{display:inline-block;width:5px;height:5px;border-radius:50%;margin-left:1px}
.ml-cert i.on,.mcert i.on{background:#5a6478}
.ml-cert i.off,.mcert i.off{background:#d4dae4}
.meta-view{padding:8px 12px 14px}

.mreg{margin:4px 0 9px}
.mreg-h{font-size:.66rem;font-weight:800;letter-spacing:.07em;color:var(--rc);background:none;border-left:3px solid var(--rc);border-radius:0;padding:1px 0 1px 8px;display:block;margin:8px 0 3px}
.mgrp{margin:2px 0 7px}
.mgrp-h{font-size:.62rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#8a93a5;padding:4px 4px 2px;border-bottom:1px dashed var(--line)}

.msign{border-bottom:1px solid var(--line2)}
.msign-head{width:100%;display:grid;grid-template-columns:16px 74px minmax(150px,1fr) 208px 52px 24px;align-items:center;gap:9px;background:none;border:none;padding:7px 6px;cursor:pointer;text-align:left;font-family:inherit}
.msign-head:hover{background:#f7f9fc}
.mchev{font-size:1rem;color:#9aa3b2;transition:transform .18s;justify-self:center}
.msign.open .mchev{transform:rotate(90deg);color:var(--teal-d)}
.mdir{font-size:.6rem;font-weight:800;text-align:center;padding:2px 4px;border-radius:4px;border:1px solid currentColor;letter-spacing:.02em;white-space:nowrap}
.mname{font-size:.83rem;font-weight:700;color:var(--navy);line-height:1.25;min-width:0}
.mba{display:block;font-size:.64rem;font-weight:600;color:#8a93a5;letter-spacing:.01em;margin-top:1px}
.mflag{font-size:.72rem}
.mstrip{justify-self:start}
.mstrip-svg{width:208px;height:20px;display:block}
.mval{font-size:.92rem;font-weight:800;text-align:right;font-variant-numeric:tabular-nums}
.mcert{justify-self:center;white-space:nowrap;line-height:1}

.mdetail{max-height:0;overflow:hidden;transition:max-height .28s ease;background:#fbfcfe}
.mdetail-in{padding:10px 12px 12px 34px;border-top:1px dashed var(--line)}
.msumm{font-size:.76rem;color:#3f4a5e;margin-bottom:8px;font-variant-numeric:tabular-nums}
.msumm strong{color:var(--navy)}
.mcav{font-size:.74rem;line-height:1.45;border-radius:7px;padding:6px 10px;margin-bottom:6px}
.mcav-warn{background:#fff6e9;border:1px solid #f0cf8f;color:#7a4a06}
.mcav-warn strong{color:#7a3e00}
.mctab{border:1px solid var(--line2);border-radius:8px;overflow:hidden}
.mc-head,.mc-row{display:grid;grid-template-columns:minmax(120px,1.5fr) 46px 92px 34px minmax(80px,1fr) 30px 46px;gap:6px;align-items:center;font-size:.72rem;padding:5px 9px}
.mc-head{background:#f1f4f8;font-weight:800;color:#6b7280;text-transform:uppercase;letter-spacing:.03em;font-size:.6rem}
.mc-row{border-top:1px solid var(--line2)}
.mc-row:nth-child(odd){background:#fff}
.mc-cite{font-weight:700;color:var(--navy)}
.mc-val{font-weight:800;font-variant-numeric:tabular-nums}
.mc-qual{font-weight:700;color:#95691a;font-style:italic;font-size:.9em}
.mc-wt{display:flex;align-items:center;gap:5px}
.mc-bar{height:8px;border-radius:2px;min-width:3px}
.mc-wn{font-size:.66rem;color:#6b7280;font-variant-numeric:tabular-nums}
.mc-cl,.mc-gt,.mc-n,.mc-pg{color:#4a5568}
.mc-pg{font-weight:700;color:#8a4b00}
.mc-note{font-size:.72rem;color:#5a6478;line-height:1.45;padding:2px 9px 7px 9px;border-top:1px dotted var(--line2);background:#fbfcfe}

@media (max-width:760px){
  .msign-head{grid-template-columns:14px 60px 1fr;grid-template-areas:"chev dir name" "strip strip val";row-gap:5px}
  .mchev{grid-area:chev}.mdir{grid-area:dir}.mname{grid-area:name}
  .mstrip{grid-area:strip}.mval{grid-area:val;text-align:left}
  .mcert{display:none}
  .meta-axis{display:none}
  .mc-head{display:none}
  .mc-row{grid-template-columns:1fr auto;grid-template-areas:"cite val" "wt wt" "cl gt";gap:5px 8px;padding:8px 10px}
  .mc-cite{grid-area:cite}.mc-val{grid-area:val;text-align:right}.mc-wt{grid-area:wt}
  .mc-cl{grid-area:cl}.mc-gt{grid-area:gt}.mc-n,.mc-pg{display:none}
  .mc-note{line-height:1.5;padding:4px 10px 8px}
  .mdetail-in{padding:10px 10px 12px 16px}
}

/* ---------- CURRENT-LEDGER WEIGHTED EVIDENCE ---------- */
.reliability-fold>summary{background:linear-gradient(120deg,#0c2036,#123a52);color:#eaf3f8;border-color:#123a52}
.reliability-fold>summary::before{color:#7fd4e6}
.weighted-evidence-shell{max-width:1180px;margin:0 auto}
.weighted-axis-tabs{display:flex;gap:6px;margin-bottom:7px;padding:0 2px}
.weighted-axis-tab{border:1px solid #b9c9d8;border-radius:999px;background:#fff;color:#29445f;padding:7px 13px;font:inherit;font-size:.72rem;font-weight:800;cursor:pointer}
.weighted-axis-tab.on{background:#123a52;border-color:#123a52;color:#fff}
.weighted-axis-panel[hidden]{display:none}
.lr-wrap{max-width:1180px;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}
.lr-intro{padding:12px 16px;background:#f5f9fc;border-bottom:1px solid #dce7ef;color:#405269;font-size:.78rem;line-height:1.55}
.lr-intro strong{color:#0b5062}
.lr-method{margin:8px 13px 0;border:1px solid #d8e5ee;border-radius:8px;background:#fbfdff;color:#405269;font-size:.7rem}
.lr-method>summary{list-style:none;cursor:pointer;padding:7px 9px;color:#15576a;font-weight:800}
.lr-method>summary::-webkit-details-marker{display:none}
.lr-method>summary::before{content:'\25B8';display:inline-block;margin-right:7px;font-size:.6rem;transition:transform .15s}
.lr-method[open]>summary::before{transform:rotate(90deg)}
.lr-method>div{padding:0 10px 8px;border-top:1px solid #e2eaf0;line-height:1.5}
.lr-method p{margin:7px 0 0}
.lr-tools{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:11px 14px 7px;border-bottom:1px solid var(--line2)}
.lr-search{flex:1 1 300px;max-width:430px;border:1px solid var(--line);border-radius:8px;padding:8px 11px;font:inherit;font-size:.8rem;color:var(--navy);outline:none}
.lr-search:focus{border-color:var(--teal);box-shadow:0 0 0 3px rgba(14,157,176,.12)}
.lr-reset{border:1px solid var(--line);background:#fff;color:#526276;border-radius:7px;padding:7px 10px;font-family:inherit;font-size:.7rem;font-weight:750;cursor:pointer}
.lr-filters{display:flex;gap:5px;flex-wrap:wrap}
.lr-filter{border:1px solid #cbd6e2;background:#fff;color:#263c58;border-radius:16px;padding:5px 9px;font:inherit;font-size:.68rem;font-weight:750;cursor:pointer;white-space:nowrap}
.lr-filter i{font-style:normal;opacity:.67;margin-left:3px}
.lr-filter:hover{border-color:var(--teal);color:var(--teal-d)}
.lr-filter.on{background:var(--navy);border-color:var(--navy);color:#fff}
.lr-sort-label{display:flex;align-items:center;gap:5px;margin-left:auto;color:#758196;font-size:.61rem;font-weight:800;letter-spacing:.04em;text-transform:uppercase}
.lr-sort{border:1px solid var(--line);border-radius:7px;background:#fff;color:var(--navy);padding:5px 7px;font:inherit;font-size:.7rem;font-weight:700;text-transform:none;letter-spacing:0}
.lr-visual-legend{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:7px 14px;background:#eef4f8;border-top:1px solid #dbe6ee;border-bottom:1px solid #d6e1ea;color:#4d6075;font-size:.64rem}
.lr-visual-legend strong{color:#173a54}.lr-legend-scale{display:grid;grid-template-columns:repeat(3,1fr);min-width:170px;position:relative;color:#8490a1;font-size:.58rem;text-align:center}
.lr-legend-scale::before{content:'';position:absolute;left:8%;right:8%;top:50%;height:5px;transform:translateY(-50%);border-radius:999px;background:linear-gradient(90deg,#dfe6ee,#b8ccd8,#2b7180);z-index:0}
.lr-legend-scale i{font-style:normal;position:relative;z-index:1;text-shadow:0 1px #eef4f8}.lr-legend-scale i:first-child{text-align:left}.lr-legend-scale i:last-child{text-align:right}
.lr-legend-pips,.lr-cert{display:inline-flex;align-items:center;gap:3px}.lr-legend-pips i,.lr-cert i{display:inline-block;width:6px;height:6px;border-radius:50%;background:#c8d0da}.lr-legend-pips i.on,.lr-cert i.on{background:#52647b}.lr-cert i.on{background:var(--rel-color)}
.lr-visible-count{padding:2px 16px 8px;color:#788396;font-size:.7rem;font-style:italic}
.lr-list{border-top:1px solid var(--line2)}
.lr-page-group{border-bottom:1px solid #d9e2eb;background:#fff}
.lr-page-group>summary{list-style:none;display:flex;align-items:center;gap:8px;padding:8px 13px;background:#edf3f7;color:#173a54;border-left:4px solid var(--group-color,#0e9db0);cursor:pointer;font-size:.75rem;font-weight:850;text-transform:uppercase;letter-spacing:.035em}
.lr-page-group>summary::-webkit-details-marker{display:none}
.lr-page-group>summary::before{content:'›';font-size:1rem;color:var(--group-color,#0e9db0);transition:transform .15s}
.lr-page-group[open]>summary::before{transform:rotate(90deg)}
.lr-page-group-count{margin-left:auto;background:#dce7ef;color:#526579;border-radius:11px;padding:1px 7px;font-size:.64rem;letter-spacing:0}
.lr-page-subgroup-title{margin:0;padding:6px 14px 5px 34px;background:#f7f9fb;border-top:1px solid #e2e8ef;border-bottom:1px solid #e8edf2;color:#56667a;font-size:.66rem;font-weight:800;text-transform:uppercase;letter-spacing:.03em}
.lr-neutral-note{color:#626e7e;font-style:italic}
.lr-row{border-bottom:1px solid var(--line2)}
.lr-row[hidden]{display:none}
.lr-row-head{list-style:none;display:grid;grid-template-columns:16px minmax(165px,.8fr) minmax(210px,1.15fr) minmax(150px,.65fr) auto;align-items:center;gap:9px;padding:8px 12px;cursor:pointer;color:var(--navy)}
.lr-row-head::-webkit-details-marker{display:none}
.lr-row-head::before{content:'›';font-size:1.05rem;color:#8090a5;transition:transform .16s;justify-self:center}
.lr-row[open]>.lr-row-head::before{transform:rotate(90deg);color:var(--teal-d)}
.lr-row-head:hover{background:#f7fafc}
.lr-name{font-size:.82rem;font-weight:800;line-height:1.25}
.lr-directions{display:flex;gap:4px;align-items:center;flex-wrap:wrap}
.lr-direction{display:inline-flex;border:1px solid currentColor;border-radius:12px;padding:2px 7px;font-size:.6rem;font-weight:800;white-space:nowrap}
.lr-direction b{margin-left:4px;font-variant-numeric:tabular-nums}
.lr-primary{color:#123a52;background:#edf4f8}.lr-secondary{color:#0b7180;background:#eff9fa}
.lr-nonassoc{color:#5d6878;background:#f5f6f8}
.lr-contra{color:#b9362a;background:#fff4f2}.lr-ipsi{color:#246b9b;background:#f0f7fc}
.lr-dominant{color:#8240a3;background:#faf3fd}.lr-nondominant{color:#167546;background:#eff9f3}
.lr-right,.lr-left,.lr-bilateral{color:#5c4a87;background:#f7f4fc}.lr-nonlat{color:#5d6878;background:#f5f6f8}
.lr-other{color:#7b5a18;background:#fff8e9}.lr-unreported{color:#687386;background:#f5f7fa}
.lr-reliability{display:grid;grid-template-columns:minmax(86px,1fr) auto auto;align-items:center;gap:6px;min-width:145px}
.lr-no-directional{grid-template-columns:minmax(112px,1fr) auto;color:#667284}
.lr-no-directional-label{font-size:.68rem;font-weight:800;white-space:nowrap}
.lr-rel-track{position:relative;height:8px;border-radius:999px;background:linear-gradient(to right,transparent 49.5%,#cbd4df 49.5%,#cbd4df 50.5%,transparent 50.5%),linear-gradient(to right,transparent 74.5%,#d7dee7 74.5%,#d7dee7 75.5%,transparent 75.5%),#e7ecf2}
.lr-rel-fill{position:absolute;inset:0 auto 0 0;width:var(--rel-position);border-radius:999px;background:var(--rel-color);opacity:.28}
.lr-rel-dot{position:absolute;left:var(--rel-position);top:50%;width:9px;height:9px;border-radius:50%;transform:translate(-50%,-50%);background:var(--rel-color);border:1.5px solid #fff;box-shadow:0 0 0 1px color-mix(in srgb,var(--rel-color) 40%,transparent)}
.lr-rel-value{min-width:38px;color:var(--rel-color);font-size:.75rem;text-align:right;font-variant-numeric:tabular-nums}
.lr-evidence-counts{font-size:.64rem;color:#687589;text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.lr-evidence-counts b{color:#163a53}.lr-evidence-counts i{font-style:normal;color:#b3bbc6;margin:0 2px}
.lr-row-body{padding:0 12px 12px 37px;background:#fbfcfe;border-top:1px dashed #dbe2ea}
.lr-weighted{display:grid;grid-template-columns:minmax(210px,.7fr) minmax(220px,1.3fr);gap:10px;align-items:center;padding:9px 0 2px;color:#53657a;font-size:.67rem}
.lr-weighted>div:first-child{display:flex;flex-direction:column;gap:2px}.lr-weighted strong{color:#17314f;font-size:.7rem}
.lr-weightbar{display:flex;height:10px;border-radius:999px;overflow:hidden;background:#e8edf2}
.lr-weightbar>span{display:block;min-width:2px;box-sizing:border-box}
.lr-weightbar>span+span{border-left:2px solid #fff}
.lr-weightbar .lr-primary{background:#123a52}.lr-weightbar .lr-secondary{background:#37a6b5}.lr-weightbar .lr-nonassoc{background:#9ca6b3}
.lr-summary{margin:0;padding:10px 0 8px;color:#33465d;font-size:.78rem;line-height:1.48}
.lr-families{margin:0 0 8px;border:1px solid #cfe0ea;border-radius:8px;background:#f5fafc}
.lr-families>summary{display:flex;gap:7px;align-items:center;padding:7px 10px;cursor:pointer;color:#15576a;font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.03em}
.lr-families>summary span{margin-left:auto;background:#dceff4;border-radius:10px;padding:1px 6px}
.lr-family{display:grid;grid-template-columns:minmax(150px,1fr) minmax(180px,1fr);gap:3px 12px;padding:7px 10px;border-top:1px solid #dce9ef;font-size:.72rem;color:#405269}
.lr-family strong{color:#19364c}.lr-family small{grid-column:1/-1;color:#778397;font-size:.64rem}
.lr-exceptions{margin:7px 0;border:1px solid #edd6aa;border-radius:8px;background:#fff9ef;color:#684c20;font-size:.72rem;overflow:hidden}
.lr-exceptions>summary{list-style:none;display:flex;align-items:center;gap:7px;padding:8px 10px;cursor:pointer;font-weight:800}
.lr-exceptions>summary::-webkit-details-marker{display:none}
.lr-exceptions>summary::before{content:'\25B8';font-size:.58rem;color:#a8670b;transition:transform .15s}
.lr-exceptions[open]>summary::before{transform:rotate(90deg)}
.lr-exceptions>summary span{margin-left:auto;background:#f3dfb7;border-radius:999px;padding:1px 7px;font-size:.62rem}
.lr-exceptions ul{margin:0;padding:8px 12px 9px 28px;border-top:1px solid #f0dfbd}
.lr-sources{margin:7px 0;border:1px solid #d6e1ea;border-radius:8px;background:#f7fafc;overflow:hidden}
.lr-sources>summary{list-style:none;display:flex;align-items:center;gap:7px;padding:8px 10px;cursor:pointer;color:#24425a;font-size:.7rem;font-weight:800;text-transform:uppercase;letter-spacing:.04em}
.lr-sources>summary::-webkit-details-marker{display:none}.lr-sources>summary::before{content:'\25B8';font-size:.58rem;color:#34778a;transition:transform .15s}.lr-sources[open]>summary::before{transform:rotate(90deg)}
.lr-sources>summary span{margin-left:auto;background:#dceaf0;border-radius:999px;padding:1px 7px;font-size:.62rem}.lr-sources>p{margin:0;padding:0 10px 7px;color:#748195;font-size:.62rem}.lr-sources>div{padding:0 8px 6px;border-top:1px solid #e0e8ee}
.lr-source{margin:5px 0;border:1px solid #dce3eb;border-radius:8px;background:#fff;overflow:hidden}
.lr-source>summary{display:flex;align-items:center;gap:12px;padding:7px 9px;cursor:pointer;color:#203d56;font-size:.72rem;font-weight:750}
.lr-source>summary span:first-child{min-width:0;overflow-wrap:anywhere}
.lr-source>summary span:last-child{margin-left:auto;color:#778397;font-size:.62rem;white-space:nowrap}
.lr-source-file,.lr-source-context{padding:6px 10px 0;color:#7a8697;font-size:.63rem;line-height:1.4;overflow-wrap:anywhere}
.lr-source-context{color:#53657a}
.lr-source-section{padding:7px 10px 9px;color:#445267;font-size:.68rem}
.lr-source-section+ .lr-source-section{border-top:1px solid #edf0f4}
.lr-source-section>strong{display:block;margin-bottom:4px;color:#24425a;font-size:.62rem;text-transform:uppercase;letter-spacing:.04em}
.lr-source-section ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px}
.lr-source-section li{display:grid;grid-template-columns:minmax(130px,.75fr) minmax(180px,1.35fr) auto;gap:3px 9px;align-items:start;padding:5px 0;border-top:1px dotted #e2e7ed;line-height:1.35}
.lr-source-section li:first-child{border-top:0}
.lr-item-title{font-weight:750;color:#1e3a53}.lr-item-text{color:#46566a}.lr-locator{color:#8b5b13;font-size:.61rem;text-align:right}
.lr-stat-value{grid-column:1;font-weight:850;color:#0b6776;font-variant-numeric:tabular-nums}
.lr-stat-value+.lr-item-title{grid-column:2}.lr-stat-meta{grid-column:1/3;color:#66758a;font-size:.62rem}
.lr-linkage-note{margin-top:8px;color:#7b8798;font-size:.62rem}
.lr-empty{color:#7b8798;font-size:.7rem;font-style:italic}
.lr-unreported{margin:12px;border:1px solid #dce3eb;border-radius:9px;background:#f8fafc}
.lr-unreported>summary{display:flex;gap:8px;align-items:center;padding:9px 11px;cursor:pointer;color:#4c5c70;font-size:.73rem;font-weight:800}
.lr-unreported>summary span{margin-left:auto;background:#e6ebf1;border-radius:11px;padding:1px 7px;font-size:.64rem}
.lr-unreported>p{margin:0;padding:0 11px 8px;color:#68768a;font-size:.68rem;line-height:1.45}
.lr-unreported-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;padding:0 10px 10px}
.lr-unreported-sign{border:1px solid #e1e6ec;border-radius:6px;background:#fff;padding:5px 7px;color:#536175;font-size:.67rem;line-height:1.3}
.lr-unreported-sign[hidden]{display:none}
.lr-historical{margin:12px;padding-top:10px;border-top:1px solid var(--line)}
.lr-historical>p{margin:0 3px 8px;color:#6c788b;font-size:.68rem;line-height:1.45}
.lr-historical .historical-meta-fold{margin:0}
.lr-historical .historical-meta-fold>summary{min-height:36px;padding:7px 11px;background:#f3f5f8;color:#47566b;border:1px solid #dbe2ea;font-size:.75rem}
.lr-historical .historical-meta-fold>summary::before{color:#7c8898}

@media (max-width:820px){
  .lr-row-head{grid-template-columns:16px 1fr;gap:5px 8px;padding:9px 10px}
  .lr-name{font-size:.8rem}.lr-directions,.lr-reliability,.lr-evidence-counts{grid-column:2;text-align:left;white-space:normal}
  .lr-row-body{padding:0 10px 11px 34px}
  .lr-sort-label{margin-left:0}
  .lr-unreported-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .lr-source-section li{grid-template-columns:1fr auto}.lr-item-text,.lr-stat-meta{grid-column:1/-1}.lr-stat-value+.lr-item-title{grid-column:1}.lr-locator{grid-column:2;grid-row:1}
  .lr-weighted{grid-template-columns:1fr}
}
@media (max-width:520px){
  .weighted-axis-tabs{display:grid;grid-template-columns:1fr 1fr}.weighted-axis-tab{white-space:normal}
  .lr-tools{padding:9px 10px 6px;overflow:hidden}.lr-search{flex:1 1 100%;width:100%;max-width:none;min-width:0;box-sizing:border-box}
  .lr-filters{width:100%;min-width:0}.lr-filter{flex:1 1 auto;min-width:0;text-align:center;white-space:normal}
  .lr-sort-label{max-width:100%;flex-wrap:wrap}.lr-sort{max-width:100%}
  .lr-visual-legend{gap:8px}.lr-legend-scale{order:3;width:100%}.lr-reliability{width:100%;grid-template-columns:minmax(100px,1fr) auto auto}
  .lr-directions{min-width:0}.lr-direction{max-width:100%;white-space:normal;line-height:1.25}
  .lr-family{grid-template-columns:1fr}.lr-family small{grid-column:1}
  .lr-unreported-grid{grid-template-columns:1fr}
  .lr-source>summary{align-items:flex-start;flex-direction:column;gap:3px}.lr-source>summary span:last-child{margin-left:0;white-space:normal}
}

/* ---------- SOURCE-FIGURES EXPLORER ---------- */
.figures-fold>summary{background:#eef2f7;color:#3f4a5e}
/* descriptive-statistics (sensitivity) fold */
.ds-fold>summary{background:#eaf6ef;color:#1a5c40}
.ds-wrap{max-width:1180px;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}
.ds-method{font-size:.78rem;line-height:1.55;color:#3a5648;padding:13px 16px;background:#f6fbf8;border-bottom:1px solid var(--line2);margin:0}
.ds-tablewrap{overflow-x:auto}
.ds-table{width:100%;border-collapse:collapse;font-size:.82rem}
.ds-table th{text-align:left;font-size:.62rem;text-transform:uppercase;letter-spacing:.06em;color:#6a7686;background:#f8fafc;padding:8px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
.ds-table td{padding:8px 12px;border-bottom:1px solid #eef1f5;vertical-align:top}
.ds-sign{font-weight:700;color:var(--navy);background:#fbfdfc;border-right:1px solid #eef1f5}
.ds-cond{color:#1a6b4a;font-weight:600}
.ds-val{font-family:'SF Mono','Consolas',monospace;font-weight:700;color:var(--navy);white-space:nowrap}
.ds-rng{font-weight:500;color:#8a93a5}
.ds-k{text-align:center;color:#6a7686}
.ds-src{color:#4a5568;font-size:.76rem}
.ds-spec{font-size:.78rem;line-height:1.55;color:#7a4a06;background:#fff7ec;border-top:1px solid #f0dcbd;padding:12px 16px;margin:0}
.fx-wrap{max-width:1180px;margin:0;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}
.fx-intro{font-size:.78rem;line-height:1.55;color:#4a5568;padding:13px 16px;background:#fbfcfe;border-bottom:1px solid var(--line2)}
.evidence-method-note{display:inline-block;margin-left:5px}
.evidence-method-note>summary{cursor:pointer;color:#0a6472;font-weight:750}
.evidence-method-note>p{margin:6px 0 0;padding:7px 9px;border:1px solid #d8e5ee;border-radius:6px;background:#fff;line-height:1.45}
.fx-tools{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:11px 16px 6px}
.fx-search{flex:1 1 320px;width:auto;max-width:430px;border:1px solid var(--line);border-radius:7px;padding:8px 11px;font-size:.84rem;outline:none}
.fx-search:focus{border-color:var(--teal);box-shadow:0 0 0 3px rgba(14,157,176,.13)}
.fx-reset{border:1px solid var(--line);background:#fff;color:#526276;border-radius:7px;padding:7px 10px;font-family:inherit;font-size:.7rem;font-weight:700;cursor:pointer}
.fx-reset:hover{border-color:var(--teal);color:var(--teal-d)}
.fx-btns{display:flex;gap:6px;flex-wrap:wrap}
.fxb{border:1px solid var(--line);background:#fff;color:var(--navy);border-radius:16px;padding:5px 10px;font-size:.73rem;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.fxb:hover{border-color:var(--teal);color:var(--teal-d)}
.fxb.on{background:var(--navy);color:#fff;border-color:var(--navy)}
.fxb i{font-style:normal;font-size:.64rem;opacity:.7;font-weight:800}
.fx-count{font-size:.72rem;color:var(--muted);font-style:italic;padding:2px 16px 8px}
.fx-table{max-height:560px;overflow-y:auto;border-top:1px solid var(--line2)}
.fx-row{display:grid;grid-template-columns:96px minmax(150px,1.4fr) 88px minmax(120px,1fr);gap:8px;align-items:start;padding:7px 16px;border-bottom:1px solid var(--line2);font-size:.78rem}
.fx-row:nth-child(even){background:#fbfcfe}
.fx-row[data-excl="1"]{opacity:.55}
.fx-m{grid-column:1;color:#fff;font-size:.6rem;font-weight:800;text-transform:uppercase;letter-spacing:.03em;padding:2px 6px;border-radius:4px;text-align:center;align-self:start;white-space:nowrap}
.fx-ph{grid-column:2;font-weight:700;color:var(--navy);line-height:1.3}
.fx-dir{font-size:.58rem;font-weight:800;padding:1px 5px;border-radius:3px;margin-left:6px;vertical-align:middle;border:1px solid currentColor}
.fx-dir.fx-contra{color:#c0392b}.fx-dir.fx-ipsi{color:#2471a3}.fx-dir.fx-dominant{color:#8e44ad}.fx-dir.fx-nondominant{color:#1a7a4a}.fx-dir.fx-variable{color:#95691a}
.fx-reg{display:block;font-size:.66rem;font-weight:600;color:#8a93a5;margin-top:1px}
.fx-val{grid-column:3;font-weight:800;color:var(--ink);font-variant-numeric:tabular-nums;font-size:.76rem}
.fx-val small{display:block;margin-top:2px;color:#64748b;font-size:.62rem;font-weight:650}
.fx-src{grid-column:4;font-size:.7rem;color:#5a6478;line-height:1.35}
.fx-src b{color:#b5470b}
.fx-q{grid-column:2 / -1;font-size:.72rem;color:#6b7280;font-style:italic;line-height:1.4;padding-top:3px;border-top:1px dotted var(--line2);margin-top:3px}
.fx-q div{font-style:normal;margin-top:3px;color:#475569}
.fx-owner{color:#8a5209!important;background:#fff8e7;border-left:3px solid #d9a441;padding:5px 7px}
.fx-context{grid-column:2 / -1;font-size:.72rem;color:#475569;border:1px solid var(--line2);border-radius:6px;padding:5px 8px;background:#fff}
.fx-context>summary{cursor:pointer;font-weight:700;color:var(--teal-d)}
.fx-context>div{margin-top:5px;line-height:1.45}
.fx-context code,.ev-trace code{font-size:.66rem;overflow-wrap:anywhere}
.ev-map{display:inline-block;font-size:.58rem;font-weight:800;border:1px solid currentColor;border-radius:4px;padding:1px 5px}
.ev-map-exact{color:#1a7a4a}.ev-map-related{color:#95691a}
.reviewed-card-evidence{margin-bottom:14px}.ev-measure,.ev-owner{margin:6px 0;color:#475569}
.ev-paper{margin-bottom:7px;padding:7px 9px;border:1px solid #dbe4ee;border-radius:6px;background:#f7fafc;color:#475569;line-height:1.4}
.ev-paper>div+div{margin-top:3px}.ev-paper-file{color:var(--navy);font-weight:700;overflow-wrap:anywhere}.ev-paper-role{display:inline-block;margin-left:6px;padding:1px 6px;border-radius:4px;background:#e8f4f7;color:#0e6675;font-size:.72em;font-weight:700}.ev-finding{margin:5px 0 3px}
.ev-stats{margin:7px 0}.ev-stats>summary{cursor:pointer;color:#0e7490;font-weight:700}.ev-stat-list{margin:5px 0 0;padding-left:22px}.ev-stat-list>li{margin:5px 0}.ev-stat-context{display:grid;gap:2px;margin-top:3px;color:#64748b;font-size:.9em}.ev-stat-context span{display:block}
.ev-trace{margin-top:5px;border:1px solid var(--line2);border-radius:6px;padding:4px 7px;color:#475569}
.ev-trace>summary{cursor:pointer;font-weight:700;color:var(--teal-d)}
.ev-trace>div{margin-top:4px;line-height:1.4}
.fx-row.fx-hidden,[data-fx-group].fx-hidden{display:none!important}
@media (max-width:760px){
  .fx-row{grid-template-columns:1fr auto;grid-template-areas:"m val" "ph ph" "src src" "q q";gap:3px 8px}
  .fx-m{grid-area:m}.fx-ph{grid-area:ph}.fx-val{grid-area:val;text-align:right}.fx-src{grid-area:src}.fx-q{grid-area:q}.fx-context{grid-column:1 / -1}
  .fx-search{width:100%}
  .evidence-method-note{display:block;margin:5px 0 0}
  .syn-family-context{grid-template-columns:1fr}
  .evidence-axis-heading,.evidence-sign-group>summary,.syn-family>summary,.evidence-study>summary{align-items:flex-start}
  .syn-family>summary{flex-wrap:wrap}
  .syn-family-meta{flex:1 1 100%;padding-left:13px;text-align:left}
  .evidence-result-counts{align-items:flex-start;flex-direction:column;gap:2px}
  .evidence-statistic-head{align-items:flex-start;flex-direction:column}
  .reviewed-evidence-scroll{max-height:52vh}
  .evidence-history-shell>summary{align-items:flex-start}
  .reviewed-evidence-count{max-width:54%}
  .ev-toolbar{justify-content:stretch}
  .ev-toolbar button{flex:1}
}

/* probabilistic forest-plot section */
.forest-wrap{max-width:1180px;margin:0 auto 16px;padding:0 16px}
.forest-card{background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}
.forest-head{background:linear-gradient(120deg,#12234a,#1a3a6b);color:#fff;padding:14px 18px}
.forest-head h2{font-size:1rem;font-weight:800;letter-spacing:.01em;margin-bottom:3px}
.forest-head p{font-size:.76rem;opacity:.85;line-height:1.5}
.forest-body{padding:14px 10px 6px}
.forest-svg{width:100%;height:auto;display:block}
.forest-legend{display:flex;gap:18px;flex-wrap:wrap;padding:6px 18px 14px;font-size:.74rem;color:#555}
.forest-legend span{display:inline-flex;align-items:center;gap:6px}
.fl-dot{width:11px;height:11px;border-radius:50%;display:inline-block}

/* paper library */
.lib{max-width:1180px;margin:0 auto;padding:0 16px}
.lib-details{background:#fff;border:1px solid var(--line);border-radius:10px;margin-bottom:16px;overflow:hidden}
.lib-details>summary{list-style:none;cursor:pointer;padding:13px 18px;font-size:.82rem;font-weight:800;color:var(--navy);text-transform:uppercase;letter-spacing:.05em;display:flex;align-items:center;gap:9px}
.lib-details>summary::-webkit-details-marker{display:none}
.lib-details>summary::before{content:"\25B6";font-size:.6rem;color:var(--teal);transition:transform .15s}
.lib-details[open]>summary::before{transform:rotate(90deg)}
.lib-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:10px;padding:0 18px 18px}
.evidence-library-details>summary{text-transform:none;letter-spacing:0;flex-wrap:wrap}
.evidence-library-details>summary>span:first-of-type{margin-right:auto}
.evidence-library-summary{color:#64748b;font-size:.68rem;font-weight:650;text-align:right}
.evidence-library-body{border-top:1px solid var(--line2);padding:12px 14px 14px;background:#f8fafc}
.evidence-library-overview{margin:0 0 10px;color:#475569;font-size:.76rem;line-height:1.5}
.evidence-view-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:9px}
.evidence-view-tab{border:1px solid #cdd8e5;border-radius:999px;background:#fff;color:#17314f;padding:6px 10px;font-family:inherit;font-size:.72rem;font-weight:750;cursor:pointer;display:inline-flex;align-items:center;gap:6px}
.evidence-view-tab:hover{border-color:var(--teal);color:var(--teal-d)}
.evidence-view-tab.on{background:#17314f;border-color:#17314f;color:#fff}
.evidence-view-tab i{font-style:normal;font-size:.62rem;opacity:.75}
.evidence-view-panel[hidden]{display:none}
.evidence-view-panel>.fx-wrap{max-width:none}
.paper{border:1px solid var(--line2);border-radius:9px;padding:11px 13px;background:#fbfcfe}
.paper .p-cite{font-weight:800;color:var(--navy);font-size:.82rem}
.paper .p-jrnl{font-style:italic;color:var(--teal-d);font-size:.74rem;margin:1px 0 4px}
.paper .p-title{font-size:.8rem;color:#2a2a2a;margin-bottom:5px}
.paper .p-contrib{font-size:.76rem;color:#5a6478;line-height:1.45}

/* ---------- EMPTY ---------- */
#no-results{display:none;padding:44px 20px;text-align:center;color:var(--muted);font-size:.95rem;font-style:italic}

/* ---------- ABBREV + FOOTER ---------- */
.abbrev{max-width:1180px;margin:0 auto;padding:0 16px}
.abbrev-details{background:#fff;border:1px solid var(--line);border-radius:10px;margin-bottom:20px;overflow:hidden}
.abbrev-details>summary{list-style:none;cursor:pointer;padding:13px 18px;font-size:.82rem;font-weight:800;color:var(--navy);text-transform:uppercase;letter-spacing:.05em;display:flex;align-items:center;gap:9px}
.abbrev-details>summary::-webkit-details-marker{display:none}
.abbrev-details>summary::before{content:"\25B6";font-size:.6rem;color:var(--teal);transition:transform .15s}
.abbrev-details[open]>summary::before{transform:rotate(90deg)}
.abbrev-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:5px 24px;padding:0 18px 18px}
.abbrev-item{font-size:.78rem;color:#444}
.abbrev-item strong{color:var(--navy)}
.footer{background:var(--navy);color:#8fa0b4;padding:20px 24px;font-size:.76rem;line-height:1.75}
.footer strong{color:#b3c1d1}
.footer a{color:#9fc3e0;text-decoration:underline}
.footer a:hover{color:#cfe0ee}

/* ==================== MOBILE ==================== */
@media (max-width:760px){
  .site-header{padding:14px 16px 12px}
  .site-header h1{font-size:1.12rem}
  .search-wrap{flex:1 1 55%;max-width:none}
  #search-input{width:auto}
  .search-clear{display:none}
  .browse-mode-field{flex:1 1 42%;min-width:150px}
  .filter-toggle{display:inline-flex;padding:6px 11px;font-size:.78rem}
  .filter-panel{display:none;flex:1 1 100%;width:100%;flex-direction:row;flex-wrap:wrap;gap:9px;padding-top:2px}
  .filter-panel.open{display:flex}
  .filter-field{flex:1 1 45%}
  .filter-field select{width:100%}
  .tool-actions{margin-left:0;flex:1 1 100%;justify-content:flex-start}
  #result-count{margin-left:0}
  .region-section{scroll-margin-top:118px}
  .sign-name{font-size:.9rem}
  .detail-inner{padding:4px 14px 14px 20px}
  .lib-grid{grid-template-columns:1fr}
  .evidence-library-details>summary{align-items:flex-start}
  .evidence-library-summary{flex:1 1 100%;text-align:left;padding-left:15px;line-height:1.45}
  .evidence-library-body{padding:10px 8px}
  .evidence-view-tabs{display:grid;grid-template-columns:1fr}
  .evidence-view-tab{justify-content:space-between;border-radius:7px;min-height:38px}
}
@media (max-width:420px){
  .filter-field{flex:1 1 100%}
  .head-chips{width:100%;justify-content:flex-start;padding-left:26px;margin-top:2px}
  .sign-head{flex-wrap:wrap}
  .sign-name{flex:1 1 auto}
}

@media print{
  .sticky-head,.filter-toggle,.tb-fab{display:none}
  .detail{max-height:none!important}
  .region-section.collapsed .region-body{display:block}
  .site-header,.region-toggle,.evid-badge,.phase-badge,.chip{print-color-adjust:exact;-webkit-print-color-adjust:exact}
}
"""

JS = (
    "const CLASSIFICATION_TREES=" + classification_trees_json + ";\n"
    + "const SIGN_SEARCH=" + sign_search_json + ";\n"
    + r"""
/* ---------- Brodmann map ---------- */
(function(){
  const card=document.querySelector('.brain-card');
  if(!card||typeof BRAIN_TILES==='undefined') return;
  const svgs=[...card.querySelectorAll('.brain-svg')];
  const panel=document.getElementById('brain-panel');
  const empty=panel.querySelector('.bp-empty'), body=panel.querySelector('.bp-body');
  const hover=document.getElementById('brain-hover');
  const latColor={contra:'#c0392b',ipsi:'#2471a3',dominant:'#8e44ad',nondominant:'#1a7a4a',
                  right:'#d35400',nonlat:'#6b7280',variable:'#95691a'};
  const latBg={contra:'#fdf2f2',ipsi:'#eaf4fb',dominant:'#f5f0fb',nondominant:'#eafaf1',
               right:'#fef5ee',nonlat:'#f3f4f6',variable:'#fdf8ee'};
  const latLab={contra:'CONTRA',ipsi:'IPSI',dominant:'DOM',nondominant:'NON-DOM',
                right:'RIGHT',nonlat:'NON-LAT',variable:'VARIABLE'};
  const evColor={I:'#1a7a4a',II:'#c47a00',III:'#c0392b'};
  const traceBody=panel.querySelector('.bp-trace');
  let hemi='L', sel=null, traced=null;

  /* density buckets + "has data" styling */
  const counts=Object.values(BRAIN_TILES).map(t=>t.signs.length).filter(n=>n>0);
  const maxN=Math.max(1,...counts);
  const RAMP=[[179,218,255],[173,182,250],[180,142,223],[187,102,176],[185,60,113],[172,1,26]];
  function densColour(t){                     /* t in 0..1 across the ramp */
    const x=Math.max(0,Math.min(1,t))*(RAMP.length-1), i=Math.min(RAMP.length-2,Math.floor(x)), f=x-i;
    const a=RAMP[i], b=RAMP[i+1];
    const c=[0,1,2].map(k=>Math.round(a[k]+(b[k]-a[k])*f));
    /* relative luminance decides whether the numeral reads dark or white */
    const L=[0,1,2].map(k=>{const v=c[k]/255; return v<=0.04045?v/12.92:Math.pow((v+0.055)/1.055,2.4);});
    const lum=0.2126*L[0]+0.7152*L[1]+0.0722*L[2];
    return ['rgb('+c.join(',')+')', lum<0.30?'#fff':'#1e2a3d'];
  }
  card.querySelectorAll('.ba-hit').forEach(p=>{
    const n=+p.dataset.n||0;
    if(n>0) p.classList.add('has');
    const [fill,ink]=densColour(n>0?Math.sqrt(n/maxN):0);
    const num=p.nextElementSibling;
    if(n>0){ p.style.setProperty('--dens',fill); if(num) num.style.setProperty('--densink',ink); }
  });
  const dkMax=document.getElementById('dk-max');
  if(dkMax) dkMax.textContent=maxN;
  card.querySelectorAll('.ba-num').forEach(t=>{
    const tile=BRAIN_TILES[t.dataset.tile];
    if(tile&&tile.signs.length) t.classList.add('has');
  });
  const MARKS='.ba-hit,.ba-num,.deep-chip';

  /* which signs actually apply to the hemisphere on screen */
  function applies(lc){
    if(hemi==='L') return lc!=='nondominant'&&lc!=='right';
    return lc!=='dominant';
  }
  function sideNote(s){
    const lc=s.lc;
    if(lc==='contra') return 'contralateral to the focus \u2014 expressed on the '+(hemi==='L'?'right':'left')+' side';
    if(lc==='ipsi')   return 'ipsilateral to the focus \u2014 expressed on the '+(hemi==='L'?'left':'right')+' side';
    if(lc==='dominant')    return hemi==='L'?'dominant hemisphere (left assumed)':'expected from the left/dominant side';
    if(lc==='nondominant') return hemi==='L'?'expected from the right/non-dominant side':'non-dominant hemisphere';
    if(lc==='right')  return hemi==='L'?'reported from the right hemisphere':'right hemisphere';
    return s.lat||'';
  }

  function render(tid){
    const t=BRAIN_TILES[tid]; if(!t) return;
    sel=tid;
    card.querySelectorAll(MARKS).forEach(el=>
      el.classList.toggle('sel', el.dataset.tile===tid));
    /* land on a view that actually draws it (a traced set can span views) */
    if(!t.buried&&t.views&&t.views.length&&t.views.indexOf(curView())<0) showView(t.views[0]);
    const back=document.getElementById('bp-back');
    if(traced&&BRAIN_SIGNS[traced]){back.hidden=false; back.textContent='← '+BRAIN_SIGNS[traced].n;}
    else back.hidden=true;
    empty.hidden=true; traceBody.hidden=true; body.hidden=false;
    document.getElementById('bp-num').textContent=t.label;
    document.getElementById('bp-name').textContent=t.name;
    document.getElementById('bp-lobe').textContent=t.lobe;
    const n=t.signs.length;
    document.getElementById('bp-count').textContent=n?(n+(n===1?' sign':' signs')):'no signs in this dataset';
    hover.textContent=(t.bas.length?'BA '+t.label+' \u2014 ':'')+t.name;
    const list=document.getElementById('bp-list');
    if(!n){list.innerHTML='<div class="bp-empty" style="padding:18px">No sign in the current dataset is'+
      ' localized to this area. That is a gap in the evidence collected here, not proof the area is silent.</div>';revealPanel();return;}
    list.innerHTML=t.signs.map(s=>{
      const on=applies(s.lc);
      return '<button class="bp-row'+(on?'':' off')+'" data-sign="'+s.id+'">'+
        '<span class="bp-rname">'+esc(s.n)+
          '<span class="bp-chips">'+
            '<span class="bp-chip" style="background:'+(latBg[s.lc]||'#f3f4f6')+';color:'+(latColor[s.lc]||'#333')+
              ';border:1px solid '+(latColor[s.lc]||'#333')+'">'+(latLab[s.lc]||'?')+'</span>'+
            '<span class="bp-chip" style="background:#eef2f7;color:#5a6478">'+esc(s.ph)+'</span>'+
          '</span>'+
          '<span class="bp-side">'+esc(sideNote(s))+'</span>'+
        '</span>'+
        '<span class="bp-ev" style="background:'+(evColor[s.ev]||'#888')+'" title="Evidence '+s.ev+'">'+s.ev+'</span>'+
      '</button>';}).join('');
    list.scrollTop=0;
    revealPanel();
  }
  function esc(x){return String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

  function revealPanel(){
    /* On phones the one-column layout places the detail panel below the map. */
    if(window.matchMedia('(max-width:899px)').matches)
      requestAnimationFrame(()=>panel.scrollIntoView({behavior:'smooth',block:'center'}));
  }

  function clear(){
    sel=null; empty.hidden=false; body.hidden=true;
    hover.textContent='Select a numbered area';
    card.querySelectorAll('.sel').forEach(el=>el.classList.remove('sel'));
    clearTrace();
  }

  /* ---------- the mapping read backwards: one sign -> all of its areas ----------
     Same source as the figure itself (data/brodmann_map.json, gated by
     tools/validate_data.py), so a sign can never light up areas its card does not
     claim — and the panel states which rule put it there. */
  function clearTrace(){
    traced=null;
    card.classList.remove('tracing');
    card.querySelectorAll('.trace').forEach(el=>el.classList.remove('trace'));
    card.querySelectorAll('.seg-b[data-view]').forEach(b=>b.classList.remove('has-trace'));
    traceBody.hidden=true;
    document.getElementById('bp-back').hidden=true;
  }

  function traceSign(sid,scroll){
    const s=BRAIN_SIGNS[String(sid)];
    if(!s||!s.areas.length) return false;
    traced=String(sid); sel=null;
    const set=s.areas;
    card.classList.add('tracing');
    card.querySelectorAll('.sel').forEach(el=>el.classList.remove('sel'));
    card.querySelectorAll(MARKS).forEach(el=>
      el.classList.toggle('trace', set.indexOf(el.dataset.tile)>=0));

    /* flag every view that carries part of the set, and land on one that does */
    const per={};
    svgs.forEach(v=>{per[v.dataset.view]=0;});
    set.forEach(a=>{const t=BRAIN_TILES[a]; if(t)(t.views||[]).forEach(v=>{per[v]=(per[v]||0)+1;});});
    card.querySelectorAll('.seg-b[data-view]').forEach(b=>
      b.classList.toggle('has-trace',(per[b.dataset.view]||0)>0));
    /* land on the view showing most of the set, staying put on a tie */
    let best=null;
    Object.keys(per).forEach(v=>{if(best===null||per[v]>per[best]) best=v;});
    if(best&&per[best]&&per[curView()]<per[best]) showView(best);

    empty.hidden=true; body.hidden=true; traceBody.hidden=false;
    document.getElementById('bt-name').textContent=s.n;
    const nb=set.filter(a=>BRAIN_TILES[a]&&BRAIN_TILES[a].buried).length;
    document.getElementById('bt-count').textContent=
      set.length+(set.length===1?' Brodmann area':' Brodmann areas')+
      (nb?'  ·  '+nb+' with no surface':'');
    document.getElementById('bt-list').innerHTML=set.map(a=>{
      const t=BRAIN_TILES[a]; if(!t) return '';
      const where=t.buried?'no surface representation — chip below the figure'
        :(t.views||[]).map(v=>v.charAt(0).toUpperCase()+v.slice(1)).join(' · ');
      return '<button class="bt-row" data-tile="'+a+'"><span class="bt-num">'+esc(t.label)+'</span>'+
        '<span class="bt-name">'+esc(t.name)+'<span class="bt-where">'+esc(where)+'</span></span>'+
        '<span class="bt-n" title="signs this atlas localizes here">'+t.signs.length+'</span></button>';
    }).join('');
    const note = applies(s.lc) ? '' : 'Not expected from the hemisphere shown.';
    const why=document.getElementById('bt-why');
    why.textContent=note; why.hidden=!note;
    hover.textContent=s.n+' — '+set.length+(set.length===1?' area':' areas')+' highlighted';
    if(scroll){
      const f=card.closest('.brain-fold'); if(f&&!f.open) f.open=true;
      card.scrollIntoView({behavior:'smooth',block:'center'});
    }
    return true;
  }

  /* clicking an area */
  card.addEventListener('click',e=>{
    const hit=e.target.closest('.ba-hit,.ba-num,.deep-chip');
    if(!hit) return;
    const g=hit.closest('.lab-L,.lab-R');
    if(g&&((hemi==='R'&&g.classList.contains('lab-L'))||(hemi==='L'&&g.classList.contains('lab-R')))) return;
    /* stepping outside a traced set means the user has moved on */
    if(traced&&!hit.classList.contains('trace')) clearTrace();
    render(hit.dataset.tile);
  });
  card.addEventListener('keydown',e=>{
    if((e.key==='Enter'||e.key===' ')&&e.target.matches('.ba-hit,.ba-num')){
      e.preventDefault(); render(e.target.dataset.tile);}
    if(e.key==='Escape') clear();
  });
  card.addEventListener('mouseover',e=>{
    const hit=e.target.closest('.ba-hit,.ba-num');
    if(!hit) return;
    /* a traced set owns the caption; hovering past it must not steal the line */
    if(traced&&!hit.classList.contains('trace')) return;
    const t=BRAIN_TILES[hit.dataset.tile]; if(!t) return;
    const n=t.signs.length;
    hover.textContent=(t.bas.length?'BA '+t.label+' — ':'')+t.name+(n?'  ·  '+n+(n===1?' sign':' signs'):'  ·  no signs');
  });
  card.addEventListener('mouseleave',()=>{
    const t=traced&&BRAIN_SIGNS[traced];
    hover.textContent = t ? t.n+' — '+t.areas.length+(t.areas.length===1?' area':' areas')+' highlighted'
                          : (sel?BRAIN_TILES[sel].name:'Select a numbered area');});

  /* jump from the panel to the full sign card */
  panel.addEventListener('click',e=>{
    if(e.target.closest('#bp-back')){ if(traced) traceSign(traced); return; }
    const trow=e.target.closest('.bt-row');
    if(trow){ render(trow.dataset.tile); return; }
    const row=e.target.closest('.bp-row'); if(!row) return;
    const browseRow=Array.from(document.querySelectorAll((browseMode.value==='region'?'#region-browse-sections':'#browse-sections')+' .browse-sign')).find(node=>String(node.dataset.id)===String(row.dataset.sign));
    if(browseRow){
      const wrapper=browseRow.closest('.browse-sign-wrap');
      const regionSection=wrapper.closest('.region-section');
      if(regionSection){regionSection.classList.remove('collapsed');regionSection.querySelector('.region-toggle').setAttribute('aria-expanded','true');}
      let ancestor=wrapper.parentElement;
      while(ancestor){
        if(ancestor.classList&&ancestor.classList.contains('browse-subsection')){
          ancestor.classList.remove('collapsed');
          ancestor.querySelector(':scope > .browse-subtoggle')?.setAttribute('aria-expanded','true');
        }
        if(ancestor===regionBrowseSections||ancestor===browseSections)break;
        ancestor=ancestor.parentElement;
      }
      if(!wrapper.classList.contains('open'))void toggleBrowseSign(browseRow);
      wrapper.scrollIntoView({behavior:'smooth',block:'center'});
      return;
    }
    const el=Array.from(document.querySelectorAll('.sign')).find(node=>String(node.dataset.id)===String(row.dataset.sign)); if(!el) return;
    const sec=el.closest('.region-section'), sub=el.closest('.sub-block');
    if(sec) sec.classList.remove('collapsed');
    if(sub) sub.classList.remove('collapsed');
    if(!el.classList.contains('open')){const h=el.querySelector('.sign-head'); if(h) h.click();}
    el.scrollIntoView({behavior:'smooth',block:'center'});
    el.classList.add('match'); setTimeout(()=>el.classList.remove('match'),2200);
  });
  document.getElementById('bp-close').addEventListener('click',clear);
  document.getElementById('bt-close').addEventListener('click',clear);

  /* entry from a sign card: "Show on map" traces the whole set, a single
     Brodmann chip traces the set and opens that one area */
  document.addEventListener('click',e=>{
    const jump=e.target.closest('.map-jump');
    if(jump){ traceSign(jump.dataset.sign,true); return; }
    const chip=e.target.closest('.ba-chip');
    if(chip){
      const source=chip.closest('.sign,.browse-sign-wrap');
      if(source&&traceSign(source.dataset.id,true)) render(chip.dataset.ba);
    }
  });

  /* view + hemisphere switches */
  function showView(name){
    card.querySelectorAll('.seg-b[data-view]').forEach(x=>{
      const on=x.dataset.view===name; x.classList.toggle('active',on); x.setAttribute('aria-selected',on);});
    svgs.forEach(s=>s.classList.toggle('show',s.dataset.view===name));
  }
  function curView(){return (svgs.find(v=>v.classList.contains('show'))||svgs[0]).dataset.view;}
  card.querySelectorAll('.seg-b[data-view]').forEach(b=>
    b.addEventListener('click',()=>showView(b.dataset.view)));
  function applyHemi(){
    svgs.forEach(s=>{
      const flips = s.dataset.view==='lateral'||s.dataset.view==='medial';
      if(flips){
        /* set on the element, not via CSS: a CSS transform on SVG content is not
           honoured consistently, and on iOS the plate stayed put while the
           numerals moved */
        const w=s.viewBox.baseVal.width, g=s.querySelector('.plate');
        if(g){ if(hemi==='R') g.setAttribute('transform','translate('+w+',0) scale(-1,1)');
               else g.removeAttribute('transform'); }
      } else s.classList.toggle('show-R',hemi==='R');
      if(flips)
        s.querySelectorAll('.ba-num,.ba-hit,.brain-orient').forEach(t=>{
          const a=t.tagName==='circle'?'cx':'x';
          const mx=t.getAttribute('data-mx');
          if(mx===null) return;
          const want=hemi==='R'?'1':'';
          if((t.dataset.swapped||'')===want) return;
          t.setAttribute('data-mx',t.getAttribute(a)); t.setAttribute(a,mx);
          t.dataset.swapped=want;
        });
    });
    if(traced&&!traceBody.hidden) traceSign(traced);
    else if(sel) render(sel);
  }
  card.querySelectorAll('.seg-b[data-hemi]').forEach(b=>b.addEventListener('click',()=>{
    if(hemi===b.dataset.hemi) return;
    card.querySelectorAll('.seg-b[data-hemi]').forEach(x=>x.classList.toggle('active',x===b));
    hemi=b.dataset.hemi; applyHemi();
  }));
  document.getElementById('brain-density').addEventListener('change',e=>
    card.classList.toggle('dens',e.target.checked));

  /* ---------- label position editor ----------
     #edit-labels turns it on. Pick an area from the grouped list, the view zooms
     to it, then move it by dragging, by holding a D-pad (continuous nudge), or
     by tapping where it should go. Zoom works in every mode. */
  const LS='atlasLabelPos';
  let saved={}; try{saved=JSON.parse(localStorage.getItem(LS)||'{}');}catch(e){saved={};}
  svgs.forEach(s=>{ s.dataset.vb0 = s.getAttribute('viewBox'); });
  function vb0(svg){ return svg.dataset.vb0.split(/\s+/).map(Number); }
  function place(svg,tile,x,y){
    const w=vb0(svg)[2];
    /* the hit disc rides with its numeral, so what you click stays where you put it */
    const move=(el,nx)=>{
      if(el.tagName==='circle'){el.setAttribute('cx',nx);el.setAttribute('cy',y);}
      else {el.setAttribute('x',nx);el.setAttribute('y',y);}
      el.setAttribute('data-mx',w-nx);
    };
    svg.querySelectorAll('.ba-labels:not(.lab-R) .ba-num,.ba-labels:not(.lab-R) .ba-hit')
       .forEach(t=>{if(t.dataset.tile===tile) move(t,x);});
    svg.querySelectorAll('.lab-R .ba-num,.lab-R .ba-hit')
       .forEach(t=>{if(t.dataset.tile===tile) move(t,w-x);});
  }
  function applySaved(){
    svgs.forEach(s=>{const o=saved[s.dataset.view]||{};
      Object.keys(o).forEach(k=>place(s,k,o[k][0],o[k][1]));});
  }
  applySaved();
  if(location.hash.toLowerCase().indexOf('edit')<0) return;
  document.body.classList.add('lbledit');

  const ed=document.createElement('div'); ed.className='lbl-editor';
  ed.innerHTML=
    '<div class="le-row"><select id="le-pick" aria-label="Brodmann area"></select>'+
    '<button id="le-fold" title="collapse">▾</button></div>'+
    '<div class="le-body">'+
      '<div class="le-modes" role="group" aria-label="Move mode">'+
        '<button data-mode="drag" class="on">Drag</button>'+
        '<button data-mode="nudge">Nudge</button>'+
        '<button data-mode="place">Place</button></div>'+
      '<div class="le-row le-zoom"><button id="le-out">−</button>'+
        '<span id="le-z">1.0×</span><button id="le-in">+</button>'+
        '<button id="le-fit">Fit</button></div>'+
      '<div id="lbl-read">Pick an area to begin</div>'+
      '<div class="le-row"><button id="le-done">Done \u2713</button>'+
      '<button id="lbl-copy">Copy positions</button>'+
      '<button id="lbl-reset">Reset</button></div>'+
    '</div>';
  document.body.appendChild(ed);
  const pad=document.createElement('div'); pad.className='dpad'; pad.hidden=true;
  pad.innerHTML='<button data-d="u">▲</button><button data-d="l">◀</button>'+
    '<button data-d="c" title="hold an arrow to glide">●</button>'+
    '<button data-d="r">▶</button><button data-d="d">▼</button>';
  document.body.appendChild(pad);

  const read=ed.querySelector('#lbl-read'), pick=ed.querySelector('#le-pick');
  let mode='drag', cur=null, zoom=1, drag=null;
  const shown=()=>svgs.find(s=>s.classList.contains('show'));

  function fillPicker(){
    const svg=shown(); if(!svg) return;
    const byLobe={};
    svg.querySelectorAll('.ba-labels:not(.lab-R) .ba-num').forEach(t=>{
      const k=t.dataset.tile, inf=BRAIN_TILES[k]; if(!inf) return;
      (byLobe[inf.lobe]=byLobe[inf.lobe]||[]).push([k,inf.label,inf.name]);
    });
    let h='<option value="">Area…</option>';
    Object.keys(byLobe).sort().forEach(lo=>{
      h+='<optgroup label="'+lo+'">';
      byLobe[lo].sort((a,b)=>a[1].localeCompare(b[1],undefined,{numeric:true}))
        .forEach(r=>{h+='<option value="'+r[0]+'">'+r[1]+' — '+r[2].split('(')[0].trim()+'</option>';});
      h+='</optgroup>';
    });
    pick.innerHTML=h; if(cur) pick.value=cur;
  }
  function labelEl(){ const svg=shown(); if(!svg||!cur) return null;
    return svg.querySelector('.ba-labels:not(.lab-R) .ba-num[data-tile="'+cur+'"]'); }
  function setView(cx,cy){
    const svg=shown(); if(!svg) return;
    const [,,w,h]=vb0(svg), nw=w/zoom, nh=h/zoom;
    svg.setAttribute('viewBox',(cx-nw/2)+' '+(cy-nh/2)+' '+nw+' '+nh);
    ed.querySelector('#le-z').textContent=zoom.toFixed(1)+'×';
  }
  function recenter(){
    const t=labelEl(); const svg=shown(); if(!svg) return;
    if(zoom===1){ svg.setAttribute('viewBox',svg.dataset.vb0); ed.querySelector('#le-z').textContent='1.0×'; return; }
    if(t) setView(+t.getAttribute('x'), +t.getAttribute('y'));
  }
  function select(tile){
    cur=tile;
    document.body.classList.toggle('focusing', !!tile);
    svgs.forEach(s=>s.querySelectorAll('.ba-num,.ba-hit').forEach(t=>
      t.classList.toggle('edit-sel', !!tile && t.dataset.tile===tile)));
    pad.hidden = !(mode==='nudge' && cur);
    const t=labelEl();
    if(t){ if(zoom<2.2) zoom=2.2; setView(+t.getAttribute('x'), +t.getAttribute('y')); say(); }
  }
  function say(){ const t=labelEl(); if(!t){read.textContent='Pick an area to begin';return;}
    read.textContent=shown().dataset.view+' '+cur+'  →  ('+
      Math.round(t.getAttribute('x'))+', '+Math.round(t.getAttribute('y'))+')'; }
  function store(x,y){ const svg=shown(); if(!svg||!cur) return;
    (saved[svg.dataset.view]=saved[svg.dataset.view]||{})[cur]=[Math.round(x),Math.round(y)];
    localStorage.setItem(LS,JSON.stringify(saved)); say(); }
  function moveTo(x,y){ const svg=shown(); if(!svg||!cur) return; place(svg,cur,x,y); store(x,y); }
  function toSvg(svg,e){ const p=svg.createSVGPoint(); p.x=e.clientX; p.y=e.clientY;
    return p.matrixTransform(svg.getScreenCTM().inverse()); }

  fillPicker();
  pick.addEventListener('change',e=>select(e.target.value||null));
  ed.querySelector('#le-fold').addEventListener('click',()=>ed.classList.toggle('folded'));
  ed.querySelectorAll('.le-modes button').forEach(b=>b.addEventListener('click',()=>{
    mode=b.dataset.mode;
    ed.querySelectorAll('.le-modes button').forEach(x=>x.classList.toggle('on',x===b));
    pad.hidden = !(mode==='nudge' && cur);
    document.body.classList.toggle('lbl-place', mode==='place');
  }));
  ed.querySelector('#le-in').addEventListener('click',()=>{zoom=Math.min(8,zoom*1.5);recenter();});
  ed.querySelector('#le-out').addEventListener('click',()=>{zoom=Math.max(1,zoom/1.5);recenter();});
  ed.querySelector('#le-fit').addEventListener('click',()=>{zoom=1;recenter();});
  card.querySelectorAll('.seg-b[data-view]').forEach(b=>b.addEventListener('click',()=>{
    setTimeout(()=>{zoom=1;cur=null;pad.hidden=true;fillPicker();recenter();say();},0);}));

  /* continuous nudge while an arrow is held; step scales with zoom */
  let rep=null;
  function step(d){ const t=labelEl(); if(!t) return;
    const k=1.1/zoom, dx=(d==='l'?-k:d==='r'?k:0), dy=(d==='u'?-k:d==='d'?k:0);
    moveTo(+t.getAttribute('x')+dx, +t.getAttribute('y')+dy); recenter(); }
  pad.addEventListener('pointerdown',e=>{ const b=e.target.closest('button'); if(!b) return;
    e.preventDefault(); const d=b.dataset.d; if(d==='c') return;
    step(d); rep=setInterval(()=>step(d),40); });
  ['pointerup','pointercancel','pointerleave'].forEach(ev=>
    window.addEventListener(ev,()=>{ if(rep){clearInterval(rep); rep=null;} }));

  /* drag, and tap-to-place */
  card.addEventListener('pointerdown',e=>{
    const svg=e.target.closest('.brain-svg'); if(!svg) return;
    if(mode==='place'){
      if(!cur) return; e.preventDefault(); e.stopPropagation();
      const p=toSvg(svg,e); moveTo(p.x,p.y); return;
    }
    const t=e.target.closest('.ba-hit'); if(!t||mode!=='drag') return;
    e.preventDefault(); e.stopPropagation();
    if(t.dataset.tile!==cur){ cur=t.dataset.tile; pick.value=cur; select(cur); }
    drag={svg:svg}; t.classList.add('drag');
  },true);
  window.addEventListener('pointermove',e=>{ if(!drag) return;
    const p=toSvg(drag.svg,e); moveTo(p.x,p.y); });
  window.addEventListener('pointerup',()=>{ if(drag){
    card.querySelectorAll('.ba-hit.drag').forEach(t=>t.classList.remove('drag')); drag=null; }});
  window.addEventListener('keydown',e=>{
    if(!cur||['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].indexOf(e.key)<0) return;
    e.preventDefault(); const t=labelEl(); if(!t) return;
    const k=e.shiftKey?10:1;
    moveTo(+t.getAttribute('x')+(e.key==='ArrowLeft'?-k:e.key==='ArrowRight'?k:0),
           +t.getAttribute('y')+(e.key==='ArrowUp'?-k:e.key==='ArrowDown'?k:0));
    recenter(); });

  ed.querySelector('#le-done').addEventListener('click',()=>{
    cur=null; pick.value=''; pad.hidden=true;
    document.body.classList.remove('focusing');
    svgs.forEach(s=>s.querySelectorAll('.ba-num,.ba-hit').forEach(t=>t.classList.remove('edit-sel')));
    read.textContent='Saved \u2014 pick another area';
  });
  ed.querySelector('#lbl-copy').addEventListener('click',()=>{
    let out='LABEL_POS = {\n';
    svgs.forEach(s=>{ const seen={}, parts=[];
      s.querySelectorAll('.ba-labels:not(.lab-R) .ba-num').forEach(t=>{
        const k=t.dataset.tile; if(seen[k])return; seen[k]=1;
        parts.push('"'+k+'": ('+Math.round(t.getAttribute('x'))+', '+Math.round(t.getAttribute('y'))+')');
      });
      if(parts.length) out+=' "'+s.dataset.view+'": {\n   '+parts.join(', ')+',\n },\n'; });
    out+='}\n';
    function box(){ let ta=ed.querySelector('#lbl-out');
      if(!ta){ta=document.createElement('textarea');ta.id='lbl-out';ed.querySelector('.le-body').appendChild(ta);}
      ta.value=out; ta.focus(); ta.select(); read.textContent='Select all and copy from the box'; }
    if(navigator.clipboard&&navigator.clipboard.writeText)
      navigator.clipboard.writeText(out).then(()=>{read.textContent='Copied to clipboard';},box);
    else box();
  });
  ed.querySelector('#lbl-reset').addEventListener('click',()=>{
    localStorage.removeItem(LS); location.reload(); });
})();

const searchInput=document.getElementById('search-input');
const searchSubmit=document.getElementById('search-submit');
const searchClear=document.getElementById('search-clear');
const browseMode=document.getElementById('browse-mode');
const regionOrderMode=document.getElementById('region-order-mode');
const regionOrderField=document.getElementById('region-order-field');
const fRegion=document.getElementById('filter-region');
const fPhase=document.getElementById('filter-phase');
const fLat=document.getElementById('filter-lat');
const fEvid=document.getElementById('filter-evid');
const resultCount=document.getElementById('result-count');
const noResults=document.getElementById('no-results');
const regionView=document.getElementById('region-view');
const regionBrowseSections=document.getElementById('region-browse-sections');
const semiologyView=document.getElementById('semiology-view');
const browseSections=document.getElementById('browse-sections');
const browseNote=document.getElementById('browse-note');
const sourceSignStore=document.getElementById('source-sign-store');
const signs=Array.from(sourceSignStore.querySelectorAll('.sign'));
const sections=Array.from(sourceSignStore.querySelectorAll('.region-section'));
const signCopiesById=new Map();
const totalRegionIds={};
signs.forEach(sign=>{
  const id=String(sign.dataset.id);
  if(!signCopiesById.has(id)) signCopiesById.set(id,[]);
  signCopiesById.get(id).push(sign);
  const region=sign.dataset.region;
  if(!totalRegionIds[region]) totalRegionIds[region]=new Set();
  totalRegionIds[region].add(id);
});
const canonicalSigns=new Map(Array.from(signCopiesById,([id,copies])=>[id,copies[0]]));
const uniqueSignCount=canonicalSigns.size;
let appliedQuery='';
let builtBrowseMode='';
let builtRegionMode='';

const fragmentCache=new Map();
function loadFragment(path){
  if(!fragmentCache.has(path)){
    fragmentCache.set(path,fetch(path,{cache:'no-store'}).then(response=>{
      if(!response.ok) throw new Error('HTTP '+response.status);
      return response.text();
    }));
  }
  return fragmentCache.get(path);
}
function bindDetailPanels(sign){
  sign.querySelectorAll('.detail details').forEach(panel=>{
    if(panel.dataset.heightBound) return;
    panel.dataset.heightBound='true';
    panel.addEventListener('toggle',()=>{
      if(!sign.classList.contains('open')) return;
      requestAnimationFrame(()=>{
        const detail=sign.querySelector('.detail');
        detail.style.maxHeight=detail.scrollHeight+'px';
      });
    });
  });
}
document.addEventListener('click',event=>{
  const control=event.target.closest('[data-ev-action]');
  if(!control) return;
  event.preventDefault();
  event.stopPropagation();
  const shell=control.closest('.evidence-history-shell');
  if(!shell) return;
  const open=control.dataset.evAction==='expand';
  shell.querySelectorAll('details.ev-trace,details.ev-stats,details.history-results,details.syn-family').forEach(panel=>{ panel.open=open; });
  const sign=control.closest('.sign');
  if(sign&&sign.classList.contains('open')) requestAnimationFrame(()=>{
    const detail=sign.querySelector('.detail');
    detail.style.maxHeight=detail.scrollHeight+'px';
  });
});
document.addEventListener('click',event=>{
  const control=event.target.closest('[data-syn-action]');
  if(!control) return;
  event.preventDefault();
  event.stopPropagation();
  const shell=control.closest('.syn-family-shell');
  if(!shell) return;
  const open=control.dataset.synAction==='expand';
  shell.querySelectorAll('details.syn-family').forEach(panel=>{panel.open=open;});
  const sign=control.closest('.sign');
  if(sign&&sign.classList.contains('open')) requestAnimationFrame(()=>{
    const detail=sign.querySelector('.detail');
    detail.style.maxHeight=detail.scrollHeight+'px';
  });
});
async function ensureSignDetail(sign){
  const d=sign.querySelector('.detail');
  const path=d.dataset.detailPath;
  if(!path||d.dataset.loaded==='true') return d;
  try{
    d.innerHTML=await loadFragment(path);
    d.dataset.loaded='true';
    bindDetailPanels(sign);
  }catch(error){
    d.innerHTML='<div class="detail-loading">Details could not be loaded. Reload the page and try again.</div>';
  }
  return d;
}
async function openSign(sign){
  const d=sign.querySelector('.detail');
  sign.classList.add('open');
  sign.querySelector('.sign-head').setAttribute('aria-expanded','true');
  d.style.maxHeight='48px';
  await ensureSignDetail(sign);
  if(sign.classList.contains('open')) d.style.maxHeight=d.scrollHeight+'px';
}
function closeSign(sign){
  const d=sign.querySelector('.detail');
  sign.classList.remove('open');
  sign.querySelector('.sign-head').setAttribute('aria-expanded','false');
  d.style.maxHeight='0px';
}
function toggleSign(sign){ sign.classList.contains('open')?closeSign(sign):void openSign(sign); }

// row click
signs.forEach(sign=>{
  sign.querySelector('.sign-head').addEventListener('click',()=>toggleSign(sign));
});

// Nested reviewed-source panels change a card's height after it has opened.
signs.forEach(bindDetailPanels);

// region collapse
sections.forEach(sec=>{
  sec.querySelector('.region-toggle').addEventListener('click',()=>{
    const collapsed=sec.classList.toggle('collapsed');
    sec.querySelector('.region-toggle').setAttribute('aria-expanded',!collapsed);
  });
});

// subregion collapse
document.querySelectorAll('.sub-toggle').forEach(btn=>{
  btn.addEventListener('click',()=>{
    const sb=btn.closest('.sub-block');
    const collapsed=sb.classList.toggle('collapsed');
    btn.setAttribute('aria-expanded',!collapsed);
    if(!collapsed){
      sb.querySelectorAll('.sign.open').forEach(s=>{const d=s.querySelector('.detail');d.style.maxHeight=d.scrollHeight+'px';});
    }
  });
});

// region-jump pills
document.querySelectorAll('.pill').forEach(p=>{
  p.addEventListener('click',()=>{
    if(browseMode.value!=='region') setBrowseMode('region');
    const sec=document.getElementById('browse-'+p.dataset.target);
    if(sec){ sec.classList.remove('collapsed'); sec.scrollIntoView({behavior:'smooth',block:'start'}); }
  });
});

// Filtering is deliberately submit-based. Typing does not touch the full sign
// list; Search or Enter applies the completed query once, and no result card is
// opened automatically.
function itemMatches(item){
  const reg=fRegion.value,ph=fPhase.value,lat=fLat.value,ev=fEvid.value;
  if(reg && item.dataset.region!==reg) return false;
  if(ph && !((item.dataset.phaseSearch||item.dataset.phase||'').toLowerCase().includes(ph.toLowerCase()))) return false;
  if(lat && item.dataset.latcode!==lat) return false;
  if(ev && item.dataset.evid!==ev) return false;
  const searchable=(SIGN_SEARCH[String(item.dataset.id)]||'')+' '+(item.dataset.search||'');
  if(appliedQuery && !searchable.includes(appliedQuery)) return false;
  return true;
}

function idMatches(id){
  return (signCopiesById.get(String(id))||[]).some(itemMatches);
}

const signCollator=new Intl.Collator(undefined,{numeric:true,sensitivity:'base'});
function visibleSignName(value){
  const original=String(value||'').trim();
  const stripped=original.replace(/^Focal\s+/i,'').trim();
  return stripped===original||!stripped?original:stripped.charAt(0).toLocaleUpperCase()+stripped.slice(1);
}
function signName(id){ return visibleSignName(canonicalSigns.get(String(id)).querySelector('.sign-name').textContent.trim()); }
function sortSignIds(ids,descending=false){
  const values=Array.from(new Set(ids.map(String))).filter(id=>canonicalSigns.has(id));
  values.sort((a,b)=>signCollator.compare(signName(a),signName(b)));
  if(descending) values.reverse();
  return values;
}

function browseGroups(mode){
  if(mode==='az'||mode==='za'){
    const descending=mode==='za';
    const grouped=new Map();
    sortSignIds(Array.from(canonicalSigns.keys()),descending).forEach(id=>{
      const match=signName(id).match(/[A-Za-z0-9]/);
      const key=match?match[0].toUpperCase():'#';
      if(!grouped.has(key)) grouped.set(key,[]);
      grouped.get(key).push(id);
    });
    const keys=Array.from(grouped.keys()).sort(signCollator.compare);
    if(descending) keys.reverse();
    return keys.map(label=>({label,sign_ids:grouped.get(label)}));
  }
  const scheme=mode==='ilae'?'ILAE_SEIZURE_2025':'LUDERS_5D_2005';
  const tree=CLASSIFICATION_TREES[scheme]||{groups:[]};
  const mapped=new Set();
  const groups=(tree.groups||[]).filter(group=>{
    const ids=sortSignIds(group.all_sign_ids||group.sign_ids||[]);
    ids.forEach(id=>mapped.add(id));
    return ids.length;
  });
  const unclassified=sortSignIds(Array.from(canonicalSigns.keys()).filter(id=>!mapped.has(id)));
  if(unclassified.length) groups.push({
    node_id:scheme+':UNCLASSIFIED',label:'Not yet classified in this scheme',
    sign_ids:unclassified,all_sign_ids:unclassified,children:[]
  });
  return groups;
}

function appendBrowseSign(parent,id,parentLabel='',contextRegion=''){
  const source=canonicalSigns.get(String(id));
  if(!source) return;
  const wrapper=document.createElement('div'); wrapper.className='browse-sign-wrap'; wrapper.dataset.id=id;
  if(contextRegion) wrapper.dataset.contextRegion=contextRegion;
  const row=document.createElement('button'); row.type='button'; row.className='browse-sign'; row.dataset.id=id;
  row.setAttribute('aria-expanded','false');
  wrapper.style.setProperty('--accent',source.style.getPropertyValue('--accent')||'#8ca0b8');
  const arrow=document.createElement('span'); arrow.className='browse-arrow'; arrow.textContent='›';
  const label=document.createElement('span'); label.className='browse-sign-name';
  const originalName=signName(String(id));
  const lowerName=originalName.toLocaleLowerCase();
  const lowerParent=String(parentLabel||'').toLocaleLowerCase();
  label.textContent=lowerName===lowerParent
    ? 'General '+lowerParent+' findings'
    : (lowerParent==='aura'&&lowerName==='aura present'?'Presence of a preceding aura':originalName);
  const meta=document.createElement('span'); meta.className='browse-meta';
  const phase=source.dataset.phaseSearch||source.dataset.phase||'';
  compactPhaseLabels(phase).forEach(value=>{
    const phaseChip=document.createElement('span'); phaseChip.className='browse-meta-chip'; phaseChip.textContent=value;
    meta.append(phaseChip);
  });
  const regions=Array.from(new Set((source.dataset.regions||source.dataset.region||'').split('|').filter(Boolean)));
  regions.slice(0,2).forEach(region=>{
    const chip=document.createElement('span'); chip.className='browse-meta-chip region'; chip.textContent=region;
    meta.append(chip);
  });
  if(regions.length>2){
    const more=document.createElement('span'); more.className='browse-meta-chip region'; more.textContent='+'+(regions.length-2);
    meta.append(more);
  }
  const detail=document.createElement('div'); detail.className='browse-detail'; detail.hidden=true;
  row.append(arrow,label,meta); wrapper.append(row,detail); parent.append(wrapper);
}

function compactPhaseLabels(value){
  const text=String(value||'').toLocaleLowerCase();
  if(!text||text==='multiple phases') return [];
  const labels=[];
  const add=label=>{if(!labels.includes(label)) labels.push(label);};
  const isPre=text.includes('preictal')||text.includes('pre-ictal');
  const isPost=text.includes('postictal')||text.includes('post-ictal');
  const isInter=text.includes('interictal');
  if(text.includes('aura')) add('Aura');
  if(isPre) add('Preictal');
  if(isPost) add('Postictal');
  if(isInter) add('Interictal');
  if(!isPre&&!isPost&&!isInter&&(text.includes('ictal')||text.includes('seizure onset'))) add('Ictal');
  return labels.slice(0,2);
}

function eligibleIds(ids,allowed,seen,take=false){
  const values=sortSignIds(ids||[]).filter(id=>(!allowed||allowed.has(id))&&(!seen||!seen.has(id)));
  if(take&&seen) values.forEach(id=>seen.add(id));
  return values;
}

function appendClassificationNode(parent,node,allowed=null,seen=null,contextRegion=''){
  const nodeIds=eligibleIds(node.all_sign_ids||node.sign_ids||[],allowed,seen);
  if(!nodeIds.length) return;
  const direct=node.sign_ids||[];
  const broad=node.broad_sign_ids||[];
  const children=(node.children||[]).filter(child=>eligibleIds(child.all_sign_ids||child.sign_ids||[],allowed,seen).length);
  const subsection=document.createElement('div'); subsection.className='browse-subsection collapsed';
  const toggle=document.createElement('button');
  toggle.className='browse-subtoggle'; toggle.type='button'; toggle.setAttribute('aria-expanded','false');
  const chev=document.createElement('span'); chev.className='browse-chev'; chev.textContent='▼';
  const name=document.createElement('span'); name.className='browse-name'; name.textContent=node.label;
  const count=document.createElement('span'); count.className='browse-count';
  count.textContent=nodeIds.length;
  const body=document.createElement('div'); body.className='browse-subbody';
  toggle.append(chev,name,count); subsection.append(toggle,body);
  children.forEach(child=>appendClassificationNode(body,child,allowed,seen,contextRegion));
  const general=eligibleIds([...direct,...broad],allowed,seen,true);
  general.forEach(id=>appendBrowseSign(body,id,node.label,contextRegion));
  parent.append(subsection);
}

function appendSignBucket(parent,label,ids,contextRegion='',extraClass=''){
  const values=sortSignIds(ids||[]);
  if(!values.length) return;
  const subsection=document.createElement('div'); subsection.className=('browse-subsection broad-only collapsed '+extraClass).trim();
  const toggle=document.createElement('button');
  toggle.className='browse-subtoggle'; toggle.type='button'; toggle.setAttribute('aria-expanded','false');
  const chev=document.createElement('span'); chev.className='browse-chev'; chev.textContent='▼';
  const name=document.createElement('span'); name.className='browse-name';
  name.textContent=label;
  const count=document.createElement('span'); count.className='browse-count'; count.textContent=values.length;
  const body=document.createElement('div'); body.className='browse-subbody';
  values.forEach(id=>appendBrowseSign(body,id,label,contextRegion));
  toggle.append(chev,name,count); subsection.append(toggle,body); parent.append(subsection);
}

function appendBroadClassificationBucket(parent,label,ids,contextRegion=''){
  appendSignBucket(parent,'General or source-wide '+String(label||'').toLocaleLowerCase()+' findings',ids,contextRegion,'broad-mappings');
}

function buildBrowseView(mode){
  if(builtBrowseMode===mode) return;
  builtBrowseMode=mode;
  browseSections.replaceChildren();
  browseNote.textContent=(mode==='az'||mode==='za')
    ? 'Alphabetical view of the same evidence-backed signs.'
    : 'Grouped by the selected classification; unassigned signs remain visible.';
  const fragment=document.createDocumentFragment();
  browseGroups(mode).forEach((group,index)=>{
    const section=document.createElement('section');
    section.className='browse-section'+(index?' collapsed':'');
    const toggle=document.createElement('button');
    toggle.className='browse-toggle'; toggle.type='button'; toggle.setAttribute('aria-expanded',index?'false':'true');
    const chev=document.createElement('span'); chev.className='browse-chev'; chev.textContent='▼';
    const name=document.createElement('span'); name.className='browse-name'; name.textContent=group.label;
    const groupIds=sortSignIds(group.all_sign_ids||group.sign_ids||[]);
    const count=document.createElement('span'); count.className='browse-count'; count.textContent=groupIds.length;
    toggle.append(chev,name,count);
    const body=document.createElement('div'); body.className='browse-body';
    if(mode==='az'||mode==='za') groupIds.forEach(id=>appendBrowseSign(body,id));
    else {
      const seen=new Set();
      (group.children||[]).forEach(child=>appendClassificationNode(body,child,null,seen));
      const general=eligibleIds([...(group.sign_ids||[]),...(group.broad_sign_ids||[])],null,seen,true);
      appendBroadClassificationBucket(body,group.label,general);
    }
    section.append(toggle,body); fragment.append(section);
  });
  browseSections.append(fragment);
}

function ludersRegionCategories(regionIds){
  const tree=CLASSIFICATION_TREES.LUDERS_5D_2005||{groups:[]};
  const preferred=['Aura','Seizure','Lateralizing signs','Diagnostic signs'];
  const ordered=preferred.map(label=>(tree.groups||[]).find(group=>group.label===label)).filter(Boolean);
  const used=new Set();
  const categories=[];
  ordered.forEach(group=>{
    const ids=sortSignIds(group.all_sign_ids||group.sign_ids||[]).filter(id=>regionIds.has(id));
    if(!ids.length) return;
    ids.forEach(id=>used.add(id));
    categories.push({label:group.label,group,ids});
  });
  const other=sortSignIds(Array.from(regionIds).filter(id=>!used.has(id)));
  if(other.length) categories.push({label:'Other signs',group:null,ids:other});
  return categories;
}

function appendRegionCategoryContent(parent,category,mode,region){
  const allowed=new Set(category.ids),seen=new Set();
  if(mode==='az'||!category.group){
    category.ids.forEach(id=>appendBrowseSign(parent,id,category.label,region));
    return;
  }
  if(mode==='luders'){
    (category.group.children||[]).forEach(child=>appendClassificationNode(parent,child,allowed,seen,region));
    const general=eligibleIds([...(category.group.sign_ids||[]),...(category.group.broad_sign_ids||[])],allowed,seen,true);
    appendBroadClassificationBucket(parent,category.label,general,region);
  }else{
    const ilae=CLASSIFICATION_TREES.ILAE_SEIZURE_2025||{groups:[]};
    (ilae.groups||[]).forEach(group=>appendClassificationNode(parent,group,allowed,seen,region));
  }
  const remaining=eligibleIds(category.ids,allowed,seen,true);
  if(mode==='luders') appendSignBucket(parent,'Not yet placed within Lüders 5D',remaining,region,'unclassified-mappings');
  else if(mode==='ilae') appendSignBucket(parent,'Not yet placed within ILAE 2025',remaining,region,'unclassified-mappings');
  else remaining.forEach(id=>appendBrowseSign(parent,id,category.label,region));
}

function buildRegionBrowseView(mode){
  if(builtRegionMode===mode) return;
  builtRegionMode=mode;
  regionBrowseSections.replaceChildren();
  const fragment=document.createDocumentFragment();
  sections.forEach((sourceSection,index)=>{
    const region=sourceSection.dataset.region;
    const regionIds=totalRegionIds[region]||new Set();
    if(!regionIds.size) return;
    const section=document.createElement('section');
    section.className='region-section'+(index?' collapsed':'');
    section.id='browse-'+sourceSection.id;
    section.dataset.region=region;
    const sourceToggle=sourceSection.querySelector('.region-toggle');
    const toggle=document.createElement('button');toggle.className='region-toggle';toggle.type='button';
    toggle.style.setProperty('--rc',sourceToggle.style.getPropertyValue('--rc'));
    toggle.setAttribute('aria-expanded',index?'false':'true');
    const chev=document.createElement('span');chev.className='region-chev';chev.textContent='▼';
    const name=document.createElement('span');name.className='region-name';name.textContent=region.toLocaleUpperCase();
    const count=document.createElement('span');count.className='region-count';count.textContent=regionIds.size;
    toggle.append(chev,name,count);
    const body=document.createElement('div');body.className='region-body';
    ludersRegionCategories(regionIds).forEach(category=>{
      const subsection=document.createElement('div');subsection.className='browse-subsection region-category collapsed';
      const subToggle=document.createElement('button');subToggle.className='browse-subtoggle';subToggle.type='button';subToggle.setAttribute('aria-expanded','false');
      const subChev=document.createElement('span');subChev.className='browse-chev';subChev.textContent='▼';
      const subName=document.createElement('span');subName.className='browse-name';subName.textContent=category.label;
      const subCount=document.createElement('span');subCount.className='browse-count';subCount.textContent=category.ids.length;
      const subBody=document.createElement('div');subBody.className='browse-subbody';
      appendRegionCategoryContent(subBody,category,mode,region);
      subToggle.append(subChev,subName,subCount);subsection.append(subToggle,subBody);body.append(subsection);
    });
    section.append(toggle,body);fragment.append(section);
  });
  regionBrowseSections.append(fragment);
}

function filterRegionView(){
  buildRegionBrowseView(regionOrderMode.value);
  const active=!!(appliedQuery||fRegion.value||fPhase.value||fLat.value||fEvid.value);
  const visibleIds=new Set();
  const perRegionIds={};
  regionBrowseSections.querySelectorAll('.browse-sign-wrap').forEach(wrapper=>{
    const id=String(wrapper.dataset.id),region=wrapper.dataset.contextRegion;
    const show=(signCopiesById.get(id)||[]).some(item=>item.dataset.region===region&&itemMatches(item));
    wrapper.style.display=show?'':'none';
    if(show){
      visibleIds.add(id);
      if(!perRegionIds[region]) perRegionIds[region]=new Set();
      perRegionIds[region].add(id);
    }else if(wrapper.classList.contains('open')){
      wrapper.classList.remove('open');wrapper.querySelector('.browse-detail').hidden=true;
    }
  });
  Array.from(regionBrowseSections.querySelectorAll('.browse-subsection')).reverse().forEach(subsection=>{
    const count=new Set(Array.from(subsection.querySelectorAll('.browse-sign-wrap')).filter(row=>row.style.display!=='none').map(row=>row.dataset.id)).size;
    subsection.style.display=count?'':'none';
    const counter=subsection.querySelector(':scope > .browse-subtoggle .browse-count');if(counter)counter.textContent=count;
  });
  let opened=false;
  regionBrowseSections.querySelectorAll('.region-section').forEach(sec=>{
    const ids=perRegionIds[sec.dataset.region];const count=ids?ids.size:0;
    sec.style.display=count?'':'none';
    sec.querySelector('.region-count').textContent=count;
    const shouldOpen=count&&(!active? !opened:!opened);
    sec.classList.toggle('collapsed',!shouldOpen);
    sec.querySelector('.region-toggle').setAttribute('aria-expanded',shouldOpen?'true':'false');
    if(shouldOpen)opened=true;
  });
  document.querySelectorAll('[data-region]').forEach(el=>{
    if(el.tagName==='SPAN'&&(el.closest('.region-count')||el.closest('.pill-count'))){
      const ids=perRegionIds[el.dataset.region];
      el.textContent=active?(ids?ids.size:0):(totalRegionIds[el.dataset.region]?.size||0);
    }
  });
  document.querySelectorAll('.pill').forEach(p=>{
    const sec=document.getElementById('browse-'+p.dataset.target);
    p.style.opacity=(sec&&sec.style.display!=='none')?'1':'.4';
  });
  return visibleIds;
}

function filterBrowseView(){
  const active=!!(appliedQuery||fRegion.value||fPhase.value||fLat.value||fEvid.value);
  const visibleIds=new Set();
  let opened=false;
  browseSections.querySelectorAll('.browse-section').forEach(section=>{
    let count=0;
    section.querySelectorAll('.browse-sign').forEach(row=>{
      const show=idMatches(row.dataset.id);
      const wrapper=row.closest('.browse-sign-wrap');
      wrapper.style.display=show?'':'none';
      if(!show&&wrapper.classList.contains('open')) toggleBrowseSign(row);
      if(show){ count++; visibleIds.add(String(row.dataset.id)); }
    });
    section.style.display=count?'':'none';
    section.querySelector('.browse-count').textContent=count;
    Array.from(section.querySelectorAll('.browse-subsection')).reverse().forEach(subsection=>{
      const subcount=Array.from(subsection.querySelectorAll('.browse-sign-wrap')).filter(wrapper=>wrapper.style.display!=='none').length;
      subsection.style.display=subcount?'':'none';
      const counter=subsection.querySelector(':scope > .browse-subtoggle .browse-count');
      if(counter) counter.textContent=subcount;
    });
    const shouldOpen=count>0&&(!active?!opened:!opened);
    section.classList.toggle('collapsed',!shouldOpen);
    section.querySelector('.browse-toggle').setAttribute('aria-expanded',shouldOpen?'true':'false');
    if(shouldOpen) opened=true;
  });
  return visibleIds;
}

function filterAll(){
  const visibleIds=browseMode.value==='region'?filterRegionView():filterBrowseView();
  const visible=visibleIds.size;
  const active=!!(appliedQuery||fRegion.value||fPhase.value||fLat.value||fEvid.value);
  resultCount.textContent=visible+' of '+uniqueSignCount+' signs shown';
  document.body.classList.toggle('filtering',active);
  noResults.style.display=visible===0?'block':'none';
  refreshStudyFamilyFilter(visibleIds,active);
}

function setBrowseMode(mode){
  const regional=mode==='region';
  browseMode.value=mode;
  regionView.hidden=!regional; semiologyView.hidden=regional;
  regionOrderField.hidden=!regional;
  document.body.classList.toggle('alt-browse',!regional);
  if(regional) buildRegionBrowseView(regionOrderMode.value);
  else buildBrowseView(mode);
  filterAll();
}

async function toggleBrowseSign(row){
  const wrapper=row.closest('.browse-sign-wrap');
  const panel=wrapper.querySelector('.browse-detail');
  const opening=!wrapper.classList.contains('open');
  if(opening&&!panel.dataset.loaded){
    const source=canonicalSigns.get(String(row.dataset.id));
    const sourceDetail=source.querySelector('.detail');
    const detail=document.createElement('div'); detail.className='detail'; detail.style.maxHeight='none';
    try{
      detail.innerHTML=sourceDetail.dataset.detailPath
        ? await loadFragment(sourceDetail.dataset.detailPath)
        : sourceDetail.innerHTML;
      detail.querySelectorAll('[id]').forEach(node=>node.removeAttribute('id'));
      panel.append(detail); panel.dataset.loaded='true';
    }catch(error){
      detail.innerHTML='<div class="detail-loading">Details could not be loaded. Reload the page and try again.</div>';
      panel.append(detail);
    }
  }
  wrapper.classList.toggle('open',opening);
  panel.hidden=!opening;
  row.setAttribute('aria-expanded',opening?'true':'false');
  row.querySelector('.browse-arrow').textContent=opening?'⌄':'›';
}

function handleBrowseContainerClick(event){
  const regionToggle=event.target.closest('.region-toggle');
  if(regionToggle){
    const section=regionToggle.closest('.region-section');
    const collapsed=section.classList.toggle('collapsed');
    regionToggle.setAttribute('aria-expanded',collapsed?'false':'true');
    return;
  }
  const subtoggle=event.target.closest('.browse-subtoggle');
  if(subtoggle){
    const subsection=subtoggle.closest('.browse-subsection');
    const collapsed=subsection.classList.toggle('collapsed');
    subtoggle.setAttribute('aria-expanded',collapsed?'false':'true');
    return;
  }
  const toggle=event.target.closest('.browse-toggle');
  if(toggle){
    const section=toggle.closest('.browse-section');
    const collapsed=section.classList.toggle('collapsed');
    toggle.setAttribute('aria-expanded',collapsed?'false':'true');
    return;
  }
  const row=event.target.closest('.browse-sign'); if(row) void toggleBrowseSign(row);
}
browseSections.addEventListener('click',handleBrowseContainerClick);
regionBrowseSections.addEventListener('click',handleBrowseContainerClick);

function applySearch(){ appliedQuery=searchInput.value.toLowerCase().trim(); filterAll(); }
searchSubmit.addEventListener('click',applySearch);
searchInput.addEventListener('keydown',event=>{ if(event.key==='Enter'){ event.preventDefault(); applySearch(); } });
searchClear.addEventListener('click',()=>{ searchInput.value=''; appliedQuery=''; filterAll(); searchInput.focus(); });
[fRegion,fPhase,fLat,fEvid].forEach(el=>el.addEventListener('change',filterAll));
browseMode.addEventListener('change',()=>setBrowseMode(browseMode.value));
regionOrderMode.addEventListener('change',()=>{
  builtRegionMode='';
  buildRegionBrowseView(regionOrderMode.value);
  filterAll();
});

/* ---------- collapsing the toolbar ---------- */
(function(){
  const KEY='atlasToolbar';
  const fab=document.getElementById('tb-fab'), tog=document.getElementById('tb-toggle');
  const state=document.getElementById('tb-collapse');
  if(!fab||!tog||!state) return;
  function set(open,remember){
    document.body.classList.toggle('tb-collapsed',!open);
    state.checked=!open;
    tog.setAttribute('aria-expanded',open); fab.setAttribute('aria-expanded',open);
    if(remember){ try{localStorage.setItem(KEY,open?'open':'closed');}catch(e){} }
  }
  function auto(){
    let pref=null; try{pref=localStorage.getItem(KEY);}catch(e){}
    /* a stated preference wins; otherwise a short viewport (a phone on its side)
       starts collapsed, which is the case the toolbar was crowding */
    if(pref) set(pref==='open',false); else set(window.innerHeight>520,false);
  }
  state.addEventListener('change',()=>{
    const open=!state.checked;
    set(open,true);
    if(open) searchInput.focus({preventScroll:true});
  });
  window.addEventListener('orientationchange',()=>setTimeout(auto,150));
  auto();
})();

// expand / collapse all (visible)
/* These reach every level that can be folded - the summary panels at the top, the
   region banners, the sub-region banners and the cards. Collapse all used to leave
   the regions and the panels open, so on a phone it barely shortened the page. */
function setAll(open){
  if(browseMode.value!=='region'){
    browseSections.querySelectorAll('.browse-section').forEach(section=>{
      if(section.style.display==='none') return;
      section.classList.toggle('collapsed',!open);
      section.querySelector('.browse-toggle').setAttribute('aria-expanded',open?'true':'false');
    });
    browseSections.querySelectorAll('.browse-subsection').forEach(subsection=>{
      if(subsection.style.display==='none') return;
      subsection.classList.toggle('collapsed',!open);
      subsection.querySelector(':scope > .browse-subtoggle').setAttribute('aria-expanded',open?'true':'false');
    });
    return;
  }
  document.querySelectorAll('.frontpage-fold').forEach(d=>{ d.open=open; });
  regionBrowseSections.querySelectorAll('.region-section').forEach(sec=>{
    sec.classList.toggle('collapsed',!open);
    const t=sec.querySelector('.region-toggle'); if(t) t.setAttribute('aria-expanded',open);
  });
  regionBrowseSections.querySelectorAll('.browse-subsection').forEach(subsection=>{
    subsection.classList.toggle('collapsed',!open);
    subsection.querySelector(':scope > .browse-subtoggle')?.setAttribute('aria-expanded',open?'true':'false');
  });
  if(!open) regionBrowseSections.querySelectorAll('.browse-sign-wrap.open .browse-sign').forEach(row=>void toggleBrowseSign(row));
}
document.getElementById('expand-all').addEventListener('click',()=>setAll(true));
document.getElementById('collapse-all').addEventListener('click',()=>setAll(false));

// filters toggle (mobile)
const ft=document.getElementById('filter-toggle');
const fp=document.getElementById('filter-panel');
ft.addEventListener('click',()=>{
  const open=fp.classList.toggle('open');
  ft.classList.toggle('open',open);
  ft.setAttribute('aria-expanded',open?'true':'false');
});

// quiz mode
const quiz=document.getElementById('quiz-mode');
quiz.addEventListener('change',()=>{
  document.body.classList.toggle('quiz',quiz.checked);
  if(quiz.checked){ signs.forEach(s=>closeSign(s)); }
});

// recompute open heights on resize (avoid clipping when text rewraps)
let rt;
window.addEventListener('resize',()=>{
  clearTimeout(rt);
  rt=setTimeout(()=>{
    signs.forEach(s=>{ if(s.classList.contains('open')){ const d=s.querySelector('.detail'); d.style.maxHeight=d.scrollHeight+'px'; } });
  },120);
});

// ---- weighted meta-analysis: row expand + view toggle ----
function mOpen(row){const d=row.querySelector('.mdetail');row.classList.add('open');
  row.querySelector('.msign-head').setAttribute('aria-expanded','true');d.style.maxHeight=d.scrollHeight+'px';}
function mClose(row){const d=row.querySelector('.mdetail');row.classList.remove('open');
  row.querySelector('.msign-head').setAttribute('aria-expanded','false');d.style.maxHeight='0px';}
document.querySelectorAll('.msign-head').forEach(h=>{
  h.addEventListener('click',()=>{const r=h.closest('.msign');r.classList.contains('open')?mClose(r):mOpen(r);});
});
const mRegionSortWrap=document.querySelector('.msort-region');
const mSignSortWrap=document.querySelector('.msort-sign');
const mRegionSort=document.getElementById('meta-sort-region');
const mSignSort=document.getElementById('meta-sort-sign');
const dirRank={contra:0,ipsi:1,dominant:2,nondominant:3};
function mCompare(a,b,k){
  if(k==='original') return (+a.dataset.order)-(+b.dataset.order);
  if(k==='pooled') return (+b.dataset.pooled)-(+a.dataset.pooled) || a.dataset.name.localeCompare(b.dataset.name);
  if(k==='cert') return (+b.dataset.cert)-(+a.dataset.cert) || (+b.dataset.weight)-(+a.dataset.weight)
    || (+b.dataset.pooled)-(+a.dataset.pooled) || a.dataset.name.localeCompare(b.dataset.name);
  if(k==='dir') return (dirRank[a.dataset.dir]-dirRank[b.dataset.dir]) || a.dataset.name.localeCompare(b.dataset.name);
  return a.dataset.name.localeCompare(b.dataset.name);
}
function mSortFlat(k){
  const view=document.getElementById('meta-view-sign');
  const rows=Array.from(view.querySelectorAll(':scope > .msign')).sort((a,b)=>mCompare(a,b,k));
  rows.forEach(row=>view.appendChild(row));
}
function mSortRegion(k){
  document.querySelectorAll('#meta-view-region > .mreg').forEach(region=>{
    const groups=Array.from(region.children).filter(node=>node.classList.contains('mgrp'));
    groups.forEach(group=>{
      const rows=Array.from(group.children).filter(node=>node.classList.contains('msign')).sort((a,b)=>mCompare(a,b,k));
      rows.forEach(row=>group.appendChild(row));
    });
    groups.sort((a,b)=>{
      if(k==='original') return (+a.dataset.order)-(+b.dataset.order);
      const firstA=Array.from(a.children).find(node=>node.classList.contains('msign'));
      const firstB=Array.from(b.children).find(node=>node.classList.contains('msign'));
      return mCompare(firstA,firstB,k);
    });
    groups.forEach(group=>region.appendChild(group));
  });
}
function mApplySort(view){
  if(view==='region') mSortRegion(mRegionSort.value);
  else mSortFlat(mSignSort.value);
}
document.querySelectorAll('.mtab').forEach(tab=>{
  tab.addEventListener('click',()=>{
    const v=tab.dataset.view;
    document.querySelectorAll('.mtab').forEach(t=>t.classList.toggle('on',t===tab));
    document.getElementById('meta-view-region').hidden=(v!=='region');
    document.getElementById('meta-view-sign').hidden=(v!=='sign');
    mRegionSortWrap.hidden=(v!=='region');
    mSignSortWrap.hidden=(v!=='sign');
    mApplySort(v);
    document.querySelectorAll('.meta-view:not([hidden]) .msign.open').forEach(r=>{
      const d=r.querySelector('.mdetail');d.style.maxHeight=d.scrollHeight+'px';});
  });
});
if(mRegionSort) mRegionSort.addEventListener('change',()=>mSortRegion(mRegionSort.value));
if(mSignSort) mSignSort.addEventListener('change',()=>mSortFlat(mSignSort.value));

// ---- complete current-ledger weighted evidence ----
document.querySelectorAll('.weighted-evidence-shell').forEach(shell=>{
  const tabs=Array.from(shell.querySelectorAll('.weighted-axis-tab'));
  const panels=Array.from(shell.querySelectorAll('.weighted-axis-panel'));
  tabs.forEach(tab=>tab.addEventListener('click',()=>{
    const axis=tab.dataset.axisTab;
    tabs.forEach(item=>{
      const selected=item===tab;
      item.classList.toggle('on',selected);
      item.setAttribute('aria-selected',selected?'true':'false');
    });
    panels.forEach(panel=>{ panel.hidden=panel.dataset.axisPanel!==axis; });
  }));
});

function bindLedgerReliability(wrap){
  if(wrap.dataset.bound==='true') return;
  wrap.dataset.bound='true';
  const search=wrap.querySelector('.lr-search');
  const reset=wrap.querySelector('.lr-reset');
  const sort=wrap.querySelector('.lr-sort');
  const list=wrap.querySelector('.lr-list');
  const count=wrap.querySelector('.lr-visible-count');
  const filters=Array.from(wrap.querySelectorAll('.lr-filter'));
  const rows=Array.from(wrap.querySelectorAll('.lr-row'));
  const rowsBySign=new Map(rows.filter(row=>row.dataset.signId).map(row=>[String(row.dataset.signId),row]));
  const unreported=Array.from(wrap.querySelectorAll('.lr-unreported-sign'));
  const unreportedCount=wrap.querySelector('.lr-unreported-count');
  let active='all';
  function compare(a,b){
    const key=sort.value;
    if(key==='name') return a.dataset.name.localeCompare(b.dataset.name);
    if(key==='manuscripts') return (+b.dataset.manuscripts)-(+a.dataset.manuscripts)
      || (+b.dataset.findings)-(+a.dataset.findings) || a.dataset.name.localeCompare(b.dataset.name);
    if(key==='statistics') return (+b.dataset.statistics)-(+a.dataset.statistics)
      || (+b.dataset.findings)-(+a.dataset.findings) || a.dataset.name.localeCompare(b.dataset.name);
    const associationOrder=(a.dataset.bucket==='nonassoc')-(b.dataset.bucket==='nonassoc');
    if(key==='certainty') return associationOrder
      || (+b.dataset.cert)-(+a.dataset.cert)
      || (+b.dataset.manuscripts)-(+a.dataset.manuscripts)
      || (+b.dataset.weight)-(+a.dataset.weight)
      || a.dataset.name.localeCompare(b.dataset.name);
    return associationOrder
      || (+b.dataset.reliability)-(+a.dataset.reliability)
      || (+b.dataset.cert)-(+a.dataset.cert)
      || (+b.dataset.manuscripts)-(+a.dataset.manuscripts)
      || a.dataset.name.localeCompare(b.dataset.name);
  }
  function pageOrganizationLabel(){
    if(!browseMode) return 'page organization';
    if(browseMode.value==='region'){
      const within=regionOrderMode?.selectedOptions?.[0]?.textContent?.trim()||'A–Z';
      return 'brain region → '+within;
    }
    return browseMode.selectedOptions?.[0]?.textContent?.trim()||'page organization';
  }
  function pageGroups(){
    const regional=browseMode?.value==='region';
    const container=regional?regionBrowseSections:browseSections;
    const sectionSelector=regional?':scope > .region-section':':scope > .browse-section';
    const seen=new Set(),groups=[];
    Array.from(container?.querySelectorAll(sectionSelector)||[]).forEach(section=>{
      const label=regional
        ? String(section.dataset.region||'Region')
        : (section.querySelector(':scope > .browse-toggle .browse-name')?.textContent?.trim()||'Other signs');
      const color=regional
        ? (section.querySelector(':scope > .region-toggle')?.style.getPropertyValue('--rc')||'#0e9db0')
        : '#0e9db0';
      const subgroupMap=new Map();
      section.querySelectorAll('.browse-sign').forEach(item=>{
        const row=rowsBySign.get(String(item.dataset.id||''));
        if(!row||seen.has(row)) return;
        seen.add(row);
        let subgroup='';
        if(regional){
          const category=item.closest('.region-category');
          if(category&&section.contains(category)) subgroup=category.querySelector(':scope > .browse-subtoggle .browse-name')?.textContent?.trim()||'';
        }
        if(!subgroupMap.has(subgroup)) subgroupMap.set(subgroup,[]);
        subgroupMap.get(subgroup).push(row);
      });
      const subgroups=Array.from(subgroupMap,([label,groupRows])=>({label,rows:groupRows}));
      if(subgroups.length) groups.push({label,color,subgroups});
    });
    const remaining=rows.filter(row=>!seen.has(row)).sort((a,b)=>a.dataset.name.localeCompare(b.dataset.name));
    if(remaining.length) groups.push({label:'Other evidence-bearing signs',color:'#7b8798',subgroups:[{label:'',rows:remaining}]});
    return groups;
  }
  function renderPageGroups(query){
    const openKeys=new Set(Array.from(list.querySelectorAll('.lr-page-group[open]')).map(group=>group.dataset.key));
    list.replaceChildren();
    let opened=false;
    pageGroups().forEach((group,index)=>{
      const details=document.createElement('details');
      details.className='lr-page-group';details.dataset.key=group.label;
      details.style.setProperty('--group-color',group.color);
      const summary=document.createElement('summary');
      const name=document.createElement('span');name.textContent=group.label;
      const badge=document.createElement('span');badge.className='lr-page-group-count';
      summary.append(name,badge);
      const body=document.createElement('div');body.className='lr-page-group-body';
      let groupVisible=0;
      group.subgroups.forEach(subgroup=>{
        const section=document.createElement('section');section.className='lr-page-subgroup';
        const subgroupVisible=subgroup.rows.filter(row=>!row.hidden).length;
        if(subgroup.label){
          const heading=document.createElement('h4');heading.className='lr-page-subgroup-title';
          heading.textContent=subgroup.label;heading.hidden=subgroupVisible===0;section.append(heading);
        }
        subgroup.rows.forEach(row=>section.append(row));
        section.hidden=subgroupVisible===0;groupVisible+=subgroupVisible;body.append(section);
      });
      badge.textContent=groupVisible.toLocaleString();details.hidden=groupVisible===0;
      details.open=groupVisible>0&&(query?true:(openKeys.size?openKeys.has(group.label):!opened));
      if(details.open) opened=true;
      details.append(summary,body);list.append(details);
    });
  }
  function apply(){
    const query=search.value.trim().toLowerCase();
    let visible=0;
    rows.forEach(row=>{
      const show=(active==='all'||row.dataset.bucket===active)
        &&(!query||row.dataset.search.includes(query));
      row.hidden=!show;
      if(show) visible++;
    });
    if(sort.value==='page') renderPageGroups(query);
    else{
      list.replaceChildren();
      rows.sort(compare).forEach(row=>list.append(row));
    }
    let visibleUnreported=0;
    unreported.forEach(item=>{
      const show=!query||item.dataset.search.includes(query);
      item.hidden=!show;
      if(show) visibleUnreported++;
    });
    count.textContent=visible.toLocaleString()+' of '+rows.length.toLocaleString()+' evidence-bearing summaries shown'
      +(sort.value==='page'?' · organized by '+pageOrganizationLabel():'');
    if(unreportedCount) unreportedCount.textContent=visibleUnreported.toLocaleString();
  }
  filters.forEach(button=>button.addEventListener('click',()=>{
    active=button.dataset.filter;
    filters.forEach(item=>item.classList.toggle('on',item===button));
    apply();
  }));
  search.addEventListener('input',apply);
  sort.addEventListener('change',apply);
  [browseMode,regionOrderMode].forEach(control=>control?.addEventListener('change',()=>{
    if(sort.value==='page') setTimeout(apply,0);
  }));
  reset.addEventListener('click',()=>{
    search.value=''; active='all'; sort.value='page';
    filters.forEach(button=>button.classList.toggle('on',button.dataset.filter==='all'));
    apply(); search.focus();
  });
  apply();
  setTimeout(apply,0);
}
document.querySelectorAll('.lr-wrap').forEach(bindLedgerReliability);

// ---- local table controls; study summaries also inherit active sign filters ----
let activeStudySignIds=null;

function bindFxWrap(wrap){
  if(wrap.dataset.filterBound) return;
  wrap.dataset.filterBound='true';
  const search=wrap.querySelector('.fx-search');
  const table=wrap.querySelector('.fx-table');
  const count=wrap.querySelector('.fx-count');
  const secondaryCount=wrap.querySelector('.fx-secondary-count');
  const reset=wrap.querySelector('.fx-reset');
  if(!search||!table||!count) return;
  const rows=Array.from(table.querySelectorAll('.fx-row'));
  const buttons=Array.from(wrap.querySelectorAll('.fxb'));
  const label=wrap.dataset.itemLabel||'items';
  const inheritSignFilter=wrap.dataset.globalSignFilter==='true';
  const summaryCount=wrap.closest('.frontpage-fold')?.querySelector(':scope > summary .fx-summary-count');
  let mfilter='all';
  function apply(){
    const q=(search.value||'').toLowerCase().trim();
    const availableCounted=[];
    let vis=0;
    let availableSecondary=0;
    let visibleSecondary=0;
    rows.forEach(r=>{
      const linked=(r.dataset.signIds||'').split('|').filter(Boolean);
      const globallyMatched=!inheritSignFilter||!activeStudySignIds||linked.some(id=>activeStudySignIds.has(id));
      const locallyMatched=!q||(r.dataset.fq||'').includes(q);
      const counted=r.dataset.countItem!=='false';
      const secondaryItems=r.querySelectorAll('[data-statistic-id]').length;
      if(globallyMatched&&locallyMatched){
        if(counted) availableCounted.push(r);
        availableSecondary+=secondaryItems;
      }
      const show=globallyMatched&&locallyMatched&&((mfilter==='all')||r.dataset.metric===mfilter);
      r.classList.toggle('fx-hidden',!show);
      if(show&&counted) vis++;
      if(show) visibleSecondary+=secondaryItems;
    });
    table.querySelectorAll('[data-fx-group]').forEach(group=>{
      const visibleRows=Array.from(group.querySelectorAll('.fx-row')).filter(row=>!row.classList.contains('fx-hidden'));
      group.classList.toggle('fx-hidden',visibleRows.length===0);
      const badge=group.querySelector('[data-fx-group-count]');
      if(badge) badge.textContent=visibleRows.filter(row=>row.dataset.countItem!=='false').length.toLocaleString();
    });
    buttons.forEach(button=>{
      const metric=button.dataset.f;
      const metricCount=metric==='all'?availableCounted.length:availableCounted.filter(row=>row.dataset.metric===metric).length;
      const badge=button.querySelector('i');
      if(badge) badge.textContent=metricCount.toLocaleString();
    });
    count.textContent=vis.toLocaleString()+' of '+availableCounted.length.toLocaleString()+' '+label+' shown';
    if(secondaryCount) secondaryCount.textContent=visibleSecondary.toLocaleString()+' of '+availableSecondary.toLocaleString()+' reported numbers shown';
    if(summaryCount) summaryCount.textContent=vis.toLocaleString();
  }
  buttons.forEach(b=>b.addEventListener('click',()=>{
    buttons.forEach(x=>x.classList.toggle('on',x===b));
    mfilter=b.dataset.f;
    apply();
  }));
  search.addEventListener('input',apply);
  reset?.addEventListener('click',()=>{
    search.value='';
    mfilter='all';
    buttons.forEach(button=>button.classList.toggle('on',button.dataset.f==='all'));
    apply();
    search.focus();
  });
  wrap.applyCurrentFilters=apply;
  apply();
}
document.querySelectorAll('.fx-wrap').forEach(bindFxWrap);

async function ensureEvidencePanel(panel){
  if(!panel||panel.dataset.loaded==='true') return;
  if(panel.fragmentPromise) return panel.fragmentPromise;
  const host=panel.querySelector(':scope > .lazy-fragment');
  if(!host) return;
  host.textContent='Loading…';
  panel.fragmentPromise=(async()=>{
    try{
      host.outerHTML=await loadFragment(panel.dataset.fragment);
      panel.dataset.loaded='true';
      panel.querySelectorAll('.fx-wrap').forEach(bindFxWrap);
    }catch(error){
      host.textContent='This view could not be loaded. Reload the page and try again.';
    }finally{
      delete panel.fragmentPromise;
    }
  })();
  return panel.fragmentPromise;
}

function bindEvidenceLibrary(library){
  const tabs=Array.from(library.querySelectorAll('.evidence-view-tab'));
  const panels=Array.from(library.querySelectorAll('.evidence-view-panel'));
  if(!tabs.length||!panels.length||library.dataset.evidenceBound) return;
  library.dataset.evidenceBound='true';
  async function activate(tab){
    const view=tab.dataset.evidenceView;
    tabs.forEach(item=>{
      const active=item===tab;
      item.classList.toggle('on',active);
      item.setAttribute('aria-selected',String(active));
    });
    panels.forEach(panel=>panel.hidden=panel.dataset.evidencePanel!==view);
    await ensureEvidencePanel(panels.find(panel=>panel.dataset.evidencePanel===view));
  }
  tabs.forEach(tab=>tab.addEventListener('click',()=>void activate(tab)));
  void activate(tabs.find(tab=>tab.classList.contains('on'))||tabs[0]);
}
document.querySelectorAll('.evidence-library-details').forEach(bindEvidenceLibrary);

async function ensureDeferredFold(fold){
  if(!fold||fold.dataset.loaded==='true') return;
  if(fold.fragmentPromise) return fold.fragmentPromise;
  const host=fold.querySelector(':scope > .lazy-fragment');
  if(!host) return;
  host.textContent='Loading…';
  fold.fragmentPromise=(async()=>{
    try{
      host.outerHTML=await loadFragment(fold.dataset.fragment);
      fold.dataset.loaded='true';
      fold.querySelectorAll('.fx-wrap').forEach(bindFxWrap);
      if(fold.matches('.evidence-library-details')) bindEvidenceLibrary(fold);
      fold.querySelectorAll('.evidence-library-details').forEach(bindEvidenceLibrary);
    }catch(error){
      host.textContent='This section could not be loaded. Close it, reload the page, and try again.';
    }finally{
      delete fold.fragmentPromise;
    }
  })();
  return fold.fragmentPromise;
}

function refreshStudyFamilyFilter(visibleIds,active){
  activeStudySignIds=active?new Set(Array.from(visibleIds,String)):null;
  document.querySelectorAll('.evidence-library-details .fx-wrap[data-global-sign-filter="true"]')
    .forEach(wrap=>wrap.applyCurrentFilters?.());
}

document.querySelectorAll('details[data-fragment]').forEach(fold=>{
  fold.addEventListener('toggle',async()=>{
    if(fold.open) await ensureDeferredFold(fold);
  });
});

filterAll();
"""
)

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>Seizure Semiology &mdash; Interactive Study Reference</title>
<!-- Added to the Home Screen this runs with no address bar or tab strip, which is
     the only way a page can get that space back on iOS. -->
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Semiology">
<meta name="theme-color" content="#12263f">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icon-180.png">
<style>""" + CSS + """</style>
</head>
<body>

<div class="site-header">
  <h1>Seizure Semiology &mdash; Interactive Study Reference</h1>
  <p>Search the evidence library or browse the signs below. Results from different studies are shown separately. <span class="edu-inline">&#9888;&#65039; Educational reference &mdash; not for clinical decision-making.</span></p>
</div>

<input class="tb-state" type="checkbox" id="tb-collapse" aria-label="Collapse toolbar">
<div class="sticky-head" id="sticky-head">
  <nav class="region-nav">
""" + pills_html + """
  </nav>
  <div class="toolbar">
    <div class="search-wrap">
      <span class="search-icon">&#128269;</span>
      <input type="text" id="search-input" placeholder="Search signs, anatomy, or sources...">
      <button class="search-btn" id="search-submit" type="button">Search</button>
      <button class="search-btn search-clear" id="search-clear" type="button">Clear</button>
    </div>
    <label class="browse-mode-field"><span class="ctrl-label">Organize signs by</span>
      <select id="browse-mode">
        <option value="region">Brain region</option>
        <option value="az">Semiology A&ndash;Z</option>
        <option value="za">Semiology Z&ndash;A</option>
        <option value="ilae">ILAE 2025 classification</option>
        <option value="luders">L&uuml;ders 5D classification</option>
      </select>
    </label>
    <label class="browse-mode-field" id="region-order-field"><span class="ctrl-label">Within each region</span>
      <select id="region-order-mode">
        <option value="luders">L&uuml;ders 5D</option>
        <option value="ilae">ILAE 2025</option>
        <option value="az">A&ndash;Z</option>
      </select>
    </label>
    <button class="filter-toggle" id="filter-toggle" aria-expanded="false"><span>Filters</span><span class="chev">&#9660;</span></button>
    <div class="filter-panel" id="filter-panel">
      <div class="filter-field"><span class="ctrl-label">Region</span>
        <select id="filter-region">
          <option value="">All Regions</option>
          <option value="Temporal">Temporal</option>
          <option value="Frontal">Frontal</option>
          <option value="Parietal">Parietal</option>
          <option value="Occipital">Occipital</option>
          <option value="Insular">Insular</option>
          <option value="Deep/Subcortical">Deep/Subcortical</option>
          <option value="Multiregional/Propagation">Multiregional</option>
        </select>
      </div>
      <div class="filter-field"><span class="ctrl-label">Phase</span>
        <select id="filter-phase">
          <option value="">All Phases</option>
          <option value="Aura">Aura</option>
          <option value="Ictal">Ictal</option>
          <option value="Postictal">Postictal</option>
          <option value="Interictal">Interictal</option>
          <option value="Peri-ictal">Peri-ictal</option>
        </select>
      </div>
      <div class="filter-field"><span class="ctrl-label">Lateralization</span>
        <select id="filter-lat">
          <option value="">All</option>
          <option value="contra">Contralateral</option>
          <option value="ipsi">Ipsilateral</option>
          <option value="dominant">Dominant</option>
          <option value="nondominant">Non-dominant</option>
          <option value="right">Right hemisphere</option>
          <option value="nonlat">Non-lateralizing</option>
          <option value="variable">Variable</option>
        </select>
      </div>
      <div class="filter-field"><span class="ctrl-label">Evidence</span>
        <select id="filter-evid">
          <option value="">All Levels</option>
          <option value="I">I (Strong)</option>
          <option value="II">II (Moderate)</option>
          <option value="III">III (Expert)</option>
        </select>
      </div>
    </div>
    <div class="tool-actions">
      <button class="act-btn" id="expand-all">&#10753; Expand all</button>
      <button class="act-btn" id="collapse-all">&#10752; Collapse all</button>
      <label class="quiz-toggle"><input type="checkbox" id="quiz-mode"><span class="quiz-switch"></span>Quiz mode</label>
    </div>
      <label class="tb-toggle" id="tb-toggle" for="tb-collapse" role="button" aria-expanded="true" aria-controls="sticky-head"
             title="Hide the toolbar">&#9650;<span class="vh"> Hide toolbar</span></label>
    </div>
    <span id="result-count"></span>
  </div>
</div>
<label class="tb-fab" id="tb-fab" for="tb-collapse" role="button" aria-expanded="false" aria-controls="sticky-head"
       aria-label="Show search and filters">&#128269;<span class="tb-dot" aria-hidden="true"></span></label>

<main>
""" + brain_fold + meta_fold + """
  <div class="quiz-hint"><strong>Quiz mode on:</strong> lateralization &amp; evidence cues are hidden. Read each sign, predict its localization/lateralization, then expand to check yourself.</div>
  <p class="axis-display-note">Region colors identify anatomy only; they do not indicate evidence strength.</p>
  <div id="source-sign-store" hidden>
""" + sections_html + """
  </div>
  <div id="region-view">
    <p class="browse-note">Each region is organized first by Aura, Seizure, lateralizing signs, and diagnostic signs; choose the ordering within those sections above.</p>
    <div id="region-browse-sections"></div>
  </div>
  <div id="semiology-view" hidden>
    <p class="browse-note" id="browse-note"></p>
    <div id="browse-sections"></div>
  </div>
  <div id="no-results">No signs match the current search or filters. Try clearing them.</div>
</main>

<div class="abbrev">
  <details class="abbrev-details">
    <summary>Abbreviations &amp; Terminology</summary>
    <div class="abbrev-grid">
      <div class="abbrev-item"><strong>EZ</strong> = Epileptogenic Zone</div>
      <div class="abbrev-item"><strong>MTLE</strong> = Mesial Temporal Lobe Epilepsy</div>
      <div class="abbrev-item"><strong>NFLE</strong> = Nocturnal Frontal Lobe Epilepsy</div>
      <div class="abbrev-item"><strong>SEEG</strong> = Stereoelectroencephalography</div>
      <div class="abbrev-item"><strong>SDE</strong> = Subdural Electrode (grid/strip)</div>
      <div class="abbrev-item"><strong>OFC</strong> = Orbitofrontal Cortex</div>
      <div class="abbrev-item"><strong>ACC</strong> = Anterior Cingulate Cortex</div>
      <div class="abbrev-item"><strong>SMA</strong> = Supplementary Motor Area</div>
      <div class="abbrev-item"><strong>SSMA</strong> = Supplementary Sensorimotor Area</div>
      <div class="abbrev-item"><strong>FEF</strong> = Frontal Eye Field (BA 8)</div>
      <div class="abbrev-item"><strong>TPJ</strong> = Temporo-Parietal Junction</div>
      <div class="abbrev-item"><strong>PIVC</strong> = Parieto-Insular Vestibular Cortex</div>
      <div class="abbrev-item"><strong>STG/MTG/ITG</strong> = Sup./Mid./Inf. Temporal Gyrus</div>
      <div class="abbrev-item"><strong>SPL/IPL</strong> = Sup./Inf. Parietal Lobule</div>
      <div class="abbrev-item"><strong>S1/S2</strong> = 1&#176;/2&#176; Somatosensory Cortex</div>
      <div class="abbrev-item"><strong>M1</strong> = Primary Motor Cortex</div>
      <div class="abbrev-item"><strong>V1-V5</strong> = Visual areas (calcarine&#8594;MT/V5)</div>
      <div class="abbrev-item"><strong>BATS</strong> = Bilateral Asymmetric Tonic Seizure</div>
      <div class="abbrev-item"><strong>AP sign</strong> = Automatism + Posturing (temporal)</div>
      <div class="abbrev-item"><strong>M2E</strong> = Mouth-to-hand automatism (SMA)</div>
      <div class="abbrev-item"><strong>AAPR</strong> = Automatism w/ preserved responsiveness</div>
      <div class="abbrev-item"><strong>TIRDA</strong> = Temporal Intermittent Rhythmic Delta</div>
      <div class="abbrev-item"><strong>SUDEP</strong> = Sudden Unexplained Death in Epilepsy</div>
      <div class="abbrev-item"><strong>PPV</strong> = Positive Predictive Value</div>
      <div class="abbrev-item"><strong>OBE</strong> = Out-of-Body Experience</div>
      <div class="abbrev-item"><strong>GTCS</strong> = Generalized Tonic-Clonic Seizure</div>
      <div class="abbrev-item"><strong>BG</strong> = Basal Ganglia</div>
    </div>
  </details>
</div>

""" + evidence_library_html + """

<div class="lib">
  <details class="lib-details">
    <summary>Source Library &mdash; """ + str(len(PAPERS)) + """ Contributing Manuscripts</summary>
    <div class="lib-grid">
""" + papers_html + """
    </div>
  </details>
</div>

<div class="footer">
  <strong>Educational use:</strong> This reference is designed for teaching and self-study by epilepsy trainees. Each evidence entry shows who was studied, what was counted, the reported result, and important cautions. Results from different studies are not combined. Real localization always integrates ictal EEG, imaging, neuropsychology, and history. &nbsp;|&nbsp;
  <strong>Schools referenced:</strong> Paris SEEG (Bancaud, Talairach, Chauvel, Bartolomei, McGonigal); Cleveland Clinic (L&#252;ders, Kotagal, Bleasel, Dinner); Lyon SEEG (Isnard, Maugui&#232;re, Ryvlin, Ostrowsky); Montreal (Penfield, Jasper, Rasmussen). &nbsp;|&nbsp;
  <strong>Contribute a paper or correction:</strong> new evidence is welcome &mdash; <a href="https://github.com/ckadipas/seizure-semiology-atlas/issues/new/choose">submit it here</a>. Every submission is reviewed by the maintainers before it appears.
</div>

<script>""" + JS + """</script>
</body>
</html>"""

fragments_dir = os.path.join(DOCS, "fragments")
shutil.rmtree(fragments_dir, ignore_errors=True)
os.makedirs(fragments_dir, exist_ok=True)
for fragment_name, fragment_html in {**deferred_fragments, **detail_fragments}.items():
    with open(os.path.join(fragments_dir, fragment_name), "w", encoding="utf-8") as fragment_file:
        fragment_file.write(fragment_html)

for name in ("seizure_semiology_localization.html", "index.html"):
    with open(os.path.join(DOCS, name), "w", encoding="utf-8") as f:
        f.write(HEAD)

with open(os.path.join(DOCS, "CNAME"), "w", encoding="utf-8") as f:
    f.write("www.semiologyatlas.org\n")

# Added to the Home Screen the page runs with no address bar or tab strip. A page
# cannot hide browser chrome any other way, so this is what makes that possible.
with open(os.path.join(DOCS, "manifest.webmanifest"), "w") as f:
    json.dump({
        "name": "Seizure Semiology — Interactive Study Reference",
        "short_name": "Semiology",
        "start_url": "./index.html",
        "scope": "./",
        "display": "standalone",
        "orientation": "any",
        "background_color": "#f4f6fa",
        "theme_color": "#12263f",
        "icons": [{"src": "icon-180.png", "sizes": "180x180", "type": "image/png"},
                  {"src": "icon-512.png", "sizes": "512x512", "type": "image/png",
                   "purpose": "any maskable"}],
    }, f, indent=1, ensure_ascii=False)
for _icon in ("icon-180.png", "icon-512.png"):
    _src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", _icon)
    if os.path.exists(_src):
        shutil.copyfile(_src, os.path.join(DOCS, _icon))

_placement_count = sum(region_counts.values())
_area_ref_count = sum(len(signs) for areas in area_signs_by_region.values() for signs in areas.values())
_card_count = _placement_count + _area_ref_count
print(f"Written: {len(HEAD)} chars, {len(data)} unique signs, {_card_count} anatomical placements")

# ---- sanity checks ----
h=HEAD
assert h.count('class="sign"')==_card_count
assert h.count(chr(34).join(["class=","sign",""]))==_card_count
assert 'id="quiz-mode"' in h
assert 'id="expand-all"' in h and 'id="collapse-all"' in h
assert h.count('data-area-ref="true"') == _area_ref_count
assert len(re.findall(r'class="sign"[^>]*\bdata-search=', h)) == _card_count
assert 'class="detail"' in h
assert '@media (max-width:760px)' in h
assert h.count('class="pill"')==len(region_order)
assert 'body.quiz' in h
print("All sanity checks passed.")
