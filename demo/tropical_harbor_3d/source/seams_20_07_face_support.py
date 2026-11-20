# Reject cap cells that bridge a cliff or span a gap between sampled rows.
repaired=[];removed_faces=0
for old in list(newpatches):
    coords=[old.matrix_world@v.co for v in old.data.vertices];tops=[]
    for p in old.data.polygons:
        if p.material_index!=0:continue
        ps=[coords[i] for i in p.vertices];c=sum(ps,Vector())/len(ps)
        gap=c.z-ground(c.x,-c.y)
        edge=max((ps[(j+1)%len(ps)]-v).length for j,v in enumerate(ps))
        if p.normal.z<.90 or gap>.095 or gap<-.02 or edge>1.10:removed_faces+=1;continue
        tops.append(tuple(p.vertices))
    used=sorted(set(i for p in tops for i in p));remap={old:i for i,old in enumerate(used)}
    verts=[coords[i][:] for i in used];faces=[tuple(remap[i] for i in p) for p in tops];n=len(verts);nt=len(faces)
    edges={}
    for f in faces:
        for a,b in zip(f,f[1:]+f[:1]):
            k=tuple(sorted((a,b)));edges.setdefault(k,[]).append((a,b))
    verts.extend([(x,y,ground(x,-y)-.025) for x,y,h in verts[:]])
    for f in faces[:]:faces.append(tuple(n+i for i in reversed(f)))
    for entries in edges.values():
        if len(entries)==1:
            a,b=entries[0];faces.append((a,n+a,n+b,b))
    ob=mesh(old.name.replace('S22_','S22F_'),verts,faces,turfmat);ob.data.materials.append(rootmat)
    ids=np.ones(len(faces),np.int32);ids[:nt]=0;ob.data.polygons.foreach_set('material_index',ids)
    sm=np.zeros(len(faces),np.bool_);sm[:nt]=True;ob.data.polygons.foreach_set('use_smooth',sm)
    archive.objects.link(old);C.objects.unlink(old);repaired.append(ob)
newpatches=repaired
# The background grass uses its own material, so it needs neutral vertex colour.
attr=terrain.data.color_attributes['BankBlend'];values=np.empty(len(attr.data)*4,np.float32);attr.data.foreach_get('color',values);values=values.reshape(-1,4)
for p in terrain.data.polygons:
    if p.material_index==2:
        for i in p.vertices:values[i,:]=1
attr.data.foreach_set('color',values.ravel())
# Grass blades must have full support on a retained top face.
points=[];polys=[]
for ob in newpatches:
    start=len(points);points.extend([ob.matrix_world@v.co for v in ob.data.vertices]);polys.extend([tuple(start+i for i in p.vertices) for p in ob.data.polygons if p.material_index==0])
turf_bvh=BVHTree.FromPolygons(points,polys);removed_blades=0
blade=next(o for o in C.objects if o.name.startswith('S22_GroundedGrassBlades'))
bm=bmesh.new();bm.from_mesh(blade.data);delete=[]
for f in bm.faces:
    low=min(v.co.z for v in f.verts);roots=[v.co for v in f.verts if v.co.z<low+.025];p=sum(roots,Vector())/len(roots)
    hit,n,i,d=turf_bvh.ray_cast(Vector((p.x,p.y,40)),Vector((0,0,-1)),120)
    if hit is None:delete.append(f)
removed_blades=len(delete);bmesh.ops.delete(bm,geom=delete,context='FACES');bm.to_mesh(blade.data);bm.free();blade.data.update()
bpy.context.view_layer.update();print('FACE_SUPPORT',removed_faces,'bad top cells',removed_blades,'unsupported blades removed')
(LOG/'face_support.json').write_text(json.dumps({'removed_bridging_cells':removed_faces,'removed_blades':removed_blades},indent=2),encoding='utf8')
export_collection('Reference_Terrain','terrain.glb');bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/reference_harbor_mcp.blend'))
