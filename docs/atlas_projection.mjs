/* Static delivery of the same generated result/facet projection used locally. */
let atlasSnapshot;
const atlasAsciiLower = value => String(value ?? '').replace(/[A-Z]/g, c => c.toLowerCase());

function atlasProjectWeights(weights, rows) {
  const selected = new Set(rows.map(row => row.id));
  const output = { LOCALIZATION: [], LATERALIZATION: [] };
  for (const axis of Object.keys(output)) {
    for (const summary of weights?.[axis] || []) {
      const context = summary.result_ids || [];
      if (!context.some(id => selected.has(id))) continue;
      const contributions = [];
      for (const contribution of summary.contributions || []) {
        const resultIds = contribution.result_ids || [];
        if (!resultIds.some(id => selected.has(id))) continue;
        const complete = resultIds.every(id => selected.has(id));
        contributions.push(complete ? { ...contribution, complete } : {
          ...contribution, complete, weight_components: {},
          potential_weight: null, final_weight: null,
        });
      }
      const complete = context.every(id => selected.has(id));
      output[axis].push(complete ? { ...summary, complete, contributions } : {
        ...summary, complete, contributions, pattern_label: null, summary: null,
      });
    }
  }
  return output;
}

export async function atlasData(path, signal) {
  if (document.documentElement.dataset.projection !== 'static') {
    const response = await fetch(path, { signal });
    if (!response.ok) throw new Error('Atlas request failed');
    return response.json();
  }
  if (!atlasSnapshot) atlasSnapshot = (async () => {
    const version = document.documentElement.dataset.snapshot;
    const asset = `atlas-projection.json.gz${version ? `?v=${encodeURIComponent(version)}` : ''}`;
    const response = await fetch(asset, { signal });
    if (!response.ok) throw new Error('Atlas snapshot unavailable');
    const stream = response.body.pipeThrough(new DecompressionStream('gzip'));
    return new Response(stream).json();
  })().catch(error => { atlasSnapshot = null; throw error; });
  const snapshot = await atlasSnapshot;
  if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
  const url = new URL(path, location.href);
  if (url.pathname === '/api/catalogue') return snapshot.catalogue;
  return atlasPivot(snapshot, url.searchParams);
}

export function atlasPivot(snapshot, parameters) {
  const query = atlasAsciiLower((parameters.get('q') || '').trim());
  const filters = Object.entries(JSON.parse(parameters.get('filters') || '{}'));
  const regions = JSON.parse(parameters.get('regions') || '[]');
  if (!Array.isArray(regions) || regions.some(id => typeof id !== 'string')) throw new Error('Invalid region selection');
  const rows = snapshot.rows.filter(row =>
    regions.every(id => (row.facets.anatomy || []).some(value => value.id === id)) &&
    filters.every(([facet, ids]) => !ids.length || (row.facets[facet] || []).some(value => ids.includes(value.id))) &&
    (!query || [...row.search_text, ...Object.values(row.facets).flat().map(value => value.label)]
      .some(text => atlasAsciiLower(text).includes(query))));
  const findings = new Set(), sources = new Set(), statisticIds = new Set(), facets = {};
  for (const row of rows) {
    findings.add(row.finding_ref);
    for (const id of row.statistic_ids) statisticIds.add(id);
    for (const [facet, values] of Object.entries(row.facets)) {
      const seen = new Set();
      for (const value of values) {
        if (facet === 'source') sources.add(value.id);
        if (seen.has(value.id)) continue;
        seen.add(value.id);
        const bucket = (facets[facet] ||= new Map());
        if (!bucket.has(value.id)) bucket.set(value.id, { id: value.id, label: value.label, count: 0 });
        bucket.get(value.id).count += 1;
      }
    }
  }
  const offset = Math.max(0, Number(parameters.get('offset')) || 0);
  const limit = Math.max(1, Math.min(200, Number(parameters.get('limit')) || 50));
  const page = parameters.get('limit') === 'all' ? rows : rows.slice(offset, offset + limit);
  return {
    total: rows.length,
    counts: { results: rows.length, findings: findings.size, sources: sources.size, statistics: statisticIds.size },
    facets: Object.fromEntries(Object.entries(facets).map(([facet, items]) => [facet, [...items.values()]])),
    rows: page,
    statistics: Object.fromEntries([...new Set(page.flatMap(row => row.statistic_ids))]
      .map(id => [id, snapshot.statistics[id]])),
    weights: atlasProjectWeights(snapshot.weights, rows),
    appraisal_receipts: snapshot.appraisal_receipts || {},
  };
}

export function atlasWeights(response, axis) {
  return response?.weights?.[String(axis || '').toUpperCase()] || [];
}

export function atlasAppraisalLabel(receipt) {
  return receipt.source_terms?.join('; ') || 'Assessed source findings';
}

export function atlasEvidenceSection(role) {
  const value = String(role || '').replace(/^EVIDENCE:/, '');
  if (['PRIMARY_RESULT', 'CASE_OBSERVATION'].includes(value)) return 'study';
  if (['REVIEW_SYNTHESIS', 'GUIDELINE_RECOMMENDATION'].includes(value)) return 'review';
  if (['CITED_STUDY_RESTATEMENT', 'PRIMARY_RESULT_SAME_SOURCE_RESTATEMENT',
       'EDUCATIONAL_STATEMENT', 'METHOD_OR_DEFINITION', 'SOURCE_CONTEXT'].includes(value)) return 'background';
  return 'other';
}

// Presentation groups retain result references and never infer memberships.
export function atlasGroups(rows, facet) {
  const groups = new Map();
  for (const row of rows) {
    const values = facet ? [...new Map((row.facets[facet] || []).map(value => [value.id, value])).values()] : [];
    const memberships = values.length ? values : [{ id: '', label: facet ? 'Not reported' : 'All signs' }];
    for (const value of memberships) {
      const key = facet === 'sign' && !value.id ? row.id : value.id;
      if (!groups.has(key)) groups.set(key, {
        id: key, label: facet === 'sign' && !value.id ? row.term || 'Finding' : value.label, rows: [],
      });
      groups.get(key).rows.push(row);
    }
  }
  return [...groups.values()].sort((a, b) => a.label.localeCompare(b.label));
}

export function atlasClassificationGroups(rows, facet, items) {
  const dictionary = new Map(items.filter(item => item.facet === facet).map(item => [item.id, item]));
  const groups = new Map(atlasGroups(rows, facet).map(group => [group.id, {
    ...group, children: [], ordinal: dictionary.get(group.id)?.ordinal ?? Infinity,
    directRows: group.rows.filter(row => !group.id || row.facets[facet].some(value => value.id === group.id && value.assigned)),
  }]));
  const roots = [];
  for (const group of groups.values()) {
    const parent = groups.get(dictionary.get(group.id)?.parent_id);
    if (parent && parent !== group) parent.children.push(group);
    else roots.push(group);
  }
  const sort = values => {
    values.sort((a, b) => a.ordinal - b.ordinal || a.label.localeCompare(b.label));
    for (const group of values) sort(group.children);
  };
  sort(roots);
  return roots;
}

export function atlasCounts(rows) {
  return {
    findings: new Set(rows.map(row => row.finding_ref)).size,
    results: new Set(rows.map(row => row.id)).size,
    signs: new Set(rows.flatMap(row => (row.facets.sign || []).map(value => value.id))).size,
    sources: new Set(rows.flatMap(row => (row.facets.source || []).map(value => value.id))).size,
    statistics: new Set(rows.flatMap(row => row.statistic_ids)).size,
  };
}

// Organize existing occurrence links under their approved dictionary terms.
export function atlasDictionaryGroups(rows, facet, items, categoryId = '') {
  const dictionary = new Map(items.filter(item => item.facet === facet).map(item => [item.id, item]));
  const paths = new Map(), groups = new Map(), unplaced = [];
  const pathFor = id => {
    if (paths.has(id)) return paths.get(id);
    const path = [], seen = new Set();
    for (let item = dictionary.get(id); item; item = dictionary.get(item.parent_id)) {
      if (seen.has(item.id)) throw new Error('Cyclic classification dictionary');
      seen.add(item.id); path.push(item);
    }
    paths.set(id, path); return path;
  };
  for (const row of rows) {
    const choices = new Map();
    for (const link of row.facets[facet] || []) {
      if (!link.assigned) continue;
      const path = pathFor(link.id);
      if (categoryId && !path.some(item => item.id === categoryId)) continue;
      if (!path.length || path.some(item => ['DIMENSION', 'ATTRIBUTE_CATEGORY', 'MODIFIER_CATEGORY'].includes(item.kind))) continue;
      if (facet === 'ilae' && !path.some(item => item.kind === 'DESCRIPTOR_ROOT')) continue;
      const terms = path.filter(item => ['TYPE', 'TERM'].includes(item.kind));
      const target = terms.at(-1) || path.find(item => ['CATEGORY', 'DESCRIPTOR_CATEGORY', 'WORKSHEET_CATEGORY', 'EVENT_CATEGORY'].includes(item.kind));
      if (target) choices.set(target.id, target);
    }
    const selected = [...choices.values()].filter(item => ![...choices.values()].some(other =>
      other.id !== item.id && pathFor(other.id).some(parent => parent.id === item.id)));
    if (!selected.length) unplaced.push(row);
    for (const item of selected) {
      if (!groups.has(item.id)) groups.set(item.id, { id: item.id, label: item.label, dictionary: item, rows: [] });
      groups.get(item.id).rows.push(row);
    }
  }
  return { groups: [...groups.values()].sort((a, b) => a.label.localeCompare(b.label)), unplaced };
}

export const atlasMetricLabels = Object.freeze({
  "ACCURACY": "Accuracy",
  "ASSOCIATION_COEFFICIENT": "Association coefficient",
  "CORRELATION": "Correlation",
  "COUNT": "Count",
  "COUNT_AND_PERCENTAGE": "Count and percentage",
  "DURATION": "Duration",
  "DURATION_RANGE": "Duration range",
  "DURATION_THRESHOLD": "Duration threshold",
  "FREQUENCY": "Frequency",
  "HAZARD_RATIO": "Hazard ratio",
  "HETEROGENEITY_I2": "Heterogeneity (I²)",
  "INTEROBSERVER_AGREEMENT": "Interobserver agreement",
  "KAPPA": "Kappa",
  "LATENCY": "Latency",
  "LR": "Likelihood ratio",
  "MEAN": "Mean",
  "MEDIAN": "Median",
  "META_ANALYSIS_WEIGHT": "Reported meta-analysis weight",
  "NPV": "Negative predictive value",
  "NUMBER_OF_PATIENTS": "Number of patients",
  "ODDS": "Odds",
  "ODDS_RATIO": "Odds ratio",
  "OR": "Odds ratio",
  "P_VALUE": "P value",
  "PERCENT": "Percent",
  "PERCENTAGE": "Percentage",
  "PERCENTAGE_RANGE": "Percentage range",
  "PPV": "Positive predictive value",
  "PROBABILITY": "Probability",
  "PROPORTION": "Proportion",
  "RANGE": "Range",
  "RATE": "Rate",
  "RATE_RANGE": "Rate range",
  "RATIO": "Ratio",
  "RISK_RATIO": "Risk ratio",
  "SENSITIVITY": "Sensitivity",
  "SPECIFICITY": "Specificity",
  "STANDARD_ERROR": "Standard error",
  "THRESHOLD": "Threshold",
  "UPPER_BOUND_PERCENTAGE": "Percentage upper bound",
  "Z_STATISTIC": "Z statistic"
});

export function atlasMetricTypes(statistics) {
  return [...new Set(statistics.map(stat => stat.metric_type))]
    .filter(type => Object.hasOwn(atlasMetricLabels, type))
    .sort((a, b) => atlasMetricLabels[a].localeCompare(atlasMetricLabels[b]));
}

// Follow declared restatements within one selected source; values are never matched.
export function atlasStatisticGroups(statistics) {
  const records=new Map(statistics.map(stat=>[stat.statistic_id,stat])), groups=new Map();
  for(const stat of records.values()) {
    let owner=stat;
    const visited=new Set();
    while(owner.restates_statistic_id && records.has(owner.restates_statistic_id)) {
      if(visited.has(owner.statistic_id))throw new Error('Cyclic statistic restatement');
      const target=records.get(owner.restates_statistic_id);
      if(!owner.source_sha256 || !owner.source_report_sha256 || owner.source_sha256!==target.source_sha256 || owner.source_report_sha256!==target.source_report_sha256)break;
      visited.add(owner.statistic_id);owner=target;
    }
    if(!groups.has(owner.statistic_id))groups.set(owner.statistic_id,{statistic:owner,statements:[]});
    groups.get(owner.statistic_id).statements.push(stat);
  }
  return [...groups.values()];
}

export function atlasWeightPresentation(contribution, axis) {
  if (!contribution) return { label: '—', calculation: '', applied: '—', reason: '' };
  const c = contribution, status = c.weight_status || '';
  const pending = !c.complete || /UNRESOLVED|PENDING/.test(status);
  const format = (value, digits) => Number(value).toLocaleString('en-US', { maximumFractionDigits: digits });
  const parts = c.weight_components || {}, factors = [parts.class_base, parts.directness_multiplier, parts.size_factor];
  const unassessed = c.evidence_class === 'UNCLASSIFIED' &&
    (parts.class_base === 0 || c.authority_category === 'Structured design not resolved');
  const applied = unassessed ? 'Not assigned' : pending ? 'Pending' : c.final_weight == null ? '—' : format(c.final_weight, 2);
  const ready = [...factors, c.potential_weight].every(value => typeof value === 'number' && Number.isFinite(value));
  const product = factors.reduce((value, factor) => value * factor, 1);
  const calculation = ready ? (unassessed ? 'Stored calculation: ' : 'Weight before eligibility: ') + factors.map(value => format(value, 4)).join(' × ') +
    (product === c.potential_weight ? ' = ' : ' ≈ ') + format(c.potential_weight, 4) : '';
  const reason = unassessed ? 'Evidence class has not been assigned; the stored calculation is not an assessed weight.' :
    !c.complete ? 'Weight unavailable for this filtered subset.' :
    status === 'NOT_APPLIED_WEIGHT_METADATA_UNRESOLVED' ? 'No weight is assigned to this result.' :
    status === 'NOT_APPLIED_CONTRIBUTION_SCOPE_UNRESOLVED' ? 'No separate contribution is assigned to this result.' :
    pending ? 'Weight not calculated.' : status === 'NOT_APPLIED_SEPARATE_EVIDENCE_PARTITION' ?
    'Not included in the primary-evidence total.' : status === 'NOT_APPLIED_NO_USABLE_AXIS_TARGET' ?
    'No eligible source-reported ' + (axis === 'LATERALIZATION' ? 'lateralization' : 'localization') + ' target.' : c.weight_status_label || '';
  const stored = !unassessed && typeof c.potential_weight === 'number' && Number.isFinite(c.potential_weight) && (ready || !/UNRESOLVED|PENDING/.test(status));
  return { label: stored ? format(c.potential_weight,2) : '—', calculation, applied, reason };
}

const atlasEscape = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const atlasRoleLabel = value => String(value ?? '').replace(/_/g,' ').toLowerCase().replace(/\b\w/g, letter => letter.toUpperCase());
const atlasComparableText = value => String(value ?? '').trim().toLowerCase().replace(/\s+/g,' ');

function groupedSourceAnatomy(row) {
  const groups = new Map();
  for (const value of (row.source_anatomy || [])) {
    const excerpt = String(value.source_excerpt || "").trim();
    const key = JSON.stringify([excerpt || value.source_term || "", value.locator || "", value.role || "",
      value.context_qualifier || "", value.context_polarity || "", value.context_modality || "",
      value.decision_role || '', value.source_sign_id || '', value.source_scope || '']);
    if (!groups.has(key)) groups.set(key, { value, terms: new Set(), targets: new Set(), support: [] });
    if (value.source_term) groups.get(key).terms.add(value.source_term);
    if (value.target_label) groups.get(key).targets.add(value.target_label);
    const supportKey = JSON.stringify([value.role || "", excerpt]);
    if ((value.role || excerpt) && !groups.get(key).support.some(item => item.key === supportKey)) groups.get(key).support.push({ key: supportKey, role: value.role || "", excerpt });
  }
  return [...groups.values()];
}

export function atlasSourceAnatomyMarkup(row, seenExcerpts=new Set(), {h=atlasEscape, roleLabel=atlasRoleLabel, sourceLocator=String, comparableText=atlasComparableText}={}) {
  const contextLabels = {
    MEASURED_TRACT_ASSOCIATION: 'Measured tract association',
    HYPOTHESIZED_MECHANISM: 'Hypothesized mechanism',
    POSSIBLE_PROPAGATION: 'Possible propagation; source hypothesis',
    CASE_ICTAL_EEG_ONSET: 'Seizure onset recorded by EEG in this case',
    NEGATIVE_ANATOMY_NONINVOLVEMENT: 'Reported absence of involvement',
    CITED_NEUROPATHOLOGY_DIRECT_RELEVANCE_UNKNOWN: 'Cited neuropathology; direct relevance uncertain',
    PET_HYPOMETABOLISM: 'PET hypometabolism',
    CASE_MRI_LESION: 'MRI lesion in this case',
  };
  return groupedSourceAnatomy(row).map(group => {
    const value = group.value;
    const qualifiers=[];
    if(value.decision_role==='CONTEXT')qualifiers.push(contextLabels[value.context_qualifier]||roleLabel(value.context_qualifier||'SOURCE_REPORTED_CONTEXT'));
    if(value.context_polarity&&value.context_polarity!=='POSITIVE_ASSOCIATION')qualifiers.push(roleLabel(value.context_polarity));
    if(value.context_modality)qualifiers.push(roleLabel(value.context_modality));
    for(const term of group.terms)seenExcerpts.add(comparableText(term));
    const support=group.support.flatMap(item=>{
      const excerpt=String(item.excerpt||'').trim(),key=comparableText(excerpt);
      if(!excerpt||seenExcerpts.has(key))return [];
      seenExcerpts.add(key);
      return ['<blockquote>'+h(excerpt)+'</blockquote>'];
    }).join('');
    const label = {COHORT_CONTEXT:'Study cohort anatomy',COMPARATOR_CONTEXT:'Comparison anatomy',
      ONSET:'Seizure onset',STIMULATION:'Stimulation site',NETWORK:'Network',
      SYMPTOMATOGENIC:'Symptom-producing region',LESION:'Lesion location',SOURCE_REPORTED:'Reported localization'}[value.role] || 'Reported anatomy';
    return '<div class="source-detail">'+(value.source_sign_label?'<strong>'+h(value.source_sign_label)+':</strong> ':'')+(value.source_scope==='CLAIM'&&!value.source_sign_id?'<span>Finding context · </span>':'')+'<strong>'+h(value.decision_role==='CONTEXT' && value.role==='SOURCE_REPORTED' ? 'Anatomical context' : label)+':</strong> '+h([...group.targets].join('; ') || [...group.terms].join('; '))+
      (qualifiers.length?' · '+qualifiers.map(h).join(' · '):'')+
      (group.targets.size && [...group.terms].join('; ')!==[...group.targets].join('; ') ? '<p>'+h([...group.terms].join('; '))+'</p>' : '')+
      (value.locator?'<small>'+h(sourceLocator(value.locator))+'</small>':'')+support+'</div>';
  }).join('');
}

export function atlasSourceFindingsMarkup(rows, {compact=false,localizationAnnotation=null}={}) {
  if (compact) {
    const labels={COHORT_CONTEXT:'Study cohort anatomy',COMPARATOR_CONTEXT:'Comparison anatomy',ONSET:'Seizure onset',STIMULATION:'Stimulation site',NETWORK:'Network',SYMPTOMATOGENIC:'Symptom-producing region',LESION:'Lesion location',SOURCE_REPORTED:'Reported localization'};
    const subjects=new Map();
    for(const row of rows) {
      for(const [axis,values] of [['LOCALIZATION',row.source_anatomy || []],['LATERALIZATION',row.source_laterality || row.facets?.laterality || []]]) {
        for(const value of values) {
          const target=value.target_label || value.label || value.source_term;
          if(!target)continue;
          const findingContext=value.source_scope==='CLAIM'&&!value.source_sign_id;
          const subjectKey=JSON.stringify([row.source?.id || row.id,value.source_sign_id || '',value.source_sign_id ? '' : value.source_sign_label || '',
            !value.source_sign_id && (value.source_sign_label || findingContext) ? row.finding_ref || row.id : '']);
          if(!subjects.has(subjectKey))subjects.set(subjectKey,{names:new Set(),findingContext,axes:new Map()});
          const subject=subjects.get(subjectKey);
          if(value.source_sign_label)subject.names.add(value.source_sign_label);
          const label=axis==='LOCALIZATION'
            ? value.decision_role==='CONTEXT' && value.role==='SOURCE_REPORTED' ? 'Anatomical context' : labels[value.role] || 'Reported anatomy'
            : value.role==='COHORT_CONTEXT' ? 'Cohort lateralization' : value.role==='STIMULATION' ? 'Stimulation lateralization' : 'Reported lateralization';
          const axisKey=JSON.stringify([axis,value.role || '',label]);
          if(!subject.axes.has(axisKey))subject.axes.set(axisKey,{axis,label,contexts:new Map()});
          const section=subject.axes.get(axisKey);
          const propagation=(row.modifiers || []).some(modifier=>value.link_id && modifier.evidence_link_id===value.link_id && modifier.target_axis===axis && modifier.modifier_type==='PROPAGATION');
          const qualifiers=[value.context_polarity && value.context_polarity!=='POSITIVE_ASSOCIATION' ? atlasRoleLabel(value.context_polarity) : '',
            value.context_qualifier ? atlasRoleLabel(value.context_qualifier) : '',value.context_modality,propagation?'Propagation':''].filter(Boolean);
          const contextKey=JSON.stringify([value.source_scope || '',value.decision_role || '',value.context_polarity || '',value.context_qualifier || '',value.context_modality || '',propagation]);
          if(!section.contexts.has(contextKey))section.contexts.set(contextKey,{qualifiers:[...new Set(qualifiers)],targets:new Map()});
          const targets=section.contexts.get(contextKey).targets,key=JSON.stringify([value.target_id || value.id || target,target]);
          if(!targets.has(key))targets.set(key,{label:target,annotations:new Set()});
          const annotation=axis==='LOCALIZATION' ? localizationAnnotation?.(row,value) : '';
          if(annotation)targets.get(key).annotations.add(String(annotation));
        }
      }
    }
    const markup=[...subjects.values()].map(subject=>{
      const heading=[...subject.names].join('; ') || (subject.findingContext?'Finding context':'');
      const axes=[...subject.axes.values()].sort((a,b)=>Number(a.axis==='LATERALIZATION')-Number(b.axis==='LATERALIZATION')).map(section=>'<div class="anatomy-axis"><dt>'+atlasEscape(section.label)+':</dt><dd>'+[...section.contexts.values()].map(context=>
        '<span>'+[...context.targets.values()].map(target=>atlasEscape(target.label)+(target.annotations.size?' <span class="anatomy-qualifier">('+[...target.annotations].map(atlasEscape).join(' · ')+')</span>':'')).join('; ')+(context.qualifiers.length?' <span class="anatomy-qualifier">('+context.qualifiers.map(atlasEscape).join(' · ')+')</span>':'')+'</span>'
      ).join('')+'</dd></div>').join('');
      return '<div class="anatomy-subject">'+(heading?'<h4>'+atlasEscape(heading)+'</h4>':'')+'<dl>'+axes+'</dl></div>';
    }).join('');
    return markup?'<section class="paper-anatomy compact-anatomy" aria-label="Reported localization and lateralization">'+markup+'</section>':'';
  }
  const findings = [...new Map(rows.map(row => [row.id, row])).values()].flatMap(row => {
    const anatomy = atlasSourceAnatomyMarkup(row);
    const laterality = [...new Map((row.source_laterality || row.facets?.laterality || []).map(value => [JSON.stringify([value.target_label || value.label,value.source_term,value.role,value.source_sign_id,value.locator]),value])).values()]
      .map(value => '<p class="source-detail">'+(value.source_sign_label?'<strong>'+atlasEscape(value.source_sign_label)+':</strong> ':'')+'<strong>' + (value.role==='COHORT_CONTEXT' ? 'Cohort lateralization' : value.role==='STIMULATION' ? 'Stimulation lateralization' : 'Reported lateralization') + ':</strong> ' + atlasEscape(value.target_label || value.label) +
        (value.source_term && value.source_term!==(value.target_label || value.label) ? '<br>'+atlasEscape(value.source_term) : '')+(value.locator?'<small>'+atlasEscape(value.locator)+'</small>':'')+'</p>').join('');
    const locator = laterality && row.source?.locator ? '<small>'+atlasEscape(row.source.locator)+'</small>' : '';
    return anatomy || laterality ? ['<article class="anatomy-result"><h4>'+atlasEscape(row.term)+'</h4>'+anatomy+laterality+locator+'</article>'] : [];
  });
  return findings.length ? '<section class="paper-anatomy" aria-label="Reported localization and lateralization">'+findings.join('')+'</section>' : '';
}
