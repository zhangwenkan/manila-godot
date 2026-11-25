"""Export only after all live structure and pier clearance checks pass."""
import bpy, json
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/terrain_structure_20261123'
exec((ROOT/'source/structure23_07_check.py').read_text(encoding='utf8'),globals())
assert result['technical_pass']
exec((ROOT/'source/structure25_pier_clearance.py').read_text(encoding='utf8'),globals())
assert audit_structure25_pier_clearance(28032)['technical_pass']
exec((ROOT/'source/structure23_08_export.py').read_text(encoding='utf8'),globals())
