"""G23 surface revision. Execute only inside the owned GUI Blender via MCP.

Writes the five RGBA surface PNGs and replaces their packed Blender images.
Does not touch LandUse, mesh geometry, runtime shader, lighting or camera.
RGB is sRGB reflectance; alpha is independent linear height, never opacity.
The caller coordinates source saving/export after its geometry pass.
"""
import ast
import bpy
import json
import math
import struct
import zlib
from pathlib import Path

import numpy as np

assert not bpy.app.background, 'Run this authoring pass through the owned GUI Blender MCP'
assert bpy.data.filepath, 'Open the project source first'
ROOT = Path(bpy.data.filepath).parent.parent
OUT = ROOT / 'assets/reference'
LOG = ROOT / 'captures/ground_integration_20261123'
terrain = bpy.data.objects.get('C25_ContourBuiltCoast')
assert terrain is not None and terrain.type == 'MESH', 'Wrong Blender source'
assert (OUT / 'G23_LandUse.png').is_file(), 'G23 integration is missing'
OUT.mkdir(parents=True, exist_ok=True)
LOG.mkdir(parents=True, exist_ok=True)

# Load only stateless authoring helpers, never replay the old script body.
for helper in ast.parse((ROOT / 'source/ground23_02_surfaces.py').read_text(encoding='utf8')).body:
    if isinstance(helper, ast.FunctionDef) and helper.name in ('ss', 'noise', 'ellipse', 'save_image'):
        exec(compile(ast.Module(body=[helper], type_ignores=[]), 'G23 texture helpers', 'exec'), globals())

SPECS = {
    'Grass': {'tile_m': 6.0, 'height_range_m': 0.025, 'size': 1024},
    'Rock': {'tile_m': 8.0, 'height_range_m': 0.38, 'size': 2048},
    'Path': {'tile_m': 4.0, 'height_range_m': 0.012, 'size': 1024},
    'Soil': {'tile_m': 4.0, 'height_range_m': 0.050, 'size': 1024},
    'Sand': {'tile_m': 6.0, 'height_range_m': 0.012, 'size': 2048},
}
images = {}
stats = {}


def store_surface(role, rgb, height):
    """Keep all alpha data independent of sRGB and report clipping/repeat limits."""
    assert rgb.shape == (*height.shape, 3)
    assert np.isfinite(rgb).all() and np.isfinite(height).all()
    name = 'G23_' + role
    clipped = np.clip(height, 0.0, 1.0)
    images[name] = save_image(name, rgb, clipped)
    step = SPECS[role]['tile_m'] / len(height)
    slope_x = (np.roll(clipped, -1, axis=1) - np.roll(clipped, 1, axis=1))
    slope_y = (np.roll(clipped, -1, axis=0) - np.roll(clipped, 1, axis=0))
    slope = np.hypot(slope_x, slope_y) * SPECS[role]['height_range_m'] / (2 * step)
    stats[role] = {
        **SPECS[role],
        'rgb_mean': np.mean(rgb, axis=(0, 1)).tolist(),
        'height_min': float(height.min()),
        'height_max': float(height.max()),
        'height_clip_fraction': float(np.mean((height < 0) | (height > 1))),
        'slope_p50_p90_p99': np.percentile(slope, [50, 90, 99]).tolist(),
    }


def fractured_height(n, cells, seed):
    """Periodic continuous broad planes; no grooves, mortar, cell rims or sun bake.

    A jittered control net is rasterized into an image, never into Blender mesh.
    Adjacent faces share heights at edges. Random diagonal choices and strongly
    displaced control points avoid horizontal masonry rows. Material color is
    independent of these faces, so this is a normal field rather than a mosaic.
    """
    rng = np.random.default_rng(seed)
    jitter = rng.uniform(-0.32, 0.32, (cells, cells, 2))
    values = np.clip(0.50 + rng.uniform(-0.27, 0.27, (cells, cells))
                     + noise(cells, 3, seed + 3) * 0.19, 0.16, 0.84)
    diagonals = rng.random((cells, cells)) > 0.5
    result = np.zeros((n, n), np.float32)
    covered = np.zeros((n, n), bool)

    def point(i, j):
        offset = jitter[j % cells, i % cells]
        return ((i + offset[0]) / cells, (j + offset[1]) / cells,
                values[j % cells, i % cells])

    def signed_area(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def raster_triangle(a, b, c):
        x0 = max(0, int(math.floor(min(a[0], b[0], c[0]) * n)))
        x1 = min(n, int(math.ceil(max(a[0], b[0], c[0]) * n)) + 1)
        y0 = max(0, int(math.floor(min(a[1], b[1], c[1]) * n)))
        y1 = min(n, int(math.ceil(max(a[1], b[1], c[1]) * n)) + 1)
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32) / n
        divisor = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        assert abs(divisor) > 1e-9
        u = ((b[1] - c[1]) * (xx - c[0]) + (c[0] - b[0]) * (yy - c[1])) / divisor
        v = ((c[1] - a[1]) * (xx - c[0]) + (a[0] - c[0]) * (yy - c[1])) / divisor
        w = 1 - u - v
        inside = (u >= -1e-6) & (v >= -1e-6) & (w >= -1e-6)
        local = result[y0:y1, x0:x1]
        local[inside] = (u * a[2] + v * b[2] + w * c[2])[inside]
        covered[y0:y1, x0:x1] |= inside

    for j in range(-1, cells + 1):
        for i in range(-1, cells + 1):
            a, b, c, d = point(i, j), point(i + 1, j), point(i + 1, j + 1), point(i, j + 1)
            # Strong jitter can make a quad concave; choose its valid internal
            # diagonal before rasterizing, instead of overlapping a neighbour.
            first_valid = signed_area(a, b, c) > 0 and signed_area(a, c, d) > 0
            second_valid = signed_area(a, b, d) > 0 and signed_area(b, c, d) > 0
            assert first_valid or second_valid
            use_first = first_valid and (not second_valid or diagonals[j % cells, i % cells])
            if use_first:
                raster_triangle(a, b, c)
                raster_triangle(a, c, d)
            else:
                raster_triangle(a, b, d)
                raster_triangle(b, c, d)
    assert covered.all(), 'Unexpected hole in the periodic height image'
    return result


# Rock: the height image covers every pixel with mineral break planes. The old
# 16 m/0.22 m setup could only tilt its large planes by a few degrees. At 8 m,
# these unequal 0.6-1.7 m faces produce readable changes in the live sun response.
n = SPECS['Rock']['size']
broad = noise(n, 5, 1101)
mineral = noise(n, 18, 1102)
grain = noise(n, 147, 1103)
primary = fractured_height(n, 8, 1121)
secondary = fractured_height(n, 19, 1122)
height = 0.50 + (primary - 0.50) * 1.30 + (secondary - 0.50) * 0.10 + grain * 0.007
rgb = np.empty((n, n, 3), np.float32)
rgb[:] = [0.413, 0.433, 0.399]
rgb += (broad * 0.058 + mineral * 0.025 + grain * 0.009)[..., None]
rgb += mineral[..., None] * np.array([0.014, 0.003, -0.014])
store_surface('Rock', rgb, height)
del primary, secondary

# Grass: short leaf groups have modest reflectance contrast and rotate over the
# whole tile. No long bright 5-14 cm strokes, combed field, or dark tuft outline.
n = SPECS['Grass']['size']
broad = noise(n, 4, 1201)
mid = noise(n, 23, 1202)
fine = noise(n, 157, 1203)
rgb = np.empty((n, n, 3), np.float32)
rgb[:] = [0.307, 0.401, 0.164]
rgb += (broad * 0.032 + mid * 0.018 + fine * 0.008)[..., None] * [0.88, 1.0, 0.60]
height = 0.44 + broad * 0.07 + mid * 0.06 + fine * 0.025
rng = np.random.default_rng(1224)
for k in range(5100):
    cx, cy = rng.random(2)
    if rng.random() < 0.19 and broad[int(cy * n) % n, int(cx * n) % n] < -0.08:
        continue
    angle = rng.uniform(0, math.tau)
    for leaf in range(2):
        a = angle + rng.uniform(-1.05, 1.05)
        length = rng.uniform(0.0018, 0.0048)
        tint = rng.uniform(-0.005, 0.014)
        ellipse(rgb, height, cx + math.cos(a) * length * 0.25,
                cy + math.sin(a) * length * 0.25, length,
                rng.uniform(0.0007, 0.0013), a,
                [tint * 0.8, tint, tint * 0.5], rng.uniform(0.035, 0.10), 0.55)
store_surface('Grass', rgb, height)

# Footpath: retain warm compressed soil, with broad worn patches and embedded
# mineral particles. Small grains have material variation, never baked shadows.
n = SPECS['Path']['size']
broad = noise(n, 5, 1301)
mid = noise(n, 29, 1302)
grain = noise(n, 151, 1303)
rgb = np.empty((n, n, 3), np.float32)
rgb[:] = [0.539, 0.459, 0.345]
rgb += (broad * 0.062 + mid * 0.032 + grain * 0.018)[..., None] * [1.0, 0.92, 0.77]
height = 0.44 + mid * 0.10 + grain * 0.095
rng = np.random.default_rng(1324)
for k in range(1250):
    cx, cy = rng.random(2)
    radius = rng.uniform(0.0012, 0.0048)
    tint = rng.uniform(-0.035, 0.045)
    ellipse(rgb, height, cx, cy, radius, radius * rng.uniform(0.52, 0.88),
            rng.uniform(0, math.tau), [tint, tint * 0.93, tint * 0.80],
            rng.uniform(0.025, 0.12), 0.35)
store_surface('Path', rgb, height)

# Soil: a coarse granular matrix with unequal, closely seated dry aggregates.
# The clods have no displaced painted highlight/dark skirt pair.
n = SPECS['Soil']['size']
broad = noise(n, 5, 1401)
mid = noise(n, 31, 1402)
grain = noise(n, 169, 1403)
rgb = np.empty((n, n, 3), np.float32)
rgb[:] = [0.470, 0.365, 0.246]
rgb += (broad * 0.065 + mid * 0.042 + grain * 0.026)[..., None] * [1.0, 0.88, 0.67]
height = 0.36 + broad * 0.08 + mid * 0.17 + grain * 0.075
rng = np.random.default_rng(1424)
for k in range(1050):
    cx, cy = rng.random(2)
    radius = rng.uniform(0.0035, 0.014)
    tint = rng.uniform(-0.026, 0.038)
    ellipse(rgb, height, cx, cy, radius, radius * rng.uniform(0.55, 0.90),
            rng.uniform(0, math.tau), [tint, tint * 0.86, tint * 0.66],
            rng.uniform(0.06, 0.21), 0.45)
store_surface('Soil', rgb, height)

# Sand: calm broad areas with low shallow variation and sparse deposited grit.
# Fine structure stays below the coarse grains, avoiding a screen of dark noise.
n = SPECS['Sand']['size']
broad = noise(n, 4, 1501)
mid = noise(n, 25, 1502)
grain = noise(n, 231, 1503)
rgb = np.empty((n, n, 3), np.float32)
rgb[:] = [0.783, 0.709, 0.552]
rgb += (broad * 0.044 + mid * 0.020 + grain * 0.017)[..., None] * [1.0, 0.96, 0.84]
height = 0.47 + mid * 0.09 + grain * 0.13
rng = np.random.default_rng(1524)
for k in range(1050):
    cx, cy = rng.random(2)
    radius = rng.uniform(0.0007, 0.0023)
    tint = rng.uniform(-0.044, 0.030)
    ellipse(rgb, height, cx, cy, radius, radius * rng.uniform(0.52, 0.90),
            rng.uniform(0, math.tau), [tint, tint * 0.95, tint * 0.84],
            rng.uniform(0.025, 0.11), 0.35)
store_surface('Sand', rgb, height)

# Reconnect the existing source preview and the image archive nodes only.
# Runtime scale/range changes are deliberately left to the coordinating agent.
material = terrain.data.materials[0]
for role in SPECS:
    name = 'G23_' + role
    archive = material.node_tree.nodes.get(name) or material.node_tree.nodes.new('ShaderNodeTexImage')
    archive.name = name
    archive.label = name + ' | RGB reflectance / A height'
    archive.image = images[name]
    preview = material.node_tree.nodes.get('G23Preview ' + role)
    if preview is not None and preview.type == 'TEX_IMAGE':
        preview.image = images[name]

report = {
    'authoring': 'Owned GUI Blender MCP, image authoring only',
    'rgb': 'sRGB reflectance',
    'alpha': 'independent linear height, CHANNEL_PACKED',
    'sun_shadows_baked': False,
    'land_use_modified': False,
    'geometry_modified': False,
    'runtime_modified': False,
    'source_save_required': True,
    'recommended_surface_parameters': stats,
    'rock_design': 'Full coverage, continuous uneven mineral planes; no outlined cells or fissure overlay',
    'grass_design': 'Low-contrast short leaves, varied local orientations and density, larger repeat domain',
}
(LOG / 'surface_revision_11.json').write_text(json.dumps(report, indent=2), encoding='utf8')
bpy.context.view_layer.update()
print(json.dumps({'generated': list(images), 'parameters': SPECS,
                  'source_save_required': True, 'report': str(LOG / 'surface_revision_11.json')}))
