"""One-time baseline through this round's owned GUI Blender MCP."""
import bpy, os, json, hashlib, shutil, importlib.util
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(bpy.data.filepath).parent.parent
LOG = ROOT / 'captures/lighthouse_integration_20261126'
assert os.getpid() == 18904 and bpy.types.blendermcp_server.port == 9891 and not bpy.app.background
assert not (LOG/'before_manifest.json').exists()
assert not bpy.data.collections.get('Reference_Lighthouse')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(bpy.data.filepath) == 'e082061ae50f01584de769b5f9f4dfb7fb4e9df39db82f4f91a8e819bb248e23'
definition = ROOT.parent.parent/'docs/pirate_island_20261125/pirate25_export.py'
spec=importlib.util.spec_from_file_location('lighthouse26_baseline_defs',definition)
helpers=importlib.util.module_from_spec(spec); spec.loader.exec_module(helpers)
paths=[Path(bpy.data.filepath), ROOT/'environment/reference_coast.gd', ROOT/'environment/reference_environment.gd',
       ROOT/'materials/reference_water.gdshader', ROOT/'fleet_harbor.gd', ROOT/'fleet_harbor.tscn']
paths += list((ROOT/'fleet').glob('*.gd')) + list((ROOT/'assets/reference').glob('*.glb'))
paths += [ROOT/'assets/reference/shore_relief_height.json']
manifest=[]
for path in paths:
    relative=path.relative_to(ROOT); dst=LOG/'before'/relative
    assert not dst.exists()
    dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,dst)
    manifest.append({'relative':relative.as_posix(),'sha256':sha(path),'bytes':path.stat().st_size,
                     'preserve':path.suffix=='.glb' or path.name=='shore_relief_height.json'})
(LOG/'before_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
objects={o.name:o for c in bpy.data.collections if c.name.startswith('Reference_') and not c.hide_render for o in c.all_objects}
rows=[{'name':o.name,'type':o.type,'digest':helpers.object_digest(o),
       'collections':sorted(c.name for c in o.users_collection),'parent':o.parent.name if o.parent else None}
      for o in objects.values()]
(LOG/'objects_before.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
materials={m.name:m for o in objects.values() if o.type in {'MESH','FONT'} for m in o.data.materials if m}
states={name:helpers.material_state(m) for name,m in materials.items()}
(LOG/'materials_before.json').write_text(json.dumps(states,ensure_ascii=False,indent=2),encoding='utf-8')
report={'pid':os.getpid(),'port':9891,'source':bpy.data.filepath,'sha256':sha(bpy.data.filepath),
        'dirty':bpy.data.is_dirty,'objects':len(rows),'materials':len(states),'backup_files':len(manifest),
        'blender':bpy.app.version_string,'time':datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'snapshot_scope':'All old active Reference_* recursive objects, raw transform/mesh/UV/material slots, collection/parent and referenced material states. Not every hidden archive datablock.'}
(LOG/'session_start.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
print('AVAILABLE_MATERIALS',json.dumps(sorted(materials)))
