"""Scoped Blender-MCP helpers for the v7 material sample; no external services."""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import bpy

SOURCE = Path(__file__).resolve().parent
ASSET = SOURCE.parent
INPUT = Path(r"C:/Users/51440/Downloads/harbor dock 3d model.glb")
INPUT_SHA = "b809395557fa853da7ef64f20a267515974bc3e5d58598a8ba64c86f4317a85c"
REFERENCE_SCENE = "INS7_Reference"
SAMPLE_SCENE = "INS7_StyleSample"


def verify_input():
    assert hashlib.sha256(INPUT.read_bytes()).hexdigest() == INPUT_SHA, "Original GLB changed"


def fresh(path):
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path, value):
    fresh(path).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


@contextmanager
def preserve_session():
    window = bpy.context.window
    scene, layer = window.scene, window.view_layer
    active = layer.objects.active
    selected = list(bpy.context.selected_objects)
    mode = active.mode if active else "OBJECT"
    filepath = bpy.data.filepath
    try:
        if mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        yield
    finally:
        if bpy.context.object and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        window.scene, window.view_layer = scene, layer
        for obj in layer.objects:
            obj.select_set(False)
        for obj in selected:
            if obj.name in layer.objects:
                obj.select_set(True)
        layer.objects.active = active
        if active and mode != "OBJECT":
            bpy.ops.object.mode_set(mode=mode)
        assert bpy.data.filepath == filepath, "Live Blender file identity changed"


def switch(scene):
    bpy.context.window.scene = scene
    bpy.context.window.view_layer = scene.view_layers[0]


def independent_scene(name):
    assert name not in bpy.data.scenes, f"Stage already exists: {name}; inspect before retrying"
    scene = bpy.data.scenes.new(name)
    scene.unit_settings.system = "METRIC"
    switch(scene)
    return scene


def bounds(objects):
    from mathutils import Vector
    points = [obj.matrix_world @ Vector(corner) for obj in objects if obj.type == "MESH" for corner in obj.bound_box]
    return [[min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]]
