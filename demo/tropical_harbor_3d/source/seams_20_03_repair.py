# Executed only through the verified isolated Blender MCP session.
import bmesh
from mathutils.kdtree import KDTree

archive=bpy.data.collections.new('Archive_Seams20_Before');bpy.context.scene.collection.children.link(archive);archive.hide_render=True;archive.hide_viewport=True
backup=terrain.copy();backup.data=terrain.data.copy();backup.name='Seams20_BeforeSoil';archive.objects.link(backup)

# Restore shared vertices along the old face-by-face material split. Geometry
# remains continuous; soil colour will blend over the physical slope instead.
bm=bmesh.new();bm.from_mesh(terrain.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00005)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(terrain.data);bm.free();terrain.data.update()

# Slightly fair lateral irregularities on exposed banks, keeping all standing
# pads, shore, basin, steps, and upper/lower horizontal surfaces at their heights.
bm=bmesh.new();bm.from_mesh(terrain.data);bm.verts.ensure_lookup_table();adjusted=0
for _ in range(2):
    updates=[]
    for v in bm.verts:
        x,y,h=v.co;z=-y;d=x-shore(z)
        if not (2<z<79 and 1.5<d<26 and h>.5):continue
        if abs(z-65.2)<4.8 and d<12:continue
        if 38.8<z<41.4 and d<7:continue
        if min(abs(z-k) for k in [61,44,29,12])<2.15:continue
        if any(abs(z-s['gz'])<s['w']/2+.4 and abs(d-s['d'])<s['depth']/2+.5 for s in SITES):continue
        if not v.link_faces or all(f.normal.z>.88 for f in v.link_faces):continue
        near=[]
        for e in v.link_edges:
            q=e.other_vert(v);dz=abs(q.co.y-y);dx=abs(q.co.x-x)
            if dz>.1 and dx<.6 and abs(q.co.z-h)<.40:near.append(q.co.z)
        if len(near)>=2:
            target=sum(near)/len(near);delta=max(-.035,min(.035,(target-h)*.35))
            if abs(delta)>.001:updates.append((v,h+delta))
    for v,h in updates:v.co.z=h
    adjusted+=len(updates);bm.normal_update()
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(terrain.data);bm.free();terrain.data.update()
terrain.data.polygons.foreach_set('use_smooth',np.ones(len(terrain.data.polygons),np.bool_))

# Author a continuous soil weight at shared vertices from the actual bank
# incline. It affects surface finish only; the already-modelled ledges stay.
weights=[]
for v in terrain.data.vertices:
    z=-v.co.y;d=v.co.x-shore(z);n=abs(v.normal.z)
    w=(1-smooth(.73,.94,n))*smooth(.28,.55,v.co.z)
    if d<0 or d>27 or z<0 or z>82:w=0
    weights.append(w)
attr=terrain.data.color_attributes.get('BankBlend') or terrain.data.color_attributes.new(name='BankBlend',type='FLOAT_COLOR',domain='POINT')
rgba=np.ones((len(weights),4),np.float32);rgba[:,0]=weights;rgba[:,1:3]=0;attr.data.foreach_set('color',rgba.ravel())
indices=np.empty(len(terrain.data.polygons),np.int32);terrain.data.polygons.foreach_get('material_index',indices)
indices[indices==1]=0;terrain.data.polygons.foreach_set('material_index',indices)
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())

turfmat=bpy.data.materials['Ref_R21_Turf'];rootmat=bpy.data.materials['Ref_R21_TurfRoot'];newpatches=[];records=[]
for old in patches:
    topfaces=[p for p in old.data.polygons if p.material_index==0];nz=len(topfaces)//14;nx=14;w=15
    oldrows=[]
    for j in range(nz+1):
        row=[old.matrix_world@old.data.vertices[j*w+i].co for i in range(w)]
        oldrows.append(row)
    verts=[];faces=[];min_shift=100;max_shift=0
    for j,row in enumerate(oldrows):
        z=-row[0].y;x0=row[0].x;x1=row[-1].x;original_width=x1-x0
        # Inspect actual support along each cross-section. Only points that
        # reached outward from the bank need an inward correction.
        delta=row[0].z-ground(x0,z)
        if delta>.18:
            goal=row[0].z-.105
            limit=min(1.2,max(.05,original_width-.10))
            candidates=[x0+limit*k/60 for k in range(61)]
            found=next((x for x in candidates if ground(x,z)>=goal-.018),None)
            if found is not None:x0=found
        # Ensure narrow tapered tips also rest on soil instead of cantilevering.
        x1=max(x1,x0+.08);shift=x0-row[0].x;min_shift=min(min_shift,shift);max_shift=max(max_shift,shift)
        endfade=smooth(0,.55,min(z+oldrows[0][0].y,-oldrows[-1][0].y-z))
        for i in range(w):
            t=i/nx;x=x0+(x1-x0)*t;g=ground(x,z)
            rear=smooth(0,.35,(x1-x))
            thickness=(.052+.010*math.sin(z*2.4+x*3.0)+.006*math.sin(z*7.2))
            thickness=.007+(thickness-.007)*rear*endfade
            verts.append((x,-z,g+thickness))
    topn=len(verts)
    for x,y,h in verts[:]:verts.append((x,y,ground(x,-y)-.035))
    for j in range(nz):
        for i in range(nx):
            a=j*w+i;faces.append((a,a+w,a+w+1,a+1))
    ntop=len(faces)
    for f in faces[:]:faces.append(tuple(topn+i for i in reversed(f)))
    perimeter=list(range(w))+[j*w+nx for j in range(1,nz+1)]+[nz*w+i for i in range(nx-1,-1,-1)]+[j*w for j in range(nz-1,0,-1)]
    for i,a in enumerate(perimeter):
        b=perimeter[(i+1)%len(perimeter)];faces.append((a,b,topn+b,topn+a))
    ob=mesh(old.name.replace('R21_Turf_','S22_Turf_'),verts,faces,turfmat);ob.data.materials.append(rootmat)
    mids=np.ones(len(faces),np.int32);mids[:ntop]=0;ob.data.polygons.foreach_set('material_index',mids)
    sm=np.zeros(len(faces),np.bool_);sm[:ntop]=True;ob.data.polygons.foreach_set('use_smooth',sm)
    archive.objects.link(old);C.objects.unlink(old);newpatches.append(ob)
    gaps=[v[2]-ground(v[0],-v[1]) for v in verts[:topn]]
    bm=bmesh.new();bm.from_mesh(ob.data);open_edges=sum(not e.is_manifold for e in bm.edges);bm.free();assert open_edges==0,(ob.name,open_edges)
    records.append({'name':ob.name,'front_inward_max':max_shift,'min_gap':min(gaps),'max_gap':max(gaps),'closed':True})

# Project retained blade clusters to the corrected grass surface; discard those
# whose old front point is now outside a cap rather than leave them in the air.
points=[];polys=[]
for ob in newpatches:
    start=len(points);points.extend([ob.matrix_world@v.co for v in ob.data.vertices])
    polys.extend([tuple(start+i for i in p.vertices) for p in ob.data.polygons if p.material_index==0])
turf_bvh=BVHTree.FromPolygons(points,polys);oldblade=next(o for o in C.objects if o.name.startswith('R21_TurfBladeFans'))
bladeverts=[];bladefaces=[];removed=0
for p in oldblade.data.polygons:
    ps=[oldblade.matrix_world@oldblade.data.vertices[i].co for i in p.vertices]
    bottom=min(v.z for v in ps);roots=[v for v in ps if v.z<bottom+.025];root=sum(roots,Vector())/len(roots)
    hit,n,idx,dist=turf_bvh.ray_cast(Vector((root.x,root.y,40)),Vector((0,0,-1)),120)
    if hit is None:removed+=1;continue
    dh=hit.z-.008-bottom;a=len(bladeverts);bladeverts.extend([(v.x,v.y,v.z+dh) for v in ps]);bladefaces.append((a,a+1,a+2))
blade=mesh('S22_GroundedGrassBlades',bladeverts,bladefaces,turfmat);blade.data.uv_layers.active.data.foreach_set('uv',np.tile(np.array([0,0,1,0,.5,1],np.float32),len(bladefaces)))
archive.objects.link(oldblade);C.objects.unlink(oldblade)

# Runtime grounding follows the amended base mesh.
data={'d0':0,'z0':0,'step':.25,'columns':145,'rows':329,'heights':[]}
for j in range(329):
    z=j*.25
    for i in range(145):data['heights'].append(round(ground(shore(z)+i*.25,z),5))
(OUT/'shore_relief_height.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
report={'smoothed_bank_vertices':adjusted,'patches':records,'removed_unsupported_blades':removed,'retained_blade_triangles':len(bladefaces)}
(LOG/'repair_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('REPAIRED',len(records),'closed caps','maximum_top_gap',max(r['max_gap'] for r in records),'removed_blades',removed)
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/reference_harbor_mcp.blend'))
export_collection('Reference_Terrain','terrain.glb')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/reference_harbor_mcp.blend'))
