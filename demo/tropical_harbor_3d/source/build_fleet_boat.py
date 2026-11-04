"""Build the reference-led open timber cargo boat, without changing the water-study boat.

blender --background --factory-startup --python build_fleet_boat.py -- assets
"""
import math
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_test_boat as geo
import bpy
from mathutils import Vector


# Blender +Y is bow; export maps this to Godot -Z. Waterline is Z=0.
STARBOARD = [(0.0, -2.22), (0.50, -2.22), (0.69, -1.84), (0.83, -1.28),
             (0.90, -0.65), (0.90, 0.50), (0.81, 1.10), (0.60, 1.70),
             (0.27, 2.10), (0.0, 2.32)]
OUTLINE = STARBOARD + [(-x, y) for x, y in reversed(STARBOARD[1:-1])]
DECK_TOP = 0.28


def sheer(y):
    return 0.085 * (max(0.0, abs(y) - 0.9) / 1.42) ** 1.7


def ring(scale, height, lift=1.0):
    return [(x * scale, y * scale, height + sheer(y) * lift) for x, y in OUTLINE]


def band(name, low_scale, high_scale, low, high, width, mat, bevel=0.003):
    n = len(OUTLINE)
    vertices = (ring(low_scale, low) + ring(high_scale, high)
                + ring(high_scale - width, high) + ring(low_scale - width, low))
    faces = []
    for level in range(4):
        for i in range(n):
            j = (i + 1) % n
            faces.append((level * n + i, level * n + j,
                          ((level + 1) % 4) * n + j, ((level + 1) % 4) * n + i))
    return geo.mesh_object(name, vertices, faces, [mat], bevel)


def beam(name, start, end, width, depth, mat):
    a, b = Vector(start), Vector(end)
    obj = geo.box(name, (a + b) / 2, (width, depth, (b - a).length), mat, 0.006)
    obj.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler()
    return obj


def width_at(y):
    for a, b in zip(STARBOARD[1:], STARBOARD[2:]):
        if a[1] <= y <= b[1]:
            t = (y - a[1]) / (b[1] - a[1])
            return a[0] + (b[0] - a[0]) * t
    raise ValueError('Outside working hull')


def build():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system = 'METRIC'
    wood = [geo.material('Hull honey timber %02d' % i, c)
            for i, c in enumerate(('926447', 'a47650', 'b4875b', 'bb9468'))]
    floor = [geo.material('Floor warm timber %02d' % i, c)
             for i, c in enumerate(('b68e60', 'c29c6d', 'b99464', 'c4a174'))]
    frame = geo.material('Structural aged timber', '73543c')
    endgrain = geo.material('Seat end grain', 'a88155')
    peg = geo.material('Wooden fastening pins', '634b38')

    # Closed lower bowl, then separate, thick strakes. Gaps are above the waterline.
    n = len(OUTLINE)
    vertices = ring(0.45, -0.30, 0.0) + ring(0.71, -0.14, 0.2) + ring(0.86, 0.17)
    vertices += ring(0.78, 0.17) + ring(0.66, -0.07, 0.0)
    faces = [tuple(reversed(range(n)))]
    for level in range(4):
        for i in range(n):
            j = (i + 1) % n
            faces.append((level * n + i, level * n + j, (level + 1) * n + j, (level + 1) * n + i))
    faces.append(tuple(range(4 * n, 5 * n)))
    geo.mesh_object('Closed lower timber hull', vertices, faces, [wood[0]])
    for i in range(4):
        low = 0.165 + i * 0.115
        band('Side strake %02d' % i, 0.86 + i * 0.035, 0.895 + i * 0.035,
             low, low + 0.110, 0.055, wood[i])
    band('Continuous shaped gunwale', 1.006, 1.006, 0.619, 0.665, 0.085, frame, 0.006)
    band('Fine outer rubbing strip', 0.978, 0.978, 0.484, 0.508, 0.020, frame, 0.003)

    # Low floorboards leave the side planks and ribs visible inside the open boat.
    deck_outline = [(x * 0.825, y * 0.825) for x, y in OUTLINE]
    geo.prism('Floor foundation', deck_outline, 0.215, 0.25, frame)
    for i in range(9):
        left = -0.747 + i * 0.166
        polygon = geo.clip_x(geo.clip_x(deck_outline, left + 0.004, True), left + 0.158, False)
        if len(polygon) >= 3:
            geo.prism('Floorboard %02d' % i, polygon, 0.246, DECK_TOP, floor[i % 4], 0.002)
    # Ribs follow the flared side wall, outside the four crew standing areas.
    for i, y in enumerate((-1.55, -1.04, -0.30, 0.36, 1.04, 1.53)):
        outer = width_at(y)
        for side in (-1, 1):
            beam('Inner rib %02d %s' % (i, side), (side * outer * 0.833, y, 0.277),
                 (side * outer * 0.940, y, 0.621 + sheer(y)), 0.045, 0.065, frame)
    for i, y in enumerate((-1.52, 1.50)):
        width = width_at(y) * 1.77
        geo.box('End thwart %02d' % i, (0, y, 0.466 + sheer(y)), (width, 0.27, 0.069), floor[1], 0.008)
        for side in (-1, 1):
            geo.box('Thwart support %02d %s' % (i, side), (side * width * 0.39, y, 0.36),
                    (0.065, 0.21, 0.19), frame, 0.005)
            geo.cylinder('Thwart pin %02d %s' % (i, side), (side * width * 0.40, y, 0.505 + sheer(y)),
                         0.016, 0.008, peg, vertices=8)
    geo.box('Flat stern transom capping', (0, -2.217, 0.698), (0.96, 0.10, 0.085), endgrain, 0.009)
    beam('Raised bow stem', (0, 2.16, 0.35), (0, 2.33, 0.78), 0.065, 0.08, frame)
    # A low stern pennant support replaces the former roof mast, away from cargo/crew.
    geo.cylinder('Low stern pennant post', (0, -1.91, 0.72), 0.019, 0.70, frame, vertices=10)
    bpy.context.view_layer.update()
    for obj in bpy.context.scene.objects:
        if any(word in obj.name.lower() for word in ('cabin', 'roof', 'glazing')):
            raise RuntimeError('Open boat must not contain cabin geometry')
    if max((obj.matrix_world @ Vector(c)).z for obj in bpy.context.scene.objects for c in obj.bound_box) > 1.1:
        raise RuntimeError('Unoccupied boat silhouette must remain low')


build()
output = Path(sys.argv[sys.argv.index('--') + 1])
output.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='fleet-boat-') as scratch:
    geo.validate_and_export(Path(scratch))
    shutil.copyfile(Path(scratch) / 'test_boat.glb', output / 'fleet_boat.glb')
print('FLEET_BOAT_PASS open_hull=True deck_top=', DECK_TOP, output / 'fleet_boat.glb')
