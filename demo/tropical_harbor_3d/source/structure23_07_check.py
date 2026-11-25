"""Read-only live geometry review; no mutations or exports."""
import bpy,json
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/terrain_structure_20261123'
exec((ROOT/'source/structure23_audit.py').read_text(encoding='utf8'),globals())
result=audit_structure23_design(LOG/'design.json',28032,changed_collections=['Reference_Town'])
print(json.dumps({'status':result.get('status'),'failures':result.get('failures'),'incomplete':result.get('incomplete')}))
