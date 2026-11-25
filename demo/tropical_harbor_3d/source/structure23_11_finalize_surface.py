"""Refresh surface and contacts after full-width slope finishing; GUI MCP only."""
import bpy,json,time
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/terrain_structure_20261123'
for name in ['structure23_02_land.py','structure23_03_props.py','structure23_04_manual_props.py','structure23_04_grass.py','structure23_07_check.py']:
    exec(compile((ROOT/'source'/name).read_text(encoding='utf8'),name,'exec'),globals())
assert not json.loads((LOG/'structure_audit.json').read_text(encoding='utf8'))['failures']
assert not json.loads((LOG/'manual_props.json').read_text(encoding='utf8'))['problems']
print('SURFACE_AND_CONTACTS_COMPLETE')
