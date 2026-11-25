"""Author position-aware ground detail only through this round's GUI Blender MCP.

Reads the current cliff25 land/height raster and preserved route/court design.
Writes one linear RGBA PNG and packs it into the current source. No geometry,
LandUse, props, grass, camera, lighting, source save, or GLB export is performed.
R: brightness, G: warmth, B: shallow height (all .5 neutral); A: contact softness.
"""
import bpy
import hashlib
import json
import math
import os
import struct
import zlib
from pathlib import Path

import numpy as np

assert not bpy.app.background, "Execute inside the owned GUI Blender MCP"
ROOT = Path(bpy.data.filepath).parent.parent
LOG = ROOT / "captures/cliff_contacts_20261125"
OUT = ROOT / "assets/reference"
session = json.loads((LOG / "session_start.json").read_text(encoding="utf-8-sig"))
assert os.getpid() == session["pid"]
assert bpy.types.blendermcp_server.port == session["port"]
assert Path(bpy.data.filepath).resolve() == Path(session["file"]).resolve()
terrain = bpy.data.objects["C25_ContourBuiltCoast"]
land_path = LOG / "land_data.npz"
assert land_path.exists(), "Generate this round's actual land/height raster first"
data = np.load(land_path)
spec_path = LOG / "design.json"
spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
roles_full = data["land"]
height_full = data["height"]
normal_full = data["normal"]
assert roles_full.shape == (*height_full.shape, 4)
assert normal_full.shape == height_full.shape
assert np.isfinite(height_full).all() and np.isfinite(roles_full).all()

N = 1024
yy, xx = np.mgrid[:N, :N].astype(np.float32)
X = 7.0 + (xx + 0.5) * 20.0 / N
Z = 22.0 + (yy + 0.5) * 23.0 / N


def ss(a, b, value):
    t = np.clip((value - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def sample_world(array):
    """Bilinear sample the saved -4..44 / -15..82 actual-ground atlas."""
    rows, columns = array.shape[:2]
    fx = np.clip((X + 4.0) * columns / 48.0 - 0.5, 0, columns - 1.001)
    fy = np.clip((Z + 15.0) * rows / 97.0 - 0.5, 0, rows - 1.001)
    ix, iy = fx.astype(np.int32), fy.astype(np.int32)
    tx, ty = fx - ix, fy - iy
    if array.ndim == 3:
        tx, ty = tx[..., None], ty[..., None]
    return ((array[iy, ix] * (1 - tx) + array[iy, ix + 1] * tx) * (1 - ty)
            + (array[iy + 1, ix] * (1 - tx) + array[iy + 1, ix + 1] * tx) * ty)


def polygon_distance(poly):
    points = np.asarray(poly, float)
    inside = np.zeros(X.shape, bool)
    distance = np.full(X.shape, 1e5, np.float32)
    for a, b in zip(points, np.roll(points, -1, axis=0)):
        dx, dz = b - a
        length2 = dx * dx + dz * dz
        if length2 < 1e-10:
            continue
        if abs(dz) > 1e-10:
            inside ^= ((a[1] > Z) != (b[1] > Z)) & (X < dx * (Z - a[1]) / dz + a[0])
        t = np.clip(((X - a[0]) * dx + (Z - a[1]) * dz) / length2, 0, 1)
        distance = np.minimum(distance, np.hypot(X - a[0] - t * dx, Z - a[1] - t * dz))
    return np.where(inside, -distance, distance)


def organic_field(seed, count, radius_min, radius_max):
    """Unequal rotated clusters; no lattice, tiled noise, or fixed wave rows."""
    rng = np.random.default_rng(seed)
    numerator = np.zeros(X.shape, np.float32)
    denominator = np.full(X.shape, 0.7, np.float32)
    for _ in range(count):
        cx, cz = rng.uniform(5.5, 28.5), rng.uniform(20.5, 46.5)
        rx = rng.uniform(radius_min, radius_max)
        rz = rx * rng.uniform(0.5, 1.65)
        angle = rng.uniform(0, math.tau)
        dx, dz = X - cx, Z - cz
        a = (dx * math.cos(angle) + dz * math.sin(angle)) / rx
        b = (-dx * math.sin(angle) + dz * math.cos(angle)) / rz
        weight = np.exp(-1.7 * (a * a + b * b))
        numerator += weight * rng.uniform(-1.0, 1.0)
        denominator += weight
    return numerator / denominator


roles = np.clip(sample_world(roles_full), 0, 1)
roles /= np.maximum(roles.sum(axis=2), 1.0)[..., None]
grass, rock, path, soil = np.moveaxis(roles, -1, 0)
sand = np.maximum(1.0 - roles.sum(axis=2), 0)
height = sample_world(height_full)
normal = np.clip(sample_world(normal_full), 0, 1)
broad = organic_field(252501, 54, 1.15, 3.25)
secondary = organic_field(252502, 88, 0.32, 1.15)
warm_field = organic_field(252503, 31, 1.4, 3.4)

# Signed distance to the entire route/court union; intersecting paths never get
# artificial loose-soil lines inside their junctions. Actual LandUse remains
# authoritative, so these controls cannot paint a new road outside it.
road_distance = np.full(X.shape, 1e5, np.float32)
route_count = 0
platform_count = 0
for route in spec["routes"]:
    if route.get("paint_strength", 1.0) <= 0:
        continue
    points = np.asarray(route["points"], float)
    width = float(route.get("paint_halfwidth", route["halfwidth"]))
    if points[:, 0].max() + width + 1 < 7 or points[:, 0].min() - width - 1 > 27:
        continue
    if points[:, 1].max() + width + 1 < 22 or points[:, 1].min() - width - 1 > 45:
        continue
    route_count += 1
    for a, b in zip(points, points[1:]):
        dx, dz = b[:2] - a[:2]
        length2 = dx * dx + dz * dz
        if length2 < 1e-10:
            continue
        t = np.clip(((X - a[0]) * dx + (Z - a[1]) * dz) / length2, 0, 1)
        distance = np.hypot(X - a[0] - t * dx, Z - a[1] - t * dz) - width
        road_distance = np.minimum(road_distance, distance)
for platform in spec["platforms"]:
    if platform.get("paint_strength", 1.0) <= 0:
        continue
    points = np.asarray(platform["polygon"], float)
    if points[:, 0].max() + 1 < 7 or points[:, 0].min() - 1 > 27:
        continue
    if points[:, 1].max() + 1 < 22 or points[:, 1].min() - 1 > 45:
        continue
    platform_count += 1
    road_distance = np.minimum(road_distance, polygon_distance(points))

flat = ss(0.65, 0.94, normal)
road_core = (1 - ss(-0.44, -0.10, road_distance)) * flat
ragged_rim = road_distance + 0.035 + secondary * 0.26
road_rim = np.exp(-(ragged_rim / (0.22 + broad * 0.10)) ** 2) * flat

# Detect nearby exposed rock using the actual role raster, then keep the small
# dark soil pocket on the lower non-rock contact. No global cliff-foot stripe.
near_rock = rock.copy()
for radius in (6, 12, 20):
    for dy, dx in ((radius, 0), (-radius, 0), (0, radius), (0, -radius),
                   (radius, radius), (radius, -radius), (-radius, radius), (-radius, -radius)):
        shifted = np.roll(np.roll(rock, dy, axis=0), dx, axis=1)
        near_rock = np.maximum(near_rock, shifted)
foot_pocket = ss(0.10, 0.55, near_rock) * (1 - ss(0.08, 0.40, rock))
foot_pocket *= 0.45 + ss(-0.12, 0.18, broad) * 0.55
shore_wet = (1 - ss(0.045, 0.38, height)) * ss(-0.16, 0.01, height)
# One broad low swell follows true sand elevation/deposition, not an arbitrary
# set of parallel XY lines. At .020m height range it stays millimetres deep.
sand_swell = np.sin(height * 9.0 + broad * 0.65) * (1 - shore_wet * 0.70)

# Keep a readable scale between compressed walking earth, loose uneven rims,
# broad grass tufts, and shallow sand deposition at the ordinary game camera.
# All fields are tied to the shared route/court union or actual ground roles.
brightness_grass = 0.50 + broad * 0.82 + secondary * 0.22 - road_rim * 0.065
brightness_path = 0.48 + road_core * 0.075 - road_rim * 0.25 + broad * 0.32 + secondary * 0.15
brightness_soil = 0.48 + broad * 0.38 + secondary * 0.18 - foot_pocket * 0.14
brightness_sand = 0.53 + broad * 0.17 + secondary * 0.035 - shore_wet * 0.28 + sand_swell * 0.035
brightness = (brightness_grass * grass + brightness_path * path + brightness_soil * soil
              + brightness_sand * sand + 0.5 * rock)
warmth = (0.5 + (warm_field * 0.36 + broad * 0.12) * grass
          + (0.065 * road_rim - 0.020 * road_core) * path
          + (foot_pocket * 0.04 + warm_field * 0.14) * soil
          + (0.04 - shore_wet * 0.12) * sand)
surface_height = (0.5 + (broad * 0.20 + secondary * 0.09) * grass
                  + (-road_core * 0.055 + road_rim * 0.065 + secondary * 0.045) * path
                  + (broad * 0.11 + secondary * 0.09) * soil
                  + sand_swell * 0.075 * sand)
two = np.sort(np.concatenate((roles, sand[..., None]), axis=2), axis=2)[..., -2:]
competition = two[..., 0] / np.maximum(two[..., 1], 0.001)
softness = ss(0.04, 0.30, competition) * (1 - ss(0.05, 0.35, rock))
softness *= np.clip(0.85 + broad * 0.25, 0.6, 1.0)
rgba = np.stack((brightness, warmth, surface_height, softness), axis=2)
rgba[..., :3] = np.clip(rgba[..., :3], 0.20, 0.80)
rgba[..., 3] = np.clip(rgba[..., 3], 0, 1)
assert np.isfinite(rgba).all()


def chunk(kind, payload):
    return (struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF))


name = "C25_GroundDetail"
destination = OUT / (name + ".png")
pixels = np.round(rgba[::-1] * 255).astype(np.uint8)
raw = b"".join(b"\0" + row.tobytes() for row in pixels)
destination.write_bytes(b"\x89PNG\r\n\x1a\n"
                       + chunk(b"IHDR", struct.pack(">IIBBBBB", N, N, 8, 6, 0, 0, 0))
                       + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
image = bpy.data.images.get(name)
if image:
    bpy.data.images.remove(image)
image = bpy.data.images.load(str(destination), check_existing=False)
image.name = name
image.colorspace_settings.name = "Non-Color"
image.alpha_mode = "CHANNEL_PACKED"
image.pack()
material = terrain.data.materials[0]
node = material.node_tree.nodes.get(name) or material.node_tree.nodes.new("ShaderNodeTexImage")
node.name = name
node.label = "C25: brightness / warmth / shallow height / contact softness (linear)"
node.image = image
terrain["cliff25_ground_detail"] = True
report = {
    "authoring": "owned GUI Blender MCP", "image": destination.name,
    "size": [N, N], "world_x": [7.0, 27.0], "world_z": [22.0, 45.0],
    "channels": ["brightness_neutral_0.5", "warmth_neutral_0.5", "height_neutral_0.5", "contact_softness"],
    "linear_data": True, "source_image_packed": bool(image.packed_file),
    "source_save_required": True, "geometry_modified": False, "land_use_modified": False,
    "route_count_in_region": route_count, "platform_count_in_region": platform_count,
    "input_land_sha256": hashlib.sha256(land_path.read_bytes()).hexdigest(),
    "input_design_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
    "output_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
    "channel_min": rgba.min(axis=(0, 1)).tolist(), "channel_max": rgba.max(axis=(0, 1)).tolist(),
    "height_range_m": 0.020, "iteration": 2, "visual_accepted": False,
}
(LOG / "ground_detail.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
