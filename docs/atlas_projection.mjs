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
  const rows = snapshot.rows.filter(row =>
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
  };
}

export function atlasWeights(response, axis) {
  return response?.weights?.[String(axis || '').toUpperCase()] || [];
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
