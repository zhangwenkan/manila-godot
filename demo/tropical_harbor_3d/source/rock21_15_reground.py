# Execute once through the verified Blender MCP after rock21_14_wide_forms.
# This file only follows the changed ground: it never replays earlier XY placements.
# Historical run completed. Architectural exclusions below were corrected after
# that run; do not rerun. Step 19 reverses the recorded erroneous moves exactly.
from pathlib import Path
exec((Path(bpy.data.filepath).parent / 'shore_21_context.py').read_text(encoding='utf8'), globals())
LOG = ROOT / 'captures/rock_earth_rebuild_20261121'
assert terrain.get('rock21_wide_forms'), 'Wide-forms terrain stage is missing'
assert not terrain.get('rock21_wide_regrounded'), 'Wide-forms grounding already applied'
assert max(abs(terrain.matrix_world[r][c] - float(r == c))
           for r in range(4) for c in range(4)) < 1e-7, 'Terrain coordinates must be world coordinates'

baseline_path = LOG / 'before_wide_forms.npz'
with np.load(str(baseline_path), allow_pickle=False) as raw:
    old = {key: raw[key].copy() for key in ('positions', 'loops', 'starts', 'sizes')}
oldfaces = [old['loops'][s:s + n].tolist() for s, n in zip(old['starts'], old['sizes'])]
old_bvh = BVHTree.FromPolygons([Vector(p) for p in old['positions']], oldfaces)
# Construct from the actual authored mesh so ray polygon indices match LandUse loops.
ground_bvh = BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],
                                [tuple(p.vertices) for p in mesh.polygons])
EPSILON = .015
REGION = {'godot_z': [-15, 66], 'x': [6, 38]}


def region(p):
    return -15 < -p.y < 66 and 6 < p.x < 38


def ray(bvh, x, y):
    return bvh.ray_cast(Vector((float(x), float(y), 80)), Vector((0, 0, -1)), 300)


def foot(o):
    points = [o.matrix_world @ v.co for v in o.data.vertices]
    assert points, 'Empty grounding mesh: ' + o.name
    bottom = min(p.z for p in points)
    low = [p for p in points if p.z < bottom + .04]
    return sum(low, Vector()) / len(low)


def suffix(o):
    value = o.name.rsplit('.', 1)[-1]
    return int(value) if value.isdigit() else 0


plans = []
skipped = []
unchanged = {}
planned_names = set()


def plan_group(kind, objects, support, gap_limits):
    if not region(support):
        return
    old_hit, *_ = ray(old_bvh, support.x, support.y)
    new_hit, *_ = ray(ground_bvh, support.x, support.y)
    if old_hit is None or new_hit is None:
        skipped.append({'kind': kind, 'objects': [o.name for o in objects],
                        'reason': 'missing old or current terrain ray'})
        return
    delta = new_hit.z - old_hit.z
    if abs(delta) <= EPSILON:
        unchanged[kind] = unchanged.get(kind, 0) + 1
        return
    old_gap = support.z - old_hit.z
    target_gap = float(np.clip(old_gap, gap_limits[0], gap_limits[1]))
    dz = new_hit.z + target_gap - support.z
    if abs(dz) < .001:
        unchanged[kind] = unchanged.get(kind, 0) + 1
        return
    names = [o.name for o in objects]
    assert not (set(names) & planned_names), 'A component belongs to two grounding groups'
    planned_names.update(names)
    plans.append({'kind': kind, 'objects': objects,
                  'support': list(support), 'terrain_delta': float(delta),
                  'old_gap': float(old_gap), 'target_gap': target_gap,
                  'gap_clamped': abs(target_gap - old_gap) > 1e-6,
                  'delta_z': float(dz)})


fol = bpy.data.collections['Reference_Foliage']
trunks = sorted([o for o in fol.objects if o.name == 'Tree_Trunk' or o.name.startswith('Tree_Trunk.')], key=suffix)
crowns = sorted([o for o in fol.objects if o.name.startswith('D19_Tree_Crown')], key=suffix)
branches = sorted([o for o in fol.objects if o.name == 'Tree_Branch' or o.name.startswith('Tree_Branch.')], key=suffix)
assert len(crowns) == len(trunks) * 6 and len(branches) == len(trunks) * 5, 'Tree assembly count changed'
for i, trunk in enumerate(trunks):
    assembly = [trunk] + crowns[i * 6:(i + 1) * 6] + branches[i * 5:(i + 1) * 5]
    plan_group('tree', assembly, foot(trunk), (-.18, .02))

palms = sorted([o for o in fol.objects if o.name == 'Palm_Trunk' or o.name.startswith('Palm_Trunk.')], key=suffix)
parts = {key: sorted([o for o in fol.objects if o.name.startswith(prefix)], key=suffix)
         for key, prefix in [('rachis', 'D19_Palm_FrondRachis'), ('leaves', 'D19_Palm_FrondLeaflets'),
                             ('nuts', 'Palm_Coconut'), ('rings', 'D19_Palm_GrowthRing')]}
part_counts = [('rachis', 8), ('leaves', 8), ('nuts', 3), ('rings', 12)]
assert all(len(parts[key]) == len(palms) * count for key, count in part_counts), 'Palm assembly count changed'
for i, trunk in enumerate(palms):
    assembly = [trunk]
    for key, count in part_counts:
        assembly.extend(parts[key][i * count:(i + 1) * count])
    plan_group('palm', assembly, foot(trunk), (-.16, .02))

# Keep their current XY positions and current reasonable burial; no fixed placements.
for o in fol.objects:
    if o.type != 'MESH' or not o.name.startswith('S20_CourtyardShrub'):
        continue
    p = center(o)
    p.z = bounds(o)[2][0]
    plan_group('shrub', [o], p, (-.24, .02))
for o in bpy.data.collections['Reference_Rocks'].objects:
    if o.type != 'MESH':
        continue
    p = center(o)
    p.z = bounds(o)[2][0]
    plan_group('rock', [o], p, (-max(.35, float(o.dimensions.z) * .30), .025))

# Match step 12's XY touching-group rule and exclusions. Build complete groups
# before region filtering, so a group crossing the regional border stays assembled.
excluded = ('Hut_', 'D19_Hut', 'D19_Thatch', 'D19_Reed',
            'D19_RidgeBinding', 'D19_EaveRafter', 'D19_Door', 'Pier_', 'Arrival_',
            'Pile_Lashing', 'S20_DeckPeg', 'S20_PileEndGrain', 'S20_MooringKnot',
            'S20_RopeTail', 'S20_PileBracket', 'D19_Deck', 'D19_Pile', 'D19_Mooring', 'D19_RopeTail')
obs = [o for o in bpy.data.collections['Reference_Coast'].objects
       if o.type == 'MESH' and not o.name.startswith(excluded)]
boxes = [bounds(o) for o in obs]
parents = list(range(len(obs)))


def find(index):
    while parents[index] != index:
        parents[index] = parents[parents[index]]
        index = parents[index]
    return index


# Sweep by X avoids comparing every pair in a large complete collection.
active = []
for i in sorted(range(len(obs)), key=lambda index: boxes[index][0][0]):
    b = boxes[i]
    active = [j for j in active if boxes[j][0][1] + .07 >= b[0][0]]
    for j in active:
        a = boxes[j]
        if b[1][0] <= a[1][1] + .07 and b[1][1] >= a[1][0] - .07:
            parents[find(i)] = find(j)
    active.append(i)
groups = {}
for i, o in enumerate(obs):
    groups.setdefault(find(i), []).append(o)
for group in groups.values():
    support_object = min(group, key=lambda o: bounds(o)[2][0])
    plan_group('coast_prop_group', group, foot(support_object), (-.08, .04))

# Prepare grass before changing any object. Sample the actual triangle at the
# root, including interpolated grass weight, not a distant triangle corner.
growth = bpy.data.objects['L24_GrassTuftClusters']
attr = mesh.color_attributes['LandUse']
assert attr.domain == 'CORNER', 'LandUse is expected on face corners'
mesh.calc_loop_triangles()
triangles_by_face = {}
for triangle in mesh.loop_triangles:
    triangles_by_face.setdefault(triangle.polygon_index, []).append(tuple(triangle.loops))


def grass_weight(hit, face_index):
    for loops in triangles_by_face[face_index]:
        a, b, c = [mesh.vertices[mesh.loops[li].vertex_index].co for li in loops]
        ab, ac, ap = b - a, c - a, hit - a
        d00, d01, d11 = ab.dot(ab), ab.dot(ac), ac.dot(ac)
        denominator = d00 * d11 - d01 * d01
        if abs(denominator) < 1e-16:
            continue
        wb = (d11 * ap.dot(ab) - d01 * ap.dot(ac)) / denominator
        wc = (d00 * ap.dot(ac) - d01 * ap.dot(ab)) / denominator
        wa = 1 - wb - wc
        if min(wa, wb, wc) >= -1e-5:
            return sum(weight * attr.data[li].color[0]
                       for weight, li in zip((wa, wb, wc), loops))
    raise AssertionError('Unable to interpolate grass role at terrain hit')


vv, ff = [], []
grass_stats = {'input_blades': len(growth.data.polygons), 'removed_steep_or_non_grass': 0,
               'removed_missing_surface': 0, 'replanted': 0, 'unchanged_ground': 0,
               'outside_region': 0, 'missing_baseline_kept': 0}
grass_deltas = []
for blade in growth.data.polygons:
    assert len(blade.vertices) == 3, 'Grass is expected to contain triangular blades'
    vs = [growth.matrix_world @ growth.data.vertices[i].co for i in blade.vertices]
    # Existing source blades use vertices 0 and 1 as their two root corners.
    root = (vs[0] + vs[1]) / 2
    root.z = min(vs[0].z, vs[1].z)
    dz = 0.0
    if region(root):
        hit, normal, face_index, _ = ray(ground_bvh, root.x, root.y)
        if hit is None:
            grass_stats['removed_missing_surface'] += 1
            continue
        if normal.z < .83 or grass_weight(hit, face_index) < .65:
            grass_stats['removed_steep_or_non_grass'] += 1
            continue
        old_hit, *_ = ray(old_bvh, root.x, root.y)
        if old_hit is None:
            grass_stats['missing_baseline_kept'] += 1
        elif abs(hit.z - old_hit.z) > EPSILON:
            gap = float(np.clip(root.z - old_hit.z, -.03, .005))
            dz = hit.z + gap - root.z
            grass_stats['replanted'] += 1
            grass_deltas.append(float(dz))
        else:
            grass_stats['unchanged_ground'] += 1
    else:
        grass_stats['outside_region'] += 1
    first = len(vv)
    vv.extend((v.x, v.y, v.z + dz) for v in vs)
    ff.append((first, first + 1, first + 2))

# Only Z translation is allowed. Capture target world matrices before applying
# any parent transforms, then apply parents first to avoid double translations.
targets = {}
before_world = {}
for plan in plans:
    for o in plan['objects']:
        before_world[o.name] = o.matrix_world.copy()
        matrix = o.matrix_world.copy()
        matrix.translation.z += plan['delta_z']
        targets[o.name] = (o, matrix)


def parent_depth(o):
    depth = 0
    while o.parent is not None:
        depth += 1
        o = o.parent
    return depth


for o, matrix in sorted(targets.values(), key=lambda pair: parent_depth(pair[0])):
    o.matrix_world = matrix
bpy.context.view_layer.update()
for name, (o, target) in targets.items():
    assert max(abs(o.matrix_world[r][c] - target[r][c])
               for r in range(4) for c in range(4)) < 2e-5, 'Grounding transform mismatch: ' + name

grass_changed = bool(grass_deltas or grass_stats['removed_steep_or_non_grass']
                     or grass_stats['removed_missing_surface'])
if grass_changed:
    gm = bpy.data.meshes.new('R27_WideFormsRootedGrass')
    gm.from_pydata(vv, [], ff)
    gm.update()
    for material in growth.data.materials:
        gm.materials.append(material)
    growth.data = gm
    growth.matrix_world = Matrix.Identity(4)

terrain['rock21_wide_regrounded'] = True
report = {
    'baseline': str(baseline_path), 'required_stage': 'rock21_wide_forms',
    'completed_marker': 'rock21_wide_regrounded', 'region': REGION,
    'minimum_absolute_ground_delta_m': EPSILON,
    'horizontal_placements_changed': 0,
    'moves': [{key: ([o.name for o in value] if key == 'objects' else value)
               for key, value in plan.items()} for plan in plans],
    'unchanged_groups': unchanged, 'skipped_missing_surface': skipped,
    'coast_touch_groups': len(groups), 'grass': grass_stats,
    'grass_output_blades': len(ff),
    'grass_delta_range': [min(grass_deltas), max(grass_deltas)] if grass_deltas else [0, 0],
    'exports_completed': False, 'source_saved': False,
}
report_path = LOG / 'reground_final.json'
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
export_collection('Reference_Foliage', 'foliage.glb')
export_collection('Reference_Rocks', 'rocks.glb')
export_collection('Reference_Coast', 'coast.glb')
report['exports_completed'] = True
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'source/harbor_shore_control_mcp.blend'))
report['source_saved'] = True
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps({'groups_moved': len(plans), 'components_moved': len(targets),
                  'gap_clamped_groups': sum(plan['gap_clamped'] for plan in plans),
                  'grass': grass_stats, 'saved': True}))
