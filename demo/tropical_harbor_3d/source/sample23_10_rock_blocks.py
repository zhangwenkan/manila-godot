# Regional broad broken faces. Live Blender MCP only; reusable texture operation.
import bpy,json,math,numpy as np,struct,zlib
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/rock_path_sample_20261123';OUT=ROOT/'assets/reference'
src=(ROOT/'source/sample23_05_surfaces.py').read_text(encoding='utf8')
exec(src[src.index('def ss('):src.index('# Long nonrepeating')],globals())
w,h=4096,768;vv,uu=np.mgrid[0:h,0:w].astype(np.float32)
z=10+45*(uu+.5)/w;e=.7+4.4*(vv+.5)/h
rgb=np.empty((h,w,3),np.float32);rgb[:]=[.305,.344,.350]
height=np.full((h,w),.285,np.float32)
def level(row,x):
 base=[.35,1.42,2.29,3.36,4.27,5.55][row]
 return base+.13*np.sin(x*.83+row*1.2)+.075*np.sin(x*1.77+row*.9)
def chamfer(poly):
 result=[]
 for i,p in enumerate(poly):
  a=np.array(poly[i-1]);b=np.array(p);c=np.array(poly[(i+1)%len(poly)])
  result.append(tuple(b+(a-b)*min(.11,.075/max(np.linalg.norm(a-b),.01))))
  result.append(tuple(b+(c-b)*min(.11,.075/max(np.linalg.norm(c-b),.01))))
 return result
def face(poly,tint,tilt):
 x0=max(0,int((min(p[0] for p in poly)-10)/45*w)-2);x1=min(w,int((max(p[0] for p in poly)-10)/45*w)+3)
 y0=max(0,int((min(p[1] for p in poly)-.7)/4.4*h)-2);y1=min(h,int((max(p[1] for p in poly)-.7)/4.4*h)+3)
 if x1<=x0 or y1<=y0:return
 X=z[y0:y1,x0:x1];Y=e[y0:y1,x0:x1];inside=np.zeros(X.shape,bool);dist=np.full(X.shape,100,np.float32)
 for (a,b),(c,d) in zip(poly,poly[1:]+poly[:1]):
  if abs(d-b)>1e-9:inside^=((b>Y)!=(d>Y))&(X<(c-a)*(Y-b)/(d-b)+a)
  dx,dy=c-a,d-b;q=np.clip(((X-a)*dx+(Y-b)*dy)/(dx*dx+dy*dy),0,1)
  dist=np.minimum(dist,np.hypot(X-a-q*dx,Y-b-q*dy))
 weight=ss(0,.045,dist)*inside;bevel=ss(.025,.20,dist)
 cx=sum(p[0] for p in poly)/len(poly);cy=sum(p[1] for p in poly)/len(poly)
 plane=np.clip((Y-cy)*.045+(X-cx)*tilt,-.035,.04)
 edge_dark=(1-bevel)*.027
 color=np.array([.345+tint,.382+tint*.90,.387+tint*.84])+plane[:,:,None]-edge_dark[:,:,None]
 # Small slanted chips only within broad face edges; quiet central planes remain.
 grain=.002*np.sin(X*37+Y*51)*np.cos(X*13-Y*29)
 color+=grain[:,:,None]
 dest=rgb[y0:y1,x0:x1];dest[:]=dest*(1-weight[:,:,None])+color*weight[:,:,None]
 hf=.29+.22*bevel+plane*1.2
 height[y0:y1,x0:x1]=height[y0:y1,x0:x1]*(1-weight)+hf*weight
rows=[
 [8,11.8,14.2,17.5,20.8,23.0,26.6,28.7,32.4,35.2,38.8,41.0,44.2,47.1,50.8,53.2,57],
 [8,10.9,14.8,18.1,21.3,24.9,27.1,30.8,33.2,36.5,39.1,42.8,45.0,48.5,52.1,57],
 [8,12.7,16.3,19.4,22.8,25.6,29.2,32.0,35.9,39.8,43.0,46.4,49.5,53.8,57],
 [8,11.4,14.9,18.8,22.0,25.0,28.9,31.3,34.7,38.3,41.5,45.2,48.9,52.7,57],
 [8,12.1,15.8,19.2,23.5,27.0,30.4,34.5,37.4,40.8,44.7,48.1,51.7,57]]
for row,cuts in enumerate(rows):
 for j,(a,b) in enumerate(zip(cuts,cuts[1:])):
  skew=.12*math.sin(j*1.7+row);mid=a+(b-a)*.53
  poly=[(a,level(row,a)),(mid,level(row,mid)),(b,level(row,b)),(b+skew,level(row+1,b)),(mid+.13,level(row+1,mid)),(a+skew,level(row+1,a))]
  face(chamfer(poly),.024*math.sin(j*2.3+row*1.1),.009*math.sin(j*1.5-row))
# Tall sloping planes intentionally erase some complete horizontal boundaries.
for poly,tint,tilt in [
 ([(22.6,1.65),(24.1,1.70),(24.8,2.12),(24.5,3.23),(23.5,3.45),(22.4,2.83)],-.015,.012),
 ([(27.0,1.36),(28.5,1.53),(29.1,2.35),(28.7,2.84),(27.4,2.99),(26.9,2.18)],.018,-.012),
 ([(37.3,2.24),(38.3,1.98),(39.3,2.38),(39.6,3.54),(38.5,3.76),(37.1,3.17)],-.019,.014),
 ([(42.5,1.33),(44.2,1.28),(45.2,1.78),(45.4,2.61),(44.0,3.00),(42.8,2.61)],.008,-.013),
 ([(48.4,2.16),(49.8,1.91),(51.1,2.34),(51.3,3.46),(50.0,3.65),(48.8,3.11)],-.018,.013)]:
 face(chamfer(poly),tint,tilt)
rgba=np.ones((h,w,4),np.float32);rgba[:,:,:3]=rgb;rock=png('S23_Rock_Albedo',rgba)
rgba[:,:,:3]=height[:,:,None];rockh=png('S23_Rock_Height',rgba,True,16)
# Minimal standard single-channel float EXR. Authored here from unquantized data.
def attr(name,kind,data):return name.encode()+b'\0'+kind.encode()+b'\0'+struct.pack('<I',len(data))+data
channels=b'R\0'+struct.pack('<iB3xii',2,0,1,1)+b'\0'
header=struct.pack('<II',20000630,2)+attr('channels','chlist',channels)+attr('compression','compression',b'\0')
box=struct.pack('<iiii',0,0,w-1,h-1)
header+=attr('dataWindow','box2i',box)+attr('displayWindow','box2i',box)+attr('lineOrder','lineOrder',b'\0')+attr('pixelAspectRatio','float',struct.pack('<f',1))+attr('screenWindowCenter','v2f',struct.pack('<ff',0,0))+attr('screenWindowWidth','float',struct.pack('<f',1))+b'\0'
offset=len(header)+8*h;chunkbytes=8+4*w
with (OUT/'S23_Rock_Height.exr').open('wb') as f:
 f.write(header);f.write(b''.join(struct.pack('<Q',offset+i*chunkbytes) for i in range(h)))
 for i,row in enumerate(height[::-1]):f.write(struct.pack('<ii',i,w*4));f.write(row.astype('<f4').tobytes())
mat=bpy.data.objects['C25_ContourBuiltCoast'].data.materials[0]
mat.node_tree.nodes['S23 regional rock albedo'].image=rock
mat.node_tree.nodes['S23 regional rock height'].image=rockh
np.savez_compressed(str(LOG/'rock_height_float.npz'),height=height)
(LOG/'rock_blocks.json').write_text(json.dumps({'layout':'five uneven levels, staggered broad panels and five tall sloping interruptions','pixels':[w,h],'height_source':'float32 live Blender EXR, nonrepeat region','range':[float(height.min()),float(height.max())]},indent=2),encoding='utf8')
print('Authored broad staggered rock faces and float32 EXR height inside Blender')
