import { atlasGroups, atlasCounts, atlasEvidenceSection, atlasDictionaryGroups, atlasMetricLabels, atlasMetricTypes, atlasWeightPresentation, atlasAppraisalLabel, atlasSourceFindingsMarkup, atlasStatisticGroups } from './atlas_projection.mjs?v=2997065b3e977309d968ad0585dae4c4d2423a04d084b669ead100dcf89b94aa';

const styles = `
:host{color-scheme:light;--ink:#193a3b;--muted:#60736c;--teal:#176862;--pale:#eaf2ed;--line:#dce5df;--canvas:#f6f8f4;--serif:Georgia,'Times New Roman',serif;font:15px/1.5 Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:var(--ink);background:var(--canvas)}
*{box-sizing:border-box}body{margin:0}button,input,select{font:inherit;color:inherit}button,summary,a{touch-action:manipulation}button,summary{cursor:pointer}button,a,input,select,summary{-webkit-tap-highlight-color:transparent}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #b88636;outline-offset:3px}button:disabled{cursor:default;opacity:.6}a{color:var(--teal)}h1,h2,h3,h4,p{margin:0}h1{font:34px/1.2 var(--serif);letter-spacing:-.6px}h2{font:25px/1.25 var(--serif)}h3{font-size:16px}h4{font-size:14px}small,.muted{color:var(--muted)}[hidden]{display:none!important}button{border:0;background:none}.skip{position:absolute;top:-70px;left:16px;background:white;padding:12px;z-index:5}.skip:focus{top:10px}
.masthead{background:white;border-bottom:1px solid var(--line)}.mast-inner{max-width:1220px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:18px;padding:15px 28px}.brand{display:flex;gap:9px;align-items:center;font-weight:700;letter-spacing:-.3px}.brand svg{width:28px;height:28px}.help-button{color:var(--teal);font-size:12px;min-height:44px;padding:8px 0;text-align:right;text-decoration:underline;text-underline-offset:3px}
main{max-width:1220px;margin:auto;padding:30px 28px}.intro{display:flex;gap:20px;align-items:center;justify-content:space-between;margin-bottom:23px}.corpus{font-size:13px;color:var(--muted)}.corpus button{padding:7px 0;color:var(--teal);text-decoration:underline;text-underline-offset:3px}.toolbar{display:grid;grid-template-columns:minmax(220px,1.4fr) minmax(170px,1fr) minmax(185px,1fr);gap:14px;padding:18px;background:white;border:1px solid var(--line);border-radius:9px}.field{display:flex;flex-direction:column;gap:6px;min-width:0}.field label{font-size:11px;font-weight:650;color:var(--muted)}input,select{width:100%;min-width:0;height:43px;border:1px solid #cdd9d2;background:white;border-radius:5px;padding:0 10px;font-size:14px}input::placeholder{color:#87958d}.dependent{grid-column:1/-1;display:flex;gap:14px}.dependent .field{flex:1;max-width:540px}.list-meta{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:13px 1px;font-size:12px;color:var(--muted)}.list-meta button{font-size:12px;min-height:36px;text-decoration:underline;text-underline-offset:3px;color:var(--muted)}
.sign-list{display:grid;gap:10px}.sign-card{background:white;border:1px solid var(--line);border-radius:8px;min-width:0}.sign-card>summary{display:flex;align-items:center;gap:20px;list-style:none;padding:19px 21px}.sign-card>summary::-webkit-details-marker{display:none}.sign-card>summary:after{content:'+';font-size:23px;font-weight:300;color:var(--teal);margin-left:2px;flex:none}.sign-card[open]>summary:after{content:'−'}.sign-card[open]{border-color:#9dbbb0}.sign-card[open]>summary{background:#f3f7f2;border-radius:8px 8px 0 0}.sign-title{min-width:0;flex:1}.sign-title strong{font-size:17px;font-weight:600;line-height:1.4;display:block;overflow-wrap:anywhere}.sign-meta{font-size:12px;color:var(--muted);display:block;margin-top:5px}.weights{display:flex;gap:9px;flex-wrap:wrap}.weight-scope{flex-basis:100%;font-size:10px;color:var(--muted)}.weight{display:flex;align-items:baseline;gap:9px;padding:6px 10px;border-radius:5px;background:var(--pale);font-size:11px;color:#46665b}.weight b{font-size:15px;color:var(--teal);font-weight:650;font-variant-numeric:tabular-nums}.weight.pending{background:#f7f0e2;color:#826535}.weight.pending b{color:#826535;font-size:12px}.weight.none{background:#f3f5f2;color:#7a877f}.weight.none b{color:#7a877f}.sign-body{padding:20px;min-width:0;border-top:1px solid var(--line)}.inside-controls{display:flex;gap:12px;margin:0 0 20px;align-items:end;flex-wrap:wrap}.inside-controls .field{flex:1;min-width:150px}.inside-controls select{font-size:12px;height:40px}.inside-controls .field label{font-size:10px}.inside-controls .filter-button{min-height:40px;color:var(--teal);font-size:12px;padding:0 5px}.filter-row{display:flex;gap:10px;margin-bottom:18px}.filter-row .field{flex:1;max-width:360px}.context-details{font-size:12px;margin:0 0 18px;color:var(--muted)}.context-details>summary{color:var(--teal);min-height:32px;display:flex;align-items:center;gap:6px}.context-details>summary:before{content:'▸'}.context-details[open]>summary:before{content:'▾'}.context-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:12px 0}.context-grid h4{font-size:12px;margin-bottom:7px}.context-line{margin:7px 0;overflow-wrap:anywhere}.context-line small{display:block;font-size:10px}.source-wording{margin-top:10px;font-size:12px}
.paper{border-top:1px solid var(--line);padding-top:20px;margin-top:20px;min-width:0}.paper:first-child{margin-top:0;padding-top:0;border:0}.paper-head{display:flex;justify-content:space-between;align-items:start;gap:16px;margin-bottom:12px}.paper-title{min-width:0;flex:1}.paper-title h3{font-size:16px}.paper-title p{font-size:12px;color:var(--muted);margin-top:4px;overflow-wrap:anywhere}.paper .weights{gap:6px}.paper .weight{font-size:10px;padding:4px 7px}.paper .weight b{font-size:13px}.paper-tools{display:flex;gap:15px;align-items:baseline;flex-wrap:wrap;font-size:11px;margin:8px 0 14px}.paper-tools a,.text-button{font-size:12px;color:var(--teal);text-decoration:underline;text-underline-offset:3px}.text-button{padding:7px 0;min-height:34px;text-align:left}.calculation{font-size:12px;min-width:0}.calculation summary{color:var(--teal);min-height:32px;display:flex;align-items:center;gap:6px}.calculation summary:before{content:'▸'}.calculation[open] summary:before{content:'▾'}.calculation-body{padding:12px 0 16px;display:grid;gap:12px}.calculation-row{padding:12px;background:#f5f8f3;border-radius:5px}.calculation-row strong{display:block;margin-bottom:6px}.factors{display:flex;flex-wrap:wrap;gap:5px 14px;font-size:12px}.factors span{white-space:normal}.calculation-row p{margin-top:7px;color:var(--muted);font-size:11px}
.statistics{display:grid;gap:8px}.stat-card{display:grid;grid-template-columns:minmax(0,1fr) minmax(110px,auto);gap:7px 22px;border:1px solid #e2e8e1;border-radius:6px;padding:14px 16px;min-width:0;background:#fff}.stat-label{font-size:11px;color:var(--muted);margin-bottom:3px}.stat-description{font-size:13px;overflow-wrap:anywhere;line-height:1.5}.stat-value{font-size:20px;font-weight:600;line-height:1.3;color:var(--teal);text-align:right;overflow-wrap:anywhere;max-width:280px;font-variant-numeric:tabular-nums}.stat-value small{display:block;font-size:11px;font-weight:400;color:var(--muted);margin-top:5px}.stat-context{grid-column:1/-1;font-size:11px;color:var(--muted);overflow-wrap:anywhere}.stat-foot{grid-column:1/-1;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:7px 18px}.stat-foot .text-button{font-size:11px}.pill{font-size:10px;line-height:1.4;color:#526e5c;background:#edf3ed;border-radius:3px;padding:3px 6px;display:inline-block}.pill.review{background:#f4eddf;color:#7b6337}.pill.context{background:#eef0f4;color:#5e6c7b}.more{width:100%;min-height:44px;padding:12px;font-size:12px;color:var(--teal);background:#f0f5ee;border:1px solid var(--line);border-radius:6px;margin-top:8px}.empty{padding:30px 14px;text-align:center;font-size:13px;color:var(--muted)}.group-heading{font-size:13px;color:var(--muted);font-weight:650;margin:13px 2px 2px}.result-summary .stat-value{font-size:22px;flex:none;width:150px}.source-card>summary .sign-title strong{font-size:16px}.finding{margin:14px 0;border-top:1px solid var(--line);padding-top:12px;font-size:12px;overflow-wrap:anywhere}.finding h4{font-size:13px;margin-bottom:6px}.finding p{color:var(--muted);margin-top:7px}.sign-links{display:flex;gap:6px 16px;flex-wrap:wrap;margin-bottom:14px}
footer{max-width:1220px;margin:auto;padding:4px 28px 28px;display:flex;justify-content:space-between;gap:15px;font-size:11px;color:var(--muted)}footer a{color:var(--muted)}dialog{padding:0;width:min(800px,calc(100vw - 24px));max-height:90dvh;border:1px solid var(--line);border-radius:10px;color:var(--ink);background:white;overflow-x:hidden}dialog::backdrop{background:#102a2aae}.dialog-head{display:flex;align-items:start;gap:20px;justify-content:space-between;padding:20px 23px;border-bottom:1px solid var(--line);position:sticky;top:0;background:white;z-index:1}.dialog-head h2{font-size:23px;overflow-wrap:anywhere}.dialog-head button{border:1px solid var(--line);border-radius:4px;min-height:40px;padding:5px 10px;font-size:12px;flex:none}.dialog-body{padding:22px;font-size:13px;overflow-wrap:anywhere}.dialog-body h3{margin:23px 0 9px}.dialog-body h3:first-child{margin-top:0}.dialog-body p{margin:9px 0}.dialog-body ul{padding-left:20px}.dialog-body li{margin:7px 0}.dialog-body dl{display:grid;grid-template-columns:140px minmax(0,1fr);gap:12px;margin:18px 0}.dialog-body dt{color:var(--muted);font-size:12px}.dialog-body dd{margin:0}.dialog-value{font-size:28px;color:var(--teal)}
@media(max-width:850px){.sign-card>summary{flex-wrap:wrap;gap:12px}.sign-card>summary .sign-title{flex-basis:calc(100% - 45px)}.sign-card>summary:after{order:1;margin-left:auto}.sign-card>summary .weights{order:2;width:100%}.weight{flex:1;justify-content:space-between}.result-summary .stat-value{order:2;width:100%;text-align:left}.paper-head{display:block}.paper-head .weights{margin-top:10px}.toolbar{grid-template-columns:1fr 1fr}.toolbar>.field:first-child{grid-column:1/-1}.inside-controls .field{min-width:125px}}
@media(max-width:540px){.mast-inner{padding:10px 17px;gap:14px}.brand{font-size:14px;flex-shrink:0}.brand svg{width:24px;height:24px}.help-button{font-size:11px;max-width:140px;line-height:1.5}main{padding:22px 15px}.intro{display:block;margin-bottom:15px}h1{font-size:30px}.corpus{margin-top:8px;font-size:12px}.toolbar{padding:13px;gap:11px}input,select{font-size:16px}.toolbar label{font-size:10px}.dependent{flex-direction:column;gap:11px}.dependent .field{max-width:none}.sign-card>summary{padding:16px 14px;gap:11px}.sign-title strong{font-size:16px}.weights{gap:7px}.weight{font-size:10px;padding:6px 8px;gap:5px;min-width:0}.weight b{font-size:14px}.sign-body{padding:15px 12px}.inside-controls{gap:10px;margin-bottom:15px}.inside-controls .field{flex-basis:calc(50% - 10px);min-width:0}.inside-controls .field:last-of-type:nth-child(3){flex-basis:100%}.inside-controls select{font-size:14px}.filter-row{display:block}.filter-row .field{margin-top:10px}.context-grid{grid-template-columns:1fr;gap:8px}.paper{margin-top:18px;padding-top:18px}.stat-card{padding:12px;grid-template-columns:minmax(0,1fr);gap:6px}.stat-value{grid-row:1;text-align:left;max-width:none;font-size:22px}.stat-value small{font-size:11px;margin-top:3px}.stat-description{font-size:13px}.stat-label{font-size:10px}.stat-context{font-size:11px}.stat-foot{align-items:start}.paper-title h3{font-size:16px}.paper-title p{font-size:11px}.paper .weight{font-size:10px}.paper-tools{gap:12px}.dialog-head{padding:15px;gap:12px}.dialog-head h2{font-size:21px}.dialog-body{padding:17px}.dialog-body dl{grid-template-columns:1fr;gap:3px}.dialog-body dd{margin-bottom:10px}footer{padding:4px 16px 24px;font-size:10px}.source-card>summary .sign-title strong{font-size:15px}}
@media(prefers-reduced-motion:no-preference){.sign-card{transition:border-color .15s}.sign-card>summary:hover{background:#f4f8f2}}
.inside-controls{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr) auto}.inside-controls .field{min-width:0}.inside-controls .field:nth-of-type(3){grid-column:1/-1}.inside-controls .filter-button{grid-column:3;grid-row:1;padding:0 2px}.filter-row .field select{font-size:14px}
.sign-card:not([open])>summary .sign-title strong{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}

.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap}.active-filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}.filter-chip{font-size:12px;padding:6px 9px;background:#eaf2ed;border-radius:5px}.dictionary-controls{grid-template-columns:minmax(0,1fr) minmax(0,1fr);margin-bottom:18px}.shared-context{font-size:12px;color:var(--muted);margin:10px 0 18px;overflow-wrap:anywhere}.source-result{margin:16px 0 20px}.source-result>h4{font-size:13px;font-weight:600;margin-bottom:9px;overflow-wrap:anywhere}.result-table,.weight-table{border-collapse:collapse;table-layout:fixed;width:100%;font-size:12px}.result-table th,.result-table td,.weight-table th,.weight-table td{border-bottom:1px solid var(--line);padding:10px 9px;text-align:left;vertical-align:top;overflow-wrap:anywhere}.result-table th,.weight-table th{color:var(--muted);font-size:11px;font-weight:600;background:#f4f7f2}.result-table th:nth-child(1){width:31%}.result-table th:nth-child(2){width:33%}.result-table th:nth-child(3){width:22%}.result-table th:nth-child(4){width:14%}.result-table small{display:block;color:var(--muted);font-size:11px;margin-top:4px;font-weight:400}.result-number{font-weight:650;color:var(--teal);font-variant-numeric:tabular-nums}.result-role{margin-top:7px}.paper-weights{margin:17px 0}.paper-weights>h4{font-size:12px;margin-bottom:7px}.weight-table th:first-child{width:62%}.weight-table th:nth-child(n+2),.weight-table td:nth-child(n+2){text-align:right;font-variant-numeric:tabular-nums}.weight-table th button{font-size:11px;padding:0;text-align:right}.calculation-line{font-size:11px;margin:12px 0;color:var(--muted);overflow-wrap:anywhere}.additional-results{margin:24px 0;font-size:12px;color:var(--muted)}.additional-results summary{cursor:pointer;color:var(--teal);padding:12px 0}.additional-papers{display:grid;gap:8px}.additional-papers button{border-top:1px solid var(--line);padding:10px 0}.paper{margin-top:26px;padding-top:22px}.paper:first-of-type{margin-top:0}
@media(max-width:540px){.result-table,.result-table tbody{display:block}.result-table thead{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}.result-table tr{display:grid;grid-template-columns:minmax(0,1fr);padding:11px 0;border-top:1px solid var(--line)}.result-table td{display:block;width:auto!important;border:0;padding:4px 0;font-size:12px}.result-table td::before{content:attr(data-label);display:block;color:var(--muted);font-size:10px;font-weight:400;margin-bottom:3px}.result-table td:nth-child(3){grid-row:1;font-size:20px}.result-table td:nth-child(4){padding-top:0}.result-table td:nth-child(4) button{min-height:34px}.weight-table{font-size:11px}.weight-table th,.weight-table td{padding:8px 4px}.weight-table th:first-child{width:52%}.weight-table th button{font-size:9px}.shared-context{font-size:11px}.source-result>h4{font-size:12px}.dictionary-controls select{font-size:14px}.paper{margin-top:23px}.paper-title h3{font-size:16px}}
.toolbar{grid-template-columns:minmax(210px,1.4fr) minmax(150px,1fr) minmax(180px,1fr) minmax(140px,.8fr)}.dictionary-controls{grid-template-columns:repeat(3,minmax(0,1fr))}.dictionary-controls .field:nth-of-type(3){grid-column:auto}.evidence-class-label{display:inline-block;color:var(--teal);font-size:11px;font-weight:600}.weight-table td small{display:block;color:var(--muted);font-size:10px;font-weight:400;margin-top:3px}
@media(max-width:850px){.toolbar{grid-template-columns:1fr 1fr}#evidence-class-field{grid-column:1/-1}}
@media(max-width:540px){.dictionary-controls{grid-template-columns:1fr 1fr}.dictionary-controls .field:nth-of-type(3){grid-column:1/-1}}
.source-scope{font-size:11px;color:var(--teal);font-weight:600;margin:0 0 8px}
.paper-anatomy{margin:14px 0 20px}.anatomy-result{margin:12px 0;font-size:12px;overflow-wrap:anywhere}.anatomy-result h4{font-size:13px;margin-bottom:5px}.source-detail{margin:7px 0}.source-detail p{margin-top:4px;color:var(--muted)}.source-detail small{display:block;margin-top:4px}.source-detail blockquote{margin:7px 0;padding-left:10px;border-left:2px solid var(--line);color:var(--muted)}
.region-card{border:1px solid var(--line);border-radius:8px;background:white;min-width:0}.region-card>summary,.paper>summary{display:flex;align-items:center;gap:12px;list-style:none;padding:13px 16px}.region-card>summary{background:var(--pale);border-radius:8px;font-size:16px}.region-card>summary span{font-size:12px;color:var(--muted);margin-left:auto}.region-card>summary::-webkit-details-marker,.paper>summary::-webkit-details-marker{display:none}.region-card>summary:after,.paper>summary:after{content:'+';color:var(--teal);font-size:22px;margin-left:auto}.region-card[open]>summary:after,.paper[open]>summary:after{content:'−'}.region-body{display:grid;gap:8px;padding:10px}.paper,.paper:first-child{border:1px solid var(--line);border-radius:6px;padding:0;margin:10px 0 0}.paper>summary{background:#f5f8f4}.paper>summary .paper-tools{margin:7px 0 0;gap:10px}.paper-content{padding:12px 14px;max-height:min(68dvh,44rem);overflow:auto;overscroll-behavior:contain;scrollbar-gutter:stable;border-top:1px solid var(--line);font-size:12px}.paper-content> a{display:inline-block;margin-bottom:8px}.compact-anatomy{display:grid;gap:9px;padding:8px 0}.anatomy-subject{min-width:0;overflow-wrap:anywhere}.compact-anatomy h4{margin:0 0 2px;font-size:inherit}.compact-anatomy dl,.compact-anatomy dd{margin:0}.anatomy-axis{display:flex;flex-wrap:wrap;gap:0 5px}.anatomy-axis dt{color:var(--muted)}.anatomy-axis dd>span{display:block}.anatomy-qualifier{color:var(--muted)}.paper-content .shared-context{margin:8px 0}.paper-content .context-details{margin:8px 0 0}.paper-content .result-table{margin-top:10px}.paper-content .result-table th{position:sticky;top:0;background:#f1f5ee;z-index:1}.result-table td>strong{display:block}.paper-content .paper-weights{margin:8px 0}.paper-content .calculation-line{margin:10px 0}.paper-content .source-detail{margin:8px 0}.paper-content .source-detail small{display:block}.paper-content .source-detail blockquote{margin:5px 0;padding-left:10px;border-left:2px solid var(--line)}.paper-content .anatomy-result{margin:10px 0}.paper-content .result-table td,.paper-content .weight-table td{padding-top:9px;padding-bottom:9px}
@media(max-width:540px){.region-body{padding:6px}.region-card>summary{padding:13px 12px}.paper>summary{padding:11px 10px}.paper-content{padding:10px;max-height:65dvh;scrollbar-gutter:auto}.compact-anatomy{gap:8px}.paper-content .result-table th{position:static}.paper-title p{font-size:12px}}


.paper-links{display:flex;align-items:center;flex-wrap:wrap;gap:4px 16px;margin-bottom:8px}.paper-links .map-link{margin:0}
.embedded-help{display:none}:host([data-embedded]){--ink:#1a1d2e;--muted:#667085;--teal:#0a7a8a;--pale:#edf4f9;--line:#e3e8f0;--canvas:#fff;--serif:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;font:14px/1.5 Inter,ui-sans-serif,system-ui,sans-serif;background:transparent;display:block;min-width:0}:host([data-embedded]) .owner-only,:host([data-embedded]) .intro h1{display:none}:host([data-embedded]) .embedded-help{display:block}:host([data-embedded]) main{max-width:none;margin:0;padding:0}:host([data-embedded]) .intro{margin-bottom:10px}:host([data-embedded]) .intro-actions{display:flex;justify-content:space-between;align-items:center;gap:12px;width:100%}:host([data-embedded]) .toolbar{grid-template-columns:repeat(3,minmax(0,1fr));padding:12px;gap:10px}:host([data-embedded]) .sign-card>summary{padding:12px 14px}:host([data-embedded]) .sign-title strong{font-size:15px}:host([data-embedded]) .sign-body{padding:12px}:host([data-embedded]) #reset{display:none}@media(max-width:650px){:host([data-embedded]) .toolbar{grid-template-columns:1fr 1fr}:host([data-embedded]) #evidence-class-field{grid-column:1/-1}}`;

const markup = `
<a class="skip" href="#main">Skip to signs</a>
<header class="masthead owner-only"><div class="mast-inner"><div class="brand"><svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><rect width="32" height="32" rx="9" fill="#176862"/><path d="M8 16h4l3-7 3 14 3-7h3" stroke="white" stroke-width="1.8" stroke-linejoin="round"/></svg>Semiology Atlas</div><button class="help-button" id="help">Weights & statistics explained</button></div></header>
<main id="main"><div class="intro"><h1>Signs & evidence</h1><div class="intro-actions"><div class="corpus" id="corpus">Loading evidence…</div><button class="help-button embedded-help" data-evidence-help>Weights & statistics explained</button></div></div>
<div class="toolbar" aria-label="Organize signs and evidence"><div class="field"><label id="search-label" for="search">Search</label><input id="search" type="search" placeholder="Sign or source wording" autocomplete="off"></div><div class="field"><label for="organize">Organize by</label><select id="organize"><option value="az">A–Z</option><option value="region">Region</option><option value="ilae">ILAE</option><option value="luders">Lüders</option><option value="source">Source paper</option></select></div><div class="field"><label id="order-label" for="order">Order signs by</label><select id="order"></select></div><div class="field" id="evidence-class-field"><label for="evidence-class">Evidence class</label><select id="evidence-class"></select></div><div class="dependent" id="dependent" hidden><div class="field" id="group-field" hidden><label id="group-label" for="group">Group</label><select id="group"></select></div><div class="field" id="metric-field" hidden><label for="metric">Metric</label><select id="metric"></select></div></div></div>
<div class="list-meta"><span id="match-count" aria-live="polite">Loading signs…</span><button id="reset">Reset</button></div><div class="active-filters" id="active-filters"></div><section class="sign-list" id="sign-list" aria-label="Signs and evidence"><div class="empty">Loading evidence…</div></section><section id="additional-results" class="additional-results" hidden></section>
</main>
<footer class="owner-only"><span>Owner preview</span><a href="https://www.semiologyatlas.org/" target="_blank" rel="noopener">Public atlas ↗</a></footer>
<dialog id="record-dialog" aria-labelledby="dialog-title"><div class="dialog-head"><h2 id="dialog-title"></h2><button id="close-dialog" aria-label="Close details">Close</button></div><div class="dialog-body" id="dialog-body"></div></dialog>
<template id="scientific-explanation"><h3>Dictionary terms and source wording</h3><p>Clinical terms follow the selected ILAE or Lüders dictionary and its approved relationships. Category filters restrict the displayed terms to that dictionary branch. Changing dictionaries clears the previous category; region and evidence-class filters remain. Author-specific wording remains attached to each paper result. Grouping terms does not merge sign identities or imply that their statistical results are comparable.</p><p>Search includes the terms used in the papers. Opening a dictionary term collects its linked paper results. Additional paper results retain source records without a usable clinical dictionary relationship in the selected scheme.</p><h3>Reported statistics</h3><p>Statistic selectors list statistical and quantitative measures. Clinical features, sequence descriptions, and other paper-specific fields remain in the paper results under All statistics.</p><p>Each reported value retains its source, measured phenomenon, population, subgroup, analysis unit, denominator, comparator, and uncertainty. Shared context is displayed once per paper; differences remain in the result rows. Numerical ordering uses the recorded metric and unit and does not convert percentages and proportions. Missing numeric fields follow numeric values.</p><h3>Evidence class</h3><p>Evidence-class filters select existing assignments for the displayed sign and source results. A result matches when the selected class is recorded for localization or lateralization. Unclassified includes records marked unclassified and records without a class assignment. The sign list shows terms with matching evidence; it does not assign a class to the sign itself.</p><p>Paper ordering lists Class I, II, and III in that sequence, followed by unclassified evidence. Where a paper has several recorded classes, its lowest numbered class determines its position and all classes remain displayed. This ordering does not calculate a new evidence score.</p><h3>Paper weights</h3><p>Each appraisal retains its original sign, paper, findings, and statistics. The table shows that stored appraisal once. A changed or narrower sign grouping can reference the appraisal without receiving a separate numerical contribution. Appraisals are not summed into a dictionary-level score.</p><p><strong>Appraised weight = class base × method factor × size factor.</strong> The applied contribution also depends on the recorded eligibility and scope. The class bases are 3, 2, or 1; an unclassified source can have a base of 0. Method factors are 1.5 for SEEG or postoperative evidence, 1.35 for other intracranial evidence, 1.2 for video, 1.15 for imaging, 1.1 for scalp EEG, 1 for review evidence, and 0.9 when the method is absent.</p><p>The size factor is min(2, 1 + log₁₀(N)/2). Missing N gives a factor of 1, and the class-I calculation does not use sample size. The selected N is unavailable here. A dash indicates that an appraisal is unavailable for that axis. A zero produced by an unresolved evidence class is unavailable, not a numerical assessment of the evidence. Calculation details retain the recorded factors and explain contribution eligibility and scope. An applied contribution of 0 indicates exclusion from the primary-evidence total; an unassigned contribution has not been established for the displayed scope. Approximate equality reflects rounded recorded factors.</p><h3>Combined estimates</h3><p>A pooled estimate requires a defined clinical question, compatible measures, appropriate uncertainty, and assessment of overlapping cohorts. Several results from one paper do not represent independent studies. The existing paper weights do not pool reported statistics or provide a validated clinical prediction score.</p></template>
`;

/** Render the shared evidence inside a site-owned host without fetching or remapping data. */
export function createEvidenceReview(host, options) {
  host.replaceChildren();
  const root=host.shadowRoot || host.attachShadow({mode:'open'});
  host.toggleAttribute('data-embedded',Boolean(options.embedded ?? options.onShowMap));
  options={...options,embedded:options.embedded ?? Boolean(options.onShowMap)};
  root.innerHTML='<style>'+styles+'</style>'+markup;

let {data, catalogue} = options; let sources;
const publicSite = Boolean(options.onShowMap);
const $ = id => root.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const clean = value => value == null || /^(NONE|NULL|NOT_REPORTED|NOT_APPLICABLE|UNKNOWN|\[\]|\{\})$/i.test(String(value).trim()) ? '' : String(value).trim();
const uniq = values => [...new Set(values)];
const number = value => Number(value).toLocaleString('en-US');
const parse = value => { try { return typeof value === 'string' ? JSON.parse(value) : value; } catch { return null; } };
const words = value => clean(value).toLowerCase().replace(/_/g,' ').replace(/^./, char => char.toUpperCase());
const metricNames = atlasMetricLabels;
const metricName = value => metricNames[value] || words(value) || 'Other reported statistic';
const metricTypesFor = atlasMetricTypes;
const sectionNames = {study:'Original study',review:'Review or guidance',background:'Cited or contextual',other:'Other evidence'};
const roleNames = {PRIMARY_RESULT:'Original study result',CASE_OBSERVATION:'Case observation',REVIEW_SYNTHESIS:'Review synthesis',GUIDELINE_RECOMMENDATION:'Guideline recommendation',CITED_STUDY_RESTATEMENT:'Cited study result',PRIMARY_RESULT_SAME_SOURCE_RESTATEMENT:'Repeated result from the same source',EDUCATIONAL_STATEMENT:'Educational statement',METHOD_OR_DEFINITION:'Method or definition',SOURCE_CONTEXT:'Source context',COHORT_CONTEXT:'Study population',SOURCE_REPORTED_TARGET:'Reported relationship',SOURCE_REPORTED:'Reported relationship',STIMULATION:'Stimulation context'};
const roleName = value => roleNames[value] || words(value);
function bibliography(id) { return sources.get(id)?.bibliography || {}; }
function citation(id) {
  const source = sources.get(id), bib = bibliography(id), authors = parse(bib.authors_json) || [];
  const first = typeof authors[0] === 'string' ? authors[0] : authors[0]?.family_name || authors[0]?.display_name;
  return first ? `${first}${authors.length > 1 ? ' et al.' : ''}${bib.publication_year ? ', ' + bib.publication_year : ''}` : clean(bib.citation_text) || source?.label || 'Source document';
}
function paperCount(rows) { return new Set(rows.map(row => row.source.id)).size; }
function rowKinds(row) { return uniq((row.facets.evidence || []).map(value => atlasEvidenceSection(value.id))); }
function sourceTitle(id) { return sources.get(id)?.label || data.rows.find(row => row.source.id === id)?.source.title || 'Source document'; }
function rolePill(role) { const section = atlasEvidenceSection(role); return `<span class="pill ${section === 'review' ? 'review' : ['background','other'].includes(section) ? 'context' : ''}">${esc(roleName(role))}</span>`; }
function uncertainty(stat) {
  const scalar = value => value && typeof value === 'object' ? clean(value.value) : clean(value);
  const labels = {confidence_interval:'Confidence interval',ci:'Confidence interval',p_value:'P value',p:'P value',standard_error:'Standard error',standard_deviation:'Standard deviation',sd:'Standard deviation',range:'Range',interquartile_range:'Interquartile range',test_statistic:'Test statistic',other:'Other uncertainty'};
  const display = raw => {
    if (!clean(raw)) return [];
    const value = typeof raw === 'string' && /^[\[{]/.test(raw.trim()) ? parse(raw) : raw;
    if (value == null) return [];
    if (typeof value !== 'object') return [String(value)];
    if (Array.isArray(value)) return value.flatMap(display);
    if (clean(value.value_text)) return [value.value_text];
    const lower = scalar(value.lower ?? value.lower_bound ?? value.ci_lower), upper = scalar(value.upper ?? value.upper_bound ?? value.ci_upper);
    if (lower && upper) return [[scalar(value.level ?? value.confidence_level) && `${scalar(value.level ?? value.confidence_level)}%`,words(value.type || value.kind) || 'Reported interval',`${lower}–${upper}`].filter(Boolean).join(' ')];
    return Object.entries(labels).flatMap(([key,label]) => display(value[key]).map(text => `${label}: ${text}`));
  };
  return uniq([stat.uncertainty,stat.uncertainty_json].flatMap(display)).join('; ');
}
function locator(value) {
  const parsed = parse(value);
  if (!Array.isArray(parsed)) return clean(value);
  return uniq(parsed.map(item => [item.page != null ? `p. ${item.page}` : '',clean(item.object),clean(item.position)].filter(Boolean).join(', '))).filter(Boolean).join('; ');
}


  const params = new URLSearchParams(options.embedded ? '' : location.search);
  const state = {query:params.get('q') || '',sourceQuery:'',organize:'az',scheme:'luders',filters:{},order:'name',metric:'',limit:30,focus:'',openRegions:new Set(),regionLimits:new Map()};
  const opened = new Set(), detailState = new Map(), weightIndex = new Map();
  let evidenceMap = publicSite ? {showEvidence: options.onShowMap, clear: () => options.onClearFilters?.()} : null, mapResultIds = null, dialogRows = [], additionalPaperRows = new Map();
  let currentView = '', signOrganization = 'az', signOrder = 'name', pendingFocus = '', selectedAnatomy = new Set();
  let groups = [], unplaced = [], entries = [], nodeIndex, nativeSigns, statOwners, metricTypes = [];
  let sections = new Map(), sectionRoots = [];
  const categoryKinds = new Set(['CATEGORY','DESCRIPTOR_CATEGORY','BASIC_DESCRIPTOR','PUBLIC_FAMILY','WORKSHEET_CATEGORY','EVENT_CATEGORY']);
  const axes = ['LOCALIZATION','LATERALIZATION'];
  const axisName = axis => axis === 'LOCALIZATION' ? 'Localization' : 'Lateralization';
  const option = (id,label) => `<option value="${esc(id)}">${esc(label)}</option>`;
  const paperIds = rows => uniq(rows.map(row => row.source.id));
  const statisticsFor = rows => uniq(rows.flatMap(row => row.statistic_ids)).map(id => data.statistics[id]).filter(Boolean);
  const nativeIds = rows => uniq(rows.flatMap(row => row.facets.sign || []).map(item => item.id));
  const evidenceClassOrder = ['I','II','III','UNCLASSIFIED'];
  const classLabel = id => id === 'UNCLASSIFIED' ? 'Unclassified' : 'Class '+id;
  const classesFor = rows => uniq(rows.flatMap(row => row.facets.evidence_class?.length ? row.facets.evidence_class.map(item => item.id) : ['UNCLASSIFIED'])).sort((a,b) => evidenceClassOrder.indexOf(a)-evidenceClassOrder.indexOf(b) || a.localeCompare(b));
  const classMatches = (row,id) => !id || classesFor([row]).includes(id);
  const classOptions = ids => option('','All classes') + evidenceClassOrder.filter(id => ids.includes(id)).map(id => option(id,classLabel(id))).join('');
  const classRank = rows => Math.min(...classesFor(rows).map(id => { const rank=evidenceClassOrder.indexOf(id); return rank<0 ? Infinity : rank; }));
  const ownersFor = (stat,rows) => { const selected = new Set(rows.map(row => row.id)); return (statOwners.get(stat.statistic_id) || []).filter(row => selected.has(row.id)); };
  const selectedRows = rows => rows.filter(row => (!mapResultIds || mapResultIds.has(row.id)) && Object.entries(state.filters).every(([facet,id]) => state.organize === 'source' && ['ilae','luders'].includes(facet) || (facet === 'evidence_class' ? classMatches(row,id) : !id || (row.facets[facet] || []).some(item => item.id === id))) && (state.organize === 'source' || !state.order.startsWith('values-') || !state.metric || row.statistic_ids.some(id => data.statistics[id]?.metric_type === state.metric)));
  const queryMatch = value => String(value || '').toLocaleLowerCase().includes(state.query.trim().toLocaleLowerCase());
  const valueText = stat => clean(stat.value_text) || String(stat.numeric_value ?? 'Not reported');
  function grouping() {
    ({groups,unplaced} = atlasDictionaryGroups(data.rows.filter(row => row.record_kind === 'SIGN_EVIDENCE'),state.scheme,catalogue.items));
    unplaced = [...unplaced,...data.rows.filter(row => row.record_kind !== 'SIGN_EVIDENCE')];
  }
  function updateQuery() { if(options.embedded)return; const url = new URL(location.href); state.query ? url.searchParams.set('q',state.query) : url.searchParams.delete('q'); history.replaceState(null,'',url); }
  function syncControls() {
    const sourceMode = state.organize === 'source', classified = ['ilae','luders'].includes(state.organize);
    $('organize').value = state.organize;
    const sourceCount=atlasCounts(data.rows).sources;
    $('corpus').innerHTML = sourceMode ? `${number(sourceCount)} ${sourceCount===1?'publication':'publications'}` : `${number(groups.length)} ${state.scheme === 'ilae' ? 'ILAE' : 'Lüders'} terms · <button id="all-sources">${number(sourceCount)} sources</button>`;
    $('order-label').textContent = sourceMode ? 'Order papers by' : classified ? 'Within classifications' : state.organize==='region' ? 'Within regions' : 'Order signs by';
    const sorts = sourceMode ? [['name','Author A–Z'],['title','Title A–Z'],['year','Publication year: newest first']] : [...(classified ? [['region','Region']] : []),['name','A–Z'],['papers','Number of publications'],['values-high','Reported statistics: high to low'],['values-low','Reported statistics: low to high']];
    if (!sorts.some(([id]) => id === state.order)) state.order = 'name';
    $('order').innerHTML = sorts.map(([id,label]) => option(id,label)).join(''); $('order').value = state.order;
    $('evidence-class').innerHTML = classOptions(classesFor(data.rows)); $('evidence-class').value = state.filters.evidence_class || '';
    const facet = ['region','ilae','luders'].includes(state.organize) ? state.organize : '';
    $('group-field').hidden = !facet;
    if (facet) {
      const labels = {region:'Region',ilae:'ILAE category',luders:'Lüders category'};
      const choices = catalogue.items.filter(item => item.facet === facet && item.linked_count && (facet === 'region' || categoryKinds.has(item.kind))).sort((a,b) => (a.ordinal ?? Infinity)-(b.ordinal ?? Infinity) || a.label.localeCompare(b.label));
      $('group-label').textContent = labels[facet]; $('group').innerHTML = option('','All '+(facet === 'region' ? 'regions' : 'categories')) + choices.map(item => option(item.id,item.label)).join(''); $('group').value = state.filters[facet] || '';
    }
    const values = state.order.startsWith('values-') && state.organize !== 'source';
    $('metric-field').hidden = !values; $('dependent').hidden = !facet && !values;
    if (values) { $('metric').innerHTML = option('','All statistics') + metricTypes.map(type => option(type,metricName(type))).join(''); $('metric').value = state.metric; }
    $('active-filters').innerHTML = Object.entries(state.filters).filter(([facet,id]) => id && facet !== 'evidence_class' && !(sourceMode && ['ilae','luders'].includes(facet))).map(([facet,id]) => `<button class="filter-chip" data-clear-filter="${esc(facet)}">${esc(nodeIndex.get(id)?.label || facet)} ×</button>`).join('');
    $('search').closest('.field').hidden = options.embedded && !sourceMode;
    $('search-label').textContent = sourceMode ? 'Search papers' : 'Search';
    $('search').placeholder = sourceMode ? 'Title, author or citation' : 'Sign or source wording';
    $('search').value = sourceMode ? state.sourceQuery : state.query;
    if (mapResultIds && !options.embedded) $('active-filters').insertAdjacentHTML('beforeend','<button class="filter-chip" data-clear-map>Map selection ×</button>');

  }
  function settings(id) { if (!detailState.has(id)) detailState.set(id,{sort:'name',metric:'',evidenceClass:'',papers:6,weights:'LOCALIZATION',openPapers:new Set()}); return detailState.get(id); }
  function evidenceStats(rows,setting) {
    const selectedMetric = setting.metric || (state.order.startsWith('values-') ? state.metric : '');
    const stats = statisticsFor(rows).filter(stat => !selectedMetric || stat.metric_type === selectedMetric);
    return stats.sort((a,b) => {
      const group = metricName(a.metric_type).localeCompare(metricName(b.metric_type)) || clean(a.unit).localeCompare(clean(b.unit));
      if (group || !state.order.startsWith('values-') || !clean(a.unit)) return group || a.statistic_id.localeCompare(b.statistic_id);
      const av = typeof a.numeric_value === 'number' && Number.isFinite(a.numeric_value) ? a.numeric_value : null;
      const bv = typeof b.numeric_value === 'number' && Number.isFinite(b.numeric_value) ? b.numeric_value : null;
      return (av == null)-(bv == null) || (state.order === 'values-low' ? 1 : -1)*((av ?? 0)-(bv ?? 0)) || a.statistic_id.localeCompare(b.statistic_id);
    });
  }
  function sourceMatches(id) {
    const query=state.sourceQuery.trim().toLocaleLowerCase();
    if(!query)return true;
    const bib=bibliography(id),authors=parse(bib.authors_json)||[];
    const names=authors.map(author=>typeof author==='string'?author:Object.values(author||{}).filter(value=>typeof value==='string').join(' ')).join(' ');
    return [sourceTitle(id),bib.title,bib.citation_text,names].some(value=>String(value||'').toLocaleLowerCase().includes(query));
  }
  function organizeEntries(selected) {
    const classified=['ilae','luders'].includes(state.organize),regional=state.organize==='region'||classified&&state.order==='region';
    const ordered=catalogue.maps?.region_groups||[], result=[];
    for(const group of selected) {
      const banners=[],seen=new Set();
      if(classified)for(let item=group.dictionary;item;item=nodeIndex.get(item.parent_id)) {
        if(seen.has(item.id))throw new Error('Cyclic classification dictionary');
        seen.add(item.id);if(categoryKinds.has(item.kind))banners.unshift(item);
      }
      const regions=regional?atlasGroups(group.rows,'region'):[null];
      for(const region of regions) {
        const path=[...banners];
        if(region) {
          const ordinal=ordered.findIndex(item=>item.id===region.id||item.anatomy_node_id===region.id);
          path.push({id:region.id||'unlinked',label:region.id?region.label:'No linked region',ordinal:ordinal<0?Infinity:ordinal});
        }
        result.push({type:'sign',group:region?{...group,rows:region.rows}:group,banners:path,key:JSON.stringify([...path.map(item=>item.id),group.id])});
      }
    }
    return result.sort((a,b)=>{
      for(let index=0;index<Math.max(a.banners.length,b.banners.length);index++) {
        const left=a.banners[index],right=b.banners[index];
        if(!left||!right)return Boolean(left)-Boolean(right);
        if(left.id!==right.id)return (left.ordinal??Infinity)-(right.ordinal??Infinity)||left.label.localeCompare(right.label)||left.id.localeCompare(right.id);
      }
      return (state.order==='papers'?paperIds(b.group.rows).length-paperIds(a.group.rows).length:0)||(state.query.trim()?Number(queryMatch(b.group.label))-Number(queryMatch(a.group.label)):0)||a.group.label.localeCompare(b.group.label);
    });
  }
  function sectionMarkup(section) {
    const count=new Set(section.indices.map(index=>entries[index].group.id)).size;
    return `<details class="region-card" data-region="${esc(section.key)}" ${state.openRegions.has(section.key)?'open':''}><summary><strong>${esc(section.label)}</strong><span>${count} ${count===1?'term':'terms'}</span></summary><div class="region-body"></div></details>`;
  }
  function renderList() {
    entries = [];
    if (state.organize === 'source') {
      entries = atlasGroups(selectedRows(data.rows),'source').filter(group => sourceMatches(group.id)).sort((a,b) => (state.order === 'year' ? (Number(bibliography(b.id).publication_year)||0)-(Number(bibliography(a.id).publication_year)||0) : state.order==='title'?sourceTitle(a.id).localeCompare(sourceTitle(b.id)):0) || citation(a.id).localeCompare(citation(b.id))).map(group => ({type:'source',group,key:'source:'+group.id}));
    } else {
      const categoryId=state.filters[state.scheme],categoryGroups=categoryId ? atlasDictionaryGroups(data.rows.filter(row=>row.record_kind==='SIGN_EVIDENCE'),state.scheme,catalogue.items,categoryId).groups : groups;
      let selected = categoryGroups.map(group => ({...group,rows:selectedRows(group.rows).filter(row => !state.query.trim() || queryMatch(group.label) || queryMatch(row.term) || queryMatch(row.sign_label))})).filter(group => group.rows.length && (!state.focus || group.id === state.focus) && (!state.order.startsWith('values-') || !state.metric || statisticsFor(group.rows).some(stat => stat.metric_type === state.metric)));
      entries=organizeEntries(selected);
    }
    const rowSet = [...new Map(entries.flatMap(entry => entry.group.rows).map(row => [row.id,row])).values()];
    const termCount = new Set(entries.map(entry => entry.group.id)).size;
    $('corpus').hidden = state.organize === 'source' && entries.length === atlasCounts(data.rows).sources;
    $('match-count').textContent = state.organize === 'source' ? `${number(entries.length)} ${entries.length === 1 ? 'publication' : 'publications'}` : `${number(termCount)} dictionary ${termCount === 1 ? 'term' : 'terms'} · ${number(paperIds(rowSet).length)} ${paperIds(rowSet).length === 1 ? 'paper' : 'papers'}`;
    sections=new Map();sectionRoots=[];
    entries.forEach((entry,index)=>{
      const path=[];let parent=null;
      for(const banner of entry.banners||[]) {
        path.push(banner.id);const key=JSON.stringify(path);
        if(!sections.has(key)){const section={key,label:banner.label,indices:[],direct:[],children:[]};sections.set(key,section);(parent?parent.children:sectionRoots).push(section);}
        parent=sections.get(key);parent.indices.push(index);
      }
      if(parent)parent.direct.push(index);
    });
    const ungrouped=entries.map((entry,index)=>({entry,index})).filter(({entry})=>!entry.banners?.length);
    $('sign-list').innerHTML = (sectionRoots.map(sectionMarkup).join('')+ungrouped.slice(0,state.limit).map(({entry,index})=>entryMarkup(entry,index)).join('')) || `<div class="empty">${state.organize==='source'?'No papers match this selection.':'No dictionary terms match this selection.'}</div>`;
    root.querySelectorAll('.region-card[open]').forEach(renderRegion);
    if (ungrouped.length > state.limit) $('sign-list').insertAdjacentHTML('beforeend',`<button class="more" id="more-signs">Show remaining ${state.organize==='source'?'papers':'terms'} (${number(ungrouped.length-state.limit)})</button>`);
    root.querySelectorAll('.sign-card[open]').forEach(renderEntry);
    const extra = state.organize === 'source' ? [] : selectedRows(unplaced).filter(row => !state.query.trim() || queryMatch(row.term));
    evidenceMap?.update?.([...new Map([...rowSet,...extra].map(row=>[row.id,row])).values()]);
    const paperGroups = atlasGroups(extra,'source');
    additionalPaperRows = new Map(paperGroups.map(group=>[group.id,group.rows]));
    $('additional-results').hidden = !paperGroups.length;
    if (!entries.length && paperGroups.length) {
      $('sign-list').innerHTML = '';
      $('match-count').textContent = `${number(paperGroups.length)} ${paperGroups.length === 1 ? 'source' : 'sources'} · ${number(evidenceStats(extra,{metric:''}).length)} reported values`;
      $('additional-results').innerHTML = paperGroups.map(group => paperMarkup(group.id,group.rows,evidenceStats(group.rows,settings(group.id)),settings(group.id),group.id)).join('');
    } else $('additional-results').innerHTML = paperGroups.length ? `<details><summary>Additional paper results · ${paperGroups.length} ${paperGroups.length === 1 ? 'source' : 'sources'}</summary><div class="additional-papers">${paperGroups.map(group => `<button class="text-button" data-source="${esc(group.id)}">${esc(citation(group.id))} · ${esc(group.label)}</button>`).join('')}</div></details>` : '';
  }
  function entryMarkup(entry,index) {
    const papers=paperIds(entry.group.rows).length;
    return `<details class="sign-card" data-entry="${index}" ${opened.has(entry.key)?'open':''}><summary><div class="sign-title"><strong>${esc(entry.type==='source'?sourceTitle(entry.group.id):entry.group.label)}</strong><span class="sign-meta">${entry.type==='source'?esc(citation(entry.group.id)):`${papers} ${papers===1?'paper':'papers'}`}</span></div></summary><div class="sign-body"></div></details>`;
  }
  function renderRegion(card) {
    if(!card.open)return;
    const id=card.dataset.region,limit=state.regionLimits.get(id)||30;
    const section=sections.get(id);if(!section||card.dataset.limit===String(limit))return;
    card.querySelector('.region-body').innerHTML=section.children.map(sectionMarkup).join('')+section.direct.slice(0,limit).map(index=>entryMarkup(entries[index],index)).join('')+(section.direct.length>limit?`<button class="more" data-more-region="${esc(id)}">Show remaining terms (${section.direct.length-limit})</button>`:'');
    card.dataset.limit=String(limit);card.querySelectorAll('.region-card[open]').forEach(renderRegion);card.querySelectorAll('.sign-card[open]').forEach(renderEntry);
  }
  function contexts(stat) {
    const metadata = value => clean(value).split(';').map(part => clean(part)).filter(Boolean).join('; ');
    const denominator = clean(stat.denominator) || (stat.denominator_value != null ? String(stat.denominator_value) : '');
    return [['Population',metadata(stat.population)],['Subgroup',metadata(stat.subgroup)],['Analysis unit',metadata(stat.analysis_unit)],['Denominator',denominator],['Timepoint',metadata(stat.timepoint)],['Endpoint',metadata(stat.endpoint)],['Comparator',metadata(stat.comparator)]];
  }
  function resultsMarkup(stats,rows) {
    if (!stats.length) return '';
    stats=atlasStatisticGroups(stats).map(group=>group.statistic);
    const shared = new Map(contexts(stats[0]).filter(([key,value]) => value && stats.every(stat => new Map(contexts(stat)).get(key) === value)));
    return `${shared.size ? `<p class="shared-context">${[...shared].map(([key,value]) => `${esc(key)}: ${esc(value)}`).join(' · ')}</p>` : ''}<table class="result-table"><thead><tr><th>Finding / statistic</th><th>Study context</th><th>Value</th><th><span class="sr-only">Source details</span></th></tr></thead><tbody>${stats.map(stat => {
      const terms=uniq(ownersFor(stat,rows).map(row=>row.term));
      const measure = clean(stat.measure), label = metricName(stat.metric_type);
      const description = measure && measure.toLocaleLowerCase() !== label.toLocaleLowerCase() && measure !== clean(stat.value_text) ? `<small>${esc(measure)}</small>` : '';
      const context = contexts(stat).filter(([key,value]) => value && shared.get(key) !== value && !(key==='Endpoint' && terms.includes(value))).map(([key,value]) => `${esc(key)}: ${esc(value)}`).join('<br>');
      return `<tr data-statistic="${esc(stat.statistic_id)}"><td data-label="Finding / statistic"><strong>${terms.map(esc).join(' · ')}</strong><small>${esc(label)}</small>${description}${stat.evidence_role==='EDUCATIONAL_STATEMENT'?rolePill(stat.evidence_role):''}</td><td data-label="Study context">${context || '—'}</td><td data-label="Value" class="result-number">${esc(valueText(stat))}${uncertainty(stat) ? `<small>${esc(uncertainty(stat))}</small>` : ''}</td><td><button class="text-button" data-stat="${esc(stat.statistic_id)}">Source details</button></td></tr>`;
    }).join('')}</tbody></table>`;
  }
  function weightRows(rows,sourceId,setting) {
    const selected=new Set(rows.map(row=>row.id)),records=new Map();
    const add=(key,label,axis,value,current,context=false)=>{
      if(!records.has(key))records.set(key,{id:key,label,values:{},context});
      const record=records.get(key);
      if(!record.values[axis])record.values[axis]={...value,current:[]};
      else if(record.values[axis].id!==value.id)throw new Error('Distinct appraisal receipts cannot share a weight cell');
      if(!record.values[axis].current.some(item=>item.id===current.id))record.values[axis].current.push(current);
    };
    const receiptScope=receipt=>JSON.stringify([receipt.source_id,receipt.original_sign_id,[...receipt.finding_refs].sort(),[...receipt.statistic_ids].sort()]);
    for(const id of nativeIds(rows))for(const axis of axes){
      const contribution=(weightIndex.get(id)?.get(axis)?.contributions||[]).find(c=>c.source_id===sourceId);
      if(!contribution?.result_ids.some(result=>selected.has(result)))continue;
      const currentIds=new Set(contribution.result_ids.filter(result=>selected.has(result)));
      const current={...contribution,label:nativeSigns.get(id)?.label||rows.find(row=>row.sign_id===id)?.term||'',complete:contribution.complete!==false&&contribution.result_ids.every(result=>selected.has(result))};
      const references=(contribution.appraisal_receipt_ids||[]).map(key=>{
        const receipt=data.appraisal_receipts?.[key];
        if(!receipt||receipt.source_id!==sourceId||receipt.axis!==axis)throw new Error('Appraisal reference changes source or axis');
        return receipt;
      });
      const contextual=contribution.appraisal_match_status==='SOURCE_WORK_CONTEXT';
      const scoped=references.filter(receipt=>!contextual&&receipt.context_result_ids.some(result=>currentIds.has(result)));
      for(const receipt of scoped)add('appraisal:'+receiptScope(receipt),atlasAppraisalLabel(receipt),axis,{...receipt,complete:true,appraisal:true},current);
      if(!scoped.length)add('contribution:'+id,current.label,axis,current,current);
      if(contextual)for(const receipt of references)add('context:'+receiptScope(receipt),atlasAppraisalLabel(receipt),axis,{...receipt,complete:true,appraisal:true},current,true);
    }
    const scopedIds=new Set([...records.values()].filter(record=>!record.context).flatMap(record=>Object.values(record.values).filter(value=>value.appraisal).map(value=>value.id)));
    for(const record of records.values())if(record.context)for(const axis of axes)if(scopedIds.has(record.values[axis]?.id))delete record.values[axis];
    return [...records.values()].filter(record=>axes.some(axis=>record.values[axis])).sort((a,b) => {
      const av=a.values[setting.weights]?.potential_weight,bv=b.values[setting.weights]?.potential_weight;
      return (av == null)-(bv == null) || (Number(bv)||0)-(Number(av)||0) || a.label.localeCompare(b.label);
    });
  }
  function currentWeightMarkup(value,axis) {
    return value.current.map(current=>{
      const view=atlasWeightPresentation(current,axis),unassigned=/UNRESOLVED/.test(current.weight_status||'');
      return `<p><strong>${esc(current.label)}</strong>: ${esc(unassigned?'Not assigned':view.applied)}${view.reason?`<br>${esc(view.reason)}`:''}</p>`;
    }).join('');
  }
  function paperWeights(rows,sourceId,setting,groupId) {
    const records = weightRows(rows,sourceId,setting); if (!records.length) return '';
    const scoped=records.filter(item=>!item.context),context=records.filter(item=>item.context);
    const table=scoped.map(item=>`<tr><td>${esc(item.label)}</td>${axes.map(axis=>{
      const value=item.values[axis];if(!value)return '<td>—</td>';
      const view=atlasWeightPresentation(value,axis);
      return `<td${value.appraisal?` data-appraisal="${esc(value.id)}"`:''}>${esc(view.label)}${['I','II','III'].includes(value.evidence_class)?`<small>${esc(classLabel(value.evidence_class))}</small>`:''}</td>`;
    }).join('')}</tr>`).join('');
    const details=scoped.map(item=>axes.filter(axis=>item.values[axis]).map(axis=>{
      const value=item.values[axis],view=atlasWeightPresentation(value,axis);
      return `<section class="calculation-line"><strong>${esc(item.label)} · ${axisName(axis)}</strong>${view.label==='—'&&view.reason?`<p>${esc(view.reason)}</p>`:''}${view.calculation?`<p>${esc(view.calculation)}</p>`:''}${!publicSite&&value.appraisal&&value.original_sign_label?`<p>Original database label: ${esc(value.original_sign_label)}</p>`:''}<h5>Applied contribution</h5>${currentWeightMarkup(value,axis)}</section>`;
    }).join('')).join('');
    const other=context.length?`<details class="calculation"><summary>Appraisals for other signs in this paper</summary>${context.map(item=>axes.filter(axis=>item.values[axis]).map(axis=>{const value=item.values[axis],view=atlasWeightPresentation(value,axis);return `<section data-context-appraisal="${esc(value.id)}"><strong>${esc(item.label)} · ${axisName(axis)}</strong><p>Stored weight: ${esc(view.label)}${['I','II','III'].includes(value.evidence_class)?` · ${esc(classLabel(value.evidence_class))}`:''}</p>${!publicSite&&value.original_sign_label?`<details><summary>Original database label</summary><p>${esc(value.original_sign_label)}</p></details>`:''}</section>`;}).join('')).join('')}</details>`:'';
    return `<div class="paper-weights"><h4>Paper weights by assessed sign</h4><table class="weight-table"><thead><tr><th>Assessed sign</th>${axes.map(axis=>`<th><button data-weight-order="${axis}" data-group="${esc(groupId)}">${axisName(axis)} weight ↓</button></th>`).join('')}</tr></thead><tbody>${table}</tbody></table><details class="calculation"><summary>Calculation and contribution scope</summary>${details}</details>${other}</div>`;
  }
  function findingsMarkup(rows) { return [...new Map(rows.map(row=>[row.id,row])).values()].map(row => `<article class="finding"><h4>${esc(row.term)}</h4>${clean(row.source.excerpt) ? `<p>${esc(row.source.excerpt)}</p>` : ''}<p>${esc(locator(row.source.locator))}</p></article>`).join(''); }
  function sourceLink(id) { const doi=clean(bibliography(id).doi); return doi ? `<a href="https://doi.org/${esc(encodeURI(doi))}" target="_blank" rel="noopener">Publication ↗</a>` : ''; }
  function localizationAnnotation(row,value) {
    const matches=(row.facets.anatomy || []).filter(item=>selectedAnatomy.has(item.id) && item.source_item_id===value.target_id && item.source_term===value.source_term && item.role===value.role);
    const exact=new Set(matches.filter(item=>item.scope==='EXACT').map(item=>item.id));
    const labels=uniq(matches.filter(item=>item.scope==='OVERLAP' && !exact.has(item.id)).map(item=>item.label).filter(Boolean));
    return labels.length ? `Anatomical overlap · ${labels.join('; ')}` : '';
  }
  function paperMarkup(id,rows,stats,setting,groupId,embedded=false) {
    const roles=uniq(rows.flatMap(row=>(row.facets.evidence || []).map(item=>item.id.replace(/^EVIDENCE:/,''))));
    const evidenceClasses=classesFor(rows).map(classLabel).join(' · ');
    const body=`<div class="paper-content" tabindex="0" role="region" aria-label="${esc(citation(id))}: evidence">${embedded?`<div class="paper-tools"><span class="evidence-class-label">${esc(evidenceClasses)}</span>${roles.map(rolePill).join(' ')}</div>`:''}<div class="paper-links">${sourceLink(id)}${publicSite?`<button class="text-button map-link" data-show-map="${esc(groupId)}" data-map-source="${esc(id)}">Show on map</button>`:''}</div>${atlasSourceFindingsMarkup(rows,{compact:true,localizationAnnotation})}${paperWeights(rows,id,setting,groupId)}${resultsMarkup(stats,rows)}<details class="context-details"><summary>Findings and source passages</summary>${atlasSourceFindingsMarkup(rows)}${findingsMarkup(rows.filter(row=>!(row.source_anatomy||[]).some(value=>clean(value.source_excerpt)===clean(row.source.excerpt))))}</details></div>`;
    return embedded ? body : `<details class="paper" data-paper="${esc(id)}" data-group="${esc(groupId)}" ${setting.openPapers?.has(id)?'open':''}><summary><div class="paper-title"><h3>${esc(sourceTitle(id))}</h3><p>${esc(citation(id))}</p><div class="paper-tools"><span class="evidence-class-label">${esc(evidenceClasses)}</span>${roles.map(rolePill).join(' ')}</div></div></summary>${body}</details>`;
  }
  function signBody(group,embedded=false) {
    const setting=settings(group.id),rowsForClass=group.rows.filter(row=>classMatches(row,setting.evidenceClass)),allStats=statisticsFor(rowsForClass),types=metricTypesFor([...allStats,...(setting.metric?[{metric_type:setting.metric}]:[])]);
    let stats=evidenceStats(rowsForClass,setting),ids=paperIds(rowsForClass);
    if (setting.metric || (state.order.startsWith('values-') && state.metric)) { const included=new Set(stats.flatMap(stat=>paperIds(ownersFor(stat,rowsForClass)))); ids=ids.filter(id=>included.has(id)); }
    ids.sort((a,b)=>(setting.sort==='class' ? classRank(rowsForClass.filter(row=>row.source.id===a))-classRank(rowsForClass.filter(row=>row.source.id===b)) : 0) || (setting.sort==='year' ? (Number(bibliography(b).publication_year)||0)-(Number(bibliography(a).publication_year)||0) : 0) || citation(a).localeCompare(citation(b)));
    const controls=`<div class="inside-controls dictionary-controls" data-paper-count="${ids.length}"><div class="field"><label>Paper order</label><select data-detail="sort" data-group="${esc(group.id)}" aria-label="Paper order">${[['name','Author A–Z'],['year','Newest paper'],['class','Evidence class (I–III)']].map(([id,label])=>`<option value="${id}" ${setting.sort===id?'selected':''}>${label}</option>`).join('')}</select></div><div class="field"><label>Reported statistic</label><select data-detail="metric" data-group="${esc(group.id)}" aria-label="Reported statistic">${[['','All statistics'],...types.map(type=>[type,metricName(type)])].map(([id,label])=>`<option value="${esc(id)}" ${setting.metric===id?'selected':''}>${esc(label)}</option>`).join('')}</select></div><div class="field"><label>Evidence class</label><select data-detail="evidenceClass" data-group="${esc(group.id)}" aria-label="Study evidence class">${[['','All classes'],...classesFor(group.rows).map(id=>[id,classLabel(id)])].map(([id,label])=>`<option value="${esc(id)}" ${setting.evidenceClass===id?'selected':''}>${esc(label)}</option>`).join('')}</select></div></div>`;
    const fullGroup=groups.find(item=>item.id===group.id),fullRows=(fullGroup ? selectedRows(fullGroup.rows) : group.rows).filter(row=>classMatches(row,setting.evidenceClass));
    const expand=state.query.trim() && fullRows.length>rowsForClass.length ? `<button class="text-button" data-all-term="${esc(group.id)}">View all ${paperIds(fullRows).length} papers for this term</button>` : '';
    return expand + controls + (publicSite && !embedded?`<button class="text-button map-link" data-show-map="${esc(group.id)}">Show on map</button>`:'') + ids.slice(0,setting.papers).map(id=>{const rows=rowsForClass.filter(row=>row.source.id===id),owned=new Set(statisticsFor(rows).map(stat=>stat.statistic_id));return paperMarkup(id,rows,stats.filter(stat=>owned.has(stat.statistic_id)),setting,group.id,embedded);}).join('') + (ids.length>setting.papers ? `<button class="more" data-more-papers="${esc(group.id)}">Show ${ids.length-setting.papers} remaining papers</button>` : '') + (!ids.length ? '<p class="empty">No papers match the selected filters.</p>' : '');
  }
  function renderEntry(card) { const entry=entries[Number(card.dataset.entry)]; if (!entry || !card.open) return; card.querySelector('.sign-body').innerHTML=signBody(entry.group,entry.type==='source'); if(entry.type==='sign'){const count=Number(card.querySelector('[data-paper-count]').dataset.paperCount),total=paperIds(entry.group.rows).length;card.querySelector('.sign-meta').textContent=count<total ? `${count} of ${total} papers` : `${count} ${count===1?'paper':'papers'}`;} card.dataset.loaded='true'; }
  function refreshGroup(id) { root.querySelectorAll('.sign-card[open]').forEach(card=>{if(entries[Number(card.dataset.entry)]?.group.id===id)renderEntry(card);}); }
  function openDialog(title,body,rows=[]) { dialogRows=rows; $('dialog-title').textContent=title; $('dialog-body').innerHTML=body; $('record-dialog').showModal(); $('record-dialog').scrollTop=0; }
  function openStatistic(id) {
    const stat=data.statistics[id]; if(!stat)return; const rows=statOwners.get(id)||[];
    const statements=atlasStatisticGroups(Object.values(data.statistics)).find(group=>group.statistic.statistic_id===id)?.statements || [stat];
    const fields=[['Statistic',metricName(stat.metric_type)],['Reported measure',stat.measure],['Numerator',clean(stat.numerator)||stat.numerator_value],...contexts(stat),['Reported unit',stat.unit],['Phase',stat.phase],['Anatomy / laterality',stat.anatomy_laterality_context],['Uncertainty',uncertainty(stat)],['Evidence role',roleName(stat.evidence_role)],['Independence classification',stat.independent_evidence===1?'Independent observation; independence of cohorts is not established.':stat.independent_evidence===0?'Not classified as independent evidence.':'Not recorded'],['Source locator',locator(stat.source_locator)]];
    if(stat.independence_status)fields.push(['Reporting status',roleName(stat.independence_status)]);
    if(stat.restatement_explanation)fields.push(['Restatement context',stat.restatement_explanation]);
    openDialog(clean(stat.measure)||metricName(stat.metric_type),`<div class="dialog-value">${esc(valueText(stat))}</div><p>${paperIds(rows).map(id=>esc(citation(id))).join(' · ')}</p><dl>${fields.map(([label,value])=>`<dt>${esc(label)}</dt><dd>${esc(clean(value)||'Not recorded')}</dd>`).join('')}</dl><h3>Source passages</h3>${statements.map(item=>`<p><strong>${esc(locator(item.source_locator))}</strong><br>${esc(item.source_excerpt)}</p>`).join('')}`);
  }
  function explain() { openDialog('Weights & statistics explained','<h3>Organization and ordering</h3><p>Lüders and ILAE use their recorded classification categories. Region adds regional groups within those categories. A–Z and Number of publications order signs within each group. Reported-statistic ordering applies within each paper, separately for each metric and unit.</p>'+root.getElementById('scientific-explanation').innerHTML); }
  function refresh() { state.limit=30; opened.clear(); syncControls(); renderList(); }
  function resetFilters({preserveFocus=false}={}) {
    detailState.clear();
    selectedAnatomy.clear();
    Object.assign(state,{query:'',sourceQuery:'',filters:{},metric:'',focus:preserveFocus?state.focus:''});
    if(!preserveFocus)pendingFocus='';
    $('search').value='';updateQuery();refresh();
  }
  root.addEventListener('toggle',event=>{const card=event.target;if(!card.isConnected)return;if(card.classList.contains('region-card')){if(card.open){state.openRegions.add(card.dataset.region);renderRegion(card);}else state.openRegions.delete(card.dataset.region);return;}if(card.classList.contains('paper')){const papers=settings(card.dataset.group).openPapers;if(card.open)papers.add(card.dataset.paper);else papers.delete(card.dataset.paper);return;}if(!card.classList.contains('sign-card'))return;const entry=entries[Number(card.dataset.entry)];if(!entry)return;if(card.open){opened.add(entry.key);if(!card.dataset.loaded)renderEntry(card);}else opened.delete(entry.key);},true);
  root.addEventListener('click',event=>{
    const button=event.target.closest('button');if(!button)return;
    if(button.id==='help' || button.hasAttribute('data-evidence-help'))explain();
    if(button.hasAttribute('data-clear-map')){evidenceMap?.clear();return;}
    if(button.dataset.showMap){
      const card=button.closest('.sign-card'),group=card?entries[Number(card.dataset.entry)]?.group:null;
      const additional=button.closest('#additional-results .paper');
      const context=group?selectedRows(group.rows).filter(row=>classMatches(row,settings(group.id).evidenceClass)):button.closest('#record-dialog')?dialogRows:additional?additionalPaperRows.get(additional.dataset.paper)||[]:[];
      const rows=context.filter(row=>!button.dataset.mapSource || row.source.id===button.dataset.mapSource);
      if(rows.length){if(button.closest('#record-dialog'))$('record-dialog').close();evidenceMap?.showEvidence(rows,button.dataset.mapSource?sourceTitle(button.dataset.mapSource):group.label);}
      return;
    }
    if(button.id==='close-dialog')$('record-dialog').close();
    if(button.id==='reset'){if(options.embedded && options.onClearFilters)options.onClearFilters();else resetFilters();return;}
    if(button.id==='all-sources'){if(options.embedded){options.onViewSources?.();return;}evidenceMap?.clear(false);mapResultIds=null;Object.assign(state,{query:'',sourceQuery:'',organize:'source',filters:{},order:'name',metric:'',focus:''});$('search').value='';updateQuery();refresh();}
    if(button.id==='more-signs'){state.limit=entries.length;renderList();}
    if(button.dataset.moreRegion){state.regionLimits.set(button.dataset.moreRegion,Infinity);renderRegion(button.closest('.region-card'));}
    if(button.dataset.clearFilter){delete state.filters[button.dataset.clearFilter];refresh();}
    if(button.dataset.stat)openStatistic(button.dataset.stat);
    if(button.dataset.allTerm){if(options.embedded){pendingFocus=button.dataset.allTerm;options.onClearFilters?.({preserveFocus:true});return;}state.query='';state.focus=button.dataset.allTerm;$('search').value='';updateQuery();opened.clear();opened.add(state.focus);syncControls();renderList();}
    if(button.dataset.morePapers){settings(button.dataset.morePapers).papers=Infinity;refreshGroup(button.dataset.morePapers);}
    if(button.dataset.weightOrder){settings(button.dataset.group).weights=button.dataset.weightOrder;refreshGroup(button.dataset.group);}
    if(button.dataset.source){const id=button.dataset.source,rows=selectedRows(unplaced).filter(row=>row.source.id===id && (!state.query.trim() || queryMatch(row.term)));openDialog(citation(id),paperMarkup(id,rows,evidenceStats(rows,settings(id)),settings(id),id),rows);}
  });
  root.addEventListener('change',event=>{
    const {id,value,dataset}=event.target;
    if(dataset.detail){settings(dataset.group)[dataset.detail]=value;refreshGroup(dataset.group);return;}
    if(dataset.facet){if(value)state.filters[dataset.facet]=value;else delete state.filters[dataset.facet];refresh();return;}
    if(id==='organize'){state.organize=value;state.order='name';state.focus='';if(['ilae','luders'].includes(value)){if(state.scheme!==value){delete state.filters.ilae;delete state.filters.luders;}state.scheme=value;grouping();}}
    else if(id==='group'){if(value)state.filters[state.organize]=value;else delete state.filters[state.organize];}
    else if(id==='evidence-class'){if(value)state.filters.evidence_class=value;else delete state.filters.evidence_class;for(const setting of detailState.values())setting.evidenceClass='';}
    else if(id==='order')state.order=value;
    else if(id==='metric')state.metric=value;
    else return;
    refresh();
  });
  $('search').addEventListener('input',event=>{state[state.organize==='source'?'sourceQuery':'query']=event.target.value;state.focus='';state.limit=30;opened.clear();updateQuery();renderList();});
  sources=new Map(catalogue.items.filter(item=>item.facet==='source').map(item=>[item.id,item]));nodeIndex=new Map(catalogue.items.map(item=>[item.id,item]));nativeSigns=new Map(atlasGroups(data.rows,'sign').map(group=>[group.id,group]));statOwners=new Map();
    for(const row of data.rows)for(const id of row.statistic_ids){if(!statOwners.has(id))statOwners.set(id,[]);statOwners.get(id).push(row);}
    for(const axis of axes)for(const summary of data.weights[axis]||[]){if(!weightIndex.has(summary.sign_id))weightIndex.set(summary.sign_id,new Map());weightIndex.get(summary.sign_id).set(axis,summary);}
    metricTypes=metricTypesFor(statisticsFor(data.rows.filter(row=>row.record_kind==='SIGN_EVIDENCE')));

  grouping();
  if(options.embedded)$('organize').querySelector('option[value="source"]').remove();
  $('search').value=state.query;syncControls();renderList();
  return {
    resetFilters,
    update({rows,view='browse',query='',queryContext={}}) {
      selectedAnatomy=new Set(queryContext.anatomy || []);
      mapResultIds=new Set(rows.map(row=>row.id));state.query=options.embedded?'':query;state.focus=pendingFocus;pendingFocus='';
      if(view!==currentView){if(currentView!=='sources'){signOrganization=state.organize;signOrder=state.order;}state.organize=view==='sources'?'source':signOrganization;state.order=view==='sources'?'name':signOrder;currentView=view;}
      $('organize').closest('.field').hidden=view==='sources';refresh();
    },
    collapseAll(){root.querySelectorAll('details[open]').forEach(element=>{element.open=false;});opened.clear();state.openRegions.clear();},
    expandGroups(){root.querySelectorAll('.region-card,.sign-list>.sign-card').forEach(element=>{element.open=true;});}
  };

}
