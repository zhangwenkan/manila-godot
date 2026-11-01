"""Validate the delivered sample in a separate Blender process; read-only."""
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

assert bpy.app.background
assert Path(bpy.data.filepath).name == "insurance_pixel_sample.blend"
assert len(bpy.data.scenes) == 1
scene = bpy.data.scenes[0]
assert scene.name == "INS7_StyleSample"
assert all(o.type in {"MESH","EMPTY"} for o in scene.objects)
meshes = [o for o in scene.objects if o.type == "MESH"]
assert len(meshes) == 39
images = set()
checked_edges = 0
for obj in meshes:
    bm = bmesh.new(); bm.from_mesh(obj.data)
    assert all(e.is_manifold for e in bm.edges), obj.name
    assert all(f.calc_area() > 1e-9 for f in bm.faces), obj.name
    seen = set()
    for face in bm.faces:
        signature = tuple(sorted(tuple(round(v,7) for v in p.co) for p in face.verts))
        assert signature not in seen, obj.name
        seen.add(signature)
    bm.free()
    assert all(not f.use_smooth for f in obj.data.polygons)
    for mat in obj.data.materials:
        if not mat or not mat.use_nodes:
            continue
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        assert bsdf.inputs["Roughness"].default_value == 1
        assert bsdf.inputs["Metallic"].default_value == 0
        assert bsdf.inputs["Specular IOR Level"].default_value == 0
        assert not bsdf.inputs["Normal"].is_linked
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE":
                assert node.interpolation == "Closest"
                assert node.image.packed_file
                images.add(node.image)
    if obj.data.materials[0].name != "INS7_Atlas":
        continue
    uv = obj.data.uv_layers.active.data
    for face in obj.data.polygons:
        loops = list(face.loop_indices)
        for a,b in zip(loops, loops[1:]+loops[:1]):
            pa = obj.matrix_world @ obj.data.vertices[obj.data.loops[a].vertex_index].co
            pb = obj.matrix_world @ obj.data.vertices[obj.data.loops[b].vertex_index].co
            texels = (uv[a].uv-uv[b].uv).length*512
            density = texels/(pa-pb).length
            assert abs(density-24) < .024, (obj.name,density)
            checked_edges += 1
assert sorted(tuple(i.size) for i in images) == [(256,64),(512,512)]
print("INS7_SAMPLE_SOURCE_PASS", len(meshes), "closed editable parts;",checked_edges,"UV edges at 24 texels/unit; 2 packed nearest textures; no smooth/normal-map/specular")
