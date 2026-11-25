"""One-time snapshot in owned MCP, before changing the existing island root."""
import bpy, os, json, hashlib, shutil, importlib.util
from pathlib import Path
from datetime import datetime
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/pirate_orientation_20261125'
assert os.getpid()==38548 and not bpy.app.background and bpy.types.blendermcp_server.port==9881
assert not (LOG/'session_start.json').exists()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert sha(bpy.data.filepath)=='09330e1d03d41f946ebda7121c44c38d6089e839e5030f35cb36457b5f89457b'
HELPER=ROOT.parent.parent/'docs/pirate_orientation_20261125/pirate_orientation25_invariants.py'
spec=importlib.util.spec_from_file_location('pirate_orientation_invariants',HELPER)
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
local=helpers.capture_island_local()
(LOG/'island_local_before.json').write_text(json.dumps(local,ensure_ascii=False,indent=2),encoding='utf8')
oldns={}
exec(compile((ROOT.parent.parent/'docs/pirate_island_20261125/pirate25_export.py').read_text(encoding='utf8'), 'pirate25_export.py','exec'),oldns)
digest=oldns['object_digest']
rows=[]
for col in bpy.data.collections:
    if col.name.startswith('Reference_') and col.name!='Reference_PirateIsland' and not col.hide_render:
        for obj in col.objects:
            if obj.type=='MESH': rows.append({'name':obj.name,'collection':col.name,'digest':digest(obj)})
(LOG/'objects_before.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
paths=[Path(bpy.data.filepath),ROOT/'materials/reference_water.gdshader',ROOT/'materials/landform_mass.gdshader',ROOT/'fleet_harbor.gd',ROOT/'fleet_harbor.tscn']
paths+=list((ROOT/'fleet').glob('*.gd'))+list((ROOT/'assets/reference').glob('*.glb'))+[ROOT/'assets/reference/shore_relief_height.json',ROOT/'environment/reference_coast.gd',ROOT/'environment/reference_environment.gd',ROOT/'tools/capture_art.py',ROOT/'tools/reference_rebuild_review.gd',ROOT/'tools/reference_pirate_review.gd']
manifest=[]
for p in paths:
    rel=p.relative_to(ROOT);target=LOG/'before'/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists(): shutil.copy2(p,target)
    # Camera work has its own earlier actual snapshot. Never overwrite it with a later file.
    manifest.append({'relative':rel.as_posix(),'sha256':sha(target),'bytes':target.stat().st_size,'snapshot_file':str(target)})
(LOG/'before_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
report={'pid':os.getpid(),'port':9881,'source':bpy.data.filepath,'sha256':sha(bpy.data.filepath),'dirty':bpy.data.is_dirty,'objects':len(rows),'island_objects':len([o for o in bpy.data.collections['Reference_PirateIsland'].all_objects if o.type=='MESH']),'backup_files':len(manifest),'blender':bpy.app.version_string,'created_local':datetime.now().astimezone().isoformat()}
(LOG/'session_start.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
