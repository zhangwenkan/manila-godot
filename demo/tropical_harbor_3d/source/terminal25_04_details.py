"""New TN25 details. Execute only through the owned Blender MCP session.

Uses the current-round terminal25 namespace; does not load any old terminal asset.
The caller owns PID/file/port guards and saving/export. This is a one-shot pass.
"""
import bpy

exec(r'''
import math, json
import bpy

_tn25_collection = bpy.data.collections['Reference_Terminal']
assert not _tn25_collection.get('terminal25_details_started', False), 'TN25 details already started; inspect before retrying'
_tn25_collection['terminal25_details_started'] = True
_tn25_details_before = set(_tn25_collection.objects)
_tn25_detail_groups = {}

def _tn25_tag_since(before, label):
    group = sorted(set(_tn25_collection.objects) - before, key=lambda ob: ob.name)
    for ob in group:
        ob['terminal_detail_group'] = label
        ob['terminal25_detail_pass'] = True
    _tn25_detail_groups[label] = [ob.name for ob in group]
    return group

def _tn25_circle(name, center, radius, tube_radius, role, plane='XZ', sides=20):
    x,y,z=center
    pts=[]
    for i in range(sides+1):
        a=math.tau*i/sides
        if plane=='XZ':pts.append((x+radius*math.cos(a),y,z+radius*math.sin(a)))
        elif plane=='XY':pts.append((x+radius*math.cos(a),y+radius*math.sin(a),z))
        else:pts.append((x,y+radius*math.cos(a),z+radius*math.sin(a)))
    return T(name,pts,tube_radius,role,8)

def _tn25_front_prism(name, polygon_xz, front_y, depth, role):
    # A closed extrusion: front normal points towards -Y, back towards +Y.
    n=len(polygon_xz)
    area=sum(polygon_xz[i][0]*polygon_xz[(i+1)%n][1]-polygon_xz[(i+1)%n][0]*polygon_xz[i][1] for i in range(n))
    poly=list(polygon_xz if area>0 else reversed(polygon_xz))
    vs=[(x,front_y,z) for x,z in poly]+[(x,front_y+depth,z) for x,z in poly]
    fs=[tuple(range(n)),tuple(range(2*n-1,n-1,-1))]
    for i in range(n):
        j=(i+1)%n
        fs.append((i,n+i,n+j,j))
    return mesh(name,vs,fs,role)

def _tn25_pulley(name, x,y,z, radius=.14):
    # Visible wheel plane is XZ; two clevis straps retain the actual spindle.
    _tn25_circle(name+'_Rim',(x,y,z),radius,.027,'iron')
    T(name+'_Hub',[(x,y-.14,z),(x,y+.14,z)],.045,'brass',10)
    for a in (0,math.pi/2):
        L(name+'_Spoke',(x-math.cos(a)*radius*.80,y,z-math.sin(a)*radius*.80),
          (x+math.cos(a)*radius*.80,y,z+math.sin(a)*radius*.80),.035,'iron')
    for yy in (y-.115,y+.115):
        B(name+'_Clevis',(x,yy,z+.15),(.075,.035,.34),'iron',.007)

# Left wall hoist. Its complete support and payload remain on the terminal work side.
_before=set(_tn25_collection.objects)
L('HoistMast',(-6.96,24.20,1.84),(-6.96,24.20,6.10),.22,'beam')
L('HoistArm',(-6.96,24.20,5.83),(-9.02,24.20,5.83),.21,'wood')
L('HoistLowerBrace',(-6.96,24.20,3.66),(-8.66,24.20,5.73),.16,'wood')
for zz in (2.22,3.75,5.51):
    B('HoistWallPlate',(-6.78,24.20,zz),(.065,.46,.24),'iron',.01)
    L('HoistWallSpacer',(-6.80,24.20,zz),(-6.99,24.20,zz),.14,'beam')
    B('HoistMastStrap',(-6.96,24.20,zz),(.255,.255,.065),'iron',.007)
    for yy in (24.04,24.36):
        T('HoistWallBolt',[(-6.84,yy,zz),(-6.90,yy,zz)],.025,'brass',8)
for xx in (-7.14,-8.70):
    B('HoistArmBand',(xx,24.20,5.83),(.075,.245,.245),'iron',.007)
T('HoistTopStay',[(-6.96,24.20,6.08),(-7.68,24.20,5.97),(-8.86,24.20,5.92)],.021,'rope',8)
_tn25_pulley('HoistOuterPulley',-8.78,24.20,5.59,.15)
_tn25_pulley('HoistInnerPulley',-7.02,24.20,5.59,.105)
# The drum axle runs into the two support cheeks, with its crank outside.
T('HoistDrum',[(-7.00,23.92,3.06),(-7.00,24.48,3.06)],.17,'wood',12)
for yy in (23.90,24.50):
    T('HoistDrumFlange',[(-7.00,yy-.024,3.06),(-7.00,yy+.024,3.06)],.225,'iron',14)
    B('HoistDrumCheek',(-7.00,yy,2.95),(.34,.07,.48),'beam',.012)
T('HoistDrumAxle',[(-7.00,23.71,3.06),(-7.00,24.63,3.06)],.038,'brass',10)
L('HoistCrank',(-7.00,23.69,3.06),(-7.00,23.69,2.78),.055,'iron')
T('HoistCrankGrip',[(-7.00,23.66,2.78),(-7.00,23.49,2.78)],.052,'wood',10)
for i in range(7):
    _tn25_circle('HoistDrumRope',(-7.00,24.02+i*.055,3.06),.181,.018,'rope')
T('HoistFeedRope',[(-7.04,24.20,3.22),(-7.13,24.20,4.42),(-7.13,24.20,5.53),
                   (-7.10,24.20,5.64),(-7.02,24.20,5.70),(-7.00,24.20,5.70),
                   (-8.67,24.20,5.70),(-8.78,24.20,5.75),(-8.90,24.20,5.69),
                   (-8.94,24.20,5.59),(-8.91,24.20,5.48),(-8.80,24.20,5.43),
                   (-8.78,24.20,3.61)],.018,'rope',8)
_tn25_circle('HoistHookEye',(-8.78,24.20,3.53),.081,.023,'iron',sides=16)
T('HoistHook',[(-8.78,24.20,3.45),(-8.77,24.20,3.35),(-8.69,24.20,3.27),
              (-8.60,24.20,3.30),(-8.58,24.20,3.38)],.038,'iron',10)
_tn25_tag_since(_before,'crane_fixed')

# Three short timber lengths, supported by two closed wraps and four rising sling legs.
_before=set(_tn25_collection.objects)
_logs=[(-8.93,2.32),(-8.63,2.32),(-8.78,2.58)]
for i,(xx,zz) in enumerate(_logs):
    T('HoistedTimber',[(xx,23.51,zz),(xx,24.89,zz)],.145,'wood',12)
    for yy in (23.502,24.898):
        _tn25_circle('TimberEndRing',(xx,yy,zz),.080,.0045,'beam',sides=14)
for yy in (23.75,24.64):
    wrap=[(-9.085,yy,2.32),(-9.06,yy,2.20),(-8.93,yy,2.16),(-8.63,yy,2.16),
          (-8.50,yy,2.20),(-8.475,yy,2.32),(-8.56,yy,2.52),(-8.65,yy,2.68),
          (-8.78,yy,2.745),(-8.91,yy,2.68),(-9.00,yy,2.52),(-9.085,yy,2.32)]
    T('TimberClosedBinding',wrap,.022,'rope',8)
    for xx in (-8.98,-8.58):
        T('TimberSlingLeg',[(xx,yy,2.53),(-8.78,24.20,3.23),(-8.67,24.20,3.29)],.021,'rope',8)
_tn25_tag_since(_before,'hoisted_load')

# Solid iron anchor: ring, shank, stock, curved arms and broad pointed flukes.
_before=set(_tn25_collection.objects)
_tn25_circle('AnchorEye',(1.45,23.42,4.54),.165,.045,'iron',sides=22)
_tn25_front_prism('AnchorShank',[(1.38,4.40),(1.52,4.40),(1.53,3.14),(1.45,3.03),(1.37,3.14)],23.35,.14,'iron')
B('AnchorStock',(1.45,23.42,4.12),(1.04,.16,.115),'iron',.018)
for side in (-1,1):
    pts=[(1.45,23.42,3.10),(1.45+side*.22,23.42,3.13),(1.45+side*.43,23.42,3.27),
         (1.45+side*.59,23.42,3.48),(1.45+side*.64,23.42,3.62)]
    T('AnchorCurvedArm',pts,.080,'iron',10)
    polygon=[(1.45+side*.46,3.60),(1.45+side*.75,3.84),(1.45+side*.72,3.47)]
    _tn25_front_prism('AnchorFluke',polygon,23.32,.20,'iron')
T('AnchorWallHook',[(1.45,23.69,4.65),(1.45,23.39,4.65),(1.45,23.35,4.58)],.035,'iron',8)
for xx,zz in ((1.45,4.65),(1.45,3.14)):
    B('AnchorWallMount',(xx,23.665,zz),(.15,.045,.15),'iron',.013)
_tn25_tag_since(_before,'anchor')

# A single sagging rope between the towers; six restrained, closed cloth pennants.
_before=set(_tn25_collection.objects)
def _tn25_flagline(t):
    return (-3.0+3.1*t,24.0,7.1-1.1*t-.23*4*t*(1-t))
T('BuntingRope',[_tn25_flagline(i/24) for i in range(25)],.016,'rope',8)
for t in (0.0,1.0):
    xx,yy,zz=_tn25_flagline(t)
    T('BuntingWallPin',[(xx,yy+.12,zz),(xx,yy-.04,zz)],.025,'iron',8)
_tn25_tag_since(_before,'bunting_rope')
for i in range(6):
    _before=set(_tn25_collection.objects)
    tc=(i+1)/7;half=.050
    a=_tn25_flagline(tc-half);b=_tn25_flagline(tc);c=_tn25_flagline(tc+half)
    h=.40+.035*(i%3)
    front=[a,b,c,(a[0]+.072,23.94,a[2]-.18),(c[0]-.072,23.95,c[2]-.18),
           (b[0]+.035,23.90,b[2]-h)]
    vs=front+[(x,y+.012,z) for x,y,z in front]
    faces=[(0,3,1),(1,3,4),(1,4,2),(3,5,4),
           (6,7,9),(7,10,9),(7,8,10),(9,10,11)]
    outline=[0,1,2,4,5,3]
    for j in range(len(outline)):
        q=outline[j];r=outline[(j+1)%len(outline)]
        faces.append((q,r,r+6,q+6))
    mesh('Pennant',vs,faces,'red' if i in (1,4) else 'canvas')
    for pt in (a,c):
        T('PennantTie',[(pt[0],pt[1]+.02,pt[2]+.025),(pt[0],pt[1]-.035,pt[2]-.045)],.009,'rope',6)
    _tn25_tag_since(_before,'pennant_%02d'%(i+1))

# Small vane above the right tower; readable silhouette, no oversized crown.
_before=set(_tn25_collection.objects)
T('VaneMast',[(1.45,25.20,7.48),(1.45,25.20,8.62)],.036,'wood',10)
for zz in (7.63,8.20,8.52):
    _tn25_circle('VaneCollar',(1.45,25.20,zz),.074,.017,'brass','XY',16)
T('VaneArrowShaft',[(.92,25.20,8.43),(1.98,25.20,8.43)],.025,'iron',8)
_tn25_front_prism('VaneArrow',[(.85,8.43),(1.10,8.57),(1.10,8.29)],25.17,.06,'roof')
_tn25_front_prism('VaneTail',[(1.75,8.32),(1.98,8.32),(1.91,8.43),(1.98,8.54),(1.75,8.54)],25.17,.06,'roof')
_tn25_front_prism('VaneBird',[(1.34,8.65),(1.38,8.59),(1.51,8.59),(1.59,8.65),
                             (1.63,8.71),(1.54,8.69),(1.48,8.74),(1.39,8.74),(1.39,8.69)],25.17,.055,'roof')
_tn25_front_prism('VaneBeak',[(1.34,8.68),(1.28,8.66),(1.34,8.64)],25.17,.055,'brass')
_tn25_tag_since(_before,'weather_vane')

# Four small lanterns attached to their actual wall planes.
def _tn25_lantern(name, x,y,z, wall_y):
    L(name+'_WallArm',(x,wall_y,z+.22),(x,y,z+.22),.035,'iron')
    B(name+'_WallPlate',(x,wall_y-.012,z+.12),(.12,.035,.22),'iron',.008)
    _tn25_circle(name+'_Ring',(x,y,z+.20),.050,.012,'brass',sides=14)
    B(name+'_Pane',(x,y,z),(.145,.125,.23),'canvas',.008)
    for zz in (-.145,.145):
        B(name+'_Cap',(x,y,z+zz),(.22,.20,.04),'iron',.014)
    for dx in (-.088,.088):
        for dy in (-.075,.075):
            L(name+'_Corner',(x+dx,y+dy,z-.13),(x+dx,y+dy,z+.13),.019,'brass')
    B(name+'_Crossrail',(x,y-.081,z-.015),(.18,.018,.020),'brass',.003)
for i,(x,y,z,wall_y) in enumerate([(-6.22,23.40,3.95,23.70),(-2.65,23.75,3.95,24.05),
                                  (-.25,23.75,3.95,24.05),(2.42,23.40,4.75,23.70)]):
    _before=set(_tn25_collection.objects)
    _tn25_lantern('Lantern_%02d'%(i+1),x,y,z,wall_y)
    _tn25_tag_since(_before,'lantern_%02d'%(i+1))

# Small service shelf in the low gallery, plus one bound barrel in its side bay.
_before=set(_tn25_collection.objects)
B('ServiceShelfTop',(-1.48,23.63,2.67),(1.48,.46,.075),'deck',.014)
for xx in (-2.08,-.88):
    for yy in (23.48,23.80):
        L('ServiceShelfLeg',(xx,yy,1.85),(xx,yy,2.63),.055,'beam')
B('ServiceShelfLower',(-1.48,23.63,2.08),(1.36,.39,.05),'wood',.01)
for i in range(4):
    xx=-1.96+i*.28;yy=23.67;h=.24+.035*(i%3)
    T('ServiceBottleBody',[(xx,yy,2.71),(xx,yy,2.71+h*.70)],.052,'glass',10)
    T('ServiceBottleShoulder',[(xx,yy,2.71+h*.70),(xx,yy,2.71+h*.78)],.039,'glass',10)
    T('ServiceBottleNeck',[(xx,yy,2.71+h*.78),(xx,yy,2.71+h)],.021,'glass',8)
    T('ServiceBottleStopper',[(xx,yy,2.71+h),(xx,yy,2.73+h)],.023,'wood',8)
for i in range(3):
    _tn25_circle('ShelfRopeCoil',(-1.06,23.60,2.72+i*.018),.095+i*.009,.012,'rope','XY',18)
_tn25_tag_since(_before,'service_shelf')

_before=set(_tn25_collection.objects)
bx,by,bottom=-7.45,25.54,1.85
levels=[(0,.26),(.12,.29),(.43,.325),(.74,.29),(.86,.26)]
vs=[]
for zz,rad in levels:
    for i in range(12):
        a=math.tau*i/12;vs.append((bx+rad*math.cos(a),by+rad*math.sin(a),bottom+zz))
faces=[tuple(range(11,-1,-1)),tuple(48+i for i in range(12))]
for j in range(4):
    for i in range(12):
        k=j*12+i;n=j*12+(i+1)%12
        faces.append((k,n,n+12,k+12))
mesh('WorkBarrel',vs,faces,'wood')
for zz,rad in ((.15,.299),(.70,.302)):
    _tn25_circle('WorkBarrelHoop',(bx,by,bottom+zz),rad,.026,'iron','XY',20)
T('BarrelBung',[(bx+.04,by-.03,bottom+.86),(bx+.04,by-.03,bottom+.88)],.042,'beam',10)
_tn25_tag_since(_before,'work_barrel')

_tn25_new=set(_tn25_collection.objects)-_tn25_details_before
_tn25_collection['terminal25_details_complete']=True
detail_report={'status':'created','objects':len(_tn25_new),'groups':_tn25_detail_groups,
               'source':'New details from user 2D reference and current town materials; no old terminal import',
               'animation_created':False,'left_load_floor_gap_m':.325,
               'note':'Static authored assemblies only; support, scene clearance and rendered appearance require final live audit.'}
print('TN25_DETAILS '+json.dumps(detail_report,ensure_ascii=False))
''', bpy.app.driver_namespace['terminal25'])
