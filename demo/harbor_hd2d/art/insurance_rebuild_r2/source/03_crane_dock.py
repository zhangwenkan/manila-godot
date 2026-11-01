"""Build the spatial crane, timber dock and restrained props through local MCP."""
from pathlib import Path
import sys
import math
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rebuild_lib import *

verify_input()
b=current_model()
assert b.scene.get('office_complete') and not b.scene.get('crane_complete')
with preserve_session():
    switch(b.scene)
    # Four I-section posts and depth beams: a gantry, not a flat portal facade.
    xleft,xright=2.55,5.95
    yfront,yrear=.15,2.55
    for ix,x in enumerate([xleft,xright]):
        for iy,y in enumerate([yfront,yrear]):
            tag=f'Post_{ix}_{iy}'
            b.box(tag+'Web',(x,y,3.52),(.13,.44,5.76),'Crane',texture='red')
            for dx in [-.19,.19]:
                b.box(tag+'Flange'+str(dx),(x+dx,y,3.52),(.10,.51,5.76),'Crane',texture='red')
                b.box(tag+'Edge'+str(dx),(x+dx-.038,y-.266,3.52),(.034,.026,5.72),'Crane',mat='RedLight')
            b.box(tag+'Foot',(x,y,.70),(.68,.77,.18),'Crane',mat='Steel')
            b.box(tag+'FootRim',(x,y,.79),(.52,.61,.10),'Crane',mat='RedDark')
            for dx in [-.25,.25]:
                for dy in [-.28,.28]:
                    b.cylinder(tag+'Anchor'+str((dx,dy)),(x+dx,y+dy,.80),.04,.065,'Crane',mat='SteelLight',sides=6)
    for y,name in [(yfront,'Front'),(yrear,'Rear')]:
        b.beam(name+'Header',(2.30,y,6.26),(6.20,y,6.26),.37,.48,texture='red')
        b.beam(name+'Crossbar',(2.55,y,3.18),(5.95,y,3.18),.23,.28,texture='red')
        for side,(xa,xb) in enumerate([(2.64,4.25),(5.86,4.25)]):
            b.beam(name+'BraceShadow'+str(side),(xa,y+.04,3.37),(xb,y+.04,5.92),.31,.20,mat='Ink')
            b.beam(name+'Brace'+str(side),(xa,y-.09,3.37),(xb,y-.09,5.92),.20,.14,texture='red')
            b.beam(name+'BraceEdge'+str(side),(xa-.045,y-.175,3.39),(xb-.045,y-.175,5.90),.034,.025,mat='RedLight')
        b.beam(name+'MidTie',(3.0,y-.10,3.80),(5.5,y-.10,3.80),.16,.18,texture='red')
        for x in [2.80,5.70]:
            b.box(name+'JointPlate'+str(x),(x,y-.225,3.32),(.34,.06,.36),'Crane',mat='RedDark')
    for x,name in [(xleft,'Left'),(xright,'Right')]:
        b.beam(name+'DepthGirder',(x,yfront,6.30),(x,yrear,6.30),.32,.28,texture='red')
        b.beam(name+'SideKnee',(x,yfront,5.13),(x,1.40,6.22),.17,.17,texture='red')
        b.beam(name+'RearKnee',(x,yrear,5.25),(x,1.55,6.22),.17,.17,texture='red')
    b.box('MachineryDeck',(4.05,1.40,6.43),(5.42,2.84,.23),'Crane',texture='red')
    b.box('PlatformFrontRim',(4.05,-.045,6.44),(5.53,.105,.14),'Crane',mat='Ink')
    b.box('PlatformFrontHighlight',(4.05,-.108,6.51),(5.36,.025,.038),'Crane',mat='RedLight')
    b.box('PlatformRearRim',(4.05,2.86,6.44),(5.53,.10,.14),'Crane',mat='RedDark')
    b.sign('CargoCraneSign',(4.25,-.185,5.98),3.38,.71,(264,8,504,56),'Crane')
    # A raised diagonal boom, pivot, pulley, stay lines and hanging hook.
    pivot=Vector((4.05,1.47,6.66)); tip=Vector((1.56,1.47,8.39))
    b.beam('BoomWeb',pivot,tip,.29,.47,texture='red')
    for y,name in [(1.18,'Front'),(1.76,'Back')]:
        a=(pivot.x,y,pivot.z); c=(tip.x,y,tip.z)
        b.beam('Boom'+name+'Outline',a,c,.36,.11,mat='Ink')
        b.beam('Boom'+name+'Flange',(a[0],y-.03,a[2]+.025),(c[0],y-.03,c[2]+.025),.25,.09,texture='red')
    for index,t in enumerate([.18,.42,.67,.89]):
        p=pivot.lerp(tip,t)
        b.box('BoomCrossRib'+str(index),(p.x,1.47,p.z),(.13,.67,.16),'Crane',mat='RedDark')
    b.beam('BoomMast',(1.56,1.49,6.59),(1.56,1.49,8.33),.18,.22,texture='red')
    b.cylinder('BoomTipPulley',(1.56,1.43,8.36),.24,.26,'Crane',mat='Ink',axis='Y')
    b.cylinder('BoomTipHub',(1.56,1.255,8.36),.15,.12,'Crane',mat='RedLight',axis='Y')
    b.cylinder('BoomPivot',(4.05,1.47,6.68),.26,.83,'Crane',mat='Steel',axis='Y')
    b.cylinder('BoomPivotCap',(4.05,.99,6.68),.115,.10,'Crane',mat='SteelLight',axis='Y')
    b.cable('LongBackStay',[(1.59,1.52,8.50),(6.13,2.31,6.64)],.031)
    b.cable('ShortMastStay',[(1.52,1.52,8.29),(.86,1.52,6.55)],.03)
    b.cable('BoomHoistLine',[(1.70,1.28,8.42),(3.73,1.20,6.96)],.026,mat='Steel')
    b.cable('HangingLiftLine',[(1.35,1.27,8.33),(1.35,1.27,4.51)],.030)
    b.box('HookBlock',(1.35,1.27,4.41),(.26,.26,.36),'Crane',mat='WoodDark')
    b.box('HookBlockFace',(1.35,1.12,4.41),(.18,.04,.25),'Crane',mat='Wood')
    b.cable('Hook',[(1.35,1.27,4.25),(1.35,1.27,4.08),(1.46,1.27,3.98),(1.60,1.27,4.02),(1.64,1.27,4.13)],.055,mat='Steel')
    for y in [1.04,1.97]:
        b.prism('WinchCheek'+str(y),[(3.77,6.58),(4.64,6.58),(4.64,6.97),(4.43,7.20),(3.97,7.20),(3.77,6.97)],y,y+.12,'Crane',mat='Steel')
    b.cylinder('WinchDrum',(4.21,1.57,6.95),.28,.72,'Crane',mat='Rope',axis='Y')
    for y in [1.23,1.9]: b.cylinder('WinchFlange'+str(y),(4.21,y,6.95),.34,.075,'Crane',mat='Steel',axis='Y')
    b.cylinder('WinchAxle',(4.21,.995,6.95),.115,.08,'Crane',mat='SteelLight',axis='Y')
    b.box('OperatorBoxOutline',(6.34,.52,6.75),(1.20,1.0,1.04),'Crane',mat='Ink')
    b.box('OperatorBox',(6.34,.49,6.77),(1.10,.99,.94),'Crane',texture='red')
    b.box('OperatorPanel',(6.34,-.025,6.62),(.91,.045,.49),'Crane',mat='Cream')
    b.box('OperatorPanelInset',(6.26,-.055,6.66),(.45,.025,.26),'Crane',mat='WoodDark')
    for i in range(3): b.box('OperatorSwitch'+str(i),(6.57,-.058,6.56+i*.09),(.07,.033,.04),'Crane',mat='Steel')
    b.beam('OperatorKnee',(5.96,.54,5.79),(6.81,.54,6.32),.18,.16,texture='red')
    # Back maintenance ladder and a short rear guard rail, away from the front silhouette.
    for x in [5.18,5.62]: b.beam('LadderRail'+str(x),(x,2.95,.92),(x,2.95,6.77),.048,.048,mat='Steel')
    for i in range(17): b.beam('LadderRung'+str(i),(5.18,2.95,1.05+i*.33),(5.62,2.95,1.05+i*.33),.034,.034,mat='SteelLight')
    for x in [3.15,4.05,4.95]: b.beam('RearGuardUpright'+str(x),(x,2.80,6.57),(x,2.80,7.14),.055,.055,mat='RedDark')
    b.beam('RearGuardRail',(3.15,2.80,7.14),(4.95,2.80,7.14),.060,.060,mat='RedDark')

    # A thick, finished timber platform with four fascia sides and support pilings.
    for ix in range(2):
        for iy in range(2):
            b.box('DockDeck'+str((ix,iy)),(-3.60+ix*7.20,-1.80+iy*3.60,.43),(7.20,3.60,.36),'Dock',texture='wood')
    for ix in range(2):
        for y in [-3.64,3.64]:
            b.box('DockFascia'+str((ix,y)),(-3.60+ix*7.20,y,.36),(7.20,.14,.43),'Dock',texture='wood')
            b.box('DockRim'+str((ix,y)),(-3.60+ix*7.20,y,.64),(7.20,.15,.07),'Dock',mat='WoodDark')
    for x in [-7.22,7.22]:
        b.box('DockSideFascia'+str(x),(x,0,.36),(.14,7.28,.43),'Dock',texture='wood')
        b.box('DockSideRim'+str(x),(x,0,.64),(.15,7.28,.07),'Dock',mat='WoodDark')
    for x in [-6.65,-.15,6.6]:
        for y in [-3.69,3.62]:
            b.cylinder('MooringPile'+str((x,y)),(x,y,.47),.18,1.70,'Dock',mat='WoodDark',sides=8)
            b.cylinder('MooringPileCap'+str((x,y)),(x,y,1.31),.16,.06,'Dock',mat='WoodLight',sides=8)
            b.box('PileGrain'+str((x,y)),(x-.04,y-.175,.89),(.04,.022,.61),'Dock',mat='Wood')
    for x in [-5.0,1.5,5.5]:
        b.cylinder('RearSupport'+str(x),(x,2.8,.05),.19,.92,'Dock',mat='WoodDark',sides=8)

    def crate(name,x,y,z,size=.65):
        b.box(name+'Body',(x,y,z+size/2),(size,size,size),'Props',texture='wood')
        for dx in [-1,1]:
            for yy in [y-size/2-.018,y+size/2+.018]:
                b.box(name+'Stile'+str((dx,yy)),(x+dx*(size/2-.06),yy,z+size/2),(.09,.05,size+.04),'Props',mat='WoodDark')
        for zz in [z+.05,z+size-.05]:
            b.box(name+'Rail'+str(zz),(x,y-size/2-.035,zz),(size,.065,.09),'Props',mat='WoodLight')
        b.beam(name+'Diagonal',(x-size*.33,y-size/2-.073,z+.14),(x+size*.33,y-size/2-.073,z+size-.14),.064,.05,group='Props',mat='Wood')
    for spec in [('LeftCrate',-5.38,-1.98,.62,.67),('LeftStack',-5.30,-1.91,1.29,.57),('LeftLow',-4.63,-2.18,.62,.52),('DoorCrate',-1.30,-2.65,.62,.51),('EastTall',1.60,-.62,.62,.74),('EastStack',1.60,-.62,1.36,.65),('RearCrate',-5.88,3.02,.62,.64),('CraneCrate',5.32,1.96,.62,.65)]: crate(*spec)

    def barrel(name,x,y,z,r=.29,h=.73):
        sides=12; rings=[(0,r*.80),(.10*h,r*.95),(.48*h,r),(h*.9,r*.94),(h,r*.80)]
        vertices=[(x+rr*math.cos(i*math.tau/sides),y+rr*math.sin(i*math.tau/sides),z+zz) for zz,rr in rings for i in range(sides)]
        faces=[tuple(reversed(range(sides))),tuple(range(4*sides,5*sides))]
        for j in range(4):
            for i in range(sides): faces.append((j*sides+i,j*sides+(i+1)%sides,(j+1)*sides+(i+1)%sides,(j+1)*sides+i))
        obj=b.mesh(name+'Staves',vertices,faces,'Props',mat='Wood')
        for material in ['WoodDark','WoodLight']: obj.data.materials.append(b.materials[material])
        for face in obj.data.polygons:
            if face.index>1: face.material_index=1 if face.index%5==0 else 0
        for i,zz in enumerate([.14,.58]): b.cylinder(name+'Hoop'+str(i),(x,y,z+zz),r*.988,.075,'Props',mat='Steel',sides=12)
        b.cylinder(name+'Lid',(x,y,z+h+.01),r*.76,.022,'Props',mat='WoodDark',sides=12)
    barrel('EastBarrel',1.86,-1.76,.62)
    barrel('EastSmallBarrel',1.33,-1.47,.62,.23,.61)
    barrel('CraneBarrel',6.55,1.37,.62)
    barrel('RearBarrel',-5.95,2.12,.62,.26,.67)
    b.cable('CoiledMooringRope',[(-6.1,-2.63,.68),(-6.45,-2.68,.69),(-6.52,-2.97,.70),(-6.23,-3.10,.70),(-5.97,-2.91,.72),(-6.14,-2.72,.72)],.065,group='Props',mat='Rope')
    b.scene['crane_complete']=True
    bpy.context.view_layer.update()
    print('R2_CRANE_DOCK_BUILT',len(b.parts),'total editable parts; spatial gantry with boom, cables, hook, deck and pilings')
verify_input()
