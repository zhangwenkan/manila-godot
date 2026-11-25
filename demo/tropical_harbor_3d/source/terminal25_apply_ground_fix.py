from pathlib import Path
import bpy
p=Path(bpy.data.filepath).parent/'terminal25_08_ground_fix.py'
exec(compile(p.read_text(encoding='utf8'),str(p),'exec'),{'TN25_GROUND_FIX_APPLY':True})
