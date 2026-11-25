"""Verify final G23 saved source and close this guarded owned GUI session."""
import bpy,json,os
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/ground_integration_20261123'
terrain=bpy.data.objects['C25_ContourBuiltCoast']
assert terrain.get('ground23_integrated_shoulders')
assert bpy.data.objects['L24_GrassTuftClusters'].get('ground23_reground_integrated_shoulders')
assert not bpy.data.is_dirty,'Source must be saved before normal quit'
plate=bpy.data.objects['G23_EmbeddedRockOutcrops']
assert plate.hide_render and any(c.name=='Archive_G23_V5_RockPlates' for c in plate.users_collection)
mat=terrain.data.materials[0];pr=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
assert pr.inputs['Base Color'].links[0].from_node.name.startswith('G23Preview ')
assert all(bpy.data.images.get('G23_'+role) for role in ('Grass','Rock','Path','Soil','Sand','LandUse'))
verification=json.loads((LOG/'final_independent_verification.json').read_text(encoding='utf8'))
assert verification['technical_pass']
report={'pid':os.getpid(),'port':bpy.types.blendermcp_server.port,'source':bpy.data.filepath,
        'source_saved':True,'dirty':bpy.data.is_dirty,'source_material_restored':True,
        'rock_plates_archived':True,'final_active_terrain_triangles':len(terrain.data.polygons),
        'full_capture':'art_20261123_210034_907190','last_surface_capture':'art_20261123_205741_819828',
        'technical_pass':True,'visual_accepted':False,'normal_quit_requested':True,'process_exited':False}
(LOG/'session_close.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
def quit_owned_session():
    bpy.ops.wm.quit_blender()
    return None
bpy.app.timers.register(quit_owned_session,first_interval=1.5)
