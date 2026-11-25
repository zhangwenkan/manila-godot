"""Repaint only the new physical rock masses and their crown/toe contacts in MCP."""
import bpy,os,json,sys,numpy as np,struct,zlib,importlib
from pathlib import Path
assert os.getpid()==9864 and not bpy.app.background and bpy.types.blendermcp_server.port==9881
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/cliff_contacts_20261125';OUT=ROOT/'assets/reference'
sys.path.insert(0,str(ROOT/'source'))
from structure23_common import ss,polygon_distance,route_profile
import cliff25_geometry_common as geometry
importlib.reload(geometry)
spec=json.loads((LOG/'design.json').read_text(encoding='utf8'))
terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
old=np.load(ROOT/'captures/terrain_structure_20261123/land_data.npz')
land=old['land'].copy();n=land.shape[0]
v,u=np.mgrid[:n,:n].astype(np.float32);X=-4+48*(u+.5)/n;Z=-15+97*(v+.5)/n
p=np.array([v.co[:] for v in mesh.vertices],np.float32);mesh.calc_loop_triangles()
height=old['height'].copy();normal=old['normal'].copy()
# Rasterize the actual edited faces, retaining all old values outside the area.
for face in mesh.loop_triangles:
    pp=p[list(face.vertices)]
    if pp[:,0].max()<15 or pp[:,0].min()>27 or (-pp[:,1]).max()<21 or (-pp[:,1]).min()>46:continue
    px=(pp[:,0]+4)/48*n-.5;py=(-pp[:,1]+15)/97*n-.5
    x0=max(0,int(np.ceil(px.min())));x1=min(n-1,int(np.floor(px.max())));y0=max(0,int(np.ceil(py.min())));y1=min(n-1,int(np.floor(py.max())))
    if x1<x0 or y1<y0:continue
    den=(py[1]-py[2])*(px[0]-px[2])+(px[2]-px[1])*(py[0]-py[2])
    if abs(den)<1e-12:continue
    yy,xx=np.mgrid[y0:y1+1,x0:x1+1].astype(np.float32)
    a=((py[1]-py[2])*(xx-px[2])+(px[2]-px[1])*(yy-py[2]))/den
    b=((py[2]-py[0])*(xx-px[2])+(px[0]-px[2])*(yy-py[2]))/den;c=1-a-b
    hit=(a>=-1e-5)&(b>=-1e-5)&(c>=-1e-5)
    hh=a*pp[0,2]+b*pp[1,2]+c*pp[2,2]
    height[y0:y1+1,x0:x1+1][hit]=hh[hit]
    nn=np.cross(pp[1]-pp[0],pp[2]-pp[0]);nn/=np.linalg.norm(nn)
    normal[y0:y1+1,x0:x1+1][hit]=abs(nn[2])
scope=np.zeros_like(X)
# Protect full usable route/court footprints as well as their existing worn
# pixels. The fixed geometric roadbed must not acquire new rock/soil paint.
road_lock=old['land'][...,2]>.018
for route in spec['routes']:
    points=np.array(route['points']);pad=route['halfwidth']+route.get('bench_margin',.28)+.12
    box=(X>points[:,0].min()-pad)&(X<points[:,0].max()+pad)&(Z>points[:,1].min()-pad)&(Z<points[:,1].max()+pad)
    d,_=route_profile(X[box],Z[box],route['points'])
    road_lock[box]|=d<=route['halfwidth']+route.get('bench_margin',.28)
for court in spec['platforms']:
    points=np.array(court['polygon']);pad=.18
    box=(X>points[:,0].min()-pad)&(X<points[:,0].max()+pad)&(Z>points[:,1].min()-pad)&(Z<points[:,1].max()+pad)
    road_lock[box]|=polygon_distance(X[box],Z[box],court['polygon'])<=.12
soil_regions=[
    {'name':'clinic_north_toe_pocket','polygon':[(17.25,28.15),(17.76,27.95),(18.50,28.15),(18.40,28.70),(17.65,29.15),(17.12,28.90)],'h_above_toe':.42,'strength':.76},
    {'name':'clinic_south_apron_wedge','polygon':[(17.15,29.55),(17.92,29.65),(18.55,30.60),(18.80,31.10),(18.18,30.85),(17.70,30.30)],'h_above_toe':.32,'strength':.70},
    {'name':'tavern_south_recess','polygon':[(17.15,42.90),(17.52,42.55),(18.08,43.10),(18.60,44.05),(17.90,44.18),(17.30,43.60)],'h_above_toe':.37,'strength':.68},
]
region_reports=[]
for group in geometry.MASSES:
    rows=group['sections'];stations=np.array([s[0] for s in rows])
    start,end=group['z_range'];zf0,zf1=group['z_fade']
    mask=(X>15.5)&(X<23.2)&(Z>start)&(Z<end)
    xx,zz=X[mask],Z[mask];hh,nn=height[mask],normal[mask]
    j=np.clip(np.searchsorted(stations,zz,side='right')-1,0,len(rows)-2)
    t=ss(0.,1.,(zz-stations[j])/(stations[j+1]-stations[j]))
    toe=np.zeros_like(xx);crown=toe.copy();low=toe.copy();high=toe.copy()
    for k in range(len(rows)-1):
        take=j==k;a,b=rows[k][1],rows[k+1][1]
        toe[take]=(1-t[take])*a[0][0]+t[take]*b[0][0]
        crown[take]=(1-t[take])*a[-1][0]+t[take]*b[-1][0]
        low[take]=(1-t[take])*a[0][1]+t[take]*b[0][1]
        high[take]=(1-t[take])*a[-1][1]+t[take]*b[-1][1]
    cross=np.clip((xx-toe)/np.maximum(crown-toe,.05),0,1)
    zone=ss(start,start+zf0,zz)*(1-ss(end-zf1,end,zz))
    zone*=ss(toe-.24,toe+.12,xx)*(1-ss(crown+.12,crown+.43,xx))
    # Grass belongs only on the actual crown/low bank. A mid-face shelf never
    # becomes a vertical green tongue merely because it is locally level.
    # A 2cm coarse irregularity avoids a mechanically straight contact without
    # drawing long green lobes down the rock face.
    crown_variation=.018*np.sin(zz*1.21+.4)+.012*np.sin(zz*2.67)
    cap=ss(high-.10,high+.025,hh+crown_variation)*ss(.72,.91,nn)*ss(.76,.98,cross)
    exposure=ss(low+.075,low+.28,hh)*ss(.015,.12,cross)
    rock=exposure*(1-cap)
    soil=np.zeros_like(xx)
    for pocket in soil_regions:
        d=polygon_distance(xx,zz,pocket['polygon'])
        shape=1-ss(-.08,.19,d)
        # The patch has a bounded irregular plan shape; height merely limits
        # it near the foot, and can never create a continuous low orange band.
        pocket_top=low+pocket['h_above_toe']+.045*np.sin(zz*2.3+xx)
        patch=shape*(1-ss(pocket_top-.10,pocket_top+.16,hh))*pocket['strength']
        patch*=ss(low-.04,low+.07,hh)*(1-cap)
        soil=np.maximum(soil,patch)
    rock*=1-soil
    grass=np.clip(1-rock-soil,0,1)
    target=np.stack((grass,rock,np.zeros_like(xx),soil),axis=1)
    zone[road_lock[mask]]=0
    original_region=land[mask]
    land[mask]=original_region*(1-zone[:,None])+target*zone[:,None]
    scope[mask]=np.maximum(scope[mask],zone)
    region_reports.append({'name':group['name'],'scope_pixels':int((zone>.01).sum()),
                           'soil_pixels_over_half':int(((soil>.5)&(zone>.5)).sum()),
                           'contact_mapping':'current cliff25_geometry_common eased section endpoints'})
land[road_lock]=old['land'][road_lock]
land=np.clip(land,0,1).astype(np.float32);land/=np.maximum(land.sum(2),1)[...,None]
def chunk(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
raw=b''.join(b'\0'+row.tobytes() for row in np.uint8(land[::-1]*255+.5))
path=OUT/'G23_LandUse.png';path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',n,n,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b''))
im=bpy.data.images.get('G23_LandUse')
if im:bpy.data.images.remove(im)
im=bpy.data.images.load(str(path));im.name='G23_LandUse';im.colorspace_settings.name='Non-Color';im.alpha_mode='CHANNEL_PACKED';im.pack()
mesh.materials[0].node_tree.nodes['G23_LandUse'].image=im
idx=np.array([l.vertex_index for l in mesh.loops],np.int32)
ix=np.clip(((p[idx,0]+4)/48*n).astype(int),0,n-1);iy=np.clip(((-p[idx,1]+15)/97*n).astype(int),0,n-1)
mesh.color_attributes['LandUse'].data.foreach_set('color',land[iy,ix].ravel())
np.savez_compressed(LOG/'land_data.npz',land=land,height=height,normal=normal,scope=scope,desired_path=old['desired_path'])
report={'iteration':2,'changed_pixels':int(np.any(abs(land-old['land'])>1e-6,axis=2).sum()),'road_role_max_error':float(np.max(abs(land[road_lock]-old['land'][road_lock]))),'protected_road_court_pixels':int(road_lock.sum()),'explicit_crown_toe_contacts':True,'continuous_toe_soil_band':False,'soil_pockets':soil_regions,'regions':region_reports,'visual_accepted':False}
(LOG/'contacts.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
