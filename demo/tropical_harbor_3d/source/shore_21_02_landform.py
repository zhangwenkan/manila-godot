# One-time authored terrain operation, executed only through Blender MCP.
exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
from mathutils.geometry import delaunay_2d_cdt
assert not terrain.get('shore21_landform'), 'Already applied; inspect instead of replaying'
bpy.ops.wm.save_as_mainfile(filepath=str(LOG/'before/harbor_shore_control_mcp.blend'),copy=True)
before_bvh=ground_bvh
oldpos=np.empty((len(mesh.vertices),3),np.float32);mesh.vertices.foreach_get('co',oldpos.ravel())
def interp(z,rows,col=1):return float(np.interp(z,[p[0] for p in rows],[p[col] for p in rows]))
toe=[(37.5,15.3),(39.2,12.1),(41.6,11.0),(42.6,10.0),(44.2,9.7),(45.2,10.4),(47.6,13.0),(50,14.5)]
crown=[(37.5,17.5),(39.2,13.8),(41.6,12.6),(42.6,11.8),(44.2,11.6),(45.2,12.9),(47.6,15.4),(50,16.1)]
# World-space control sections: low toe, shoulder lip, shelf back, upper rim.
# The shelf exists only at the returning headland, not as another coastal band.
design=[(39.2,18.08,18.55,19.02,19.78),
        (40.4,17.35,17.78,18.08,19.10),
        (41.6,16.86,17.25,17.58,18.52),
        (42.6,16.28,16.63,17.02,18.20),
        (43.4,16.16,16.82,17.68,19.04),
        (44.2,16.38,17.20,18.72,20.02),
        (45.2,17.05,17.90,19.46,20.80),
        (46.4,18.20,18.76,19.54,21.30),
        (47.6,19.72,20.06,20.40,22.04),
        (48.8,21.30,21.62,22.05,23.20)]
edited=[]
for v in mesh.vertices:
    x,y,h=oldpos[v.index];z=-float(y)
    if not 39.2<z<48.8:continue
    sh=float(shore(z));a=interp(z,toe)+sh;b=interp(z,crown)+sh
    low=float(np.interp(z,[37.5,43,46.6,60.5],[1.65,1.65,1.18,1.18]))
    if x<a-.22 or x>max(b+1.5,21.4) or h<low-.02:continue
    w=float(smooth(39.2,41.4,z)*(1-smooth(46.8,48.8,z)))
    dt,lip,back,rim=[interp(z,design,i) for i in range(1,5)]
    shelf=float(smooth(42.0,43.4,z)*(1-smooth(45.4,47.0,z)))
    if h<4.14-.001:
        frac=max(0,min(1,(h-low)/(4.14-low)))
        old_shelf=float(smooth(42.8,43.6,z)*(1-smooth(45.1,46.2,z)))
        knots=[0,.20/(4.14-low),.85/(4.14-low),(1.02+.28*(1-old_shelf))/(4.14-low),1-.15/(4.14-low),1-.035/(4.14-low),1]
        newx=float(np.interp(frac,knots,[dt,dt+.20,lip,back,rim-.20,rim-.08,rim]))
        newh=float(np.interp(frac,knots,[low,low+.16,low+.84,low+.84+.14*(1-shelf),3.99,4.105,4.14]))
        v.co.x=x*(1-w)+newx*w;v.co.z=h*(1-w)+newh*w
    elif x<21.5 and x>=b-.25:
        move=(rim-b)*max(0,min(1,(21.5-x)/(21.5-b))) if b<21.4 else 0
        v.co.x=x+w*move
    edited.append(v.index)
mesh.update()
attr=mesh.color_attributes['LandUse']
for p in mesh.polygons:
    x,y,h=p.center;z=-y
    if 41.3<z<47.4 and 15.8<x<21.4 and 1.6<h<4.13:
        if p.normal.z>.87 and 43.0<z<46.2 and 2.10<h<2.85:
            color=(1,0,0,0)
        else:color=(0,1,0,0)
        for li in p.loop_indices:attr.data[li].color=color
        p.use_smooth=False

# Replace the small sea-access domain with a broad angled inlet, sharing its perimeter.
bpy.context.view_layer.update();slope_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
selected={p.index for p in mesh.polygons if 50.8<-p.center.y<55.45 and .45<p.center.x-float(shore(-p.center.y))<10.0}
counts={}
for i in selected:
    ids=list(mesh.polygons[i].vertices)
    for a,b in zip(ids,ids[1:]+ids[:1]):
        k=tuple(sorted((a,b)));counts[k]=counts.get(k,0)+1
adj={}
for (a,b),n in counts.items():
    if n==1:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
assert all(len(v)==2 for v in adj.values()),'Inlet boundary branches'
boundary=[min(adj)];prev=None;cur=boundary[0]
while True:
    nxt=next(n for n in adj[cur] if n!=prev)
    if nxt==boundary[0]:break
    boundary.append(nxt);prev,cur=cur,nxt
    assert len(boundary)<=len(adj)
assert len(boundary)==len(adj),'Inlet boundary has separate holes'
def inside(x,y,poly):
    out=False
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:out=not out
    return out
vlist=[tuple(v.co) for v in mesh.vertices]
polys=[];colors=[];smoothflags=[]
for p in mesh.polygons:
    if p.index in selected:continue
    polys.append(list(p.vertices));colors.extend(tuple(attr.data[li].color) for li in p.loop_indices);smoothflags.append(p.use_smooth)
ids=list(boundary);coords=[Vector(vlist[i][:2]) for i in ids]
edges=[(i,(i+1)%len(boundary)) for i in range(len(boundary))]
boundarypoly=[tuple(v) for v in coords]
# Sections run from beach to the low courtyard; width tapers inland.
sections=[(1.25,53.0,1.82,.27),(3.1,53.15,1.65,.34),(4.8,53.45,1.30,.53),(6.5,53.55,1.02,.87),(8.9,53.40,.60,1.18)]
left=[];right=[]
for d,z,half,h in sections:
    left.append((float(shore(z-half)+d),-(z-half),h))
    right.append((float(shore(z+half)+d),-(z+half),h))
inlet=left+right[::-1]
assert all(inside(p[0],p[1],boundarypoly) for p in inlet), 'Designed inlet extends outside selected patch'
off=len(coords)
for p in inlet:ids.append(len(vlist));vlist.append(p);coords.append(Vector(p[:2]))
edges.extend((off+i,off+(i+1)%len(inlet)) for i in range(len(inlet)))
for j in range(1,len(sections)-1):edges.append((off+j,off+len(inlet)-1-j))
for idx in sorted({v for i in selected for v in mesh.polygons[i].vertices}-set(boundary)):
    p=vlist[idx]
    if inside(p[0],p[1],[(v[0],v[1]) for v in inlet]):continue
    ids.append(idx);coords.append(Vector(p[:2]))
rv,re,rf,orig,_,_=delaunay_2d_cdt(coords,edges,[list(range(len(boundary)))],1,1e-6,True)
mapping=[]
for i,p in enumerate(rv):
    if orig[i]:idx=ids[orig[i][0]]
    else:
        hit,*_=slope_bvh.ray_cast(Vector((p.x,p.y,80)),Vector((0,0,-1)),300)
        idx=len(vlist);vlist.append((p.x,p.y,hit.z))
    mapping.append(idx)
inpoly=[(p[0],p[1]) for p in inlet]
for f in rf:
    vi=[mapping[i] for i in f];ps=[Vector(vlist[i]) for i in vi]
    if (ps[1]-ps[0]).cross(ps[2]-ps[0]).z<0:vi.reverse()
    c=sum(ps,Vector())/len(ps);d=c.x-float(shore(-c.y))
    if inside(c.x,c.y,inpoly):
        col=(0,0,0,0) if d<4.1 else (0,0,.16,.84)
    else:
        hit,n,pi,_=slope_bvh.ray_cast(Vector((c.x,c.y,80)),Vector((0,0,-1)),300)
        col=tuple(attr.data[mesh.polygons[pi].loop_start].color)
        if col[2]>.5:col=(1,0,0,0)
    polys.append(vi);colors.extend([col]*len(vi));smoothflags.append(False if inside(c.x,c.y,inpoly) else True)
dm=bpy.data.meshes.new('C26_RockShoulderAndRecessedLanding');dm.from_pydata(vlist,[],polys);dm.update()
dm.materials.append(mesh.materials[0])
ca=dm.color_attributes.new(name='LandUse',type='FLOAT_COLOR',domain='CORNER');dm.color_attributes.active_color=ca
ca.data.foreach_set('color',np.array(colors,np.float32).ravel())
for p,s in zip(dm.polygons,smoothflags):p.use_smooth=s
uv=dm.uv_layers.new(name='UVMap');li=np.empty(len(dm.loops),np.int32);dm.loops.foreach_get('vertex_index',li)
uv.data.foreach_set('uv',(np.asarray(vlist,np.float32)[li,:2]/2.4).ravel())
dm.set_sharp_from_angle(angle=math.radians(32));terrain.data=dm
terrain['shore21_landform']='local rock shoulder and diagonal recessed inlet'
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
refresh_height();export_land()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print(json.dumps({'edited_vertices':len(edited),'inlet_replaced_faces':len(selected),'vertices':len(dm.vertices),'faces':len(dm.polygons),'saved':bpy.data.filepath}))
