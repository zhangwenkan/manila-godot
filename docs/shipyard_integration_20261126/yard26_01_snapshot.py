"""Capture this round's real baseline and inspect the north-bank site through MCP."""
import bpy, os, json, hashlib, shutil, importlib.util
from pathlib import Path
from datetime import datetime
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/shipyard_integration_20261126'
LOG.mkdir(parents=True,exist_ok=True)
assert os.getpid()==29492 and bpy.types.blendermcp_server.port==9881 and not bpy.app.background
assert not (LOG/'session_start.json').exists()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(bpy.data.filepath)=='c7875c007daf21c3e4d3cec38df6ad6ed9bb2f59460f64625ba240f1a05519c1'
path=ROOT.parent.parent/'docs/pirate_orientation_20261125/pirate_orientation25_export.py'
spec=importlib.util.spec_from_file_location('yard_baseline_utils',path)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
files=[Path(bpy.data.filepath),ROOT/'fleet_harbor.gd',ROOT/'fleet_harbor.tscn',ROOT/'environment/reference_coast.gd',ROOT/'environment/reference_environment.gd',ROOT/'materials/reference_water.gdshader',ROOT/'assets/reference/shore_relief_height.json',ROOT/'tools/capture_art.py',ROOT/'tools/reference_rebuild_review.gd']
files+=list((ROOT/'fleet').glob('*.gd'))+list((ROOT/'assets/reference').glob('*.glb'))
rows=[]
for p in files:
    rel=p.relative_to(ROOT);out=LOG/'before'/rel;out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():
        assert sha(out)==sha(p),'Before already differs from source; review actual edit history: '+str(p)
    else:
        shutil.copy2(p,out)
    rows.append({'relative':rel.as_posix(),'sha256':sha(out),'bytes':out.stat().st_size})
(LOG/'before_manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
objects=[];site=[]
from mathutils import Vector
for col in bpy.data.collections:
    if not col.name.startswith('Reference_') or col.hide_render:continue
    for obj in col.objects:
        if obj.type!='MESH':continue
        objects.append({'name':obj.name,'collection':col.name,'digest':helper.object_digest(obj)})
        pts=[obj.matrix_world@Vector(c) for c in obj.bound_box]
        lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)]
        if lo[0]<25 and hi[0]>3 and lo[1]<22 and hi[1]>-3:
            site.append({'name':obj.name,'collection':col.name,'bounds_blender':[lo,hi],'location':list(obj.location),'vertices':len(obj.data.vertices),'materials':[m.name if m else '' for m in obj.data.materials]})
(LOG/'objects_before.json').write_text(json.dumps(objects,indent=2),encoding='utf8')
(LOG/'site_objects_before.json').write_text(json.dumps(site,indent=2),encoding='utf8')
r={'created_local':datetime.now().astimezone().isoformat(),'pid':os.getpid(),'port':9881,'source':bpy.data.filepath,'sha256':sha(bpy.data.filepath),'dirty':bpy.data.is_dirty,'files':len(rows),'objects':len(objects),'site_objects':len(site),'collections':[{'name':c.name,'count':len(c.objects),'hidden':c.hide_render} for c in bpy.data.collections if c.name.startswith('Reference_')]}
(LOG/'session_start.json').write_text(json.dumps(r,indent=2),encoding='utf8')
print(json.dumps(r))
