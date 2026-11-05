"""Author the existing wood atlases inside Blender through execute_blender_code.

Run through the live Blender MCP connection, never blender --background.
Mesh geometry and existing UVs stay intact. Colors are painted in board coordinates
and rasterized into the UV atlas, so grain follows each board rather than world axes.
"""
import bpy
import hashlib
import json
import struct
import zlib
from pathlib import Path
import numpy as np


if Path(bpy.data.filepath).name != 'harbor_art_mcp.blend':
    raise RuntimeError('Open harbor_art_mcp.blend through Blender MCP before authoring its atlases.')
ROOT = Path(bpy.data.filepath).parent.parent
SIZE = 2048


def png(path, rgba):
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    data = np.ascontiguousarray(np.flipud(np.clip(rgba * 255.0 + 0.5, 0, 255).astype(np.uint8)))
    raw = b''.join(b'\0' + row.tobytes() for row in data)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', SIZE, SIZE, 8, 6, 0, 0, 0))
                    + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def style(name, kind):
    seed = int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    name = name.lower()
    if kind == 'pier':
        base = np.array([132, 106, 85], dtype=float)
        if 'pile' in name or 'bearer' in name or 'stringer' in name:
            base = np.array([99, 78, 60], dtype=float)
        if 'crown' in name:
            base = np.array([165, 144, 111], dtype=float)
    else:
        base = np.array([149, 123, 94], dtype=float)
        if 'strake' in name or 'hull' in name or 'rubbing' in name:
            base = np.array([107, 82, 64], dtype=float)
        elif 'gunwale' in name or 'thwart' in name or 'rib' in name:
            base = np.array([126, 100, 75], dtype=float)
        if 'fiber' in name:
            base *= 0.72
    base *= rng.uniform(0.84, 1.12)
    base += rng.uniform(-4, 4, 3)
    return base / 255.0, rng.uniform(0, 6.28), rng.uniform(0.23, 0.77), rng.uniform(0.2, 0.8), seed % 4 == 0


def painted(coords, lo, span, axis, normal, name, kind):
    base, phase, knot_l, knot_t, has_knot = style(name, kind)
    l = (coords[:, axis] - lo[axis]) / span[axis]
    candidates = [i for i in range(3) if i != axis]
    cap = abs(normal[axis]) > 0.82
    transverse = min(candidates, key=lambda i: abs(normal[i]))
    t = (coords[:, transverse] - lo[transverse]) / span[transverse]
    curved = 'pile' in name.lower()
    if curved and not cap:
        a, b = candidates
        t = np.arctan2((coords[:, a] - lo[a]) / span[a] - .5,
                       (coords[:, b] - lo[b]) / span[b] - .5) / (2 * np.pi) + .5
    # Low-frequency color shapes remain legible at the game's normal camera distance.
    flow = t + .026 * np.sin(l * 9 + phase) + .012 * np.sin(l * 23 + phase * 2)
    broad = np.sin(flow * 27 + phase + .45 * np.sin(l * 6))
    fibers = np.sin(flow * 91 + phase + .6 * np.sin(l * 17 + phase))
    streak = np.exp(-((np.sin(flow * 14 + phase)) / .12) ** 2)
    streak *= (.45 + .55 * np.sin(l * 9 + phase) ** 2)
    shading = .027 * broad + .005 * fibers - .042 * streak
    if has_knot and not curved and not cap:
        radius = np.sqrt(((l - knot_l) / .078) ** 2 + ((t - knot_t) / .19) ** 2)
        shading -= .085 * np.exp(-radius ** 2 * 2.8)
        shading += .028 * np.cos(radius * 12) * np.exp(-radius ** 2 * .6)
    if cap:
        a, b = candidates
        a = (coords[:, a] - lo[a]) / span[a] - .44
        b = (coords[:, b] - lo[b]) / span[b] - .53
        rings = np.sqrt((a * 1.03) ** 2 + b ** 2)
        shading = .018 * np.sin(rings * 70 + .6 * np.sin(a * 19)) - .017
    # Soft worn edges and dark end grain are painted, not baked directional lighting.
    edge = np.minimum(t, 1 - t)
    end = np.minimum(l, 1 - l)
    wear = .032 * np.exp(-np.maximum(edge, 0) / .035) * (.65 + .35 * np.sin(l * 32 + phase) ** 2)
    if curved or cap:
        wear *= .25
    end_dark = .028 * np.exp(-np.maximum(end, 0) / .035) if not cap else 0
    rgb = base + shading[:, None] * np.array([1.0, .85, .65]) + wear[:, None] - np.asarray(end_dark).reshape(-1, 1)
    return np.clip(rgb, 0.025, .85), .5 + shading * .32


def paint_collection(collection, kind):
    color = np.zeros((SIZE, SIZE, 4), dtype=np.float32)
    height = np.full((SIZE, SIZE), .5, dtype=np.float32)
    mask = np.zeros((SIZE, SIZE), dtype=bool)
    count = 0
    for obj in sorted(bpy.data.collections[collection].objects, key=lambda o: o.name):
        if obj.type != 'MESH' or not obj.data.uv_layers:
            continue
        if kind == 'pier' and not any(s.material and s.material.name == 'PierWood_Lit' for s in obj.material_slots):
            continue
        mesh = obj.data
        verts = np.array([v.co[:] for v in mesh.vertices])
        lo, hi = verts.min(0), verts.max(0)
        span = np.maximum(hi - lo, .0001)
        axis = int(span.argmax())
        uv_data = mesh.uv_layers.active.data
        mesh.calc_loop_triangles()
        for tri in mesh.loop_triangles:
            uv = np.array([uv_data[i].uv[:] for i in tri.loops]) * SIZE - .5
            x0, y0 = np.maximum(np.floor(uv.min(0)).astype(int), 0)
            x1, y1 = np.minimum(np.ceil(uv.max(0)).astype(int), SIZE - 1)
            if x1 < x0 or y1 < y0:
                continue
            v0, v1 = uv[1] - uv[0], uv[2] - uv[0]
            det = v0[0] * v1[1] - v0[1] * v1[0]
            if abs(det) < 1e-8:
                continue
            y, x = np.mgrid[y0:y1+1, x0:x1+1]
            dx, dy = x - uv[0, 0], y - uv[0, 1]
            b = (dx * v1[1] - dy * v1[0]) / det
            c = (v0[0] * dy - v0[1] * dx) / det
            inside = (b >= -.001) & (c >= -.001) & (b + c <= 1.001)
            if not inside.any():
                continue
            b, c = b[inside], c[inside]
            positions = verts[list(tri.vertices)]
            coords = positions[0] + b[:, None] * (positions[1] - positions[0]) + c[:, None] * (positions[2] - positions[0])
            rgb, h = painted(coords, lo, span, axis, np.array(tri.normal[:]), obj.name, kind)
            xx, yy = x[inside], y[inside]
            color[yy, xx, :3] = rgb
            color[yy, xx, 3] = 1
            height[yy, xx] = h
            mask[yy, xx] = True
        count += 1
    coverage = float(mask.mean())
    # Dilate island borders so mipmaps never sample black outside painted UVs.
    for _ in range(12):
        grow = mask.copy()
        for dy, dx in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            near = np.roll(mask, (dy, dx), (0, 1)) & ~grow
            color[near] = np.roll(color, (dy, dx), (0, 1))[near]
            height[near] = np.roll(height, (dy, dx), (0, 1))[near]
            grow[near] = True
        mask = grow
    gy, gx = np.gradient(height)
    normal = np.stack((-gx * 5, -gy * 5, np.ones_like(gx)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    normals = np.ones_like(color)
    normals[:, :, :3] = normal * .5 + .5
    color[:, :, 3] = 1
    for suffix, data in [('albedo', color), ('normal', normals)]:
        path = ROOT / 'assets' / (kind + '_wood_' + suffix + '.png')
        png(path, data)
        name = ('BoatWood_' if kind == 'boat' else 'PierWood_') + suffix.title()
        old = bpy.data.images.get(name)
        if old:
            old.unpack(method='REMOVE') if old.packed_file else None
            old.filepath = str(path)
            old.reload()
            image = old
        else:
            image = bpy.data.images.load(str(path), check_existing=False)
            image.name = name
        image.colorspace_settings.name = 'sRGB' if suffix == 'albedo' else 'Non-Color'
        image.pack()
    mat = bpy.data.materials['BoatWood_Lit' if kind == 'boat' else 'PierWood_Lit']
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Roughness'].default_value = .90 if kind == 'boat' else .92
    bsdf.inputs['Specular IOR Level'].default_value = .2
    for node in mat.node_tree.nodes:
        if node.type == 'NORMAL_MAP':
            node.inputs['Strength'].default_value = .65
    return {'kind': kind, 'painted_meshes': count, 'atlas_coverage': round(coverage, 3)}


# Define WOOD_TARGET in the MCP call to author one atlas per request.
target = globals().get('WOOD_TARGET', 'pier')
print(json.dumps(paint_collection('Boat_Workshop' if target == 'boat' else 'Pier_Working', target)))
