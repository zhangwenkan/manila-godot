# Restore each cap from its original footprint, then locate the actual plateau.
for ob in list(C.objects):
    if ob.name.startswith(('S22_Turf_','S22_GroundedGrassBlades')):archive.objects.link(ob);C.objects.unlink(ob)
newpatches=[];records=[]
for original in patches:
    ntop=sum(p.material_index==0 for p in original.data.polygons);nz=ntop//14;nx=14;w=15
    verts=[];faces=[];rowlimits=[]
    for j in range(nz+1):
        row=[original.matrix_world@original.data.vertices[j*w+i].co for i in range(w)]
        z=-row[0].y;x0=row[0].x;x1=row[-1].x;goal=row[0].z-.10
        # The end tapers used to cap the search at 8cm width; a front must be
        # allowed to move to its support even when the original tip was narrow.
        needs_crest=row[0].z-ground(x0,z)>.18
        if needs_crest:
            for k in range(100):
                x=x0+k*.025;g=ground(x,z);gradient=abs(ground(x+.04,z)-ground(x-.04,z))/.08
                if g>=goal-.025 and gradient<.50:
                    x0=x;break
        # A front edge is never carried down a neighbouring cliff by a taper.
        for k in range(80):
            gradient=abs(ground(x0+.035,z)-ground(x0-.035,z))/.07
            if gradient<.65:break
            x0+=.025
        x1=max(x1,x0+.10)
        # Stop a grass bed before the next rising face at its back.
        if x1-x0>.25:
            h0=ground(x0+.07,z)
            for x in np.arange(x0+.20,x1,.06):
                if ground(float(x),z)>h0+.20:
                    x1=max(x0+.10,float(x)-.07);break
        rowlimits.append([z,x0,x1])
    # Smooth isolated plan-view jumps without expanding back over the slope.
    for _ in range(2):
        previous=[r[:] for r in rowlimits]
        for j in range(1,nz):
            rowlimits[j][1]=max(previous[j][1],(previous[j-1][1]+2*previous[j][1]+previous[j+1][1])/4)
            rowlimits[j][2]=max(rowlimits[j][1]+.10,previous[j][2])
    for j,(z,x0,x1) in enumerate(rowlimits):
        end=smooth(0,.4,min(z-rowlimits[0][0],rowlimits[-1][0]-z))
        for i in range(w):
            x=x0+(x1-x0)*i/nx;rear=smooth(0,.25,x1-x);g=ground(x,z)
            t=.007+(.050+.007*math.sin(z*2.4+x*3)-.007)*rear*end
            verts.append((x,-z,g+t))
    topn=len(verts)
    verts.extend([(x,y,ground(x,-y)-.025) for x,y,h in verts[:]])
    for j in range(nz):
        for i in range(nx):
            a=j*w+i;faces.append((a,a+w,a+w+1,a+1))
    ntop=len(faces)
    for f in faces[:]:faces.append(tuple(topn+i for i in reversed(f)))
    ring=list(range(w))+[j*w+nx for j in range(1,nz+1)]+[nz*w+i for i in range(nx-1,-1,-1)]+[j*w for j in range(nz-1,0,-1)]
    for k,a in enumerate(ring):b=ring[(k+1)%len(ring)];faces.append((a,b,topn+b,topn+a))
    ob=mesh(original.name.replace('R21_Turf_','S22_Turf_'),verts,faces,turfmat);ob.data.materials.append(rootmat)
    matids=np.ones(len(faces),np.int32);matids[:ntop]=0;ob.data.polygons.foreach_set('material_index',matids)
    sm=np.zeros(len(faces),np.bool_);sm[:ntop]=True;ob.data.polygons.foreach_set('use_smooth',sm)
    newpatches.append(ob);gaps=[h-ground(x,-y) for x,y,h in verts[:topn]]
    bm=bmesh.new();bm.from_mesh(ob.data);bad=sum(not e.is_manifold for e in bm.edges);bm.free();assert bad==0
    records.append({'name':ob.name,'min_gap':min(gaps),'max_gap':max(gaps),'closed':True})

points=[];polys=[]
for ob in newpatches:
    start=len(points);points.extend([ob.matrix_world@v.co for v in ob.data.vertices]);polys.extend([tuple(start+i for i in p.vertices) for p in ob.data.polygons if p.material_index==0])
turf_bvh=BVHTree.FromPolygons(points,polys)
oldblade=bpy.data.objects['R21_TurfBladeFans.001'];bladeverts=[];bladefaces=[];removed=0
for p in oldblade.data.polygons:
    ps=[oldblade.matrix_world@oldblade.data.vertices[i].co for i in p.vertices];bottom=min(v.z for v in ps);roots=[v for v in ps if v.z<bottom+.025];root=sum(roots,Vector())/len(roots)
    hit,n,idx,dist=turf_bvh.ray_cast(Vector((root.x,root.y,40)),Vector((0,0,-1)),120)
    if hit is None:removed+=1;continue
    a=len(bladeverts);dh=hit.z-.008-bottom;bladeverts.extend([(v.x,v.y,v.z+dh) for v in ps]);bladefaces.append((a,a+1,a+2))
blade=mesh('S22_GroundedGrassBlades',bladeverts,bladefaces,turfmat);blade.data.uv_layers.active.data.foreach_set('uv',np.tile(np.array([0,0,1,0,.5,1],np.float32),len(bladefaces)))
(LOG/'cap_fit_report.json').write_text(json.dumps({'patches':records,'removed_blades':removed,'retained_blades':len(bladefaces)},indent=2),encoding='utf8')
bpy.context.view_layer.update();export_collection('Reference_Terrain','terrain.glb');bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/reference_harbor_mcp.blend'))
print('CAP_FIT',len(records),max(r['max_gap'] for r in records))
