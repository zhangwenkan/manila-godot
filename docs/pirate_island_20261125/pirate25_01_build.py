"""Run once through the owned Blender MCP. New island only; no existing mesh edits."""
import bpy,bmesh,math,random,json,os,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/pirate_island_20261125'
assert os.getpid()==1028 and not bpy.app.background and bpy.types.blendermcp_server.port==9881
assert (LOG/'before_manifest.json').exists() and not bpy.data.collections.get('Reference_PirateIsland')
rng=random.Random(251126)
C=bpy.data.collections.new('Reference_PirateIsland');bpy.context.scene.collection.children.link(C)
root=bpy.data.objects.new('P25_Assembly',None);C.objects.link(root)
root.location=(-17.5,22,0);root.rotation_euler.z=math.radians(-20);root['reference_asset']='pirate_island'
P={r:bpy.data.materials['Ref_TR20_'+r] for r in ['wood','deck','beam','stone']}
P.update({r:bpy.data.materials[n] for r,n in {'iron':'Ref_D19_ForgedIron','rope':'Ref_Rope','brass':'Ref_D19_AgedBrass','leaf0':'Ref_D19_Foliage0','leaf1':'Ref_D19_Foliage1','leaf2':'Ref_D19_Foliage2'}.items()})
def linear(rgb):
 a=np.asarray(rgb)/255.;return np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)
def mat(name,rgb,source=None,rough=.9):
 m=bpy.data.materials[source].copy() if source else bpy.data.materials.new('P25_'+name)
 m.name='P25_'+name;m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 if source:
  links=list(p.inputs['Base Color'].links)
  if links and links[0].from_node.type=='TEX_IMAGE':
   n=links[0].from_node;src=n.image;w,h=src.size;a=np.empty(w*h*4,np.float32);src.pixels.foreach_get(a);a=a.reshape(h,w,4)
   base=np.mean(a[:,:,:3],axis=(0,1));a[:,:,:3]*=linear(rgb)/np.maximum(base,.001)
   im=bpy.data.images.new('P25_'+name+'_Color',width=w,height=h,alpha=True);im.colorspace_settings.name='sRGB';im.pixels.foreach_set(a.ravel())
   im.filepath_raw=str(ROOT/('assets/reference/P25_'+name+'_Color.png'));im.file_format='PNG';im.save();im.pack();n.image=im
  else:
   for l in links:m.node_tree.links.remove(l)
   p.inputs['Base Color'].default_value=(*linear(rgb),1)
 else:p.inputs['Base Color'].default_value=(*linear(rgb),1)
 p.inputs['Roughness'].default_value=rough
 P[name]=m;return m
mat('rock',(137,137,120),'Ref_TR20_stone');mat('rocklight',(157,153,132),'Ref_TR20_stone')
mat('rockdark',(104,111,99),'Ref_TR20_stone');mat('sand',(183,166,123),'Ref_Sand')
mat('moss',(88,115,44),'Ref_D19_Foliage1');mat('bone',(214,203,169),'Ref_TR20_ivory')
mat('void',(27,33,28));mat('flag',(45,51,48));mat('soil',(106,111,61),'Ref_Sand')
supports=[]
def mesh(name,vs,fs,role):
 d=bpy.data.meshes.new('P25_'+name);d.from_pydata(vs,[],fs);d.update()
 bm=bmesh.new();bm.from_mesh(d);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(d);bm.free()
 o=bpy.data.objects.new('P25_'+name,d);C.objects.link(o);o.parent=root;d.materials.append(P[role]);o['pirate25_role']=role
 uv=d.uv_layers.new(name='UVMap')
 for poly in d.polygons:
  ax=max(range(3),key=lambda j:abs(poly.normal[j]));a=[j for j in range(3) if j!=ax]
  for li in poly.loop_indices:
   v=d.vertices[d.loops[li].vertex_index].co;uv.data[li].uv=(v[a[0]]*.42,v[a[1]]*.42)
 return o
def box(name,c,s,role='wood',bevel=.015):
 x,y,z=[a/2 for a in s];vs=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
 o=mesh(name,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],role);o.location=c
 if role in ('wood','deck','beam'):
  long=max(range(3),key=lambda j:s[j]);uv=o.data.uv_layers.active
  for p in o.data.polygons:
   ax=max(range(3),key=lambda j:abs(p.normal[j]));cross=next((j for j in range(3) if j!=ax and j!=long),(long+1)%3)
   for li in p.loop_indices:
    v=o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(v[cross]*1.25,v[long]*.5)
 if bevel:
  m=o.modifiers.new('Soft worn edges','BEVEL');m.width=min(bevel,min(s)*.2);m.segments=1
  m=o.modifiers.new('Broad face normals','WEIGHTED_NORMAL');m.keep_sharp=True
 return o
def tube(name,pts,r,role='wood',sides=8):
 pts=[Vector(p) for p in pts];vs=[];fs=[]
 for i,p in enumerate(pts):
  q=(pts[min(len(pts)-1,i+1)]-pts[max(0,i-1)]).normalized();u=q.cross(Vector((0,0,1)))
  if u.length<.01:u=q.cross(Vector((0,1,0)))
  u.normalize();v=q.cross(u).normalized()
  rr=r[i] if isinstance(r,(list,tuple)) else r
  for j in range(sides):vs.append(p+rr*(math.cos(j*math.tau/sides)*u+math.sin(j*math.tau/sides)*v))
 fs.append(tuple(reversed(range(sides))))
 for i in range(len(pts)-1):
  for j in range(sides):fs.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
 fs.append(tuple((len(pts)-1)*sides+j for j in range(sides)))
 return mesh(name,vs,fs,role)
def beam(name,a,b,w,role='beam'):
 a,b=Vector(a),Vector(b);d=b-a;o=box(name,(a+b)/2,(w,w,d.length),role);o.rotation_euler=d.to_track_quat('Z','Y').to_euler();return o
def blob(name,c,s,role='rock',seed=0):
 rr=random.Random(seed);N=9;vs=[];fs=[]
 phases=[rr.uniform(-.06,.06) for j in range(N)];rad=[rr.uniform(.87,1.08) for j in range(N)]
 for k,(z,r) in enumerate([(-.50,.75),(-.35,1),(.28,.90),(.50,.64)]):
  for j in range(N):
   a=j*math.tau/N+phases[j];vs.append((math.cos(a)*r*rad[j]*s[0]/2+.08*s[0]*z,math.sin(a)*r*rad[j]*s[1]/2+.10*s[1]*z,(z+(.018*math.sin(j*2+seed) if k in [1,2] else .012*math.sin(j+seed)))*s[2]))
 fs.append(tuple(reversed(range(N))))
 for k in range(3):
  for j in range(N):fs.append((k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j))
 fs.append(tuple(3*N+j for j in range(N)))
 o=mesh(name,vs,fs,role);o.location=c
 return o
def ellipsoid(name,c,s,role,seg=18,rings=10):
 vs=[(0,0,-s[2])];fs=[]
 for k in range(1,rings):
  t=-math.pi/2+math.pi*k/rings
  for j in range(seg):
   a=math.tau*j/seg;vs.append((s[0]*math.cos(t)*math.cos(a),s[1]*math.cos(t)*math.sin(a),s[2]*math.sin(t)))
 vs.append((0,0,s[2]));top=len(vs)-1
 for j in range(seg):fs.append((0,1+(j+1)%seg,1+j))
 for k in range(rings-2):
  for j in range(seg):fs.append((1+k*seg+j,1+k*seg+(j+1)%seg,1+(k+1)*seg+(j+1)%seg,1+(k+1)*seg+j))
 for j in range(seg):fs.append((top,1+(rings-2)*seg+j,1+(rings-2)*seg+(j+1)%seg))
 o=mesh(name,vs,fs,role);o.location=c
 for p in o.data.polygons:p.use_smooth=True
 return o
# The sandy shelf is a single closed body with a real submerged skirt, and an inset front cove.
N=64;RINGS=13;vs=[(0,0,.43)];fs=[]
def radius(a):
 front=max(0,-math.sin(a));return 5.25+.36*math.sin(3*a+.4)+.24*math.cos(5*a)-1.20*front**14
def ground_z(x,y,rfrac=None):
 a=math.atan2(y/1.0,x);r=math.hypot(x,y)/radius(a) if rfrac is None else rfrac
 core=.46+.24*math.exp(-((x+2.4)**2+(y-1.8)**2)/8)+.20*math.exp(-((x-2)**2+(y-2.6)**2)/7)
 z=core+.035*math.sin(x*2.1)*math.cos(y*1.7)
 if r>.66:z=z*(1-(r-.66)/.34)-.16*((r-.66)/.34)
 return z
for k in range(1,RINGS+1):
 f=k/RINGS
 for j in range(N):
  a=j*math.tau/N;r=radius(a)*f;x=r*math.cos(a);y=r*math.sin(a)
  vs.append((x,y,ground_z(x,y,f)))
for j in range(N):fs.append((0,1+j,1+(j+1)%N))
for k in range(RINGS-1):
 for j in range(N):
  a=1+k*N+j;b=1+k*N+(j+1)%N;c=1+(k+1)*N+(j+1)%N;d=1+(k+1)*N+j
  fs.extend([(a,b,c),(a,c,d)])
bottom_start=len(vs)
for j in range(N):
 a=j*math.tau/N;r=radius(a)*1.035;vs.append((r*math.cos(a),r*math.sin(a),-1.3))
for j in range(N):fs.append((1+(RINGS-1)*N+j,bottom_start+j,bottom_start+(j+1)%N,1+(RINGS-1)*N+(j+1)%N))
fs.append(tuple(reversed([bottom_start+j for j in range(N)])))
base=mesh('IslandSandBody',vs,fs,'sand')
for p in base.data.polygons:p.use_smooth=True
# Rock massing: broad, leaning shoulders in three groups. Front cove stays open.
rocks=[(-3.6,1.1,1.8,2.1,2.9,3.7),(-3.1,2.75,2.15,2.9,2.8,4.5),(-1.15,3.1,2.1,2.8,2.8,4.4),
 (1.05,3.3,3.4,2.8,2.8,7.0),(2.7,2.55,2.75,2.2,3.0,5.7),(3.75,1.45,2.15,1.85,2.7,4.5),
 (3.95,-.4,1.75,1.8,2.9,3.7),(3.1,-2.7,1.6,2.25,2.15,3.45),(-4.05,-1.1,1.5,1.9,2.5,3.2),(-3.5,-2.7,.85,2.0,1.5,1.95)]
rock_objects=[]
for i,(x,y,z,sx,sy,sz) in enumerate(rocks):
 o=blob('RidgeMass', (x,y,z),(sx,sy,sz),'rock' if i%3 else 'rocklight',100+i);rock_objects.append(o)
 # Attached, overlapping smaller facets are purposeful shoulders, not surface scratches.
 if i in [0,3,4,5,7,8]:
  blob('RockShoulder',(x-.48,y-.45,z*.69),(sx*.62,sy*.72,sz*.62),'rocklight',130+i)
# A true cave: closed thick arch strip, extruded to a deep dim rear wall.
cx=.65;cy=.35;floor=.40
path=[(-1.35,0),(-1.38,1.1),(-1.10,2.12),(-.48,2.78),(.22,2.95),(.85,2.48),(1.29,1.55),(1.35,0)]
outer=[(-2.15,-.12),(-2.2,1.4),(-1.78,2.72),(-.72,3.55),(.48,3.75),(1.6,3.17),(2.0,1.7),(2.1,-.12)]
av=[];af=[]
for y in [cy-.25,cy+2.5]:
 for p in (path,outer):
  av.extend((cx+x,y,floor+z) for x,z in p)
M=len(path)
for i in range(M-1):
 af.extend([(i,i+1,M+i+1,M+i),(2*M+i,3*M+i,3*M+i+1,2*M+i+1),(i,2*M+i,2*M+i+1,i+1),(M+i,M+i+1,3*M+i+1,3*M+i)])
af.extend([(0,M,3*M,2*M),(M-1,3*M-1,4*M-1,2*M-1)])
cave=mesh('CaveSolidArch',av,af,'rockdark')
back=mesh('CaveBackWall',[(cx+x,cy+2.48,floor+z) for x,z in path],[tuple(range(M))],'void')
solid=back.modifiers.new('Rock back depth','SOLIDIFY');solid.thickness=.25
box('CaveFloor',(cx,cy+1.1,.38),(2.6,2.7,.16),'rockdark')
# Irregular entrance stones follow the opening but remain part of the natural ridge.
for i in range(M-1):
 a=Vector((path[i][0],path[i][1]));b=Vector(path[i+1]);u=Vector(outer[i]);v=Vector(outer[i+1]);quad=[a,b,v,u]
 vv=[(cx+p.x,cy-.40-.035*math.sin(i*1.7),floor+p.y) for p in quad]+[(cx+p.x,cy+.22,floor+p.y) for p in quad]
 o=mesh('CaveEntranceStone',vv,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],'rocklight' if i%3 else 'rock')
 bevel=o.modifiers.new('Eroded stone corners','BEVEL');bevel.width=.11;bevel.segments=1
# Moss rests on actual rock top faces with a few natural hanging tongues.
for i,o in enumerate(rock_objects):
 d=o.data;top=d.polygons[-1];points=[o.location+d.vertices[j].co for j in top.vertices];center=sum(points,Vector())/len(points)
 mv=[center+Vector((0,0,.018))]+[center+(p-center)*.92+Vector((0,0,.025)) for p in points];mf=[]
 for j in range(len(points)):mf.append((0,j+1,(j+1)%len(points)+1))
 moss=mesh('RockCrownMoss',mv,mf,'moss');so=moss.modifiers.new('Thin living ground','SOLIDIFY');so.thickness=.025
 if i in [0,3,5,7,8]:
  # A broad taper is embedded against the rock shoulder, with no floating strands.
  p=points[6];q=points[7];w=(q-p)*.18;mid=p*.35+q*.65
  vs2=[mid-w+Vector((0,0,.015)),mid+w+Vector((0,0,.015)),mid+Vector((-.08,-.10,-.8)),mid+Vector((-.13,-.11,-1.3))]
  mesh('MossCleft',vs2,[(0,1,2),(0,2,3)],'moss')
# Individual grounded rocks connect the large faces to the beach, with an open central landing.
for i,(x,y,s) in enumerate([(-2.5,-.3,.65),(-1.8,-.7,.50),(2.65,-.6,.60),(2.85,-1.5,.45),(-3.2,-3.5,.6),(3.75,-3.5,.52),(-4.7,.2,.8),(4.65,.6,.7),(-1.9,-2.2,.32),(2.25,-3.3,.30)]):
 z=ground_z(x,y);o=blob('BeachTalus',(x,y,z+s*.25),(s*1.25,s,s*.85),'rocklight',260+i)
 supports.append({'object':o.name,'bottom_local':[x,y,z-.18],'support':'P25_IslandSandBody'})
# Surface ground beneath the forest is a low irregular earthen bank, not a flat grass disc.
bank=blob('ForestEarthBank',(-1.9,1.3,.72),(4.6,4.6,1.35),'soil',310)
# Trees use broad asymmetrical crowns and layered needle canopies compatible with town colors.
def tree(x,y,z,h,kind,seed):
 rr=random.Random(seed);bend=rr.uniform(-.18,.18)
 trunk=tube('TreeTrunk',[(x,y,z-.12),(x+.05,y,z+h*.34),(x+bend,y+.1,z+h*.68)],[.15,.13,.065],'beam',8)
 for a in [0,2.2,4.1]:tube('TreeRoot',[(x+math.cos(a)*.43,y+math.sin(a)*.43,z-.03),(x,y,z+.22)], [.055,.13],'beam',6)
 if kind=='broad':
  for j in range(5):
   a=j*math.tau/5+.2;xx=x+math.cos(a)*h*.19;yy=y+math.sin(a)*h*.19;zz=z+h*(.68+rr.uniform(-.08,.08))
   tube('TreeBranch',[(x,y,z+h*.4),(xx,yy,zz)],[.085,.035],'beam',6)
   blob('BroadCanopy',(xx,yy,zz),(h*.64,h*.62,h*.47),'leaf'+str((j+seed)%3),seed*10+j)
  blob('BroadTop',(x-.1,y+.05,z+h*.91),(h*.67,h*.64,h*.46),'leaf1',seed*10+8)
 else:
  for k in range(4):
   zz=z+h*(.35+k*.17);R=h*(.25-k*.043);N2=11;v=[];f=[]
   for lev,(dz,rad) in enumerate([(-.10,R*.75),(.04,R),(.50*h,R*.08)]):
    for j in range(N2):
     a=j*math.tau/N2+k*.25;r=rad*(1+.10*math.sin(j*3+seed));v.append((x+bend*k/4+math.cos(a)*r,y+math.sin(a)*r,zz+dz+.07*math.sin(j*2+seed)))
   f.append(tuple(reversed(range(N2))))
   for lev in range(2):
    for j in range(N2):f.append((lev*N2+j,lev*N2+(j+1)%N2,(lev+1)*N2+(j+1)%N2,(lev+1)*N2+j))
   f.append(tuple(2*N2+j for j in range(N2)))
   mesh('NeedleCanopy',v,f,'leaf'+str((k+seed)%3))
 return trunk
# Heights queried against actual evaluated local rock/earth surface, never a guessed floating shelf.
bpy.context.view_layer.update()
support_objects=[base,bank]+rock_objects
def surface(x,y):
 best=-100
 for o in support_objects:
  inv=o.matrix_local.inverted();org=inv@Vector((x,y,20));dire=inv.to_3x3()@Vector((0,0,-1))
  ok,loc,n,ix=o.ray_cast(org,dire)
  if ok:best=max(best,(o.matrix_local@loc).z)
 return max(ground_z(x,y),best)
trees=[(-3.1,1.6,3.2,'broad'),(-2.8,2.8,3.4,'pine'),(-1.7,2.7,3.1,'broad'),(-.35,3.7,3.2,'pine'),(-3.7,.5,2.7,'pine'),(-2.7,.2,2.8,'broad'),(-1.55,1.3,3.0,'pine'),(-3.5,-.9,2.1,'broad'),(3.6,1.6,2.6,'pine'),(3.8,-.6,2.35,'broad'),(2.8,3.7,2.5,'pine')]
for i,(x,y,h,kind) in enumerate(trees):
 z=surface(x,y);o=tree(x,y,z,h,kind,400+i);supports.append({'object':o.name,'bottom_local':[x,y,z-.12],'support':'terrain_group'})
# Three short broken dock fragments wrap the inlet, with beams and submerged pile feet.
def dock(name,x,y,w,length,z,missing=()):
 n=round(length/.27)
 for j in range(n):
  if j in missing:continue
  yy=y+(j/(n-1)-.5)*length;o=box(name+'Plank',(x+(.025*math.sin(j*1.3)),yy,z),(w+.06*math.sin(j),.25,.11),'deck');o.rotation_euler.z=.015*math.sin(j)
 for dx in [-w*.32,w*.32]:box(name+'Runner',(x+dx,y,z-.13),(.13,length+.1,.19),'beam')
 for yy in [y-length*.42,y+length*.42]:
  for xx in [x-w*.43,x+w*.43]:
   tube(name+'Pile',[(xx,yy,-.95),(xx+.025,yy,z+.35)],[.13,.11],'beam',9)
   for zz in [z-.02,z+.10]:tube(name+'Lashing',[(xx+.125*math.cos(a*math.tau/12),yy+.125*math.sin(a*math.tau/12),zz) for a in range(13)],.025,'rope',5)
dock('InnerJetty',-.4,-2.65,1.15,2.20,.67,())
dock('BrokenOuterJetty',.1,-5.05,1.05,1.65,.55,(0,4))
beam('BrokenBrace',(-.35,-5.7,-.2),(.50,-4.5,.39),.13)
# Small whalebone skeleton lies on the left beach, not on the walking approach.
for i in range(7):
 x=-2.8+i*.24;y=-2.05;z=ground_z(x,y)+.12
 ellipsoid('WhaleVertebra',(x,y,z),(.14,.14,.13),'bone',12,6)
 for sign in [-1,1]:
  tube('WhaleRib',[(x,y,z),(x+.03,y+sign*.25,z+.30),(x+.07,y+sign*.47,z+.34),(x+.11,y+sign*.58,z+.13)],[.065,.055,.04,.025],'bone',6)
blob('WhaleSkull',(-3.05,-2.08,ground_z(-3,-2)+.20),(.58,.48,.40),'bone',510)
# Pirate skull emblem with real recessed sockets and a small separate jaw.
skull=ellipsoid('SkullCranium',(cx,cy-.73,4.35),(.68,.40,.72),'bone',24,16)
for dx in [-.28,.28]:
 cutter=ellipsoid('SocketCutter',(cx+dx,cy-1.02,4.35),(.25,.30,.255),'void',20,12)
 bpy.context.view_layer.update();mod=skull.modifiers.new('Carved eye socket','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter;mod.solver='EXACT'
 bpy.context.view_layer.objects.active=skull;skull.select_set(True);bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
 ellipsoid('EyeRecess',(cx+dx,cy-.84,4.35),(.207,.13,.215),'void',16,8)
nose=mesh('NoseCavity',[(cx-.10,cy-1.12,4.12),(cx+.10,cy-1.12,4.12),(cx,cy-1.15,4.36),(cx-.08,cy-.87,4.14),(cx+.08,cy-.87,4.14),(cx,cy-.87,4.33)],[(0,1,2),(3,5,4),(0,3,4,1),(1,4,5,2),(2,5,3,0)],'void')
mod=skull.modifiers.new('Nasal hollow','BOOLEAN');mod.operation='DIFFERENCE';mod.object=nose;mod.solver='EXACT';bpy.context.view_layer.objects.active=skull;bpy.ops.object.modifier_apply(modifier=mod.name)
for sign in [-1,1]:
 ellipsoid('CheekBone',(cx+sign*.49,cy-.88,4.13),(.18,.17,.22),'bone',14,8)
 tube('JawBone',[(cx+sign*.48,cy-.67,4.02),(cx+sign*.37,cy-.88,3.83),(cx+sign*.12,cy-1,3.80)],.08,'bone',8)
for j in range(7):box('SkullTooth',(cx+(j-3)*.116,cy-1.05,3.98),(.093,.14,.26-.015*abs(j-3)),'bone',.024)
for sign in [-1,1]:
 a=Vector((cx-sign*1.00,cy-.57,3.75));b=Vector((cx+sign*1.08,cy-.57,4.42));tube('CrossBone',[a,a.lerp(b,.25),a.lerp(b,.75),b],[.11,.08,.08,.11],'bone',9)
 for p in [a,b]:
  for dx in [-.07,.07]:ellipsoid('BoneJoint',p+Vector((dx,-.015,0)),(.11,.10,.14),'bone',12,8)
# Treasure chest with slatted barrel-vault lid and real metal straps.
chx=1.8;chy=-1.3;chz=ground_z(chx,chy)+.35
box('ChestBody',(chx,chy,chz),(1.1,.67,.62),'beam')
for j in range(6):box('ChestFrontBoard',(chx+(j-2.5)*.175,chy-.35,chz),(.164,.055,.54),'wood',.009)
for k in range(8):
 a=math.pi*k/8;b=math.pi*(k+1)/8;vs=[]
 for xx in [chx-.56,chx+.56]:
  vs.extend([(xx,chy+.35*math.cos(a),chz+.30+.35*math.sin(a)),(xx,chy+.35*math.cos(b),chz+.30+.35*math.sin(b))])
 o=mesh('ChestLidSlat',vs,[(0,1,3,2)],'wood');s=o.modifiers.new('Lid timber thickness','SOLIDIFY');s.thickness=.06
for xx in [chx-.40,chx+.40]:
 tube('ChestLidStrap',[(xx,chy+.375*math.cos(a*math.pi/12),chz+.30+.375*math.sin(a*math.pi/12)) for a in range(13)],.045,'brass',5)
 box('ChestIronBand',(xx,chy-.38,chz),(.065,.045,.61),'brass',.005)
box('ChestLock',(chx,chy-.40,chz+.14),(.13,.08,.20),'brass',.01)
# Barrel beside cave is grounded by construction.
bx=-1.2;by=-.35;bz=ground_z(bx,by)
for j in range(12):
 a=j*math.tau/12;b=(j+.95)*math.tau/12;v=[]
 for z,r in [(0,.25),(.40,.31),(.78,.25)]:v.extend([(bx+r*math.cos(a),by+r*math.sin(a),bz+z),(bx+r*math.cos(b),by+r*math.sin(b),bz+z)])
 o=mesh('BarrelStave',v,[(0,1,3,2),(2,3,5,4)],'wood');s=o.modifiers.new('Stave thickness','SOLIDIFY');s.thickness=.035
for z in [.10,.67]:tube('BarrelHoop',[(bx+.28*math.cos(j*math.tau/20),by+.28*math.sin(j*math.tau/20),bz+z) for j in range(21)],.035,'iron',5)
box('BarrelTop',(bx,by,bz+.75),(.42,.42,.04),'wood',.04)
# A partial wreck is its own assembly at the outer left shallows.
wreck_origin=Vector((-3.55,-4.15,-.03));wreck_angle=math.radians(-36)
def W(p):return wreck_origin+Matrix.Rotation(wreck_angle,3,'Z')@Vector(p)
for j in range(7):
 yy=-1.55+j*.43;width=.76*(1-(abs(yy)/2.2)**2)
 for sign in [-1,1]:tube('WreckRib',[W((0,yy,-.33)),W((sign*width*.62,yy,-.02)),W((sign*width,yy,.48+.1*math.sin(j)))],[.075,.07,.055],'beam',6)
for sign in [-1,1]:
 for k in range(3):
  pts=[W((sign*(.50+k*.11)*(1-(abs(y)/2.3)**2),y,-.06+k*.20)) for y in [-1.6,-1.1,-.6,-.1,.4,.9,1.4]]
  tube('WreckHullStrake',pts,.095,'wood',4)
beam('WreckKeel',W((0,-1.75,-.28)),W((0,1.7,-.28)),.18)
for j in range(5):
 yy=-.9+j*.29;beam('WreckDeck',W((-.43,yy,.13)),W((.26+.06*math.sin(j),yy,.13)),.18,'deck')
mastbottom=W((0,.50,-.3));masttop=W((-.18,.60,2.20));tube('WreckBrokenMast',[mastbottom,masttop],[.115,.072],'beam',9)
beam('WreckYard',W((-.85,.56,1.72)),W((.80,.56,1.8)),.085)
# Torn flag and simple bone symbol are actual geometry, readable at the gameplay distance.
flagvs=[W((-.06,.57,1.95)),W((.94,.64,1.92)),W((.80,.61,1.55)),W((.96,.63,1.17)),W((-.06,.57,1.20))]
flag=mesh('PirateFlag',flagvs,[(0,1,2,3,4)],'flag');s=flag.modifiers.new('Canvas thickness','SOLIDIFY');s.thickness=.012
fc=W((.39,.53,1.63));ellipsoid('FlagSkull',fc,(.13,.035,.14),'bone',12,8)
for sign in [-1,1]:tube('FlagBones',[W((.16,.52,1.36+(.06 if sign>0 else 0))),W((.66,.52,1.42-(.06 if sign>0 else 0)))],.025,'bone',5)
for i in range(10):
 x=-4.4+rng.random()*2.7;y=-4.9+rng.random()*.9;z=max(-.1,ground_z(x,y))+.05
 o=box('DriftTimber',(x,y,z),(rng.uniform(.45,1.1),.13,.10),'wood');o.rotation_euler=(.05,rng.uniform(-.15,.15),rng.uniform(-.8,.8))
# Sparse broad grass tufts anchor soil against the rocks; keep central sand and the cave mouth clear.
for i in range(45):
 a=rng.uniform(0,math.tau);r=rng.uniform(2.6,4.4);x=r*math.cos(a);y=r*math.sin(a)
 if y<-.6 and abs(x)<2.5:continue
 z=surface(x,y)
 if z>2.0:continue
 for j in range(3):
  t=j*2.1;d=Vector((math.cos(t)*.1,math.sin(t)*.1,0));p=Vector((x,y,z-.025));v=[p-d,p+d,p+Vector((math.sin(t)*.16,math.cos(t)*.16,.32+rng.random()*.16))]
  o=mesh('GroundLeaf',v,[(0,1,2)],'moss');s=o.modifiers.new('Leaf thickness','SOLIDIFY');s.thickness=.005
bpy.context.view_layer.update()
report={'objects':len([o for o in C.objects if o.type=='MESH']),'root_blender':list(root.location),'rotation_z_degrees':-20,'front_godot':[-math.sin(math.radians(20)),0,math.cos(math.radians(20))],'terrain_objects':[base.name],'skirt_bottom':-1.3,'skirt_indices':list(range(bottom_start,bottom_start+N)),'supports':supports}
(LOG/'build.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.app.driver_namespace['pirate25']=globals()
print(json.dumps({k:v for k,v in report.items() if k not in ['supports','skirt_indices']}))
