from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
from model_lib import *

assert SCENE_NAME not in bpy.data.scenes, 'Asset scene already exists; inspect before rebuilding'
old=bpy.context.scene
state={'scene':old.name,'active':bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,'selected':[o.name for o in bpy.context.selected_objects]}
s=bpy.data.scenes.new(SCENE_NAME)
s['original_scene_state']=str(state)
s.unit_settings.system='METRIC'
col=bpy.data.collections.new('INS_Model')
s.collection.children.link(col)
bpy.context.window.scene=s
root=group('InsuranceAsset')
root['source']='Blender-MCP custom model from user single-view reference; unseen sides designed locally'
root['godot_origin']=[18.9,0,-10.2]
for name in ['Office','Roof','Crane','Dock','Props','Tug']:
    group(name,root)
material('INS_Wall',(.29,.48,.54),'wall_blue.png')
material('INS_Tin',(.48,.53,.51),'roof_tin.png',.1)
material('INS_Red',(.57,.15,.08),'crane_red.png',.12)
material('INS_Wood',(.47,.31,.15),'dock_wood.png')
material('INS_Dark',(.055,.075,.077))
material('INS_Trim',(.19,.32,.35))
material('INS_Cream',(.82,.77,.58))
material('INS_Glass',(.095,.22,.28),roughness=.46)
material('INS_GlassLight',(.24,.42,.46),roughness=.48)
material('INS_Rust',(.32,.13,.055))
material('INS_Iron',(.17,.20,.19),metallic=.3)
material('INS_Rope',(.35,.27,.16))
material('INS_Blue',(.10,.29,.43))
material('INS_BoatRed',(.49,.11,.065))
material('INS_Stone',(.27,.30,.28))
dock=bpy.data.objects['Dock']
box('INS_DockFoundation',(0,0,.31),(13.4,7.5,.32),'INS_Dark',dock,.05)
box('INS_DeckBlockout',(0,0,.53),(13.4,7.5,.10),'INS_Wood',dock)
box('INS_WatersidePier',(-7.7,-2.35,.47),(2.0,1.7,.20),'INS_Wood',dock)
office=bpy.data.objects['Office']
# Envelope is divided into genuine front-wall openings in the next stage.
for name,x,w,h in [('Central',-1.8,3.6,3.55),('LeftWing',-4.6,2.0,2.8),('RightWing',.85,1.7,2.95)]:
    box('INS_Blockout_'+name,(x,1.95,(h+.6)/2),(w,2.7,h-.6),'INS_Wall',office)
roof=bpy.data.objects['Roof']
for name,cx,half,eave,ridge in [('Central',-1.8,2.05,3.65,5.12),('Left',-4.6,1.25,2.9,3.75),('Right',.85,1.02,3.05,3.65)]:
    for side in [-1,1]:
        slab('INS_BlockoutRoof_'+name+str(side),[(cx,.32,ridge),(cx,3.63,ridge),(cx+side*half,3.63,eave),(cx+side*half,.32,eave)],.13,'INS_Tin',roof)
crane=bpy.data.objects['Crane']
for x in [2.5,5.5]:
    for y in [.15,2.35]:
        beam('INS_CraneColumn',(x,y,.65),(x,y,6.55),.26,'INS_Red',crane)
for y in [.15,2.35]:
    beam('INS_TopGirder',(2.2,y,6.5),(5.9,y,6.5),.42,'INS_Red',crane)
beam('INS_BoomBlockout',(4.0,.7,6.55),(1.55,-1.2,8.0),.30,'INS_Red',crane)
tug=bpy.data.objects['Tug']
tug.location=(-10.0,-2.8,0)
box('INS_TugBlockout',(0,0,.12),(1.24,3.35,.68),'INS_Blue',tug,.1)
box('INS_TugCabinBlockout',(0,-.25,.8),(.96,1.12,.70),'INS_Cream',tug)
bpy.context.view_layer.update()
export_glb(SOURCE/'insurance_blockout.glb')
print('BLOCKOUT_READY',len(s.objects),'original:',old.name,len(old.objects))
