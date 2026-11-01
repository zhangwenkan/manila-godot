"""Create a new locked reference and complete stepped office through local MCP."""
from pathlib import Path
import sys
import math
import json
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rebuild_lib import *

verify_input()
assert SCENE not in bpy.data.scenes
assert 'Insurance_R2_Reference' not in bpy.data.scenes
with preserve_session():
    before={'filepath':bpy.data.filepath,'scene':bpy.context.scene.name,'selected':[o.name for o in bpy.context.selected_objects]}
    reference=bpy.data.scenes.new('Insurance_R2_Reference'); switch(reference)
    prior=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(INPUT))
    imported=list(set(bpy.data.objects)-prior)
    for obj in imported:
        obj.hide_select=True; obj['reference_only']=True
    reference['input_sha256']=SHA
    # Reference is kept raw; rebuilding uses its overall side-by-side layout and the image.
    scene=bpy.data.scenes.new(SCENE); switch(scene)
    scene.unit_settings.system='METRIC'
    b=Model(scene); bpy.app.driver_namespace['insurance_r2_builder']=b
    b.root['visual_status']='Full reconstruction draft; not approved'
    b.root['front']='Blender -Y; glTF +Z'
    b.root['rear_design']='Inferred complete rear; source image shows front only'
    cx=-2.45; left=-6.05; right=1.15; front=-1.30; rear=3.45; base=.62; eave=3.12

    def wall_with_openings(name,y,openings,back=False):
        xs=sorted(set([left,right]+[a for h in openings for a in [h[0],h[1]]]))
        zs=sorted(set([base,eave]+[a for h in openings for a in [h[2],h[3]]]))
        for i,(xa,xb) in enumerate(zip(xs,xs[1:])):
            for j,(za,zb) in enumerate(zip(zs,zs[1:])):
                x=(xa+xb)/2; z=(za+zb)/2
                if any(h[0]<x<h[1] and h[2]<z<h[3] for h in openings): continue
                b.box(name+f'_{i}_{j}',(x,y,z),(xb-x,.20,zb-za),'Office','wall')
    # Real apertures, not one front rectangle with decorative windows on top.
    wall_with_openings('Facade',front,[(-4.65,-3.85,1.45,2.25),(-3.10,-1.22,1.46,2.48),(-.67,.42,.62,2.47)])
    wall_with_openings('RearWall',rear,[(-4.95,-3.70,1.52,2.47),(-1.10,.15,1.52,2.47)],True)
    for x,name in [(left,'WestWall'),(right,'EastWall')]:
        b.box(name,(x,(front+rear)/2,(base+eave)/2),(.20,rear-front,eave-base),'Office','wall')
    b.box('EnclosedFloor',(cx,(front+rear)/2,.66),(7.2,rear-front,.16),'Office','wood')
    for y,name in [(front,'FrontGable'),(rear,'RearGable')]:
        b.prism(name,[(left,eave),(right,eave),(cx,4.55)],y-.10,y+.10,'Office','wall')
    for x in [left+.03,right-.03]:
        for y in [front-.12,rear+.12]:
            b.box('CornerTrim'+str((x,y)),(x,y,1.88),(.11,.10,2.62),'Office',mat='WallDark')
    for y in [front-.13,rear+.13]:
        b.box('BaseBeam'+str(y),(cx,y,.70),(7.30,.11,.18),'Office',mat='WoodDark')
        b.box('Lintel'+str(y),(cx,y,3.08),(7.28,.12,.16),'Office',mat='WallDark')
    b.window('LeftWindow',-4.25,front,1.85,.80,.80,small=True)
    b.window('CounterWindow',-2.16,front,1.97,1.88,1.02)
    for x in [-4.325,-.475]: b.window('RearWindow'+str(x),x,rear,1.995,1.25,.95,back=True)
    b.box('DoorRecess',(-.125,front+.12,1.57),(1.09,.14,1.90),'Office',mat='Ink')
    b.box('DoorWood',(-.125,front+.025,1.53),(.91,.09,1.76),'Office','wood')
    b.box('DoorGlass',(-.125,front-.035,2.00),(.63,.035,.49),'Office',mat='Glass')
    b.box('DoorGlassReflection',(-.18,front-.057,2.15),(.44,.012,.055),'Office',mat='GlassLight')
    for x in [-.675,.425]: b.box('DoorJamb'+str(x),(x,front-.085,1.59),(.10,.16,1.98),'Office',mat='WoodDark')
    b.box('DoorHeader',(-.125,front-.085,2.55),(1.20,.16,.12),'Office',mat='Wood')
    b.box('DoorHandle',(.16,front-.085,1.35),(.055,.08,.19),'Office',mat='Cream')
    for i in range(3):
        b.box('EntranceStep'+str(i),(-.125,front-.63+i*.17,.67+i*.10),(1.35,.74-i*.17,.15),'Office','wood')
    b.box('CounterSill',(-2.16,front-.27,1.39),(2.10,.37,.13),'Office',mat='WoodDark')
    for name,x,w,z,mat in [('CounterAwning',-2.16,2.10,2.61,'Wood'),('DoorAwning',-.125,1.32,2.80,'WallLight')]:
        awning=b.box(name,(x,front-.25,z),(w,.62,.13),'Office',mat=mat); awning.rotation_euler.x=math.radians(10)
        b.box(name+'Edge',(x,front-.565,z-.055),(w+.04,.07,.10),'Office',mat='Ink')
        for i in range(int(w/.22)):
            xx=x-w/2+.11+i*.22
            b.box(name+'Seam'+str(i),(xx,front-.30,z+.07),(.022,.48,.018),'Office',mat='WoodDark' if mat=='Wood' else 'WallDark')
    b.sign('InsuranceSign',(cx,front-.21,3.77),5.15,.91,(8,8,248,56),'Office')
    b.window('GableVent',cx,front-.02,4.36,.51,.44,small=True)

    def roof(name,width,y0,y1,low,high,solid=False):
        x0=cx-width/2; x1=cx+width/2
        if solid:
            # Upper tiers are closed masses down to the lower roof, not floating facades.
            b.prism(name+'EnclosedTier',[(x0,low-.65),(x1,low-.65),(x1,low-.08),(cx,high-.13),(x0,low-.08)],y0+.12,y1-.12,'Office','wall')
        for side,(xa,xb,za,zb) in enumerate([(x0,cx,low,high),(cx,x1,high,low)]):
            verts=[(xa,y0,za-.14),(xb,y0,zb-.14),(xb,y1,zb-.14),(xa,y1,za-.14),(xa,y0,za),(xb,y0,zb),(xb,y1,zb),(xa,y1,za)]
            b.mesh(name+'Plate'+str(side),verts,FACES,'Roof','roof',uv_axis=(0,1,0))
            for y,label in [(y0-.015,'Front'),(y1+.015,'Rear')]:
                b.beam(name+label+'Fascia'+str(side),(xa,y,za-.06),(xb,y,zb-.06),.105,.17,group='Roof',mat='Ink')
                b.beam(name+label+'FasciaLight'+str(side),(xa,y-.025,za+.008),(xb,y-.025,zb+.008),.033,.06,group='Roof',mat='SteelLight')
            xx=xa if side==0 else xb; zz=za if side==0 else zb
            b.box(name+'Eave'+str(side),(xx,(y0+y1)/2,zz-.05),(.12,y1-y0,.14),'Roof',mat='Steel')
        b.box(name+'Ridge',(cx,(y0+y1)/2,high+.025),(.11,y1-y0+.12,.095),'Roof',mat='Steel')

    roof('LowerRoof',7.46,-1.60,3.66,3.23,4.80)
    roof('MiddleRoof',5.82,.36,3.72,4.15,5.56,True)
    roof('HighRoof',3.48,1.68,3.79,5.28,6.30,True)
    # Side and rear furnishings establish a designed exterior on every side.
    for x,name in [(left-.14,'West'),(right+.14,'East')]:
        b.box(name+'SideUtilityBox',(x,1.50,1.43),(.20,.76,.87),'Office',mat='WoodDark')
        for i in range(4): b.box(name+'UtilitySlat'+str(i),(x+(-.12 if x<0 else .12),1.50,1.16+i*.18),(.03,.64,.06),'Office',mat='Wood')
    for x in [left+.15,right-.15]:
        b.cable('RearDrain'+str(x),[(x,rear+.19,3.12),(x,rear+.19,1.0),(x+.12,rear+.30,.70)],.045,group='Office',mat='Steel')
    scene['office_complete']=True
    scene['source_reference']='User image 6.png and local generated GLB; hidden rear is inferred'
    bpy.context.view_layer.update()
    fresh(SOURCE/'reference_record.json').write_text(json.dumps({'input_sha256':SHA,'original_session':before,'raw_reference_objects':[o.name for o in imported],'office_footprint':[left,right,front,rear],'rear':'Inferred fully enclosed; not claimed exact to unseen reference'},indent=2),encoding='utf-8')
    print('R2_OFFICE_BUILT',len(b.parts),'editable parts; front, back, side walls and three roof tiers')
verify_input()
