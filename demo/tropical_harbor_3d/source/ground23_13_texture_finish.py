"""Restore readable G23 grass / packed path / sand surfaces in live Blender MCP.

Only these three PNGs and their existing image nodes are updated. Rock retains
the complete folded height map from step 11; coordinate its 0.70 m range in the
runtime shader. No mesh, LandUse, soil, runtime code or scene save is performed.
"""
import ast
import bpy
import json
import math
import struct
import zlib
from pathlib import Path

import numpy as np

assert not bpy.app.background, 'Execute through the owned GUI Blender MCP'
assert bpy.data.filepath, 'Open the project source first'
ROOT = Path(bpy.data.filepath).parent.parent
OUT = ROOT / 'assets/reference'
LOG = ROOT / 'captures/ground_integration_20261123'
terrain = bpy.data.objects.get('C25_ContourBuiltCoast')
assert terrain is not None and terrain.type == 'MESH', 'Wrong Blender source'
assert (OUT / 'G23_Rock.png').is_file(), 'Step 11 surface set is missing'
LOG.mkdir(parents=True, exist_ok=True)

# Extract function definitions only. Never replay the stateful authoring bodies.
for filename, names in (
    ('ground23_02_surfaces.py', ('ss', 'noise', 'ellipse', 'save_image')),
    ('ground23_11_surface_revision.py', ('store_surface',)),
):
    tree = ast.parse((ROOT / 'source' / filename).read_text(encoding='utf8'))
    for helper in tree.body:
        if isinstance(helper, ast.FunctionDef) and helper.name in names:
            exec(compile(ast.Module(body=[helper], type_ignores=[]), 'G23 surface helper', 'exec'), globals())

SPECS = {
    'Grass': {'tile_m': 5.0, 'height_range_m': 0.040, 'size': 1024},
    'Path': {'tile_m': 4.0, 'height_range_m': 0.012, 'size': 1024},
    'Sand': {'tile_m': 6.0, 'height_range_m': 0.012, 'size': 2048},
}
images = {}
stats = {}

# Readable short clusters with a hierarchy of dense and thin patches. Four to
# eight centimetres is full leaf length: ellipse radius is half of that value.
n = SPECS['Grass']['size']
tile = SPECS['Grass']['tile_m']
broad = noise(n, 5, 2301)
density = ss(-0.28, 0.28, broad * 0.78 + noise(n, 11, 2302) * 0.35)
mid = noise(n, 29, 2303)
fine = noise(n, 131, 2304)
rgb = np.empty((n, n, 3), np.float32)
rgb[:] = [0.307, 0.405, 0.157]
rgb += (broad * 0.056 + mid * 0.027 + fine * 0.012)[..., None] * [0.88, 1.0, 0.55]
rgb += (density - 0.5)[..., None] * [-0.008, 0.012, -0.005]
height = 0.40 + broad * 0.065 + mid * 0.065 + fine * 0.035
rng = np.random.default_rng(2324)
tuft_count = 0
leaf_count = 0
for k in range(8200):
    cx, cy = rng.random(2)
    local_density = float(density[int(cy * n) % n, int(cx * n) % n])
    if rng.random() > 0.22 + local_density * 0.76:
        continue
    tuft_count += 1
    angle = rng.uniform(0, math.tau)
    radius = rng.uniform(0.0035, 0.0075)
    # Root mat is broad and weak; leaves carry the visible variation.
    ellipse(rgb, height, cx, cy, radius, radius * rng.uniform(0.65, 0.95), angle,
            [-0.010, -0.013, -0.006], -0.026, 0.65)
    for blade in range(3 if local_density < 0.50 else 4):
        leaf_count += 1
        a = angle + rng.uniform(-0.92, 0.92)
        length = rng.uniform(0.04, 0.08) / (2 * tile)
        width = rng.uniform(0.012, 0.023) / (2 * tile)
        variation = rng.uniform(0.028, 0.055)
        if rng.random() < 0.18:
            variation *= -0.55
        bx = cx + math.cos(a) * length * rng.uniform(0.25, 0.60)
        by = cy + math.sin(a) * length * rng.uniform(0.25, 0.60)
        ellipse(rgb, height, bx, by, length, width, a,
                [variation * 0.81, variation, variation * 0.44],
                rng.uniform(0.085, 0.19), 0.42)
store_surface('Grass', rgb, height)
stats['Grass'].update({'tufts': tuft_count, 'leaves': leaf_count,
                       'leaf_full_length_m': [0.04, 0.08],
                       'green_leaf_contrast': [0.028, 0.055]})

# Warm compacted path. Quiet worn patches alternate with embedded aggregates;
# the 0.10-0.30 m patches remain legible after normal game-distance mip filtering.
n = SPECS['Path']['size']
tile = SPECS['Path']['tile_m']
broad = noise(n, 5, 2401)
mid = noise(n, 27, 2402)
grain = noise(n, 151, 2403)
rgb = np.empty((n, n, 3), np.float32)
rgb[:] = [0.542, 0.463, 0.350]
rgb += (broad * 0.067 + mid * 0.034 + grain * 0.020)[..., None] * [1.0, 0.92, 0.77]
height = 0.44 + mid * 0.10 + grain * 0.095
rng = np.random.default_rng(2424)
for k in range(150):
    cx, cy = rng.random(2)
    radius = rng.uniform(0.10, 0.30) / (2 * tile)
    angle = rng.uniform(0, math.tau)
    tint = rng.uniform(-0.040, 0.038)
    ellipse(rgb, height, cx, cy, radius, radius * rng.uniform(0.55, 0.90), angle,
            [tint, tint * 0.91, tint * 0.77], rng.uniform(-0.07, 0.055), 0.55)
    # Offset a smaller connected lobe: patches have unequal outlines, not disks.
    ellipse(rgb, height, cx + math.cos(angle) * radius * 0.55,
            cy + math.sin(angle) * radius * 0.55, radius * 0.55,
            radius * 0.45, angle + 0.5, [tint * 0.35, tint * 0.31, tint * 0.27],
            rng.uniform(-0.025, 0.025), 0.65)
for k in range(1450):
    cx, cy = rng.random(2)
    radius = rng.uniform(0.0013, 0.0050)
    tint = rng.uniform(-0.042, 0.051)
    ellipse(rgb, height, cx, cy, radius, radius * rng.uniform(0.52, 0.88),
            rng.uniform(0, math.tau), [tint, tint * 0.93, tint * 0.80],
            rng.uniform(0.025, 0.12), 0.35)
store_surface('Path', rgb, height)
stats['Path']['compressed_patch_count'] = 150

# Sand keeps broad calm light areas but gains shallow irregular deposits. This
# is a sparse 0.10-0.30 m patch scale, not a periodic ripple or dark noise layer.
n = SPECS['Sand']['size']
tile = SPECS['Sand']['tile_m']
broad = noise(n, 4, 2501)
mid = noise(n, 25, 2502)
grain = noise(n, 231, 2503)
rgb = np.empty((n, n, 3), np.float32)
rgb[:] = [0.783, 0.709, 0.552]
rgb += (broad * 0.049 + mid * 0.025 + grain * 0.019)[..., None] * [1.0, 0.96, 0.84]
height = 0.47 + mid * 0.09 + grain * 0.13
rng = np.random.default_rng(2524)
for k in range(185):
    cx, cy = rng.random(2)
    radius = rng.uniform(0.10, 0.30) / (2 * tile)
    angle = rng.uniform(0, math.tau)
    tint = rng.uniform(-0.030, 0.023)
    ellipse(rgb, height, cx, cy, radius, radius * rng.uniform(0.52, 0.88), angle,
            [tint, tint * 0.96, tint * 0.84], rng.uniform(-0.055, 0.065), 0.55)
    ellipse(rgb, height, cx - math.cos(angle) * radius * 0.55,
            cy - math.sin(angle) * radius * 0.55, radius * 0.6,
            radius * 0.36, angle - 0.7, [tint * 0.4, tint * 0.38, tint * 0.34],
            rng.uniform(-0.025, 0.025), 0.65)
for k in range(1150):
    cx, cy = rng.random(2)
    radius = rng.uniform(0.0007, 0.0023)
    tint = rng.uniform(-0.048, 0.033)
    ellipse(rgb, height, cx, cy, radius, radius * rng.uniform(0.52, 0.90),
            rng.uniform(0, math.tau), [tint, tint * 0.95, tint * 0.84],
            rng.uniform(0.025, 0.11), 0.35)
store_surface('Sand', rgb, height)
stats['Sand']['deposit_patch_count'] = 185

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
    'rgb': 'sRGB reflectance', 'alpha': 'independent linear CHANNEL_PACKED height',
    'generated': list(images), 'surface_parameters': stats,
    'rock': {'image': 'Step 11 retained byte-for-byte', 'tile_m': 8.0, 'height_range_m': 0.70},
    'soil_land_use_geometry_runtime_modified': False,
    'source_save_required': True,
}
(LOG / 'texture_finish_13.json').write_text(json.dumps(report, indent=2), encoding='utf8')
bpy.context.view_layer.update()
print(json.dumps({'generated': list(images), 'parameters': SPECS,
                  'rock_parameters': report['rock'], 'source_save_required': True}))
