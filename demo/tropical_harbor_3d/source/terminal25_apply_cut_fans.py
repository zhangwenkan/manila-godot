from pathlib import Path
import bpy
code=Path(bpy.data.filepath).parent/'terminal25_15_cut_fans.py'
exec(compile(code.read_text(encoding='utf8'),str(code),'exec'),{'TN25_FAN_APPLY':True})
