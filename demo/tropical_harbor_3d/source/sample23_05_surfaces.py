# Generate authored sample textures inside the verified live Blender MCP only.
import bpy,json,math,zlib,struct,numpy as np
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/rock_path_sample_20261123';OUT=ROOT/'assets/reference'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
assert terrain.get('sample23_paths')
def ss(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def png(name,rgba,linear=False,bits=8):
 # Arrays are authored bottom-to-top in UV coordinates. PNG rows are top-to-bottom.
 rgba=np.clip(rgba,0,1);h,w=rgba.shape[:2]
 data=np.round(rgba*(65535 if bits==16 else 255)).astype('>u2' if bits==16 else np.uint8)[::-1]
 def chunk(tag,d):return struct.pack('>I',len(d))+tag+d+struct.pack('>I',zlib.crc32(tag+d)&0xffffffff)
 raw=b''.join(b'\0'+row.tobytes() for row in data)
 content=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,bits,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b'')
 path=OUT/(name+'.png');path.write_bytes(content)
 old=bpy.data.images.get(name)
 if old:bpy.data.images.remove(old)
 image=bpy.data.images.load(str(path),check_existing=False);image.name=name
 image.colorspace_settings.name='Non-Color' if linear else 'sRGB'
 image.alpha_mode='CHANNEL_PACKED' if linear else 'STRAIGHT';image.pack()
 return image
# Long nonrepeating elevation strip: each layer bends and ends with its own layout.
w,h=4096,768;vv,uu=np.mgrid[0:h,0:w].astype(np.float32)
z=10+37*(uu+.5)/w;e=.7+4.4*(vv+.5)/h
large=.013*np.sin(z*.47+e*.8)+.009*np.sin(z*1.29-e*2.1)+.004*np.sin(z*3.7+e*7.3)
rgb=np.empty((h,w,3),np.float32);rgb[:]=[.445,.469,.466]
rgb+=large[:,:,None]
height=np.full((h,w),.5,np.float32)
layers=[
 ([10,15,19,23,27,31,35,39,43,47],[1.05,1.08,1.17,1.0,1.19,1.05,1.1,1.05,1.12,1.22],.018),
 ([10,13,17,21,24,27,30,33,37,40,43,47],[1.68,1.57,1.72,1.64,1.80,1.68,1.82,1.73,1.59,1.81,1.69,1.85],-.006),
 ([10,14,18,22,25,28,32,35,38,41,44,47],[2.43,2.29,2.36,2.57,2.41,2.57,2.49,2.37,2.55,2.47,2.59,2.45],.025),
 ([10,13,17,20,24,28,31,34,38,42,45,47],[3.21,3.08,3.30,3.15,3.29,3.13,3.43,3.20,3.12,3.26,3.11,3.23],-.012),
 ([10,14,18,21,25,29,32,36,39,43,47],[3.91,4.02,3.84,4.07,3.97,4.11,3.94,4.07,3.89,4.04,3.95],.014)]
for j,(zs,hs,tint) in enumerate(layers):
 line=np.interp(z,zs,hs)+.013*np.sin(z*(1.7+j*.29)+j)
 d=e-line
 # Broad shelf and subtle bevel above, recessed narrow undercut below.
 seam=np.exp(-(d/.032)**2)
 under=np.exp(-((d+.075)/.095)**2)
 lip=np.exp(-((d-.09)/.13)**2)
 duration=.52+.48*ss(-.45,.35,np.sin(z*.31+j*1.7))
 rgb+=(tint*ss(-.09,.22,d)-under*.033*duration+lip*.026-seam*.036*duration)[:,:,None]
 height+=(-seam*.105*duration-under*.09+lip*.12)
# Individual short joints stop inside strata; no wall-spanning vertical grid.
joints=[(13.7,1.13,1.64,.15),(17.8,2.4,3.13,-.22),(22.9,1.78,2.49,.16),(25.8,2.55,3.25,-.18),(28.4,1.19,1.73,.11),(30.2,3.4,4.02,.19),(36.8,1.1,1.64,-.16),(39.1,2.50,3.19,.19),(42.6,1.75,2.58,-.18),(44.8,3.15,4.01,.14)]
for k,(zz,lo,hi,slant) in enumerate(joints):
 axis=zz+slant*(e-lo)+.012*np.sin(e*9+k)
 d=z-axis;fade=ss(lo,lo+.12,e)*(1-ss(hi-.12,hi,e))
 seam=np.exp(-(d/.029)**2)*fade
 crease=np.exp(-(d/.12)**2)*fade
 rgb-= (seam*.041+crease*.014)[:,:,None]
 height-=seam*.08+crease*.035
grain=.0025*np.sin(z*59+e*83)*np.sin(z*31-e*67)
rgb+=grain[:,:,None];height+=grain*.8
rgba=np.ones((h,w,4),np.float32);rgba[:,:,:3]=rgb
rock=png('S23_Rock_Albedo',rgba)
rgba[:,:,:3]=height[:,:,None];rockh=png('S23_Rock_Height',rgba,True,16)
# Restrained compacted earth with broad wear, not a uniform bright yellow paint.
n=1024;v,u=np.mgrid[0:n,0:n].astype(np.float32)/n
broad=.016*np.sin(math.tau*(u*2+v))+.010*np.cos(math.tau*(v*3-u))
fine=.004*np.sin(math.tau*(u*37+v*11))*.5+.003*np.sin(math.tau*(u*83-v*71))
rgb=np.empty((n,n,3),np.float32);rgb[:]=[.575,.507,.389]
rgb+=(broad+fine)[:,:,None]
wear=np.exp(-((u-.52)/.20)**2)*(.5+.5*np.sin(math.tau*v))
rgb+=wear[:,:,None]*np.array([.016,.014,.011])
rgba=np.ones((n,n,4),np.float32);rgba[:,:,:3]=rgb
pathimage=png('S23_Path_Albedo',rgba)
# Rasterize actual shared surface and stored land roles into the regional map.
n=1536;v,u=np.mgrid[0:n,0:n].astype(np.float32)
X=8+26*(u+.5)/n;Z=10+37*(v+.5)/n
land=np.zeros((n,n,4),np.float32);heightfield=np.full((n,n),-100,np.float32);nz=np.ones((n,n),np.float32)
coords=np.array([v.co[:] for v in mesh.vertices],np.float32)
attrs=np.array([c.color[:] for c in mesh.color_attributes['LandUse'].data],np.float32)
mesh.calc_loop_triangles()
for tri in mesh.loop_triangles:
 p=coords[list(tri.vertices)];px=(p[:,0]-8)/26*n-.5;py=(-p[:,1]-10)/37*n-.5
 x0=max(0,int(np.ceil(px.min())));x1=min(n-1,int(np.floor(px.max())))
 y0=max(0,int(np.ceil(py.min())));y1=min(n-1,int(np.floor(py.max())))
 if x1<x0 or y1<y0:continue
 den=(py[1]-py[2])*(px[0]-px[2])+(px[2]-px[1])*(py[0]-py[2])
 if abs(den)<1e-12:continue
 yy,xx=np.mgrid[y0:y1+1,x0:x1+1].astype(np.float32)
 a=((py[1]-py[2])*(xx-px[2])+(px[2]-px[1])*(yy-py[2]))/den
 b=((py[2]-py[0])*(xx-px[2])+(px[0]-px[2])*(yy-py[2]))/den;c=1-a-b
 inside=(a>=-1e-5)&(b>=-1e-5)&(c>=-1e-5)
 heights=a*p[0,2]+b*p[1,2]+c*p[2,2];desth=heightfield[y0:y1+1,x0:x1+1]
 valid=inside&(heights>=desth)
 if not valid.any():continue
 cl=attrs[list(tri.loops)]
 sample=a[:,:,None]*cl[0]+b[:,:,None]*cl[1]+c[:,:,None]*cl[2]
 land[y0:y1+1,x0:x1+1][valid]=sample[valid];desth[valid]=heights[valid]
 nz[y0:y1+1,x0:x1+1][valid]=tri.normal.z
assert np.min(heightfield)>-90,'Uncovered regional map'
# Remove diffuse former yellow pads; explicitly paint purposeful path occupancy.
land[:,:,0]+=land[:,:,2];land[:,:,2]=0
rockweight=ss(.12,.58,land[:,:,1])
rockweight*=1-ss(.78,.95,nz)
land[:,:,0]=np.maximum(land[:,:,0]+land[:,:,1]-rockweight,0);land[:,:,1]=rockweight
soil=ss(.16,.67,land[:,:,3]);land[:,:,0]+=np.maximum(land[:,:,3]-soil,0);land[:,:,3]=soil
routes=json.loads((LOG/'routes.json').read_text())
pathweight=np.zeros((n,n),np.float32)
for r in routes:
 dist=np.full((n,n),100,np.float32)
 for a,b in zip(r['points'],r['points'][1:]):
  dx,dz=b[0]-a[0],b[1]-a[1];t=np.clip(((X-a[0])*dx+(Z-a[1])*dz)/(dx*dx+dz*dz),0,1)
  dist=np.minimum(dist,np.hypot(X-a[0]-dx*t,Z-a[1]-dz*t))
 edge=.035*np.sin(X*3.7+Z*2.2)+.022*np.sin(X*6.3-Z*4.5)
 rw=1-ss(r['halfwidth']-.045+edge,r['halfwidth']+.10+edge,dist)
 pathweight=np.maximum(pathweight,rw)
for x,z,rx,rz in [(13.25,23.9,1.25,1.45),(14.6,32,1.18,1.0),(22.25,28.5,.83,1.13),(22.3,14.8,.85,1.0),(10.45,37.6,.9,.9)]:
 d=np.sqrt(((X-x)/rx)**2+((Z-z)/rz)**2)
 pathweight=np.maximum(pathweight,1-ss(.93,1.05,d))
pathweight*=ss(.55,.82,nz)*ss(.30,.65,heightfield)
land*=1-pathweight[:,:,None];land[:,:,2]=pathweight
land=np.clip(land,0,1)
total=land.sum(axis=2);land/=np.maximum(total,1)[:,:,None]
landimage=png('S23_LandUse',land,True)
np.savez_compressed(str(LOG/'regional_surface_data.npz'),land=land,height=heightfield,normal_z=nz)
# Source material records actual mapping and image roles. Godot applies runtime blend.
mat=mesh.materials[0];nodes=mat.node_tree.nodes
for name,img,uvname in [('S23 regional land roles',landimage,'UVMap'),('S23 regional rock albedo',rock,'RockRegion'),('S23 regional rock height',rockh,'RockRegion'),('S23 compacted path',pathimage,'UVMap')]:
 node=nodes.get(name) or nodes.new('ShaderNodeTexImage');node.name=name;node.label=name;node.image=img
 uvnode=nodes.new('ShaderNodeUVMap');uvnode.uv_map=uvname;mat.node_tree.links.new(uvnode.outputs['UV'],node.inputs['Vector'])
terrain['sample23_surfaces']=True
(LOG/'surfaces.json').write_text(json.dumps({'rock_size':[w,h],'land_size':[n,n],'path_size':[1024,1024],'rock_uv':'z and elevation, 37m by4.4m','land_uv':'x8..34,z10..47','generated_via':'live Blender MCP','road_routes':len(routes),'original_game_assets_imported':False},indent=2),encoding='utf8')
print('Generated S23 regional rock layers, height, land roles and compacted path in live Blender')
