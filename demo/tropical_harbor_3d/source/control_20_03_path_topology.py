# Cut exact road boundaries into an interior subdomain; no material-painted diagonal.
mesh=terrain.data;bpy.context.view_layer.update();before_path_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
selected=set()
for p in mesh.polygons:
    gx,gy,gh=p.center;gz=-gy;ddg=gx-float(shore(gz))
    if 48.6<gz<58.8 and 10.3<ddg<22.2:selected.add(p.index)
edgecount={};edgeorient={}
for idx in selected:
    ids=list(mesh.polygons[idx].vertices)
    for a,b in zip(ids,ids[1:]+ids[:1]):
        key=tuple(sorted((a,b)));edgecount[key]=edgecount.get(key,0)+1;edgeorient[key]=(a,b)
boundary_edges=[edgeorient[e] for e,c in edgecount.items() if c==1]
adj={}
for a,b in boundary_edges:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
assert all(len(v)==2 for v in adj.values()),'road domain must have one boundary'
boundary=[min(adj)];previous=None;current=boundary[0]
while True:
    nxt=next(v for v in adj[current] if v!=previous)
    if nxt==boundary[0]:break
    boundary.append(nxt);previous,current=current,nxt
    assert len(boundary)<=len(adj)
assert len(boundary)==len(adj),'unexpected separate hole in road domain'
pathstations=[]
for a,b in zip(route,route[1:]):
    length=math.hypot(b[0]-a[0],b[1]-a[1]);steps=max(1,int(math.ceil(length/.5)))
    for k in range(steps):
        t=k/steps;pathstations.append(tuple(a[j]*(1-t)+b[j]*t for j in range(3)))
pathstations.append(route[-1])
left=[];right=[]
for i,a in enumerate(pathstations):
    b=pathstations[max(0,i-1)];c=pathstations[min(len(pathstations)-1,i+1)]
    tangent=Vector((c[0]-b[0],c[1]-b[1])).normalized();normal=Vector((-tangent.y,tangent.x))
    width=.62 if i<len(pathstations)-4 else .8
    left.append(p3(a[0]+normal.x*width,a[1]+normal.y*width,a[2]));right.append(p3(a[0]-normal.x*width,a[1]-normal.y*width,a[2]))
pathpoly=left+right[::-1]
vlist=[tuple(v.co) for v in mesh.vertices];polys=[];weights=[];smoothflags=[]
for p in mesh.polygons:
    if p.index in selected:continue
    polys.append(list(p.vertices));weights.append([tuple(mesh.color_attributes['LandUse'].data[li].color) for li in p.loop_indices]);smoothflags.append(p.use_smooth)
localids=list(boundary);localcoords=[Vector((vlist[i][0],vlist[i][1])) for i in localids]
edges=[(i,(i+1)%len(boundary)) for i in range(len(boundary))]
offset=len(localids)
for p in pathpoly:localids.append(len(vlist));vlist.append(p);localcoords.append(Vector((p[0],p[1])))
edges.extend((offset+i,offset+(i+1)%len(pathpoly)) for i in range(len(pathpoly)))
for idx in sorted({v for i in selected for v in mesh.polygons[i].vertices}-set(boundary)):
    p=vlist[idx]
    if inside_polygon(p[0],p[1],[(q[0],q[1]) for q in pathpoly]):continue
    localids.append(idx);localcoords.append(Vector((p[0],p[1])))
rv,re,rf,orig,_,_=delaunay_2d_cdt(localcoords,edges,[list(range(len(boundary)))],1,1e-6,True)
outids=[]
for i,v in enumerate(rv):
    if orig[i]:idx=localids[orig[i][0]]
    else:
        hit,*_=before_path_bvh.ray_cast(Vector((v.x,v.y,80)),Vector((0,0,-1)),300)
        idx=len(vlist);vlist.append((v.x,v.y,hit.z if hit else lowh(-v.y)))
    if idx not in boundary:
        gx,gy,gh=vlist[idx];dist,elev=route_nearest(gx,-gy)
        f=1-float(smooth(.6,1.35,dist));vlist[idx]=(gx,gy,gh*(1-f)+elev*f)
    outids.append(idx)
for f in rf:
    ids=[outids[i] for i in f];pts=[Vector(vlist[i]) for i in ids]
    if (pts[1]-pts[0]).cross(pts[2]-pts[0]).z<0:ids.reverse()
    p=sum(pts,Vector())/len(pts)
    inpath=inside_polygon(p.x,p.y,[(q[0],q[1]) for q in pathpoly])
    if inpath:col=(0,0,1,0)
    else:
        hit,n,pi,_=before_path_bvh.ray_cast(Vector((p.x,p.y,80)),Vector((0,0,-1)),300)
        col=tuple(mesh.color_attributes['LandUse'].data[mesh.polygons[pi].loop_start].color) if hit else (1,0,0,0)
        if col[2]>.5:col=(1,0,0,0)
    polys.append(ids);weights.append([col]*len(ids));smoothflags.append(True)
dm=bpy.data.meshes.new('C25_SharedContourAndRoadEdges');dm.from_pydata(vlist,[],polys);dm.update();dm.materials.append(mesh.materials[0])
attr=dm.color_attributes.new(name='LandUse',type='FLOAT_COLOR',domain='CORNER');dm.color_attributes.active_color=attr;attr.data.foreach_set('color',np.array([c for row in weights for c in row],np.float32).ravel())
uv=dm.uv_layers.new(name='UVMap')
for p,s in zip(dm.polygons,smoothflags):
    p.use_smooth=s
loop_vertices=np.empty(len(dm.loops),np.int32);dm.loops.foreach_get('vertex_index',loop_vertices)
uv.data.foreach_set('uv',(np.asarray(vlist,np.float32)[loop_vertices,:2]/2.4).ravel())
dm.set_sharp_from_angle(angle=math.radians(32));terrain.data=dm
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get());refresh_height();export_land()
print('PATH_CONSTRAINTS',len(pathpoly),'road-edge points;',len(selected),'old faces replaced')
print('ROCKS',[(o.name,[round(v,2) for v in center(o)],round(o.dimensions.length,2)) for o in rocks.objects if 38<-center(o).y<60])
print('SHRUBS',[(o.name,[round(v,2) for v in center(o)]) for o in fol.objects if o.name.startswith('S20_CourtyardShrub') and 38<-center(o).y<60])
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
