import bpy
from pathlib import Path
root=Path(bpy.data.filepath).parent.parent
p=root.parents[1]/'docs/reference_review_20261125/cliff25_final_readonly.py'
ns={}
exec(compile(p.read_text(encoding='utf-8-sig'),str(p),'exec'),ns)
r=ns['final_cliff25_readonly'](9864)
assert r['technical_pass'],r['failures']
