"""Assign surfaces to the graded physical ground, inside GUI Blender MCP."""
import bpy,json,sys,numpy as np,struct,zlib
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/terrain_structure_20261123';OUT=ROOT/'assets/reference'
assert not bpy.app.background
sys.path.insert(0,str(ROOT/'source'))
import importlib,structure23_common as util;importlib.reload(util)
spec=json.loads((LOG/'design.json').read_text(encoding='utf8'))
ob=bpy.data.objects['C25_ContourBuiltCoast'];mesh=ob.data;assert ob.get('structure23_grade')
n=2048;v,u=np.mgrid[:n,:n].astype(np.float32);X=-4+48*(u+.5)/n;Z=-15+97*(v+.5)/n
p=np.array([v.co[:] for v in mesh.vertices],np.float32);mesh.calc_loop_triangles()
height=np.full((n,n),-100,np.float32);normal=np.ones((n,n),np.float32)
for face in mesh.loop_triangles:
    pp=p[list(face.vertices)];px=(pp[:,0]+4)/48*n-.5;py=(-pp[:,1]+15)/97*n-.5
    x0=max(0,int(np.ceil(px.min())));x1=min(n-1,int(np.floor(px.max())));y0=max(0,int(np.ceil(py.min())));y1=min(n-1,int(np.floor(py.max())))
    if x1<x0 or y1<y0:continue
    den=(py[1]-py[2])*(px[0]-px[2])+(px[2]-px[1])*(py[0]-py[2])
    if abs(den)<1e-12:continue
    yy,xx=np.mgrid[y0:y1+1,x0:x1+1].astype(np.float32)
    a=((py[1]-py[2])*(xx-px[2])+(px[2]-px[1])*(yy-py[2]))/den
    b=((py[2]-py[0])*(xx-px[2])+(px[0]-px[2])*(yy-py[2]))/den;c=1-a-b
    hh=a*pp[0,2]+b*pp[1,2]+c*pp[2,2];dest=height[y0:y1+1,x0:x1+1]
    hit=(a>=-1e-5)&(b>=-1e-5)&(c>=-1e-5)&(hh>=dest)
    dest[hit]=hh[hit];nn=np.cross(pp[1]-pp[0],pp[2]-pp[0]);nn/=np.linalg.norm(nn)
    normal[y0:y1+1,x0:x1+1][hit]=abs(nn[2])
assert height.min()>-99
target,influence,path=util.design_field(X,Z,spec)
# A small averaging radius only softens material contact. Retain the exact
# triangle normal array for road auditing; no road is admitted by this filter.
nn=normal.copy()
for _ in range(14):nn=(nn*4+np.roll(nn,1,0)+np.roll(nn,-1,0)+np.roll(nn,1,1)+np.roll(nn,-1,1))/8
steep=1-util.ss(.53,.76,nn)
rock=steep*util.ss(.95,1.85,height)
soil=(1-util.ss(.48,.68,nn))*(1-rock)
# The shore sand edge is the actual foot of the broad lowered shore, not
# independent Gaussian bays or rectangular material cutouts.
edge=.018*np.sin(X*7.1+Z*4.2)+.013*np.cos(X*10.3-Z*8.8)
sand=1-util.ss(.34,.52,height+edge)
grass=np.clip(1-rock-soil,0,1)
import structure23_surface_contacts as contacts;importlib.reload(contacts)
grass,rock,soil,contact_report=contacts.clean_cliff_grass(grass,rock,soil,height,nn)
land=np.stack([grass,rock,np.zeros_like(X),soil],axis=2)*(1-sand[...,None])
# Only explicitly authored shore access routes dissipate into beach sand.
# Interior low routes remain paths; absolute elevation never clips them.
for r in spec['routes']:
    if r.get('beach_end'):
        end=np.array(r['points'][-1]);previous=np.array(r['points'][-2]);direction=end[:2]-previous[:2];direction/=np.linalg.norm(direction)
        # Fade through the final cross-section and out onto the beach. A
        # radial hole at the endpoint leaves a conspicuous painted doughnut.
        progress=(X-end[0])*direction[0]+(Z-end[1])*direction[1]
        d,_=util.route_profile(X,Z,r['points'][-2:]);local=1-util.ss(r['halfwidth']+.2,r['halfwidth']+.55,d)
        path*=1-local*util.ss(-.85,.10,progress)
land*=1-path[...,None];land[...,2]+=path
old=np.load(ROOT/'captures/road_contacts_20261123/land_data.npz')['land']
scope=util.ss(-2,0,Z)*(1-util.ss(65,68,Z))*util.ss(7.8,9.5,X)*(1-util.ss(34,37,X))
land=old*(1-scope[...,None])+land*scope[...,None]
land=np.clip(land,0,1).astype(np.float32);land/=np.maximum(1,land.sum(2))[...,None]
def chunk(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
data=np.round(land[::-1]*255).astype(np.uint8);raw=b''.join(b'\0'+r.tobytes() for r in data)
pathfile=OUT/'G23_LandUse.png'
pathfile.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',n,n,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b''))
image=bpy.data.images.get('G23_LandUse')
if image:bpy.data.images.remove(image)
image=bpy.data.images.load(str(pathfile));image.name='G23_LandUse';image.pack()
image.colorspace_settings.name='Non-Color';image.alpha_mode='CHANNEL_PACKED'
mesh.materials[0].node_tree.nodes['G23_LandUse'].image=image
# Also keep source vertex roles consistent; the runtime atlas has higher
# resolution but never overlays an unrelated historical geometry role map.
idx=np.array([l.vertex_index for l in mesh.loops],np.int32)
ix=np.clip(((p[idx,0]+4)/48*n).astype(int),0,n-1);iy=np.clip(((-p[idx,1]+15)/97*n).astype(int),0,n-1)
mesh.color_attributes['LandUse'].data.foreach_set('color',land[iy,ix].ravel())
np.savez_compressed(LOG/'land_data.npz',land=land,height=height,normal=normal,scope=scope,desired_path=path)
ob['structure23_land']=True
report={'routes':len(spec['routes']),'platforms':len(spec['platforms']),'map_size':n,'geometry_driven_shore_and_slope':True,'path_elevation_clipping':False,'source_image_packed':bool(image.packed_file),'cliff_contacts':contact_report,'visual_accepted':False}
(LOG/'land.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
