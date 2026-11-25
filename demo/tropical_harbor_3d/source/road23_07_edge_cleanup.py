"""Remove the two small grass islands found in the first same-camera review."""
import bpy, bmesh, ast, json, shutil, struct, zlib
import numpy as np
from pathlib import Path

ROOT = Path(bpy.data.filepath).parent.parent
LOG = ROOT / 'captures/road_contacts_20261123'
OUT = ROOT / 'assets/reference'
terrain = bpy.data.objects['C25_ContourBuiltCoast']
assert terrain.get('road23_grass_contacts') and not terrain.get('road23_edge_cleanup')
backup = LOG / 'preview1'
backup.mkdir(exist_ok=False)
for name in ('land_data.npz', 'occupancy.json', 'grass_contacts.json', 'export.json', 'core_audit.json'):
    shutil.copy2(LOG / name, backup / name)
shutil.copy2(OUT / 'G23_LandUse.png', backup / 'G23_LandUse.png')
with np.load(str(LOG / 'land_data.npz')) as src:
    arrays = {key: src[key].copy() for key in src.files}
land = arrays['land']; before = land.copy(); height = arrays['height']; scope = arrays['scope']
for nd in ast.parse((ROOT / 'source/ground23_02_surfaces.py').read_text(encoding='utf8')).body:
    if isinstance(nd, ast.FunctionDef) and nd.name in ('ss', 'save_image'):
        exec(compile(ast.Module(body=[nd], type_ignores=[]), 'Pure image helpers', 'exec'), globals())
n = 2048
v, u = np.mgrid[0:n, 0:n].astype(np.float32)
X = -4 + 48 * (u + .5) / n; Z = -15 + 97 * (v + .5) / n
patches = [('grill_slope_island', 12.33, 26.99, .70, .67),
           ('trade_sand_shoulder_triangle', 12.95, 11.43, .44, .42)]
cleanup = np.zeros((n, n), np.float32)
for name, x, z, rx, rz in patches:
    distance = np.sqrt(((X - x) / rx) ** 2 + ((Z - z) / rz) ** 2)
    cleanup = np.maximum(cleanup, 1 - ss(.67, 1, distance))
cleanup[scope == 0] = 0
# Preserve the route and rock channels exactly; return grass fragments to the
# surrounding soil or sandy shoulder without widening the walking surface.
removed_grass = land[..., 0] * cleanup
land[..., 0] -= removed_grass
land[..., 3] += removed_grass * ss(.38, .72, height)
assert np.array_equal(land[..., 1:3], before[..., 1:3])
assert np.array_equal(land[cleanup == 0], before[cleanup == 0])
assert land.min() >= 0 and land.sum(axis=2).max() <= 1.00001
im = save_image('G23_LandUse', land[..., :3], land[..., 3], True)
for mat in bpy.data.materials:
    if mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.name == 'G23_LandUse': node.image = im

def sample(a, x, z):
    px = float(np.clip((x + 4) / 48 * n - .5, 0, n - 1.001))
    pz = float(np.clip((z + 15) / 97 * n - .5, 0, n - 1.001))
    ix, iz = int(px), int(pz); fx, fz = px - ix, pz - iz
    return (a[iz, ix] * (1 - fx) + a[iz, ix + 1] * fx) * (1 - fz) + (a[iz + 1, ix] * (1 - fx) + a[iz + 1, ix + 1] * fx) * fz

grass = []
for name in ('L24_GrassTuftClusters', 'G23_RootedGrassMargins'):
    ob = bpy.data.objects[name]; bm = bmesh.new(); bm.from_mesh(ob.data)
    count = len(bm.faces); remove = []
    for face in bm.faces:
        assert len(face.verts) == 3 and all(len(v.link_faces) == 1 for v in face.verts)
        points = [ob.matrix_world @ v.co for v in face.verts[:2]]
        points.append((points[0] + points[1]) * .5)
        if any(sample(cleanup, p.x, -p.y) > .001 and sample(land, p.x, -p.y)[0] < .40 for p in points):
            remove.append(face)
    if remove: bmesh.ops.delete(bm, geom=[v for f in remove for v in f.verts], context='VERTS')
    copy = ob.data.copy(); bm.to_mesh(copy); copy.update(); bm.free(); ob.data = copy
    grass.append({'name': name, 'before_triangles': count, 'removed': len(remove), 'after_triangles': len(copy.polygons), 'retained_positions_unchanged': True})
arrays['land'] = land; arrays['edge_cleanup'] = cleanup
np.savez_compressed(str(LOG / 'land_data.npz'), **arrays)
report = {'patches': patches, 'changed_pixels': int(np.any(land != before, axis=2).sum()),
          'path_and_rock_channels_unchanged': True, 'geometry_unchanged': True,
          'outside_original_scope_unchanged': True, 'grass': grass, 'visual_accepted': False}
(LOG / 'edge_cleanup.json').write_text(json.dumps(report, indent=2), encoding='utf8')
occupancy = json.loads((LOG / 'occupancy.json').read_text(encoding='utf8'))
occupancy['edge_cleanup_report'] = 'edge_cleanup.json'
occupancy['first_pass_report'] = 'preview1/occupancy.json'
(LOG / 'occupancy.json').write_text(json.dumps(occupancy, ensure_ascii=False, indent=2), encoding='utf8')
terrain['road23_edge_cleanup'] = True
print(json.dumps(report))
