import bpy
exec(compile('''
assert not (LOG/'roof_revision.json').exists(),'Do not replay roof revision'
old=[o.name for o in C.objects if any(o.name.startswith('TN25_'+q) for q in ['Entrance','MainLower','MainUpper','SmallTower'])]
for name in old:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
def up_panel(name,vs,fs,role='roof',thick=.025):
 o=mesh(name,vs,fs,role)
 bm=bmesh.new();bm.from_mesh(o.data)
 for f in bm.faces:
  if f.normal.z<0:f.normal_flip()
 bm.to_mesh(o.data);bm.free();o.data.update()
 mod=o.modifiers.new('Closed slate thickness','SOLIDIFY');mod.thickness=thick;mod.offset=-1
 return o
def hip_roof(name,cx,cy,w,d,eave,rise,hip,rows):
 W=w/2;D=d/2
 def rz(t):return eave+rise*(1-t)**1.7+.08*t**5
 def sidep(s,t,u,lift=0):
  a=cy-D+hip*(1-t);b=cy+D-hip*(1-t)
  return (cx+s*W*t,a+(b-a)*u,rz(t)+lift)
 def endp(s,t,u,lift=0):return (cx+W*t*u,cy+s*(D-hip*(1-t)),rz(t)+lift)
 for s in [-1,1]:
  vs=[]
  for i in range(17):
   for u in [0,1]:vs.append(sidep(s,i/16,u))
  up_panel(name+'SideDeck',vs,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(16)],thick=.075)
  vs=[endp(s,0,0)]
  for i in range(1,17):
   for u in [-1,1]:vs.append(endp(s,i/16,u))
  fs=[(0,1,2)]+[(1+2*(i-1),2+2*(i-1),2+2*i,1+2*i) for i in range(1,16)]
  up_panel(name+'HipDeck',vs,fs,thick=.075)
  columns=max(5,round(d/.34))
  for i in range(rows):
   ta=i/rows;tb=(i+1)/rows
   for j in range(columns):
    ua=(j+.012)/columns;ub=(j+1-.012)/columns
    vs=[sidep(s,t,u,.035) for t in [ta,(ta+tb)/2,tb] for u in [ua,ub]]
    up_panel(name+'SideSlate',vs,[(0,1,3,2),(2,3,5,4)])
   n=max(2,round(w*(i+1)/rows/.34))
   for j in range(n):
    ua=-1+2*(j+.012)/n;ub=-1+2*(j+1-.012)/n
    if i==0:
     vs=[endp(s,0,0,.038),endp(s,tb,ua,.038),endp(s,tb,ub,.038)];fs=[(0,1,2)]
    else:
     vs=[endp(s,t,u,.038) for t in [ta,(ta+tb)/2,tb] for u in [ua,ub]];fs=[(0,1,3,2),(2,3,5,4)]
    up_panel(name+'HipSlate',vs,fs)
  for side in [-1,1]:
   pts=[endp(s,i/16,side,.065) for i in range(17)]
   T(name+'CurvedHipTrim',pts,.085,'wood',4)
  B(name+'FrontFascia',(cx,cy+s*D,eave+.015),(w+.12,.12,.16),'wood',.012)
  B(name+'SideFascia',(cx+s*W,cy,eave+.015),(.12,d+.12,.16),'wood',.012)
 T(name+'RidgeCap',[(cx,cy-D+hip-.055,eave+rise+.065),(cx,cy+D-hip+.055,eave+rise+.065)],.075,'roof',8)
hip_roof('Entrance',-4.9,23.53,2.28,1.18,4.08,1.13,.46,4)
hip_roof('MainLower',-4.9,25.35,4.16,3.86,6.85,2.20,.96,7)
hip_roof('MainUpper',-4.9,25.50,2.65,3.22,8.30,1.95,.70,7)
hip_roof('SmallTower',1.45,25.275,3.25,3.65,5.60,1.95,.82,6)
o=bpy.data.objects['TN25_UpperTowerBody'];o.location.z=7.72
for v in o.data.vertices:v.co.z*=1.16/.94
o.data.update()
for o in C.objects:
 if o.name.startswith('TN25_UpperTowerPost'):
  o.location.z=7.83
  for v in o.data.vertices:v.co.z*=1.02/1.16
  o.data.update()
 if o.name.startswith('TN25_GalleryRoofTile'):
  bm=bmesh.new();bm.from_mesh(o.data)
  for f in bm.faces:
   if f.normal.z<0:f.normal_flip()
  bm.to_mesh(o.data);bm.free();o.data.update()
  for m in o.modifiers:
   if m.type=='SOLIDIFY':m.offset=-1
# Close the low gallery roof with a slate underdeck and its supported rear edge.
up_panel('GalleryRoofDeck',[(-3.11,23.83,4.53),(.18,23.83,4.53),(.18,26.40,5.25),(-3.11,26.40,5.25)],[(0,1,2,3)],thick=.09)
B('GalleryRearRoofBeam',(-1.475,26.31,5.13),(3.28,.16,.20),'wood',.012)
wall('GalleryUpperRear',1,26.27,-3.05,.10,4.52,5.20,[],'plaster')
# Anchor sits fully below its window, as in the reference.
anchor=[o for o in C.objects if o.get('terminal_detail_group')=='anchor']
for o in anchor:o.location.z-=.62
# Small cloth badges and broad brick repairs keep the facade readable at game scale.
for name,cx,cy,ztop,w,h in [('Main',-4.9,23.35,5.23,.44,.62),('Small',1.45,23.34,4.30,.34,.49)]:
 pts=[(cx-w/2,cy,ztop),(cx+w/2,cy,ztop),(cx+w/2,cy,ztop-h*.72),(cx,cy,ztop-h),(cx-w/2,cy,ztop-h*.72)]
 o=mesh(name+'HarborBadge',pts,[(0,1,2,3,4)],'canvas');s=o.modifiers.new('Badge cloth','SOLIDIFY');s.thickness=.014
 B(name+'BadgeStripe',(cx,cy-.012,ztop-h*.37),(.045,.018,h*.72),'red',.002)
 B(name+'BadgeCross',(cx,cy-.014,ztop-h*.25),(w,.018,.045),'red',.002)
 L(name+'BadgeRod',(cx-w*.65,cy,ztop+.025),(cx+w*.65,cy,ztop+.025),.035,'brass')
for cx,cy,z in [(-6.23,23.59,3.07),(-3.51,23.59,5.0),(.46,23.59,2.66),(2.42,23.59,3.05)]:
 for k in range(3):B('WallBrickRepair',(cx+(k%2)*.14,cy,z+(k//2)*.095),(.22,.035,.074),'brick',.005)
bpy.context.view_layer.update()
(LOG/'roof_revision.json').write_text(json.dumps({'old_roof_objects_removed':len(old),'new_roofs':'four curved slate hipped roofs, closed side and end decks; upward facing tiles','anchor_lowered_m':.62,'gallery_back_closed':True,'objects':len(C.objects)},indent=2),encoding='utf8')
print('TN25_ROOF_REVISION',len(C.objects))
''','terminal25_09_roofs.py','exec'),bpy.app.driver_namespace['terminal25'])
