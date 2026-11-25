"""Repeatable complete-group grounding, executed only in the owned GUI MCP.

All transforms are derived from this turn's objects_before.json. This module
never exports/saves, never changes grass meshes, and never replays old scripts.
Set STRUCTURE23_PROPS_APPLY=False in the MCP namespace for a read-only plan.
"""
import bpy, os, json, math, sys, numpy as np
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(bpy.data.filepath).parent.parent
LOG = ROOT / 'captures/terrain_structure_20261123'
APPLY = bool(globals().get('STRUCTURE23_PROPS_APPLY', True))
assert not bpy.app.background, 'Author only in the independent GUI MCP'
session = json.loads((LOG / 'session_start.json').read_text(encoding='utf8'))
assert os.getpid() == session['pid'], 'This is not the snapshotted GUI session'
assert bpy.types.blendermcp_server.port == session['port'], 'MCP port changed'
sys.path.insert(0, str(ROOT / 'source'))
import importlib, structure23_common as util
importlib.reload(util)

terrain = bpy.data.objects['C25_ContourBuiltCoast']
assert terrain.get('structure23_grade') and terrain.get('structure23_land')
assert np.max(np.abs(np.array(terrain.matrix_world) - np.eye(4))) < 1e-7
mesh = terrain.data
base = np.load(LOG / 'baseline.npz')
assert len(mesh.vertices) == len(base['positions'])
old_bvh = BVHTree.FromPolygons([Vector(p) for p in base['positions']], base['triangles'].tolist(), all_triangles=True)
new_bvh = BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices], [list(p.vertices) for p in mesh.polygons], all_triangles=True)
data = np.load(LOG / 'land_data.npz')
land, height, normal = data['land'], data['height'], data['normal']
design = json.loads((LOG / 'design.json').read_text(encoding='utf8'))
route_boxes = [(r, np.array(r['points'])[:, :2].min(0)-r['halfwidth']-.12,
               np.array(r['points'])[:, :2].max(0)+r['halfwidth']+.12) for r in design['routes']]
thresholds = [q for q in design['platforms'] if 'threshold_landing' in q['name'] or q['name']=='trade_pier_sand_landing']
n = len(land)
records = {r['name']: r for r in json.loads((LOG / 'objects_before.json').read_text(encoding='utf8'))}
active = {name: bpy.data.objects[name] for name in records if name in bpy.data.objects}
before_matrices = {name: Matrix(r['matrix']) for name, r in records.items()}
points_cache = {}


def suffix(name):
    value = name.rsplit('.', 1)[-1]
    return int(value) if value.isdigit() else 0


def prefix(name):
    value = name.rsplit('.', 1)
    return value[0] if len(value) == 2 and value[1].isdigit() else name


def matching(col, stem):
    return sorted([name for name, r in records.items() if col in r['collections'] and prefix(name) == stem], key=suffix)


def points(name):
    if name not in points_cache:
        obj = active[name]
        assert obj.type == 'MESH' and len(obj.data.vertices) == records[name]['vertices'], 'Baseline geometry changed: ' + name
        raw = np.empty(len(obj.data.vertices) * 3, dtype=np.float64)
        obj.data.vertices.foreach_get('co', raw)
        mat = np.array(before_matrices[name])
        points_cache[name] = raw.reshape(-1, 3) @ mat[:3, :3].T + mat[:3, 3]
    return points_cache[name]


def ray(bvh, x, y):
    hit, nn, index, distance = bvh.ray_cast(Vector((float(x), float(y), 80)), Vector((0, 0, -1)), 200)
    return None if hit is None else (float(hit.z), float(nn.z))


def map_at(xy):
    xy = np.asarray(xy, float)
    xx = np.clip(((xy[:, 0] + 4) / 48 * n).astype(int), 0, n - 1)
    yy = np.clip(((-xy[:, 1] + 15) / 97 * n).astype(int), 0, n - 1)
    return land[yy, xx], height[yy, xx], normal[yy, xx]


def touching(names, pad=.07):
    """Complete XY touching components, using immutable baseline bounds."""
    names = sorted(names)
    boxes = [np.array(records[name]['bounds']) for name in names]
    parents = list(range(len(names)))
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    sweep = []
    for i in sorted(range(len(names)), key=lambda k: boxes[k][0, 0]):
        b = boxes[i]
        sweep = [j for j in sweep if boxes[j][1, 0] + pad >= b[0, 0]]
        for j in sweep:
            a = boxes[j]
            if b[0, 1] <= a[1, 1] + pad and b[1, 1] >= a[0, 1] - pad:
                parents[find(i)] = find(j)
        sweep.append(i)
    result = {}
    for i, name in enumerate(names):
        result.setdefault(find(i), []).append(name)
    return list(result.values())


groups = []
claimed = set()


def add_group(kind, names, support=None):
    assert not (claimed & set(names)), 'Object claimed twice'
    assert all(name in active for name in names), 'Missing baseline component'
    claimed.update(names)
    if support is None:
        support = min(names, key=lambda name: records[name]['bounds'][0][2])
    groups.append({'id': kind + ':' + support, 'kind': kind, 'names': names, 'support_name': support})


# Only the known complete assembly counts are accepted. No nearest-crown guess.
trunks = matching('Reference_Foliage', 'Tree_Trunk')
crowns = matching('Reference_Foliage', 'D19_Tree_Crown')
branches = matching('Reference_Foliage', 'Tree_Branch')
assert len(trunks) == 40 and len(crowns) == 240 and len(branches) == 200, 'Tree assembly inventory changed'
for i, name in enumerate(trunks):
    add_group('tree', [name] + crowns[i*6:(i+1)*6] + branches[i*5:(i+1)*5], name)
palms = matching('Reference_Foliage', 'Palm_Trunk')
parts = [(matching('Reference_Foliage', stem), count) for stem, count in
         [('D19_Palm_FrondRachis', 8), ('D19_Palm_FrondLeaflets', 8), ('Palm_Coconut', 3), ('D19_Palm_GrowthRing', 12)]]
assert len(palms) == 18 and all(len(names) == 18*count for names, count in parts), 'Palm assembly inventory changed'
for i, name in enumerate(palms):
    add_group('palm', [name] + [part for names, count in parts for part in names[i*count:(i+1)*count]], name)
for name in matching('Reference_Foliage', 'S20_CourtyardShrub'):
    add_group('shrub', [name])
for name, r in records.items():
    if 'Reference_Rocks' in r['collections']:
        add_group('rock', [name])

coast_excluded = ('Hut_', 'D19_Hut', 'D19_Thatch', 'D19_Reed', 'D19_RidgeBinding', 'D19_EaveRafter',
                  'D19_Door', 'Pier_', 'Arrival_', 'Pile_Lashing', 'S20_DeckPeg', 'S20_PileEndGrain',
                  'S20_MooringKnot', 'S20_RopeTail', 'S20_PileBracket', 'D19_Deck', 'D19_Pile',
                  'D19_Mooring', 'D19_RopeTail')
coast = [name for name, r in records.items() if 'Reference_Coast' in r['collections'] and not name.startswith(coast_excluded)]
# The old XY sweep joins the shore net, timber, a full crate and supply crates
# through touching silhouettes even though their physical feet span 1.7m.
# Preserve each real assembly before doing the remaining coast XY sweep.
net_names = [name for name in coast if prefix(name) in ('S20_NetPost', 'S20_NetRail', 'S20_NetHorizontal', 'S20_NetVertical')]
if net_names:
    add_group('coast_prop', net_names, 'S20_NetPost')
timber_names = [name for name in coast if prefix(name) in ('S20_StackBearers', 'S20_TimberStack')]
for names in touching(timber_names):
    add_group('coast_prop', names)
orphan_names = [name for name in ('Crate_Frame.032', 'Crate_Frame.044') if name in coast]
for name in orphan_names:
    add_group('coast_legacy_fragment', [name])
coast = [name for name in coast if name not in claimed]
for names in touching(coast):
    add_group('coast_prop', names)

# Ground furniture only. Matching a broad Town_ prefix is deliberately forbidden.
planters = matching('Reference_Town', 'Town_Planter')
bands, leaves = matching('Reference_Town', 'Town_PlanterBand'), matching('Reference_Town', 'Town_PlanterLeaf')
assert len(planters) == 13 and len(bands) == 26 and len(leaves) == 234
for i, name in enumerate(planters):
    add_group('planter', [name]+bands[i*2:(i+1)*2]+leaves[i*18:(i+1)*18], name)
tops, legs = matching('Reference_Town', 'Town_TableTop'), matching('Reference_Town', 'Town_TableLeg')
backs, seats, chairlegs = [matching('Reference_Town', stem) for stem in ('Town_ChairBack', 'Town_ChairSeat', 'Town_ChairLeg')]
assert len(tops) == 4 and len(legs) == 16 and len(backs) == len(seats) == 8 and len(chairlegs) == 32
for i, name in enumerate(tops):
    add_group('seating', [name]+legs[i*4:(i+1)*4]+backs[i*2:(i+1)*2]+seats[i*2:(i+1)*2]+chairlegs[i*8:(i+1)*8], legs[i*4])
bench = [name for name, r in records.items() if 'Reference_Town' in r['collections'] and prefix(name) in
         ('Town_BenchBack', 'Town_BenchBackRail', 'Town_BenchLeg', 'Town_DinerBenchSlat')]
assert len(bench) == 12
add_group('seating', bench, 'Town_BenchLeg')
town_stems = {'Town_MenuAFrame', 'Town_MenuLeg', 'Town_NetCord', 'Town_NetFloat', 'Town_NetRackPost', 'Town_NetRackRail',
              'Town_Fish', 'Town_FishCounter', 'Town_FishCounterBrace', 'Town_FishEye', 'Town_FishTray', 'Town_FishTrayRim', 'Town_MarketPost',
              'Town_TavernBarrel', 'Town_TavernHoop', 'Town_TavernLid', 'Town_TradeBarrel', 'Town_TradeHoop',
              'Town_TradeCrate', 'Town_TradeCrateBrace'}
# These exact signs belong to independent menus and fish stalls, not facades.
special_signs = {stem + '.' + str(i).zfill(3) for stem in ('Town_SignFrame', 'Town_SignBoard', 'Town_Lettering') for i in (6, 12, 13, 14)}
special_canopy = {name for name, r in records.items() if 'Reference_Town' in r['collections'] and
                 ((prefix(name) in ('Town_AwningCanvas', 'TR20_ScallopedCanvas') and 42 <= suffix(name) <= 53) or
                  (prefix(name) == 'Town_AwningLeadingRail' and suffix(name) in (4, 5)) or
                  (prefix(name) == 'Town_AwningBracket' and 8 <= suffix(name) <= 11))}
assert special_signs <= records.keys(), 'Known independent menu/stall components changed'
town = [name for name, r in records.items() if 'Reference_Town' in r['collections'] and
        (prefix(name) in town_stems or name in special_signs or name in special_canopy)]
for names in touching(town):
    kind = 'market_stall' if any(prefix(name) == 'Town_MarketPost' for name in names) else 'town_prop'
    add_group(kind, names)
# Hanging sacks are restored as a whole to their baseline. They must not follow
# the trade crate just because their XY silhouettes overlap it.
for names in touching(matching('Reference_Town', 'TR20_ProduceSack')):
    add_group('building_supported_goods', names)

# Hulls of real structural supports. Props may be beside these, never relocated
# through them. Tree crowns are not used to pretend the ground is occupied.
building_hulls = []
support_vertices, support_faces = [], []
for name in records:
    if prefix(name) in ('Town_Floor', 'Town_Footing', 'Town_Step', 'Hut_Floor', 'Hut_EntrySteps') or name.startswith('Town_TavernPorch'):
        hull = util.convex_hull(points(name)[:, :2])
        if len(hull) >= 3:
            building_hulls.append((name, hull))
    if prefix(name) in ('Town_Floor', 'Hut_Floor', 'Town_BalconyBoard', 'Town_TradeBalconyBoard', 'Town_TradeVerandaDeck', 'Pier_DeckBoard', 'Arrival_ApronBoard', 'Arrival_LeftPierBoard') or name.startswith('Town_TavernPorch'):
        pp = points(name)
        offset = len(support_vertices)
        support_vertices.extend(Vector(q) for q in pp)
        support_faces.extend([offset+i for i in polygon.vertices] for polygon in active[name].data.polygons)
structure_bvh = BVHTree.FromPolygons(support_vertices, support_faces)


def sample_hull(hull, spacing=.24):
    lo, hi = hull.min(0), hull.max(0)
    xx, yy = np.meshgrid(np.linspace(lo[0], hi[0], max(2, min(31, int((hi[0]-lo[0])/spacing)+2))),
                         np.linspace(lo[1], hi[1], max(2, min(31, int((hi[1]-lo[1])/spacing)+2))))
    pp = np.column_stack([xx.ravel(), yy.ravel()])
    pp = pp[util.polygon_distance(pp[:, 0], pp[:, 1], hull) <= .015]
    return np.concatenate([pp, hull, hull.mean(0)[None]])


def hull_collides(hull, other, padding=.10):
    if np.any(hull.max(0)+padding < other.min(0)) or np.any(other.max(0)+padding < hull.min(0)):
        return False
    # SAT of convex projected outlines, with a small placement margin.
    for poly in (hull, other):
        edges = np.roll(poly, -1, axis=0)-poly
        for edge in edges:
            axis = np.array([-edge[1], edge[0]])
            norm = np.linalg.norm(axis)
            if norm < 1e-9:
                continue
            axis /= norm
            a, b = hull@axis, other@axis
            if a.max()+padding < b.min() or b.max()+padding < a.min():
                return False
    return True


def prepare(g):
    name = g['support_name']
    p = points(name)
    bottom = p[:, 2].min()
    root = p[p[:, 2] <= bottom+.04].mean(0)
    if g['kind'] in ('tree', 'palm'):
        low = p[p[:, 2] <= bottom+.65]
        contact = p[p[:, 2] <= bottom+.04]
    else:
        # Only physical low members define occupancy; tall canopy and leaves
        # still move with their assembly, but do not inflate a walking obstacle.
        low_parts, contacts = [], []
        for member in g['names']:
            q = points(member)
            low_parts.append(q[q[:, 2] <= bottom+1.15])
            if q[:, 2].min() <= bottom+.16:
                qq = q[q[:, 2] <= q[:, 2].min()+.035]
                if len(qq) > 12:
                    ix = np.unique(np.concatenate([np.argmin(qq[:, :2], axis=0), np.argmax(qq[:, :2], axis=0), np.linspace(0, len(qq)-1, 8).astype(int)]))
                    qq = qq[ix]
                contacts.append(qq)
        low = np.concatenate([q for q in low_parts if len(q)])
        contact = np.concatenate(contacts)
    hull = util.convex_hull(low[:, :2])
    if len(hull) < 3 or (hull.max(0)-hull.min(0)).min() < .015:
        lo, hi = low[:, :2].min(0)-.04, low[:, :2].max(0)+.04
        hull = np.array([[lo[0], lo[1]], [hi[0], lo[1]], [hi[0], hi[1]], [lo[0], hi[1]]])
    # Deterministic sparse roots for ray tests, dense footprint for road checks.
    if len(contact) > 48:
        contact = contact[np.linspace(0, len(contact)-1, 48).astype(int)]
    oldhit = ray(old_bvh, *root[:2])
    limits = {'tree': (-.18, .02), 'palm': (-.16, .02), 'shrub': (-.24, .01),
              'rock': (-max(.35, float(np.ptp(p[:, 2]))*.30), .025)}.get(g['kind'], (-.06, .03))
    old_gaps = []
    for q in contact:
        hit = ray(old_bvh, *q[:2])
        old_gaps.append(None if hit is None else float(q[2]-hit[0]))
    g.update(root=root, hull=hull, samples=sample_hull(hull), contact=contact,
             oldhit=oldhit, limits=limits, old_gaps=old_gaps)


for g in groups:
    prepare(g)
reservations = {g['id']: g['hull'] for g in groups}
outcomes, targets, unresolved = [], {}, []


def exact_ground(g, shift):
    desired = []
    gaps = []
    for p, oldgap in zip(g['contact'], g['old_gaps']):
        hit = ray(new_bvh, *(p[:2]+shift))
        if hit is None or oldgap is None:
            return None
        keep = float(np.clip(oldgap, *g['limits']))
        desired.append(hit[0]+keep-p[2])
        gaps.append(keep)
    # Rooted vegetation/rocks retain burial; rigid legs require a common plane.
    if g['kind'] in ('tree', 'palm', 'shrub', 'rock'):
        q = ray(new_bvh, *(g['root'][:2]+shift))
        if q is None or g['oldhit'] is None:
            return None
        oldgap = g['root'][2]-g['oldhit'][0]
        dz = q[0]+float(np.clip(oldgap, *g['limits']))-g['root'][2]
    else:
        dz = max(desired)
    residual = np.asarray(desired)-dz
    return float(dz), float(np.ptp(desired)), [float(residual.min()), float(residual.max())]


def on_structural_support(g):
    # Cast just above the actual foot, so an upper balcony cannot conceal a
    # lower floor. Test several feet because a crate corner can lie in a deck
    # board gap while its other feet are supported.
    probes = np.concatenate([g['root'][None], g['contact']])
    good = 0
    for q in probes:
        hit, _, _, _ = structure_bvh.ray_cast(Vector((float(q[0]), float(q[1]), float(q[2]+.26))), Vector((0, 0, -1)), .55)
        if hit is not None and -.15 <= q[2]-hit.z <= .25:
            good += 1
    return good >= max(1, math.ceil(len(probes)*.45))


def assess(g, shift, moved):
    ss = g['samples']+shift
    role, hh, nn = map_at(ss)
    maxpath = float(role[:, 2].max())
    # Court surface is valid working/seating space. Only actual route width
    # and the small threshold landing are protected as through circulation.
    x, z = ss[:, 0], -ss[:, 1]
    conflicts = []
    lo, hi = np.array([x.min(), z.min()]), np.array([x.max(), z.max()])
    for route, rlo, rhi in route_boxes:
        if np.any(hi < rlo) or np.any(lo > rhi):
            continue
        distance, _ = util.route_profile(x, z, route['points'])
        if float(distance.min()) < route['halfwidth']+.06:
            conflicts.append(route['name'])
    for court in thresholds:
        if np.min(util.polygon_distance(x, z, court['polygon'])) < .06:
            conflicts.append(court['name'])
    hit_path = bool(conflicts)
    minnormal = float(nn.min())
    slope_limit = {'tree': .69, 'palm': .69, 'shrub': .68, 'rock': .48}.get(g['kind'], .91)
    reasons = []
    if hit_path:
        reasons.append('true_route_or_threshold_footprint')
    if minnormal < slope_limit:
        reasons.append('ground_too_steep')
    metrics = {'maximum_path_weight': maxpath, 'minimum_up_normal': minnormal, 'mean_grass_weight': float(role[:, 0].mean()), 'route_conflicts': conflicts}
    if moved and reasons:
        return reasons, metrics
    hull = g['hull']+shift
    # Existing near-foundation furniture is not rejected solely for its old
    # overlap. Every newly relocated footprint must clear structural supports.
    if moved:
        if any(hull_collides(hull, h, .11) for name, h in building_hulls):
            reasons.append('structural_footprint')
        if any(key != g['id'] and hull_collides(hull, h, .07) for key, h in reservations.items()):
            reasons.append('other_prop_footprint')
        rr, _, _ = map_at((g['root'][:2]+shift)[None])
        if g['kind'] in ('tree', 'palm', 'shrub', 'rock', 'planter') and (rr[0, 0] < .55 or np.mean(role[:, 0]) < .45):
            reasons.append('not_adjacent_grass')
        low_shore_prop = g['kind'] == 'coast_prop' and g['oldhit'] is not None and g['oldhit'][0] < .45
        if float(hh.min()) < (.16 if low_shore_prop else .32):
            reasons.append('shore_or_water')
        root_h = float(map_at((g['root'][:2]+shift)[None])[1][0])
        if g['kind'] in ('market_stall', 'seating', 'town_prop', 'coast_prop') and g['oldhit'] is not None and abs(root_h-g['oldhit'][0]) > 1.0:
            reasons.append('different_terrace_level')
    return reasons, metrics


# Larger prop assemblies reserve their destination before single shrubs/rocks.
priority = {'market_stall': 0, 'seating': 0, 'town_prop': 1, 'coast_prop': 2, 'planter': 3, 'tree': 4, 'palm': 4, 'rock': 5, 'shrub': 6,
            'coast_legacy_fragment': 7, 'building_supported_goods': 7}
groups.sort(key=lambda g: (priority[g['kind']], g['id']))
for g in groups:
    root = g['root']
    item = {'group': g['id'], 'kind': g['kind'], 'objects': g['names'], 'support_object': g['support_name'],
            'before_support_blender': root.tolist(), 'before_support_godot': [float(root[0]), float(root[2]), float(-root[1])],
            'baseline_source': 'objects_before.json', 'component_count': len(g['names'])}
    shift, dz = np.zeros(2), 0.0
    if g['kind'] in ('coast_legacy_fragment', 'building_supported_goods'):
        item.update(status='restored_baseline_semantic_exclusion', reason=['preexisting_orphan_component_requires_separate_review'] if g['kind'] == 'coast_legacy_fragment' else ['hanging_goods_are_building_components'])
    elif not (6 < root[0] < 38 and -15 < -root[1] < 68):
        item.update(status='kept_outside_region', reason=['outside_structural_rebuild_region'])
    elif g['oldhit'] is None:
        item.update(status='kept_unresolved', reason=['missing_baseline_terrain'])
        unresolved.append(g['id'])
    elif g['kind'] not in ('tree', 'palm', 'shrub', 'rock') and on_structural_support(g):
        item.update(status='kept_on_existing_building_support', reason=['baseline_contact_on_floor_or_deck'])
    elif root[2]-g['oldhit'][0] > .75 and g['kind'] not in ('tree', 'palm', 'shrub', 'rock'):
        # Includes the two travel balcony planters and hanging produce sacks.
        item.update(status='kept_on_existing_elevated_support', reason=['baseline_support_is_above_terrain'], baseline_ground_gap=float(root[2]-g['oldhit'][0]))
    else:
        reasons, metrics = assess(g, shift, False)
        exact = exact_ground(g, shift)
        if exact is None:
            reasons.append('missing_current_terrain')
        elif exact[1] > .22 and g['kind'] not in ('tree', 'palm', 'shrub', 'rock'):
            reasons.append('rigid_feet_cannot_share_current_ground')
        item['before_metrics'] = metrics
        if reasons:
            found = None
            # Local search; never scatter a whole market stall to a remote site.
            maximum_radius = 3.50 if g['kind'] in ('market_stall', 'seating', 'town_prop') else 5.25
            for radius in np.arange(.175, maximum_radius+.01, .175):
                candidates = []
                count = max(16, int(math.ceil(2*math.pi*radius/.32)))
                for angle in np.linspace(0, 2*math.pi, count, endpoint=False):
                    candidate = np.array([math.cos(angle), math.sin(angle)])*radius
                    rr, mm = assess(g, candidate, True)
                    if rr:
                        continue
                    score = radius + .30*(1-mm['mean_grass_weight'])
                    candidates.append((score, candidate, mm))
                for score, candidate, mm in sorted(candidates, key=lambda value: value[0]):
                    ground = exact_ground(g, candidate)
                    if ground is None:
                        continue
                    if ground[1] > .20 and g['kind'] not in ('tree', 'palm', 'shrub', 'rock'):
                        continue
                    found = candidate, ground, mm
                    break
                if found is not None:
                    break
            if found is not None:
                shift, exact, after_metrics = found
                dz = exact[0]
                item.update(status='relocated_and_regrounded', reason=reasons, after_metrics=after_metrics)
            else:
                # No silent bad relocation. Keep baseline XY and report the
                # obstruction; a valid vertical follow still avoids floating.
                # An excessive spread cannot be repaired by raising the whole
                # assembly to its highest foot; that leaves all other feet in
                # the air. Keep baseline height for explicit manual treatment.
                dz = exact[0] if exact is not None and (exact[1] <= .22 or g['kind'] in ('tree', 'palm', 'shrub', 'rock')) else 0.0
                item.update(status='regrounded_needs_manual_placement', reason=reasons+['no_valid_local_grass_destination'])
                unresolved.append(g['id'])
        else:
            dz = exact[0]
            item.update(status='regrounded_in_place' if abs(dz) > .001 else 'kept_already_grounded', reason=['follow_new_physical_surface'] if abs(dz) > .001 else ['baseline_contact_valid'])
        if exact is not None:
            item['support_height_spread_m'] = exact[1]
            item['contact_residual_range_m'] = exact[2]
    delta = np.array([shift[0], shift[1], dz])
    reservations[g['id']] = g['hull']+shift
    item.update(delta_blender=delta.tolist(), after_support_blender=(root+delta).tolist(),
                after_support_godot=[float(root[0]+shift[0]), float(root[2]+dz), float(-root[1]-shift[1])],
                xy_distance_m=float(np.linalg.norm(shift)))
    outcomes.append(item)
    for name in g['names']:
        matrix = before_matrices[name].copy()
        matrix.translation += Vector(delta)
        targets[name] = matrix

report = {'stage': 'structure23_03_props', 'apply': APPLY, 'pid': os.getpid(), 'groups': outcomes,
          'group_count': len(groups), 'component_count': len(targets), 'unresolved_groups': unresolved,
          'complete_tree_groups': len(trunks), 'complete_palm_groups': len(palms),
          'exact_menu_stall_sign_exceptions': sorted(special_signs), 'exact_stall_canopy_components': sorted(special_canopy),
          'source_saved': False, 'exports_completed': False, 'visual_accepted': False,
          'grouping_rule': 'known suffix-count tree/palm/planter/seating assemblies; remaining immutable-baseline XY touching coast and explicit Town whitelist',
          'circulation_rule': 'actual design.routes and threshold landings; court material alone does not exclude props',
          'legacy_orphan_components_kept_at_baseline': orphan_names,
          'grass_handled': False, 'ground_cover_handled': False}
(LOG / 'props_plan.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
if APPLY:
    preserved = {name: obj.matrix_world.copy() for name, obj in active.items() if name not in targets}
    # Parent-before-child world assignment avoids double translation.
    def depth(name):
        value, obj = 0, active[name]
        while obj.parent is not None:
            value, obj = value+1, obj.parent
        return value
    for name in sorted(targets, key=depth):
        active[name].matrix_world = targets[name]
    bpy.context.view_layer.update()
    assert all(np.max(np.abs(np.array(active[name].matrix_world)-np.array(matrix))) < 3e-5 for name, matrix in targets.items()), 'Group transform mismatch'
    assert all(np.max(np.abs(np.array(active[name].matrix_world)-np.array(matrix))) < 3e-5 for name, matrix in preserved.items()), 'A non-whitelisted component followed a moved parent'
    moved = [{'name': name, 'before': records[name]['matrix'], 'after': np.array(matrix).tolist()} for name, matrix in targets.items()
             if np.max(np.abs(np.array(matrix)-np.array(before_matrices[name]))) > 1e-6]
    (LOG / 'props_object_matrices.json').write_text(json.dumps(moved, ensure_ascii=False, indent=2), encoding='utf8')
    terrain['structure23_props'] = True
    report['applied'] = True
    report['moved_components'] = len(moved)
    (LOG / 'props.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps({'apply': APPLY, 'groups': len(groups), 'components': len(targets),
                  'relocated': sum(o['status'] == 'relocated_and_regrounded' for o in outcomes),
                  'unresolved': unresolved, 'report': str(LOG / ('props.json' if APPLY else 'props_plan.json'))}, ensure_ascii=False))
