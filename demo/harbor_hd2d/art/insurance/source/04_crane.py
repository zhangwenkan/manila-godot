from pathlib import Path
import sys, math
sys.path.insert(0,str(Path(__file__).parent))
from model_lib import *
root=activate()
assert root.get('office_complete') and not root.get('crane_complete')
crane=bpy.data.objects['Crane']
obj=bpy.data.objects['INS_BoomBlockout']
assert obj.parent==crane
bpy.data.objects.remove(obj,do_unlink=True)
# Four bolted feet, horizontal ties and open triangular bracing.
for x in [2.5,5.5]:
    for y in [.15,2.35]:
        box('INS_CraneFoot',(x,y,.72),(.66,.64,.22),'INS_Stone',crane,.025)
        box('INS_BasePlate',(x,y,.865),(.48,.48,.055),'INS_Iron',crane,.007)
        for dx in [-.18,.18]:
            for dy in [-.18,.18]:
                cylinder('INS_AnchorBolt',(x+dx,y+dy,.919),.029,.055,'INS_Cream',crane,6)
        for z in [3.4,5.45,6.47]:
            box('INS_GussetPlate',(x,y-.15,z),(.47,.045,.40),'INS_Red',crane,.008)
            for dx in [-.15,.15]:
                cylinder('INS_GussetRivet',(x+dx,y-.186,z),.027,.025,'INS_Iron',crane,8,(0,-1,0))
    for lo,hi in [(.95,3.35),(3.5,6.35)]:
        beam('INS_SideDiagonal',(x,.15,lo),(x,2.35,hi),.13,'INS_Red',crane)
        beam('INS_SideDiagonal',(x,2.35,lo),(x,.15,hi),.13,'INS_Red',crane)
    for z in [3.40,5.45,6.47]:
        beam('INS_SideCrossbeam',(x,-.04,z),(x,2.54,z),.22,'INS_Red',crane)
for y in [.15,2.35]:
    for z in [3.4,5.5]:
        beam('INS_FrontCrossbeam',(2.5,y,z),(5.5,y,z),.22,'INS_Red',crane)
    # Lower knees leave an open cargo passage instead of a wall of X beams.
    beam('INS_PortalKnee',(2.5,y,2.25),(3.6,y,3.4),.18,'INS_Red',crane)
    beam('INS_PortalKnee',(5.5,y,2.25),(4.4,y,3.4),.18,'INS_Red',crane)
    for i in range(4):
        x=2.5+i*.75
        beam('INS_UpperTruss',(x,y,5.5 if i%2==0 else 6.5),(x+.75,y,6.5 if i%2==0 else 5.5),.115,'INS_Red',crane)
# Open service deck, railings and ladder.
box('INS_ServiceDeck',(4,1.18,3.48),(3.60,2.94,.17),'INS_Iron',crane)
for x in [2.20,5.80]:
    for y in [-.28,.52,1.40,2.62]:
        beam('INS_ServiceRailPost',(x,y,3.56),(x,y,4.20),.045,'INS_Iron',crane)
    for z in [3.86,4.20]:
        beam('INS_ServiceSideRail',(x,-.28,z),(x,2.62,z),.043,'INS_Iron',crane)
for z in [3.86,4.20]:
    beam('INS_ServiceBackRail',(2.2,2.62,z),(5.8,2.62,z),.043,'INS_Iron',crane)
for x in [5.27,5.75]:
    beam('INS_LadderRail',(x,-.49,.78),(x,-.49,4.1),.043,'INS_Iron',crane)
for i in range(12):
    beam('INS_LadderRung',(5.27,-.49,.84+i*.27),(5.75,-.49,.84+i*.27),.037,'INS_Iron',crane)
# Operator cabin: genuine framed window band with solid lower panels.
cabin=group('INS_OperatorCabin',crane)
box('INS_CabinLower',(4.28,1.33,3.85),(1.87,1.67,.57),'INS_Red',cabin)
box('INS_CabinFloor',(4.28,1.33,3.58),(1.97,1.77,.11),'INS_Iron',cabin)
box('INS_CabinRoof',(4.28,1.33,4.91),(2.10,1.89,.15),'INS_Tin',cabin)
for x in [3.35,5.21]:
    for y in [.495,2.165]:
        box('INS_CabinWindowPost',(x,y,4.52),(.095,.095,.76),'INS_Red',cabin)
for y in [.51,2.15]:
    box('INS_CabinWindow',(4.28,y,4.52),(1.75,.04,.65),'INS_Glass',cabin)
    box('INS_CabinMullion',(4.28,y-.03,4.52),(.06,.08,.71),'INS_Cream',cabin)
    for z in [4.15,4.86]:
        box('INS_CabinRail',(4.28,y,z),(1.91,.12,.08),'INS_Red',cabin)
for x in [3.36,5.2]:
    box('INS_CabinSideGlass',(x,1.33,4.52),(.04,1.55,.65),'INS_GlassLight',cabin)
# Winch drum and cable wound between solid flanges.
for x in [3.5,4.15]:
    cylinder('INS_WinchFlange',(x,1.24,6.81),.29,.085,'INS_Red',crane,16,(1,0,0))
cylinder('INS_WinchDrum',(3.825,1.24,6.81),.19,.59,'INS_Iron',crane,16,(1,0,0))
for i in range(10):
    ring('INS_CableWinding',(3.57+i*.055,1.24,6.81),.205,.025,'INS_Rope',crane,'YZ',16)
# Two parallel triangular boom trusses, cross-braced along their length.
a=Vector((4.0,.7,6.65)); b=Vector((1.55,-1.2,7.96))
span=b-a
lateral=Vector((-span.y,span.x,0)).normalized()*.20
for side in [-1,1]:
    offset=lateral*side
    beam('INS_BoomLowerChord',a+offset,b+offset,.095,'INS_Red',crane)
    beam('INS_BoomUpperChord',a+offset+Vector((0,0,.32)),b+offset+Vector((0,0,.12)),.09,'INS_Red',crane)
    for i in range(5):
        t=i/5; u=(i+1)/5
        p=a.lerp(b,t)+offset; q=a.lerp(b,u)+offset
        height=.32-.20*(t if i%2==0 else u)
        if i%2==0: p.z+=height
        else: q.z+=height
        beam('INS_BoomLattice',p,q,.06,'INS_Red',crane,bevel=.005)
for t in [0,.2,.4,.6,.8,1]:
    p=a.lerp(b,t)
    beam('INS_BoomCrossTie',p-lateral,p+lateral,.065,'INS_Red',crane)
for p in [a,b]:
    cylinder('INS_BoomPivot',p,.16,.58,'INS_Iron',crane,16,lateral.normalized())
# Head sheave, continuous hoist cable, block and hooked end.
ring('INS_HeadSheave',b,.16,.035,'INS_Cream',crane,'XZ')
tube('INS_HoistCable',[(3.8,1.24,7.01),(3.85,.70,7.05),(1.57,-1.20,8.12),(1.43,-1.20,7.96),(1.43,-1.20,2.54)],.022,'INS_Dark',crane)
tube('INS_ReturnCable',[(1.70,-1.20,7.96),(1.70,-1.20,2.54)],.021,'INS_Dark',crane)
box('INS_HookBlock',(1.565,-1.20,2.42),(.36,.22,.32),'INS_Red',crane,.06)
cylinder('INS_HookBlockPin',(1.565,-1.345,2.42),.07,.065,'INS_Iron',crane,12,(0,-1,0))
tube('INS_CargoHook',[(1.565,-1.20,2.27),(1.565,-1.20,2.12),(1.43,-1.20,2.04),(1.36,-1.20,1.91),(1.43,-1.20,1.80),(1.59,-1.20,1.80),(1.69,-1.20,1.91),(1.68,-1.20,2.02)],.054,'INS_Iron',crane)
box('INS_CraneSignBacking',(4.0,-.102,5.43),(3.37,.15,.64),'INS_Red',crane)
box('INS_CraneSignFace',(4.0,-.190,5.43),(3.17,.045,.48),'INS_Cream',crane,.006)
text('INS_CargoCraneLettering','CARGO CRANE',(4.0,-.219,5.43),2.88,'INS_Dark',crane)
# Close the visible clerestory sides and the sloping ends of each low wing.
office=bpy.data.objects['Office']
for x in [-3.59,-.01]:
    box('INS_ClerestorySide',(x,1.95,3.42),(.15,2.70,.42),'INS_Wall',office)
for left,right,zl,zr in [(-5.6,-3.6,2.77,3.18),(0,1.7,3.29,3.02)]:
    base=2.73 if left<0 else 2.93
    for y in [.60,3.16]:
        vertices=[(left,y,base),(right,y,base),(right,y,zr),(left,y,zl),(left,y+.14,base),(right,y+.14,base),(right,y+.14,zr),(left,y+.14,zl)]
        mesh('INS_WingRoofClosure',vertices,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],'INS_Wall',office,.004)
root['crane_complete']=True
bpy.context.view_layer.update()
print('CRANE_DETAILED',len(crane.children_recursive))
