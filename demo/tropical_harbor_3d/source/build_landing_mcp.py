"""Run using execute_code on the live Blender MCP server (port 9877).

Build the arrival landing from copies of the approved pier components. The
approved source collections are preserved. Coordinates here use Blender Z up.
"""
import bpy
import bmesh
import json
from mathutils import Matrix, Vector
from pathlib import Path

if Path(bpy.data.filepath).name != 'harbor_art_mcp.blend':
    raise RuntimeError('The live harbor_art_mcp.blend must be open.')
root = Path(bpy.data.filepath).parent.parent
source = bpy.data.collections['Pier_Working']
name = 'Harbor_Arrival_Landing'
if name in bpy.data.collections:
    raise RuntimeError('Landing already exists; inspect it before rebuilding.')
collection = bpy.data.collections.new(name)
bpy.context.scene.collection.children.link(collection)


def copy_part(template, name, transform):
    obj = template.copy()
    obj.data = template.data.copy()
    obj.name = name
    obj.matrix_world = Matrix.Identity(4)
    for vertex in obj.data.vertices:
        vertex.co = transform(template.matrix_world @ vertex.co)
    center = Vector([(min(v.co[i] for v in obj.data.vertices) + max(v.co[i] for v in obj.data.vertices)) * .5 for i in range(3)])
    for vertex in obj.data.vertices:
        vertex.co -= center
    obj.location = center
    collection.objects.link(obj)
    obj.hide_set(False)
    obj.hide_viewport = False
    obj.hide_render = False
    return obj


boards = sorted((o for o in source.objects if o.name.startswith('Walkboard_')), key=lambda o: o.name)
deck = []
for i in range(65):
    template = boards[i % len(boards)]
    center = template.location.x
    x = (i - 32) * .28
    deck.append(copy_part(template, f'LandingBoard_{i:02}',
        lambda p, center=center, x=x: Vector((p.x - center + x, p.y * 1.65, p.z))))

for side in [-1, 1]:
    bearer = source.objects[f'Long bearer {side}']
    copy_part(bearer, f'Landing bearer {side}', lambda p: Vector((p.x * 2.27, p.y * 1.65, p.z)))
    pile = source.objects[f'WaterPile_{side}_0']
    crown = source.objects[f'Pile crown {side} 0']
    for row in range(7):
        x = -8.55 + row * 2.85
        y = side * 1.60

        def pile_transform(p, x=x, y=y, origin=pile.location.copy()):
            z = .2 + (p.z - .2) * (4.6 / 1.75) if p.z < .2 else p.z
            return Vector((p.x - origin.x + x, p.y - origin.y + y, z))

        copy_part(pile, f'WaterPile_Landing_{side}_{row}', pile_transform)
        for template in [crown, source.objects[f'Binding {side} 0 0'], source.objects[f'Binding {side} 0 1']]:
            origin = template.location.copy()
            copy_part(template, f'Landing {template.name} row {row}',
                lambda p, origin=origin, x=x, y=y: Vector((p.x - origin.x + x, p.y - origin.y + y, p.z)))
for row in range(7):
    template = source.objects['Cross bearer 0']
    copy_part(template, f'Landing cross bearer {row}',
        lambda p, x=-8.55 + row * 2.85: Vector((p.x - template.location.x + x, p.y * 1.65, p.z)))

# One draw for the repeated planks; keep piles individually named for water contacts.
bpy.ops.object.select_all(action='DESELECT')
for obj in deck:
    obj.select_set(True)
bpy.context.view_layer.objects.active = deck[0]
bpy.ops.object.join()
bpy.context.object.name = 'LandingDeck'

for c in bpy.data.collections:
    c.hide_viewport = False
bpy.ops.object.select_all(action='DESELECT')
for obj in collection.objects:
    if obj.type == 'MESH':
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.to_mesh(obj.data)
        bm.free()
    obj.select_set(True)
bpy.context.view_layer.objects.active = next(iter(collection.objects))
path = root / 'assets/harbor_landing_mcp.glb'
bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
    export_texcoords=True, export_normals=True, export_tangents=True,
    export_vertex_color='NONE', export_materials='EXPORT', export_image_format='AUTO',
    export_apply=True, export_yup=True, export_animations=False)
collection.hide_viewport = True
collection.hide_render = True
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(json.dumps({'file':str(path), 'bytes':path.stat().st_size, 'objects':len(collection.objects),
    'width_m':3.4, 'length_m':18.2, 'pile_bottom_m':-4.4}))
