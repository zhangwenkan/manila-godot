"""Add a closed tug hull and cabin, then save/export only this reconstructed scene."""
from pathlib import Path
import sys
import math
import json
import bpy
import bmesh
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rebuild_lib import *

verify_input()
b=current_model()
assert b.scene.get('crane_complete') and not b.scene.get('export_complete')
for path in [SOURCE/'insurance_r2_library.blend',ASSET/'insurance_rebuild_r2.glb',SOURCE/'build_record.json']:
    fresh(path)
with preserve_session():
    switch(b.scene)
    # Tug plan: flat stern at the dock, a continuous round/pointed bow toward the viewer.
    cx=-3.70; cy=-5.83
    plan=[(-.95,1.84),(.95,1.84),(1.17,1.45),(1.28,.55),(1.24,-.67),(.94,-1.43),(.49,-1.89),(0,-2.08),(-.49,-1.89),(-.94,-1.43),(-1.24,-.67),(-1.28,.55),(-1.17,1.45)]
    n=len(plan)
    rings=[(.68,-.16),(.79,.03),(.91,.21),(1.0,.87),(1.0,1.05)]
    vertices=[(cx+x*s,cy+y*s,z+(.08 if y<-1.3 else 0)) for s,z in rings for x,y in plan]
    faces=[tuple(reversed(range(n))),tuple(range((len(rings)-1)*n,len(rings)*n))]
    for j in range(len(rings)-1):
        for i in range(n): faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    hull=b.mesh('TugClosedHull',vertices,faces,'Tug',mat='Hull')
    for mat in ['Ink','RedDark','HullLight','Wood']: hull.data.materials.append(b.materials[mat])
    for face in hull.data.polygons:
        if face.index==0: face.material_index=1
        elif face.index==1: face.material_index=4
        else: face.material_index=[1,2,0,3][(face.index-2)//n]
    # Thin deck inside the gunwale; hull remains a real closed volume below it.
    deck=b.mesh('TugDeck',[(cx+x*.91,cy+y*.94,z) for z in [.98,1.025] for x,y in plan],[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],'Tug',texture='wood')
    gunwale=[(cx+x,cy+y,1.09+(.08 if y<-1.3 else 0)) for x,y in plan]
    # The closure is segmented, avoiding a duplicated-end ring on a capped tube.
    for i in range(n): b.beam('TugGunwale'+str(i),gunwale[i],gunwale[(i+1)%n],.105,.105,group='Tug',mat='Ink')
    b.box('TugCabinShadow',(cx,-4.88,1.61),(1.47,1.36,1.18),'Tug',mat='Ink')
    b.box('TugCabin',(cx,-4.89,1.64),(1.33,1.27,1.11),'Tug',mat='Cream')
    b.box('TugCabinRoof',(cx,-4.88,2.23),(1.53,1.46,.15),'Tug',mat='CreamLight')
    b.box('TugCabinRoofRim',(cx,-4.88,2.31),(1.45,1.38,.045),'Tug',mat='Steel')
    for i in [-1,0,1]:
        x=cx+i*.40
        b.box('CabinFrontWindowFrame'+str(i),(x,-5.543,1.89),(.32,.06,.33),'Tug',mat='Ink')
        b.box('CabinFrontWindow'+str(i),(x,-5.580,1.89),(.23,.025,.23),'Tug',mat='Glass')
        b.box('CabinFrontGlint'+str(i),(x-.025,-5.597,1.97),(.14,.015,.025),'Tug',mat='GlassLight')
    for side in [-1,1]:
        x=cx+side*.69
        b.box('CabinSideWindowFrame'+str(side),(x,-4.93,1.86),(.045,.64,.38),'Tug',mat='Ink')
        b.box('CabinSideWindow'+str(side),(x+side*.03,-4.93,1.86),(.022,.53,.27),'Tug',mat='Glass')
        b.box('CabinSideGlint'+str(side),(x+side*.044,-4.93,1.96),(.016,.40,.034),'Tug',mat='GlassLight')
    b.box('CabinRearDoor',(cx,-4.229,1.54),(.61,.042,.87),'Tug',mat='WoodDark')
    b.box('CabinRearGlass',(cx,-4.202,1.77),(.40,.022,.31),'Tug',mat='Glass')
    b.box('CabinRoofHatchFrame',(cx,-4.91,2.35),(.76,.72,.12),'Tug',mat='Ink')
    b.box('CabinRoofHatch',(cx,-4.91,2.42),(.62,.60,.06),'Tug',mat='Cream')
    b.box('CabinRoofHatchGlass',(cx,-4.91,2.46),(.46,.43,.025),'Tug',mat='GlassLight')
    b.box('TugEngineBoxDark',(cx,-6.22,1.35),(.97,1.24,.67),'Tug',mat='Ink')
    b.box('TugEngineBox',(cx,-6.22,1.37),(.86,1.15,.65),'Tug',mat='Red')
    for i in range(7):
        b.box('EngineTopVent'+str(i),(cx,-6.69+i*.14,1.703),(.68,.045,.021),'Tug',mat='RedDark')
        b.box('EngineFrontSlat'+str(i),(cx,-6.808,1.14+i*.073),(.68,.022,.031),'Tug',mat='RedLight')
    b.cylinder('TugFunnel',(cx,-4.24,2.49),.12,.64,'Tug',mat='Ink',sides=8)
    b.cylinder('TugFunnelCap',(cx,-4.24,2.81),.17,.06,'Tug',mat='Steel',sides=8)
    b.beam('TugMast',(cx,-4.20,2.43),(cx,-4.20,3.10),.055,.055,group='Tug',mat='Steel')
    b.beam('TugMastBar',(cx-.32,-4.20,2.95),(cx+.32,-4.20,2.95),.048,.048,group='Tug',mat='Steel')
    for side in [-1,1]:
        for i,y in enumerate([-4.54,-5.61,-6.60]):
            x=cx+side*(1.20 if i<2 else 1.13)
            b.box('TugFenderOutline'+str((side,i)),(x,y,.93),(.16,.29,.56),'Tug',mat='Ink')
            b.box('TugFenderRubber'+str((side,i)),(x+side*.03,y,.93),(.16,.17,.42),'Tug',mat='Steel')
        b.cable('TugSideRail'+str(side),[(cx+side*.89,-4.12,1.12),(cx+side*1.04,-4.35,1.54),(cx+side*1.12,-5.8,1.47)],.04,group='Tug',mat='Steel')
    b.cylinder('BowBollard',(cx,-7.15,1.22),.08,.28,'Tug',mat='Steel',sides=8)
    b.beam('BowBollardCross',(cx-.19,-7.15,1.33),(cx+.19,-7.15,1.33),.065,.065,group='Tug',mat='Steel')
    b.cable('TugMooringLine',[(cx-.82,-4.0,1.12),(-5.20,-3.71,1.03),(-6.65,-3.69,1.17)],.025,group='Tug',mat='Rope')
    b.scene['tug_complete']=True
    bpy.context.view_layer.update()
    parts=[]
    for obj in b.parts:
        bm=bmesh.new(); bm.from_mesh(obj.data)
        assert all(e.is_manifold for e in bm.edges),obj.name
        assert all(f.calc_area()>1e-9 for f in bm.faces),obj.name
        assert all(not f.use_smooth for f in obj.data.polygons),obj.name
        assert len(obj.data.uv_layers)==1 and obj.data.uv_layers.active.name=='PixelUV',obj.name
        parts.append({'name':obj.name,'group':obj.parent.name,'faces':len(bm.faces),'vertices':len(bm.verts)})
        bm.free()
    for name in ['InsuranceSignLetterFace','CargoCraneSignLetterFace']:
        obj=bpy.data.objects[PREFIX+name]
        uv=obj.data.uv_layers.active
        front=[p for p in obj.data.polygons if p.normal.y<-.9]
        assert len(front)==1
        coords=[uv.data[i].uv for i in front[0].loop_indices]
        assert max(p.x for p in coords)-min(p.x for p in coords)>.4
        assert max(p.y for p in coords)-min(p.y for p in coords)>.3
    bounds_points=[o.matrix_world@Vector(corner) for o in b.parts for corner in o.bound_box]
    bounds=[[min(p[i] for p in bounds_points) for i in range(3)],[max(p[i] for p in bounds_points) for i in range(3)]]
    b.scene['export_complete']=True
    bpy.data.libraries.write(str(SOURCE/'insurance_r2_library.blend'),{b.scene},fake_user=True,compress=True)
    report={'input_sha256':SHA,'stage':'complete rebuilt asset draft; not game-integrated or art-approved','editable_parts':parts,'bounds_blender_z_up':bounds,'density':DENSITY,'rear':'Fully enclosed inferred rear, because reference is front-only','sign_uv':'One shared active PixelUV on every part before joining','reference_camera':{'yaw':0,'pitch':42,'target':[0,-1.05,3.35]},'materials':list(b.materials)}
    (SOURCE/'build_record.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert 'Insurance_R2_Export' not in bpy.data.scenes
    export=bpy.data.scenes.new('Insurance_R2_Export'); switch(export)
    root=bpy.data.objects.new('InsuranceRebuildR2',None); export.collection.objects.link(root)
    for name,group in b.groups.items():
        copies=[]
        for original in b.parts:
            if original.parent!=group: continue
            mesh=original.data.copy(); mesh.transform(original.matrix_world)
            obj=bpy.data.objects.new('R2ExportPart',mesh); export.collection.objects.link(obj); copies.append(obj)
        assert copies
        bpy.ops.object.select_all(action='DESELECT')
        for obj in copies: obj.select_set(True)
        bpy.context.view_layer.objects.active=copies[0]; bpy.ops.object.join()
        joined=copies[0]; joined.name='INS_'+name+'Geometry'; joined.parent=root
        assert joined.name=='INS_'+name+'Geometry'
        assert len(joined.data.uv_layers)==1 and joined.data.uv_layers.active.name=='PixelUV'
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=str(ASSET/'insurance_rebuild_r2.glb'),export_format='GLB',use_selection=True,use_active_scene=True,export_yup=True,export_apply=True,export_cameras=False,export_lights=False,export_animations=False,export_image_format='AUTO')
    print(json.dumps({'result':'R2_COMPLETE_EXPORT','parts':len(parts),'source_polygons':sum(p['faces'] for p in parts),'groups':6,'bounds':bounds,'art_approved':False}))
verify_input()
