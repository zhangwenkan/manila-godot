"""Grade and inspect before touching surface images or prop placement."""
import bpy
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
for name in ['structure23_05_prepare.py','structure23_01_grade.py','structure23_10_slope_cleanup.py']:
    exec(compile((ROOT/'source'/name).read_text(encoding='utf8'),name,'exec'),globals())
