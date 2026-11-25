exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
from collections import Counter
from mathutils.geometry import delaunay_2d_cdt
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
assert not terrain.get('rock21_repaired'),'Already applied'
raw=np.load(str(LOG/'terrain_before.npz'));old={k:raw[k] for k in raw.files};raw.close()
oldfaces=[old['loops'][s:s+n].tolist() for s,n in zip(old['starts'],old['sizes'])]
old_bvh=BVHTree.FromPolygons([Vector(p) for p in old['positions']],oldfaces)
def oldground(x,z):
    h,*_=old_bvh.ray_cast(Vector((float(x),-float(z),80)),Vector((0,0,-1)),300)
    return h.z if h else -15
# Protect the entire actual hull envelope and the original underwater berth.
basin=0
for v in mesh.vertices:
    x,y,h=v.co;z=-y
    if 61.9<z<68.5 and x<17.6:
        w=float(smooth(61.9,62.8,z))*(1-float(smooth(16.5,17.6,x)))
        if w>0:v.co.z=h*(1-w)+oldground(x,z)*w;basin+=1
mesh.update()
# Undo only the discontinuous early x displacement around the tavern foundation.
base_src=(ROOT/'source/rock21_01_rebuild.py').read_text(encoding='utf8')
exec(base_src[base_src.index('def inside('):base_src.index('def cliff_value(')],globals())
reset=0
for v in mesh.vertices:
    x,y,h=v.co;z=-y
    if not 39<z<44.2 or not 15.5<x<18:continue
    ft=line(z,toe);ct=line(z,crown)
    if not low(z)+.03<h<high(z)-.03:continue
    # Inverse monotone original relief; foundation-band fold arises from abrupt exclusion.
    a=.12+.13*(.5+.5*math.sin(z*2.1+.5));w=float(smooth(37.8,39,z))*(1-float(smooth(62,63.3,z)))
    w*=1-.9*float(smooth(49.8,51.2,z)*(1-smooth(53,55,z)))
    if any(inside(x,z,p) or edge_distance(x,z,p)<.75 for p in floors):continue
    lo,hi=ft,ct
    for _ in range(24):
        m=(lo+hi)/2;t=(m-ft)/(ct-ft);val=m-(ct-ft)*a*math.sin(math.pi*t)*w
        if val<x:lo=m
        else:hi=m
    f=(lo+hi)/2
    fade=1-float(smooth(43.0,44.2,z))
    if f>x:v.co.x=x+(f-x)*fade;reset+=1
mesh.update()
# Re-triangulate the actual folded neighbourhood, sharing its untouched perimeter.
bad={p.index for p in mesh.polygons if p.normal.z<-.000001};chosen=set(bad)
for _ in range(2):
    vi={v for i in chosen for v in mesh.polygons[i].vertices}
    chosen|={p.index for p in mesh.polygons if set(p.vertices)&vi}
if chosen:
    ec=Counter()
    for i in chosen:
        f=list(mesh.polygons[i].vertices)
        for a,b in zip(f,f[1:]+f[:1]):ec[tuple(sorted((a,b)))]+=1
    adj={}
    for (a,b),n in ec.items():
        if n==1:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
    assert all(len(v)==2 for v in adj.values()),'Repair boundary branches'
    unseen=set(adj);rings=[]
    while unseen:
        start=min(unseen);ring=[start];pr=None;cur=start
        while True:
            nxt=next(v for v in adj[cur] if v!=pr)
            if nxt==start:break
            ring.append(nxt);pr,cur=cur,nxt
            assert len(ring)<=len(adj)
        unseen-=set(ring);rings.append(ring)
    positions=[tuple(v.co) for v in mesh.vertices];ca=mesh.color_attributes['LandUse'];cols_by_v={}
    for p in mesh.polygons:
        for li in p.loop_indices:cols_by_v[mesh.loops[li].vertex_index]=tuple(ca.data[li].color)
    ff=[];cc=[]
    for p in mesh.polygons:
        if p.index in chosen:continue
        ff.append(list(p.vertices));cc.extend(tuple(ca.data[i].color) for i in p.loop_indices)
    for ring in rings:
        outer=[positions[i][:2] for i in ring]
        internal=sorted({v for i in chosen for v in mesh.polygons[i].vertices}-set(ring))
        internal=[i for i in internal if inside(positions[i][0],positions[i][1],outer)]
        ids=ring+internal;coords=[Vector(positions[i][:2]) for i in ids]
        rv,re,rf,orig,_,_=delaunay_2d_cdt(coords,[(i,(i+1)%len(ring)) for i in range(len(ring))],[list(range(len(ring)))],1,1e-7,True)
        mapped=[]
        for i,v in enumerate(rv):
            assert orig[i],'Unexpected crossing in repair boundary'
            mapped.append(ids[orig[i][0]])
        for f in rf:
            vi=[mapped[i] for i in f];a,b,c=[Vector(positions[i]) for i in vi]
            if (b-a).cross(c-a).z<0:vi.reverse()
            ff.append(vi);cc.extend(cols_by_v[i] for i in vi)
    dm=bpy.data.meshes.new('R27_RepairedHeadland');dm.from_pydata(positions,[],ff);dm.update();dm.materials.append(mesh.materials[0])
    ca=dm.color_attributes.new(name='LandUse',type='FLOAT_COLOR',domain='CORNER');dm.color_attributes.active_color=ca;ca.data.foreach_set('color',np.asarray(cc,np.float32).ravel())
    uv=dm.uv_layers.new(name='UVMap');idx=np.array([l.vertex_index for l in dm.loops]);uv.data.foreach_set('uv',(np.asarray(positions,np.float32)[idx,:2]/2.4).ravel())
    terrain.data=dm;mesh=dm
for p in mesh.polygons:p.use_smooth=True
mesh.set_sharp_from_angle(angle=math.radians(58));mesh.update()
terrain['rock21_repaired']=True
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
refresh_height();export_land();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print(json.dumps({'berth_vertices':basin,'reset_vertices':reset,'retriangulated_faces':len(chosen),'previous_negative':len(bad)}))
