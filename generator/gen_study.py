import hashlib, json, re, os, shutil, sys
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
FLAGS = None

PAPERS = []
ledger_by_ref = {}
ledger_evidence_by_cardid = {}
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
        for _cid in _row["exact_sign_ids"]:
            ledger_evidence_by_cardid.setdefault(_cid, []).append((_entry, "EXACT"))
        for _cid in _row["related_sign_ids"]:
            ledger_evidence_by_cardid.setdefault(_cid, []).append((_entry, "RELATED"))

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
        if numerator and denominator and str(numerator).upper() != "NOT_APPLICABLE" and str(denominator).upper() != "NOT_APPLICABLE":
            context.append(f'<span><strong>Counts:</strong> {esc(numerator)} / {esc(denominator)}</span>')
        uncertainty = statistic.get("uncertainty")
        if uncertainty and str(uncertainty).upper() not in {"NONE", "NOT_APPLICABLE", "NOT_REPORTED", "{}"}:
            context.append(f'<span><strong>Statistical details:</strong> {esc(uncertainty)}</span>')
        items.append(
            f'<li><strong>{esc(statistic_value(statistic))}</strong> '
            f'<span class="ev-meta">{esc(metric)}</span>'
            + (f'<div class="ev-stat-context">{"".join(context)}</div>' if context else "")
            + '</li>'
        )
    if len(items) == 1:
        return f'<div class="ev-measure"><strong>Reported result:</strong><ul class="ev-stat-list">{items[0]}</ul></div>'
    return (
        f'<details class="ev-stats"><summary>{len(items)} reported results</summary>'
        f'<ol class="ev-stat-list">{"".join(items)}</ol></details>'
    )

def slug(s):
    return re.sub(r'[^a-z0-9]+','-', s.lower()).strip('-')

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
    for region in d.get("regions") or [d["region"]]:
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
        all_sign_ids = list(OrderedDict.fromkeys(
            direct[node_id] + [sign_id for child in child_rows for sign_id in child["all_sign_ids"]]
        ))
        return {
            "node_id": node_id,
            "label": row["label"],
            "node_kind": row.get("node_kind", ""),
            "sign_ids": direct[node_id],
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

def ledger_evidence_block(cid):
    """Render reviewed findings linked to this sign without exposing audit metadata."""
    linked = ledger_evidence_by_cardid.get(cid, [])
    if not linked:
        return "", 0, ""
    items, search = [], []
    for entry, relation in linked:
        source, row = entry["source"], entry["finding"]
        search.extend([row["source_term"], row["claim"], statistic_search_text(row), row["citation"],
                       row["evidence_text"], row["source_finding_ref"]])
        measure = statistic_block(row)
        items.append(
            '<li class="reviewed-card-evidence">'
            f'<div><strong>{esc(row["source_term"])}</strong> &mdash; {esc(row["claim"])}</div>'
            f'{measure}'
            '<details class="ev-trace"><summary>Source and study details</summary>'
            f'<div><strong>Source:</strong> {esc(source["source_file"])}</div>'
            f'{cited_source_line(row)}'
            f'<div><strong>Where to find it:</strong> {esc(row["locators"])}</div>'
            f'<div><strong>Relevant source text:</strong> {esc(row["evidence_text"])}</div>'
            f'<div><strong>Who was studied:</strong> {esc(row["population"])}</div>'
            f'<div><strong>Source type:</strong> {esc(ROLE_LABEL.get(row["evidence_role"], "Source information"))}</div>'
            '</details></li>')
    return ('<div class="d-row d-ev"><span class="d-label">Evidence from reviewed sources</span>'
            '<ul class="ev-list">'+"".join(items)+'</ul></div>', len(linked), " ".join(search))

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
            refs.append(f'''<div class="sign" id="area-sign-{slug(region)}-{aid}-{d['id']}"
    data-area-ref="true" data-id="{d['id']}" data-ba="{esc(aid)}" data-region="{esc(region)}"
    data-phase="{esc(d['phase'])}" data-latcode="{esc(lc)}" data-evid="{esc(ec)}"
    data-search="{esc(ref_search)}" style="--accent:{latcolor.get(lc,'#999')}">
  <button class="sign-head" aria-expanded="false">
    <span class="chevron">&#8250;</span>
    <span class="sign-name">{esc(d['sign'])}</span>
    <span class="head-chips">
      <span class="chip phase-badge phase-{slug(d['phase'].split('/')[0])}">{esc(d['phase'])}</span>
      <span class="chip lat-chip" style="color:{latcolor.get(lc,'#333')};background:{latbg.get(lc,'#f7f7f7')};border-color:{latcolor.get(lc,'#333')}">{latlabel.get(lc,'?')}</span>
      <span class="chip evid-dot" style="background:{evidcolor.get(ec,'#888')}" title="Evidence level {ec}">{ec}</span>
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
            ev_block, _nsrc, ev_text = ledger_evidence_block(d.get("id"))
            lib_chip = (f'<span class="chip lib-chip" title="Reviewed source findings">&#128218; {_nsrc}</span>'
                        if _nsrc else '')
            search_str = ""
            ppv_block = sens_block = ""
            detail_name = "sign-" + hashlib.sha256(str(d["id"]).encode("utf-8")).hexdigest()[:24] + ".html"
            detail_path = "fragments/" + detail_name
            if detail_name not in detail_fragments:
                detail_fragments[detail_name] = f'''<div class="detail-inner">
      <div class="d-row d-lat">
        <span class="d-label">Lateralization</span>
        <span class="d-value"><span class="lat-badge" style="color:{latcolor.get(lc,'#333')};background:{latbg.get(lc,'#f7f7f7')};border-color:{latcolor.get(lc,'#333')}">{latlabel.get(lc,'?')}</span> {esc(d['lat'])}</span>
      </div>
      <div class="d-row d-loc">
        <span class="d-label">Anatomical localization</span>
        <span class="d-value">{esc(d['loc'])}</span>
      </div>
      {map_row}
      <div class="d-metrics">
        <div class="metric"><span class="d-label">Strength of evidence</span><span class="metric-val"><span class="evid-badge" style="background:{evidcolor.get(ec,'#888')}">{ec}</span></span></div>
      </div>
      <div class="d-row d-notes">
        <span class="d-label">Clinical notes &amp; mechanism</span>
        <span class="d-value">{esc(d['notes'])}</span>
      </div>
      <div class="d-row d-cite">
        <span class="d-label">Key citations</span>
        <span class="d-value cite">{esc(d['cite'])}</span>
      </div>
      {ev_block}
      {sens_block}
      {ppv_block}
    </div>'''
            rows.append(f'''<div class="sign" id="sign-{slug(r)}-{d['id']}" data-id="{d['id']}" data-region="{esc(r)}" data-phase="{esc(d['phase'])}" data-latcode="{lc}" data-evid="{ec}" data-search="{esc(search_str)}" style="--accent:{accent}">
  <button class="sign-head" aria-expanded="false">
    <span class="chevron">&#8250;</span>
    <span class="sign-name">{esc(d['sign'])}</span>
    <span class="head-chips">
      <span class="chip phase-badge phase-{slug(d['phase'].split('/')[0])}">{esc(d['phase'])}</span>
      <span class="chip lat-chip" style="color:{latcolor.get(lc,'#333')};background:{latbg.get(lc,'#f7f7f7')};border-color:{latcolor.get(lc,'#333')}">{latlabel.get(lc,'?')}</span>
      <span class="chip evid-dot" style="background:{evidcolor.get(ec,'#888')}" title="Evidence level {ec}">{ec}</span>
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

    return f'''<details class="frontpage-fold meta-fold">
<summary>Evidence-weighted lateralizing reliability</summary>
<div class="meta-wrap"><div class="meta-card">
  <div class="meta-head">
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
meta_fold = build_meta(META, FLAGS)

# ---------- Source-figures explorer (every extracted data point) ----------
# Renders ALL findings from enrichment/corpus_findings.json as a compact, filterable,
# searchable table so every figure the corpus reading produced is on the page and
# checkable against its verbatim quote - not only the lateralization figures that
# feed the pooled plot. Frequency / localization / PPV / odds-ratio figures live
# here because they are population-specific and heterogeneous (they don't pool into
# one model), but they are still fully accounted for and inspectable.
def build_figures(corpus):
    if not corpus or not corpus.get("sources"):
        return ""
    labels = OrderedDict([
        ("PERCENTAGE", "Percentage"), ("COUNT", "Count"), ("P_VALUE", "P value"),
        ("OTHER", "Other"), ("RANGE", "Range"), ("MEAN", "Mean"), ("PPV", "PPV"),
        ("MEDIAN", "Median"), ("KAPPA", "Kappa"), ("DURATION", "Duration"),
        ("THRESHOLD", "Threshold"), ("ODDS_RATIO", "Odds ratio"),
        ("HAZARD_RATIO", "Hazard ratio"), ("FREQUENCY", "Frequency"),
        ("SENSITIVITY", "Sensitivity"), ("SPECIFICITY", "Specificity"),
        ("NPV", "NPV"), ("CORRELATION", "Correlation"),
    ])
    colors = {
        "PERCENTAGE":"#2471a3", "COUNT":"#5b6472", "P_VALUE":"#8e44ad", "OTHER":"#6b7280",
        "RANGE":"#95691a", "MEAN":"#0a7a8a", "PPV":"#1a7a4a", "MEDIAN":"#0a7a8a",
        "KAPPA":"#8e44ad", "DURATION":"#95691a", "THRESHOLD":"#95691a",
        "ODDS_RATIO":"#c0392b", "HAZARD_RATIO":"#c0392b", "FREQUENCY":"#2471a3",
        "SENSITIVITY":"#1a7a4a", "SPECIFICITY":"#1a7a4a", "NPV":"#1a7a4a",
        "CORRELATION":"#8e44ad",
    }
    sign_by_id = {str(sign["id"]): sign for sign in data}
    rows, counts = [], {}
    for source in corpus["sources"]:
        source_file = source["source_file"]
        for finding in source["findings"]:
            exact_names, related_names = [], []
            for key, names in (("exact_sign_ids", exact_names), ("related_sign_ids", related_names)):
                for sign_id in finding.get(key, []):
                    sign = sign_by_id.get(str(sign_id))
                    if sign and sign["sign"] not in names:
                        names.append(sign["sign"])
            sign_context = []
            if exact_names:
                sign_context.append("Linked sign: " + "; ".join(exact_names))
            if related_names:
                sign_context.append("Related sign: " + "; ".join(related_names))
            for statistic in finding_statistics(finding):
                metric = str(statistic.get("metric_type") or "OTHER").upper()
                counts[metric] = counts.get(metric, 0) + 1
                value = statistic_value(statistic)
                locator = statistic.get("source_locator") or finding.get("locators") or ""
                excerpt = statistic.get("source_excerpt") or finding.get("evidence_text") or ""
                anatomy = statistic.get("anatomy_laterality_context") or finding.get("laterality_localization") or ""
                details = list(sign_context)
                for label, field in (
                    ("Anatomy / side", anatomy), ("Who was studied", statistic.get("population") or finding.get("population")),
                    ("Subgroup", statistic.get("subgroup")), ("Time", statistic.get("timepoint")),
                    ("Outcome", statistic.get("endpoint")), ("What was counted", statistic.get("analysis_unit")),
                    ("Compared with", statistic.get("comparator")),
                ):
                    if field and str(field).upper() not in {"NONE", "NOT_APPLICABLE", "NOT_REPORTED"}:
                        details.append(f"{label}: {field}")
                searchable = " ".join(" ".join(str(part or "").split()) for part in [
                    metric, labels.get(metric, metric.replace("_", " ").title()), value,
                    finding.get("source_term"), source_file, locator, excerpt, *details,
                ]).lower()
                context_html = "".join(f'<div><strong>{esc(item.split(":", 1)[0])}:</strong>{esc(item.split(":", 1)[1])}</div>'
                                       if ":" in item else f'<div>{esc(item)}</div>' for item in details)
                rows.append(
                    f'<div class="fx-row stat-row" data-metric="{esc(metric)}" data-statistic-id="{esc(statistic.get("statistic_id", ""))}" data-fq="{esc(searchable)}">'
                    f'<span class="fx-m" style="background:{colors.get(metric,"#6b7280")}">{esc(labels.get(metric, metric.replace("_", " ").title()))}</span>'
                    f'<span class="fx-ph">{esc(finding.get("source_term", "Reported result"))}'
                    + (f'<span class="fx-reg">{esc(" · ".join(sign_context))}</span>' if sign_context else '') + '</span>'
                    f'<span class="fx-val">{esc(value)}</span>'
                    f'<span class="fx-src">{esc(source_file)}<br>{esc(locator)}</span>'
                    f'<span class="fx-q">&ldquo;{esc(excerpt)}&rdquo;</span>'
                    '<details class="fx-context"><summary>Source and study details</summary>'
                    f'{context_html}</details></div>')
    total = len(rows)
    buttons = [f'<button class="fxb on" data-f="all">All <i>{total}</i></button>']
    for metric in list(labels) + sorted(set(counts) - set(labels)):
        if counts.get(metric):
            label = labels.get(metric, metric.replace("_", " ").title())
            buttons.append(f'<button class="fxb" data-f="{esc(metric)}">{esc(label)} <i>{counts[metric]}</i></button>')
    return f'''<details class="frontpage-fold figures-fold">
<summary>Source statistics &mdash; {total:,} reported results from {len(corpus["sources"])} source files</summary>
<div class="fx-wrap" data-item-label="statistics">
  <div class="fx-intro">Each row is one result exactly as catalogued from its source, with the linked sign, anatomical or lateralizing context, source passage, and study details. These rows are not pooled; the separate weighted-analysis panel explains and shows the approved weighted comparisons.</div>
  <div class="fx-tools">
    <input type="text" class="fx-search" placeholder="Search signs, values, sources, anatomy, or source text&hellip;">
    <div class="fx-btns">{"".join(buttons)}</div>
  </div>
  <div class="fx-count"></div>
  <div class="fx-table">
{chr(10).join(rows)}
  </div>
</div>
</details>'''

deferred_fragments = {}

def defer_details_body(html, filename):
    """Keep a fold's banner in the main page and load its large body on demand."""
    summary_end = html.index("</summary>") + len("</summary>")
    details_end = html.rfind("</details>")
    deferred_fragments[filename] = html[summary_end:details_end]
    shell = html[:summary_end] + '<div class="lazy-fragment">Open this section to load its contents.</div>' + html[details_end:]
    return shell.replace("<details ", f'<details data-fragment="fragments/{filename}" ', 1)

figures_fold = defer_details_body(build_figures(CORPUS), "source-statistics.html")
def build_evidence_library(corpus):
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
            is_stat = bool(finding_statistics(row))
            search = " ".join(str(x or "") for x in [
                row["source_term"], row["claim"], statistic_search_text(row), row["citation"], row["locators"],
                row["evidence_text"], row["population"], row["laterality_localization"],
                source["source_file"], ROLE_LABEL.get(role, ""),
            ]).lower().replace('"', "")
            measure = statistic_block(row)
            rows.append(
                f'<div class="fx-row evidence-row" data-metric="{role}" data-fq="{esc(search)}">'
                f'<span class="fx-m" style="background:{role_color.get(role,"#6b7280")}">{esc(ROLE_LABEL.get(role,"Source information"))}</span>'
                f'<span class="fx-ph">{esc(row["source_term"])}<span class="fx-reg">{esc(row["phase"])}</span></span>'
                f'<span class="fx-val">{"Reported number" if is_stat else "Description"}</span>'
                f'<span class="fx-src">{esc(source["source_file"])}<br>{esc(row["locators"])}</span>'
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
    accounting = corpus["integration_accounting"]
    return f'''<div class="lib evidence-library">
<details class="lib-details evidence-library-details">
<summary>Reviewed evidence library &mdash; {accounting["public_ledger_findings"]:,} findings</summary>
<div class="fx-wrap" data-item-label="findings">
  <div class="fx-intro"><strong>{accounting["owner_reviewed_findings"]:,} findings reviewed</strong> &middot; <strong>{accounting["public_ledger_findings"]:,} findings included</strong> &middot; <strong>{accounting["source_reported_statistics"]:,} reported statistics</strong> from {accounting["source_reports"]} source files. Results from each source are shown separately and are not combined across studies.</div>
  <div class="fx-tools"><input type="text" class="fx-search" placeholder="Search signs, claims, measures, sources, locators&hellip;"><div class="fx-btns">{"".join(buttons)}</div></div>
  <div class="fx-count"></div>
  <div class="fx-table">{chr(10).join(rows)}</div>
</div>
</details>
</div>'''

evidence_library_html = defer_details_body(build_evidence_library(CORPUS), "evidence-library.html")


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

#semiology-view[hidden],#region-view[hidden]{display:none}
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
.browse-sign-wrap{margin:6px 0;border-radius:8px}
.browse-sign{width:100%;display:flex;align-items:center;gap:10px;background:#fff;border:1px solid var(--line);border-left:4px solid var(--accent,#8ca0b8);border-radius:8px;padding:9px 12px;text-align:left;font-family:inherit;cursor:pointer}
.browse-sign:hover{border-color:var(--teal);box-shadow:0 2px 9px rgba(15,30,61,.08)}
.browse-sign-wrap.open .browse-sign{border-color:var(--teal);border-radius:8px 8px 0 0}
.browse-arrow{color:var(--teal-d);font-size:1rem}
.browse-sign-name{flex:1;color:var(--navy);font-size:.86rem;font-weight:700;line-height:1.3}
.browse-meta{font-size:.66rem;color:var(--muted);white-space:nowrap}
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
.d-metrics{display:flex;gap:10px;padding:11px 0;border-bottom:1px solid var(--line2);flex-wrap:wrap}
.metric{flex:1;min-width:110px;background:#fff;border:1px solid var(--line);border-radius:8px;padding:8px 11px}
.metric .d-label{margin-bottom:5px}
.metric-val{font-size:.9rem;font-weight:700;color:var(--navy);font-family:'SF Mono','Consolas',monospace}
.evid-badge{display:inline-block;color:#fff;font-size:.72rem;font-weight:800;padding:2px 9px;border-radius:5px}
.cite{color:var(--teal-d);font-style:italic;font-size:.82rem}

@media (min-width:760px){
  .detail-inner{display:grid;grid-template-columns:1.5fr 1fr;grid-template-areas:"lat lat" "loc metrics" "map map" "notes notes" "cite cite" "ev ev";gap:0 20px;column-gap:24px}
  .d-lat{grid-area:lat}
  .d-loc{grid-area:loc}
  .d-map{grid-area:map}
  .d-metrics{grid-area:metrics;flex-direction:column;border-bottom:1px solid var(--line2)}
  .metric{min-width:0}
  .d-notes{grid-area:notes}
  .d-cite{grid-area:cite}
  .d-ev{grid-area:ev}
}

/* ---------- QUIZ MODE ---------- */
body.quiz .lat-chip,body.quiz .evid-dot{display:none}
body.quiz .sign{border-left-color:#cbd3e0}
.quiz-hint{display:none;background:#f0fbfd;border:1px solid #b8e6ee;color:#0a5b68;font-size:.78rem;padding:8px 14px;border-radius:8px;margin:0 0 12px}
body.quiz .quiz-hint{display:block}

/* library evidence chip + block */
.lib-chip{background:#fff4e6;color:#a15c00;border:1px solid #e8b878;display:inline-flex;align-items:center;gap:3px}
body.quiz .lib-chip{display:none}
.d-ev{background:#fffaf2;border:1px solid #f0dcbd;border-radius:9px;padding:10px 12px !important;margin-top:6px}
.d-ev .d-label{color:#a15c00;margin-bottom:7px}
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
.fx-tools{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:11px 16px 6px}
.fx-search{flex:0 0 auto;width:270px;border:1px solid var(--line);border-radius:7px;padding:8px 11px;font-size:.84rem;outline:none}
.fx-search:focus{border-color:var(--teal);box-shadow:0 0 0 3px rgba(14,157,176,.13)}
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
.reviewed-card-evidence{margin-bottom:9px}.ev-measure,.ev-owner{margin:4px 0;color:#475569}
.ev-stats{margin:7px 0}.ev-stats>summary{cursor:pointer;color:#0e7490;font-weight:700}.ev-stat-list{margin:5px 0 0;padding-left:22px}.ev-stat-list>li{margin:5px 0}.ev-stat-context{display:grid;gap:2px;margin-top:3px;color:#64748b;font-size:.9em}.ev-stat-context span{display:block}
.ev-trace{margin-top:5px;border:1px solid var(--line2);border-radius:6px;padding:4px 7px;color:#475569}
.ev-trace>summary{cursor:pointer;font-weight:700;color:var(--teal-d)}
.ev-trace>div{margin-top:4px;line-height:1.4}
.fx-row.fx-hidden{display:none}
@media (max-width:760px){
  .fx-row{grid-template-columns:1fr auto;grid-template-areas:"m val" "ph ph" "src src" "q q";gap:3px 8px}
  .fx-m{grid-area:m}.fx-ph{grid-area:ph}.fx-val{grid-area:val;text-align:right}.fx-src{grid-area:src}.fx-q{grid-area:q}.fx-context{grid-column:1 / -1}
  .fx-search{width:100%}
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
      const s=chip.closest('.sign');
      if(s&&traceSign(s.dataset.id,true)) render(chip.dataset.ba);
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
const fRegion=document.getElementById('filter-region');
const fPhase=document.getElementById('filter-phase');
const fLat=document.getElementById('filter-lat');
const fEvid=document.getElementById('filter-evid');
const resultCount=document.getElementById('result-count');
const noResults=document.getElementById('no-results');
const regionView=document.getElementById('region-view');
const semiologyView=document.getElementById('semiology-view');
const browseSections=document.getElementById('browse-sections');
const browseNote=document.getElementById('browse-note');
const signs=Array.from(document.querySelectorAll('.sign'));
const sections=Array.from(document.querySelectorAll('.region-section'));
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

const fragmentCache=new Map();
function loadFragment(path){
  if(!fragmentCache.has(path)){
    fragmentCache.set(path,fetch(path,{cache:'force-cache'}).then(response=>{
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
    const sec=document.getElementById(p.dataset.target);
    if(sec){ sec.classList.remove('collapsed'); sec.scrollIntoView({behavior:'smooth',block:'start'}); }
  });
});

// Filtering is deliberately submit-based. Typing does not touch the full sign
// list; Search or Enter applies the completed query once, and no result card is
// opened automatically.
function itemMatches(item){
  const reg=fRegion.value,ph=fPhase.value,lat=fLat.value,ev=fEvid.value;
  if(reg && item.dataset.region!==reg) return false;
  if(ph && !(item.dataset.phase||'').toLowerCase().includes(ph.toLowerCase())) return false;
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
function signName(id){ return canonicalSigns.get(String(id)).querySelector('.sign-name').textContent.trim(); }
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

function appendBrowseSign(parent,id){
  const source=canonicalSigns.get(String(id));
  if(!source) return;
  const wrapper=document.createElement('div'); wrapper.className='browse-sign-wrap'; wrapper.dataset.id=id;
  const row=document.createElement('button'); row.type='button'; row.className='browse-sign'; row.dataset.id=id;
  row.setAttribute('aria-expanded','false');
  wrapper.style.setProperty('--accent',source.style.getPropertyValue('--accent')||'#8ca0b8');
  const arrow=document.createElement('span'); arrow.className='browse-arrow'; arrow.textContent='›';
  const label=document.createElement('span'); label.className='browse-sign-name'; label.textContent=signName(String(id));
  const meta=document.createElement('span'); meta.className='browse-meta';
  meta.textContent=(source.dataset.phase||'')+' · '+(source.dataset.region||'');
  const detail=document.createElement('div'); detail.className='browse-detail'; detail.hidden=true;
  row.append(arrow,label,meta); wrapper.append(row,detail); parent.append(wrapper);
}

function appendClassificationNode(parent,node){
  const direct=sortSignIds(node.sign_ids||[]);
  const children=(node.children||[]).filter(child=>sortSignIds(child.all_sign_ids||child.sign_ids||[]).length);
  const subsection=document.createElement('div'); subsection.className='browse-subsection collapsed';
  const toggle=document.createElement('button');
  toggle.className='browse-subtoggle'; toggle.type='button'; toggle.setAttribute('aria-expanded','false');
  const chev=document.createElement('span'); chev.className='browse-chev'; chev.textContent='▼';
  const name=document.createElement('span'); name.className='browse-name'; name.textContent=node.label;
  const count=document.createElement('span'); count.className='browse-count';
  count.textContent=sortSignIds(node.all_sign_ids||node.sign_ids||[]).length;
  const body=document.createElement('div'); body.className='browse-subbody';
  toggle.append(chev,name,count); subsection.append(toggle,body);
  direct.forEach(id=>appendBrowseSign(body,id));
  children.forEach(child=>appendClassificationNode(body,child));
  parent.append(subsection);
}

function buildBrowseView(mode){
  if(builtBrowseMode===mode) return;
  builtBrowseMode=mode;
  browseSections.replaceChildren();
  browseNote.textContent=(mode==='az'||mode==='za')
    ? 'Signs are alphabetized here. Each row opens the same evidence-backed sign shown in the regional view.'
    : 'The same signs are grouped using the selected classification. Signs that are not yet assigned remain visible under Not yet classified.';
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
      sortSignIds(group.sign_ids||[]).forEach(id=>appendBrowseSign(body,id));
      (group.children||[]).forEach(child=>appendClassificationNode(body,child));
    }
    section.append(toggle,body); fragment.append(section);
  });
  browseSections.append(fragment);
}

function filterRegionView(){
  const active=!!(appliedQuery||fRegion.value||fPhase.value||fLat.value||fEvid.value);
  const showAreaBlocks=!!(appliedQuery||fRegion.value);
  const visibleIds=new Set();
  const perRegionIds={};
  function record(item){
    const id=String(item.dataset.id),region=item.dataset.region;
    visibleIds.add(id);
    if(!perRegionIds[region]) perRegionIds[region]=new Set();
    perRegionIds[region].add(id);
  }
  signs.forEach(sign=>{
    const show=itemMatches(sign);
    sign.style.display=show?'':'none';
    sign.classList.toggle('match',show&&!!appliedQuery);
    if(show) record(sign); else closeSign(sign);
  });
  let openedSection=false;
  sections.forEach(sec=>{
    const blocks=Array.from(sec.querySelectorAll(':scope .region-body > .sub-block'));
    let openedBlock=false,sectionHas=false;
    blocks.forEach(sb=>{
      const isArea=sb.classList.contains('area-map-block');
      const items=Array.from(sb.querySelectorAll('.sign'));
      const count=new Set(items.filter(item=>item.style.display!=='none').map(item=>String(item.dataset.id))).size;
      const show=count>0&&(!isArea||showAreaBlocks);
      sb.style.display=show?(isArea?'block':''):'none';
      const counter=sb.querySelector('.sub-count'); if(counter) counter.textContent=count;
      const shouldOpen=active&&show&&!openedSection&&!openedBlock;
      sb.classList.toggle('collapsed',!shouldOpen);
      const toggle=sb.querySelector('.sub-toggle'); if(toggle) toggle.setAttribute('aria-expanded',shouldOpen?'true':'false');
      if(shouldOpen) openedBlock=true;
      if(show) sectionHas=true;
    });
    if(!active){
      blocks.forEach(sb=>{
        const isArea=sb.classList.contains('area-map-block');
        sb.style.display=isArea?'none':'';
        sb.classList.add('collapsed');
        const toggle=sb.querySelector('.sub-toggle'); if(toggle) toggle.setAttribute('aria-expanded','false');
      });
      sectionHas=true;
    }
    sec.style.display=sectionHas?'':'none';
    const shouldOpen=!active||(sectionHas&&!openedSection);
    sec.classList.toggle('collapsed',!shouldOpen);
    sec.querySelector('.region-toggle').setAttribute('aria-expanded',shouldOpen?'true':'false');
    if(active&&sectionHas&&!openedSection) openedSection=true;
  });
  document.querySelectorAll('[data-region]').forEach(el=>{
    if(el.tagName==='SPAN'&&(el.closest('.region-count')||el.closest('.pill-count'))){
      const ids=perRegionIds[el.dataset.region];
      el.textContent=active?(ids?ids.size:0):(totalRegionIds[el.dataset.region]?.size||0);
    }
  });
  document.querySelectorAll('.pill').forEach(p=>{
    const sec=document.getElementById(p.dataset.target);
    p.style.opacity=(sec&&sec.style.display!=='none')?'1':'.4';
  });
  return visibleIds.size;
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
  return visibleIds.size;
}

function filterAll(){
  const visible=browseMode.value==='region'?filterRegionView():filterBrowseView();
  const active=!!(appliedQuery||fRegion.value||fPhase.value||fLat.value||fEvid.value);
  resultCount.textContent=visible+' of '+uniqueSignCount+' signs shown';
  document.body.classList.toggle('filtering',active);
  noResults.style.display=visible===0?'block':'none';
}

function setBrowseMode(mode){
  const regional=mode==='region';
  regionView.hidden=!regional; semiologyView.hidden=regional;
  document.body.classList.toggle('alt-browse',!regional);
  if(!regional) buildBrowseView(mode);
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

browseSections.addEventListener('click',event=>{
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
});

function applySearch(){ appliedQuery=searchInput.value.toLowerCase().trim(); filterAll(); }
searchSubmit.addEventListener('click',applySearch);
searchInput.addEventListener('keydown',event=>{ if(event.key==='Enter'){ event.preventDefault(); applySearch(); } });
searchClear.addEventListener('click',()=>{ searchInput.value=''; appliedQuery=''; filterAll(); searchInput.focus(); });
[fRegion,fPhase,fLat,fEvid].forEach(el=>el.addEventListener('change',filterAll));
browseMode.addEventListener('change',()=>setBrowseMode(browseMode.value));

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
  document.querySelectorAll('.region-section').forEach(sec=>{
    sec.classList.toggle('collapsed',!open);
    const t=sec.querySelector('.region-toggle'); if(t) t.setAttribute('aria-expanded',open);
  });
  document.querySelectorAll('.sub-block').forEach(sb=>sb.classList.toggle('collapsed',!open));
  document.querySelectorAll('.sub-toggle').forEach(b=>b.setAttribute('aria-expanded',open));
  if(open) signs.forEach(s=>{ if(s.style.display!=='none'&&s.closest('.sub-block')?.style.display!=='none') openSign(s); });
  else     signs.forEach(s=>closeSign(s));
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
mRegionSort.addEventListener('change',()=>mSortRegion(mRegionSort.value));
mSignSort.addEventListener('change',()=>mSortFlat(mSignSort.value));

// ---- reviewed findings and source statistics: independently scoped filters ----
function bindFxWrap(wrap){
  if(wrap.dataset.filterBound) return;
  wrap.dataset.filterBound='true';
  const search=wrap.querySelector('.fx-search');
  const table=wrap.querySelector('.fx-table');
  const count=wrap.querySelector('.fx-count');
  if(!search||!table||!count) return;
  const rows=Array.from(table.querySelectorAll('.fx-row'));
  const buttons=Array.from(wrap.querySelectorAll('.fxb'));
  const label=wrap.dataset.itemLabel||'items';
  let mfilter='all';
  function apply(){
    const q=(search.value||'').toLowerCase().trim();
    let vis=0;
    rows.forEach(r=>{
      const show=((mfilter==='all')||r.dataset.metric===mfilter)&&(!q||(r.dataset.fq||'').includes(q));
      r.classList.toggle('fx-hidden',!show);
      if(show) vis++;
    });
    count.textContent=vis+' of '+rows.length+' '+label+' shown';
  }
  buttons.forEach(b=>b.addEventListener('click',()=>{
    buttons.forEach(x=>x.classList.toggle('on',x===b));
    mfilter=b.dataset.f;
    apply();
  }));
  search.addEventListener('input',apply);
  apply();
}
document.querySelectorAll('.fx-wrap').forEach(bindFxWrap);
document.querySelectorAll('details[data-fragment]').forEach(fold=>{
  fold.addEventListener('toggle',async()=>{
    if(!fold.open||fold.dataset.loaded==='true') return;
    const host=fold.querySelector(':scope > .lazy-fragment');
    if(!host) return;
    host.textContent='Loading…';
    try{
      host.outerHTML=await loadFragment(fold.dataset.fragment);
      fold.dataset.loaded='true';
      fold.querySelectorAll('.fx-wrap').forEach(bindFxWrap);
    }catch(error){
      host.textContent='This section could not be loaded. Close it, reload the page, and try again.';
    }
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
""" + brain_fold + meta_fold + figures_fold + """
  <div class="quiz-hint"><strong>Quiz mode on:</strong> lateralization &amp; evidence cues are hidden. Read each sign, predict its localization/lateralization, then expand to check yourself.</div>
  <div id="region-view">
""" + sections_html + """
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
    <summary>Source Library &mdash; """ + str(len(PAPERS)) + """ papers grounding this resource</summary>
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
assert h.count("data-search=") == _card_count
assert 'class="detail"' in h
assert '@media (max-width:760px)' in h
assert h.count('class="pill"')==len(region_order)
assert 'body.quiz' in h
print("All sanity checks passed.")
