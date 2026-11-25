# Absolute reconstruction from this pass's measured snapshot, executed in Blender MCP.
exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
from mathutils.geometry import delaunay_2d_cdt
from collections import Counter
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
assert not terrain.get('rock21_contours'),'Already applied'
raw=np.load(str(LOG/'terrain_before.npz'))
old={k:raw[k] for k in raw.files};raw.close()
oldfaces=[old['loops'][s:s+n].tolist() for s,n in zip(old['starts'],old['sizes'])]
old_bvh=BVHTree.FromPolygons([Vector(v) for v in old['positions']],oldfaces)
def oldground(x,z):
    h,*_=old_bvh.ray_cast(Vector((float(x),-float(z),80)),Vector((0,0,-1)),300)
    return h.z if h else -15
# Read definitions only: no historical operations or scene mutations.
src=(ROOT/'source/rock21_01_rebuild.py').read_text(encoding='utf8')
exec(src[src.index('def inside('):src.index('def cliff_value(')],globals())
base=[tuple(p) for p in old['positions']]
chosen=set()
for i,f in enumerate(oldfaces):
    c=np.mean(old['positions'][f],axis=0);z=-c[1]
    if 35.7<z<66 and -.02<c[0]-float(shore(z))<29:chosen.add(i)
counts=Counter()
for i in chosen:
    f=oldfaces[i]
    for a,b in zip(f,f[1:]+f[:1]):counts[tuple(sorted((a,b)))]+=1
adj={}
for (a,b),n in counts.items():
    if n==1:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
assert all(len(v)==2 for v in adj.values())
boundary=[min(adj)];prev=None;cur=boundary[0]
while True:
    nxt=next(v for v in adj[cur] if v!=prev)
    if nxt==boundary[0]:break
    boundary.append(nxt);prev,cur=cur,nxt
assert len(boundary)==len(adj)
outer=[(base[i][0],-base[i][1]) for i in boundary]

def blend_weight(x,z):
    w=float(smooth(35.8,37.8,z)*(1-smooth(63.5,65.6,z)))
    w*=float(smooth(.2,.75,x-float(shore(z))))*(1-float(smooth(27.5,28.7,x-float(shore(z)))))
    # Smooth recess behind the cargo quay: no rectangular threshold at z59.4.
    basin=float(smooth(58.1,60.25,z)*(1-smooth(64,65.5,z)))*(1-float(smooth(14.0,15.65,x)))
    return w*(1-basin)
def foundation_weight(x,z):
    return max([1 if inside(x,z,p) else 1-float(smooth(.25,.72,edge_distance(x,z,p))) for p in floors]+[0])
def crown_height(z):return high(z)+.065*math.sin(z*1.17)+.035*math.sin(z*2.63)
def profile(z):
    # Wide base, steep planes, one short staggered shoulder, rounded heavy crown.
    ledge=.41+.075*math.sin(z*.54)+.035*math.sin(z*1.37)
    return [0,.16,.24,.31,.37,.49,.55,.64,.75,.87,.94,.985,1], [0,.025,.08,.24,ledge-.04,ledge+.02,ledge+.11,.72,.88,.96,.985,.999,1]
def h_cliff(x,z):
    ft=line(z,toe);ct=line(z,crown);t=np.clip((x-ft)/(ct-ft),0,1)
    ts,qs=profile(z);q=float(np.interp(t,ts,qs))
    bay=float(smooth(49.7,51.3,z)*(1-smooth(53.1,55.1,z)))
    q=q*(1-bay*.72)+float(smooth(0,1,t))*bay*.72
    # Broad alternate rock heads; this is actual surface relief, not painted shadow.
    ridge=.085*math.sin(z*2.15+.5)*math.sin(math.pi*t)**2+.045*math.sin(z*4.1+t*7)*math.sin(math.pi*t)**2
    return low(z)+(crown_height(z)-low(z))*q+ridge
def authored(x,z):
    prev=oldground(x,z);ft=line(z,toe);ct=line(z,crown);ef=line(z,earthfoot);et=line(z,earthtop);lh=low(z)
    if x>=ct:h=crown_height(z)+.03*math.sin((x-ct)*.9)
    elif x>=ft:h=h_cliff(x,z)
    elif x>=et:h=lh
    elif x<=ef:h=min(prev,.24)
    else:
        t=(x-ef)/(et-ef)
        cut=float(smooth(38.2,39.3,z)*(1-smooth(41.2,42.5,z)))+.6*float(smooth(55.7,56.6,z)*(1-smooth(58.1,59.2,z)))
        cut=min(1,cut)
        q=float(smooth(0,1,t))*(1-cut)+float(np.interp(t,[0,.36,.49,.57,.70,.88,1],[0,.05,.12,.58,.90,.98,1]))*cut
        h=.24+(lh-.24)*q
    mouth=float(smooth(50.9,52.1,z)*(1-smooth(54.2,55.3,z)))
    if x<19:
        h=h*(1-mouth)+(.23+(lh-.23)*float(smooth(8.8,17.2,x)))*mouth
    w=blend_weight(x,z)*(1-foundation_weight(x,z))
    return prev*(1-w)+h*w
def oldcolor(x,z):
    hit,n,pi,_=old_bvh.ray_cast(Vector((x,-z,80)),Vector((0,0,-1)),300)
    if pi is None:return np.array([0,0,0,0])
    s=old['starts'][pi];n=old['sizes'][pi]
    return np.mean(old['colors'][s:s+n],axis=0)
def weights(x,z,h):
    ft=line(z,toe);ct=line(z,crown);et=line(z,earthtop);ef=line(z,earthfoot)
    prior=oldcolor(x,z);w=blend_weight(x,z)
    if x>=ft-.001 and x<=ct+.001:
        t=np.clip((x-ft)/(ct-ft),0,1)
        rock=float(smooth(.12,.24,t))*(1-float(smooth(.94,.985,t)))
        col=np.array([1-rock,rock,0,0])
    elif x>=ct:col=np.array([1,0,0,0])
    elif x<et+.25:
        t=np.clip((x-ef)/(et-ef),0,1)
        grass=float(smooth(.64,.74,t));soil=float(smooth(.18,.32,t))*(1-grass)
        col=np.array([grass,0,0,soil]) if h>.255 else np.array([0,0,0,0])
    else:
        col=prior.copy()
        if col[1]>.2 or col[3]>.4:col=np.array([1,0,0,0])
    mouth=float(smooth(51,52,z)*(1-smooth(54.2,55.3,z)))
    if x<19 and mouth>.001:
        mw=mouth*(1-float(smooth(17.7,19,x)))
        target=np.array([0,0,.08,.92])*float(smooth(.29,.70,h))
        col=col*(1-mw)+target*mw
    # Low cargo apron is soil/grass only where the surface rises, no green vertical plug.
    if 58<z<65 and x<15.65:
        blend=float(smooth(58,60.2,z))*(1-float(smooth(14,15.65,x)))
        col=col*(1-blend)+prior*blend
    return tuple(np.clip(prior*(1-w)+col*w,0,1))

ids=list(boundary);coords=[Vector(base[i][:2]) for i in ids]
edges=[(i,(i+1)%len(ids)) for i in range(len(ids))]
lookup={(round(p.x,6),round(p.y,6)):i for i,p in enumerate(coords)}
def add(x,z):
    key=(round(float(x),6),round(-float(z),6))
    if key in lookup:return lookup[key]
    if not inside(x,z,outer):return None
    i=len(coords);coords.append(Vector((x,-z)));ids.append(len(base));base.append((x,-z,authored(x,z)));lookup[key]=i;return i
for z in np.arange(36,65.8,.32):
    for x in np.arange(float(shore(z))+.18,float(shore(z))+28.8,.36):add(float(x),float(z))
# Constrained ribbons follow BOTH sides of every narrow material transition.
for kind,ts in [('rock',[0,.12,.16,.24,.31,.37,.49,.55,.64,.75,.87,.94,.985,1]),('earth',[0,.18,.32,.36,.49,.57,.64,.74,.88,1])]:
    for t in ts:
        chain=[]
        zs=sorted(set([round(float(v),5) for v in np.arange(37.1,64.8,.20)]+[p[0] for p in crown+toe+earthtop+earthfoot if 37.1<p[0]<64.8]))
        for z in zs:
            a=line(z,toe if kind=='rock' else earthfoot);b=line(z,crown if kind=='rock' else earthtop)
            i=add(a+(b-a)*t,z)
            if i is not None:chain.append(i)
        edges.extend((a,b) for a,b in zip(chain,chain[1:]) if a!=b)
rv,re,rf,orig,_,_=delaunay_2d_cdt(coords,edges,[list(range(len(boundary)))],1,1e-7,True)
mapping=[]
for i,p in enumerate(rv):
    if orig[i]:mapping.append(ids[orig[i][0]])
    else:mapping.append(len(base));base.append((p.x,p.y,authored(p.x,-p.y)))
faces=[];colors=[]
for i,f in enumerate(oldfaces):
    if i in chosen:continue
    faces.append(f);s=old['starts'][i];colors.extend(tuple(c) for c in old['colors'][s:s+len(f)])
newstart=len(faces);cache={}
for f in rf:
    vi=[mapping[i] for i in f];ps=[Vector(base[i]) for i in vi];c=(ps[1]-ps[0]).cross(ps[2]-ps[0])
    if abs(c.z)<1e-10:continue
    if c.z<0:vi.reverse()
    faces.append(vi)
    for i in vi:
        if i not in cache:
            x,y,h=base[i];cache[i]=weights(x,-y,h)
        colors.append(cache[i])
dm=bpy.data.meshes.new('R27_CliffRimRibbons_SoilCoves');dm.from_pydata(base,[],faces);dm.update();dm.materials.append(mesh.materials[0])
ca=dm.color_attributes.new(name='LandUse',type='FLOAT_COLOR',domain='CORNER');dm.color_attributes.active_color=ca;ca.data.foreach_set('color',np.asarray(colors,np.float32).ravel())
# Reconcile the old/new outer boundary to the same shared vertex role.
for p in dm.polygons:
    for li in p.loop_indices:
        i=dm.loops[li].vertex_index
        if i in cache:ca.data[li].color=cache[i]
uv=dm.uv_layers.new(name='UVMap');idx=np.array([l.vertex_index for l in dm.loops]);uv.data.foreach_set('uv',(np.asarray(base,np.float32)[idx,:2]/2.4).ravel())
for p in dm.polygons:p.use_smooth=True
dm.set_sharp_from_angle(angle=math.radians(58));terrain.data=dm;mesh=dm
terrain['rock21_contours']=True
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
refresh_height();export_land();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print(json.dumps({'authored_faces':len(faces)-newstart,'vertices':len(base),'constrained_edges':len(edges),'saved':True}))
