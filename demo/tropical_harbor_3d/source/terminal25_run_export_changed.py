from pathlib import Path
import bpy
p=Path(bpy.data.filepath).parent/'terminal25_06_export.py'
ns={}
exec(compile(p.read_text(encoding='utf8'),str(p),'exec'),ns)
ns['export_terminal25'](expected_pid=13812,changed_only=True)
