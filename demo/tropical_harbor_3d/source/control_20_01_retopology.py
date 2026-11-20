# Execute in the owned Blender MCP session. Contour vertices are actual mesh edges.
import bmesh
from mathutils.geometry import tessellate_polygon
oldmesh=terrain.data
oldxyz=np.empty((len(oldmesh.vertices),3),np.float32);oldmesh.vertices.foreach_get('co',oldxyz.ravel())
oldcols=np.empty((len(oldmesh.vertices),4),np.float32);oldmesh.color_attributes['LandUse'].data.foreach_get('color',oldcols.ravel())
grid_width=145;zrows=-oldxyz.reshape((-1,grid_width,3))[:,:,1].mean(1)
j0=int(np.argmin(abs(zrows-36.5)));j1=int(np.argmin(abs(zrows-62.0)))
drow=oldxyz.reshape((-1,grid_width,3))[j0,:,0]-shore(zrows[j0]);i0=15;i1=int(np.argmin(abs(drow-24.5)))
# Reuse the exact old perimeter, and remove only the enclosed faces.
outer_ids=[j0*grid_width+i for i in range(i0,i1+1)]+[j*grid_width+i1 for j in range(j0+1,j1+1)]+[j1*grid_width+i for i in range(i1-1,i0-1,-1)]+[j*grid_width+i0 for j in range(j1-1,j0,-1)]
inside_ids={j*grid_width+i for j in range(j0,j1+1) for i in range(i0,i1+1)}
verts=oldxyz.tolist();faces=[];faceweights=[];facekind=[]
for p in oldmesh.polygons:
    ids=list(p.vertices)
    if all(i in inside_ids for i in ids):continue
    faces.append(ids);faceweights.append(oldcols[ids].tolist());facekind.append('old')
lookup={tuple(round(float(v),5) for v in p):i for i,p in enumerate(verts)}
def point(p):
    key=tuple(round(float(v),5) for v in p)
    if key not in lookup:lookup[key]=len(verts);verts.append(tuple(float(v) for v in p))
    return lookup[key]
roles={'grass':(1,0,0,0),'rock':(0,1,0,0),'path':(0,0,1,0),'soil':(0,0,0,1),'sand':(0,0,0,0)}
def face(ids,kind='grass',color=None):
    if len(set(ids))<3:return
    ps=[Vector(verts[i]) for i in ids]
    normal=(ps[1]-ps[0]).cross(ps[2]-ps[0])
    if normal.z<-.00001:ids=list(reversed(ids))
    faces.append(ids);facekind.append(kind)
    faceweights.append([color or roles.get(kind,roles['rock']) for _ in ids])
def p3(d,z,h):return (float(shore(z))+d,-z,h)
def lowh(z):return float(np.interp(z,[37.5,43,46.6,60.5],[1.65,1.65,1.18,1.18]))
def highh(z):return float(np.interp(z,[37.5,51.5,57,60.5],[4.14,4.14,4.29,4.29]))
stations=[37.5,38.3,39.2,40.4,41.6,42.6,43.4,44.2,45.2,46.4,47.6,48.8,50,51,52,53,54,55,56.2,57.5,58.8,60.5]
def plan(z,keys):return float(np.interp(z,[p[0] for p in keys],[p[1] for p in keys]))
beach_toe=[(37.5,2.1),(40,1.45),(43,1.9),(46,2.8),(49,3.65),(51,3.1),(53,2.3),(55,3.2),(58,2.5),(60.5,2.0)]
low_crown=[(37.5,4.2),(40,3.3),(43,3.0),(46,4.1),(49,5.0),(51,4.5),(53,4.1),(55,4.8),(58,3.7),(60.5,3.1)]
high_crown=[(37.5,17.5),(39.2,13.8),(41.6,12.6),(42.6,11.8),(44.2,11.6),(45.2,12.9),(47.6,15.4),(50,16.1),(51,17.0),(53,19.0),(55,16.6),(56.2,14.1),(58.8,13.1),(60.5,12.8)]
high_toe=[(37.5,15.3),(39.2,12.1),(41.6,11.0),(42.6,10.0),(44.2,9.7),(45.2,10.4),(47.6,13.0),(50,14.5),(51,15.5),(53,15.3),(55,14.6),(56.2,12.5),(58.8,11.0),(60.5,10.7)]
rows=[]
for k,gz in enumerate(stations):
    a=plan(gz,beach_toe);b=plan(gz,low_crown);c=plan(gz,high_toe);e=plan(gz,high_crown)
    lh=lowh(gz);hh=highh(gz)
    inlet=1-float(smooth(.5,1.8,abs(gz-53)))
    lipheight=lh*(1-inlet)+.45*inlet
    # A short rock shelf only on the returning side of the main headland.
    shelf=float(smooth(42.8,43.6,gz)*(1-smooth(45.1,46.2,gz)))
    points=[p3(.35,gz,float(old_ground(float(shore(gz))+.35,gz))),
            p3(a,gz,.28),p3(a+.20,gz,.34),
            p3(b-.22,gz,lipheight-.12),p3(b,gz,lipheight),
            p3(c,gz,lh+.015),
            p3(c+.18,gz,lh+.20),
            p3(c+(e-c)*.32-.18*shelf,gz,lh+.85),
            p3(c+(e-c)*.64-.27*shelf,gz,lh+1.02+.28*(1-shelf)),
            p3(e-.23,gz,hh-.15),p3(e-.11,gz,hh-.035),
            p3(e,gz,hh),p3(23.0,gz,hh+.08)]
    rows.append([point(p) for p in points])

def inside_polygon(x,y,poly):
    inside=False
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if ((a[1]>y)!=(b[1]>y)) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
    return inside

def fill_polygon(boundary,kind,extra=[],heightfn=None,pathpolys=[]):
    ids=list(boundary);coords=[Vector((verts[i][0],verts[i][1])) for i in ids]
    edges=[(i,(i+1)%len(ids)) for i in range(len(ids))]
    for pp in pathpolys:
        offset=len(coords)
        for v in pp:
            coords.append(Vector((v[0],v[1])));ids.append(point(v))
        edges.extend((offset+i,offset+(i+1)%len(pp)) for i in range(len(pp)))
    for p in extra:coords.append(Vector((p[0],p[1])));ids.append(point(p))
    result=delaunay_2d_cdt(coords,edges,[list(range(len(boundary)))],1,1e-6,True)
    rverts,redges,rfaces,orig,_,_=result
    output=[]
    for idx,v in enumerate(rverts):
        if orig[idx]:output.append(ids[orig[idx][0]])
        else:
            if heightfn:zh=heightfn(v.x,-v.y)
            else:zh=old_ground(v.x,-v.y)
            output.append(point((v.x,v.y,zh)))
    for f in rfaces:
        tri=[output[i] for i in f];ps=[verts[i] for i in tri];cx=sum(p[0] for p in ps)/len(ps);cy=sum(p[1] for p in ps)/len(ps)
        role='path' if any(inside_polygon(cx,cy,[(v[0],v[1]) for v in pp]) for pp in pathpolys) else kind
        face(tri,role)

# Individual surfaces share the actual toe/crown rings. Only internal field faces use CDT.
bands=[(0,1,'sand'),(1,2,'grass'),(2,3,'soil'),(3,4,'soil'),(4,5,'grass'),(5,6,'rock'),(6,7,'rock'),(7,8,'rock'),(8,9,'rock'),(9,10,'rock'),(10,11,'soil'),(11,12,'grass')]
for a,b,kind in bands:
    boundary=[r[a] for r in rows]+[r[b] for r in rows[::-1]]
    if kind=='rock':
        for k in range(len(rows)-1):
            ids=[rows[k][a],rows[k+1][a],rows[k+1][b],rows[k][b]]
            # Main faces carry sparse broad relief, with the shared borders held fixed.
            if a in (6,8) and k%3!=0 and not 51<=stations[k]<=55:
                ps=[Vector(verts[i]) for i in ids];mid=sum(ps,Vector())/4;mid.x-=.07+.04*((k+a)%3)
                q=point(mid)
                for n in range(4):face([ids[n],ids[(n+1)%4],q],kind)
            else:face(ids,kind)
    elif a==4:
        # Shared low courtyard. A winding lane is cut into this surface's topology.
        pathleft=[];pathright=[]
        for gz in stations:
            dc=plan(gz,[(37.5,7.0),(40,5.9),(43,6.1),(46,6.3),(49,6.2),(51,6.8),(53,8.0),(55,6.8),(58,5.9),(60.5,6.1)])
            pathleft.append(p3(dc-.55,gz,lowh(gz)));pathright.append(p3(dc+.55,gz,lowh(gz)))
        # Keep the closed lane inside the patch ends to avoid touching constraints.
        pathpoly=pathleft[1:-1]+pathright[-2:0:-1]
        extra=[]
        for gz in np.arange(38.1,60.1,.9):
            da=plan(gz,low_crown);db=plan(gz,high_toe)
            for ddg in np.arange(da+.45,db-.25,.95):extra.append(p3(float(ddg),float(gz),lowh(float(gz))))
        fill_polygon(boundary,kind,extra,lambda xx,zz:lowh(zz),[pathpoly])
    elif a==11:
        extra=[p3(float(ddg),float(gz),highh(float(gz))+.08*(ddg-20)/3) for gz in np.arange(38,60,.9) for ddg in np.arange(20,22.8,1)]
        fill_polygon(boundary,kind,extra,lambda xx,zz:highh(zz))
    else:
        for k in range(len(rows)-1):face([rows[k][a],rows[k+1][a],rows[k+1][b],rows[k][b]],kind)

# Transition annulus uses the original boundary vertices; there is no stacked terrain.
inner_ids=[r[0] for r in rows]+rows[-1][1:]+[r[-1] for r in rows[-2::-1]]+rows[0][-2:0:-1]
allids=outer_ids+inner_ids;coords=[Vector((verts[i][0],verts[i][1])) for i in allids]
edges=[(i,(i+1)%len(outer_ids)) for i in range(len(outer_ids))]
offset=len(outer_ids);edges.extend((offset+i,offset+(i+1)%len(inner_ids)) for i in range(len(inner_ids)))
rv,re,rf,orig,_,_=delaunay_2d_cdt(coords,edges,[list(range(len(outer_ids)))],1,1e-6,True)
mapped=[]
for i,p in enumerate(rv):mapped.append(allids[orig[i][0]] if orig[i] else point((p.x,p.y,old_ground(p.x,-p.y))))
inner_plan=[(verts[i][0],verts[i][1]) for i in inner_ids]
for f in rf:
    ids=[mapped[i] for i in f];p=sum((Vector(verts[i]) for i in ids),Vector())/len(ids)
    if inside_polygon(p.x,p.y,inner_plan):continue
    hit,n,pi,_=old_bvh.ray_cast(Vector((p.x,p.y,80)),Vector((0,0,-1)),300)
    col=np.mean([oldcols[v] for v in oldmesh.polygons[pi].vertices],axis=0).tolist() if hit else [1,0,0,0]
    face(ids,'transition',col)

newmesh=bpy.data.meshes.new('C25_ContourEdgesSharedCourtyard');newmesh.from_pydata(verts,[],faces);newmesh.update()
archive=bpy.data.collections.new('Archive_RejectedL24_20261120');bpy.context.scene.collection.children.link(archive);archive.objects.link(terrain);C.objects.unlink(terrain);archive.hide_render=True;archive.hide_viewport=True
terrain=bpy.data.objects.new('C25_ContourBuiltCoast',newmesh);C.objects.link(terrain)
newmesh.materials.append(bpy.data.materials['Ref_L24_Landform'])
attr=newmesh.color_attributes.new(name='LandUse',type='FLOAT_COLOR',domain='CORNER');newmesh.color_attributes.active_color=attr
colors=[c for row in faceweights for c in row];attr.data.foreach_set('color',np.array(colors,np.float32).ravel())
uv=newmesh.uv_layers.new(name='UVMap')
for p,kind in zip(newmesh.polygons,facekind):
    p.use_smooth=kind not in ['rock','soil']
    for li in p.loop_indices:
        v=newmesh.vertices[newmesh.loops[li].vertex_index].co
        uv.data[li].uv=(v.y/2.4,v.z/2.4) if kind=='rock' else (v.x/2.4,v.y/2.4)
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
def ground(x,z):
    hit,*_=ground_bvh.ray_cast(Vector((x,-z,80)),Vector((0,0,-1)),300)
    return hit.z if hit else -15
def export_land():
    bpy.ops.object.select_all(action='DESELECT');terrain.hide_set(False);terrain.select_set(True);bpy.context.view_layer.objects.active=terrain
    bpy.ops.export_scene.gltf(filepath=str(OUT/'terrain.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='ACTIVE')
def refresh_height():
    values=[round(ground(float(shore(gz)+ddg),float(gz)),5) for gz in np.arange(-30,90.001,.25) for ddg in np.arange(-20,50.001,.25)]
    (OUT/'shore_relief_height.json').write_text(json.dumps({'d0':-20,'z0':-30,'step':.25,'columns':281,'rows':481,'heights':values}),encoding='utf8')
refresh_height();export_land();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
(LOG/'topology_authored.json').write_text(json.dumps({'patch_rows':[j0,j1],'patch_columns':[i0,i1],'stations':stations,'low_crown':low_crown,'high_crown':high_crown,'high_toe':high_toe,'vertices':len(newmesh.vertices),'faces':len(newmesh.polygons)},indent=2),encoding='utf8')
print('CONTOUR_PATCH',j0,j1,i0,i1,'vertices',len(newmesh.vertices),'faces',len(newmesh.polygons))
