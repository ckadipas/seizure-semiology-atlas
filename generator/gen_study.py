import json, re, os
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

with open(os.path.join(ROOT,"data","semiology_data.json")) as f:
    data = json.load(f)

# ---- load corpus enrichment (source-grounded evidence, new signs, papers, forest) ----
with open(os.path.join(ROOT,"enrichment","enrichment.json")) as f:
    ENR = json.load(f)
EVID = ENR["evidence"]; NEW_SIGNS = ENR["new_signs"]; PAPERS = ENR["papers"]; LATERAL = ENR["lateral"]

# assign ids to new signs and append
_nextid = max(x["id"] for x in data) + 1
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

latcolor = {"contra":"#c0392b","ipsi":"#2471a3","dominant":"#8e44ad","nondominant":"#1a7a4a","right":"#d35400","nonlat":"#6b7280","variable":"#95691a"}
latbg    = {"contra":"#fdf2f2","ipsi":"#eaf4fb","dominant":"#f5f0fb","nondominant":"#eafaf1","right":"#fef5ee","nonlat":"#f3f4f6","variable":"#fdf8ee"}
latlabel = {"contra":"CONTRA","ipsi":"IPSI","dominant":"DOM","nondominant":"NON-DOM","right":"RIGHT","nonlat":"NON-LAT","variable":"VARIABLE"}
evidcolor= {"I":"#1a7a4a","II":"#c47a00","III":"#c0392b"}

region_order = ["Temporal","Frontal","Parietal","Occipital","Insular","Deep/Subcortical","Multiregional/Propagation"]
region_short = {"Temporal":"Temporal","Frontal":"Frontal","Parietal":"Parietal","Occipital":"Occipital","Insular":"Insular","Deep/Subcortical":"Deep","Multiregional/Propagation":"Multiregional"}
region_colors= {"Temporal":"#1a3a6b","Frontal":"#2d4a1e","Parietal":"#4a1e3d","Occipital":"#1e3d4a","Insular":"#4a3a1e","Deep/Subcortical":"#3d2a0a","Multiregional/Propagation":"#1e1e4a"}

def esc(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")
def slug(s):
    return re.sub(r'[^a-z0-9]+','-', s.lower()).strip('-')

# group data: region -> sub -> [signs]
grouped = OrderedDict()
for r in region_order:
    grouped[r] = OrderedDict()
for d in data:
    grouped[d["region"]].setdefault(d["sub"], []).append(d)

region_counts = {r: sum(len(v) for v in grouped[r].values()) for r in region_order}

# ---- build region-jump pills ----
pills = []
for r in region_order:
    pills.append(f'<button class="pill" data-target="sec-{slug(r)}"><span class="pill-name">{esc(region_short[r])}</span><span class="pill-count" data-region="{esc(r)}">{region_counts[r]}</span></button>')
pills_html = "\n".join(pills)

# ---- build sections ----
sections = []
for r in region_order:
    rc = region_colors[r]
    sub_blocks = []
    for sub, signs in grouped[r].items():
        rows = []
        for d in signs:
            lc, ec = d["latcode"], d["evid"]
            accent = latcolor.get(lc,"#999")
            ev_text = " ".join(e["p"]+" "+e["f"] for e in d.get("_ev",[]))
            search_str = " ".join([d["sign"],d["phase"],d["lat"],d["loc"],d["sens"],d["spec"],d["notes"],d["cite"],d["region"],d["sub"],ev_text]).lower().replace('"',"")
            has_ev = bool(d.get("_ev"))
            lib_chip = ('<span class="chip lib-chip" title="Grounded in your uploaded literature">&#128218; '+str(len(d["_ev"]))+'</span>') if has_ev else ''
            ev_block = ''
            if has_ev:
                items = "".join('<li><span class="ev-src">'+esc(e["p"])+'</span> '+esc(e["f"])+'</li>' for e in d["_ev"])
                ev_block = ('<div class="d-row d-ev"><span class="d-label">&#128218; Evidence in your library</span>'
                            '<ul class="ev-list">'+items+'</ul></div>')
            rows.append(f'''<div class="sign" data-region="{esc(d['region'])}" data-phase="{esc(d['phase'])}" data-latcode="{lc}" data-evid="{ec}" data-search="{esc(search_str)}" style="--accent:{accent}">
  <button class="sign-head" aria-expanded="false">
    <span class="chevron">&#8250;</span>
    <span class="sign-name">{esc(d['sign'])}</span>
    <span class="head-chips">
      <span class="chip phase-badge phase-{d['phase'].split('/')[0].lower()}">{esc(d['phase'])}</span>
      <span class="chip lat-chip" style="color:{latcolor.get(lc,'#333')};background:{latbg.get(lc,'#f7f7f7')};border-color:{latcolor.get(lc,'#333')}">{latlabel.get(lc,'?')}</span>
      <span class="chip evid-dot" style="background:{evidcolor.get(ec,'#888')}" title="Evidence level {ec}">{ec}</span>
      {lib_chip}
    </span>
  </button>
  <div class="detail">
    <div class="detail-inner">
      <div class="d-row d-lat">
        <span class="d-label">Lateralization</span>
        <span class="d-value"><span class="lat-badge" style="color:{latcolor.get(lc,'#333')};background:{latbg.get(lc,'#f7f7f7')};border-color:{latcolor.get(lc,'#333')}">{latlabel.get(lc,'?')}</span> {esc(d['lat'])}</span>
      </div>
      <div class="d-row d-loc">
        <span class="d-label">Anatomical localization</span>
        <span class="d-value">{esc(d['loc'])}</span>
      </div>
      <div class="d-metrics">
        <div class="metric"><span class="d-label">Sensitivity</span><span class="metric-val">{esc(d['sens'])}</span></div>
        <div class="metric"><span class="d-label">Specificity</span><span class="metric-val">{esc(d['spec'])}</span></div>
        <div class="metric"><span class="d-label">Evidence</span><span class="metric-val"><span class="evid-badge" style="background:{evidcolor.get(ec,'#888')}">{ec}</span></span></div>
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
    </div>
  </div>
</div>''')
        sub_blocks.append(f'<div class="sub-block"><div class="sub-label">&#8627;&nbsp; {esc(sub)}</div>\n{chr(10).join(rows)}\n</div>')
    sections.append(f'''<section class="region-section" id="sec-{slug(r)}" data-region="{esc(r)}">
  <button class="region-toggle" style="--rc:{rc}" aria-expanded="true">
    <span class="region-chev">&#9662;</span>
    <span class="region-name">{esc(r).upper()} LOBE</span>
    <span class="region-count"><span data-region="{esc(r)}">{region_counts[r]}</span> signs</span>
  </button>
  <div class="region-body">
{chr(10).join(sub_blocks)}
  </div>
</section>''')
sections_html = "\n".join(sections)

# ---------- Probabilistic forest plot (Alim-Marvasti 2022) ----------
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

forest_html = f'''<div class="forest-wrap">
  <div class="forest-card">
    <div class="forest-head">
      <h2>&#129517; Lateralizing reliability of the classic bedside signs</h2>
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
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;background:var(--bg);color:var(--ink);font-size:15px;line-height:1.5}

/* ---------- TITLE ---------- */
.site-header{background:linear-gradient(135deg,var(--navy) 0%,var(--navy2) 55%,#0a4a5a 100%);color:#fff;padding:24px 26px 20px}
.site-header h1{font-size:1.5rem;font-weight:800;letter-spacing:.01em;margin-bottom:5px}
.site-header p{font-size:.86rem;opacity:.9;max-width:70ch}
.edu-note{margin-top:12px;display:inline-flex;align-items:center;gap:8px;background:rgba(255,220,120,.16);border:1px solid rgba(255,220,120,.4);color:#ffe9b0;font-size:.76rem;font-weight:600;padding:5px 12px;border-radius:20px}
.header-meta{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
.header-badge{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.24);border-radius:5px;padding:3px 10px;font-size:.72rem;font-weight:600}

/* ---------- STICKY HEAD ---------- */
.sticky-head{position:sticky;top:0;z-index:100;background:#fff;box-shadow:0 2px 10px rgba(15,30,61,.09);border-bottom:1px solid var(--line)}
.region-nav{display:flex;gap:7px;overflow-x:auto;padding:9px 16px;-webkit-overflow-scrolling:touch;border-bottom:1px solid var(--line2);scrollbar-width:thin}
.region-nav::-webkit-scrollbar{height:5px}
.region-nav::-webkit-scrollbar-thumb{background:#cfd6e2;border-radius:3px}
.pill{flex:0 0 auto;display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);background:#fff;color:var(--navy);border-radius:20px;padding:5px 12px;font-size:.78rem;font-weight:700;cursor:pointer;transition:all .12s;white-space:nowrap}
.pill:hover{border-color:var(--teal);color:var(--teal-d);background:#f0fbfd}
.pill-count{background:#eef1f6;color:var(--muted);border-radius:10px;padding:0 7px;font-size:.68rem;font-weight:700}

.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:10px 16px}
.search-wrap{position:relative;flex:0 0 auto}
.search-icon{position:absolute;left:9px;top:50%;transform:translateY(-50%);color:#9aa3b2;font-size:.85rem;pointer-events:none}
#search-input{width:260px;border:1px solid var(--line);border-radius:7px;padding:8px 10px 8px 30px;font-size:.86rem;color:var(--ink);outline:none;background:#fff}
#search-input:focus{border-color:var(--teal);box-shadow:0 0 0 3px rgba(14,157,176,.13)}
.filter-toggle{display:none;align-items:center;gap:6px;border:1px solid var(--line);background:#fff;color:var(--navy);border-radius:7px;padding:8px 12px;font-size:.84rem;font-weight:700;cursor:pointer}
.filter-toggle .chev{font-size:.6rem;transition:transform .15s}
.filter-toggle.open .chev{transform:rotate(180deg)}
.filter-panel{display:flex;gap:9px;flex-wrap:wrap;align-items:center}
.filter-field{display:flex;flex-direction:column;gap:2px}
.ctrl-label{font-size:.6rem;font-weight:800;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.filter-field select{border:1px solid var(--line);border-radius:6px;padding:5px 8px;font-size:.8rem;color:var(--ink);background:#fff;outline:none}
.filter-field select:focus{border-color:var(--teal)}
.tool-actions{display:flex;gap:7px;align-items:center;margin-left:auto;flex-wrap:wrap}
.act-btn{border:1px solid var(--line);background:#fff;color:var(--navy);border-radius:7px;padding:7px 11px;font-size:.78rem;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px;transition:all .12s}
.act-btn:hover{border-color:var(--teal);color:var(--teal-d);background:#f0fbfd}
.quiz-toggle{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line);border-radius:7px;padding:6px 11px;font-size:.78rem;font-weight:700;color:var(--navy);cursor:pointer;user-select:none}
.quiz-toggle input{display:none}
.quiz-switch{width:34px;height:18px;border-radius:10px;background:#cbd3e0;position:relative;transition:background .15s;flex:0 0 auto}
.quiz-switch::after{content:"";position:absolute;top:2px;left:2px;width:14px;height:14px;border-radius:50%;background:#fff;transition:transform .15s;box-shadow:0 1px 2px rgba(0,0,0,.25)}
.quiz-toggle input:checked + .quiz-switch{background:var(--teal)}
.quiz-toggle input:checked + .quiz-switch::after{transform:translateX(16px)}
#result-count{font-size:.76rem;color:var(--muted);font-style:italic;width:100%;padding:0 2px}

/* ---------- MAIN ---------- */
main{padding:16px 16px 48px;max-width:1180px;margin:0 auto}
.region-section{margin-bottom:16px;scroll-margin-top:132px}
.region-toggle{width:100%;display:flex;align-items:center;gap:12px;background:var(--rc);background:linear-gradient(120deg,var(--rc),color-mix(in srgb,var(--rc) 82%,#000));color:#fff;border:none;border-radius:11px;padding:13px 18px;font-size:1rem;font-weight:800;letter-spacing:.03em;cursor:pointer;text-align:left;box-shadow:0 2px 8px rgba(15,30,61,.12)}
.region-chev{font-size:.8rem;transition:transform .18s;opacity:.9}
.region-section.collapsed .region-chev{transform:rotate(-90deg)}
.region-name{flex:1}
.region-count{font-size:.72rem;font-weight:700;opacity:.85;background:rgba(255,255,255,.18);padding:3px 10px;border-radius:12px}
.region-body{padding:10px 0 4px}
.region-section.collapsed .region-body{display:none}

.sub-block{margin:8px 0 14px}
.sub-label{font-size:.78rem;font-weight:700;font-style:italic;color:#5a6478;padding:6px 6px 8px;letter-spacing:.01em}

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
  .detail-inner{display:grid;grid-template-columns:1.5fr 1fr;grid-template-areas:"lat lat" "loc metrics" "notes notes" "cite cite" "ev ev";gap:0 20px;column-gap:24px}
  .d-lat{grid-area:lat}
  .d-loc{grid-area:loc}
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

/* framework callout */
.callout{max-width:1180px;margin:0 auto 14px;padding:0 16px}
.callout-inner{background:linear-gradient(120deg,#0f2540,#123a52);color:#e6f0f6;border-radius:12px;padding:15px 18px;font-size:.86rem;line-height:1.55;border:1px solid #1c4a63}
.callout-inner strong{color:#7fd4e6}
.callout-inner .tag{display:inline-block;background:#0e9db0;color:#04212a;font-size:.62rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;padding:2px 8px;border-radius:5px;margin-right:8px;vertical-align:middle}

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

/* ==================== MOBILE ==================== */
@media (max-width:760px){
  .site-header{padding:18px 16px 14px}
  .site-header h1{font-size:1.18rem}
  .search-wrap{flex:1 1 100%}
  #search-input{width:100%}
  .filter-toggle{display:inline-flex}
  .filter-panel{display:none;flex:1 1 100%;width:100%;flex-direction:row;flex-wrap:wrap;gap:9px;padding-top:2px}
  .filter-panel.open{display:flex}
  .filter-field{flex:1 1 45%}
  .filter-field select{width:100%}
  .tool-actions{margin-left:0;flex:1 1 100%;justify-content:flex-start}
  .region-section{scroll-margin-top:150px}
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
  .sticky-head,.filter-toggle{display:none}
  .detail{max-height:none!important}
  .region-section.collapsed .region-body{display:block}
  .site-header,.region-toggle,.evid-badge,.phase-badge,.chip{print-color-adjust:exact;-webkit-print-color-adjust:exact}
}
"""

JS = r"""
const searchInput=document.getElementById('search-input');
const fRegion=document.getElementById('filter-region');
const fPhase=document.getElementById('filter-phase');
const fLat=document.getElementById('filter-lat');
const fEvid=document.getElementById('filter-evid');
const resultCount=document.getElementById('result-count');
const noResults=document.getElementById('no-results');
const signs=Array.from(document.querySelectorAll('.sign'));
const sections=Array.from(document.querySelectorAll('.region-section'));

function openSign(sign){
  const d=sign.querySelector('.detail');
  sign.classList.add('open');
  sign.querySelector('.sign-head').setAttribute('aria-expanded','true');
  d.style.maxHeight=d.scrollHeight+'px';
}
function closeSign(sign){
  const d=sign.querySelector('.detail');
  sign.classList.remove('open');
  sign.querySelector('.sign-head').setAttribute('aria-expanded','false');
  d.style.maxHeight='0px';
}
function toggleSign(sign){ sign.classList.contains('open')?closeSign(sign):openSign(sign); }

// row click
signs.forEach(sign=>{
  sign.querySelector('.sign-head').addEventListener('click',()=>toggleSign(sign));
});

// region collapse
sections.forEach(sec=>{
  sec.querySelector('.region-toggle').addEventListener('click',()=>{
    const collapsed=sec.classList.toggle('collapsed');
    sec.querySelector('.region-toggle').setAttribute('aria-expanded',!collapsed);
  });
});

// region-jump pills
document.querySelectorAll('.pill').forEach(p=>{
  p.addEventListener('click',()=>{
    const sec=document.getElementById(p.dataset.target);
    if(sec){ sec.classList.remove('collapsed'); sec.scrollIntoView({behavior:'smooth',block:'start'}); }
  });
});

// filtering
function filterAll(){
  const q=searchInput.value.toLowerCase().trim();
  const reg=fRegion.value,ph=fPhase.value,lat=fLat.value,ev=fEvid.value;
  let visible=0;
  const perRegion={};

  if(q.length>=1){ sections.forEach(s=>s.classList.remove('collapsed')); }

  signs.forEach(sign=>{
    let show=true;
    if(reg && sign.dataset.region!==reg) show=false;
    if(ph && !(sign.dataset.phase||'').toLowerCase().includes(ph.toLowerCase())) show=false;
    if(lat && sign.dataset.latcode!==lat) show=false;
    if(ev && sign.dataset.evid!==ev) show=false;
    if(q && !(sign.dataset.search||'').includes(q)) show=false;
    sign.classList.toggle('hidden-sign',!show);
    sign.style.display=show?'':'none';
    if(show){
      visible++;
      perRegion[sign.dataset.region]=(perRegion[sign.dataset.region]||0)+1;
      // auto-expand matches on active search
      if(q.length>=2){ sign.classList.add('match'); openSign(sign); }
      else { sign.classList.remove('match'); if(!q) closeSign(sign); }
    } else {
      sign.classList.remove('match');
      closeSign(sign);
    }
  });

  // hide empty sub-blocks
  document.querySelectorAll('.sub-block').forEach(sb=>{
    const any=Array.from(sb.querySelectorAll('.sign')).some(s=>s.style.display!=='none');
    sb.style.display=any?'':'none';
  });
  // hide empty sections + update counts
  sections.forEach(sec=>{
    const r=sec.dataset.region;
    const c=perRegion[r]||0;
    sec.style.display=c>0?'':'none';
    sec.querySelectorAll('.region-count [data-region], .region-count span[data-region]').forEach(()=>{});
  });
  // update region + pill counts
  document.querySelectorAll('[data-region]').forEach(el=>{
    if(el.tagName==='SPAN' && (el.closest('.region-count')||el.closest('.pill-count'))){
      el.textContent=perRegion[el.dataset.region]||0;
    }
  });
  document.querySelectorAll('.pill').forEach(p=>{
    const target=p.dataset.target;
    const sec=document.getElementById(target);
    p.style.opacity=(sec && sec.style.display!=='none')?'1':'.4';
  });

  resultCount.textContent=visible+' of '+signs.length+' signs shown';
  noResults.style.display=visible===0?'block':'none';
}

[searchInput,fRegion,fPhase,fLat,fEvid].forEach(el=>{
  el.addEventListener(el.tagName==='INPUT'?'input':'change',filterAll);
});

// expand / collapse all (visible)
document.getElementById('expand-all').addEventListener('click',()=>{
  signs.forEach(s=>{ if(s.style.display!=='none') openSign(s); });
});
document.getElementById('collapse-all').addEventListener('click',()=>{
  signs.forEach(s=>closeSign(s));
});

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

filterAll();
"""

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>Seizure Semiology &mdash; Interactive Study Reference</title>
<style>""" + CSS + """</style>
</head>
<body>

<div class="site-header">
  <h1>&#129504; Seizure Semiology &mdash; Interactive Study Reference</h1>
  <p>A browsable, expandable guide to localizing &amp; lateralizing signs for epilepsy fellows &mdash; now grounded in a curated library of """ + str(len(PAPERS)) + """ primary papers. Scan the sign names, then tap any entry to reveal its localization, sensitivity, specificity, mechanism, citations, and the specific evidence from your uploaded literature.</p>
  <div class="edu-note">&#9888;&#65039; Educational &amp; training reference only &mdash; not a tool for clinical decision-making.</div>
  <div class="header-meta">
    <span class="header-badge">&#128203; """ + str(len(data)) + """ Signs</span>
    <span class="header-badge">&#128218; """ + str(n_ev_signs) + """ Signs Source-Grounded</span>
    <span class="header-badge">&#129517; Lateralization Reliability Chart</span>
    <span class="header-badge">&#127891; Quiz Mode</span>
    <span class="header-badge">&#127467;&#127479; French SEEG + &#127482;&#127480; Cleveland</span>
  </div>
</div>

<div class="sticky-head">
  <nav class="region-nav">
""" + pills_html + """
  </nav>
  <div class="toolbar">
    <div class="search-wrap">
      <span class="search-icon">&#128269;</span>
      <input type="text" id="search-input" placeholder="Search signs, mechanisms, citations...">
    </div>
    <button class="filter-toggle" id="filter-toggle" aria-expanded="false"><span>&#9881;&#65039; Filters</span><span class="chev">&#9660;</span></button>
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
    <span id="result-count"></span>
  </div>
</div>

<main>
""" + forest_html + callout_html + """
  <div class="quiz-hint">&#127891; <strong>Quiz mode on:</strong> lateralization &amp; evidence cues are hidden. Read each sign, predict its localization/lateralization, then expand to check yourself.</div>
""" + sections_html + """
  <div id="no-results">No signs match the current search or filters. Try clearing them.</div>
</main>

<div class="lib">
  <details class="lib-details">
    <summary>&#128218; Source Library &mdash; """ + str(len(PAPERS)) + """ papers grounding this resource</summary>
    <div class="lib-grid">
""" + papers_html + """
    </div>
  </details>
</div>

<div class="abbrev">
  <details class="abbrev-details">
    <summary>&#128220; Abbreviations &amp; Terminology</summary>
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

<div class="footer">
  <strong>Educational use:</strong> This reference is designed for teaching and self-study by epilepsy trainees. Sensitivity and specificity values are approximate teaching figures drawn from single- and multi-center cohorts and reflect performance within the populations studied; they are <strong>not</strong> validated for individual clinical decision-making. Real localization always integrates ictal EEG, imaging, neuropsychology, and history. &nbsp;|&nbsp;
  <strong>Evidence tiers:</strong> I = multiple cohort studies / validated SEEG stimulation series; II = retrospective case series or single-center; III = case reports, expert opinion, or isolated stimulation observations. &nbsp;|&nbsp;
  <strong>Schools referenced:</strong> Paris SEEG (Bancaud, Talairach, Chauvel, Bartolomei, McGonigal); Cleveland Clinic (L&#252;ders, Kotagal, Bleasel, Dinner); Lyon SEEG (Isnard, Maugui&#232;re, Ryvlin, Ostrowsky); Montreal (Penfield, Jasper, Rasmussen).
</div>

<script>""" + JS + """</script>
</body>
</html>"""

for name in ("seizure_semiology_localization.html", "index.html"):
    with open(os.path.join(DOCS, name), "w") as f:
        f.write(HEAD)

print(f"Written: {len(HEAD)} chars, {len(data)} signs")

# ---- sanity checks ----
h=HEAD
assert h.count('class="sign"')==len(data), f'sign count {h.count(chr(34)+"class="+chr(34))}'
assert h.count(chr(34).join(["class=","sign",""]))==len(data)
assert 'id="quiz-mode"' in h
assert 'id="expand-all"' in h and 'id="collapse-all"' in h
assert h.count("data-search=")==len(data)
assert 'class="detail"' in h
assert '@media (max-width:760px)' in h
assert h.count('class="pill"')==7
assert 'body.quiz' in h
print("All sanity checks passed.")
