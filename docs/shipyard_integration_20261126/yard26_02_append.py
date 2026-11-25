"""Append only the selected editable workshop; retain old local construction."""
import bpy, os, json, math, hashlib
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/shipyard_integration_20261126'
assert os.getpid()==29492 and bpy.types.blendermcp_server.port==9881
assert (LOG/'session_start.json').exists() and not (LOG/'append.json').exists()
assert bpy.data.collections.get('Reference_Shipyard') is None
source=LOG/'source_staging/harbor_coast_mcp.blend'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='479ff9c6452ca85913a52bd3034f8ea6347d1d649846e1ea9e5eeb444cbfdba7'
with bpy.data.libraries.load(str(source),link=False) as (available,loaded):
    assert 'Shipyard_COMBINED_Craft' in available.collections
    loaded.collections=['Shipyard_COMBINED_Craft']
collection=loaded.collections[0]
bpy.context.scene.collection.children.link(collection)
collection.name='Reference_Shipyard'
collection.hide_viewport=False;collection.hide_render=False
bpy.context.view_layer.update()
objects=list(collection.all_objects)
rows=[]
for obj in objects:
    pts=[obj.matrix_world@Vector(c) for c in obj.bound_box] if obj.type=='MESH' else [obj.matrix_world.translation]
    rows.append({'name':obj.name,'type':obj.type,'parent':obj.parent.name if obj.parent else None,'matrix_world':[list(v) for v in obj.matrix_world],'bounds_local':[[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]],'hide_render':obj.hide_render,'skip':bool(obj.get('sp13_skip_export',False)),'materials':[m.name if m else '' for m in obj.data.materials] if obj.type=='MESH' else []})
(LOG/'appended_components_local.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
assembly=bpy.data.objects.new('Y26_Assembly',None);collection.objects.link(assembly)
for obj in objects:
    if obj.parent is None:
        world=obj.matrix_world.copy();obj.parent=assembly;obj.matrix_world=world
archive=bpy.data.collections.new('Archive_Y26_OriginalShoreBank');bpy.context.scene.collection.children.link(archive)
archive.hide_render=True;archive.hide_viewport=True
removed=[]
for obj in objects:
    if obj.name.startswith('M14 continuous sculpted shore bank') or obj.get('sp13_skip_export',False):
        for c in list(obj.users_collection):c.objects.unlink(obj)
        archive.objects.link(obj);removed.append(obj.name)
assembly.location=(12.35,9,0);assembly.rotation_euler=(0,0,math.radians(-90))
bpy.context.view_layer.update()
mats={m for obj in collection.all_objects if obj.type=='MESH' for m in obj.data.materials if m}
images={n.image for m in mats if m.use_nodes for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image}
missing=[im.name for im in images if not im.packed_file and not Path(bpy.path.abspath(im.filepath)).exists()]
report={'source':str(source),'members_before':len(objects),'active_meshes':len([o for o in collection.all_objects if o.type=='MESH']),'archived':removed,'material_count':len(mats),'images':[{'name':im.name,'packed':bool(im.packed_file),'path':im.filepath} for im in images],'missing_images':missing,'position_godot':[12.35,0,-9],'yaw_degrees':-90,'saved':False}
(LOG/'append.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='images'}))
assert not missing,missing
