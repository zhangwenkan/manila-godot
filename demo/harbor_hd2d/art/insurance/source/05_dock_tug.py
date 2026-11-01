from pathlib import Path
import sys, math, random
sys.path.insert(0,str(Path(__file__).parent))
from model_lib import *
root=activate()
assert root.get('crane_complete') and not root.get('dock_complete')
for name in ['INS_DeckBlockout','INS_WatersidePier','INS_TugBlockout','INS_TugCabinBlockout']:
    obj=bpy.data.objects[name]
    assert obj in list(root.children_recursive)
    bpy.data.objects.remove(obj,do_unlink=True)
dock=bpy.data.objects['Dock']; props=bpy.data.objects['Props']; tug=bpy.data.objects['Tug']
rng=random.Random(1408)
# Staggered timber deck with physical seams and a stable substructure.
for row in range(25):
    y=-3.60+row*.30
    joints=[-6.7,-2.25,2.25,6.7] if row%2==0 else [-6.7,-4.15,.30,4.75,6.7]
    for left,right in zip(joints,joints[1:]):
        box('INS_DeckPlank',((left+right)/2,y,.53+rng.uniform(-.004,.004)),(right-left-.018,.28,.10),'INS_Wood',dock,.007)
for y in [-3.73,3.73]:
    box('INS_DockEdgeBeam',(0,y,.32),(13.56,.20,.36),'INS_Wood',dock,.023)
for x in [-6.69,6.69]:
    box('INS_DockEdgeBeam',(x,0,.32),(.20,7.40,.36),'INS_Wood',dock,.023)
for x in [-6.44,-3.2,0,3.2,6.44]:
    for y in [-3.56,3.56]:
        cylinder('INS_DockPile',(x,y,.08),.17,1.04,'INS_Wood',dock,10)
        cylinder('INS_PileCap',(x,y,.60),.20,.09,'INS_Iron',dock,10)
        ring('INS_PileBand',(x,y,.15),.173,.022,'INS_Iron',dock,'XY',12)
for i in range(7):
    box('INS_PierPlank',(-7.72,-3.14+i*.255,.54),(2.04,.238,.11),'INS_Wood',dock,.007)
for y in [-3.27,-1.48]:
    box('INS_PierSideBeam',(-7.72,y,.34),(2.23,.13,.27),'INS_Wood',dock)
    cylinder('INS_PierPile',(-8.65,y,.05),.14,1.0,'INS_Wood',dock,10)
# Bollards and two mooring lines stay out of the gameplay standing ring.
for y in [-3.10,-1.65]:
    cylinder('INS_BollardBase',(-8.5,y,.635),.17,.11,'INS_Iron',props)
    cylinder('INS_BollardPost',(-8.5,y,.79),.07,.27,'INS_Iron',props)
    cylinder('INS_BollardCrossbar',(-8.5,y,.91),.05,.40,'INS_Iron',props,10,(0,1,0))

def crate(x,y,z,size):
    g=group('INS_StackedCrate',props)
    box('INS_CrateBody',(x,y,z),(size,size,size),'INS_Wood',g)
    for dx in [-.42,.42]:
        for dy in [-.51,.51]:
            box('INS_CrateStrap',(x+dx*size,y+dy*size,z),(.09*size,.05*size,size),'INS_Cream',g,.003)
    for dy in [-.51,.51]:
        beam('INS_CrateBrace',(x-size*.40,y+dy*size,z-size*.40),(x+size*.4,y+dy*size,z+size*.4),.075*size,'INS_Wood',g,bevel=.005)
    return g
for x,y,s in [(3.45,-2.7,.72),(4.3,-2.7,.72),(3.9,-2.67,.65),(5.4,-1.8,.68)]:
    crate(x,y,.58+s/2+(.72 if x==3.9 else 0),s)
for x,y in [(5.8,-2.85),(6.0,-1.65)]:
    cylinder('INS_Drum',(x,y,.98),.27,.80,'INS_Red',props,16)
    for z in [.63,.82,1.18,1.34]:
        ring('INS_DrumRim',(x,y,z),.276,.027,'INS_Iron',props,'XY',16)
    cylinder('INS_DrumTop',(x,y,1.39),.258,.018,'INS_Iron',props,16)
    cylinder('INS_DrumBung',(x+.1,y,1.414),.04,.027,'INS_Cream',props,8)
# Working-boat proportions; the bow points along Blender -Y / Godot +Z.
tug.location=(-9.82,-2.80,0)
outline=[(0,-1.78),(.32,-1.53),(.51,-1.05),(.56,-.45),(.55,.82),(.43,1.54),(-.43,1.54),(-.55,.82),(-.56,-.45),(-.51,-1.05),(-.32,-1.53)]

def hull_band(name,z0,z1,s0,s1,mat,cap0=False,cap1=False):
    n=len(outline)
    vertices=[(x*s,y*s,z) for z,s in [(z0,s0),(z1,s1)] for x,y in outline]
    faces=[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    if cap0: faces.append(tuple(reversed(range(n))))
    if cap1: faces.append(tuple(range(n,2*n)))
    return mesh(name,vertices,faces,mat,tug,.012)
hull_band('INS_TugLowerHull',-.28,-.04,.63,.91,'INS_BoatRed',True)
hull_band('INS_TugRedWaterline',-.04,.09,.91,.985,'INS_BoatRed')
hull_band('INS_TugBlueHull',.09,.43,.985,1.0,'INS_Blue')
slab('INS_TugDeck',[(x*.93,y*.96,.435) for x,y in outline],.065,'INS_Wood',tug)
tube('INS_TugGunwale',[(x,y,.46) for x,y in outline+[outline[0]]],.044,'INS_Dark',tug)
# White wheelhouse with blue inset window panes, drip cap and framed rear door.
box('INS_TugCabinBase',(0,-.29,.71),(.85,1.03,.46),'INS_Cream',tug,.035)
box('INS_TugCabinUpper',(0,-.29,1.08),(.79,.97,.40),'INS_Cream',tug,.025)
box('INS_TugCabinRoof',(0,-.29,1.32),(.99,1.18,.12),'INS_Cream',tug,.035)
for x in [-.198,.198]:
    box('INS_TugWindshield',(x,-.791,1.105),(.30,.035,.255),'INS_Glass',tug,.007)
for x in [-.406,.406]:
    for y in [-.53,-.08]:
        box('INS_TugSideWindow',(x,y,1.105),(.025,.30,.255),'INS_GlassLight',tug,.007)
box('INS_TugDoor',(0,.22,.82),(.38,.034,.56),'INS_Trim',tug,.013)
box('INS_TugDoorPane',(0,.24,.97),(.27,.018,.18),'INS_Glass',tug,.004)
# Red aft engine cover and black-capped funnel.
box('INS_TugEngineHatch',(0,.82,.66),(.76,.94,.37),'INS_BoatRed',tug,.033)
for i in range(5):
    box('INS_HatchVent',(0,.51+i*.125,.861),(.50,.042,.025),'INS_Dark',tug,.003)
cylinder('INS_TugFunnel',(.14,.51,1.10),.11,.76,'INS_BoatRed',tug)
cylinder('INS_TugFunnelCap',(.14,.51,1.47),.13,.16,'INS_Dark',tug)
beam('INS_TugMast',(-.15,-.12,1.37),(-.15,-.12,2.10),.038,'INS_Iron',tug,bevel=.004)
beam('INS_TugMastCrossbar',(-.40,-.12,1.88),(.09,-.12,1.88),.027,'INS_Iron',tug,bevel=.003)
cylinder('INS_TugLamp',(-.15,-.12,2.12),.053,.10,'INS_Cream',tug,8)
for side in [-1,1]:
    for y in [-.75,.68]:
        ring('INS_TugTyre',(side*.571,y,.275),.145,.043,'INS_Dark',tug,'YZ',16)
        tube('INS_TyreRope',[(side*.57,y,.51),(side*.63,y,.35)],.013,'INS_Rope',tug,6)
for y in [-1.29,1.24]:
    cylinder('INS_TugCleat',(0,y,.51),.036,.12,'INS_Iron',tug,8)
    beam('INS_TugCleatBar',(-.12,y,.57),(.12,y,.57),.034,'INS_Iron',tug,bevel=.003)
# Lines are dock props, not part of the decorative boat's water-clearance envelope.
tube('INS_BowMooring',[(-9.82,-4.09,.58),(-9.10,-3.7,.38),(-8.5,-3.10,.93)],.017,'INS_Rope',props,6)
tube('INS_SternMooring',[(-9.82,-1.56,.58),(-9.15,-1.5,.35),(-8.5,-1.65,.93)],.017,'INS_Rope',props,6)
# Give surfaces stable, dimension-based UVs: board grain no longer stretches per box.
for obj in root.children_recursive:
    if obj.type!='MESH' or not obj.data.uv_layers or not obj.data.materials: continue
    mat=obj.data.materials[0].name
    if mat not in ['INS_Wall','INS_Wood','INS_Tin']: continue
    uv=obj.data.uv_layers.active
    for poly in obj.data.polygons:
        normal=obj.matrix_basis.to_3x3()@poly.normal
        axis=max(range(3),key=lambda i:abs(normal[i]))
        for index in poly.loop_indices:
            p=obj.matrix_basis@obj.data.vertices[obj.data.loops[index].vertex_index].co
            if mat=='INS_Wall':
                coord=((p.y if axis==0 else p.x)/1.96,p.z/3.0)
            elif mat=='INS_Wood':
                coord=(p.x/3.0,(p.y if axis==2 else p.z)/2.4)
            else:
                coord=(p.y/1.6,p.x/2.3)
            uv.data[index].uv=coord
root['dock_complete']=True
bpy.context.view_layer.update()
print('DOCK_AND_TUG_DETAILED',len(dock.children_recursive),len(tug.children_recursive),'total',len(root.children_recursive))
