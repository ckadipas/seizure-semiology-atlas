/* Anatomical presentation only. Parcel selection never creates an evidence link. */
const vertexShader = `#version 300 es
in vec3 position;
in vec3 normal;
in vec3 color;
in float selected;
uniform mat3 rotation;
uniform vec3 center;
uniform vec2 extent;
uniform float depth;
out vec3 vNormal;
out vec3 vColor;
out float vSelected;
void main() {
  vec3 p = rotation * (position - center);
  gl_Position = vec4(p.xy / extent, -p.z / depth, 1.0);
  vNormal = rotation * normal;
  vColor = color;
  vSelected = selected;
}`;
const fragmentShader = `#version 300 es
precision highp float;
in vec3 vNormal;
in vec3 vColor;
in float vSelected;
uniform float opacity;
out vec4 outputColor;
void main() {
  vec3 n = normalize(vNormal) * (gl_FrontFacing ? 1.0 : -1.0);
  vec3 light = normalize(vec3(-.4, .6, 1.5));
  float diffuse = max(0.0, dot(n, light));
  // Reference PNG display primaries, with matte illumination and neutral fill.
  vec3 lit = vColor * (.25 + .65 * diffuse) + .06;
  vec3 linear = max(mat3(1.224852,-.042055,-.019651,
                       -.224805,1.042064,-.078653,
                        .000024,.000027,1.097871) * lit, vec3(0.0));
  vec3 display = mix(12.92 * linear, 1.055 * pow(linear,vec3(1.0/2.4)) - .055,
                     step(vec3(.0031308),linear));
  outputColor = vec4(mix(display,vec3(1.0),.30*(1.0-vSelected)), opacity);
}`;

function multiply(a, b) {
  return Array.from({length:9}, (_, i) => {
    const row = Math.floor(i / 3), column = i % 3;
    return a[row*3]*b[column] + a[row*3+1]*b[column+3] + a[row*3+2]*b[column+6];
  });
}

export function projectPoint(point, rotation, center) {
  const [x,y,z]=point.map((value,axis)=>value-center[axis]);
  return [0,3,6].map(i=>rotation[i]*x+rotation[i+1]*y+rotation[i+2]*z);
}

function viewRotation(view, hemisphere) {
  const side=(view==='medial'?1:-1)*(hemisphere==='right'?-1:1);
  return view==='dorsal'?[1,0,0,0,1,0,0,0,1]:view==='ventral'?[-1,0,0,0,1,0,0,0,-1]:[0,side,0,0,0,1,side,0,0];
}

function smoothDisplay(positions, indices) {
  // Taubin smoothing of a display copy; source geometry and labels stay intact.
  const neighbors=Array.from({length:positions.length/3},()=>new Set());
  for(let i=0;i<indices.length;i+=3)for(let j=0;j<3;j++){
    const a=indices[i+j],b=indices[i+(j+1)%3];neighbors[a].add(b);neighbors[b].add(a);
  }
  let output=positions.slice();
  for(let pass=0;pass<12;pass++){
    const next=output.slice(),gain=pass%2===0?.33:-.331;
    for(let vertex=0;vertex<neighbors.length;vertex++){
      const adjacent=neighbors[vertex];if(!adjacent.size)continue;
      for(let axis=0;axis<3;axis++){
        let mean=0;for(const neighbor of adjacent)mean+=output[neighbor*3+axis];
        next[vertex*3+axis]+=gain*(mean/adjacent.size-output[vertex*3+axis]);
      }
    }
    output=next;
  }
  return output;
}

async function loadMesh(record, palette) {
  const response = await fetch(`/local-surfaces/${encodeURIComponent(record.file)}`, {cache:'no-store'});
  if (!response.ok) throw new Error('The local surface could not be loaded.');
  const data = await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  const header = new DataView(data);
  if (header.getUint32(0, true) !== 0x3146534e) throw new Error('Unsupported surface data.');
  const count = header.getUint32(4, true), triangles = header.getUint32(8, true);
  if (count !== record.vertices || triangles !== record.triangles || data.byteLength !== 12+count*14+triangles*12)
    throw new Error('Surface data does not match its manifest.');
  let positions = new Float32Array(data, 12, count*3);
  let indices = new Uint32Array(data, 12+count*12, triangles*3);
  const labels = new Uint16Array(data, 12+count*12+triangles*12, count);
  const insula=[],insulaIndex=[...palette.values()].find(row=>row.name==='insula')?.index;
  for(let i=0;i<indices.length;i+=3){
    const a=indices[i],b=indices[i+1],c=indices[i+2];
    if(labels[a]===insulaIndex&&labels[b]===insulaIndex&&labels[c]===insulaIndex)insula.push(a,b,c);
  }
  if(record.structure!=='cortex')positions=smoothDisplay(positions,indices);
  const normals = new Float32Array(count*3), colors = new Float32Array(count*3);
  for (let i=0; i<indices.length; i+=3) {
    const a=indices[i]*3, b=indices[i+1]*3, c=indices[i+2]*3;
    const ux=positions[b]-positions[a], uy=positions[b+1]-positions[a+1], uz=positions[b+2]-positions[a+2];
    const vx=positions[c]-positions[a], vy=positions[c+1]-positions[a+1], vz=positions[c+2]-positions[a+2];
    const x=uy*vz-uz*vy, y=uz*vx-ux*vz, z=ux*vy-uy*vx;
    for (const index of [a,b,c]) { normals[index]+=x; normals[index+1]+=y; normals[index+2]+=z; }
  }
  for (let i=0; i<count; i++) {
    const length=Math.hypot(normals[i*3],normals[i*3+1],normals[i*3+2]);
    if (length) for (let axis=0;axis<3;axis++) normals[i*3+axis]/=length;
    const row=palette.get(labels[i]);
    if (!row) throw new Error('A surface label has no supplied color.');
    for (let axis=0;axis<3;axis++) colors[i*3+axis]=row.rgb[axis]/255;
  }
  return {...record, positions, indices, insulaIndices:Uint32Array.from(insula), labels, normals, colors};
}

export function bindSurfaceGestures(canvas, rotate, zoom, pick) {
  const stage=canvas.parentElement,pointers=new Map();
  let moved=false;
  const distance=()=>{const [a,b]=pointers.values();return b?Math.hypot(a.x-b.x,a.y-b.y):0;};
  stage.addEventListener('pointerdown',event=>{
    if(!pointers.size)moved=false;
    const label=event.target.closest('.surface-ba');
    if(canvas.hidden||event.button!==0||(label&&(event.pointerType!=='touch'||stage.classList.contains('surface-edit-labels'))))return;
    if(!label&&event.pointerType!=='touch')canvas.focus({preventScroll:true});
    stage.setPointerCapture(event.pointerId);
    pointers.set(event.pointerId,{x:event.clientX,y:event.clientY,startX:event.clientX,startY:event.clientY,label});
    if(pointers.size>1)moved=true;
  },{capture:true});
  stage.addEventListener('pointermove',event=>{
    const point=pointers.get(event.pointerId);
    if(!point)return;
    const before=distance(),dx=event.clientX-point.x,dy=event.clientY-point.y;
    point.x=event.clientX;point.y=event.clientY;
    if(pointers.size===2){
      const after=distance();
      if(before>0&&after>0)zoom(after/before);
    }else if(pointers.size===1){
      moved ||= Math.hypot(point.x-point.startX,point.y-point.startY)>3;
      if(moved)rotate(dx*.009,dy*.009);
    }
  });
  const end=event=>{
    const point=pointers.get(event.pointerId);
    if(!point)return;
    pointers.delete(event.pointerId);
    if(event.type==='pointerup'&&!moved){
      if(point.label){point.label.click();moved=true;}
      else pick(event.clientX,event.clientY);
    }
    if(event.type!=='pointerup')moved=true;
  };
  for(const type of ['pointerup','pointercancel','lostpointercapture'])stage.addEventListener(type,end);
  stage.addEventListener('click',event=>{if(moved&&event.detail>0){event.preventDefault();event.stopPropagation();}},{capture:true});
}

class SurfaceCanvas {
  constructor(canvas, meshes, onPick) {
    this.canvas=canvas; this.meshes=meshes; this.onPick=onPick; this.zoom=1; this.selection=[]; this.pickingEnabled=true;
    this.gl=canvas.getContext('webgl2', {antialias:true, alpha:false, preserveDrawingBuffer:false});
    if (!this.gl) throw new Error('This browser does not support WebGL 2.');
    const gl=this.gl, program=gl.createProgram();
    for (const [type, source] of [[gl.VERTEX_SHADER,vertexShader],[gl.FRAGMENT_SHADER,fragmentShader]]) {
      const shader=gl.createShader(type); gl.shaderSource(shader,source); gl.compileShader(shader);
      if (!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
      gl.attachShader(program,shader); gl.deleteShader(shader);
    }
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
    this.program=program;
    this.uniforms=Object.fromEntries(['rotation','center','extent','depth','opacity'].map(name=>[name,gl.getUniformLocation(program,name)]));
    for (const mesh of meshes) {
      mesh.vao=gl.createVertexArray(); gl.bindVertexArray(mesh.vao);
      for (const [name, values, size] of [['position',mesh.positions,3],['normal',mesh.normals,3],['color',mesh.colors,3],['selected',new Float32Array(mesh.labels.length).fill(1),1]]) {
        const buffer=gl.createBuffer();if(name==='selected')mesh.selectionBuffer=buffer;
        gl.bindBuffer(gl.ARRAY_BUFFER,buffer); gl.bufferData(gl.ARRAY_BUFFER,values,gl.STATIC_DRAW);
        const location=gl.getAttribLocation(program,name); gl.enableVertexAttribArray(location);
        gl.vertexAttribPointer(location,size,gl.FLOAT,false,0,0);
      }
      for(const key of ['indices','insulaIndices']){
        mesh[key+'Buffer']=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,mesh[key+'Buffer']);
        gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,mesh[key],gl.STATIC_DRAW);
      }
    }
    gl.enable(gl.DEPTH_TEST); gl.clearColor(1,1,1,1);
    this.observer=new ResizeObserver(()=>this.draw()); this.observer.observe(canvas);
    bindSurfaceGestures(canvas,(x,y)=>this.rotate(x,y),factor=>this.zoomBy(factor),(x,y)=>this.pick(x,y));
    canvas.addEventListener('wheel',event=>{
      event.preventDefault();this.zoomBy(Math.exp(-event.deltaY*.001));
    },{passive:false});
    canvas.addEventListener('keydown',event=>{
      const turns={ArrowLeft:[-.15,0],ArrowRight:[.15,0],ArrowUp:[0,-.15],ArrowDown:[0,.15]};
      if(turns[event.key]){event.preventDefault();this.rotate(...turns[event.key]);}
      if(['+','=','-'].includes(event.key)) {event.preventDefault();this.zoomBy(event.key==='-'?.9:1.1);}
      if(event.key==='0')this.setView(this.view,this.hemisphere,this.layer,true);
    });
    canvas.addEventListener('webglcontextlost',event=>{event.preventDefault();onPick([], 'The graphics context was interrupted. Reload the page to restore the surface.');});
  }

  setView(view, hemisphere, layer, reset=false) {
    if (!reset&&view===this.view&&hemisphere===this.hemisphere&&layer===this.layer) {this.draw();return;}
    this.view=view;this.hemisphere=hemisphere;this.layer=layer;this.zoom=1;
    this.projected=new Map();
    this.rotation=viewRotation(view,hemisphere);
    this.visible=this.meshes.filter(mesh=>(hemisphere==='both'||mesh.hemisphere===hemisphere)&&(layer!=='mesial'||mesh.structure!=='cortex')&&(layer!=='insula'||mesh.structure==='cortex'));
    const bounds=[0,1,2].map(axis=>[Math.min(...this.visible.map(m=>m.bounds[axis][0])),Math.max(...this.visible.map(m=>m.bounds[axis][1]))]);
    this.center=bounds.map(([low,high])=>(low+high)/2);
    this.radius=Math.max(...bounds.map(([low,high])=>high-low))*.57;
    this.draw();
  }

  rotate(x,y) {
    if(!this.rotation)return;
    this.projected.clear();
    const a=Math.cos(x),b=Math.sin(x),c=Math.cos(y),d=Math.sin(y);
    this.rotation=multiply([a,0,b,0,1,0,-b,0,a],multiply([1,0,0,0,c,-d,0,d,c],this.rotation));this.draw();
  }

  zoomBy(factor) {
    this.zoom=Math.max(.3,Math.min(6,this.zoom*factor));
    this.draw();
  }

  setSelection(rows) {
    this.selection=rows;
    const selected=new Set(rows.map(row=>row.index));
    for(const mesh of this.meshes){
      const values=Float32Array.from(mesh.labels,index=>!rows.length||selected.has(index)?1:0);
      this.gl.bindBuffer(this.gl.ARRAY_BUFFER,mesh.selectionBuffer);
      this.gl.bufferSubData(this.gl.ARRAY_BUFFER,0,values);
    }
    this.draw();
  }

  draw() {
    if(this.frame!==undefined)return;
    this.frame=requestAnimationFrame(()=>{this.frame=undefined;this.render();});
  }

  render() {
    if(!this.visible)return;
    const gl=this.gl, canvas=this.canvas, box=canvas.getBoundingClientRect();
    if(!box.width||!box.height){this.onRender?.();return;}
    const scale=Math.min(window.devicePixelRatio||1,2);
    const width=Math.round(box.width*scale),height=Math.round(box.height*scale);
    if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;}
    gl.viewport(0,0,width,height);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(this.program);
    const aspect=width/height;
    this.extent=[this.radius*Math.max(1,aspect)/this.zoom,this.radius*Math.max(1,1/aspect)/this.zoom];
    gl.uniformMatrix3fv(this.uniforms.rotation,false,[0,3,6,1,4,7,2,5,8].map(i=>this.rotation[i]));
    gl.uniform3fv(this.uniforms.center,this.center);gl.uniform2fv(this.uniforms.extent,this.extent);
    gl.uniform1f(this.uniforms.depth,this.radius*8);
    const passes=this.layer==='insula'?[['indices',.10],['insulaIndices',1]]:[['indices',1]];
    for(const [key,opacity] of passes){
      gl.depthMask(opacity===1);
      if(opacity<1){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);}else gl.disable(gl.BLEND);
      gl.uniform1f(this.uniforms.opacity,opacity);
      for(const mesh of this.visible){
        gl.bindVertexArray(mesh.vao);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,mesh[key+'Buffer']);
        gl.drawElements(gl.TRIANGLES,mesh[key].length,gl.UNSIGNED_INT,0);
      }
    }
    gl.depthMask(true);gl.disable(gl.BLEND);
    this.onRender?.();
  }

  projectedVertices(mesh, projection=this) {
    if(!projection.projected.has(mesh)){
      const p=mesh.positions,r=projection.rotation,c=projection.center,points=new Float32Array(p.length);
      for(let i=0;i<p.length;i+=3){const x=p[i]-c[0],y=p[i+1]-c[1],z=p[i+2]-c[2];
        for(let axis=0;axis<3;axis++)points[i+axis]=r[axis*3]*x+r[axis*3+1]*y+r[axis*3+2]*z;}
      projection.projected.set(mesh,points);
    }
    return projection.projected.get(mesh);
  }

  surfaceHit(x,y,meshes=this.visible,snap=false,projection=this) {
    let hit=null,depth=-Infinity;
    for(const mesh of meshes){
      const indices=projection===this&&this.layer==='insula'?mesh.insulaIndices:mesh.indices;
      const projected=this.projectedVertices(mesh,projection);
      for(let i=0;i<indices.length;i+=3){
        const a=indices[i]*3,b=indices[i+1]*3,c=indices[i+2]*3;
        const ax=projected[a],ay=projected[a+1],bx=projected[b],by=projected[b+1],cx=projected[c],cy=projected[c+1];
        if(x<Math.min(ax,bx,cx)||x>Math.max(ax,bx,cx)||y<Math.min(ay,by,cy)||y>Math.max(ay,by,cy))continue;
        const denominator=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy);
        if(denominator===0)continue;
        const u=((by-cy)*(x-cx)+(cx-bx)*(y-cy))/denominator;
        const v=((cy-ay)*(x-cx)+(ax-cx)*(y-cy))/denominator,w=1-u-v;
        if(u<0||v<0||w<0)continue;
        const z=u*projected[a+2]+v*projected[b+2]+w*projected[c+2];
        if(z>depth){depth=z;hit={mesh,vertices:[a/3,b/3,c/3],point:[0,1,2].map(axis=>u*mesh.positions[a+axis]+v*mesh.positions[b+axis]+w*mesh.positions[c+axis])};}
      }
    }
    if(!hit&&snap){
      let distance=Infinity;
      for(const mesh of meshes){const points=this.projectedVertices(mesh,projection);
        for(let i=0;i<points.length;i+=3){const d=(points[i]-x)**2+(points[i+1]-y)**2;
          if(d<distance){distance=d;hit={mesh,vertices:[i/3],point:Array.from(mesh.positions.subarray(i,i+3))};}}
      }
      if(hit){const [px,py]=projectPoint(hit.point,projection.rotation,projection.center);return this.surfaceHit(px,py,meshes,false,projection)||hit;}
    }
    return hit;
  }

  anchor(u,v,hemisphere,view) {
    const bilateral=['dorsal','ventral'].includes(view),key=view+':'+(bilateral?'both':hemisphere);
    this.anchorViews??=new Map();
    if(!this.anchorViews.has(key)){
      const projection={rotation:viewRotation(view,hemisphere),center:[0,0,0],projected:new Map()};
      const cortex=this.meshes.filter(mesh=>mesh.structure==='cortex'&&(bilateral||mesh.hemisphere===hemisphere));
      const bounds=[Infinity,-Infinity,Infinity,-Infinity];
      for(const mesh of cortex){const points=this.projectedVertices(mesh,projection);
        for(let i=0;i<points.length;i+=3){bounds[0]=Math.min(bounds[0],points[i]);bounds[1]=Math.max(bounds[1],points[i]);bounds[2]=Math.min(bounds[2],points[i+1]);bounds[3]=Math.max(bounds[3],points[i+1]);}}
      this.anchorViews.set(key,{projection,cortex,bounds});
    }
    const {projection,cortex,bounds}=this.anchorViews.get(key);
    return this.nodeFromHit(this.surfaceHit(bounds[0]+u*(bounds[1]-bounds[0]),bounds[3]-v*(bounds[3]-bounds[2]),
      cortex.filter(mesh=>mesh.hemisphere===hemisphere),true,projection));
  }

  nodeFromHit(hit) {
    if(!hit)return;
    const {mesh,point,vertices}=hit;
    const distance=vertex=>[0,1,2].reduce((sum,axis)=>sum+(mesh.positions[vertex*3+axis]-point[axis])**2,0);
    const vertex=vertices.reduce((nearest,index)=>distance(index)<distance(nearest)?index:nearest);
    return {hemisphere:mesh.hemisphere,node_space:mesh.node_space,vertex_count:mesh.vertices,vertex};
  }

  nodePoint(node) {
    const mesh=this.meshes.find(mesh=>mesh.structure==='cortex'&&mesh.hemisphere===node.hemisphere);
    if(!mesh||mesh.node_space!==node.node_space||mesh.vertices!==node.vertex_count
        ||!Number.isInteger(node.vertex)||node.vertex<0||node.vertex>=mesh.vertices)return null;
    return mesh.positions.subarray(node.vertex*3,node.vertex*3+3);
  }

  clearLabels(markers) {
    cancelAnimationFrame(this.labelFrame);this.labelsPending=false;
    for(const marker of markers)if(marker.patch){this.gl.deleteBuffer(marker.patch.buffer);this.gl.deleteQuery(marker.patch.query);}
  }

  labelVisibility(markers) {
    const gl=this.gl;
    if(this.labelsPending||gl.isContextLost())return;
    // Query the node's incident faces against the surface's existing depth buffer.
    // Identical triangles and LEQUAL avoid a depth bias or a second surface render.
    for(const mesh of this.visible.filter(mesh=>mesh.structure==='cortex')){
      const pending=new Map();
      for(const marker of markers)if(marker.node?.hemisphere===mesh.hemisphere&&this.nodePoint(marker.node)){
        if(marker.patch?.vertex===marker.node.vertex)continue;
        if(marker.patch){gl.deleteBuffer(marker.patch.buffer);gl.deleteQuery(marker.patch.query);}
        if(!pending.has(marker.node.vertex))pending.set(marker.node.vertex,{indices:[],markers:[]});
        pending.get(marker.node.vertex).markers.push(marker);
      }
      if(!pending.size)continue;
      for(let i=0;i<mesh.indices.length;i+=3)for(let corner=0;corner<3;corner++)
        pending.get(mesh.indices[i+corner])?.indices.push(mesh.indices[i],mesh.indices[i+1],mesh.indices[i+2]);
      for(const [vertex,entry] of pending)for(const marker of entry.markers){
        const buffer=gl.createBuffer();gl.bindVertexArray(mesh.vao);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,buffer);
        gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,Uint32Array.from(entry.indices),gl.STATIC_DRAW);
        marker.patch={vertex,mesh,buffer,count:entry.indices.length,query:gl.createQuery()};
      }
    }
    const candidates=markers.filter(marker=>marker.patch&&this.visible.includes(marker.patch.mesh));
    if(!candidates.length)return;
    const rotation=this.rotation,zoom=this.zoom,width=this.canvas.width,height=this.canvas.height;
    gl.colorMask(false,false,false,false);gl.depthMask(false);gl.depthFunc(gl.LEQUAL);
    for(const {patch} of candidates){
      gl.bindVertexArray(patch.mesh.vao);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,patch.buffer);
      gl.beginQuery(gl.ANY_SAMPLES_PASSED,patch.query);
      gl.drawElements(gl.TRIANGLES,patch.count,gl.UNSIGNED_INT,0);gl.endQuery(gl.ANY_SAMPLES_PASSED);
    }
    gl.colorMask(true,true,true,true);gl.depthMask(true);gl.depthFunc(gl.LESS);
    this.labelsPending=true;
    const finish=()=>{
      if(gl.isContextLost()){this.labelsPending=false;return;}
      if(!gl.getQueryParameter(candidates.at(-1).patch.query,gl.QUERY_RESULT_AVAILABLE)){
        this.labelFrame=requestAnimationFrame(finish);return;
      }
      for(const marker of candidates)marker.button.hidden=!gl.getQueryParameter(marker.patch.query,gl.QUERY_RESULT);
      this.labelsPending=false;
      if(rotation!==this.rotation||zoom!==this.zoom||width!==this.canvas.width||height!==this.canvas.height
          ||candidates.some(marker=>marker.patch.vertex!==marker.node.vertex))this.draw();
    };
    this.labelFrame=requestAnimationFrame(finish);
  }

  hitAt(clientX,clientY,snap=false,meshes=this.visible) {
    if(!this.extent)return;
    const box=this.canvas.getBoundingClientRect();
    return this.surfaceHit((2*(clientX-box.left)/box.width-1)*this.extent[0],
      (1-2*(clientY-box.top)/box.height)*this.extent[1],meshes,snap);
  }

  pick(clientX,clientY) {
    if(!this.pickingEnabled)return;
    const hit=this.hitAt(clientX,clientY);
    if(!hit)return;
    const indices=[...new Set(hit.vertices.map(vertex=>hit.mesh.labels[vertex]))];
    this.onPick(indices.map(index=>({index})));
  }
}

export class SurfacePanel {
  constructor(host, catalogue, onViewChange, onSelection, onClear) {
    this.host=host;this.catalogue=catalogue;this.palette=new Map(catalogue.palette.map(row=>[row.index,row]));
    this.onViewChange=onViewChange;this.onSelection=onSelection;this.selection=[];this.groups=catalogue.groups||[];this.groupSelection=[];
    try{this.markerPositions=JSON.parse(localStorage.getItem('atlas-brodmann-positions')||'{}');}catch{this.markerPositions={};}
    try{this.markerNodes=JSON.parse(localStorage.getItem('atlas-brodmann-nodes')||'{}');}catch{this.markerNodes={};}
    const defaults=catalogue.label_assignments;
    if(defaults){
      let revision;try{revision=localStorage.getItem('atlas-brodmann-label-revision');}catch{}
      if(revision!==defaults.revision){
        this.markerNodes=Object.fromEntries(defaults.labels.map(({anchor_key,...node})=>[anchor_key,node]));
        this.saveLabelAssignments();
        try{localStorage.setItem('atlas-brodmann-label-revision',defaults.revision);}catch{}
      }
    }
    this.markers=[];
    host.innerHTML=`<div class="surface-toolbar"><label><select class="surface-atlas" aria-label="Atlas"><option value="dkt40">DKT40 Atlas</option><option value="brodmann">Brodmann Labels</option></select></label><div class="surface-roi"><span>Cortical Region of Interest</span><details class="surface-regions"><summary>All Regions</summary><div class="surface-region-menu"><input type="search" aria-label="Search cortical regions" placeholder="Search regions…"><div class="surface-region-list"></div></div></details></div><button type="button" class="surface-clear">Clear selection</button><button type="button" class="surface-reset">Reset view</button></div><div class="surface-stage"><div class="surface-plates" hidden></div><canvas tabindex="0" aria-label="DKT40 cortical surface. Drag or use arrow keys to rotate; pinch, scroll, or use plus and minus to zoom. "></canvas><div class="surface-ba-labels"></div></div><div class="surface-status" role="status">Loading surfaces…</div><div class="surface-boundary"></div><div class="surface-help">Drag to rotate · pinch or scroll to zoom · tap regions to select</div>`;
    this.canvas=host.querySelector('canvas');this.status=host.querySelector('.surface-status');
    this.atlas=host.querySelector('.surface-atlas');this.layer='all';this.options=[];this.brodmannSelection=new Set();
    const labelControls=document.createElement('div');labelControls.className='surface-label-controls';
    labelControls.innerHTML='<span>Approximate positions. Tap to select. To move or remove one, turn on Edit labels, then drag it or select it and choose Remove label.</span>';
    host.querySelector('.surface-stage').after(labelControls);
    const editControl=document.createElement('div');editControl.innerHTML='<label><input type="checkbox"> Edit labels</label>';
    labelControls.after(editControl);editControl.className='surface-label-controls';this.editControl=editControl;
    this.editToggle=editControl.querySelector('input');
    this.removeLabel=document.createElement('button');this.removeLabel.type='button';this.removeLabel.textContent='Remove label';this.removeLabel.disabled=true;this.removeLabel.hidden=true;
    this.restoreLabels=document.createElement('button');this.restoreLabels.type='button';this.restoreLabels.textContent='Restore removed labels';this.restoreLabels.hidden=true;
    editControl.append(this.removeLabel,this.restoreLabels);
    this.editToggle.addEventListener('change',()=>{
      host.querySelector('.surface-stage').classList.toggle('surface-edit-labels',this.editToggle.checked);
      this.removeLabel.hidden=this.restoreLabels.hidden=!this.editToggle.checked;
      this.selectLabelForEditing(null);
    });
    this.removeLabel.addEventListener('click',()=>{
      const marker=this.editingMarker;if(!marker)return;
      this.markerNodes[marker.nodeKey]={...this.markerNodes[marker.nodeKey],label:marker.label,view:marker.view,hemisphere:marker.hemisphere,hidden:true};
      this.saveLabelAssignments();this.setBrodmann(...this.brodmannArgs);
    });
    this.restoreLabels.addEventListener('click',()=>{
      this.restoredKeys=Object.keys(this.markerNodes).filter(key=>this.markerNodes[key].hidden);
      for(const node of Object.values(this.markerNodes))delete node.hidden;
      this.saveLabelAssignments();this.setBrodmann(...this.brodmannArgs);
      undoRestore.hidden=false;
    });
    const undoRestore=document.createElement('button');undoRestore.type='button';undoRestore.textContent='Undo restore';undoRestore.hidden=true;editControl.append(undoRestore);
    undoRestore.addEventListener('click',()=>{
      for(const key of this.restoredKeys||[])this.markerNodes[key].hidden=true;
      this.saveLabelAssignments();this.setBrodmann(...this.brodmannArgs);undoRestore.hidden=true;
    });
    const exportButton=document.createElement('button');exportButton.type='button';exportButton.textContent='Export node assignments';editControl.append(exportButton);
    exportButton.addEventListener('click',()=>{
      const data=this.labelAssignments();
      const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
      const link=document.createElement('a');link.href=url;link.download='cortical-label-positions.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    });
    for(const mesh of catalogue.meshes)for(const index of Object.keys(mesh.label_counts).map(Number)) {
      if(this.palette.get(index).name!=='unknown'&&!this.options.some(row=>row.index===index))this.options.push({index});
    }
    this.options.sort((a,b)=>this.palette.get(a.index).name.localeCompare(this.palette.get(b.index).name));
    const list=host.querySelector('.surface-region-list');
    for(const group of this.groups){
      const label=document.createElement('label'),input=document.createElement('input');
      label.className='surface-group';input.type='checkbox';input.dataset.group=group.id;
      label.append(input,document.createTextNode(group.label+' lobe'));list.append(label);
      input.addEventListener('change',()=>{
        this.groupSelection=input.checked?[...this.groupSelection,group.id]:this.groupSelection.filter(id=>id!==group.id);
        this.select(this.selection);
      });
    }
    for(const row of this.options){
      const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.value=String(row.index);
      label.append(input,document.createTextNode(this.label(row)));list.append(label);
      input.addEventListener('change',()=>this.toggle(row));
    }
    for(const row of catalogue.brodmann){
      const label=document.createElement('label'),input=document.createElement('input');
      label.dataset.atlas='brodmann';input.type='checkbox';input.dataset.anatomy=row.id;
      label.append(input,document.createTextNode(row.label+(row.area_name?' — '+row.area_name:'')));list.append(label);
    }
    this.regionSearch=host.querySelector('input[type=search]');
    this.regionSearch.addEventListener('input',()=>this.filterRegionMenu());
    const menu=host.querySelector('.surface-regions');
    document.addEventListener('pointerdown',event=>{if(menu.open&&!menu.contains(event.target))menu.open=false;});
    menu.addEventListener('keydown',event=>{if(event.key==='Escape'){menu.open=false;menu.querySelector('summary').focus();}});
    this.atlas.addEventListener('change',()=>{
      this.regionSearch.value='';this.host.querySelector('.surface-boundary').replaceChildren();
      this.syncRegionMenu();this.filterRegionMenu();
      this.onViewChange(this.view,this.hemisphere);
    });
    this.syncRegionMenu();this.filterRegionMenu();
    host.querySelector('.surface-clear').addEventListener('click',onClear);
    host.querySelector('.surface-reset').addEventListener('click',()=>this.update(true));
    this.ready=Promise.all(catalogue.meshes.map(mesh=>loadMesh(mesh,this.palette))).then(meshes=>{
      this.renderer=new SurfaceCanvas(this.canvas,meshes,(rows,error)=>{
        if(error){this.status.textContent=error;return;}
        if(rows.some(row=>this.palette.get(row.index).name==='unknown'))return;
        const boundary=host.querySelector('.surface-boundary');boundary.replaceChildren();
        if(rows.length===1)this.toggle(rows[0]);
        else{
          this.status.textContent='Region boundary — choose an adjacent region:';
          for(const row of rows){const button=document.createElement('button');button.type='button';button.textContent=this.label(row);button.addEventListener('click',()=>this.toggle(row));boundary.append(button);}
        }
      });
      this.renderer.onRender=()=>{
        this.layoutLabels();
        if(!this.canvas.hidden&&this.layer==='all')this.renderer.labelVisibility(this.markers);
      };
      host.dataset.ready='true';this.select(this.selection,false);this.update();
    }).catch(error=>{this.status.textContent=error.message;host.dataset.error='true';});
  }

  saveLabelAssignments() {
    try{localStorage.setItem('atlas-brodmann-positions',JSON.stringify(this.markerPositions));localStorage.setItem('atlas-brodmann-nodes',JSON.stringify(this.markerNodes));}catch{}
  }
  labelAssignments() {
    return {format:'cortical-label-nodes-1',index_base:0,labels:Object.entries(this.markerNodes).map(([anchor_key,node])=>({...node,anchor_key}))};
  }
  selectLabelForEditing(marker) {
    this.editingMarker=this.editToggle.checked?marker:null;
    for(const entry of this.markers)entry.button.dataset.editing=String(entry===this.editingMarker);
    this.removeLabel.disabled=!this.editingMarker;
    this.removeLabel.textContent=this.editingMarker?`Remove BA ${marker.label} (${marker.hemisphere}, ${marker.view})`:'Remove label';
    this.restoreLabels.disabled=!Object.values(this.markerNodes).some(node=>node.hidden);
  }
  label(row) {const name=this.palette.get(row.index).name;return name[0].toUpperCase()+name.slice(1);}
  toggle(row) {
    const selected=this.selection.some(value=>value.index===row.index);
    this.select(selected?this.selection.filter(value=>value.index!==row.index):[...this.selection,{index:row.index}]);
  }
  filterRegionMenu() {
    const query=this.regionSearch.value.toLowerCase().replace(/[^a-z0-9]/g,'');
    for(const label of this.host.querySelector('.surface-region-list').children)
      label.hidden=(label.dataset.atlas||'dkt40')!==this.atlas.value||!label.textContent.toLowerCase().replace(/[^a-z0-9]/g,'').includes(query);
  }
  syncRegionMenu(anatomy) {
    if(anatomy)this.brodmannSelection=new Set(anatomy);
    const brodmann=this.atlas.value==='brodmann',keys=new Set(this.selection.map(row=>row.index));
    for(const checkbox of this.host.querySelectorAll('.surface-region-list input'))
      checkbox.checked=checkbox.dataset.anatomy?this.brodmannSelection.has(checkbox.dataset.anatomy):checkbox.dataset.group?this.groupSelection.includes(checkbox.dataset.group):keys.has(Number(checkbox.value));
    const count=brodmann?this.catalogue.brodmann.filter(row=>this.brodmannSelection.has(row.id)).length:this.selection.length+this.groupSelection.length;
    this.host.querySelector('.surface-roi > span').textContent=brodmann?'Brodmann Labels':'Cortical Region of Interest';
    this.host.querySelector('.surface-regions summary').textContent=count?count+' selected':brodmann?'All Labels':'All Regions';
    this.regionSearch.setAttribute('aria-label',brodmann?'Search Brodmann labels':'Search cortical regions');
    this.regionSearch.placeholder=brodmann?'Search labels…':'Search regions…';
  }
  setGroups(ids) {
    if(JSON.stringify(ids)===JSON.stringify(this.groupSelection))return;
    this.groupSelection=ids;this.select(this.selection,false);
  }
  select(rows,notify=true) {
    this.selection=rows;
    this.host.querySelector('.surface-boundary').replaceChildren();
    this.syncRegionMenu();
    const groups=this.groups.filter(group=>this.groupSelection.includes(group.id));
    const count=rows.length+groups.length;
    this.status.textContent=count?[...groups.map(group=>group.label+' lobe'),...rows.map(row=>this.label(row))].join(' + '):'DKT40 · All Regions';
    const members=new Set(groups.flatMap(group=>group.anatomy_ids));
    this.renderer?.setSelection([...rows,...this.options.filter(row=>members.has(this.palette.get(row.index).anatomy_id))]);
    if(notify)this.onSelection(rows.map(row=>({...row,...this.palette.get(row.index)})),this.groupSelection);
  }
  setView(view,hemisphere) {this.view=view;this.hemisphere=hemisphere;this.update();}
  setBrodmann(markers,selected,image,views) {
    this.brodmannArgs=[markers,selected,image,views];
    const editingKey=this.editingMarker?.nodeKey;
    const overlay=this.host.querySelector('.surface-ba-labels');overlay.replaceChildren();
    this.renderer?.clearLabels(this.markers);
    this.markers=[];
    if(!this.canvas.hidden){
      const hemispheres=['dorsal','ventral'].includes(this.view)?['left','right']:[this.hemisphere];
      markers=views.flatMap(plate=>hemispheres.flatMap(hemisphere=>plate.markers
        .filter(marker=>(!plate.bilateral||marker.hemisphere===hemisphere)&&!(plate.view==='medial'&&marker.short_label==='8v'))
        .map(marker=>{
          const frame=plate.image;
          let u=(marker.x-frame.x)/(frame.width??frame.w);
          if(plate.view==='ventral'||(!plate.bilateral&&((hemisphere==='right')!==(plate.view==='medial'))))u=1-u;
          return {...marker,hemisphere,view:plate.view,normalized:[u,(marker.y-frame.y)/(frame.height??frame.h)]};
        })));
    }
    for(const marker of markers){
      if(!Number.isFinite(Number(marker.x))||!Number.isFinite(Number(marker.y)))continue;
      const key=[this.layer,this.view,this.hemisphere,marker.hemisphere,marker.short_label].join(':');
      const nodeKey=[marker.view||this.view,marker.hemisphere||this.hemisphere,marker.short_label].join(':');
      if(this.markerNodes[nodeKey]?.hidden)continue;
      const normalized=marker.normalized||[(marker.x-image.x)/image.width,(marker.y-image.y)/image.height];
      const position=this.markerPositions[key]||normalized.map(value=>value*100);
      const button=document.createElement('button');button.type='button';button.className='surface-ba';
      button.hidden=!this.canvas.hidden;button.dataset.view=marker.view||this.view;
      const number=document.createElement('span');number.className='surface-ba-number';number.textContent=marker.short_label;button.append(number);
      button.setAttribute('aria-label',`Brodmann area ${marker.short_label}`);
      if(marker.count!==null&&marker.count!==undefined){const count=document.createElement('sup');count.className='surface-ba-count';count.textContent=marker.count;count.title=`${marker.count} linked results`;number.append(count);}
      button.setAttribute('aria-pressed',String(selected.has(marker.anatomy_id)));
      if(marker.anatomy_id)button.dataset.anatomy=marker.anatomy_id;
      const entry={nodeKey,button,position,normalized,hemisphere:marker.hemisphere||this.hemisphere,label:marker.short_label,view:marker.view||this.view,node:Number.isInteger(this.markerNodes[nodeKey]?.vertex)?this.markerNodes[nodeKey]:undefined};
      this.markers.push(entry);
      let drag=null,moved=false;
      button.addEventListener('pointerdown',event=>{
        moved=false;
        if(event.pointerType==='touch'&&!this.canvas.hidden&&!this.host.querySelector('.surface-stage').classList.contains('surface-edit-labels'))return;
        if(event.button!==0)return;event.stopPropagation();button.setPointerCapture(event.pointerId);
        if(this.editToggle.checked)this.selectLabelForEditing(entry);
        const box=overlay.getBoundingClientRect(),label=button.getBoundingClientRect();
        drag={x:event.clientX,y:event.clientY,left:label.x+label.width/2-box.x,top:label.y+label.height/2-box.y};moved=false;
      });
      button.addEventListener('pointermove',event=>{
        if(!drag)return;
        if(Math.hypot(event.clientX-drag.x,event.clientY-drag.y)<=3&&!moved)return;
        moved=true;
        button.style.left=`${drag.left+event.clientX-drag.x}px`;
        button.style.top=`${drag.top+event.clientY-drag.y}px`;
      });
      button.addEventListener('pointerup',()=>{
        if(moved){
          const label=button.getBoundingClientRect(),x=label.x+label.width/2,y=label.y+label.height/2;
          if(this.canvas.hidden){
            const box=this.imageBounds();
            position[0]=(x-box.x)/box.width*100;position[1]=(y-box.y)/box.height*100;
            this.markerPositions[key]=position;
          }else{
            const meshes=this.renderer.visible.filter(mesh=>mesh.structure==='cortex'&&mesh.hemisphere===entry.node?.hemisphere);
            const node=this.renderer.nodeFromHit(this.renderer.hitAt(x,y,true,meshes));
            if(node)entry.node=this.markerNodes[nodeKey]={...node,label:entry.label,view:entry.view};
          }
          this.saveLabelAssignments();
          this.layoutLabels();
          this.renderer?.draw();
        }
        drag=null;
      });
      for(const type of ['pointercancel','lostpointercapture'])button.addEventListener(type,()=>{drag=null;this.layoutLabels();});
      button.addEventListener('click',event=>{
        if(moved&&event.detail>0){event.preventDefault();event.stopPropagation();return;}
        if(this.editToggle.checked){event.stopPropagation();this.selectLabelForEditing(entry);return;}
        if(!marker.anatomy_id)this.status.textContent=`BA ${marker.short_label} · No evidence mapping is available yet.`;
      });
      overlay.append(button);
    }
    this.selectLabelForEditing(this.markers.find(marker=>marker.nodeKey===editingKey));
    this.layoutLabels();
    this.renderer?.draw();
  }
  imageBounds() {
    const image=this.host.querySelector('.surface-plates img'),box=image.getBoundingClientRect();
    const scale=Math.min(box.width/image.width,box.height/image.height),width=image.width*scale,height=image.height*scale;
    return {x:box.x+(box.width-width)/2,y:box.y+(box.height-height)/2,width,height};
  }
  layoutLabels() {
    if(!this.markers.length)return;
    const stage=this.host.querySelector('.surface-stage').getBoundingClientRect();
    if(this.canvas.hidden){
      const box=this.imageBounds();
      for(const {button,position} of this.markers){button.style.left=`${box.x-stage.x+box.width*position[0]/100}px`;button.style.top=`${box.y-stage.y+box.height*position[1]/100}px`;}
    }else if(this.renderer?.extent){
      for(const marker of this.markers){
        if(!marker.node){
          const node=this.renderer.anchor(...marker.normalized,marker.hemisphere,marker.view);
          if(node)marker.node=this.markerNodes[marker.nodeKey]={...node,label:marker.label,view:marker.view};
        }
        const point=marker.node&&this.renderer.nodePoint(marker.node);
        if(!point)continue;
        marker.button.dataset.vertex=String(marker.node.vertex);marker.button.dataset.hemisphere=marker.node.hemisphere;
        const [x,y]=projectPoint(point,this.renderer.rotation,this.renderer.center);
        marker.button.style.left=`${(1+x/this.renderer.extent[0])*stage.width/2}px`;
        marker.button.style.top=`${(1-y/this.renderer.extent[1])*stage.height/2}px`;
      }
    }
  }
  update(reset=false) {
    if(!this.view)return;
    const brodmann=this.atlas.value==='brodmann';
    this.host.querySelector('.surface-ba-labels').hidden=!brodmann;
    this.host.querySelector('.surface-label-controls > span').hidden=!brodmann;
    this.host.querySelector('.surface-stage').classList.toggle('surface-edit-labels',brodmann&&this.editToggle.checked);
    if(this.renderer)this.renderer.pickingEnabled=!brodmann;
    this.host.querySelector('.surface-help').textContent='Drag to rotate · pinch or scroll to zoom · tap '+(brodmann?'Brodmann labels':'regions')+' to select';
    const images=this.layer==='images',plates=this.host.querySelector('.surface-plates');
    this.canvas.hidden=images;plates.hidden=!images;
    this.host.querySelector('.surface-help').hidden=images;
    this.host.querySelector('.surface-reset').disabled=images;
    this.host.querySelector('.surface-label-controls').hidden=['mesial','insula'].includes(this.layer);
    this.editControl.hidden=!brodmann||['mesial','insula'].includes(this.layer);
    this.host.querySelector('.surface-stage').classList.toggle('surface-specialized',['mesial','insula'].includes(this.layer));
    if(images){
      plates.replaceChildren();
      for(const record of this.catalogue.images.filter(row=>row.view===this.view&&(row.hemisphere==='both'||row.hemisphere===this.hemisphere))){
        const image=document.createElement('img');image.src=`/local-surfaces/${encodeURIComponent(record.file)}`;
        image.alt=`DKT40 · ${record.hemisphere} · ${record.view}`;image.width=record.width;image.height=record.height;image.addEventListener('load',()=>this.layoutLabels());plates.append(image);
      }
      return;
    }
    const hemisphere=this.layer==='mesial'||['dorsal','ventral'].includes(this.view)?'both':this.hemisphere;
    this.renderer?.setView(this.view,hemisphere,this.layer,reset);
  }
}
