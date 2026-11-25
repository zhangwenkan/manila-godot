# Verify saved final sample and close only the guarded owned MCP process.
import bpy,json,os
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/rock_path_sample_20261123'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];assert terrain.get('sample23_local_support') and terrain.get('sample23_beach_exit')
assert not bpy.data.is_dirty,'Final source must already be saved'
mat=terrain.data.materials[0];principled=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
assert principled.inputs['Base Color'].links[0].from_node.name.startswith('S23Preview '),'Source preview was not restored after export'
report={'pid':os.getpid(),'port':bpy.types.blendermcp_server.port,'source':bpy.data.filepath,'dirty':bpy.data.is_dirty,'source_material_restored':True,'patches':['connections','grass','local_support','beach_exit'],'full_capture':'art_20261123_184239_281980','last_surface_capture':'art_20261123_184537_894398','visual_accepted':False,'normal_quit_requested':True,'process_exited':False}
(LOG/'session_close.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
def quit_owned_session():
 bpy.ops.wm.quit_blender()
 return None
bpy.app.timers.register(quit_owned_session,first_interval=1.5)
