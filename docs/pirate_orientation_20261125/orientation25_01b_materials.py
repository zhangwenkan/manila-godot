"""Supplemental read-only material baseline before the first model mutation."""
import bpy, os, json, math
from pathlib import Path
from datetime import datetime
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/pirate_orientation_20261125'
assert os.getpid()==38548 and not bpy.app.background and bpy.types.blendermcp_server.port==9881
assert not (LOG/'transform.json').exists() and not (LOG/'materials_before.json').exists()
assembly=bpy.data.objects['P25_Assembly']
assert abs(assembly.location.y-22)<1e-5 and abs(assembly.rotation_euler.z-math.radians(-20))<1e-5
rows=[]
for material in bpy.data.materials:
    p=next((n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) if material.use_nodes else None
    rows.append({'name':material.name,
                 'images':[n.image.name for n in material.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] if material.use_nodes else [],
                 'color':list(p.inputs['Base Color'].default_value) if p else None})
(LOG/'materials_before.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
report={'created_local':datetime.now().astimezone().isoformat(),'scope':'Supplemental image-reference/base-color baseline before root transform and export, not a session-start full shader graph snapshot.','count':len(rows),'source_dirty':bpy.data.is_dirty,'root_pose_unchanged':True}
(LOG/'materials_baseline_metadata.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
