import { atlasSearchRows, atlasGroups, atlasCounts, atlasEvidenceSection, atlasNavigationGroups, atlasDictionaryGroups, atlasSignSections, atlasRegionRank, atlasMetricLabels, atlasMetricTypes, atlasWeightPresentation, atlasAppraisalLabel, atlasSourceFindingsMarkup, atlasSourceFindingGroups, atlasSourceLocator, atlasStatisticGroups, atlasLoadDetails, atlasResolvedAxis } from './atlas_projection.mjs?v=343617db8d7e4f085989a3b252463726dad13ecdd3d70f905708a9d27444a00d';

const evidenceRoleLabels = {PRIMARY_RESULT:'Results from this study',CASE_OBSERVATION:'Clinical case',REVIEW_SYNTHESIS:'Review findings',REVIEW_AUTHOR_SYNTHESIS:'Review findings',GUIDELINE_RECOMMENDATION:'Clinical guidance',CITED_STUDY_RESTATEMENT:'Earlier research',PRIMARY_RESULT_SAME_SOURCE_RESTATEMENT:'Results from this study',EDUCATIONAL_STATEMENT:'Background',METHOD_OR_DEFINITION:'Method or definition',SOURCE_CONTEXT:'Background',COHORT_CONTEXT:'Study population',SOURCE_REPORTED_TARGET:'Reported relationship',SOURCE_REPORTED:'Reported relationship',STIMULATION:'Stimulation',OWNER_APPROVED_INTERPRETATION:'Interpretation'};
export function atlasEvidenceRoleLabel(value) { return evidenceRoleLabels[String(value || '').replace(/^EVIDENCE:/,'')] || ''; }

const styles = `
.weight-table td>strong{font-size:12px;font-weight:600}.weight-table td>span{display:block;font-size:12px}.weight-table td>small:last-of-type{margin-top:10px}.weight-table td>small:first-child{margin-top:0}
:host{color-scheme:light;--ink:#193a3b;--muted:#60736c;--teal:#176862;--pale:#eaf2ed;--line:#dce5df;--canvas:#f6f8f4;--serif:Georgia,'Times New Roman',serif;font:15px/1.5 Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:var(--ink);background:var(--canvas)}
*{box-sizing:border-box}body{margin:0}button,input,select{font:inherit;color:inherit}button,summary,a{touch-action:manipulation}button,summary{cursor:pointer}button,a,input,select,summary{-webkit-tap-highlight-color:transparent}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #b88636;outline-offset:3px}button:disabled{cursor:default;opacity:.6}a{color:var(--teal)}h1,h2,h3,h4,p{margin:0}h1{font:34px/1.2 var(--serif);letter-spacing:-.6px}h2{font:25px/1.25 var(--serif)}h3{font-size:16px}h4{font-size:14px}small,.muted{color:var(--muted)}[hidden]{display:none!important}button{border:0;background:none}.skip{position:absolute;top:-70px;left:16px;background:white;padding:12px;z-index:5}.skip:focus{top:10px}
.masthead{background:white;border-bottom:1px solid var(--line)}.mast-inner{max-width:1220px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:18px;padding:15px 28px}.brand{display:flex;gap:9px;align-items:center;font-weight:700;letter-spacing:-.3px}.brand svg{width:28px;height:28px}.help-button{color:var(--teal);font-size:12px;min-height:44px;padding:8px 0;text-align:right;text-decoration:underline;text-underline-offset:3px}
main{max-width:1220px;margin:auto;padding:30px 28px}.intro{display:flex;gap:20px;align-items:center;justify-content:space-between;margin-bottom:23px}.corpus{font-size:13px;color:var(--muted)}.corpus button{padding:7px 0;color:var(--teal);text-decoration:underline;text-underline-offset:3px}.toolbar{display:grid;grid-template-columns:minmax(220px,1.4fr) minmax(170px,1fr) minmax(185px,1fr);gap:14px;padding:18px;background:white;border:1px solid var(--line);border-radius:9px}.field{display:flex;flex-direction:column;gap:6px;min-width:0}.field label{font-size:11px;font-weight:650;color:var(--muted)}input,select{width:100%;min-width:0;height:43px;border:1px solid #cdd9d2;background:white;border-radius:5px;padding:0 10px;font-size:14px}input::placeholder{color:#87958d}.dependent{grid-column:1/-1;display:flex;gap:14px}.dependent .field{flex:1;max-width:540px}.list-meta{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:13px 1px;font-size:12px;color:var(--muted)}.list-meta button{font-size:12px;min-height:36px;text-decoration:underline;text-underline-offset:3px;color:var(--muted)}
.sign-section{min-width:0}.sign-section>summary{display:flex;align-items:center;gap:16px;list-style:none;padding:15px 17px;background:var(--pale);border:1px solid var(--line);border-radius:8px}.sign-section>summary::-webkit-details-marker{display:none}.sign-section>summary>strong{flex:1;min-width:0;font-size:15px;overflow-wrap:anywhere}.sign-section>summary>span{font-size:12px;color:var(--muted)}.sign-section>summary:after{content:'+';color:var(--teal);font-size:23px;flex:none}.sign-section[open]>summary:after{content:'−'}.section-body{display:grid;gap:10px;padding:10px 0 6px 12px}.section-body .sign-section>summary{background:var(--canvas)}@media(max-width:500px){.sign-section>summary{gap:8px;padding:12px}.sign-section>summary>span{max-width:100px;text-align:right}.section-body{padding-left:6px}}
.sign-list{display:grid;gap:10px}.sign-card{background:white;border:1px solid var(--line);border-radius:8px;min-width:0}.sign-card>summary{display:flex;align-items:center;gap:20px;list-style:none;padding:19px 21px}.sign-card>summary::-webkit-details-marker{display:none}.sign-card>summary:after{content:'+';font-size:23px;font-weight:300;color:var(--teal);margin-left:2px;flex:none}.sign-card[open]>summary:after{content:'−'}.sign-card[open]{border-color:#9dbbb0}.sign-card[open]>summary{background:#f3f7f2;border-radius:8px 8px 0 0}.sign-title{min-width:0;flex:1}.sign-title strong{font-size:17px;font-weight:600;line-height:1.4;display:block;overflow-wrap:anywhere}.sign-meta{font-size:12px;color:var(--muted);display:block;margin-top:5px}.weights{display:flex;gap:9px;flex-wrap:wrap}.weight-scope{flex-basis:100%;font-size:10px;color:var(--muted)}.weight{display:flex;align-items:baseline;gap:9px;padding:6px 10px;border-radius:5px;background:var(--pale);font-size:11px;color:#46665b}.weight b{font-size:15px;color:var(--teal);font-weight:650;font-variant-numeric:tabular-nums}.weight.pending{background:#f7f0e2;color:#826535}.weight.pending b{color:#826535;font-size:12px}.weight.none{background:#f3f5f2;color:#7a877f}.weight.none b{color:#7a877f}.sign-body{padding:20px;min-width:0;border-top:1px solid var(--line)}.inside-controls{display:flex;gap:12px;margin:0 0 20px;align-items:end;flex-wrap:wrap}.inside-controls .field{flex:1;min-width:150px}.inside-controls select{font-size:12px;height:40px}.inside-controls .field label{font-size:10px}.inside-controls .filter-button{min-height:40px;color:var(--teal);font-size:12px;padding:0 5px}.filter-row{display:flex;gap:10px;margin-bottom:18px}.filter-row .field{flex:1;max-width:360px}.context-details{font-size:12px;margin:0 0 18px;color:var(--muted)}.context-details>summary{color:var(--teal);min-height:32px;display:flex;align-items:center;gap:6px}.context-details>summary:before{content:'▸'}.context-details[open]>summary:before{content:'▾'}.context-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:12px 0}.context-grid h4{font-size:12px;margin-bottom:7px}.context-line{margin:7px 0;overflow-wrap:anywhere}.context-line small{display:block;font-size:10px}.source-wording{margin-top:10px;font-size:12px}
.paper{border-top:1px solid var(--line);padding-top:20px;margin-top:20px;min-width:0}.paper:first-child{margin-top:0;padding-top:0;border:0}.paper-head{display:flex;justify-content:space-between;align-items:start;gap:16px;margin-bottom:12px}.paper-title{min-width:0;flex:1}.paper-title h3{font-size:16px}.paper-title p{font-size:12px;color:var(--muted);margin-top:4px;overflow-wrap:anywhere}.paper .weights{gap:6px}.paper .weight{font-size:10px;padding:4px 7px}.paper .weight b{font-size:13px}.paper-tools{display:flex;gap:15px;align-items:baseline;flex-wrap:wrap;font-size:11px;margin:8px 0 14px}.paper-tools a,.text-button{font-size:12px;color:var(--teal);text-decoration:underline;text-underline-offset:3px}.text-button{padding:7px 0;min-height:34px;text-align:left}.calculation{font-size:12px;min-width:0}.calculation summary{color:var(--teal);min-height:32px;display:flex;align-items:center;gap:6px}.calculation summary:before{content:'▸'}.calculation[open] summary:before{content:'▾'}.calculation-body{padding:12px 0 16px;display:grid;gap:12px}.calculation-row{padding:12px;background:#f5f8f3;border-radius:5px}.calculation-row strong{display:block;margin-bottom:6px}.factors{display:flex;flex-wrap:wrap;gap:5px 14px;font-size:12px}.factors span{white-space:normal}.calculation-row p{margin-top:7px;color:var(--muted);font-size:11px}
.statistics{display:grid;gap:8px}.stat-card{display:grid;grid-template-columns:minmax(0,1fr) minmax(110px,auto);gap:7px 22px;border:1px solid #e2e8e1;border-radius:6px;padding:14px 16px;min-width:0;background:#fff}.stat-label{font-size:11px;color:var(--muted);margin-bottom:3px}.stat-description{font-size:13px;overflow-wrap:anywhere;line-height:1.5}.stat-value{font-size:20px;font-weight:600;line-height:1.3;color:var(--teal);text-align:right;overflow-wrap:anywhere;max-width:280px;font-variant-numeric:tabular-nums}.stat-value small{display:block;font-size:11px;font-weight:400;color:var(--muted);margin-top:5px}.stat-context{grid-column:1/-1;font-size:11px;color:var(--muted);overflow-wrap:anywhere}.stat-foot{grid-column:1/-1;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:7px 18px}.stat-foot .text-button{font-size:11px}.pill{font-size:10px;line-height:1.4;color:#526e5c;background:#edf3ed;border-radius:3px;padding:3px 6px;display:inline-block}.pill.review{background:#f4eddf;color:#7b6337}.pill.context{background:#eef0f4;color:#5e6c7b}.more{width:100%;min-height:44px;padding:12px;font-size:12px;color:var(--teal);background:#f0f5ee;border:1px solid var(--line);border-radius:6px;margin-top:8px}.empty{padding:30px 14px;text-align:center;font-size:13px;color:var(--muted)}.group-heading{font-size:13px;color:var(--muted);font-weight:650;margin:13px 2px 2px}.result-summary .stat-value{font-size:22px;flex:none;width:150px}.source-card>summary .sign-title strong{font-size:16px}.finding{margin:14px 0;border-top:1px solid var(--line);padding-top:12px;font-size:12px;overflow-wrap:anywhere}.finding h4{font-size:13px;margin-bottom:6px}.finding p{color:var(--muted);margin-top:7px}.sign-links{display:flex;gap:6px 16px;flex-wrap:wrap;margin-bottom:14px}
footer{max-width:1220px;margin:auto;padding:4px 28px 28px;display:flex;justify-content:space-between;gap:15px;font-size:11px;color:var(--muted)}footer a{color:var(--muted)}dialog{padding:0;width:min(800px,calc(100vw - 24px));max-height:90dvh;border:1px solid var(--line);border-radius:10px;color:var(--ink);background:white;overflow-x:hidden}dialog::backdrop{background:#102a2aae}.dialog-head{display:flex;align-items:start;gap:20px;justify-content:space-between;padding:20px 23px;border-bottom:1px solid var(--line);position:sticky;top:0;background:white;z-index:1}.dialog-head h2{font-size:23px;overflow-wrap:anywhere}.dialog-head button{border:1px solid var(--line);border-radius:4px;min-height:40px;padding:5px 10px;font-size:12px;flex:none}.dialog-body{padding:22px;font-size:13px;overflow-wrap:anywhere}.dialog-body h3{margin:23px 0 9px}.dialog-body h3:first-child{margin-top:0}.dialog-body p{margin:9px 0}.dialog-body ul{padding-left:20px}.dialog-body li{margin:7px 0}.dialog-body dl{display:grid;grid-template-columns:140px minmax(0,1fr);gap:12px;margin:18px 0}.dialog-body dt{color:var(--muted);font-size:12px}.dialog-body dd{margin:0}.dialog-value{font-size:28px;color:var(--teal)}
@media(max-width:850px){.sign-card>summary{flex-wrap:wrap;gap:12px}.sign-card>summary .sign-title{flex-basis:calc(100% - 45px)}.sign-card>summary:after{order:1;margin-left:auto}.sign-card>summary .weights{order:2;width:100%}.weight{flex:1;justify-content:space-between}.result-summary .stat-value{order:2;width:100%;text-align:left}.paper-head{display:block}.paper-head .weights{margin-top:10px}.toolbar{grid-template-columns:1fr 1fr}.toolbar>.field:first-child{grid-column:1/-1}.inside-controls .field{min-width:125px}}
@media(max-width:540px){.mast-inner{padding:10px 17px;gap:14px}.brand{font-size:14px;flex-shrink:0}.brand svg{width:24px;height:24px}.help-button{font-size:11px;max-width:140px;line-height:1.5}main{padding:22px 15px}.intro{display:block;margin-bottom:15px}h1{font-size:30px}.corpus{margin-top:8px;font-size:12px}.toolbar{padding:13px;gap:11px}input,select{font-size:16px}.toolbar label{font-size:10px}.dependent{flex-direction:column;gap:11px}.dependent .field{max-width:none}.sign-card>summary{padding:16px 14px;gap:11px}.sign-title strong{font-size:16px}.weights{gap:7px}.weight{font-size:10px;padding:6px 8px;gap:5px;min-width:0}.weight b{font-size:14px}.sign-body{padding:15px 12px}.inside-controls{gap:10px;margin-bottom:15px}.inside-controls .field{flex-basis:calc(50% - 10px);min-width:0}.inside-controls .field:last-of-type:nth-child(3){flex-basis:100%}.inside-controls select{font-size:14px}.filter-row{display:block}.filter-row .field{margin-top:10px}.context-grid{grid-template-columns:1fr;gap:8px}.paper{margin-top:18px;padding-top:18px}.stat-card{padding:12px;grid-template-columns:minmax(0,1fr);gap:6px}.stat-value{grid-row:1;text-align:left;max-width:none;font-size:22px}.stat-value small{font-size:11px;margin-top:3px}.stat-description{font-size:13px}.stat-label{font-size:10px}.stat-context{font-size:11px}.stat-foot{align-items:start}.paper-title h3{font-size:16px}.paper-title p{font-size:11px}.paper .weight{font-size:10px}.paper-tools{gap:12px}.dialog-head{padding:15px;gap:12px}.dialog-head h2{font-size:21px}.dialog-body{padding:17px}.dialog-body dl{grid-template-columns:1fr;gap:3px}.dialog-body dd{margin-bottom:10px}footer{padding:4px 16px 24px;font-size:10px}.source-card>summary .sign-title strong{font-size:15px}}
@media(prefers-reduced-motion:no-preference){.sign-card{transition:border-color .15s}.sign-card>summary:hover{background:#f4f8f2}}
.inside-controls{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr) auto}.inside-controls .field{min-width:0}.inside-controls .field:nth-of-type(3){grid-column:1/-1}.inside-controls .filter-button{grid-column:3;grid-row:1;padding:0 2px}.filter-row .field select{font-size:14px}
.sign-card:not([open])>summary .sign-title strong{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}

.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap}.active-filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}.filter-chip{font-size:12px;padding:6px 9px;background:#eaf2ed;border-radius:5px}.dictionary-controls{grid-template-columns:minmax(0,1fr) minmax(0,1fr);margin-bottom:18px}.shared-context{font-size:12px;color:var(--muted);margin:10px 0 18px;overflow-wrap:anywhere}.source-result{margin:16px 0 20px}.source-result>h4{font-size:13px;font-weight:600;margin-bottom:9px;overflow-wrap:anywhere}.result-table,.weight-table{border-collapse:collapse;table-layout:fixed;width:100%;font-size:12px}.result-table th,.result-table td,.weight-table th,.weight-table td{border-bottom:1px solid var(--line);padding:10px 9px;text-align:left;vertical-align:top;overflow-wrap:anywhere}.result-table th,.weight-table th{color:var(--muted);font-size:11px;font-weight:600;background:#f4f7f2}.result-table th:nth-child(1){width:55%}.result-table th:nth-child(2){width:45%}.result-table small{display:block;color:var(--muted);font-size:11px;margin-top:4px;font-weight:400}.result-number{font-weight:650;color:var(--teal);font-variant-numeric:tabular-nums}.result-role{margin-top:7px}.paper-weights{margin:17px 0}.paper-weights>h4{font-size:12px;margin-bottom:7px}.weight-table th:first-child{width:62%}.weight-table th:nth-child(n+2),.weight-table td:nth-child(n+2){text-align:right;font-variant-numeric:tabular-nums}.weight-table th button{font-size:11px;padding:0;text-align:right}.calculation-line{font-size:11px;margin:12px 0;color:var(--muted);overflow-wrap:anywhere}.paper{margin-top:26px;padding-top:22px}.paper:first-of-type{margin-top:0}
@media(max-width:540px){.result-table th,.result-table td{padding:8px 6px;font-size:12px}.weight-table{font-size:11px}.weight-table th,.weight-table td{padding:8px 4px}.weight-table th:first-child{width:52%}.weight-table th button{font-size:9px}.shared-context{font-size:11px}.source-result>h4{font-size:12px}.dictionary-controls select{font-size:14px}.paper{margin-top:23px}.paper-title h3{font-size:16px}}
.toolbar{grid-template-columns:minmax(210px,1.4fr) minmax(150px,1fr) minmax(180px,1fr) minmax(140px,.8fr)}.dictionary-controls{grid-template-columns:repeat(3,minmax(0,1fr))}.dictionary-controls .field:nth-of-type(3){grid-column:auto}.evidence-class-label{display:inline-block;color:var(--teal);font-size:11px;font-weight:600}.weight-table td small{display:block;color:var(--muted);font-size:10px;font-weight:400;margin-top:3px}
@media(max-width:850px){.toolbar{grid-template-columns:1fr 1fr}#evidence-class-field{grid-column:1/-1}}
@media(max-width:540px){.dictionary-controls{grid-template-columns:1fr 1fr}.dictionary-controls .field:nth-of-type(3){grid-column:1/-1}}
.source-scope{font-size:11px;color:var(--teal);font-weight:600;margin:0 0 8px}
.paper-anatomy{margin:14px 0 20px}.anatomy-result{margin:12px 0;font-size:12px;overflow-wrap:anywhere}.anatomy-result h4{font-size:13px;margin-bottom:5px}.source-detail{margin:7px 0}.source-detail p{margin-top:4px;color:var(--muted)}.source-detail small{display:block;margin-top:4px}.source-detail blockquote{margin:7px 0;padding-left:10px;border-left:2px solid var(--line);color:var(--muted)}
.paper,.paper:first-child{border:1px solid var(--line);border-radius:6px;padding:0;margin:10px 0 0}.paper>summary{background:#f5f8f4}.paper>summary .paper-tools{margin:7px 0 0;gap:10px}.paper-content{padding:12px 14px;max-height:min(68dvh,44rem);overflow:auto;scrollbar-gutter:stable;border-top:1px solid var(--line);font-size:12px}.paper-content> a{display:inline-block;margin-bottom:8px}.compact-anatomy{display:grid;gap:9px;padding:8px 0}.anatomy-subject{min-width:0;overflow-wrap:anywhere}.compact-anatomy h4{margin:0 0 2px;font-size:inherit}.compact-anatomy dl,.compact-anatomy dd{margin:0}.anatomy-axis{display:flex;flex-wrap:wrap;gap:0 5px}.anatomy-axis dt{color:var(--muted)}.anatomy-axis dd>span{display:block}.anatomy-qualifier{color:var(--muted)}.paper-content .shared-context{margin:8px 0}.paper-content .context-details{margin:8px 0 0}.paper-content .result-table{margin-top:10px}.paper-content .result-table th{position:sticky;top:0;background:#f1f5ee;z-index:1}.result-table td>strong{display:block}.result-table .result-finding-header td{background:#eef5fa}.paper-content .paper-weights{margin:8px 0}.paper-content .calculation-line{margin:10px 0}.paper-content .source-detail{margin:8px 0}.paper-content .source-detail small{display:block}.paper-content .source-detail blockquote{margin:5px 0;padding-left:10px;border-left:2px solid var(--line)}.paper-content .anatomy-result{margin:10px 0}.paper-content .result-table td,.paper-content .weight-table td{padding-top:9px;padding-bottom:9px}
@media(max-width:540px){.paper>summary{padding:11px 10px}.paper-content{padding:10px;max-height:65dvh;scrollbar-gutter:auto}.compact-anatomy{gap:8px}.paper-content .result-table th{position:static}.paper-title p{font-size:12px}}


.paper-links{display:flex;align-items:center;flex-wrap:wrap;gap:4px 16px;margin-bottom:8px}.paper-links .map-link{margin:0}.result-refinements{margin-bottom:16px;font-size:12px}.result-refinements>summary{padding:7px 0;color:var(--teal)}.refinement-state{color:var(--muted);font-size:11px}.result-refinements .inside-controls{margin:10px 0 0}.result-refinements .paper-controls{grid-template-columns:repeat(2,minmax(0,1fr))}.toolbar-label{grid-column:1/-1;color:var(--muted);font-size:12px;font-weight:600}
.paper-findings,.paper-measurements{margin:18px 0}.paper-findings>h4,.paper-measurements>h4,.paper-content .paper-weights>h4{font-size:13px;font-weight:650;margin-bottom:10px}.paper-content .paper-weights{margin-top:24px;padding-top:18px;border-top:1px solid var(--line)}.paper-content>.context-details{margin-top:18px;padding-top:10px;border-top:1px solid var(--line)}.paper-content .result-table{margin-top:8px}.paper-content .result-number{font-size:15px}.paper-content .result-number small{font-size:11px}.paper-content .compact-anatomy{margin:0;padding:0}.paper>summary{background:#fff}.paper>summary .paper-title h3{font-size:16px;line-height:1.45;font-weight:650}.paper>summary .paper-tools{gap:5px 12px}.paper-tools .pill{padding:0;background:transparent;font-size:11px}.paper-content .calculation-line h5{font-size:11px;font-weight:600;line-height:1.5;margin:8px 0 2px}
.organization-controls{display:contents}.toolbar slot[name=filters]{display:none}.embedded-help{display:none}:host([data-embedded]){--ink:#1a1d2e;--muted:#667085;--teal:#0a7a8a;--pale:#edf4f9;--line:#e3e8f0;--canvas:#fff;--serif:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;font:14px/1.5 Inter,ui-sans-serif,system-ui,sans-serif;background:transparent;display:block;min-width:0;container-type:inline-size}:host([data-embedded]) .owner-only,:host([data-embedded]) .intro h1{display:none}:host([data-embedded]) .embedded-help{display:block}:host([data-embedded]) main{max-width:none;margin:0;padding:0}:host([data-embedded]) .intro{display:none}:host([data-embedded]) .list-meta{flex-wrap:wrap;gap:6px 12px;margin:12px 0}:host([data-embedded]) #match-count{margin-right:auto}:host([data-embedded]) .list-meta slot{display:contents}:host([data-embedded]) .toolbar{grid-template-columns:minmax(0,1fr) minmax(0,1.35fr);align-items:start;padding:0;gap:20px;border:0}:host([data-embedded]) .organization-controls{display:grid;gap:12px;min-width:0}:host([data-embedded]) .toolbar slot[name=organization]{display:contents}:host([data-embedded]) .toolbar slot[name=filters]{display:block;min-width:0;align-self:stretch;border-left:1px solid var(--line);padding-left:20px}@container(max-width:520px){:host([data-embedded]) .toolbar{grid-template-columns:minmax(0,1fr);gap:12px}:host([data-embedded]) .organization-controls{grid-template-columns:repeat(auto-fit,minmax(min(140px,100%),1fr));gap:10px}:host([data-embedded]) .toolbar .organization-controls select{font-size:16px}:host([data-embedded]) .toolbar slot[name=filters]{border-left:0;border-top:1px solid var(--line);padding:12px 0 0}:host([data-embedded]) .list-meta{display:grid;grid-template-columns:minmax(0,1fr);gap:4px;margin:10px 0}:host([data-embedded]) .list-meta .help-button{max-width:none;min-height:44px;padding:4px 0;text-align:left;justify-self:start;line-height:1.4}}:host([data-embedded]) .toolbar label{font-size:14px;font-weight:650;color:var(--navy,#142653)}:host([data-embedded]) .toolbar select{height:44px;font-size:14px;font-weight:500;border:1px solid var(--line);border-radius:8px;background:#f8fafc;color:var(--navy,#142653)}:host([data-embedded]) .sign-card>summary{padding:12px 14px}:host([data-embedded]) .sign-title strong{font-size:15px}:host([data-embedded]) .sign-body{padding:12px}:host([data-embedded]) #reset{display:none}@media(max-width:850px){.toolbar>.toolbar-label+.field{grid-column:1/-1}}`;

const mobileStyles = `
.source-table{margin:12px 0 18px;font-size:13px}.source-table>h4{font-size:14px;font-weight:650;background:var(--pale);padding:10px}.source-table-context,.source-table-note,.source-table-locator{font-size:13px;margin:8px 0;line-height:1.5}.source-table-locator{color:var(--muted)}.source-table-region{max-width:100%;overflow-x:auto;border:1px solid var(--line);border-radius:5px;scrollbar-gutter:stable}.source-comparison{border-collapse:separate;border-spacing:0;table-layout:fixed;width:100%;min-width:44rem;font-size:13px}.source-comparison th,.source-comparison td{padding:9px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);text-align:left;vertical-align:top;overflow-wrap:anywhere}.source-comparison thead th{position:sticky;top:0;z-index:2;background:#f1f5ee;color:var(--ink);font-size:13px}.source-comparison thead th:first-child{width:9rem;left:0;z-index:3}.source-comparison tbody th{position:sticky;left:0;z-index:1;background:var(--canvas);min-width:9rem;font-weight:600}.source-comparison th small,.source-comparison td small{display:block;font-size:13px;font-weight:400;line-height:1.45;margin-top:5px}.source-comparison .result-number{font-size:14px;min-height:34px;padding:3px 0;text-align:left;text-decoration:underline;text-underline-offset:3px}.source-comparison .compact-anatomy{margin:5px 0}.source-comparison th:last-child,.source-comparison td:last-child{border-right:0}.source-comparison tr:last-child>*{border-bottom:0}@media(max-width:540px){.source-comparison tbody th{position:static}.source-comparison thead th:first-child{left:auto}}
.paper-content{font-size:14px;line-height:1.55}
.paper-summary{margin:14px 0 22px}.paper-summary h4{font-size:14px;margin-bottom:10px}.paper-summary p{margin:10px 0;color:var(--ink)}
.paper-content .result-table{font-size:13px}.paper-content .result-table thead th{font-size:13px}.paper-content .result-table th:nth-child(1){width:55%}.paper-content .result-table th:nth-child(2){width:45%}
.paper-content .result-table .compact-anatomy{margin-top:8px;font-size:13px}.paper-content .result-table .compact-anatomy h4{font-size:13px;font-weight:500}.paper-content .result-table small{font-size:13px}.paper-content .result-number{font-size:14px}.paper-content .result-table .text-button{display:block;font-size:13px}
@media(max-width:540px){.paper-content .result-table td{font-size:12px}.paper-content .result-table small{font-size:11px}}
.paper-topics{display:flex;flex-wrap:wrap;gap:4px 16px;margin:0 0 16px;padding:8px 0;border-bottom:1px solid var(--line)}.paper-topics button{min-height:36px;text-align:left}.paper-topic{margin:18px 0;min-width:0}.paper-topic>h4{font-size:15px;font-weight:650;margin-bottom:10px}.paper-topic>p{margin:8px 0 12px}.paper-finding{margin:10px 0;padding:8px 0;border-bottom:1px solid var(--line)}.paper-finding>.text-button{display:block;margin-top:6px}.paper-source-details{margin:14px 0 8px}.paper-source-details>button{min-height:44px}.paper-additional{margin:20px 0 8px;border-top:1px solid var(--line)}.paper-additional>summary{min-height:44px;padding:10px 0;font-size:14px;font-weight:650;color:var(--teal)}@media(max-width:540px){.paper-topics{gap:2px 12px}.paper-topics button{min-height:44px}.paper-topic{margin:16px 0}}
.controls-toggle{display:none}
@media(max-width:780px){
  :host([data-embedded]) .controls-toggle{display:flex;align-items:center;justify-content:space-between;gap:12px;width:100%;min-height:44px;margin:0 0 12px;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--pale);color:var(--navy,#142653);font:inherit;font-weight:650;text-align:left}
  .controls-toggle:after{content:'▾';color:var(--teal)}
  .controls-toggle[aria-expanded=false]:after{content:'▸'}
  :host([data-embedded]) .controls-toggle[aria-expanded=false]+.toolbar{display:none}
}`;

const markup = `
<a class="skip" href="#main">Skip to signs</a>
<header class="masthead owner-only"><div class="mast-inner"><div class="brand"><svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><rect width="32" height="32" rx="9" fill="#176862"/><path d="M8 16h4l3-7 3 14 3-7h3" stroke="white" stroke-width="1.8" stroke-linejoin="round"/></svg>Semiology Atlas</div><button class="help-button" id="help">Weights & statistics explained</button></div></header>
<main id="main"><div class="intro"><h1>Signs & evidence</h1><div class="intro-actions"><div class="corpus" id="corpus">Loading evidence…</div><button class="help-button embedded-help" data-evidence-help>Weights & statistics explained</button></div></div>
<button class="controls-toggle" id="controls-toggle" type="button" aria-expanded="true" aria-controls="evidence-toolbar">Filters and organization</button>
<div id="evidence-toolbar" class="toolbar" aria-label="Organize signs and evidence"><div class="field"><label id="search-label" for="search">Search</label><input id="search" type="search" placeholder="Sign or source wording" autocomplete="off"></div><div class="field"><label for="organize">View</label><select id="organize"><option value="sign">Signs</option><option value="source">Sources</option></select></div><div class="organization-controls"><slot name="organization"></slot><div class="field"><label id="order-label" for="order">Order signs by</label><select id="order"></select></div></div><div class="field" id="evidence-class-field"><label for="evidence-class">Evidence class</label><select id="evidence-class"></select></div><slot name="filters"></slot></div>
<div class="list-meta"><span id="match-count" aria-live="polite">Loading signs…</span><button id="reset">Reset</button><slot name="actions"></slot></div><div class="active-filters" id="active-filters"></div><section class="sign-list" id="sign-list" aria-label="Signs and evidence"><div class="empty">Loading evidence…</div></section>
</main>
<footer class="owner-only"><span>Owner preview</span><a href="https://www.semiologyatlas.org/" target="_blank" rel="noopener">Public atlas ↗</a></footer>
<dialog id="record-dialog" aria-labelledby="dialog-title"><div class="dialog-head"><h2 id="dialog-title"></h2><button id="close-dialog" aria-label="Close details">Close</button></div><div class="dialog-body" id="dialog-body"></div></dialog>
<template id="scientific-explanation"><h3>Signs and publication counts</h3><p>All signs lists each sign once. Region, ILAE and Lüders organize the same sign cards under their recorded categories, with matching papers underneath. A sign can appear in more than one supported category; totals count each sign and paper once. Region cards include only papers with a linked result in that region. Within Region, the sort control can add ILAE or Lüders subcategories. Anatomy and evidence filters narrow the results; sorting by A–Z, publications or evidence class preserves the sign names and source findings.</p><p>Sources includes all findings from each paper, including background information and findings without a sign group. Evidence publication totals count each matching paper once across Signs and Sources. Classification references without findings are counted separately and appear when no evidence filter is applied.</p><h3>Anatomy on the map</h3><p>Reported anatomy retains the regions linked to the selected findings. Study population and Comparison group describe the groups studied; they do not by themselves establish where a sign originates. Broader regions contain the linked anatomy. Overlapping atlas regions share some anatomical extent with the linked region according to the recorded relationships; overlap is not anatomical identity or a parent region. DKT40 parcels and Brodmann areas are separate atlas representations. The map displays the recorded links without adding localizing evidence.</p><h3>Reported statistics</h3><p>Statistic selectors list statistical and quantitative measures. Clinical features, sequence descriptions, and other paper-specific fields remain in the paper results under All statistics.</p><p>Each reported value retains its source, measured phenomenon, population, subgroup, analysis unit, denominator, comparator, and uncertainty. Each result shows the context reported for it. </p><h3>Evidence class</h3><p>Evidence-class filters select existing assignments for the displayed sign and source results. A result matches when the selected class is recorded for localization or lateralization. Unclassified includes results without an evidence-class assignment. The sign list shows terms with matching evidence; it does not assign a class to the sign itself.</p><p>Evidence-class ordering lists Class I, II, and III in that sequence, followed by unclassified evidence. Where a sign group or paper has several recorded classes, its lowest numbered class determines its position. All classes remain available in the findings; this ordering does not assign an overall class or calculate a new evidence score. The same order applies to papers inside each sign.</p><h3>Paper weights</h3><p>Each appraisal retains its original sign, paper, findings, and statistics. The table shows each appraisal once. A changed or narrower sign grouping can reference the appraisal without receiving a separate numerical contribution. Appraisals are not added together to give a sign an overall score.</p><p><strong>Appraised weight = class base × method factor × size factor.</strong> The applied contribution also depends on the recorded eligibility and scope. The class bases are 3, 2, or 1; an unclassified source can have a base of 0. Method factors are 1.5 for SEEG or postoperative evidence, 1.35 for other intracranial evidence, 1.2 for video, 1.15 for imaging, 1.1 for scalp EEG, 1 for review evidence, and 0.9 when the method is absent.</p><p>The size factor is min(2, 1 + log₁₀(N)/2). Missing N gives a factor of 1, and the class-I calculation does not use sample size. The selected N is unavailable here. A dash indicates that an appraisal is unavailable for that axis. A zero produced by an unresolved evidence class is unavailable, not a numerical assessment of the evidence. Calculation details retain the recorded factors and explain contribution eligibility and scope. An applied contribution of 0 indicates exclusion from the primary-evidence total; an unassigned contribution has not been established for the displayed scope. Approximate equality reflects rounded recorded factors.</p><h3>Combined estimates</h3><p>A pooled estimate requires a defined clinical question, compatible measures, appropriate uncertainty, and assessment of overlapping cohorts. Several results from one paper do not represent independent studies. The existing paper weights do not pool reported statistics or provide a validated clinical prediction score.</p></template>

`;

/** Render the shared evidence inside a site-owned host without fetching or remapping data. */
export function createEvidenceReview(host, options) {
  host.replaceChildren();
  const root=host.shadowRoot || host.attachShadow({mode:'open'});
  host.toggleAttribute('data-embedded',Boolean(options.embedded ?? options.onShowMap));
  options={...options,embedded:options.embedded ?? Boolean(options.onShowMap)};
  root.innerHTML='<style>'+styles+mobileStyles+'</style>'+markup;
  if(options.navigation){options.navigation.slot='organization';host.append(options.navigation);}
  if(options.filters){options.filters.slot='filters';host.append(options.filters);}
  if(options.actions){options.actions.slot='actions';host.append(options.actions);}
  if(options.embedded)root.querySelector('.list-meta').insertBefore(root.querySelector('[data-evidence-help]'),root.getElementById('reset'));

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
const metricName = value => metricNames[value] || words(value);
const metricTypesFor = atlasMetricTypes;
const sectionNames = {study:'Original study',review:'Review or guidance',background:'Cited or contextual',other:'Other evidence'};
const roleName = value => atlasEvidenceRoleLabel(value) || (publicSite ? '' : words(value));
function bibliography(id) { return sources.get(id)?.bibliography || {}; }
function classificationReference(id) { return sources.get(id)?.source_roles?.includes('CLASSIFICATION_REFERENCE') || false; }
function citation(id) {
  const source = sources.get(id), bib = bibliography(id), authors = parse(bib.authors_json) || [];
  const first = typeof authors[0] === 'string' ? authors[0] : authors[0]?.family_name || authors[0]?.display_name;
  return first ? `${first}${authors.length > 1 ? ' et al.' : ''}${bib.publication_year ? ', ' + bib.publication_year : ''}` : clean(bib.citation_text) || source?.label || 'Source document';
}
function paperCount(rows) { return new Set(rows.map(row => row.source.id)).size; }
function rowKinds(row) { return uniq((row.facets.evidence || []).map(value => atlasEvidenceSection(value.id))); }
function sourceTitle(id) { return sources.get(id)?.label || data.rows.find(row => row.source.id === id)?.source.title || 'Source document'; }
function rolePill(role) { const label=roleName(role); if(!label)return ''; const section = atlasEvidenceSection(role); return `<span class="pill ${section === 'review' ? 'review' : ['background','other'].includes(section) ? 'context' : ''}">${esc(label)}</span>`; }
function uncertainty(stat) {
  const scalar = value => value && typeof value === 'object' ? clean(value.value) : clean(value);
  const labels = {confidence_interval:'Confidence interval',ci:'Confidence interval',p_value:'P value',p:'P value',standard_error:'Standard error',standard_deviation:'Standard deviation',sd:'Standard deviation',range:'Range',interquartile_range:'Interquartile range',test_statistic:'Test statistic',other:'Other uncertainty'};
  const display = raw => {
    if (!clean(raw)) return [];
    const value = typeof raw === 'string' && /^[\[{]/.test(raw.trim()) ? parse(raw) : raw;
    if (value == null) return [];
    if (typeof value !== 'object') return [String(value)];
    if (Array.isArray(value)) return value.flatMap(display);
    if (clean(value.value_text)) {
      const text=clean(value.value_text),type=words(value.type || value.kind),level=scalar(value.level ?? value.confidence_level);
      const confidence=/confidence interval|\bci\b/i.test(type),label=confidence?[level && `${level}%`,'CI'].filter(Boolean).join(' '):type;
      return [label && !(confidence?/confidence interval|\bci\b/i.test(text):text.toLowerCase().includes(label.toLowerCase()))?`${label}: ${text}`:text];
    }
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
  const state = {query:params.get('q') || '',sourceQuery:'',organize:'sign',filters:{},order:'name',limit:30,focus:''};
  const opened = new Set(), bannerState = new Map(), expandedSections = new Set(), detailState = new Map(), weightIndex = new Map();
  let detailsReady = !data.details_url;
  let evidenceMap = publicSite ? {showEvidence: options.onShowMap, clear: () => options.onClearFilters?.()} : null, mapResultIds = null, dialogRows = [];
  let organization = '', currentView = '', signOrder = 'name', pendingFocus = '', selectedAnatomy = new Set(), selectedMetricIds = new Set(), classificationFilters = {}, sourceSelection = null;
  let groups = [], unplaced = [], entries = [], nodeIndex, nativeSigns, statOwners, queryRows = null;
  const axes = ['LOCALIZATION','LATERALIZATION'];
  const axisName = axis => axis === 'LOCALIZATION' ? 'Localization' : 'Lateralization';
  const option = (id,label) => `<option value="${esc(id)}">${esc(label)}</option>`;
  const paperIds = rows => uniq(rows.map(row => row.source.id));
  const termLabel = () => organization==='ilae' || organization==='region' && state.order==='ilae' ? 'ILAE' : organization==='luders' || organization==='region' && state.order==='luders' ? 'Lüders' : 'sign';
  const statisticsFor = rows => uniq(rows.flatMap(row => row.statistic_ids)).map(id => data.statistics[id]).filter(Boolean);
  const nativeIds = rows => uniq(rows.flatMap(row => row.facets.sign || []).map(item => item.id));
  const evidenceClassOrder = ['I','II','III','UNCLASSIFIED'];
  const classLabel = id => id === 'UNCLASSIFIED' ? 'Unclassified' : 'Class '+id;
  const classesFor = rows => uniq(rows.flatMap(row => row.facets.evidence_class?.length ? row.facets.evidence_class.map(item => item.id) : ['UNCLASSIFIED'])).sort((a,b) => evidenceClassOrder.indexOf(a)-evidenceClassOrder.indexOf(b) || a.localeCompare(b));
  const classMatches = (row,id) => !id || classesFor([row]).includes(id);
  const classOptions = ids => option('','All classes') + evidenceClassOrder.filter(id => ids.includes(id)).map(id => option(id,classLabel(id))).join('');
  const classRank = rows => Math.min(...classesFor(rows).map(id => { const rank=evidenceClassOrder.indexOf(id); return rank<0 ? Infinity : rank; }));
  const ownersFor = (stat,rows) => { const selected = new Set(rows.map(row => row.id)); return (statOwners.get(stat.statistic_id) || []).filter(row => selected.has(row.id)); };
  const findingRefFor = row => row.source.finding?.finding_ref || row.finding_ref || row.id;
  const findingSupportFor = stats => [...new Map(stats.flatMap(stat=>stat.finding_support || []).map(item=>[item.finding_ref,item])).values()];
  const selectedRows = rows => rows.filter(row => (!mapResultIds || mapResultIds.has(row.id)) && Object.entries(state.filters).every(([facet,id]) => ['ilae','luders'].includes(facet) || (facet === 'evidence_class' ? classMatches(row,id) : !id || (row.facets[facet] || []).some(item => item.id === id))));
  const valueText = stat => clean(stat.value_text) || String(stat.numeric_value ?? 'Not reported');
  const groupingRows = () => options.embedded ? queryRows || data.rows : atlasSearchRows(data.rows,state.query);
  function grouping() {
    ({groups,unplaced}=atlasNavigationGroups(groupingRows(),classificationFilters,catalogue.items));
  }
  function updateQuery() { if(options.embedded)return; const url = new URL(location.href); state.query ? url.searchParams.set('q',state.query) : url.searchParams.delete('q'); history.replaceState(null,'',url); }
  function setSourceQuery(value) { state.sourceQuery=value;state.focus='';state.limit=30;expandedSections.clear();opened.clear();updateQuery();renderList(); }
  function setEvidenceClass(value) { if(value)state.filters.evidence_class=value;else delete state.filters.evidence_class;for(const setting of detailState.values())setting.evidenceClass='';refresh(); }
  function syncControls() {
    const sourceMode = state.organize === 'source';
    $('organize').value = state.organize;
    const sourceCount=atlasCounts(data.rows).sources;
    $('corpus').innerHTML = sourceMode ? '' : `${number(groups.length)} ${termLabel()} terms · <button id="all-sources">${number(sourceCount)} ${sourceCount===1?'publication':'publications'}</button>`;
    $('order-label').textContent = sourceMode ? 'Sort papers' : 'Sort signs by';
    const sorts = sourceMode ? [['title','Title A–Z'],['name','Author A–Z'],['year','Newest first'],['class','Evidence class (I–III)']] : [['name','A–Z'],...(organization==='region'?[['ilae','ILAE'],['luders','Lüders']]:[]),['papers','Number of publications'],['class','Evidence class (I–III)']];
    if (!sorts.some(([id]) => id === state.order)) state.order = sourceMode ? 'title' : signOrder;
    $('order').innerHTML = sorts.map(([id,label]) => option(id,label)).join(''); $('order').value = state.order;
    $('evidence-class').innerHTML = classOptions(classesFor(data.rows)); $('evidence-class').value = state.filters.evidence_class || '';
    $('evidence-class-field').hidden = options.embedded;
    $('active-filters').innerHTML = Object.entries(state.filters).filter(([facet,id]) => id && facet !== 'evidence_class' && !['ilae','luders'].includes(facet)).map(([facet,id]) => `<button class="filter-chip" data-clear-filter="${esc(facet)}">${esc(nodeIndex.get(id)?.label || facet)} ×</button>`).join('');
    $('organize').closest('.field').hidden = options.embedded;
    $('search').closest('.field').hidden = options.embedded;
    $('search-label').textContent = sourceMode ? 'Search papers' : 'Search';
    $('search').placeholder = sourceMode ? 'Title, author or citation' : 'Sign or source wording';
    $('search').value = sourceMode ? state.sourceQuery : state.query;
    if (mapResultIds && !options.embedded) $('active-filters').insertAdjacentHTML('beforeend','<button class="filter-chip" data-clear-map>Map selection ×</button>');

  }
  function settings(id) { if (!detailState.has(id)) detailState.set(id,{metric:'',evidenceClass:'',papers:6,weights:'LOCALIZATION',openPapers:new Set(),controlsOpen:false}); return detailState.get(id); }
  function evidenceStats(rows,setting) {
    return statisticsFor(rows).filter(stat=>!setting.metric || stat.metric_type===setting.metric).sort((a,b)=>
      metricName(a.metric_type).localeCompare(metricName(b.metric_type)) || clean(a.unit).localeCompare(clean(b.unit)) || a.statistic_id.localeCompare(b.statistic_id));
  }
  function sourceMatches(id) {
    const query=state.sourceQuery.trim().toLocaleLowerCase();
    if(!query)return true;
    const bib=bibliography(id),authors=parse(bib.authors_json)||[];
    const names=authors.map(author=>typeof author==='string'?author:Object.values(author||{}).filter(value=>typeof value==='string').join(' ')).join(' ');
    return [sourceTitle(id),bib.title,bib.citation_text,names].some(value=>String(value||'').toLocaleLowerCase().includes(query));
  }
  function sourceGroups() {
    const rows=selectedRows(data.rows),groups=atlasGroups(rows,'source');
    const filtered=sourceSelection?.evidenceFiltered || selectedAnatomy.size || Object.entries(state.filters).some(([facet,id])=>id&&!['ilae','luders'].includes(facet));
    if(!filtered && (sourceSelection || rows.length===data.rows.length)) {
      const ids=new Set(groups.map(group=>group.id));
      for(const source of sources.values())if(classificationReference(source.id)&&!ids.has(source.id)&&(!sourceSelection?.sourceIds.length||sourceSelection.sourceIds.includes(source.id)))groups.push({id:source.id,label:source.label,rows:[]});
    }
    return groups;
  }
  function organizeEntries(selected, rows=[...new Map(selected.flatMap(group=>group.rows).map(row=>[row.id,row])).values()]) {
    const compare = (a,b) => (state.order==='papers'?paperIds(b.group.rows).length-paperIds(a.group.rows).length:state.order==='class'?classRank(a.group.rows)-classRank(b.group.rows):0) || a.group.label.localeCompare(b.group.label);
    const cards = (signs, banners = []) => signs.map(group=>({
      type:'sign',group,banners,key:banners.length?JSON.stringify([...banners.map(banner=>banner.key),group.id]):group.id
    })).sort(compare);
    const path = (nodes,facet,prefix=[]) => {
      let key=prefix.at(-1)?.key || '';
      return [...prefix,...nodes.map(node=>{
        key=(key?key+'/':'')+facet+':'+node.id;
        return {key,label:node.label,ordinal:facet==='region'?atlasRegionRank(node):node.ordinal};
      })];
    };
    const dictionaryCards = (rows,facet,prefix=[]) => {
      const {groups}=atlasDictionaryGroups(rows,facet,catalogue.items);
      const entries=groups.flatMap(group=>{
        const nodes=['TERM','TYPE'].includes(group.dictionary.kind)?group.path.slice(0,-1):group.path;
        return cards([group],path(nodes.filter(node=>node.kind!=='DESCRIPTOR_ROOT'),facet,prefix));
      });
      return entries.sort(compare);
    };
    if(['ilae','luders'].includes(organization))return dictionaryCards(rows,organization);
    if(organization!=='region')return cards(selected);
    if(['ilae','luders'].includes(state.order)){
      const regions=atlasGroups(rows,'region');
      for(const region of regions)if(!region.id)region.label='No linked region';
      return regions.flatMap(region=>dictionaryCards(region.rows,state.order,path([region],'region')));
    }
    return atlasSignSections(selected).flatMap(section=>{
      const banners=path([section],'region');
      return cards(section.groups,banners);
    });
  }
  function listMarkup() {
    const remaining=new Set();
    const render = (items,depth=0,banner=null) => {
      const direct=[],sections=new Map();
      for(const item of items){
        const banner=item.entry.banners?.[depth];
        if(!banner){direct.push(item);continue;}
        if(!sections.has(banner.key))sections.set(banner.key,{banner,items:[]});
        sections.get(banner.key).items.push(item);
      }
      const key=banner?.key || '',limit=expandedSections.has(key)?Infinity:state.limit;
      for(const {entry} of direct.slice(limit))remaining.add(entry.group.id);
      const cards=direct.slice(0,limit).map(({entry,index})=>entryMarkup(entry,index)).join('');
      const count=Math.max(0,direct.length-limit),kind=state.organize==='source'?'papers':'terms';
      const more=count?`<button class="more" data-more-section="${esc(key)}" aria-label="Show ${number(count)} remaining ${kind}${banner?' in '+esc(banner.label):''}">Show ${number(count)} remaining ${kind}</button>`:'';
      const children=[...sections.values()].sort((a,b)=>
        (a.banner.ordinal??Infinity)-(b.banner.ordinal??Infinity) || a.banner.label.localeCompare(b.banner.label));
      return children.map(({banner,items})=>{
        const signs=new Set(items.map(item=>item.entry.group.id)).size;
        const papers=paperIds(items.flatMap(item=>item.entry.group.rows)).length;
        const open=bannerState.get(banner.key) ?? Boolean(state.query.trim() || state.focus);
        return `<details class="sign-section" data-banner="${esc(banner.key)}" ${open?'open':''}><summary><strong>${esc(banner.label)}</strong><span>${number(signs)} ${signs===1?'term':'terms'} · ${number(papers)} ${papers===1?'paper':'papers'}</span></summary><div class="section-body">${render(items,depth+1,banner)}</div></details>`;
      }).join('')+cards+more;
    };
    return {html:render(entries.map((entry,index)=>({entry,index}))),remaining:remaining.size};
  }
  function renderList() {
    entries = [];
    if (state.organize === 'source') {
      entries = sourceGroups().filter(group => sourceMatches(group.id)).sort((a,b) => (state.order === 'year' ? (Number(bibliography(b.id).publication_year)||0)-(Number(bibliography(a.id).publication_year)||0) : state.order==='title'?sourceTitle(a.id).localeCompare(sourceTitle(b.id)):state.order==='class'?classRank(a.rows)-classRank(b.rows):0) || citation(a.id).localeCompare(citation(b.id))).map(group => ({type:'source',referenceOnly:!group.rows.length,group,key:'source:'+group.id}));
    } else {
      const selected = groups.map(group => ({...group,rows:selectedRows(group.rows)})).filter(group => group.rows.length && (!state.focus || group.id === state.focus));
      entries=organizeEntries(selected,state.focus?undefined:selectedRows(groupingRows()));
    }
    const rowSet = [...new Map(entries.flatMap(entry => entry.group.rows).map(row => [row.id,row])).values()];
    const extra = state.organize === 'source' || state.focus ? [] : selectedRows(groupingRows());
    const visibleRows = [...new Map([...rowSet,...extra].map(row=>[row.id,row])).values()];
    const publicationCount = paperIds(visibleRows).length;
    const termCount = new Set(entries.map(entry => entry.group.id)).size;
    $('corpus').hidden = options.embedded || state.organize === 'source' || (!state.query.trim() && !state.focus && !Object.values(state.filters).some(Boolean) && (!mapResultIds || mapResultIds.size === data.rows.length));
    const referenceCount=entries.filter(entry=>entry.referenceOnly).length;
    $('match-count').textContent = state.organize === 'source' ? [publicationCount?`${number(publicationCount)} evidence ${publicationCount===1?'publication':'publications'}`:'',referenceCount?`${number(referenceCount)} classification ${referenceCount===1?'reference':'references'}`:''].filter(Boolean).join(' · ') || '0 sources' : (termCount ? `${number(termCount)} ${termLabel()} ${termCount===1?'term':'terms'} · ` : '') + `${number(publicationCount)} ${publicationCount===1?'publication':'publications'} across Signs and Sources`;
    const list=listMarkup();
    $('sign-list').innerHTML = list.html || `<div class="empty">${state.organize==='source'?'No papers match this selection.':extra.length ? 'No sign terms match this selection. Papers are available in Sources.' : 'No sign terms match this selection.'}</div>`;
    root.querySelectorAll('.sign-card[open]').forEach(renderEntry);
    evidenceMap?.update?.(visibleRows);

  }
  function entryMarkup(entry,index) {
    const papers=paperIds(entry.group.rows).length;
    return `<details class="sign-card" data-entry="${index}" ${opened.has(entry.key)?'open':''}><summary><div class="sign-title"><strong>${esc(entry.type==='source'?sourceTitle(entry.group.id):entry.group.label)}</strong><span class="sign-meta">${entry.type==='source'?esc(citation(entry.group.id)):`${papers} ${papers===1?'paper':'papers'}`}</span>${entry.type==='source'&&classificationReference(entry.group.id)?'<span class="pill context">Classification reference</span>':''}</div></summary><div class="sign-body"></div></details>`;
  }
  function contexts(stat) {
    const metadata = value => clean(value).split(';').map(part => clean(part)).filter(Boolean).join('; ').replace(/\bNOT_REPORTED\b/g,'not available');
    const denominator = metadata(stat.denominator) || (stat.denominator_value != null ? String(stat.denominator_value) : '');
    return [['Population',metadata(stat.population)],['Subgroup',metadata(stat.subgroup)],['Analysis unit',metadata(stat.analysis_unit)],['Denominator',denominator],['Timepoint',metadata(stat.timepoint)],['Endpoint',metadata(stat.endpoint)],['Comparator',metadata(stat.comparator)]];
  }
  function paperResultGroups(rows,stats=[]) {
    const groups=new Map(),rowKeys=new Map(),attached=new Set();
    const add=(key,label)=>{if(!groups.has(key))groups.set(key,{label,rows:[],results:[]});return groups.get(key);};
    for(const row of rows){
      const signs=row.facets.sign || [],ids=uniq(signs.map(sign=>sign.id)).sort();
      const key=JSON.stringify([row.source.id,ids.length?ids:[row.finding_ref || row.id]]);
      rowKeys.set(row.id,key);
      add(key,uniq(signs.map(sign=>sign.label)).join(' · ') || row.term).rows.push(row);
    }
    for(const {statistic:stat,statements} of atlasStatisticGroups(stats)){
      const owners=ownersFor(stat,rows),keys=uniq(owners.map(row=>rowKeys.get(row.id))).sort();
      if(!owners.length)throw new Error('Reported statistic has no selected source owner');
      const group=keys.length===1?groups.get(keys[0]):add(JSON.stringify(keys),uniq(owners.flatMap(row=>(row.facets.sign || []).map(sign=>sign.label))).join(' · '));
      const support=findingSupportFor(statements);
      for(const item of support)attached.add(item.finding_ref);
      group.results.push({stat,rows:owners,support});
    }
    for(const group of groups.values()){
      const findings=new Map();
      for(const row of group.rows.filter(row=>!row.statistic_ids.length && !attached.has(findingRefFor(row)))){
        const key=findingRefFor(row);
        if(!findings.has(key))findings.set(key,[]);
        findings.get(key).push(row);
      }
      group.results.push(...[...findings.values()].map(rows=>({rows})));
      group.results.sort((a,b)=>Number(!a.stat)-Number(!b.stat) || locator(a.stat?.source_locator || a.rows[0].source.locator).localeCompare(locator(b.stat?.source_locator || b.rows[0].source.locator),undefined,{numeric:true}));
    }
    return [...groups.values()].sort((a,b)=>a.label.localeCompare(b.label));
  }
  function sourceTableGroups(groups,stats,rows) {
    const tables=[],used=new Set(),representatives=new Map(groups.flatMap(group=>group.results.filter(result=>result.stat).map(result=>[result.stat.statistic_id,result]))),results=new Map();
    for(const {statistic,statements} of atlasStatisticGroups(stats)){
      const representative=representatives.get(statistic.statistic_id);
      if(representative)for(const stat of statements)results.set(stat.statistic_id,{...representative,stat,rows:ownersFor(stat,rows),representative_id:statistic.statistic_id});
    }
    for(const sourceId of uniq(groups.flatMap(group=>group.rows.map(row=>row.source.id))))for(const table of data.result_tables?.[sourceId] || []){
      const rowIds=new Set(table.rows?.map(row=>row.row_id)),columnIds=new Set(table.columns?.map(column=>column.column_id)),positions=new Set();
      if(!table.table_id || !table.source_sha256 || !table.source_report_sha256 || !table.report_unit_id || !table.rows?.length || !table.columns?.length || !Array.isArray(table.cells) || rowIds.size!==table.rows.length || columnIds.size!==table.columns.length || table.rows.some(row=>!row.row_id || !clean(row.label)) || table.columns.some(column=>!column.column_id || !clean(column.label)))throw new Error('Source table layout is incomplete');
      let version;
      for(const cell of table.cells){
        const stat=data.statistics[cell.statistic_id],position=JSON.stringify([cell.row_id,cell.column_id]);
        if(!rowIds.has(cell.row_id) || !columnIds.has(cell.column_id) || positions.has(position) || used.has(cell.statistic_id) || !stat || ['source_sha256','source_report_sha256','report_unit_id'].some(key=>stat[key]!==table[key]) || version && version!==stat.source_version_role)throw new Error('Source table cell changes source, version or measurement ownership');
        const owners=statOwners.get(cell.statistic_id) || [];
        if(owners.some(row=>row.source.id!==sourceId || row.source.finding?.source_sha256!==stat.source_sha256))throw new Error('Source table cell belongs to a different paper');
        positions.add(position);used.add(cell.statistic_id);version=stat.source_version_role;
      }
      for(const note of table.footnotes || [])if((note.row_ids || []).some(id=>!rowIds.has(id)) || (note.column_ids || []).some(id=>!columnIds.has(id)))throw new Error('Source table footnote changes its scope');
      const cells=table.cells.filter(cell=>results.has(cell.statistic_id));
      if(cells.length)tables.push({table,cells,results,first:groups.findIndex(group=>group.results.some(result=>cells.some(cell=>results.get(cell.statistic_id).representative_id===result.stat?.statistic_id)))});
    }
    return tables;
  }
  function compactStatisticValue(stat,raw=stat.value_text){
    const text=clean(raw);if(!/\d/.test(text))return '';
    const labels=[metricName(stat.metric_type),clean(stat.unit),'confidence interval','reported interval','interquartile range','standard deviation','standard error','p value','range','mean','median','approximately','approx.','about','above','below','at least','at most','more than','less than','up to','patients','patient','seizures','seizure','cases','case','s','ms','sec','min','h','Hz','mm','cm','years','year','months','month','days','day','seconds','second','OR','RR','HR','CI','SD','SE','SEM','p','n'].filter(Boolean).sort((a,b)=>b.length-a.length);
    let remainder=text;
    for(const label of labels)remainder=remainder.replace(new RegExp('(?<![A-Za-z])'+label.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(?![A-Za-z])','gi'),'');
    if(/^[\d\s.,;:+\-−–—<>≤≥=~≈±%()\[\]/×*^eE]+$/.test(remainder))return text;
    const unit=clean(stat.unit).replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),number='[+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][+-]?\\d+)?';
    const pattern=new RegExp('(?<![A-Za-z0-9])((?:(?:approximately|about|above|below|at least|at most|more than|less than|up to)\\s+)?(?:[<>≤≥~≈]\\s*)?('+number+')(?:\\s*/\\s*('+number+'))?(?:\\s*(?:±|[-−–])\\s*'+number+')?(?:\\s*(?:%'+(unit?'|'+unit:'')+'))?(?:\\s*\\(\\s*('+number+')\\s*%\\s*\\))?)','gi');
    for(const match of text.matchAll(pattern)){
      if(/^\s*(?:[-−–±/×*]|to\b)/i.test(text.slice(match.index+match[0].length)))continue;
      const matches=match[3]?Number(match[2])===stat.numerator_value && Number(match[3])===stat.denominator_value:Number(match[2])===stat.numeric_value;
      if(matches || match[4] && Number(match[4])===stat.numeric_value)return match[1].trim();
    }
    return '';
  }
  function compactStatisticMarkup(stat,label,{metric=true}={}){
  const value=compactStatisticValue(stat),qualifiers=uncertainty(stat).split('; ').map(text=>compactStatisticValue(stat,text)).filter(Boolean).join('; '),name=metric && value?metricName(stat.metric_type):'';
  return `<button class="${value?'result-number':'text-button'}" data-stat="${esc(stat.statistic_id)}" aria-label="${esc(label+' — Source details')}">${esc(value || 'Source details')}</button>${name && name!=='Other'?`<small>${esc(name)}</small>`:''}${qualifiers?`<small>${esc(qualifiers)}</small>`:''}`;
  }
  function compactReportedAxes(rows){
    const filtered=rows.map(row=>({...row,source_anatomy:(row.source_anatomy || []).filter(value=>atlasResolvedAxis(value) && !['COHORT_CONTEXT','COMPARATOR_CONTEXT'].includes(value.role) && value.decision_role!=='CONTEXT' && (!value.scope || value.scope==='EXACT')),source_laterality:(row.source_laterality || []).filter(value=>atlasResolvedAxis(value) && !['COHORT_CONTEXT','COMPARATOR_CONTEXT'].includes(value.role) && value.decision_role!=='CONTEXT' && (!value.scope || value.scope==='EXACT'))}));
    return atlasSourceFindingsMarkup(filtered,{compact:true,omitHeadings:rows.map(row=>row.term)});
  }
  function sourceTableMarkup({table,cells,results}){
  const tableRows=table.rows.filter(row=>cells.some(cell=>cell.row_id===row.row_id)),columns=table.columns.filter(column=>cells.some(cell=>cell.column_id===column.column_id));
  const raw=parse(table.source_locator),locators=(Array.isArray(raw)?raw:[raw]).filter(value=>value && typeof value==='object'),title=uniq(locators.map(value=>clean(value.object)).filter(Boolean)).join(' · ') || 'Reported statistics',pages=uniq(locators.filter(value=>value.page!=null).map(value=>'p. '+value.page)).join('; ');
  const items=cells.map(cell=>results.get(cell.statistic_id)),ownerKey=result=>JSON.stringify(result.rows.map(row=>row.id).sort()),sharedOwners=items.every(result=>ownerKey(result)===ownerKey(items[0]));
    return `<section class="source-table"><h4>${esc(title)}${pages?` <small>${esc(pages)}</small>`:''}</h4>${sharedOwners?compactReportedAxes(items[0].rows):''}<div class="source-table-region" role="region" aria-label="${esc(title)}" tabindex="0"><table class="source-comparison" data-source-table="${esc(table.table_id)}"><thead><tr><th scope="col">${esc(clean(table.row_header) || 'Finding / group')}</th>${columns.map(column=>`<th scope="col">${esc(column.label)}</th>`).join('')}</tr></thead><tbody>${tableRows.map(row=>`<tr><th scope="row">${esc(row.label)}${!sharedOwners?compactReportedAxes(uniq(cells.filter(cell=>cell.row_id===row.row_id).flatMap(cell=>results.get(cell.statistic_id).rows))):''}</th>${columns.map(column=>{
    const cell=cells.find(cell=>cell.row_id===row.row_id && cell.column_id===column.column_id);if(!cell)return '<td aria-label="No result in the selected evidence">—</td>';
    const result=results.get(cell.statistic_id),stat=result.stat;
    return `<td data-statistic="${esc(stat.statistic_id)}" data-source-row="${esc(row.row_id)}" data-source-column="${esc(column.column_id)}" data-result-owners="${esc(JSON.stringify(result.rows.map(owner=>owner.id)))}">${compactStatisticMarkup(stat,row.label+', '+column.label,{metric:false})}</td>`;
  }).join('')}</tr>`).join('')}</tbody></table></div></section>`;
  }
  function resultsMarkup(stats,rows){
    const groups=paperResultGroups(rows,stats).filter(group=>group.results.length);if(!groups.length)return '';
    const tables=sourceTableGroups(groups,stats,rows),tableIds=new Set(tables.flatMap(({cells,results})=>cells.map(cell=>results.get(cell.statistic_id).representative_id))),pieces=[],ordinary=[];
    const flush=()=>{if(ordinary.length)pieces.push(`<div class="source-table-region"><table class="result-table"><thead><tr><th>Statistic</th><th>Result</th></tr></thead><tbody>${ordinary.splice(0).join('')}</tbody></table></div>`);};
    for(const [index,group] of groups.entries()){
      const sourceTables=tables.filter(table=>table.first===index).map(sourceTableMarkup).join('');if(sourceTables){flush();pieces.push(sourceTables);}
      const ownedGroups=new Map();
      for(const result of group.results.filter(result=>!tableIds.has(result.stat?.statistic_id))){
        const key=JSON.stringify([result.rows.map(owner=>owner.id).sort(),clean(result.stat?.subgroup)]);
        if(!ownedGroups.has(key))ownedGroups.set(key,[]);
        ownedGroups.get(key).push(result);
      }
      for(const results of ownedGroups.values()){
        const owners=results[0].rows,signs=uniq(owners.flatMap(row=>(row.facets.sign || []).map(sign=>sign.label))),finding=signs.join(' · ') || uniq(owners.map(row=>row.term)).join(' · ') || 'Reported finding',subgroup=clean(results[0].stat?.subgroup),label=uniq([finding,subgroup].filter(Boolean)).join(' · ');
        const endpoints=uniq(results.map(result=>clean(result.stat?.endpoint))),sharedEndpoint=endpoints.length===1?endpoints[0]:'',briefEndpoint=endpoint=>endpoint && !label.toLocaleLowerCase().includes(endpoint.toLocaleLowerCase()) && !/[.;!?\n]/.test(endpoint)?endpoint:'';
        ordinary.push(`<tr class="result-finding-header" data-finding-owners="${esc(JSON.stringify(owners.map(row=>row.id).sort()))}" data-subgroup="${esc(subgroup)}"><td colspan="2"><strong>${esc(label)}</strong>${briefEndpoint(sharedEndpoint)?`<small>${esc(sharedEndpoint)}</small>`:''}${compactReportedAxes(owners)}</td></tr>`);
        for(const {stat,rows:resultOwners} of results){
          const endpoint=clean(stat?.endpoint),name=stat?metricName(stat.metric_type):'',metric=name==='Other'?'':name,detailLabel=uniq([label,metric,endpoint].filter(Boolean)).join(' · '),endpointLabel=!sharedEndpoint?briefEndpoint(endpoint):'';
          const details=stat?compactStatisticMarkup(stat,detailLabel,{metric:false}):`<button class="text-button" data-findings="${esc(JSON.stringify(resultOwners.map(row=>row.id)))}">Source details</button>`;
          ordinary.push(`<tr${stat?` data-statistic="${esc(stat.statistic_id)}"`:''} data-result-owners="${esc(JSON.stringify(resultOwners.map(row=>row.id)))}"><td>${metric?`<strong>${esc(metric)}</strong>`:''}${endpointLabel?`<small>${esc(endpointLabel)}</small>`:''}</td><td>${details}</td></tr>`);
        }
      }
    }
    flush();return pieces.join('');
  }

  function sourceTableDetails(stat){
  return Object.values(data.result_tables || {}).flat().flatMap(table=>table.cells.filter(cell=>cell.statistic_id===stat.statistic_id).map(cell=>{
    const row=table.rows.find(row=>row.row_id===cell.row_id),column=table.columns.find(column=>column.column_id===cell.column_id),sourceLocator=locator(Array.isArray(table.source_locator)?table.source_locator:[table.source_locator]);
    const notes=(table.footnotes || []).filter(note=>(!note.row_ids?.length || note.row_ids.includes(cell.row_id)) && (!note.column_ids?.length || note.column_ids.includes(cell.column_id)));
    return `<h3>${esc(clean(table.caption) || sourceLocator || 'Source table')}</h3><p>${esc([row?.label,column?.label,sourceLocator].filter(Boolean).join(' · '))}</p>${notes.map(note=>`<p>${esc(note.text)}</p>`).join('')}`;
  })).join('');
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
  function contributionPresentation(current,axis) {
    const view=atlasWeightPresentation(current,axis);
    return {...view,applied:/UNRESOLVED/.test(current.weight_status||'')?'Not assigned':view.applied};
  }
  function currentWeightMarkup(value,axis) {
    return value.current.map(current=>{
      const view=contributionPresentation(current,axis);
      return `<p><strong>${esc(current.label)}</strong>: ${esc(view.applied)}${view.reason?`<br>${esc(view.reason)}`:''}</p>`;
    }).join('');
  }
  function paperWeights(rows,sourceId,setting,groupId) {
    const records = weightRows(rows,sourceId,setting); if (!records.length) return '';
    const scoped=records.filter(item=>!item.context),context=records.filter(item=>item.context);
    const signLabel=item=>uniq(axes.flatMap(axis=>{const value=item.values[axis],sign=value?.appraisal?nodeIndex.get(value.original_sign_id):null;return sign?.facet==='sign'?[sign.label]:[];})).join(' · ') || item.label;
    const table=scoped.map(item=>`<tr><td>${esc(signLabel(item))}</td>${axes.map(axis=>{
      const value=item.values[axis];if(!value)return '<td>—</td>';
      const view=atlasWeightPresentation(value,axis);
      const applied=uniq(value.current.map(current=>contributionPresentation(current,axis).applied));
      const contribution=applied.length>1?'See individual contributions':value.current.length>1?`Each: ${applied[0]}`:applied[0] || '—';
      return `<td${value.appraisal?` data-appraisal="${esc(value.id)}"`:''}><small>Appraised weight</small><strong>${esc(view.label)}</strong>${['I','II','III'].includes(value.evidence_class)?`<small>${esc(classLabel(value.evidence_class))}</small>`:''}<small>Applied contribution</small><span>${esc(contribution)}</span></td>`;
    }).join('')}</tr>`).join('');
    const details=scoped.map(item=>`<section class="calculation-line"><strong>${esc(signLabel(item))}</strong><details><summary>Source wording</summary><p>${esc(item.label)}</p></details>${axes.filter(axis=>item.values[axis]).map(axis=>{
      const value=item.values[axis],view=atlasWeightPresentation(value,axis);
      return `<section><h5>${axisName(axis)}</h5><p>Appraised weight: ${esc(view.label)}${['I','II','III'].includes(value.evidence_class)?` · ${esc(classLabel(value.evidence_class))}`:''}</p>${view.label==='—'&&view.reason?`<p>${esc(view.reason)}</p>`:''}${view.calculation?`<p>${esc(view.calculation)}</p>`:''}${!publicSite&&value.appraisal&&value.original_sign_label?`<p>Original database label: ${esc(value.original_sign_label)}</p>`:''}<h5>Applied contribution</h5>${currentWeightMarkup(value,axis)}</section>`;
    }).join('')}</section>`).join('');
    const other=context.length?`<details class="calculation"><summary>Appraisals for other signs in this paper</summary>${context.map(item=>`<section class="calculation-line"><strong>${esc(signLabel(item))}</strong><details><summary>Source wording</summary><p>${esc(item.label)}</p></details>${axes.filter(axis=>item.values[axis]).map(axis=>{const value=item.values[axis],view=atlasWeightPresentation(value,axis);return `<section data-context-appraisal="${esc(value.id)}"><h5>${axisName(axis)}</h5><p>Appraised weight: ${esc(view.label)}${['I','II','III'].includes(value.evidence_class)?` · ${esc(classLabel(value.evidence_class))}`:''}</p>${!publicSite&&value.original_sign_label?`<details><summary>Original database label</summary><p>${esc(value.original_sign_label)}</p></details>`:''}</section>`;}).join('')}</section>`).join('')}</details>`:'';
    return `<details class="context-details paper-weights"><summary>Evidence weights</summary><table class="weight-table"><thead><tr><th>Assessed sign</th>${axes.map(axis=>`<th>${options.embedded?axisName(axis):`<button data-weight-order="${axis}" data-group="${esc(groupId)}" title="Order by ${axisName(axis).toLowerCase()} appraised weight">${axisName(axis)} ↓</button>`}</th>`).join('')}</tr></thead><tbody>${table}</tbody></table><details class="calculation"><summary>Calculation details</summary>${details}</details>${other}</details>`;
  }
  function findingsMarkup(rows) {
    return atlasSourceFindingGroups(rows).map(row=>{
      const statement=clean(row.source.finding?.statement) || clean(row.source.excerpt);
      const passages=uniq([row.source.excerpt,...(row.source_passages || []).map(value=>value.excerpt),...(row.source_anatomy || []).map(value=>value.source_excerpt),...(row.source_laterality || []).map(value=>value.source_excerpt)].map(clean).filter(Boolean));
      const excerpts=passages.filter(text=>text!==statement && !passages.some(other=>other!==text && other.includes(text)));
      const sourceWording=uniq([...(row.source_anatomy || []),...(row.source_laterality || [])].map(value=>clean(value.source_term)).filter(Boolean)).filter(text=>!statement.includes(text) && !passages.some(passage=>passage.includes(text)));
      const pending=publicSite?[['Reported anatomy',row.source_anatomy || []],['Reported side',row.source_laterality || []]].map(([label,values])=>[label,uniq(values.filter(value=>!atlasResolvedAxis(value)).map(value=>clean(value.source_term)).filter(Boolean))]).filter(([,terms])=>terms.length).map(([label,terms])=>`<p><strong>${label}:</strong> ${esc(terms.join('; '))}</p>`).join(''):'';
      const locators=uniq([row.source.locator,...(row.source_passages || []).map(value=>value.locator),...(row.source_anatomy || []).map(value=>value.locator),...(row.source_laterality || []).map(value=>value.locator)].map(atlasSourceLocator).filter(Boolean));
      return `<article class="finding"><h4>${esc(row.term)}</h4>${statement?`<p>${esc(statement)}</p>`:''}${excerpts.map(text=>`<blockquote>${esc(text)}</blockquote>`).join('')}${pending}${!publicSite&&sourceWording.length?`<p>Source wording: ${esc(sourceWording.join('; '))}</p>`:''}<p>${esc(locators.join('; '))}</p></article>`;
    }).join('');
  }
  function sourceLink(id) { const doi=clean(bibliography(id).doi); return doi ? `<a href="https://doi.org/${esc(encodeURI(doi))}" target="_blank" rel="noopener">Publication ↗</a>` : ''; }
  function localizationAnnotation(row,value) {
    const matches=(row.facets.anatomy || []).filter(item=>selectedAnatomy.has(item.id) && item.source_item_id===value.target_id && item.source_term===value.source_term && item.role===value.role);
    const exact=new Set(matches.filter(item=>item.scope==='EXACT').map(item=>item.id));
    const labels=uniq(matches.filter(item=>item.scope==='OVERLAP' && !exact.has(item.id)).map(item=>item.label).filter(Boolean));
    return labels.length ? `Anatomical overlap · ${labels.join('; ')}` : '';
  }
  function paperPresentation(document) {
    const plan=document.presentation;
    return plan?.schema_version==='paper-presentation-1.0.0' && plan.source_sha256===document.source_sha256 && plan.source_version_role===document.version_role?plan:null;
  }
  function paperOverview(id,rows) {
    const sourceSHAs=new Set(rows.map(row=>row.source.finding?.source_sha256));
    const documents=(bibliography(id).document_overviews || []).filter(document=>sourceSHAs.has(document.source_sha256));
    const canonical=documents.filter(document=>document.version_role==='CANONICAL_REVIEWED_VERSION'),overviews=canonical.length?canonical:documents;
    const summaries=overviews.flatMap(document=>{const plan=paperPresentation(document);return plan?plan.sections.filter(section=>section.placement==='MAIN').map(section=>clean(section.summary)):[clean(document.summary)].filter(summary=>summary.toLocaleLowerCase()!==clean(sourceTitle(id)).toLocaleLowerCase());});
    const paragraphs=uniq(summaries.filter(Boolean).flatMap(summary=>summary.split(/\n\s*\n/)).map(paragraph=>paragraph.trim()));
    return paragraphs.length?'<section class="paper-summary"><h4>Summary of findings</h4>'+paragraphs.map(paragraph=>'<p>'+esc(paragraph)+'</p>').join('')+'</section>':'';
  }
  function openFindingDetails(rows,statisticIds=[]) {
    const stats=statisticIds.map(id=>data.statistics[id]);
    if(stats.some(stat=>!stat))throw new Error('Source details reference a missing reported result');
    openDialog('Source details',(stats.length?resultsMarkup(stats,rows):'')+findingsMarkup(rows,{support:true}));
  }
  function qualitativeResultsMarkup(rows) {
    return paperResultGroups(rows).filter(group=>group.results.length).map(group=>'<div class="paper-finding"><strong>'+esc(group.label)+'</strong>'+compactReportedAxes(group.rows)+'<button class="text-button" data-findings="'+esc(JSON.stringify(group.rows.map(row=>row.id)))+'">Source details</button></div>').join('');
  }
  function paperResults(id,stats,rows) {
    const sourceSHAs=new Set(rows.map(row=>row.source.finding?.source_sha256));
    const documents=(bibliography(id).document_overviews || []).filter(document=>sourceSHAs.has(document.source_sha256));
    const plans=documents.filter(paperPresentation);
    if(!plans.length)return resultsMarkup(stats,rows);
    const groups=atlasStatisticGroups(stats),selected=new Map(groups.flatMap(group=>group.statements.map(stat=>[stat.statistic_id,group]))),assigned=new Map(),seenFindings=new Set(),sections=[];
    for(const document of plans){
      const plan=document.presentation,bound=stat=>{
        const binding=plan.statistic_bindings?.[stat.statistic_id] || data.presentation?.statistic_bindings?.[stat.statistic_id] || stat;
        if(!['source_sha256','source_report_sha256','source_version_role'].every(key=>binding[key]===plan[key]) || !['source_sha256','source_version_role'].every(key=>stat[key]==null || stat[key]===binding[key]))return false;
        return stat.source_report_sha256==null || stat.source_report_sha256===binding.source_report_sha256 || stat.source_report_sha256===binding.retained_source_report_sha256 && (plan.report_lineage || []).some(lineage=>lineage.prior_report_sha256===stat.source_report_sha256 && lineage.current_report_sha256===plan.source_report_sha256 && lineage.statistics.some(item=>item.statistic_id===stat.statistic_id && item.finding_ref===stat.finding_ref));
      };
      for(const section of plan.sections)for(const id of section.statistic_ids){
        const group=selected.get(id);if(!group)continue;
        if(!bound(data.statistics[id]))throw new Error('Paper section changes source or report ownership');
        const prior=assigned.get(group);
        if(!prior || section.placement==='MAIN' && prior.placement!=='MAIN')assigned.set(group,section);
      }
      for(const section of plan.sections){
        const sectionGroups=new Set();
        for(const id of section.statistic_ids){
          const group=selected.get(id);if(!group)continue;
          if(!bound(data.statistics[id]))throw new Error('Paper section changes source or report ownership');
          if(assigned.get(group)===section)sectionGroups.add(group);
        }
        const refs=new Set(section.finding_refs),qualitative=rows.filter(row=>row.source.finding?.source_sha256===plan.source_sha256 && !row.statistic_ids.length && refs.has(findingRefFor(row)) && !seenFindings.has(findingRefFor(row)));
        for(const row of qualitative)seenFindings.add(findingRefFor(row));
        const sectionStats=[...sectionGroups].flatMap(group=>group.statements),owners=new Set(sectionStats.flatMap(stat=>ownersFor(stat,rows).map(row=>row.id))),sectionRows=rows.filter(row=>owners.has(row.id) || qualitative.includes(row));
        if(sectionRows.length)sections.push({...section,stats:sectionStats,rows:sectionRows,overview:document.summary});
      }
    }
    for(const table of data.result_tables?.[id] || []){
      const placements=new Set(table.cells.filter(cell=>selected.has(cell.statistic_id)).map(cell=>assigned.get(selected.get(cell.statistic_id)) || null));
      if(placements.size>1)throw new Error('Source table is split across paper sections');
    }
    const remainderStats=groups.filter(group=>!assigned.has(group)).flatMap(group=>group.statements),remainderOwners=new Set(remainderStats.flatMap(stat=>ownersFor(stat,rows).map(row=>row.id)));
    const remainderRows=rows.filter(row=>remainderOwners.has(row.id) || !row.statistic_ids.length && !seenFindings.has(findingRefFor(row)));
    const supporting=remainderRows.length?'<div class="paper-source-details"><button class="text-button" data-findings="'+esc(JSON.stringify(remainderRows.map(row=>row.id)))+'" data-statistics="'+esc(JSON.stringify(remainderStats.map(stat=>stat.statistic_id)))+'">Source details for additional results</button></div>':'';
    const render=section=>{
      const summary=clean(section.summary),overview=clean(section.overview),distinct=section.placement!=='MAIN' && summary && summary!==overview && !overview.split(/\n\s*\n/).includes(summary);
      return '<section class="paper-topic" data-paper-section="'+esc(section.section_id)+'" tabindex="-1"><h4>'+esc(section.heading)+'</h4>'+(distinct?'<p>'+esc(summary)+'</p>':'')+(section.stats.length?resultsMarkup(section.stats,section.rows):qualitativeResultsMarkup(section.rows))+'</section>';
    };
    const main=sections.filter(section=>section.placement==='MAIN'),additional=sections.filter(section=>section.placement==='SECONDARY');
    const navigation=sections.length>1?'<nav class="paper-topics" aria-label="Topics in this paper">'+sections.map(section=>'<button class="text-button" data-paper-topic="'+esc(section.section_id)+'">'+esc(section.heading)+'</button>').join('')+'</nav>':'';
    return navigation+main.map(render).join('')+(additional.length?'<details class="paper-additional"><summary>Additional results</summary>'+additional.map(render).join('')+'</details>':'')+supporting;
  }
  function paperContent(id,rows,setting,groupId,embedded) {
    const roles=uniq(rows.flatMap(row=>(row.facets.evidence || []).map(item=>item.id.replace(/^EVIDENCE:/,''))));
    const evidenceClasses=classesFor(rows).map(classLabel).join(' · ');
    const stats=evidenceStats(rows,setting).filter(stat=>!selectedMetricIds.size || selectedMetricIds.has('METRIC:'+stat.metric_type));
    return `${embedded?`<div class="paper-tools"><span class="evidence-class-label">${esc(evidenceClasses)}</span>${roles.map(rolePill).join(' ')}</div>`:''}<div class="paper-links">${sourceLink(id)}${publicSite?`<button class="text-button map-link" data-show-map="${esc(groupId)}" data-map-source="${esc(id)}">Show on map</button>`:''}</div>${paperOverview(id,rows)}${paperResults(id,stats,rows)}${paperWeights(rows,id,setting,groupId)}`;
  }
  function paperMarkup(id,rows,setting,groupId,embedded=false) {
    const roles=uniq(rows.flatMap(row=>(row.facets.evidence || []).map(item=>item.id.replace(/^EVIDENCE:/,''))));
    const evidenceClasses=classesFor(rows).map(classLabel).join(' · ');
    const body=`<div class="paper-content" data-evidence-paper="${esc(id)}" tabindex="0" role="region" aria-label="${esc(citation(id))}: evidence"></div>`;
    return embedded ? body : `<details class="paper" data-paper="${esc(id)}" data-group="${esc(groupId)}" ${setting.openPapers?.has(id)?'open':''}><summary><div class="paper-title"><h3>${esc(sourceTitle(id))}</h3><p>${esc(citation(id))}</p><div class="paper-tools"><span class="evidence-class-label">${esc(evidenceClasses)}</span>${roles.map(rolePill).join(' ')}</div></div></summary>${body}</details>`;
  }
  function indexWeights() {
    weightIndex.clear();
    for(const axis of axes)for(const summary of data.weights?.[axis]||[]){if(!weightIndex.has(summary.sign_id))weightIndex.set(summary.sign_id,new Map());weightIndex.get(summary.sign_id).set(axis,summary);}
  }
  async function renderPaper(body) {
    if(!body || ['loading','loaded'].includes(body.dataset.load))return;
    const card=body.closest('.sign-card'),paper=body.closest('.paper'),entry=entries[Number(card?.dataset.entry)];
    if(!entry || !card.open || paper && !paper.open)return;
    const setting=settings(entry.group.id),id=body.dataset.evidencePaper;
    const rows=entry.group.rows.filter(row=>row.source.id===id && classMatches(row,setting.evidenceClass));
    body.dataset.load='loading';body.setAttribute('aria-busy','true');
    try {
      if(!detailsReady){
        body.innerHTML=paperOverview(id,rows)+'<p role="status">Loading evidence…</p>';
        await atlasLoadDetails(data,id);
        indexWeights();detailsReady=!data.details_url;
      }
      delete body.dataset.load;
      if(!body.isConnected || !card.open || paper && !paper.open)return;
      body.innerHTML=paperContent(id,rows,setting,entry.group.id,entry.type==='source');
      body.dataset.load='loaded';
    } catch(error) {
      delete body.dataset.load;
      if(body.isConnected)body.innerHTML=paperOverview(id,rows)+'<p role="alert">Evidence details could not be loaded.</p><button class="text-button" data-retry-evidence>Retry loading evidence</button>';
      console.error('Evidence details could not be loaded',error);
    } finally { body.removeAttribute('aria-busy'); }
  }
  function signBody(group,embedded=false) {
    const setting=settings(group.id),rowsForClass=group.rows.filter(row=>classMatches(row,setting.evidenceClass)),allStats=statisticsFor(rowsForClass),types=metricTypesFor([...allStats,...(setting.metric?[{metric_type:setting.metric}]:[])]);
    let stats=evidenceStats(rowsForClass,setting).filter(stat=>!selectedMetricIds.size || selectedMetricIds.has('METRIC:'+stat.metric_type)),ids=paperIds(rowsForClass);
    if (selectedMetricIds.size || setting.metric) { const included=new Set(stats.flatMap(stat=>paperIds(ownersFor(stat,rowsForClass)))); ids=ids.filter(id=>included.has(id)); }
    ids.sort((a,b)=>(state.order==='class' ? classRank(rowsForClass.filter(row=>row.source.id===a))-classRank(rowsForClass.filter(row=>row.source.id===b)) : 0) || citation(a).localeCompare(citation(b)));
    const refinements=[setting.metric?metricName(setting.metric):'',setting.evidenceClass?classLabel(setting.evidenceClass):''].filter(Boolean);
    const controls=options.embedded?'':`<details class="result-refinements" data-group="${esc(group.id)}" ${setting.controlsOpen?'open':''}><summary>Refine this ${embedded?'paper':'sign'}'s results${refinements.length?`<span class="refinement-state"> · ${refinements.map(esc).join(' · ')}</span>`:''}</summary><div class="inside-controls dictionary-controls paper-controls" data-paper-count="${ids.length}"><div class="field"><label>Reported statistic</label><select data-detail="metric" data-group="${esc(group.id)}" aria-label="Reported statistic">${[['','All statistics'],...types.map(type=>[type,metricName(type)])].map(([id,label])=>`<option value="${esc(id)}" ${setting.metric===id?'selected':''}>${esc(label)}</option>`).join('')}</select></div><div class="field"><label>Evidence class</label><select data-detail="evidenceClass" data-group="${esc(group.id)}" aria-label="Study evidence class">${[['','All classes'],...classesFor(group.rows).map(id=>[id,classLabel(id)])].map(([id,label])=>`<option value="${esc(id)}" ${setting.evidenceClass===id?'selected':''}>${esc(label)}</option>`).join('')}</select></div></div></details>`;
    const fullGroup=group.dictionary?null:groups.find(item=>item.id===group.id),fullRows=(fullGroup ? selectedRows(fullGroup.rows) : group.rows).filter(row=>classMatches(row,setting.evidenceClass));
    const expand=state.query.trim() && fullRows.length>rowsForClass.length ? `<button class="text-button" data-all-term="${esc(group.id)}">View all ${paperIds(fullRows).length} papers for this term</button>` : '';
    return {paperCount:ids.length,html:expand + controls + (publicSite && !embedded?`<button class="text-button map-link" data-show-map="${esc(group.id)}">Show on map</button>`:'') + ids.slice(0,setting.papers).map(id=>paperMarkup(id,rowsForClass.filter(row=>row.source.id===id),setting,group.id,embedded)).join('') + (ids.length>setting.papers ? `<button class="more" data-more-papers="${esc(group.id)}">Show ${ids.length-setting.papers} remaining papers</button>` : '') + (!ids.length ? '<p class="empty">No papers match the selected filters.</p>' : '')};
  }
  function entryBody(entry) { return entry.referenceOnly?{html:`<div class="paper-links">${sourceLink(entry.group.id)}</div>`,paperCount:0}:signBody(entry.group,entry.type==='source'); }
  function renderEntry(card) { const entry=entries[Number(card.dataset.entry)]; if (!entry || !card.open) return; const body=entryBody(entry);card.querySelector('.sign-body').innerHTML=body.html; if(entry.type==='sign'){const count=body.paperCount,total=paperIds(entry.group.rows).length;card.querySelector('.sign-meta').textContent=count<total ? `${count} of ${total} papers` : `${count} ${count===1?'paper':'papers'}`;} card.dataset.loaded='true';card.querySelectorAll('.paper-content').forEach(renderPaper); }
  function refreshGroup(id) { root.querySelectorAll('.sign-card[open]').forEach(card=>{if(entries[Number(card.dataset.entry)]?.group.id===id)renderEntry(card);}); }
  function openDialog(title,body,rows=[]) { dialogRows=rows; $('dialog-title').textContent=title; $('dialog-body').innerHTML=body; $('record-dialog').showModal(); $('record-dialog').scrollTop=0; }
  function openStatistic(id) {
    const stat=data.statistics[id]; if(!stat)return; const rows=statOwners.get(id)||[];
    const statements=atlasStatisticGroups(Object.values(data.statistics)).find(group=>group.statistic.statistic_id===id)?.statements || [stat];
    const fields=[...(metricName(stat.metric_type)?[['Statistic',metricName(stat.metric_type)]]:[]),['Reported measure',stat.measure],['Numerator',clean(stat.numerator)||stat.numerator_value],...contexts(stat),['Reported unit',stat.unit],['Phase',stat.phase],['Anatomy / laterality',stat.anatomy_laterality_context],['Uncertainty',uncertainty(stat)],['Source',roleName(stat.evidence_role)],['Citation',stat.citation],['Source locator',locator(stat.source_locator)]];
    const displayValue=(label,value)=>['Numerator','Reported unit','Phase','Anatomy / laterality'].includes(label)?clean(value).replace(/\bNOT_REPORTED\b/g,'not available'):clean(value);
    if(!publicSite){
      fields.push(['Independence classification',stat.independent_evidence===1?'Independent observation; independence of cohorts is not established.':stat.independent_evidence===0?'Not classified as independent evidence.':'Not recorded']);
      if(stat.independence_status)fields.push(['Reporting status',roleName(stat.independence_status)]);
    }
    if(!publicSite && stat.restatement_explanation)fields.push(['Restatement context',stat.restatement_explanation]);
    const support=findingSupportFor(statements),supportRefs=new Set(support.map(item=>item.finding_ref));
    const relatedRows=uniq([...statements.flatMap(item=>(statOwners.get(item.statistic_id)||[])),...data.rows.filter(row=>supportRefs.has(findingRefFor(row)))]);
    for(const item of support)if(!relatedRows.some(row=>findingRefFor(row)===item.finding_ref))relatedRows.push({
      id:item.finding_ref,finding_ref:item.finding_ref,term:item.source_native_term,
      source:{id:rows[0]?.source.id,locator:item.source_locator,excerpt:item.source_excerpt,
        finding:{finding_ref:item.finding_ref,statement:item.claim}},
    });
    openDialog(clean(stat.measure)||metricName(stat.metric_type)||'Reported finding',`<div${metricName(stat.metric_type)?' class="dialog-value"':''}>${esc(valueText(stat))}</div><p>${paperIds(rows).map(id=>esc(citation(id))).join(' · ')}</p><dl>${fields.filter(([,value])=>!publicSite || clean(value)).map(([label,value])=>`<dt>${esc(label)}</dt><dd>${esc(displayValue(label,value)||'Not recorded')}</dd>`).join('')}</dl><h3>Source passages</h3>${statements.map(item=>`<p><strong>${esc(locator(item.source_locator))}</strong><br>${esc(item.source_excerpt)}</p>`).join('')}${sourceTableDetails(stat)}${findingsMarkup(relatedRows,{support:true})}`);
  }
  function explain() { openDialog('Weights & statistics explained',root.getElementById('scientific-explanation').innerHTML); }
  function refresh() { state.limit=30;expandedSections.clear(); opened.clear(); bannerState.clear(); grouping(); syncControls(); renderList(); }
  function resetFilters({preserveFocus=false}={}) {
    detailState.clear();
    selectedAnatomy.clear();selectedMetricIds.clear();classificationFilters={};sourceSelection=null;
    Object.assign(state,{query:'',sourceQuery:'',filters:{},focus:preserveFocus?state.focus:''});
    if(!preserveFocus)pendingFocus='';
    $('search').value='';updateQuery();refresh();
  }
  function showMapFor(element,{scroll=true}={}) {
    const card=element.closest('.sign-card'),entry=card?entries[Number(card.dataset.entry)]:null,group=entry?.group;
    const sourceId=element.dataset.mapSource || element.closest('.paper')?.dataset.paper;
    const context=group?selectedRows(group.rows).filter(row=>classMatches(row,settings(group.id).evidenceClass)):element.closest('#record-dialog')?dialogRows:[];
    const rows=context.filter(row=>!sourceId || row.source.id===sourceId);
    if(!rows.length)return;
    if(element.closest('#record-dialog'))$('record-dialog').close();
    const paperId=sourceId || (entry?.type==='source'?group.id:'');
    const signs=uniq(rows.flatMap(row=>(row.facets.sign||[]).map(sign=>sign.label)));
    const label=group && entry.type!=='source'?group.label:signs.length===1?signs[0]:rows.length===1?rows[0].term:'Selected findings';
    evidenceMap?.showEvidence(rows,label,{scroll,sourceLabel:paperId?citation(paperId):''});
  }
  root.addEventListener('toggle',event=>{const card=event.target;if(!card.isConnected)return;if(card.classList.contains('sign-section')){bannerState.set(card.dataset.banner,card.open);return;}if(card.classList.contains('result-refinements')){settings(card.dataset.group).controlsOpen=card.open;return;}if(card.classList.contains('paper')){const papers=settings(card.dataset.group).openPapers;if(card.open){papers.add(card.dataset.paper);renderPaper(card.querySelector('.paper-content'));}else papers.delete(card.dataset.paper);return;}if(!card.classList.contains('sign-card'))return;const entry=entries[Number(card.dataset.entry)];if(!entry)return;if(card.open){opened.add(entry.key);if(!card.dataset.loaded)renderEntry(card);else card.querySelectorAll('.paper-content').forEach(renderPaper);}else opened.delete(entry.key);},true);
  root.addEventListener('click',event=>{
    const summary=event.target.closest('.sign-card > summary, .paper > summary');
    if(event.isTrusted && !event.defaultPrevented && summary && !summary.parentElement.open && !matchMedia('(max-width:780px)').matches && !event.target.closest('button,a,input,select,textarea'))showMapFor(summary.parentElement,{scroll:false});
    const button=event.target.closest('button');if(!button)return;
    if(button.id==='controls-toggle'){button.setAttribute('aria-expanded',String(button.getAttribute('aria-expanded')!=='true'));return;}
    if(button.id==='help' || button.hasAttribute('data-evidence-help'))explain();
    if(button.hasAttribute('data-clear-map')){evidenceMap?.clear();return;}
    if(button.dataset.showMap){showMapFor(button);return;}
    if(button.id==='close-dialog')$('record-dialog').close();
    if(button.id==='reset'){if(options.embedded && options.onClearFilters)options.onClearFilters();else resetFilters();return;}
    if(button.id==='all-sources'){if(options.embedded){options.onViewSources?.();return;}evidenceMap?.clear(false);mapResultIds=null;Object.assign(state,{query:'',sourceQuery:'',organize:'source',filters:{},order:'title',focus:''});$('search').value='';updateQuery();refresh();}
    if(button.hasAttribute('data-more-section')){expandedSections.add(button.dataset.moreSection);renderList();}
    if(button.dataset.clearFilter){delete state.filters[button.dataset.clearFilter];refresh();}
    if(button.hasAttribute('data-retry-evidence')){renderPaper(button.closest('.paper-content'));return;}
    if(button.dataset.paperTopic){
      const body=button.closest('.paper-content'),section=[...body.querySelectorAll('[data-paper-section]')].find(section=>section.dataset.paperSection===button.dataset.paperTopic);
      if(section){const additional=section.closest('.paper-additional');if(additional)additional.open=true;body.scrollTo({top:body.scrollTop+section.getBoundingClientRect().top-body.getBoundingClientRect().top-12,behavior:'auto'});section.focus({preventScroll:true});}return;
    }
    if(button.dataset.stat)openStatistic(button.dataset.stat);
    if(button.dataset.findings){const ids=new Set(JSON.parse(button.dataset.findings));openFindingDetails(data.rows.filter(row=>ids.has(row.id)),JSON.parse(button.dataset.statistics || '[]'));return;}
    if(button.dataset.allTerm){if(options.embedded){pendingFocus=button.dataset.allTerm;options.onClearFilters?.({preserveFocus:true});return;}state.query='';state.focus=button.dataset.allTerm;$('search').value='';updateQuery();opened.clear();opened.add(state.focus);grouping();syncControls();renderList();}
    if(button.dataset.morePapers){settings(button.dataset.morePapers).papers=Infinity;refreshGroup(button.dataset.morePapers);}
    if(button.dataset.weightOrder){settings(button.dataset.group).weights=button.dataset.weightOrder;refreshGroup(button.dataset.group);}
  });
  root.addEventListener('change',event=>{
    const {id,value,dataset}=event.target;
    if(dataset.detail){settings(dataset.group)[dataset.detail]=value;refreshGroup(dataset.group);return;}
    if(dataset.facet){if(value)state.filters[dataset.facet]=value;else delete state.filters[dataset.facet];refresh();return;}
    if(id==='organize'){state.organize=value;state.order=value==='source'?'title':'name';state.focus='';}
    else if(id==='evidence-class'){setEvidenceClass(value);return;}
    else if(id==='order'){state.order=value;if(state.organize!=='source' && !['ilae','luders'].includes(value))signOrder=value;}
    else return;
    refresh();
  });
  $('search').addEventListener('input',event=>{if(state.organize==='source'){setSourceQuery(event.target.value);return;}state.query=event.target.value;state.focus='';state.limit=30;expandedSections.clear();opened.clear();updateQuery();grouping();renderList();});
  sources=new Map(catalogue.items.filter(item=>item.facet==='source').map(item=>[item.id,item]));nodeIndex=new Map(catalogue.items.map(item=>[item.id,item]));nativeSigns=new Map(atlasGroups(data.rows,'sign').map(group=>[group.id,group]));statOwners=new Map();
    for(const row of data.rows)for(const id of row.statistic_ids){if(!statOwners.has(id))statOwners.set(id,[]);statOwners.get(id).push(row);}
  if(detailsReady)indexWeights();

  grouping();
  $('search').value=state.query;syncControls();renderList();
  return {
    resetFilters,
    setSourceQuery,
    getSourceQuery(){return state.sourceQuery;},
    filterEvidenceClasses(rows,ids){return rows.filter(row=>!ids.length || ids.some(id=>classMatches(row,id)));},
    getEvidenceClasses(){return classesFor(data.rows);},
    update({rows,view='browse',query='',queryContext={},organization:nextOrganization=''}) {
      organization=nextOrganization;
      if(organization!=='region' && ['ilae','luders'].includes(state.order))state.order=signOrder;
      selectedAnatomy=new Set(queryContext.anatomy || []);
      selectedMetricIds=new Set(queryContext.metricIds || []);
      classificationFilters={ilae:queryContext.ilae || [],luders:queryContext.luders || []};
      sourceSelection=typeof queryContext.evidenceFiltered==='boolean'?{evidenceFiltered:queryContext.evidenceFiltered,sourceIds:queryContext.sourceIds || []}:null;
      queryRows=rows;mapResultIds=new Set(rows.map(row=>row.id));state.query=query;state.focus=pendingFocus;pendingFocus='';
      if(view!==currentView){if(currentView!=='sources' && !['ilae','luders'].includes(state.order))signOrder=state.order;state.organize=view==='sources'?'source':'sign';state.order=view==='sources'?'title':signOrder;currentView=view;}
      refresh();
    },
    collapseAll(){root.querySelectorAll('details[open]').forEach(element=>{element.open=false;});opened.clear();},
    expandGroups(){const banners=root.querySelectorAll('.sign-section');(banners.length?banners:root.querySelectorAll('.sign-list>.sign-card')).forEach(element=>{element.open=true;});}
  };

}
