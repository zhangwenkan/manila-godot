"""Refresh complete props after protecting the whole pier approach."""
import bpy
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
for name in ['structure23_03_props.py','structure23_04_manual_props.py','structure23_07_check.py']:
    exec(compile((ROOT/'source'/name).read_text(encoding='utf8'),name,'exec'),globals())
