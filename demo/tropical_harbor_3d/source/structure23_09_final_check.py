"""Run final read-only verification against the saved live source and exports."""
import bpy
from pathlib import Path
ROOT = Path(bpy.data.filepath).parent.parent
exec((ROOT / 'source/structure23_final_readonly.py').read_text(encoding='utf8'), globals())
final_structure23_readonly(28032)
