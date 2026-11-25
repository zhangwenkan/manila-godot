"""One-time placement of only the new lighthouse; never blindly replay."""
import bpy, os, json, math
from pathlib import Path
from mathutils import Vector

ROOT = Path(bpy.data.filepath).parent.parent
LOG = ROOT / 'captures/lighthouse_integration_20261126'
assert os.getpid() == 18904 and bpy.types.blendermcp_server.port == 9891
assert not bpy.app.background
assert not (LOG / 'placement.json').exists()
root = bpy.data.objects['L26_Assembly']
assert root.get('placement_pending') is True
assert root.location.length < 1e-6 and root.rotation_euler.to_matrix().is_identity
root.location = (5.5, -15.0, 0.0)
root['placement_pending'] = False
root['site_godot'] = [5.5, 0.0, 15.0]
root['site_basis'] = 'Separate submerged reef; full three-lane hull/camera/old-pier preflight, no route edits.'
bpy.context.view_layer.update()
points = [o.matrix_world @ v.co for o in bpy.data.collections['Reference_Lighthouse'].all_objects
          if o.type == 'MESH' for v in o.data.vertices]
extent = {'min_blender': [min(p[i] for p in points) for i in range(3)],
          'max_blender': [max(p[i] for p in points) for i in range(3)]}
radius = max(math.hypot(p.x - 5.5, p.y + 15) for p in points)
emitter = bpy.data.objects['L26_LampEmitter'].matrix_world.translation
report = {'pid': os.getpid(), 'port': 9891, 'center_godot': [5.5, 0, 15],
          'rotation_degrees': 0, 'extent': extent, 'horizontal_radius': radius,
          'emitter_godot': [emitter.x, emitter.z, -emitter.y],
          'legacy_reference_images_used': False, 'source_saved': False}
(LOG / 'placement.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
