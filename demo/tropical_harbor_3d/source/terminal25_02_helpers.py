import bpy,os,math,json,random,numpy as np,bmesh
from pathlib import Path
from mathutils import Vector,Matrix
assert os.getpid()==13812 and not bpy.app.background and bpy.types.blendermcp_server.port==9881
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/terminal_rebuild_20261125'
assert (LOG/'before_manifest.json').exists()
assert bpy.data.collections.get('Reference_Terminal') is None,'Do not replay construction'
C=bpy.data.collections.new('Reference_Terminal');bpy.context.scene.collection.children.link(C)
P={r:bpy.data.materials['Ref_TR20_'+r] for r in ['wood','deck','beam','stone','ivory','plaster','red']}
P.update({r:bpy.data.materials[n] for r,n in {'iron':'Ref_D19_ForgedIron','rope':'Ref_Rope','glass':'Ref_Glass','brass':'Ref_D19_AgedBrass','canvas':'Ref_Town_canvas','leaf':'Ref_D19_Foliage1','brick':'Ref_D19_TR20_Brick','reveal':'Ref_TR20_beam'}.items()})
# Independent current-town blue copy; no old terminal material is read.
roof=bpy.data.materials['Ref_TR20_blue'].copy();roof.name='Ref_TN25_NavyRoof'
node=roof.node_tree.nodes.get('Principled BSDF');link=node.inputs['Base Color'].links[0];src=link.from_node.image
w,h=src.size;pixels=np.empty(w*h*4,np.float32);src.pixels.foreach_get(pixels);pixels=pixels.reshape(h,w,4)
def lin(hx):
 c=np.array([int(hx[i:i+2],16)/255 for i in (0,2,4)]);return np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
pixels[:,:,:3]*=(lin('3d6275')/lin('557b88'))[None,None,:]
im=bpy.data.images.new('TN25_NavyRoof_Color',width=w,height=h,alpha=True);im.colorspace_settings.name='sRGB';im.pixels.foreach_set(pixels.ravel())
im.filepath_raw=str(ROOT/'assets/reference/TN25_NavyRoof_Color.png');im.file_format='PNG';im.save();im.pack();link.from_node.image=im;P['roof']=roof
root=bpy.data.objects.new('TN25_Assembly',None);C.objects.link(root);root['reference_asset']='terminal'
def mesh(name,verts,faces,role):
 data=bpy.data.meshes.new('TN25_'+name);data.from_pydata(verts,[],faces);data.update()
 bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
 o=bpy.data.objects.new('TN25_'+name,data);C.objects.link(o);data.materials.append(P[role] if isinstance(role,str) else role)
 o['terminal25_part']=name;o.parent=root
 uv=data.uv_layers.new(name='UVMap')
 for poly in data.polygons:
  axis=max(range(3),key=lambda i:abs(poly.normal[i]));axes=[i for i in range(3) if i!=axis]
  for li in poly.loop_indices:
   co=data.vertices[data.loops[li].vertex_index].co;uv.data[li].uv=(co[axes[0]]*.6,co[axes[1]]*.6)
 return o
def B(name,center,size,role,bevel=.012):
 sx,sy,sz=[v/2 for v in size]
 vs=[(x,y,z) for x,y,z in [(-sx,-sy,-sz),(sx,-sy,-sz),(sx,sy,-sz),(-sx,sy,-sz),(-sx,-sy,sz),(sx,-sy,sz),(sx,sy,sz),(-sx,sy,sz)]]
 o=mesh(name,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],role);o.location=center
 if role in ('wood','deck','beam'):
  long=max(range(3),key=lambda i:size[i]);uv=o.data.uv_layers.active
  for poly in o.data.polygons:
   normalaxis=max(range(3),key=lambda i:abs(poly.normal[i]));cross=next((i for i in range(3) if i!=long and i!=normalaxis),(long+1)%3)
   for li in poly.loop_indices:
    co=o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(co[cross]*1.25,co[long]*.5)
 if bevel:
  m=o.modifiers.new('Town-scale edge','BEVEL');m.width=min(bevel,min(size)*.25);m.segments=2
  m=o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL');m.keep_sharp=True
 return o
def L(name,a,b,width,role):
 a,b=Vector(a),Vector(b);v=b-a;o=B(name,(a+b)/2,(width,width,v.length),role,min(.012,width*.12));o.rotation_euler=v.to_track_quat('Z','Y').to_euler();return o
def T(name,points,radius,role,sides=8):
 pts=[Vector(p) for p in points];vs=[];fs=[];arc=[0.0]
 for i,p in enumerate(pts):
  d=(pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized();u=d.cross(Vector((0,0,1)))
  if u.length<.01:u=d.cross(Vector((0,1,0)))
  u.normalize();v=d.cross(u).normalized()
  for j in range(sides):vs.append(p+radius*(math.cos(j*math.tau/sides)*u+math.sin(j*math.tau/sides)*v))
  if i:arc.append(arc[-1]+(p-pts[i-1]).length)
 fs.append(tuple(reversed(range(sides))))
 for i in range(len(pts)-1):
  for j in range(sides):fs.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
 fs.append(tuple((len(pts)-1)*sides+j for j in range(sides)))
 o=mesh(name,vs,fs,role);uv=o.data.uv_layers.active
 for poly in o.data.polygons:
  for li in poly.loop_indices:
   ix=o.data.loops[li].vertex_index;uv.data[li].uv=(ix%sides/sides,arc[ix//sides]*.5)
 return o
def wall(name,axis,plane,u0,u1,z0,z1,holes,role='ivory'):
 us=sorted(set([u0,u1]+[max(u0,min(u1,x)) for h in holes for x in h[:2]]));zs=sorted(set([z0,z1]+[max(z0,min(z1,x)) for h in holes for x in h[2:]]))
 vs=[];fs=[]
 for u in us:
  for z in zs:vs.append((u,plane,z) if axis==1 else (plane,u,z))
 for i in range(len(us)-1):
  for j in range(len(zs)-1):
   u=(us[i]+us[i+1])/2;z=(zs[j]+zs[j+1])/2
   if any(a<u<b and c<z<d for a,b,c,d in holes):continue
   a=i*len(zs)+j;fs.append((a,a+1,a+len(zs)+1,a+len(zs)))
 o=mesh(name,vs,fs,role);s=o.modifiers.new('Real wall thickness','SOLIDIFY');s.thickness=.19;s.offset=0
 be=o.modifiers.new('Plaster corner','BEVEL');be.width=.009;be.segments=2;return o
def window(name,x,y,z,w,h,side=0):
 before=set(C.objects)
 B(name+'Recess',(x,y+.08,z),(w+.08,.045,h+.08),'reveal',.004)
 B(name+'Glazing',(x,y+.054,z),(w,.025,h),'glass',.002)
 for s in [-1,1]:
  B(name+'Jamb',(x+s*(w+.10)/2,y-.055,z),(.105,.16,h+.22),'wood',.008)
  B(name+'Rail',(x,y-.06,z+s*(h+.10)/2),(w+.22,.18,.10),'wood',.009)
 B(name+'Sill',(x,y-.13,z-h/2-.13),(w+.31,.33,.09),'wood',.01)
 # Substantial central mullion, with a few open diagonal lattice rods.
 B(name+'Mullion',(x,y-.08,z),(.06,.065,h),'wood',.004)
 B(name+'Transom',(x,y-.08,z),(w,.065,.06),'wood',.004)
 for s in [-1,1]:
  for k in [-1,0,1]:
   a=max(-w/2,k*.32-h/2);b=min(w/2,k*.32+h/2)
   if b>a:
    L(name+'Lattice',(x+a,y-.065,z+s*(a-k*.32)),(x+b,y-.065,z+s*(b-k*.32)),.026,'wood')
 if side:
  tf=Matrix.Translation((x,y,z))@Matrix.Rotation(side*math.pi/2,4,'Z')@Matrix.Translation((-x,-y,-z))
  for o in set(C.objects)-before:o.matrix_world=tf@o.matrix_world
def roof(name,cx,cy,w,d,eave,rise,rows=6):
 def rz(t):return eave+rise*(1-t)**1.7+.08*t**5
 D=d/2;W=w/2
 for side in [-1,1]:
  # Solid curved continuous underlay.
  ts=[i/12 for i in range(13)];vs=[]
  for t in ts:
   for yy in [-D,D]:vs.append((cx+side*W*t,cy+yy,rz(t)))
  fs=[(2*i,2*i+1,2*i+3,2*i+2) for i in range(12)]
  o=mesh(name+'CurvedUnderlay',vs,fs,'beam');s=o.modifiers.new('Solid roof deck','SOLIDIFY');s.thickness=.09
  # Actual tile laps follow the roof curve; restrained material and dimensions.
  columns=max(5,round(d/.32));step=d/columns
  for row in range(rows):
   a=row/rows;b=min(1.02,(row+1.14)/rows)
   for j in range(columns):
    y0=cy-D+j*step+.006;y1=cy-D+(j+1)*step-.006;verts=[]
    for t in [a,(a+b)*.5,b]:
     tc=min(t,1);z=rz(tc)+.036+(1 if row else 0)*.004
     for f in [0,.5,1]:verts.append((cx+side*W*t,y0+(y1-y0)*f,z+.016*math.sin(f*math.pi)))
    o=mesh(name+'SlateTile',verts,[(0,1,4,3),(1,2,5,4),(3,4,7,6),(4,5,8,7)],'roof');s=o.modifiers.new('Tile edge thickness','SOLIDIFY');s.thickness=.025
  for fy in [cy-D-.025,cy+D+.025]:
   pts=[(cx+side*W*t,fy,rz(t)+.055) for t in ts];T(name+'CurvedBargeboard',pts,.095,'wood',4)
  B(name+'EaveFascia',(cx+side*W,cy,eave+.015),(.13,d+.12,.18),'wood',.012)
 T(name+'RidgeCap',[(cx,cy-D-.10,eave+rise+.065),(cx,cy+D+.10,eave+rise+.065)],.085,'roof',8)
 # Front/back filled gables, so curves have real enclosed volume.
 for fy in [cy-D+.17,cy+D-.17]:
  vs=[(cx-W+.14,fy,eave-.12),(cx+W-.14,fy,eave-.12)]
  vs.extend((cx+W*(1-i/12),fy,rz(1-i/12)-.05) for i in range(13))
  vs.extend((cx-W*i/12,fy,rz(i/12)-.05) for i in range(1,13))
  o=mesh(name+'GableWall',vs,[tuple(range(len(vs)))],'ivory');s=o.modifiers.new('Gable thickness','SOLIDIFY');s.thickness=.14
 return rz
bpy.app.driver_namespace['terminal25']=globals()
print('NEW_TERMINAL_HELPERS_READY',len(C.objects),roof.name if hasattr(roof,'name') else 'current town palette')
