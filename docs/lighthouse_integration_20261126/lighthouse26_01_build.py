"""One-time current-town lighthouse construction, through owned GUI MCP only.

The two legacy lighthouse pictures are explicitly excluded by the user.
Design derives from current town: warm framed plaster, blue roof, timber deck,
small stone footing. Position is assigned after independent route/site review.
"""
import bpy, bmesh, math, random, json, os
from pathlib import Path
from mathutils import Vector

ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/lighthouse_integration_20261126'
assert os.getpid()==18904 and bpy.types.blendermcp_server.port==9891 and not bpy.app.background
assert (LOG/'session_start.json').exists() and bpy.data.collections.get('Reference_Lighthouse') is None
C=bpy.data.collections.new('Reference_Lighthouse'); bpy.context.scene.collection.children.link(C)
root=bpy.data.objects.new('L26_Assembly',None); C.objects.link(root)
root['reference_asset']='lighthouse'; root['placement_pending']=True
root['design_basis']='Current town and terminal materials only. Legacy lighthouse images explicitly excluded.'
P={r:bpy.data.materials['Ref_TR20_'+r] for r in ['wood','deck','beam','stone','ivory','plaster','teal']}
P.update({k:bpy.data.materials[v] for k,v in {
 'roof':'Ref_TN25_NavyRoof','iron':'Ref_D19_ForgedIron','brass':'Ref_D19_AgedBrass',
 'rope':'Ref_Rope','rock':'P25_rock','rocklight':'P25_rocklight','rockdark':'P25_rockdark',
 'dark':'Ref_Glass'}.items()})

def linear(c): return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
def plain(name,rgb,rough=.75,alpha=1,emission=0):
 m=bpy.data.materials.new('L26_'+name); m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF'); col=tuple(linear(c/255) for c in rgb)
 p.inputs['Base Color'].default_value=(*col,1); p.inputs['Roughness'].default_value=rough
 p.inputs['Alpha'].default_value=alpha
 if alpha<1:
  m.surface_render_method='BLENDED'; m.use_transparency_overlap=False
 if emission:
  p.inputs['Emission Color'].default_value=(*col,1); p.inputs['Emission Strength'].default_value=emission
 P[name]=m
plain('LanternGlass',(173,208,202),.17,.13)
plain('LensGlass',(237,204,116),.26,.46)
plain('LampCore',(255,218,136),.48,1,1.4)
plain('CopperMirror',(163,126,67),.25)
P['CopperMirror'].node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value=.35

def mesh(name,vs,fs,role):
 d=bpy.data.meshes.new('L26_'+name); d.from_pydata(vs,[],fs); d.update()
 bm=bmesh.new(); bm.from_mesh(d); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(d); bm.free()
 o=bpy.data.objects.new('L26_'+name,d); C.objects.link(o); o.parent=root
 o['lighthouse_part']=name; d.materials.append(P[role]); uv=d.uv_layers.new(name='UVMap')
 for p in d.polygons:
  axis=max(range(3),key=lambda j:abs(p.normal[j])); ax=[j for j in range(3) if j!=axis]
  for li in p.loop_indices:
   v=d.vertices[d.loops[li].vertex_index].co; uv.data[li].uv=(v[ax[0]]*.6,v[ax[1]]*.6)
 return o

def box(name,c,s,role='wood',bevel=.012):
 x,y,z=[v/2 for v in s]
 vs=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
 o=mesh(name,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],role); o.location=c
 if role in ['wood','deck','beam']:
  long=max(range(3),key=lambda j:s[j]); uv=o.data.uv_layers.active
  for p in o.data.polygons:
   ax=max(range(3),key=lambda j:abs(p.normal[j])); cross=next((j for j in range(3) if j!=ax and j!=long),(long+1)%3)
   for li in p.loop_indices:
    v=o.data.vertices[o.data.loops[li].vertex_index].co; uv.data[li].uv=(v[cross]*1.25,v[long]*.5)
 if bevel:
  m=o.modifiers.new('Town edge softness','BEVEL');m.width=min(bevel,min(s)*.20);m.segments=1
  m=o.modifiers.new('Broad normals','WEIGHTED_NORMAL');m.keep_sharp=True
 return o

def beam(name,a,b,width,role='beam'):
 a,b=Vector(a),Vector(b);d=b-a;o=box(name,(a+b)/2,(width,width,d.length),role,.008)
 o.rotation_euler=d.to_track_quat('Z','Y').to_euler();return o

def tube(name,points,radius,role,sides=8):
 pts=[Vector(p) for p in points]; vs=[];fs=[];arc=[0]
 for i,p in enumerate(pts):
  direct=(pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized(); u=direct.cross(Vector((0,0,1)))
  if u.length<.01:u=direct.cross(Vector((0,1,0)))
  u.normalize();v=direct.cross(u).normalized()
  for j in range(sides):vs.append(p+radius*(math.cos(j*math.tau/sides)*u+math.sin(j*math.tau/sides)*v))
  if i:arc.append(arc[-1]+(p-pts[i-1]).length)
 fs.append(tuple(reversed(range(sides))))
 for i in range(len(pts)-1):
  for j in range(sides):fs.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
 fs.append(tuple((len(pts)-1)*sides+j for j in range(sides)))
 o=mesh(name,vs,fs,role);uv=o.data.uv_layers.active
 for poly in o.data.polygons:
  ids=[o.data.loops[li].vertex_index for li in poly.loop_indices]
  seam=0 in [ix%sides for ix in ids] and sides-1 in [ix%sides for ix in ids]
  for li,ix in zip(poly.loop_indices,ids):
   j=ix%sides;uv.data[li].uv=(1.0 if seam and j==0 else j/sides,arc[ix//sides]*.5)
 return o

def ring(name,profile,role,n=8,phase=math.pi/8):
 vs=[];fs=[]
 for z,r in profile:
  for j in range(n):
   a=phase+j*math.tau/n;vs.append((r*math.cos(a),r*math.sin(a),z))
 fs.append(tuple(reversed(range(n))))
 for k in range(len(profile)-1):
  for j in range(n):fs.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
 fs.append(tuple((len(profile)-1)*n+j for j in range(n)))
 o=mesh(name,vs,fs,role);uv=o.data.uv_layers.active
 for poly in o.data.polygons:
  if abs(poly.normal.z)>.99:continue
  ids=[o.data.loops[li].vertex_index for li in poly.loop_indices]
  seam=0 in [ix%n for ix in ids] and n-1 in [ix%n for ix in ids]
  for li,ix in zip(poly.loop_indices,ids):
   j=ix%n;u=1 if seam and j==0 else j/n
   uv.data[li].uv=(u*math.tau*profile[ix//n][1]*.6,profile[ix//n][0]*.6)
 return o

def rock(name,c,size,role,seed):
 rr=random.Random(seed);n=9;rad=[rr.uniform(.85,1.07) for _ in range(n)];vs=[];fs=[]
 for k,(z,r) in enumerate([(-.5,.70),(-.28,1.0),(.25,.88),(.5,.55)]):
  for j in range(n):
   a=j*math.tau/n+.07*math.sin(j+seed);vs.append((size[0]*.5*r*rad[j]*math.cos(a)+.05*z,size[1]*.5*r*rad[j]*math.sin(a),size[2]*(z+.025*math.sin(j*1.7+seed))))
 fs.append(tuple(reversed(range(n))))
 for k in range(3):
  for j in range(n):fs.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
 fs.append(tuple(3*n+j for j in range(n)))
 o=mesh(name,vs,fs,role);o.location=c;return o

# A grounded low asymmetric reef, with a small working terrace rather than a grassy island.
rock('MainReef',(.15,.1,-.48),(4.45,4.1,2.5),'rock',110)
rock('WesternShoulder',(-1.45,.12,-.10),(1.9,2.5,1.55),'rocklight',112)
rock('RearShoulder',(.65,1.48,-.06),(2.3,1.55,1.5),'rock',113)
rock('LowSeawardFoot',(-.65,-1.62,-.40),(2.2,1.45,1.1),'rockdark',114)
rock('EastLowFoot',(1.75,-.55,-.27),(1.4,1.9,1.35),'rocklight',115)
ring('StoneTerrace',[(.37,1.91),(.53,1.98),(.72,1.94)],'stone',8)
ring('TowerStoneFoot',[(.67,1.32),(.87,1.33),(1.18,1.25),(1.40,1.22)],'stone',8)
# Broad stone joints are limited to the base; wall texture remains readable at ship scale.
for k,z in enumerate([.82,1.10]):
 for j in range(8):
  a=j*math.tau/8+math.pi/8
  r=1.325 if k==0 else 1.27
  p=(r*math.cos(a),r*math.sin(a),z)
  beam('FootVerticalJoint',(p[0],p[1],z-.10),(p[0],p[1],z+.10),.018,'rockdark')

def tower_radius(z): return 1.23+(z-1.35)/(6.45-1.35)*(-.29)
def face_point(a,u,z,inset=0):
 n=Vector((math.cos(a),math.sin(a),0));t=Vector((-math.sin(a),math.cos(a),0))
 r=tower_radius(z)
 return n*(r*math.cos(math.pi/8)-inset)+t*(u*r*math.sin(math.pi/8))+Vector((0,0,z))

# Eight framed trapezoid walls with actual through-openings and 18 cm wall depth.
holes={6:[(-.73,.73,1.40,2.83)],4:[(-.48,.48,3.20,4.15)],7:[(-.45,.45,4.75,5.58)],1:[(-.44,.44,3.85,4.68)]}
for j in range(8):
 a=j*math.tau/8;hs=holes.get(j,[])
 us=sorted(set([-1,1]+[x for h in hs for x in h[:2]]));zs=sorted(set([1.35,6.45]+[z for h in hs for z in h[2:]]))
 vs=[];fs=[]
 for q in range(len(us)-1):
  for k in range(len(zs)-1):
   midu=(us[q]+us[q+1])/2;midz=(zs[k]+zs[k+1])/2
   if any(l<midu<r and lo<midz<hi for l,r,lo,hi in hs):continue
   outer=[face_point(a,us[q],zs[k]),face_point(a,us[q+1],zs[k]),face_point(a,us[q+1],zs[k+1]),face_point(a,us[q],zs[k+1])]
   inner=[v-Vector((math.cos(a),math.sin(a),0))*.18 for v in outer];off=len(vs);vs.extend(outer+inner)
   fs.extend(tuple(off+i for i in f) for f in [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)])
 wall=mesh('TaperedPlasterPanel',vs,fs,'ivory' if j%3 else 'plaster')
 uv=wall.data.uv_layers.active;t=Vector((-math.sin(a),math.cos(a),0))
 for poly in wall.data.polygons:
  for li in poly.loop_indices:
   v=wall.data.vertices[wall.data.loops[li].vertex_index].co;uv.data[li].uv=(v.dot(t)*.6,v.z*.6)
 # Each real aperture has a recessed closure, sill, jamb and glazing frame.
 for u0,u1,z0,z1 in hs:
  n=Vector((math.cos(a),math.sin(a),0));t=Vector((-math.sin(a),math.cos(a),0))
  width=(u1-u0)*tower_radius((z0+z1)/2)*math.sin(math.pi/8)
  center=face_point(a,0,(z0+z1)/2,.12)
  o=box('DoorRecess' if j==6 else 'WindowRecess',center,(width,.055,z1-z0),'teal' if j==6 else 'dark',.008)
  o.rotation_euler.z=a-math.pi/2
  for u in [u0,u1]:beam('ApertureJamb',face_point(a,u,z0,-.025),face_point(a,u,z1,-.025),.075,'wood')
  for z in [z0,z1]:beam('ApertureRail',face_point(a,u0,z,-.035),face_point(a,u1,z,-.035),.085,'wood')
  if j!=6:
   beam('WindowMullion',face_point(a,0,z0,-.015),face_point(a,0,z1,-.015),.04,'wood')
   beam('WindowTransom',face_point(a,u0,(z0+z1)/2,-.015),face_point(a,u1,(z0+z1)/2,-.015),.04,'wood')
  else:
   for u in [-.42,0,.42]:beam('DoorVerticalBoard',face_point(a,u,z0+.05,.080),face_point(a,u,z1-.05,.080),.022,'wood')
   handle=face_point(a,.43,2.06,-.065)
   tube('DoorBrassPull',[handle+Vector((0,0,-.07)),handle+Vector((0,0,.07))],.025,'brass',8)
for j in range(8):
 a=math.pi/8+j*math.tau/8
 beam('TowerCornerFrame',(tower_radius(1.36)*math.cos(a),tower_radius(1.36)*math.sin(a),1.36),(tower_radius(6.44)*math.cos(a),tower_radius(6.44)*math.sin(a),6.44),.065,'wood')
ring('LowerTimberSill',[(1.33,1.265),(1.45,1.258)],'wood',8)
ring('UpperTimberCrown',[(6.27,1.02),(6.48,1.07)],'wood',8)
# Real access from the terrace to the raised door, all within the reef footprint.
for i in range(4):
 box('DoorApproachStep',(0,-1.94+i*.20,.79+i*.145),(1.02,.34,.16),'stone',.025)
for j in range(6):box('MaintenanceLandingBoard',(-1.46,-1.31-j*.18,.61),(.98,.17,.09),'deck',.008)
for x in [-1.83,-1.09]:
 box('MaintenanceRunner',(x,-1.76,.48),(.10,1.17,.18),'beam')
 for y in [-1.28,-2.20]:tube('LandingPile',[(x,y,-.80),(x,y,.88)],.085,'beam',8)
for y in [-1.29,-2.20]:
 tube('LandingMooringRing',[(-1.83+.105*math.cos(j*math.tau/16),y+.105*math.sin(j*math.tau/16),.91) for j in range(17)],.018,'iron',6)
# The eight-sided timber gallery follows the same joint sizes as the town piers.
ring('GalleryUnderRim',[(6.46,1.15),(6.57,1.50),(6.70,1.50)],'beam',8)
ring('GalleryWalkingDeck',[(6.69,1.48),(6.79,1.49)],'deck',8)
for j in range(8):
 a=j*math.tau/8+math.pi/8
 beam('GalleryKneeBrace',(.97*math.cos(a),.97*math.sin(a),6.05),(1.42*math.cos(a),1.42*math.sin(a),6.60),.095,'wood')
for j in range(16):
 a=j*math.tau/16; r=1.42
 beam('GalleryRailPost',(r*math.cos(a),r*math.sin(a),6.77),(r*math.cos(a),r*math.sin(a),7.47),.046,'iron')
for z in [7.08,7.45]:
 tube('GallerySafetyRail',[(1.42*math.cos(j*math.tau/32),1.42*math.sin(j*math.tau/32),z) for j in range(33)],.027,'iron',6)
ring('LanternFoot',[(6.78,.98),(6.94,.96)],'teal',8)
for j in range(8):
 a=math.pi/8+j*math.tau/8;b=a+math.tau/8
 beam('LanternFramePost',(.91*math.cos(a),.91*math.sin(a),6.91),(.91*math.cos(a),.91*math.sin(a),8.16),.065,'wood')
 p=[(.89*math.cos(t),.89*math.sin(t),z) for z in [6.99,8.10] for t in [a,b]]
 # Single clear pane has a physically thin solid thickness for stable normals.
 glass=mesh('LanternClearPane',[p[0],p[1],p[3],p[2]],[(0,1,2,3)],'LanternGlass')
 so=glass.modifiers.new('Window glass thickness','SOLIDIFY');so.thickness=.008
 for z in [7.48,8.13]:beam('LanternPaneRail',(.91*math.cos(a),.91*math.sin(a),z),(.91*math.cos(b),.91*math.sin(b),z),.042,'brass')
ring('LanternHead',[(8.10,.98),(8.21,1.00)],'wood',8)
# A shaped blue cap, low curvature and eight seams: same current roof material, new silhouette.
roof=ring('EightSidedBlueCap',[(8.18,1.12),(8.27,1.19),(8.47,.92),(8.74,.57),(8.92,.21),(9.02,.13)],'roof',8)
for j in range(8):
 a=math.pi/8+j*math.tau/8
 tube('CapStandingSeam',[(r*math.cos(a),r*math.sin(a),z+.012) for z,r in [(8.27,1.19),(8.47,.92),(8.74,.57),(8.92,.21)]],.018,'teal',5)
ring('CapFinial',[(9.00,.14),(9.09,.18),(9.18,.10),(9.25,.04)],'brass',12)
tube('WeatherVaneMast',[(0,0,9.11),(0,0,9.63)],.023,'iron',8)
beam('WeatherVaneBar',(-.28,0,9.48),(.32,0,9.48),.025,'iron')
mesh('WeatherVaneArrow',[(.31,-.018,9.48),(.18,-.018,9.55),(.18,-.018,9.41),(.31,.018,9.48),(.18,.018,9.55),(.18,.018,9.41)],[(0,1,2),(3,5,4),(0,3,4,1),(1,4,5,2),(2,5,3,0)],'brass')
# Center lens assembly, visible through glazing; future beams use the independent marker.
ring('LampPedestal',[(6.94,.28),(7.10,.32),(7.16,.20)],'brass',16)
tube('LensSpindle',[(0,0,7.09),(0,0,7.94)],.035,'iron',10)
ring('WarmLampCore',[(7.20,.12),(7.27,.19),(7.56,.19),(7.66,.11)],'LampCore',20)
ring('OpticalLensBody',[(7.16,.29),(7.24,.37),(7.40,.42),(7.60,.37),(7.75,.23)],'LensGlass',24)
for z,r in [(7.22,.36),(7.32,.40),(7.43,.425),(7.54,.405),(7.65,.34)]:
 tube('LensCopperRim',[(r*math.cos(j*math.tau/32),r*math.sin(j*math.tau/32),z) for j in range(33)],.016,'brass',5)
for a in [0,math.pi]:
 beam('LensBearing',(.49*math.cos(a),.49*math.sin(a),7.01),(.49*math.cos(a),.49*math.sin(a),7.71),.048,'brass')
emitter=bpy.data.objects.new('L26_LampEmitter',None);C.objects.link(emitter);emitter.parent=root;emitter.location=(0,0,7.43)
emitter['purpose']='Reserved future pilot +1/+2 beam origin. No movement rule or negative-step effect implemented.'
bpy.context.view_layer.update()
report={'pid':os.getpid(),'port':9891,'source':bpy.data.filepath,'collection':C.name,
 'objects':len(C.objects),'meshes':len([o for o in C.objects if o.type=='MESH']),
 'markers':[o.name for o in C.objects if o.type=='EMPTY'],'placement_pending':True,
 'legacy_reference_images_used':False,'design_basis':'Actual current town/terminal material system and construction dimensions',
 'raw_vertices':sum(len(o.data.vertices) for o in C.objects if o.type=='MESH')}
(LOG/'build_first.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
