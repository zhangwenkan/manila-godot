import bpy
assert 'terminal25' in bpy.app.driver_namespace
exec(compile('''
assert not any(o.name.startswith('TN25_MainFloor') for o in C.objects),'Do not replay building'
# Whole complex is newly made from the user drawing, with the current town palette.
floor=1.85
sites=[('Main',-4.9,25.35,3.7,3.3,7.0),('Small',1.45,25.275,2.7,3.15,5.6)]
for name,x,y,w,d,top in sites:
 front=y-d/2;back=y+d/2
 B(name+'Floor',(x,y,floor-.09),(w+.08,d+.08,.18),'deck',.015)
 B(name+'BuriedFooting',(x,y,1.35),(w+.24,d+.18,.55),'stone',.018)
 doorhole=[(x-.70,x+.70,1.86,4.05)] if name=='Main' else []
 windowhole=(x-.70,x+.70,5.05,6.35) if name=='Main' else (x-.62,x+.62,4.08,5.08)
 wall(name+'Front',1,front,x-w/2,x+w/2,1.95,top,doorhole+[windowhole])
 wall(name+'Back',1,back,x-w/2,x+w/2,1.95,top,[(x-.56,x+.56,3.8,4.85)],'plaster')
 for side in [-1,1]:
  plane=x+side*w/2;holes=[(y-.53,y+.53,3.0,4.2)]
  wall(name+'Side',0,plane,front,back,1.95,top,holes)
  window(name+'SideWindow',plane,y,3.6,1.06,1.2,side=side)
  for yy in [front-.045,back+.045]:B(name+'CornerPost',(plane,yy,(1.85+top)/2),(.18,.18,top-1.85+.15),'wood',.013)
  for zz in [2.35,4.48,top-.12]:B(name+'SideBeam',(plane+side*.04,y,zz),(.17,d+.16,.17),'wood',.012)
 for yy in [front-.055,back+.055]:
  for zz in [2.35,4.48,top-.12]:B(name+'FacadeBeam',(x,yy,zz),(w+.20,.17,.17),'wood',.012)
  # Two clear courses of foundation, larger blocks than the timber details.
  count=max(4,round(w/.66))
  for row in range(2):
   for i in range(count):
    px=x-w/2+(i+.5)*w/count
    if name=='Main' and yy<y and abs(px-x)<.75:continue
    B(name+'FoundationBlock',(px,yy,1.88+row*.24),(w/count-.018,.24,.225),'stone',.021)
 window(name+'FrontWindow',x,front-.025,(windowhole[2]+windowhole[3])/2,windowhole[1]-windowhole[0],windowhole[3]-windowhole[2])
 window(name+'RearWindow',x,back+.03,4.325,1.12,1.05,side=2)
# Principal doorway is deep in its real opening, with a small curved porch.
x=-4.9;y=23.7
for i in range(6):B('DoorPlank',(x-.60+(i+.5)*.20,y+.06,2.92),(.194,.095,2.0),'wood',.007)
for s in [-1,1]:B('DoorJamb',(x+s*.78,y-.10,2.94),(.17,.24,2.20),'wood',.013)
B('DoorLintel',(x,y-.10,4.08),(1.73,.24,.18),'wood',.014)
for zz in [2.22,3.65]:B('DoorBrace',(x,y-.015,zz),(1.27,.055,.10),'beam',.006)
for sx in [-1,1]:T('DoorRing',[(x+sx*.13+.055*math.cos(a*math.tau/12),y-.09,2.94+.055*math.sin(a*math.tau/12)) for a in range(13)],.012,'brass',6)
for sx in [-1,1]:B('PorchPost',(x+sx*.94,23.15,2.96),(.15,.16,2.30),'wood',.014)
roof('Entrance',x,23.53,2.28,1.18,4.08,1.13,rows=4)
# Two superimposed curved roofs form the high tower silhouette.
roof('MainLower',-4.9,25.35,4.16,3.86,6.85,2.20,rows=7)
B('UpperTowerBody',(-4.9,25.50,8.22),(2.17,2.70,.94),'ivory',.01)
for sx in [-1,1]:
 for yy in [24.12,26.88]:B('UpperTowerPost',(-4.9+sx*1.12,yy,8.30),(.14,.15,1.16),'wood',.01)
roof('MainUpper',-4.9,25.5,2.65,3.22,8.30,1.95,rows=6)
roof('SmallTower',1.45,25.275,3.25,3.65,5.60,1.95,rows=6)
# Low gallery connects the towers with a recessed working counter and real passage.
gx=-1.475;gy=25.15;gw=3.15;gd=2.25
B('GalleryFloor',(gx,gy,1.77),(gw,gd,.16),'deck',.014)
B('GalleryFoundation',(gx,gy,1.40),(gw,gd,.56),'stone',.018)
wall('GalleryRear',1,26.27,-3.05,.10,1.95,4.55,[(-2.12,-.92,2.80,3.85)],'plaster')
window('GalleryRearWindow',gx,26.31,3.32,1.20,1.05,side=2)
for xx in [-3.01,.06]:B('GalleryFrontPost',(xx,24.02,3.15),(.17,.18,2.65),'wood',.014)
B('GalleryHeader',(gx,24.01,4.48),(3.26,.20,.24),'wood',.015)
B('CounterBack',(gx,25.88,2.54),(2.5,.12,1.25),'wood',.012)
for k in range(8):B('CounterBoard',(-2.70+k*.35,24.60,2.22),(.34,.08,.68),'wood',.008)
B('WorkingCounter',(gx,24.58,2.61),(2.96,.67,.11),'deck',.014)
for xx in [-2.76,-.22]:B('CounterLeg',(xx,24.62,2.16),(.10,.36,.70),'beam',.009)
# A shallow, curved lean-to in the same slate; the gallery stays visibly lower.
for j in range(11):
 xx=-3.10+j*.295
 for k in range(5):
  ya=23.84+k*.50;yb=ya+.56;za=4.55+(ya-23.84)*.28;zb=4.55+(yb-23.84)*.28
  o=mesh('GalleryRoofTile',[(xx,ya,za),(xx+.288,ya,za),(xx+.288,yb,zb),(xx,yb,zb)],[(0,1,2,3)],'roof');m=o.modifiers.new('Slate lip','SOLIDIFY');m.thickness=.035
B('GalleryEave',(gx,23.81,4.53),(3.35,.15,.20),'wood',.015)
# New landward porch meets the preserved deck by broad, usable five-rise stairs.
for j in range(36):B('FrontPorchPlank',(-7.25+(j+.5)*10.5/36,23.19,1.79),(10.5/36-.008,.90,.12),'deck',.008)
for xx in [-7.24,-4.9,-2.1,.25,3.20]:
 B('PorchFoundation',(xx,23.33,1.40),(.32,.62,.72),'stone',.025)
 B('PorchSupportBeam',(xx,23.20,1.65),(.14,.96,.18),'beam',.01)
for xx,width in [(-4.9,2.15),(-1.0,2.0),(1.65,2.0)]:
 for k in range(5):
  top=.95+(k+1)*.18;yy=21.65+k*.265
  B('WideEntryStep',(xx,yy,top-.065),(width,.29,.13),'deck',.012)
  for s in [-1,1]:B('StepBearing',(xx+s*(width*.5-.12),yy,(.93+top-.13)/2),(.16,.25,max(.05,top-.13-.93)),'beam',.006)
# Boundaries are useful work edges, with openings aligned to the three stairs.
for xa,xb in [(-7.28,-6.04),(-3.73,-2.15),(.13,.55),(2.75,3.25)]:
 for xx in [xa,xb]:B('PorchRailPost',(xx,22.76,2.28),(.105,.105,.86),'wood',.01)
 for zz in [2.0,2.65]:L('PorchRail',(xa,22.76,zz),(xb,22.76,zz),.065,'wood')
# Rear face includes a retained hillside wall, still within the new building plot.
B('RearRetainingWall',(-.60,27.12,2.36),(7.00,.27,2.12),'stone',.018)
for i in range(10):B('RetainingCap',(-3.77+i*.70,27.12,3.46),(.68,.39,.12),'stone',.018)
bpy.context.view_layer.update()
(LOG/'building_stage.json').write_text(json.dumps({'objects':len(C.objects),'floor':floor,'sites':sites,'new_geometry_only':True}),encoding='utf8')
print('NEW_TOWN_TERMINAL_BUILT',len(C.objects))
''','terminal25_03_buildings.py','exec'),bpy.app.driver_namespace['terminal25'])
