exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
import bmesh
from mathutils.geometry import delaunay_2d_cdt
assert not terrain.get('shore21_finished'),'Already applied'
# Lower a recessed crown locally; retain the complete travel-office bearing court.
for v in mesh.vertices:
    x,y,h=v.co;z=-y
    if 42.5<z<46.4 and 17.5<x<21.5 and h>2.4:
        weight=float(np.interp(z,[42.5,43.4,44.2,45.2,46.4],[0,.35,1,.55,0]))
        front=1-float(smooth(20.0,21.5,x))
        v.co.z-=.38*weight*front*float(smooth(2.4,3.95,h))
mesh.update()
# Repair a folded upper-court triangulation created by moving the real crest.
bad={p.index for p in mesh.polygons if p.normal.z<-.0001}
chosen=set(bad)
for _ in range(2):
    vertices={v for i in chosen for v in mesh.polygons[i].vertices}
    chosen|={p.index for p in mesh.polygons if set(p.vertices)&vertices and min(mesh.vertices[v].co.z for v in p.vertices)>3.60}
if chosen:
    counts={}
    for i in chosen:
        ids=list(mesh.polygons[i].vertices)
        for a,b in zip(ids,ids[1:]+ids[:1]):
            k=tuple(sorted((a,b)));counts[k]=counts.get(k,0)+1
    adj={}
    for (a,b),n in counts.items():
        if n==1:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
    assert all(len(v)==2 for v in adj.values())
    boundary=[min(adj)];prev=None;cur=boundary[0]
    while True:
        nxt=next(n for n in adj[cur] if n!=prev)
        if nxt==boundary[0]:break
        boundary.append(nxt);prev,cur=cur,nxt
        assert len(boundary)<=len(adj)
    assert len(boundary)==len(adj)
    coords=[Vector(mesh.vertices[i].co[:2]) for i in boundary]
    rv,re,rf,orig,_,_=delaunay_2d_cdt(coords,[(i,(i+1)%len(coords)) for i in range(len(coords))],[list(range(len(coords)))],1,1e-6,True)
    assert all(o for o in orig),'Unexpected crossing in upper court perimeter'
    verts=[tuple(v.co) for v in mesh.vertices];polys=[];cols=[];sf=[]
    for p in mesh.polygons:
        if p.index in chosen:continue
        polys.append(list(p.vertices));cols.extend(tuple(mesh.color_attributes['LandUse'].data[li].color) for li in p.loop_indices);sf.append(p.use_smooth)
    for f in rf:
        vi=[boundary[orig[i][0]] for i in f];ps=[Vector(verts[i]) for i in vi]
        if (ps[1]-ps[0]).cross(ps[2]-ps[0]).z<0:vi.reverse()
        polys.append(vi);cols.extend([(1,0,0,0)]*len(vi));sf.append(True)
    dm=bpy.data.meshes.new('C26_UpperCourtRetriangulated');dm.from_pydata(verts,[],polys);dm.update();dm.materials.append(mesh.materials[0])
    ca=dm.color_attributes.new(name='LandUse',type='FLOAT_COLOR',domain='CORNER');dm.color_attributes.active_color=ca;ca.data.foreach_set('color',np.asarray(cols,np.float32).ravel())
    uv=dm.uv_layers.new(name='UVMap');idx=np.empty(len(dm.loops),np.int32);dm.loops.foreach_get('vertex_index',idx);uv.data.foreach_set('uv',(np.asarray(verts,np.float32)[idx,:2]/2.4).ravel())
    for p,s in zip(dm.polygons,sf):p.use_smooth=s
    terrain.data=dm;mesh=dm

# Round off the inlet's two earth shoulders in plan and height, keeping shop foundations fixed.
for v in mesh.vertices:
    x,y,h=v.co;z=-y;d=x-float(shore(z))
    if not 51.0<z<55.5 or not 1.2<d<6.2:continue
    center_z=float(np.interp(d,[1.25,3.1,4.8,6.5],[53.0,53.15,53.45,53.55]))
    half=float(np.interp(d,[1.25,3.1,4.8,6.5],[1.82,1.65,1.30,1.02]))
    distance=abs(z-center_z)
    if half-.02<distance<half+.85 and h>.34:
        w=(1-float(smooth(half,half+.85,distance)))*float(smooth(1.2,3.1,d))*(1-float(smooth(5.1,6.2,d)))
        target=float(np.interp(d,[1.25,3.1,4.8,6.5],[.27,.34,.53,.87]))+.08
        v.co.z=h*(1-w*.65)+target*w*.65
mesh.update()
attr=mesh.color_attributes['LandUse']
for p in mesh.polygons:
    x,y,h=p.center;z=-y;d=x-float(shore(z))
    if 51<z<55.5 and 2<d<6.5:
        if p.normal.z<.87:
            for li in p.loop_indices:attr.data[li].color=(0,0,0,1)
        p.use_smooth=True
mesh.set_sharp_from_angle(angle=math.radians(35))
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())

# Move the complete supply stack off the through-route into the eastern side of the yard.
coast=bpy.data.collections['Reference_Coast'];moved=[]
stack=[]
for o in coast.objects:
    c=center(o)
    if 52.7<-c.y<54.5 and 15.9<c.x<17.85 and o.name.startswith(('S20_shop_','S20_shopStack_','S20_shopRope_','S20_SupplySack_')):stack.append(o)
for o in stack:o.location.x+=2.05
bpy.context.view_layer.update()
base=[o for o in stack if o.name.startswith(('S20_shop_Prop_Crate','S20_shop_Prop_Barrel','S20_SupplySack'))]
dh=max(ground(center(o).x,-center(o).y)-bounds(o)[2][0] for o in base)+.005
for o in stack:o.location.z+=dh;moved.append(o.name)
# Reposition a bench at the upper end of the yard, clear of restaurant walls.
bench=[o for o in coast.objects if o.name.startswith('S20_ShadeBench')]
for o in bench:o.location.x+=2.5;o.location.y-=1.7
bpy.context.view_layer.update()
supports=[o for o in bench if 'Support' in o.name]
dh=max(ground(center(o).x,-center(o).y)-bounds(o)[2][0] for o in supports)
for o in bench:o.location.z+=dh;moved.append(o.name)

fol=bpy.data.collections['Reference_Foliage']
def place(o,x,z,scale=1,embed=.08):
    c=center(o);o.scale*=scale;bpy.context.view_layer.update();o.location.x+=x-c.x;o.location.y+=-z-c.y;bpy.context.view_layer.update()
    b=bounds(o);o.location.z+=ground(x,z)-b[2][0]-embed
    moved.append(o.name)
# A few overlapping shrubs establish the shelf as ground, rather than a green stripe.
for name,x,z,scale in [('S20_CourtyardShrub.036',17.75,44.10,1.4),('S20_CourtyardShrub.037',18.45,44.95,1.35),('S20_CourtyardShrub.038',18.10,44.55,1.45),('S20_CourtyardShrub.039',17.25,43.90,1.2)]:
    place(bpy.data.objects[name],x,z,scale)
for name,x,z in [('S20_CourtyardShrub',20.2,54.0),('S20_CourtyardShrub.001',19.85,54.65),('S20_CourtyardShrub.002',20.8,54.4),('S20_CourtyardShrub.003',20.5,53.65)]:place(bpy.data.objects[name],x,z)
# Seat the existing rock group into the new shelf and its toe.
for name,x,z,scale,embed in [('Bank_Boulder.008',17.15,43.65,1.2,.32),('Bank_Boulder.025',17.80,45.1,1.1,.20),('Bank_Boulder.007',16.65,44.2,1.3,.20)]:
    place(bpy.data.objects[name],x,z,scale,embed)
# Introduce two attached broad rock faces at the shelf return using existing owned assets.
for name,x,z,scale,embed in [('Bank_Boulder.023',11.4,54.65,1.0,.15),('Bank_Boulder.024',11.85,54.9,1.0,.13)]:place(bpy.data.objects[name],x,z,scale,embed)

# Preserve complete tree assemblies while correcting only changed ground contacts.
def suffix(o):
    s=o.name.rsplit('.',1)[-1];return int(s) if s.isdigit() else 0
def foot(o):
    ps=[o.matrix_world@v.co for v in o.data.vertices];low=min(p.z for p in ps);pts=[p for p in ps if p.z<low+.04]
    return sum(pts,Vector())/len(pts)
trunks=sorted([o for o in fol.objects if o.name=='Tree_Trunk' or o.name.startswith('Tree_Trunk.')],key=suffix)
crowns=sorted([o for o in fol.objects if o.name.startswith('D19_Tree_Crown')],key=suffix)
branches=sorted([o for o in fol.objects if o.name=='Tree_Branch' or o.name.startswith('Tree_Branch.')],key=suffix)
assert len(crowns)==len(trunks)*6 and len(branches)==len(trunks)*5
for i,t in enumerate(trunks):
    p=foot(t)
    if 39<-p.y<56 and 15<p.x<22:
        dz=ground(p.x,-p.y)-p.z-.09
        for o in [t]+crowns[i*6:(i+1)*6]+branches[i*5:(i+1)*5]:o.location.z+=dz;moved.append(o.name)

# Regrow old individual blades only on true horizontal grass support.
growth=bpy.data.objects['L24_GrassTuftClusters'];vv=[];ff=[]
for i in range(0,len(growth.data.vertices),3):
    vs=[growth.matrix_world@growth.data.vertices[i+k].co for k in range(3)]
    x=(vs[0].x+vs[1].x)/2;y=(vs[0].y+vs[1].y)/2
    if 38<-y<57:
        hit,n,pi,_=ground_bvh.ray_cast(Vector((x,y,80)),Vector((0,0,-1)),300)
        if not hit or n.z<.88 or attr.data[mesh.polygons[pi].loop_start].color[0]<.6:continue
        shift=hit.z-.012-vs[0].z
    else:shift=0
    base=len(vv);vv.extend((v.x,v.y,v.z+shift) for v in vs);ff.append((base,base+1,base+2))
gm=bpy.data.meshes.new('C26_RootedGrass');gm.from_pydata(vv,[],ff);gm.materials.append(growth.data.materials[0]);gm.update();growth.data=gm;growth.matrix_world=Matrix.Identity(4)
terrain['shore21_finished']=True
(LOG/'moved_objects.json').write_text(json.dumps(moved,indent=2),encoding='utf8')
refresh_height();export_land()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print(json.dumps({'upper_court_repaired_faces':len(chosen),'moved_objects':len(moved),'grass_triangles':len(ff),'saved':bpy.data.filepath}))
