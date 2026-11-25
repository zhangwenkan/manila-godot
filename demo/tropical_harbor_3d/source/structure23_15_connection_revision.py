"""Rebuild the remaining access relationships from this turn's immutable base."""
import bpy,json
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/terrain_structure_20261123'
for name in ['structure23_05_prepare.py','structure23_01_grade.py','structure23_10_slope_cleanup.py','structure23_11_finalize_surface.py']:
    exec(compile((ROOT/'source'/name).read_text(encoding='utf8'),name,'exec'),globals())
print('CONNECTION_REVISION_COMPLETE')
