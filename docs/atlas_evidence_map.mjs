import { SurfacePanel } from './atlas_surface.mjs?v=f992912b7859606cce938963c96b555e25aa90aac80a514eaa36107b545dbc8a';

const unique = values => [...new Set(values)];

/** Connect the existing surface viewer to result IDs in the common projection. */
export class EvidenceMap {
  constructor(root, catalogue, onSelection) {
    this.root = root;
    this.catalogue = catalogue;
    this.onSelection = onSelection;
    this.selection = {regions: [], anatomy: [], groups: []};
    this.rows = [];
    this.highlight = null;
    this.view = catalogue.maps.default_view || 'lateral';
    this.hemisphere = 'left';
    this.nodes = new Map(catalogue.items.map(item => [item.id, item]));
    this.brodmann = catalogue.items.filter(item => item.facet === 'anatomy' && item.reference === 'ATLAS:BRODMANN');
    if (!catalogue.maps.local_surfaces) { root.hidden = true; return; }
    root.hidden = false;
    this.host = root.querySelector('.brain-map');
    this.caption = root.querySelector('.map-caption');
    this.counts = root.querySelector('[data-map-counts]');
    this.viewControl = root.querySelector('[data-map-view]');
    this.hemisphereControl = root.querySelector('[data-map-hemisphere]');
    for (const [id, view] of Object.entries(catalogue.maps.views || {})) {
      const option = document.createElement('option'); option.value = id; option.textContent = view.label || id[0].toUpperCase() + id.slice(1);
      this.viewControl.append(option);
    }
    this.viewControl.value = this.view;
    root.addEventListener('toggle', () => { if (root.open) this.ensure(); });
    this.viewControl.addEventListener('change', () => { this.view = this.viewControl.value; this.render(); });
    this.hemisphereControl.addEventListener('change', () => { this.hemisphere = this.hemisphereControl.value; this.render(); });
    this.counts.addEventListener('change', () => this.render());
    this.counts.closest('label').addEventListener('click', event => event.stopPropagation());
    this.host.addEventListener('click', event => {
      const marker = event.target.closest('.surface-ba[data-anatomy]');
      if (marker) this.selectBrodmann(marker.dataset.anatomy);
    });
    this.host.addEventListener('change', event => {
      const input = event.target.closest('input[data-anatomy]');
      if (input) this.selectBrodmann(input.dataset.anatomy, input.checked);
    });
  }

  ensure() {
    if (this.surface || this.root.hidden) return;
    const maps = this.catalogue.maps;
    this.surface = new SurfacePanel(this.host, {...maps.local_surfaces, groups: maps.region_groups, brodmann: this.brodmann},
      (view, hemisphere) => { this.view = view; this.hemisphere = hemisphere; this.render(); },
      (rows, groups) => {
        this.selection.regions = unique(rows.map(row => row.anatomy_id).filter(Boolean));
        this.selection.groups = [...groups];
        this.changed();
      }, () => this.clear(), false);
    this.surface.ready.then(() => this.render());
    this.render();
  }

  selectBrodmann(id, selected = !this.selection.anatomy.includes(id)) {
    this.selection.anatomy = selected ? unique([...this.selection.anatomy, id]) : this.selection.anatomy.filter(value => value !== id);
    this.changed();
  }

  changed() {
    this.highlight = null;
    this.render();
    this.onSelection({...this.selection});
  }

  clear(notify = true) {
    this.selection = {regions: [], anatomy: [], groups: []};
    this.highlight = null;
    this.surface?.setGroups([]);
    this.surface?.select([], false);
    this.render();
    if (notify) this.onSelection({...this.selection});
  }

  update(rows) { this.rows = rows; this.highlight = null; if (this.root.open) this.render(); }

  showEvidence(rows, label) {
    this.highlight = {ids: new Set(rows.flatMap(row => (row.facets.anatomy || []).map(item => item.id))), label};
    this.root.open = true;
    this.ensure();
    this.render();
    this.root.scrollIntoView({block: 'start', behavior: 'auto'});
  }

  render() {
    if (!this.surface) return;
    const {surface, catalogue, selection} = this;
    const views = catalogue.maps.views || {};
    const current = views[this.view] || {};
    const counts = new Map();
    for (const row of this.rows) for (const item of row.facets.anatomy || []) {
      if (!counts.has(item.id)) counts.set(item.id, new Set());
      counts.get(item.id).add(row.source.id);
    }
    const showCounts = this.counts.checked && surface.atlas.value === 'brodmann';
    this.counts.disabled = surface.atlas.value !== 'brodmann';
    const markers = view => [...(Array.isArray(view.markers) ? view.markers : Object.entries(view.markers || {}).flatMap(([anatomy_id, values]) => (Array.isArray(values) ? values : [values]).map(marker => ({...marker, anatomy_id})))), ...(view.unmapped_markers || [])].map(marker => ({...marker, count: showCounts ? counts.get(marker.anatomy_id)?.size || 0 : null}));
    const selected = new Set([...selection.anatomy, ...(this.highlight?.ids || [])]);
    surface.setView(this.view, this.hemisphere);
    surface.setGroups(selection.groups);
    surface.syncRegionMenu(selection.anatomy);
    surface.setBrodmann(markers(current), selected, current.image || {}, Object.entries(views).map(([view, plate]) => ({view, bilateral: plate.bilateral_plate, image: plate.image, markers: markers(plate)})));
    // SurfacePanel labels its generic counter as results; this view counts distinct papers.
    for (const badge of this.host.querySelectorAll('.surface-ba-count')) badge.title = `${badge.textContent} papers`;
    this.viewControl.value = this.view;
    this.hemisphereControl.value = this.hemisphere;
    this.hemisphereControl.closest('label').hidden = ['dorsal', 'ventral'].includes(this.view);
    if (surface.renderer) {
      const ids = new Set([...selection.regions, ...(this.highlight?.ids || []), ...(catalogue.maps.region_groups || []).filter(group => selection.groups.includes(group.id)).flatMap(group => group.anatomy_ids)]);
      surface.renderer.setSelection(surface.options.filter(row => ids.has(surface.palette.get(row.index)?.anatomy_id)));
    }
    const labels = unique([...selection.groups, ...selection.regions, ...selection.anatomy]).map(id => {
      const node = this.nodes.get(id); return node?.area_name ? `${node.label} — ${node.area_name}` : node?.label || '';
    }).filter(Boolean);
    this.caption.textContent = this.highlight ? `Reported anatomy: ${this.highlight.label}` : labels.join(' · ');
    this.caption.hidden = !this.caption.textContent;
  }
}
