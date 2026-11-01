"""Build the temporary, meter-scale tropical water demo boat.

Run with factory-startup Blender in background mode:
  blender --background --factory-startup --python build_test_boat.py -- /output/assets

Blender: +Y is bow, +Z is up, waterline Z=0.
GLTF/Godot: -Z is bow, +Y is up, waterline Y=0.
No external textures, scene lights, cameras, or Blender project are exported.
"""

import argparse
import json
import math
import struct
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


def srgb_to_linear(value):
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def material(name, hex_color, roughness=0.72, metallic=0.0):
    channels = tuple(int(hex_color[index:index + 2], 16) / 255.0 for index in (0, 2, 4))
    color = tuple(srgb_to_linear(channel) for channel in channels) + (1.0,)
    result = bpy.data.materials.new(name)
    result.diffuse_color = color
    result.use_nodes = True
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return result


def finish_mesh(obj, materials, bevel=0.0):
    for mat in materials:
        obj.data.materials.append(mat)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    if bevel:
        modifier = obj.modifiers.new("Small softened edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        modifier.affect = "EDGES"
        modifier.limit_method = "ANGLE"
        modifier.angle_limit = 0.45
        modifier.harden_normals = True
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        normals = obj.modifiers.new("Face weighted normals", "WEIGHTED_NORMAL")
        normals.keep_sharp = True
        normals.weight = 40
        bpy.ops.object.modifier_apply(modifier=normals.name)
    return obj


def mesh_object(name, vertices, faces, materials, bevel=0.0):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return finish_mesh(obj, materials, bevel)


def box(name, center, dimensions, mat, bevel=0.012):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish_mesh(obj, [mat], bevel)


def cylinder(name, center, radius, depth, mat, axis=None, vertices=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                     end_fill_type="NGON", location=center)
    obj = bpy.context.object
    obj.name = name
    if axis:
        obj.rotation_euler = Vector(axis).to_track_quat("Z", "Y").to_euler()
    return finish_mesh(obj, [mat], bevel=0.005)


def prism(name, polygon, bottom, top, mat, bevel=0.0):
    count = len(polygon)
    vertices = [(x, y, bottom) for x, y in polygon] + [(x, y, top) for x, y in polygon]
    faces = [tuple(reversed(range(count))), tuple(range(count, 2 * count))]
    faces += [(i, (i + 1) % count, (i + 1) % count + count, i + count) for i in range(count)]
    return mesh_object(name, vertices, faces, [mat], bevel)


def clip_x(polygon, boundary, greater):
    """Clip a convex deck outline into a genuinely shaped longitudinal plank."""
    output = []
    previous = polygon[-1]
    for current in polygon:
        inside_current = current[0] >= boundary if greater else current[0] <= boundary
        inside_previous = previous[0] >= boundary if greater else previous[0] <= boundary
        if inside_current != inside_previous:
            factor = (boundary - previous[0]) / (current[0] - previous[0])
            output.append((boundary, previous[1] + factor * (current[1] - previous[1])))
        if inside_current:
            output.append(current)
        previous = current
    return output


def build():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0

    cream = material("Cabin warm cream sRGB f4dfb3", "f4dfb3")
    navy = material("Deep sea navy upper hull and rail", "264653", 0.76)
    rust = material("Terracotta lower hull", "a34f39", 0.8)
    wood = material("Rich ochre deck foundation", "ad742f", 0.85)
    planks = [material("Golden timber plank %02d" % i, color, 0.84)
              for i, color in enumerate(("c3944c", "c99a53", "bd8b43", "c69750"))]
    crate = material("Ochre cargo panels", "b98038", 0.84)
    crate_edge = material("Honey cargo battens", "d0a058", 0.82)
    glass = material("Opaque muted blue cabin glazing", "5c91a0", 0.3)
    bronze = material("Weathered brass small fittings", "b89152", 0.56, 0.25)

    # Counterclockwise outline: rounded stern, broad working middle, pointed bow.
    starboard = [(0.0, -2.3), (0.35, -2.25), (0.60, -2.09), (0.755, -1.78),
                 (0.825, -1.23), (0.825, 0.53), (0.765, 1.08), (0.605, 1.60),
                 (0.335, 2.07), (0.0, 2.3)]
    outline = starboard + [(-x, y) for x, y in reversed(starboard[1:-1])]
    count = len(outline)

    # One capped, watertight bowl: external hull, thick inset upper wall, interior floor.
    # Top face is not filled over the opening; a separate inset timber deck lies inside it.
    rings = [(0.52, -0.35), (0.76, -0.23), (0.925, 0.0), (0.985, 0.22),
             (1.0, 0.575), (0.93, 0.575), (0.93, 0.395)]
    vertices = [(x * scale, y * scale, z) for scale, z in rings for x, y in outline]
    faces = [tuple(reversed(range(count)))]
    face_materials = [0]
    for level in range(len(rings) - 1):
        for index in range(count):
            following = (index + 1) % count
            faces.append((level * count + index, level * count + following,
                          (level + 1) * count + following, (level + 1) * count + index))
            face_materials.append(0 if level < 3 else 1)
    faces.append(tuple(range((len(rings) - 1) * count, len(rings) * count)))
    face_materials.append(2)
    hull = mesh_object("Shaped capped hull with real inset deck well", vertices, faces, [rust, navy, wood])
    for face, slot in zip(hull.data.polygons, face_materials):
        face.material_index = slot
        face.use_smooth = False

    # Capped raised rail follows the hull with no wireframe/black stroke geometry.
    rail_vertices = []
    for scale, z in ((1.0, 0.566), (1.0, 0.61), (0.921, 0.61), (0.921, 0.566)):
        rail_vertices += [(x * scale, y * scale, z) for x, y in outline]
    rail_faces = []
    for level in range(4):
        next_level = (level + 1) % 4
        for index in range(count):
            following = (index + 1) % count
            rail_faces.append((level * count + index, level * count + following,
                               next_level * count + following, next_level * count + index))
    mesh_object("Raised rounded navy gunwale", rail_vertices, rail_faces, [navy], bevel=0.009)

    deck_outline = [(x * 0.929, y * 0.929) for x, y in outline]
    prism("Inset solid timber deck", deck_outline, 0.395, 0.448, wood)
    for index in range(8):
        left = -0.77 + index * 0.193
        polygon = clip_x(clip_x(deck_outline, left + 0.006, True), left + 0.187, False)
        if len(polygon) >= 3:
            prism("Longitudinal deck plank %02d" % index, polygon, 0.447, 0.456,
                  planks[index % len(planks)])

    # Compact aft cabin, leaving the forward two thirds as a useful open cargo deck.
    box("Cream aft cabin", (0, -1.32, 0.884), (0.99, 1.05, 0.85), cream, 0.034)
    box("Cabin lower navy skirting", (0, -1.32, 0.501), (1.015, 1.075, 0.095), navy, 0.012)
    box("Cabin roof navy lip", (0, -1.32, 1.319), (1.14, 1.20, 0.082), navy, 0.022)
    box("Cream gently softened roof", (0, -1.32, 1.368), (1.11, 1.17, 0.064), cream, 0.022)
    for side in (-1, 1):
        box("Forward glazing %s" % side, (side * 0.23, -0.789, 1.048), (0.338, 0.026, 0.29), glass, 0.019)
        box("Forward cream window sill %s" % side, (side * 0.23, -0.77, 0.888),
            (0.374, 0.04, 0.035), cream, 0.009)
        box("Side glazing %s" % side, (side * 0.499, -1.28, 1.048),
            (0.023, 0.57, 0.30), glass, 0.017)
        box("Side window mullion %s" % side, (side * 0.514, -1.28, 1.048),
            (0.018, 0.026, 0.316), cream, 0.007)
    box("Aft timber cabin door", (0, -1.852, 0.855), (0.40, 0.027, 0.67), planks[2], 0.016)
    box("Aft small door glazing", (0, -1.869, 1.002), (0.255, 0.016, 0.25), glass, 0.013)
    box("Brass cabin door handle", (0.128, -1.888, 0.80), (0.021, 0.019, 0.072), bronze, 0.007)

    def cargo_box(name, x, y, width, depth, height):
        bottom = 0.456
        box(name + " closed ochre body", (x, y, bottom + height / 2),
            (width, depth, height), crate, 0.015)
        # Wide matte battens give the crate readable structure without dark outlines.
        for sx in (-1, 1):
            for sy in (-1, 1):
                box(name + " corner %s %s" % (sx, sy),
                    (x + sx * (width / 2 - 0.022), y + sy * (depth / 2 - 0.018), bottom + height / 2),
                    (0.059, 0.058, height + 0.013), crate_edge, 0.007)
        for z in (bottom + 0.038, bottom + height - 0.038):
            for sy in (-1, 1):
                box(name + " face batten %s %.2f" % (sy, z),
                    (x, y + sy * (depth / 2 + 0.006), z),
                    (width, 0.028, 0.063), crate_edge, 0.006)
        for sx in (-1, 1):
            box(name + " lid batten %s" % sx,
                (x + sx * width * 0.28, y, bottom + height + 0.008),
                (0.055, depth, 0.028), crate_edge, 0.006)

    cargo_box("Cargo A", -0.28, -0.05, 0.45, 0.49, 0.39)
    cargo_box("Cargo B", 0.28, 0.48, 0.42, 0.45, 0.35)
    cargo_box("Cargo C", -0.20, 1.04, 0.43, 0.44, 0.43)

    # A short aft mast stands on the roof rather than obscuring the forward deck.
    cylinder("Aft roof mast socket", (0, -1.59, 1.415), 0.075, 0.05, navy)
    cylinder("Short warm timber mast", (0, -1.59, 1.706), 0.029, 0.58, planks[2])
    cylinder("Small mast crossarm", (0, -1.59, 1.869), 0.018, 0.29, planks[1], axis=(1, 0, 0))
    cylinder("Small brass mast cap", (0, -1.59, 2.006), 0.037, 0.036, bronze)

    # Just one compact bow cleat; no characters, ropes, or unrelated scene props.
    for x in (-0.10, 0.10):
        cylinder("Bow cleat post %.1f" % x, (x, 1.82, 0.499), 0.026, 0.085, bronze)
    cylinder("Bow cleat crossbar", (0, 1.82, 0.542), 0.022, 0.30, bronze, axis=(1, 0, 0))

    bpy.context.scene["asset_purpose"] = "Temporary desktop tropical water scale demo; not final hero boat"
    bpy.context.scene["waterline_blender_z"] = 0.0
    bpy.context.scene["bow_axis_blender"] = "+Y"
    bpy.context.view_layer.update()


def validate_and_export(output_dir):
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if any(obj.type in {"LIGHT", "CAMERA"} for obj in bpy.context.scene.objects):
        raise RuntimeError("Asset scene must not contain lights or cameras")
    triangle_count = 0
    nonmanifold = []
    positions = []
    for obj in meshes:
        obj.data.calc_loop_triangles()
        triangle_count += len(obj.data.loop_triangles)
        positions.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        if any(not edge.is_manifold for edge in bm.edges):
            nonmanifold.append(obj.name)
        if bm.calc_volume(signed=True) <= 0:
            raise RuntimeError("Non-positive signed volume: " + obj.name)
        bm.free()
    if nonmanifold:
        raise RuntimeError("Uncapped or nonmanifold meshes: " + ", ".join(nonmanifold))
    if triangle_count > 10000:
        raise RuntimeError("Triangle budget exceeded: %s" % triangle_count)
    minimum = [min(point[axis] for point in positions) for axis in range(3)]
    maximum = [max(point[axis] for point in positions) for axis in range(3)]
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "test_boat.glb"
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(output), export_format="GLB", use_selection=True,
                              export_yup=True, export_materials="EXPORT", export_cameras=False,
                              export_lights=False, export_animations=False,
                              export_extras=False, export_texcoords=False,
                              export_normals=True, export_tangents=False)
    raw = output.read_bytes()
    magic, version, size = struct.unpack_from("<4sII", raw)
    if magic != b"glTF" or version != 2 or size != len(raw):
        raise RuntimeError("Invalid GLB header")
    json_size, chunk_type = struct.unpack_from("<II", raw, 12)
    if chunk_type != 0x4E4F534A:
        raise RuntimeError("Missing GLB JSON chunk")
    document = json.loads(raw[20:20 + json_size].decode("utf-8"))
    if document.get("images") or document.get("cameras"):
        raise RuntimeError("Unexpected images/cameras in export")
    if any("uri" in buffer for buffer in document.get("buffers", [])):
        raise RuntimeError("GLB contains external buffer dependencies")
    if "KHR_lights_punctual" in document.get("extensionsUsed", []):
        raise RuntimeError("Unexpected exported lights")
    gltf_triangles = sum(document["accessors"][primitive["indices"]]["count"] // 3
                         for mesh in document["meshes"] for primitive in mesh["primitives"])
    if gltf_triangles != triangle_count:
        raise RuntimeError("Export triangle count differs from Blender mesh count")
    print("BOAT_VALIDATION " + json.dumps({
        "file": str(output), "bytes": len(raw), "triangles": triangle_count,
        "closed_meshes": len(meshes), "materials": len(document.get("materials", [])),
        "bounds_blender_min": [round(value, 5) for value in minimum],
        "bounds_blender_max": [round(value, 5) for value in maximum],
        "dimensions_blender_xyz": [round(maximum[i] - minimum[i], 5) for i in range(3)],
        "bounds_godot_min": [round(minimum[0], 5), round(minimum[2], 5), round(-maximum[1], 5)],
        "bounds_godot_max": [round(maximum[0], 5), round(maximum[2], 5), round(-minimum[1], 5)],
        "bow_blender": "+Y", "bow_godot": "-Z", "waterline_godot_y": 0,
        "all_meshes_closed_positive_volume": True, "external_dependencies": False
    }, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_directory", type=Path)
    arguments = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    build()
    validate_and_export(arguments.output_directory)
