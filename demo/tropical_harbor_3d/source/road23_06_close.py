"""Check the saved road-contact source and normally close this owned MCP session."""
import bpy, json, os
from pathlib import Path

ROOT = Path(bpy.data.filepath).parent.parent
LOG = ROOT / 'captures/road_contacts_20261123'
terrain = bpy.data.objects['C25_ContourBuiltCoast']
assert terrain.get('road23_contacts_grade') and terrain.get('road23_grass_contacts')
assert not bpy.data.is_dirty, 'Save current source before closing'
export = json.loads((LOG / 'export.json').read_text(encoding='utf8'))
core = json.loads((LOG / 'core_audit.json').read_text(encoding='utf8'))
assert export['source_saved'] and not export['dirty'] and export['source_material_restored']
assert core['status'] == 'completed' and core['core_checks_pass'] and not core['failures']
mat = terrain.data.materials[0]
pr = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
assert pr.inputs['Base Color'].links[0].from_node.name.startswith('G23Preview ')
report = {'pid': os.getpid(), 'port': bpy.types.blendermcp_server.port,
          'source': bpy.data.filepath, 'source_saved': True, 'dirty': False,
          'source_material_restored': True, 'core_checks_pass': True,
          'visual_accepted': False, 'normal_quit_requested': True, 'process_exited': False}
(LOG / 'session_close.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps(report, ensure_ascii=False))

def close_owned_road_session():
    bpy.ops.wm.quit_blender()
    return None

bpy.app.timers.register(close_owned_road_session, first_interval=1.5)
