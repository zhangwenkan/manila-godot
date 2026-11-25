"""Author a shared coast occupancy map from the final mesh, inside Blender MCP."""
import bpy,json,math,numpy as np,ast,struct,zlib
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/ground_integration_20261123';OUT=ROOT/'assets/reference'
for node in ast.parse((ROOT/'source/ground23_02_surfaces.py').read_text(encoding='utf8')).body:
    if isinstance(node,ast.FunctionDef) and node.name in ('ss','noise','save_image'):
        exec(compile(ast.Module(body=[node],type_ignores=[]),'G23 helpers','exec'),globals())
terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
assert terrain.get('ground23_forms'),'Apply the reviewed forms before rasterizing occupancy'
n=2048;v,u=np.mgrid[0:n,0:n].astype(np.float32)
X=-4+48*(u+.5)/n;Z=-15+97*(v+.5)/n
land=np.zeros((n,n,4),np.float32);height=np.full((n,n),-100,np.float32);normal=np.ones((n,n),np.float32)
p=np.array([v.co[:] for v in mesh.vertices],np.float32)
attrs=np.array([c.color[:] for c in mesh.color_attributes['LandUse'].data],np.float32)
norms=np.array([v.normal.z for v in mesh.vertices],np.float32)
mesh.calc_loop_triangles()
for tri in mesh.loop_triangles:
    pp=p[list(tri.vertices)];px=(pp[:,0]+4)/48*n-.5;py=(-pp[:,1]+15)/97*n-.5
    x0=max(0,int(np.ceil(px.min())));x1=min(n-1,int(np.floor(px.max())))
    y0=max(0,int(np.ceil(py.min())));y1=min(n-1,int(np.floor(py.max())))
    if x1<x0 or y1<y0:continue
    den=(py[1]-py[2])*(px[0]-px[2])+(px[2]-px[1])*(py[0]-py[2])
    if abs(den)<1e-12:continue
    yy,xx=np.mgrid[y0:y1+1,x0:x1+1].astype(np.float32)
    a=((py[1]-py[2])*(xx-px[2])+(px[2]-px[1])*(yy-py[2]))/den
    b=((py[2]-py[0])*(xx-px[2])+(px[0]-px[2])*(yy-py[2]))/den;c=1-a-b
    inside=(a>=-1e-5)&(b>=-1e-5)&(c>=-1e-5)
    h=a*pp[0,2]+b*pp[1,2]+c*pp[2,2];dest=height[y0:y1+1,x0:x1+1]
    valid=inside&(h>=dest)
    if not valid.any():continue
    cols=attrs[list(tri.loops)]
    land[y0:y1+1,x0:x1+1][valid]=(a[...,None]*cols[0]+b[...,None]*cols[1]+c[...,None]*cols[2])[valid]
    dest[valid]=h[valid];nn=norms[list(tri.vertices)]
    normal[y0:y1+1,x0:x1+1][valid]=(a*nn[0]+b*nn[1]+c*nn[2])[valid]
assert height.min()>-99,'Map contains uncovered terrain'

def sample(arr,x,z,x0=-4,z0=-15,sx=48,sz=97):
    h,w=arr.shape[:2];xx=np.clip((x-x0)/sx*w-.5,0,w-1.0001);yy=np.clip((z-z0)/sz*h-.5,0,h-1.0001)
    ix=xx.astype(np.int32);iy=yy.astype(np.int32);fx=(xx-ix)[...,None];fy=(yy-iy)[...,None]
    return ((arr[iy,ix]*(1-fx)+arr[iy,ix+1]*fx)*(1-fy)+(arr[iy+1,ix]*(1-fx)+arr[iy+1,ix+1]*fx)*fy)

# The current mesh carries its grass crown and rock foot with the sculpt.
# Reusing the old top-down S23 map here would put the old straight boundary
# back over a newly displaced rock face. Entrances are authored below instead.
# Avoid material islands left on the newly turned crown: face angle separates roots/rock.
rock=land[...,1]*(1-ss(.80,.97,normal))
land[...,0]+=land[...,1]-rock;land[...,1]=rock
# Irregular edges are authored at two scales, not a wider transparent blend.
warp_x=noise(n,36,611)*.33+noise(n,109,612)*.11
warp_z=noise(n,31,613)*.38+noise(n,103,614)*.10
warped=sample(land,X+warp_x,Z+warp_z)
edgezone=1-np.max(np.concatenate((land,np.maximum(0,1-land.sum(axis=2))[...,None]),axis=2),axis=2)
disturb=ss(.015,.16,edgezone)*ss(.2,.65,height)
land=land*(1-disturb[...,None])+warped*disturb[...,None]
# Exposed roots at the upper soil edge remain earth, not an extra continuous stripe.
# A sand inlet and a projecting grass shoulder match the actual sculpted landform.
bay=np.exp(-(((X-12.2)/2.2)**2+((Z-12.8)/2.0)**2)*1.6)*ss(.3,.8,normal)
bay*=1-ss(1.05,1.65,height)
land*=1-(bay*.92)[...,None]
shoulder=np.exp(-(((X-14.4)/1.9)**2+((Z-15.1)/1.7)**2)*1.8)*ss(.45,.8,normal)
land*=1-(shoulder*.60)[...,None];land[...,0]+=shoulder*.60

def band(a,b,c,d,t):return ss(a,b,t)*(1-ss(c,d,t))

# These two occupations follow the actual G23 second sculpt. Their centres
# reach full material weight: a brown strip must visibly end at each contact.
coast_warp=noise(n,43,618)*.20+noise(n,131,619)*.045
bay_center=12.5+.28*(X-10.5)
bay_width=np.clip(2.5-.30*(X-10.0),.75,3.0)
bay=(1-ss(.72,1.10,abs(Z-bay_center+coast_warp)/bay_width))*(1-ss(14.0,15.5,X+coast_warp))
bay*=1-ss(1.05,1.58,height)
land*=1-bay[...,None]
grass_tongue=band(8.9,10.0,12.3,13.7,X+coast_warp)*band(28.5,29.8,32.4,34.0,Z-coast_warp)
grass_tongue*=ss(.30,.47,height)*ss(.33,.72,normal)
land*=1-grass_tongue[...,None];land[...,0]+=grass_tongue
if terrain.get('ground23_low_shoulder_18'):
    low_grass=band(9.9,10.5,12.25,12.95,X+coast_warp)*band(54.1,55.0,57.15,58.2,Z-coast_warp)
    low_grass*=ss(.30,.43,height)*ss(.48,.78,normal)
    land*=1-low_grass[...,None];land[...,0]+=low_grass
# Two narrow, asymmetric grass incursions split the low earth face. They
# descend existing gentle shoulders, never coat the steep upper rock.
for cx,cz,rx,rz in [(11.9,17.0,1.15,1.45),(11.6,26.9,1.0,1.25)]:
    d=np.sqrt(((X-cx-coast_warp)/rx)**2+((Z-cz)/rz)**2)
    w=(1-ss(.45,1.1,d))*ss(.42,.72,height)*(1-ss(1.8,2.1,height))*ss(.55,.86,normal)
    land*=1-w[...,None];land[...,0]+=w

# Actual entrances and two shared stopping spaces govern the walking surface.
routes=json.loads((ROOT/'captures/rock_path_sample_20261123/routes.json').read_text(encoding='utf8'))
routes.append({'name':'trading_lower_lane','halfwidth':.63,'points':[(13.7,2.4),(13.2,5.2),(13.0,8.1),(12.8,10.4),(12.4,13.2),(12.7,16),(12.9,20)]})
routes.append({'name':'trading_entry','halfwidth':.65,'points':[(13.1,7),(14.8,7)]})
routes.append({'name':'diner_sari_shared_lane','halfwidth':.68,'points':[(10.85,40.7),(11.3,42.0),(12.5,43.1),(13.2,44.2),(12.65,45.5),(12.4,47.5),(12.6,49.3),(13.0,51.5),(13.7,53.7),(13.8,56.0),(13.75,57.4),(14.0,59.2),(14.1,62.0)]})
routes.append({'name':'sari_entry','halfwidth':.72,'points':[(13.75,57.35),(14.7,57.35)]})
# Erase the old linear paint where this authored network replaces it.
replace=ss(-1,2,Z)*(1-ss(61,64,Z))*ss(8,10,X)*(1-ss(32,34,X))
former=land[...,2]*replace;land[...,0]+=former;land[...,2]-=former
pathweight=np.zeros((n,n),np.float32)
edge=noise(n,37,621)*.25+noise(n,127,622)*.065
for route in routes:
    pts=route['points'];width=route['halfwidth']
    # Evaluate only a bounded patch per route to avoid full-map work per segment.
    xa=min(p[0] for p in pts)-width-1;xb=max(p[0] for p in pts)+width+1
    za=min(p[1] for p in pts)-width-1;zb=max(p[1] for p in pts)+width+1
    i0=max(0,int((xa+4)/48*n));i1=min(n,int((xb+4)/48*n)+1)
    j0=max(0,int((za+15)/97*n));j1=min(n,int((zb+15)/97*n)+1)
    xx=X[j0:j1,i0:i1];zz=Z[j0:j1,i0:i1];dd=np.full(xx.shape,100,np.float32)
    for a,b in zip(pts,pts[1:]):
        dx,dz=b[0]-a[0],b[1]-a[1];den=dx*dx+dz*dz
        if den<1e-9:continue
        t=np.clip(((xx-a[0])*dx+(zz-a[1])*dz)/den,0,1)
        dd=np.minimum(dd,np.hypot(xx-a[0]-t*dx,zz-a[1]-t*dz))
    # Passage is narrower between doors, broader at their common forecourt.
    # Quiet connecting footpaths narrow, while the stopping places below
    # provide the large worn surface; width does not oscillate like a ribbon.
    if route['name'] in ('lower_lane','trading_lower_lane'):
        widthfield=width*(.60+.15*np.cos(zz*.23+xx*.11))+edge[j0:j1,i0:i1]
    else:
        widthfield=width*(.78+.12*np.sin(zz*.31+xx*.17))+edge[j0:j1,i0:i1]
    w=1-ss(widthfield-.10,widthfield+.24,dd)
    pathweight[j0:j1,i0:i1]=np.maximum(pathweight[j0:j1,i0:i1],w)

def worn_polygon(points):
    inside=np.zeros((n,n),bool);distance=np.full((n,n),100,np.float32)
    for (ax,az),(bx,bz) in zip(points,points[1:]+points[:1]):
        if abs(bz-az)>1e-7:inside^=((az>Z)!=(bz>Z))&(X<(bx-ax)*(Z-az)/(bz-az)+ax)
        dx,dz=bx-ax,bz-az;t=np.clip(((X-ax)*dx+(Z-az)*dz)/(dx*dx+dz*dz),0,1)
        distance=np.minimum(distance,np.hypot(X-ax-t*dx,Z-az-t*dz))
    signed=np.where(inside,-distance,distance)+edge*.58
    return 1-ss(-.11,.23,signed)

# Unequal forecourts taper into the actual entrances and side working areas.
# No circular discs are stamped over the narrow walking line.
courts=[
 [(11.6,22.5),(12.4,21.3),(14.75,21.8),(14.8,26.3),(13.35,27.0),(12.0,25.4)],
 [(12.1,5.1),(13.8,4.45),(15.05,5.8),(15.05,9.25),(13.7,9.55),(12.1,7.6)],
 [(13.7,31.6),(15.1,30.9),(16.3,31.8),(15.6,33.1),(14.3,32.9)],
 [(21.3,27.6),(22.9,27.7),(23.2,28.4),(22.85,29.5),(21.7,29.4)],
 [(21.6,13.8),(23.6,13.8),(23.6,15.65),(22.2,15.8),(21.5,15.1)],
 [(11.5,48.5),(13.6,48.3),(14.1,49.1),(13.8,50.4),(12.3,50.1)],
 [(12.7,55.7),(14.45,55.4),(14.75,56.15),(14.8,58.5),(13.5,58.8),(12.9,58.0)],
]
for polygon in courts:pathweight=np.maximum(pathweight,worn_polygon(polygon))
pathweight*=ss(.48,.76,normal)*ss(.25,.65,height)
# Sandy mouths spread onto low land instead of closing with a painted round cap.
mouth=ss(10.8,8.6,X)*np.exp(-((Z-39.0)/1.65)**2)
pathweight*=1-mouth
# The sand cove absorbs its low walking surface; the remaining inland path
# bends into the grass shoulder rather than drawing across the cove as paint.
pathweight*=1-bay*.96
land*=1-pathweight[...,None];land[...,2]+=pathweight
land*=1-(mouth*.85)[...,None]
land=np.clip(land,0,1);land/=np.maximum(1,land.sum(axis=2))[...,None]
save_image('G23_LandUse',land[...,:3],land[...,3],True)
np.savez_compressed(str(LOG/'land_data.npz'),land=land,height=height,normal=normal)
nodes=mesh.materials[0].node_tree.nodes
node=nodes.get('G23_LandUse') or nodes.new('ShaderNodeTexImage');node.name='G23_LandUse';node.image=bpy.data.images['G23_LandUse']
(LOG/'land_use.json').write_text(json.dumps({'size':[n,n],'bounds_xz':[-4,-15,44,82],'routes':len(routes),'forecourt_polygons':courts,'sand_inlet':[12.2,12.8],'grass_shoulder':[11.3,31.1],'roles':'grass rock path soil; residual sand','shape_source':'current mesh roles, no stale S23 map overlay; G23 stronger forms'},indent=2),encoding='utf8')
print('Authored complete coast material occupancy and shared worn passages')
