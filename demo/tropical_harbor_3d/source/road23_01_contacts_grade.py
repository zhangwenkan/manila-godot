"""One-time local road/shore grade correction; execute only in owned GUI MCP.

This pass lowers small convex lips in the three user-marked areas. It preserves
XY coordinates, topology, materials, objects and all current contact triangles.
Pure proposal helpers may be analysed offline, but run() alone edits Blender.
No export/save, no historical script execution and no school-rock expansion.
"""
import json
from pathlib import Path
import numpy as np


def smooth(a, b, value):
    t = np.clip((value - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def band(value, a, b, c, d):
    return smooth(a, b, value) * (1 - smooth(c, d, value))


def line_profile(x, z, points):
    """Nearest centreline location, interpolated height and along distance."""
    distance = np.full(len(x), np.inf)
    target = np.zeros(len(x)); along = np.zeros(len(x)); total = 0.0
    for a, b in zip(points, points[1:]):
        a, b = np.asarray(a, float), np.asarray(b, float)
        dx, dz = b[:2] - a[:2]
        length = float(np.hypot(dx, dz))
        t = np.clip(((x - a[0]) * dx + (z - a[1]) * dz) / length ** 2, 0, 1)
        d = np.hypot(x - a[0] - t * dx, z - a[1] - t * dz)
        take = d < distance
        distance[take] = d[take]
        target[take] = (a[2] + t * (b[2] - a[2]))[take]
        along[take] = (total + t * length)[take]
        total += length
    return distance, target, along, total


def design(before, freedom):
    x, z, h = before[:, 0], -before[:, 1], before[:, 2]
    changes = []; designs = []
    # The road centre already connects. Its inside shoulder rises 0.4m over
    # 0.3m of plan distance and hides the bend behind a grass lip. Lower that
    # local shoulder toward a monotone route profile, without raising a road.
    clinic_points = [(21.8, 29.35, 4.30), (21.8, 30.25, 4.20),
                     (22.30, 30.75, 3.98), (23.10, 31.15, 3.70),
                     (24.15, 31.75, 3.37), (24.36, 32.18, 3.03),
                     (23.65, 32.82, 2.67)]
    distance, target, along, total = line_profile(x, z, clinic_points)
    weight = (1 - smooth(.55, 1.13, distance)) * band(along, .15, .75, total - .6, total)
    weight *= band(z, 29.4, 30.05, 31.70, 32.55)
    weight *= smooth(2.4, 3.0, h) * (1 - smooth(4.57, 4.72, h))
    changes.append(weight * np.clip(target - h, -.38, 0))
    designs.append({'name': 'clinic_inner_bend_lip', 'centreline_xzh': clinic_points,
                    'maximum_lowering_m': .38, 'core_halfwidth_m': .55,
                    'outer_halfwidth_m': 1.13,
                    'purpose': 'Lower the inside lip; retain actual road and protect hospital foundations.'})

    # The grill forecourt was painted over this slope. The atlas will be
    # pulled inland separately. This small monotone slope replaces the local
    # convex shoulder, retaining the sand foot and original inner platform.
    weight = band(x, 11.20, 11.60, 12.80, 13.15) * band(z, 21.2, 22.3, 26.8, 28.0)
    target = .35 + .52 * np.maximum(x - 11.40, 0)
    weight *= smooth(.34, .48, h) * (1 - smooth(1.25, 1.40, h))
    changes.append(weight * np.clip(target - h, -.25, 0))
    designs.append({'name': 'grill_forecourt_sandward_shoulder',
                    'godot_bounds_xz': [11.20, 21.2, 13.15, 28.0],
                    'target_height': '.35 + .52 * max(x-11.40, 0)',
                    'maximum_lowering_m': .25,
                    'purpose': 'Quiet slope below the separately inset court; no new path on the steep face.'})

    # The two shore rocks are protected from the live scene below. This can
    # smooth only the free shoulder beside them, not undermine their bases.
    weight = band(x, 11.10, 11.85, 13.0, 13.75) * band(z, 9.8, 10.45, 11.55, 12.30)
    target = .32 + .20 * np.maximum(x - 11.10, 0)
    weight *= smooth(.30, .40, h) * (1 - smooth(1.20, 1.40, h))
    changes.append(weight * np.clip(target - h, -.22, 0))
    designs.append({'name': 'trading_sand_mouth_north_shoulder',
                    'godot_bounds_xz': [11.10, 9.8, 13.75, 12.30],
                    'target_height': '.32 + .20 * max(x-11.10, 0)',
                    'maximum_lowering_m': .22,
                    'purpose': 'Smooth the free lip beside the shore rocks, keeping their support.'})

    weight = band(x, 12.25, 12.65, 13.30, 13.75) * band(z, 14.35, 14.95, 15.70, 16.55)
    target = .40 + .22 * np.maximum(x - 12.35, 0)
    weight *= smooth(.40, .52, h) * (1 - smooth(1.16, 1.35, h))
    changes.append(weight * np.clip(target - h, -.22, 0))
    designs.append({'name': 'trading_sand_mouth_south_tip',
                    'godot_bounds_xz': [12.25, 14.35, 13.75, 16.55],
                    'target_height': '.40 + .22 * max(x-12.35, 0)',
                    'maximum_lowering_m': .22,
                    'purpose': 'Soften the projecting grass tip; leave the revised inner route at x14.1.'})
    stacked = np.stack(changes)
    label = np.argmin(stacked, axis=0)
    delta = np.zeros_like(before)
    delta[:, 2] = stacked.min(0) * freedom
    delta[h <= .30] = 0
    return delta, label, designs


def convex_hull(points):
    points = sorted(set(tuple(map(float, p)) for p in points))
    assert len(points) >= 3, 'Contact footprint needs an area'
    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 1e-10: lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 1e-10: upper.pop()
        upper.append(p)
    return np.array(lower[:-1] + upper[:-1])


def polygon_distance(points, polygon):
    inside = np.ones(len(points), bool); distance = np.full(len(points), np.inf)
    for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
        e = b - a; rel = points - a
        inside &= e[0]*rel[:, 1] - e[1]*rel[:, 0] >= -1e-9
        t = np.clip((rel @ e) / (e @ e), 0, 1)
        distance = np.minimum(distance, np.linalg.norm(rel - t[:, None]*e, axis=1))
    distance[inside] = 0
    return distance, inside


def triangle_polygon_intersections(tri_xy, polygon):
    lo, hi = polygon.min(0), polygon.max(0)
    mask = np.all(tri_xy.max(1) >= lo, axis=1) & np.all(tri_xy.min(1) <= hi, axis=1)
    ids = np.flatnonzero(mask); active = tri_xy[ids]; hit = np.ones(len(ids), bool)
    # Exact convex intersection via separating axes. Axis-aligned bounds are
    # only a broad phase; empty corners of rotated floors are not supports.
    for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
        edge = b - a; rel = active - a
        cross = edge[0]*rel[..., 1] - edge[1]*rel[..., 0]
        hit &= ~np.all(cross < -1e-9, axis=1)
    for j in range(3):
        a = active[:, j]; edge = active[:, (j+1)%3] - a
        rel = polygon[None, :, :] - a[:, None, :]
        cross = edge[:, None, 0]*rel[..., 1] - edge[:, None, 1]*rel[..., 0]
        hit &= ~np.all(cross < -1e-9, axis=1)
    mask[:] = False; mask[ids[hit]] = True
    return mask


def protect(before, triangles, boundary, footprints):
    fixed = before[:, 2] <= .30
    fixed[boundary] = True
    freedom = np.ones(len(before))
    xy = before[triangles, :2]
    for polygon, _ in footprints:
        overlap = triangle_polygon_intersections(xy, polygon)
        fixed[np.unique(triangles[overlap])] = True
        distance, _ = polygon_distance(before[:, :2], polygon)
        freedom = np.minimum(freedom, smooth(.02, .55, distance))
    freedom[fixed] = 0
    return fixed, freedom


def run(diagnose_only=False):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    assert not bpy.app.background, 'Use the owned GUI Blender MCP'
    root = Path(bpy.data.filepath).parent.parent
    log = root / 'captures/road_contacts_20261123'
    terrain = bpy.data.objects['C25_ContourBuiltCoast']; mesh = terrain.data
    assert terrain.get('ground23_integrated_shoulders')
    assert not terrain.get('road23_contacts_grade'), 'One-time road grade already applied'
    assert np.max(abs(np.asarray(terrain.matrix_world) - np.eye(4))) < 1e-8
    with np.load(log / 'baseline.npz') as data:
        before = data['positions'].astype(float); loops_before = data['loops'].copy()
        colors_before = data['colors'].copy()
        assert np.all(data['sizes'] == 3)
    current = np.empty((len(mesh.vertices), 3), np.float32)
    mesh.vertices.foreach_get('co', current.ravel())
    assert np.array_equal(current, before.astype(np.float32)), 'Stale road baseline'
    loops = np.empty(len(mesh.loops), np.int32); mesh.loops.foreach_get('vertex_index', loops)
    assert np.array_equal(loops, loops_before), 'Topology changed since baseline'
    triangles = loops.reshape(-1, 3)
    colors = np.empty_like(colors_before); mesh.color_attributes['LandUse'].data.foreach_get('color', colors.ravel())
    assert np.array_equal(colors, colors_before), 'Unexpected mesh role change before grade'
    edges = np.sort(np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    boundary = np.unique(unique[counts == 1]); assert np.all(counts <= 2)
    old_bvh = BVHTree.FromPolygons(before.tolist(), triangles.tolist(), all_triangles=True)
    down = Vector((0, 0, -1))
    def height(bvh, x, y):
        hit = bvh.ray_cast(Vector((float(x), float(y), 60)), down, 250)[0]
        return None if hit is None else float(hit.z)
    def world_points(ob):
        p = np.empty((len(ob.data.vertices), 3), np.float32); ob.data.vertices.foreach_get('co', p.ravel())
        matrix = np.asarray(ob.matrix_world, float)
        return p.astype(float) @ matrix[:3, :3].T + matrix[:3, 3]
    active = {}
    def collect(col):
        if col.hide_render or col.name.startswith('Archive_'): return
        for ob in col.objects:
            if not ob.hide_render: active[ob.name] = ob
        for child in col.children: collect(child)
    roots = ('Reference_Town', 'Reference_Coast', 'Reference_Foliage', 'Reference_Rocks')
    for name in roots:
        assert name in bpy.data.collections; collect(bpy.data.collections[name])
    mandatory = ('Town_Floor', 'Town_Step', 'Hut_Floor', 'Hut_EntrySteps', 'Hut_StairStringer', 'Town_TavernPorch')
    trunk_names = ('Tree_Trunk', 'Palm_Trunk', 'Tree_Root', 'Palm_Root')
    ignored = ('Grass', 'Blade', 'Tuft', 'Crown', 'Frond', 'Leaf', 'Coconut', 'Canopy',
               'Roof', 'Rafter', 'Eave', 'Bargeboard', 'Sign', 'DoorHandle')
    footprints = []; contacts = []
    for ob in active.values():
        if ob.type != 'MESH' or ob == terrain or ob.name.startswith('G23_EmbeddedSlopeFragments'): continue
        required = ob.name.startswith(mandatory); tree = ob.name.startswith(trunk_names)
        rock = any(c.name == 'Reference_Rocks' for c in ob.users_collection)
        if not required and not rock and any(s in ob.name for s in ignored): continue
        p = world_points(ob)
        if not len(p): continue
        low, high = p.min(0), p.max(0)
        nearby = ((high[0] > 10.3 and low[0] < 14.8 and -low[1] > 8.7 and -high[1] < 29)
                  or (high[0] > 20.0 and low[0] < 26.3 and -low[1] > 28.0 and -high[1] < 34))
        if not required and not nearby: continue
        footprint_points = p
        if tree:
            lower = p[p[:, 2] < low[2] + max(.20, (high[2] - low[2]) * .12)]
            if len(lower) > 2: low, high = lower.min(0), lower.max(0); footprint_points = lower
        # Use a true projected shape rather than the empty corners of an
        # axis-aligned world envelope. All current semantic contacts remain
        # eligible; this change does not relax the contact-height tolerance.
        hull = convex_hull(footprint_points[:, :2])
        grid = np.array([(float(x), float(y)) for x in np.linspace(low[0], high[0], 3)
                         for y in np.linspace(low[1], high[1], 3)])
        _, inside = polygon_distance(grid, hull)
        samples = np.vstack([grid[inside], hull, (hull + np.roll(hull, -1, axis=0))*.5])
        samples = np.unique(np.round(samples, 8), axis=0).tolist()
        heights = [height(old_bvh, x, y) for x, y in samples]
        touching = any(-1.1 < low[2] - h < .32 for h in heights if h is not None)
        if not (required or tree or rock or touching): continue
        if not required and not tree and not rock and max(high[:2] - low[:2]) > 8: continue
        # A very large merged rocks envelope must not silently lock all three
        # regions; its connected components need explicit handling instead.
        assert not rock or max(high[:2] - low[:2]) < 8, 'Merged shore-rock envelope needs component contacts: ' + ob.name
        padding = np.array([[-.10, -.10], [-.10, .10], [.10, -.10], [.10, .10]])
        padded_hull = convex_hull((hull[:, None, :] + padding[None, :, :]).reshape(-1, 2))
        footprints.append((padded_hull, ob.name))
        contacts.append({'object': ob.name, 'kind': 'required' if required else 'tree' if tree else 'rock' if rock else 'prop',
                         'bounds_world': [low.tolist(), high.tolist()], 'samples_xy': samples, 'before_heights': heights,
                         'footprint_polygon_blender_xy': hull.tolist(), 'padded_polygon_blender_xy': padded_hull.tolist(),
                         'support_shape': 'actual mesh projected convex hull, plus 0.10m square padding'})
    assert sum(r['object'].startswith('Town_Floor') for r in contacts) == 9
    for name in ('Town_Step', 'Town_Step.001', 'Town_Step.002', 'Town_Step.003', 'Town_Step.004', 'Town_Step.005', 'Town_Step.007', 'Town_Step.008'):
        assert any(r['object'] == name for r in contacts), 'Missing current protected entrance ' + name
    assert any(r['kind'] == 'rock' for r in contacts), 'No current shore rock protected'
    fixed, freedom = protect(before, triangles, boundary, footprints)
    proposed, labels, designs = design(before, freedom); proposed[fixed] = 0
    old_n = np.cross(before[triangles[:, 1]] - before[triangles[:, 0]], before[triangles[:, 2]] - before[triangles[:, 0]])
    assert np.all(old_n[:, 2] > 0)
    factors = np.ones(len(before)); factors[fixed] = 0; history = []
    for iteration in range(90):
        after = (before + proposed * factors[:, None]).astype(np.float32).astype(float)
        new_n = np.cross(after[triangles[:, 1]] - after[triangles[:, 0]], after[triangles[:, 2]] - after[triangles[:, 0]])
        bad = np.flatnonzero(np.einsum('ij,ij->i', old_n, new_n) <= 0)
        if not len(bad): break
        factors[np.unique(triangles[bad])] *= .62
        limits = np.ones(len(before))
        np.minimum.at(limits, triangles.ravel(), np.repeat(np.minimum(1, factors[triangles].min(1) + .20), 3))
        factors = np.minimum(factors, limits); factors[fixed] = 0
        history.append({'iteration': iteration + 1, 'opposing_faces_before_reduction': int(len(bad))})
    assert not len(bad), 'Could not preserve normal orientation; mesh unchanged'
    delta = after - before; changed = np.flatnonzero(abs(delta[:, 2]) > 1e-6)
    for i, entry in enumerate(designs):
        ids = (labels == i) & (delta[:, 2] < -1e-6)
        entry['changed_vertices'] = int(ids.sum())
        entry['actual_maximum_lowering_m'] = float(-delta[ids, 2].min()) if ids.any() else 0
    ideal, ideal_labels, _ = design(before, np.ones(len(before)))
    tri_xy = before[triangles, :2]
    for i, entry in enumerate(designs):
        candidate = (ideal_labels == i) & (ideal[:, 2] < -.03)
        blockers = []
        for footprint, contact in zip(footprints, contacts):
            polygon, name = footprint
            overlap = triangle_polygon_intersections(tri_xy, polygon)
            locked = np.unique(triangles[overlap])
            count = int(candidate[locked].sum())
            distance, _ = polygon_distance(before[:, :2], polygon)
            proximity_count = int(np.count_nonzero(candidate & (distance < .55)))
            if count or proximity_count:
                item = dict(contact, locked_candidate_vertices=count, nearby_candidate_vertices=proximity_count)
                item['base_minus_terrain_m'] = [None if h is None else contact['bounds_world'][0][2] - h for h in contact['before_heights']]
                blockers.append(item)
        entry['unconstrained_candidates'] = int(candidate.sum())
        entry['fixed_candidates'] = int(np.count_nonzero(candidate & fixed))
        entry['candidate_freedom_quantiles'] = np.quantile(freedom[candidate], [0, .25, .5, .75, 1]).tolist() if candidate.any() else []
        entry['blocking_contacts'] = sorted(blockers, key=lambda r: (r['locked_candidate_vertices'], r['nearby_candidate_vertices']), reverse=True)
    diagnostic = {'mesh_modified': False, 'diagnose_only': diagnose_only, 'designs': designs, 'protected_contacts': len(contacts),
                  'contact_kinds': {k: sum(r['kind'] == k for r in contacts) for k in ('required', 'tree', 'rock', 'prop')},
                  'contacts': contacts, 'backtracking': history}
    (log / 'grade_precommit.json').write_text(json.dumps(diagnostic, indent=2), encoding='utf8')
    np.savez_compressed(log / 'grade_precommit.npz', before=before.astype(np.float32),
                        proposed=proposed.astype(np.float32), positions=after.astype(np.float32),
                        ideal=ideal.astype(np.float32), triangles=triangles, fixed=fixed,
                        freedom=freedom, boundary=boundary, labels=labels, ideal_labels=ideal_labels)
    if diagnose_only:
        print(json.dumps({'diagnose_only': True, 'mesh_modified': False, 'protected_contacts': len(contacts),
              'designs': [{k: v for k, v in d.items() if k != 'blocking_contacts'} for d in designs]}))
        return
    # Current exact contact protection leaves only a small free portion of the
    # inner bend. Preserve those supports and judge the combined grade/road-edge
    # change in-game; the previous 0.12m target was not an acceptance condition.
    assert designs[0]['changed_vertices'] > 0 and designs[0]['actual_maximum_lowering_m'] > 1e-6, 'Hospital bend has no free geometry change; mesh unchanged'
    diagnostic['clinic_scope_note'] = 'Small free-area lowering only; exact support protection retained. Actual lowering is recorded in designs; combined road occupancy and edge treatment require same-camera visual review.'
    assert np.array_equal(after[:, :2], before[:, :2]) and np.array_equal(after[fixed], before[fixed])
    assert np.array_equal(after[boundary], before[boundary])
    assert np.all(delta[:, 2] <= 2e-7) and -delta[:, 2].min() <= .380001
    assert np.all(new_n[:, 2] > 0) and np.all(np.linalg.norm(new_n, axis=1) > 1e-9)
    final_bvh = BVHTree.FromPolygons(after.tolist(), triangles.tolist(), all_triangles=True)
    maximum_support_delta = 0.0
    for row in contacts:
        final_h = [height(final_bvh, x, y) for x, y in row['samples_xy']]
        assert all((a is None) == (b is None) for a, b in zip(row['before_heights'], final_h))
        change = max([abs(a - b) for a, b in zip(row['before_heights'], final_h) if a is not None], default=0)
        row['max_height_delta_m'] = change; maximum_support_delta = max(maximum_support_delta, change)
    assert maximum_support_delta < 2e-5, 'Current prop/building/root/rock support changed'
    report = dict(diagnostic, applied=True, visual_accepted=False, mesh_modified=True,
                  changed_vertices=int(len(changed)), max_abs_blender_xyz_delta_m=abs(delta).max(0).tolist(),
                  topology_unchanged=True, xy_unchanged=True, boundary_unchanged=True,
                  water_vertices_unchanged=True, added_degenerate_faces=0, negative_xy_faces=0,
                  opposing_normals=0, maximum_support_delta_m=maximum_support_delta,
                  saved_blend=False, exported_assets=False)
    np.savez_compressed(log / 'grade_before_after.npz', before=before.astype(np.float32), positions=after.astype(np.float32),
                        delta=delta.astype(np.float32), triangles=triangles, boundary=boundary,
                        fixed=np.flatnonzero(fixed), changed=changed, labels=labels, factors=factors.astype(np.float32))
    try:
        mesh.vertices.foreach_set('co', after.astype(np.float32).ravel()); mesh.update()
        actual = np.empty_like(current); mesh.vertices.foreach_get('co', actual.ravel())
        assert np.array_equal(actual, after.astype(np.float32))
        terrain['road23_contacts_grade'] = True
        (log / 'grade.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
    except Exception:
        mesh.vertices.foreach_set('co', before.astype(np.float32).ravel()); mesh.update()
        if 'road23_contacts_grade' in terrain: del terrain['road23_contacts_grade']
        raise
    print(json.dumps({k: v for k, v in report.items() if k != 'contacts'}, ensure_ascii=False))


run()
