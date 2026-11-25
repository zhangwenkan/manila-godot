"""Correct three authored road contacts in the owned GUI Blender MCP.

Use G23 final occupancy as the immutable starting image, replace only the
reviewed contact areas, and give connected routes continuous core weights.
No historical top-level operation is replayed.
"""
import bpy,json,ast,math,struct,zlib,numpy as np
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/road_contacts_20261123';OUT=ROOT/'assets/reference'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
assert terrain.get('road23_contacts_grade'),'Reviewed physical contacts must precede the map'
for nd in ast.parse((ROOT/'source/ground23_02_surfaces.py').read_text(encoding='utf8')).body:
    if isinstance(nd,ast.FunctionDef) and nd.name in ('ss','noise','save_image'):
        exec(compile(ast.Module(body=[nd],type_ignores=[]),'Shared pure image helpers','exec'),globals())
with np.load(str(ROOT/'captures/ground_integration_20261123/land_data.npz')) as src:
    before=src['land'].copy()
n=2048;v,u=np.mgrid[0:n,0:n].astype(np.float32)
X=-4+48*(u+.5)/n;Z=-15+97*(v+.5)/n
height=np.full((n,n),-100,np.float32);normal=np.ones((n,n),np.float32)
p=np.array([q.co[:] for q in mesh.vertices],np.float32);nz=np.array([q.normal.z for q in mesh.vertices],np.float32)
mesh.calc_loop_triangles()
for t in mesh.loop_triangles:
    pp=p[list(t.vertices)];px=(pp[:,0]+4)/48*n-.5;py=(-pp[:,1]+15)/97*n-.5
    x0=max(0,int(np.ceil(px.min())));x1=min(n-1,int(np.floor(px.max())))
    y0=max(0,int(np.ceil(py.min())));y1=min(n-1,int(np.floor(py.max())))
    if x1<x0 or y1<y0:continue
    den=(py[1]-py[2])*(px[0]-px[2])+(px[2]-px[1])*(py[0]-py[2])
    if abs(den)<1e-12:continue
    yy,xx=np.mgrid[y0:y1+1,x0:x1+1].astype(np.float32)
    a=((py[1]-py[2])*(xx-px[2])+(px[2]-px[1])*(yy-py[2]))/den
    b=((py[2]-py[0])*(xx-px[2])+(px[0]-px[2])*(yy-py[2]))/den;c=1-a-b
    h=a*pp[0,2]+b*pp[1,2]+c*pp[2,2];dest=height[y0:y1+1,x0:x1+1]
    valid=(a>=-1e-5)&(b>=-1e-5)&(c>=-1e-5)&(h>=dest)
    if not valid.any():continue
    dest[valid]=h[valid];nn=nz[list(t.vertices)]
    normal[y0:y1+1,x0:x1+1][valid]=(a*nn[0]+b*nn[1]+c*nn[2])[valid]
assert height.min()>-99
def band(t,a,b,c,d):return ss(a,b,t)*(1-ss(c,d,t))
trade=band(X,10.4,10.9,15.6,16.2)*band(Z,9.1,9.8,20.6,21.1)
grill=band(X,9.9,10.5,15.4,16.0)*band(Z,20.4,21.1,27.0,27.8)
clinic=band(X,20.5,21.0,25.0,25.6)*band(Z,29.0,29.45,33.6,34.2)
scope=np.maximum.reduce([trade,grill,clinic])
# Recover the surrounding ground below the old painted roads. The local fill
# only supplies background where the redesigned network no longer passes.
# It cannot alter any pixel outside the explicit three contact masks.
i0,i1=int((9+4)/48*n),int((27+4)/48*n)
j0,j1=int((8+15)/97*n),int((35+15)/97*n)
work=before[j0:j1,i0:i1].copy();known=work[...,2]<.02
work[...,2]=0;work[~known]=0
for it in range(240):
    if known.all():break
    sums=np.zeros_like(work);counts=np.zeros(known.shape,np.float32)
    for axis,sign in ((0,-1),(0,1),(1,-1),(1,1)):
        valid=np.roll(known,sign,axis);vals=np.roll(work,sign,axis)
        if axis==0:valid[0 if sign==1 else -1,:]=False
        else:valid[:,0 if sign==1 else -1]=False
        sums+=vals*valid[...,None];counts+=valid
    take=(~known)&(counts>0);work[take]=sums[take]/counts[take][:,None];known[take]=True
assert known.all(),'Road-background fill did not reach the forecourt interior'
land=before.copy();land[j0:j1,i0:i1]=work
# The restaurant apron stops on the crest. Below it, one soil slope meets
# sand at its foot; no secondary grass ribbon snakes through the soil face.
soil_scope=band(X,10.0,10.6,12.5,13.05)*band(Z,21.0,21.7,26.0,26.8)
sand=1-ss(.36,.61,height)
grass=ss(.96,1.22,height)*ss(.75,.96,normal)*(1-sand)
soil=1-sand-grass
soil_roles=np.stack((grass,np.zeros_like(grass),np.zeros_like(grass),soil),axis=-1)
land=land*(1-soil_scope[...,None])+soil_roles*soil_scope[...,None]

routes=json.loads((ROOT/'captures/rock_path_sample_20261123/routes.json').read_text(encoding='utf8'))
routes += [
 {'name':'trading_lower_lane','halfwidth':.48,'points':[(13.7,2.4),(13.2,5.2),(13.0,8.1),(12.8,10.4),(13.8,11.5),(14.1,12.8),(14.1,14.1),(13.6,15.7),(14.1,16.7),(14.1,18.2),(13.8,19.1),(12.9,20)]},
 {'name':'trading_entry','halfwidth':.65,'points':[(13.1,7),(14.8,7)]},
 {'name':'diner_sari_shared_lane','halfwidth':.68,'points':[(10.85,40.7),(11.3,42),(12.5,43.1),(13.2,44.2),(12.65,45.5),(12.4,47.5),(12.6,49.3),(13,51.5),(13.7,53.7),(13.8,56),(13.75,57.4),(14,59.2),(14.1,62)]},
 {'name':'sari_entry','halfwidth':.72,'points':[(13.75,57.35),(14.7,57.35)]},
]
edge=noise(n,87,23021)*.055+noise(n,211,23022)*.018
pathweight=np.zeros((n,n),np.float32)
for route in routes:
    pts=route['points'];width=route['halfwidth']
    if route['name']=='clinic_ramp':width=.70
    if route['name']=='lower_lane':width=.53
    xa=min(pt[0] for pt in pts)-width-.4;xb=max(pt[0] for pt in pts)+width+.4
    za=min(pt[1] for pt in pts)-width-.4;zb=max(pt[1] for pt in pts)+width+.4
    a0=max(0,int((xa+4)/48*n));a1=min(n,int((xb+4)/48*n)+1)
    b0=max(0,int((za+15)/97*n));b1=min(n,int((zb+15)/97*n)+1)
    xx=X[b0:b1,a0:a1];zz=Z[b0:b1,a0:a1];dd=np.full(xx.shape,100,np.float32)
    for a,b in zip(pts,pts[1:]):
        dx,dz=b[0]-a[0],b[1]-a[1];den=dx*dx+dz*dz
        if den<1e-9:continue
        t=np.clip(((xx-a[0])*dx+(zz-a[1])*dz)/den,0,1)
        dd=np.minimum(dd,np.hypot(xx-a[0]-t*dx,zz-a[1]-t*dz))
    w=1-ss(width-.09,width+.13,dd+edge[b0:b1,a0:a1])
    pathweight[b0:b1,a0:a1]=np.maximum(pathweight[b0:b1,a0:a1],w)

def polygon(points):
    inside=np.zeros((n,n),bool);distance=np.full((n,n),100,np.float32)
    for (ax,az),(bx,bz) in zip(points,points[1:]+points[:1]):
        if abs(bz-az)>1e-7:inside^=((az>Z)!=(bz>Z))&(X<(bx-ax)*(Z-az)/(bz-az)+ax)
        dx,dz=bx-ax,bz-az;t=np.clip(((X-ax)*dx+(Z-az)*dz)/(dx*dx+dz*dz),0,1)
        distance=np.minimum(distance,np.hypot(X-ax-t*dx,Z-az-t*dz))
    return 1-ss(-.07,.16,np.where(inside,-distance,distance)+edge)
grill_court=[(13.05,22.0),(13.8,21.5),(14.75,21.8),(14.8,26.3),(13.65,26.55),(12.95,25.0),(12.9,23.3)]
clinic_court=[(21.3,27.6),(22.9,27.7),(23.2,28.4),(22.85,29.5),(21.7,29.4)]
for points in (grill_court,clinic_court):pathweight=np.maximum(pathweight,polygon(points))
# These are intentionally routed, supported walking surfaces. Do not erase
# flat lowland roads by absolute altitude or carve gaps across a ramp by its
# shading normal. Sand contacts use a continuous compacted sandy path instead.
land*=1-pathweight[...,None];land[...,2]+=pathweight
land=before*(1-scope[...,None])+land*scope[...,None]
land=np.clip(land,0,1);land/=np.maximum(1,land.sum(axis=2))[...,None]
land[scope==0]=before[scope==0]
assert np.array_equal(land[scope==0],before[scope==0])
assert np.isfinite(land).all()
im=save_image('G23_LandUse',land[...,:3],land[...,3],True)
for mat in bpy.data.materials:
    if not mat.use_nodes:continue
    for nd in mat.node_tree.nodes:
        if nd.type=='TEX_IMAGE' and nd.name=='G23_LandUse':nd.image=im
np.savez_compressed(str(LOG/'land_data.npz'),land=land,height=height,normal=normal,scope=scope)
report={'roles':'grass rock path soil; residual sand','bounds_xz':[-4,-15,44,82],
 'base':'immutable G23 final land_data.npz','routes':routes,'grill_forecourt':grill_court,
 'scope':'three reviewed blue-box road contacts; outside weights unchanged',
 'absolute_height_clipping':False,'global_slope_clipping':False,
 'outside_scope_max_delta':float(np.max(np.abs(land[scope==0]-before[scope==0]))),
 'changed_pixels':int(np.any(abs(land-before)>1e-5,axis=-1).sum()),'visual_accepted':False}
(LOG/'occupancy.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='routes'}))
