exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
from collections import Counter
from mathutils.geometry import delaunay_2d_cdt
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
assert not terrain.get('rock21_soil_patch'),'Already applied'
src=(ROOT/'source/rock21_01_rebuild.py').read_text(encoding='utf8')
exec(src[src.index('def inside('):src.index('def cliff_value(')],globals())
def ss(a,b,t):
    t=max(0.,min(1.,(t-a)/(b-a)));return t*t*(3-2*t)
chosen={p.index for p in mesh.polygons if 9.2<p.center.x<13.7 and 58.9<-p.center.y<62.15}
counts=Counter()
for i in chosen:
    f=list(mesh.polygons[i].vertices)
    for a,b in zip(f,f[1:]+f[:1]):counts[tuple(sorted((a,b)))]+=1
adj={}
for (a,b),n in counts.items():
    if n==1:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
assert all(len(v)==2 for v in adj.values()),'Soil perimeter branches'
boundary=[min(adj)];previous=None;current=boundary[0]
while True:
    nxt=next(i for i in adj[current] if i!=previous)
    if nxt==boundary[0]:break
    boundary.append(nxt);previous,current=current,nxt
assert len(boundary)==len(adj),'Soil perimeter holes'
pos=[tuple(v.co) for v in mesh.vertices];ca=mesh.color_attributes['LandUse'];cv={}
for p in mesh.polygons:
    for li in p.loop_indices:cv[mesh.loops[li].vertex_index]=tuple(ca.data[li].color)
outer=[(pos[i][0],-pos[i][1]) for i in boundary]
ids=boundary.copy();coords=[Vector(pos[i][:2]) for i in ids]
for z in np.arange(58.95,62.2,.18):
    for x in np.arange(9.25,13.75,.18):
        if not inside(x,z,outer) or edge_distance(x,z,outer)<.12:continue
        h=ground(float(x),float(z));w=ss(9.3,9.7,x)*(1-ss(13.0,13.65,x))*ss(58.9,59.6,z)*(1-ss(61.6,62.15,z))
        t=ss(9.6,14,x);target=.24+.94*t
        ids.append(len(pos));coords.append(Vector((x,-z)));pos.append((x,-z,h*(1-w)+target*w))
        g=ss(.28,.58,t);earth=ss(.09,.22,t)*(1-g)
        cv[ids[-1]]=(g,0,0,earth)
rv,re,rf,orig,_,_=delaunay_2d_cdt(coords,[(i,(i+1)%len(boundary)) for i in range(len(boundary))],[list(range(len(boundary)))],1,1e-7,True)
assert all(orig),'Crossing soil perimeter'
mapping=[ids[o[0]] for o in orig];ff=[];cc=[]
for p in mesh.polygons:
    if p.index in chosen:continue
    ff.append(list(p.vertices));cc.extend(tuple(ca.data[i].color) for i in p.loop_indices)
for f in rf:
    vi=[mapping[i] for i in f];a,b,c=[Vector(pos[i]) for i in vi]
    if (b-a).cross(c-a).z<0:vi.reverse()
    ff.append(vi);cc.extend(cv[i] for i in vi)
dm=bpy.data.meshes.new('R27_RockEarthFinal_SharedCoast');dm.from_pydata(pos,[],ff);dm.update();dm.materials.append(mesh.materials[0])
col=dm.color_attributes.new(name='LandUse',type='FLOAT_COLOR',domain='CORNER');dm.color_attributes.active_color=col;col.data.foreach_set('color',np.asarray(cc,np.float32).ravel())
uv=dm.uv_layers.new(name='UVMap');idx=np.array([l.vertex_index for l in dm.loops]);uv.data.foreach_set('uv',(np.asarray(pos,np.float32)[idx,:2]/2.4).ravel())
for p in dm.polygons:p.use_smooth=True
dm.set_sharp_from_angle(angle=math.radians(62));terrain.data=dm;mesh=dm
terrain['rock21_soil_patch']=True
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
refresh_height();export_land();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print(json.dumps({'replaced_faces':len(chosen),'new_faces':len(rf),'saved':True}))
