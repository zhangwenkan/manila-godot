# Authored cliff and soil replacement. Execute once in the verified Blender MCP GUI.
exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
from mathutils.geometry import delaunay_2d_cdt
from collections import Counter
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
assert not terrain.get('rock21_rebuilt'),'Already applied'
bpy.ops.wm.save_as_mainfile(filepath=str(LOG/'before/harbor_shore_control_mcp.blend'),copy=True)
old_bvh=ground_bvh
def oldground(x,z):
    h,*_=old_bvh.ray_cast(Vector((float(x),-float(z),80)),Vector((0,0,-1)),300)
    return h.z if h else -15
oldcols=mesh.color_attributes['LandUse']
# One continuous domain: both slopes, their low court, and their upper ground.
chosen={p.index for p in mesh.polygons if 35.7<-p.center.y<66.0 and -.02<p.center.x-float(shore(-p.center.y))<29.0}
counts=Counter()
for i in chosen:
    vs=list(mesh.polygons[i].vertices)
    for a,b in zip(vs,vs[1:]+vs[:1]):counts[tuple(sorted((a,b)))]+=1
adj={}
for (a,b),n in counts.items():
    if n==1:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
assert all(len(v)==2 for v in adj.values()),'Selected outer perimeter branches'
boundary=[min(adj)];prev=None;cur=boundary[0]
while True:
    nxt=next(n for n in adj[cur] if n!=prev)
    if nxt==boundary[0]:break
    boundary.append(nxt);prev,cur=cur,nxt
    assert len(boundary)<=len(adj)
assert len(boundary)==len(adj),'Selected domain has holes'
base=[tuple(v.co) for v in mesh.vertices]
outer=[(base[i][0],-base[i][1]) for i in boundary]
def inside(x,z,poly):
    value=False
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if (a[1]>z)!=(b[1]>z) and x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]:value=not value
    return value
def line(z,keys):return float(np.interp(z,[r[0] for r in keys],[r[1] for r in keys]))
def low(z):return line(z,[(35,1.65),(42.7,1.65),(46.3,1.18),(66,1.18)])
def high(z):return line(z,[(35,4.14),(51,4.14),(56,4.29),(66,4.29)])
# Independently shaped crowns and feet. The inlet at z52 interrupts the escarpment.
crown=[(35.5,24.0),(37.0,22.0),(38.3,20.2),(39.4,18.6),(40.7,18.55),(41.6,18.0),(42.4,17.9),(43.1,18.65),(43.8,19.1),(44.7,20.45),(45.8,21.25),(46.7,21.7),(47.6,22.4),(48.4,22.6),(49.3,24.0),(50.3,26.0),(51.5,28.0),(52.6,28.35),(53.5,27.7),(54.3,25.8),(55.1,23.1),(55.9,22.0),(56.8,21.8),(57.7,22.0),(58.7,21.3),(59.6,21.0),(60.3,20.35),(61.2,20.6),(62.2,21.1),(63.0,21.4),(64.1,22.5),(66.0,24.5)]
toe=[(35.5,20.7),(37,19.2),(38.3,18.2),(39.6,17.0),(41,16.7),(42.1,16.0),(43.4,16.7),(44.4,17.8),(45.1,18.9),(46.2,19.8),(47.9,20.7),(49.2,22.2),(50.4,24.0),(51.7,26.6),(52.9,26.8),(54.1,24.0),(55.0,21.5),(56.2,20.2),(57.2,20.45),(58.4,19.35),(59.7,19.1),(60.7,18.8),(62.1,19.5),(63.4,19.7),(64.3,20.7),(66.0,22.2)]
# Front earth crown remains behind a broad changing apron. No uniform exposed band.
earthtop=[(35.5,10.7),(37.0,10.9),(39.0,10.75),(41.1,10.4),(42.6,10.85),(43.7,11.7),(45.0,12.1),(46.8,12.7),(48.5,13.1),(50.1,13.0),(51.3,13.3),(52.4,14.7),(53.4,16.0),(54.2,14.0),(55.2,12.9),(57,12.6),(59,12.2),(60.3,11.7),(61,13.5),(63,13.7),(66,12.0)]
earthfoot=[(35.5,8.4),(37,8.7),(39.2,8.25),(41.4,7.7),(43.3,8.5),(45.1,8.95),(46.8,9.65),(48.1,10.1),(49.5,9.3),(51,9.0),(53,9.1),(54.9,9.2),(56,10.0),(58,8.9),(60,8.4),(61,11.4),(63,12.0),(66,9.3)]
# Foundation islands preserve the real rotated floor footprint and surrounding bearing ground.
found=json.loads((LOG/'foundations.json').read_text())
floors=[]
for f in found:
    if max(-p[1] for p in f['corners'])<35 or min(-p[1] for p in f['corners'])>67:continue
    poly=[(p[0],-p[1]) for p in f['corners'][:4]]
    floors.append(poly)
def edge_distance(x,z,poly):
    best=1e9
    for a,b in zip(poly,poly[1:]+poly[:1]):
        dx=b[0]-a[0];dz=b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz)))
        best=min(best,math.hypot(x-a[0]-t*dx,z-a[1]-t*dz))
    return best
def cliff_value(x,z):
    ct=line(z,crown);ft=line(z,toe);lh=low(z);hh=high(z)
    if x<=ft:return lh,0
    if x>=ct:return hh,0
    t=(x-ft)/(ct-ft)
    # Main steep planes are separated by offset short shoulders. Each return is distinct.
    bay=float(smooth(49.5,51.5,z)*(1-smooth(52.8,55.0,z)))
    shelf=float(smooth(42.0,43.1,z)*(1-smooth(44.2,45.6,z)))
    shoulder=.46+.16*math.sin(z*.63)+.09*math.sin(z*1.42)
    heights=[0,.07,shoulder-.045,shoulder+.035,.94,1]
    knots=[0,.22,.42,.68 if shelf>.15 else .51,.79,1]
    frac=float(np.interp(t,knots,heights))
    frac=frac*(1-bay*.74)+float(smooth(0,1,t))*bay*.74
    return lh+(hh-lh)*frac,1-bay*.8
def authored(x,z):
    old=oldground(x,z);lh=low(z);hh=high(z)
    ct=line(z,crown);ft=line(z,toe);et=line(z,earthtop);ef=line(z,earthfoot)
    if x>=ft:
        h,rock=cliff_value(x,z)
        if x>ct:h=hh+.045*math.sin((x-ct)*1.0)*math.sin(z*.42)
    else:
        rock=0
        if x>=et:h=lh
        elif x<=ef:h=old if old<.32 else .24
        else:
            t=(x-ef)/(et-ef)
            # Distinct soft berm / brief earth cut / sloping mouth profiles.
            cut=float(smooth(38.0,39.6,z)*(1-smooth(41.2,42.4,z)))+.55*float(smooth(56,57,z)*(1-smooth(58.0,59,z)))
            cut=min(cut,1)
            frac=float(smooth(0,1,t))*(1-cut)+float(np.interp(t,[0,.45,.63,.82,1],[0,.13,.76,.96,1]))*cut
            h=.24+(lh-.24)*frac
    # The shared courtyard's beach entrance slopes inland without a fan triangle.
    mouth=float(smooth(50.9,52.1,z)*(1-smooth(54.2,55.3,z)))
    if x<19 and z<60:
        ramp=.23+(lh-.23)*float(smooth(8.8,17.2,x))
        h=h*(1-mouth)+ramp*mouth
    # Preserve cargo basin and wet coastline, and blend only at the far ends of this patch.
    w=float(smooth(35.8,38.0,z)*(1-smooth(63.2,65.6,z)))
    w*=float(smooth(.2,.75,x-float(shore(z))))
    w*=1-float(smooth(27.5,28.7,x-float(shore(z))))
    if 59.4<z<65 and x<15.4:w*=float(smooth(14.5,15.6,x))
    h=old*(1-w)+h*w
    for poly in floors:
        d=edge_distance(x,z,poly)
        fw=1 if inside(x,z,poly) else 1-float(smooth(.38,.85,d))
        if fw>0:h=h*(1-fw)+old*fw
    return h
# Dense internal sampling only; original perimeter vertices remain unsplit and shared.
ids=list(boundary);coords=[Vector(base[i][:2]) for i in ids];edges=[(i,(i+1)%len(ids)) for i in range(len(ids))]
lookup={(round(p.x,6),round(p.y,6)):i for i,p in enumerate(coords)}
def add(x,z):
    key=(round(float(x),6),round(-float(z),6))
    if key in lookup:return lookup[key]
    if not inside(x,z,outer):return None
    i=len(coords);coords.append(Vector((x,-z)));ids.append(len(base));base.append((x,-z,authored(x,z)));lookup[key]=i;return i
for z in np.arange(36.0,65.8,.28):
    for x in np.arange(float(shore(z))+.18,float(shore(z))+28.8,.30):add(float(x),float(z))
# Explicit authored crease chains, each independently located; grass/earth boundaries use geometry.
for curve in [crown,toe,earthtop,earthfoot]:
    chain=[]
    for (za,xa),(zb,xb) in zip(curve,curve[1:]):
        n=max(1,int(math.ceil(math.hypot(zb-za,xb-xa)/.28)))
        for k in range(n):
            t=k/n;z=za+(zb-za)*t;x=xa+(xb-xa)*t
            if 37.9<z<63.3:
                idx=add(x,z)
                if idx is not None:chain.append(idx)
    edges.extend((a,b) for a,b in zip(chain,chain[1:]) if a!=b)
rv,re,rf,orig,_,_=delaunay_2d_cdt(coords,edges,[list(range(len(boundary)))],1,1e-7,True)
mapping=[]
for i,p in enumerate(rv):
    if orig[i]:mapping.append(ids[orig[i][0]])
    else:mapping.append(len(base));base.append((p.x,p.y,authored(p.x,-p.y)))
faces=[];colors=[];newstart=0
for p in mesh.polygons:
    if p.index in chosen:continue
    faces.append(list(p.vertices));colors.extend(tuple(oldcols.data[li].color) for li in p.loop_indices)
newstart=len(faces)
def weights(x,z,h,nz):
    ct=line(z,crown);ft=line(z,toe);et=line(z,earthtop);ef=line(z,earthfoot)
    grain=.065*math.sin(z*3.1+x*1.7)+.03*math.sin(x*5.2-z*2.4)
    if ft-.15<x<ct+.15 and h>low(z)+.14:
        rim=(h-low(z))/(high(z)-low(z))
        rock=(1-float(smooth(.88,.99,rim+grain*.3)))*float(smooth(.01,.12,rim))
        rock*=1-.65*float(smooth(.65,.94,nz))
        return (1-rock,rock,0,0)
    mouth=float(smooth(51.0,52.0,z)*(1-smooth(54.2,55.3,z)))
    if h<.29:return (0,0,0,0)
    if x<et+.3:
        t=max(0,min(1,(x-ef)/max(.2,et-ef)))
        grass=float(smooth(.30,.74,t+grain))*(1-mouth*.94)
        soil=float(smooth(.15,.40,t))*(1-grass)
        soil*=float(smooth(.28,.6,h))
        return (grass,0,0,soil)
    if mouth>.15 and x<19:return (1-mouth*.8,0,mouth*.3,mouth*.5)
    hit,n,pi,_=old_bvh.ray_cast(Vector((x,-z,80)),Vector((0,0,-1)),300)
    col=np.mean([oldcols.data[i].color for i in mesh.polygons[pi].loop_indices],axis=0)
    if col[1]>.2 or col[3]>.4:col=np.array([1,0,0,0])
    return tuple(col)
for f in rf:
    vi=[mapping[i] for i in f];ps=[Vector(base[i]) for i in vi]
    cross=(ps[1]-ps[0]).cross(ps[2]-ps[0])
    if cross.z<0:vi.reverse()
    if abs(cross.z)<1e-10:continue
    faces.append(vi)
    nz=abs(cross.normalized().z)
    for i in vi:
        x,y,h=base[i];colors.append(weights(x,-y,h,nz))
dm=bpy.data.meshes.new('R27_IndependentCliffHeads_EarthCoves');dm.from_pydata(base,[],faces);dm.update();dm.materials.append(mesh.materials[0])
ca=dm.color_attributes.new(name='LandUse',type='FLOAT_COLOR',domain='CORNER');dm.color_attributes.active_color=ca;ca.data.foreach_set('color',np.array(colors,np.float32).ravel())
uv=dm.uv_layers.new(name='UVMap');indices=np.array([l.vertex_index for l in dm.loops]);uv.data.foreach_set('uv',(np.asarray(base,np.float32)[indices,:2]/2.4).ravel())
for p in dm.polygons:p.use_smooth=True
dm.set_sharp_from_angle(angle=math.radians(48))
terrain.data=dm;mesh=dm;terrain['rock21_rebuilt']=True
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
refresh_height();export_land();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print(json.dumps({'replaced_faces':len(chosen),'authored_faces':len(faces)-newstart,'vertices':len(base),'source_saved':True}))
