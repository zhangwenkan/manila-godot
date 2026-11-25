import bpy
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
exec((ROOT/'source/structure23_export.py').read_text(encoding='utf8'),globals())
export_structure23(28032,changed_collections=['Reference_Town','Reference_Foliage','Reference_Coast','Reference_Rocks','Reference_GroundCover'])
