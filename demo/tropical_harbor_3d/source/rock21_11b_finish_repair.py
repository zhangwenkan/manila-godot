# Continue after the boundary-branch assertion. The earlier basin edits already exist in memory.
exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
from collections import Counter
from mathutils.geometry import delaunay_2d_cdt
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
src=(ROOT/'source/rock21_01_rebuild.py').read_text(encoding='utf8')
exec(src[src.index('def inside('):src.index('def cliff_value(')],globals())
bad={p.index for p in mesh.polygons if p.normal.z<-.000001}
# Include one entire rectangular neighbourhood, so disconnected folded pockets cannot pinch the boundary.
chosen={p.index for p in mesh.polygons if 37.8<-p.center.y<63.2 and 14.0<p.center.x<29.0}
assert bad<=chosen, str([(i,list(mesh.polygons[i].center)) for i in bad-chosen][:10])
counts=Counter()
for i in chosen:
    ids=list(mesh.polygons[i].vertices)
    for a,b in zip(ids,ids[1:]+ids[:1]):counts[tuple(sorted((a,b)))]+=1
adj={}
for (a,b),n in counts.items():
    if n==1:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
assert all(len(v)==2 for v in adj.values()),'Rectangular neighbourhood branches'
boundary=[min(adj)];pr=None;cur=boundary[0]
while True:
    nxt=next(v for v in adj[cur] if v!=pr)
    if nxt==boundary[0]:break
    boundary.append(nxt);pr,cur=cur,nxt
assert len(boundary)==len(adj),'Neighbourhood holes'
positions=[tuple(v.co) for v in mesh.vertices];ca=mesh.color_attributes['LandUse'];cv={}
for p in mesh.polygons:
    for li in p.loop_indices:cv[mesh.loops[li].vertex_index]=tuple(ca.data[li].color)
ids=boundary+sorted({v for i in chosen for v in mesh.polygons[i].vertices}-set(boundary));coords=[Vector(positions[i][:2]) for i in ids]
rv,re,rf,orig,_,_=delaunay_2d_cdt(coords,[(i,(i+1)%len(boundary)) for i in range(len(boundary))],[list(range(len(boundary)))],1,1e-7,True)
assert all(orig),'Crossed repair perimeter'
mapped=[ids[o[0]] for o in orig];ff=[];cc=[]
for p in mesh.polygons:
    if p.index in chosen:continue
    ff.append(list(p.vertices));cc.extend(tuple(ca.data[i].color) for i in p.loop_indices)
for f in rf:
    vi=[mapped[i] for i in f];a,b,c=[Vector(positions[i]) for i in vi]
    if (b-a).cross(c-a).z<0:vi.reverse()
    ff.append(vi);cc.extend(cv[i] for i in vi)
dm=bpy.data.meshes.new('R27_CliffRepairedSharedBoundary');dm.from_pydata(positions,[],ff);dm.update();dm.materials.append(mesh.materials[0])
ca=dm.color_attributes.new(name='LandUse',type='FLOAT_COLOR',domain='CORNER');dm.color_attributes.active_color=ca;ca.data.foreach_set('color',np.asarray(cc,np.float32).ravel())
uv=dm.uv_layers.new(name='UVMap');idx=np.array([l.vertex_index for l in dm.loops]);uv.data.foreach_set('uv',(np.asarray(positions,np.float32)[idx,:2]/2.4).ravel())
terrain.data=dm;mesh=dm
# Dip the exposed crown locally and rise back into the unchanged building court.
for v in mesh.vertices:
    x,y,h=v.co;z=-y
    if not 40.9<z<48.4 or h<low(z)+.03:continue
    fw=max([1 if inside(x,z,p) else 1-float(smooth(.30,.95,edge_distance(x,z,p))) for p in floors]+[0])
    dip=.82*float(smooth(40.9,43,z)*(1-smooth(46.3,48.4,z)))
    back=1-float(smooth(line(z,crown)+.1,line(z,crown)+3.2,x))
    q=float(np.clip((h-low(z))/(high(z)-low(z)),0,1))
    v.co.z-=dip*back*q**.7*(1-fw)
for p in mesh.polygons:p.use_smooth=True
mesh.set_sharp_from_angle(angle=math.radians(58));mesh.update()
terrain['rock21_repaired']=True
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
refresh_height();export_land();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print(json.dumps({'repaired_faces':len(chosen),'negative_before':len(bad),'saved':True}))
