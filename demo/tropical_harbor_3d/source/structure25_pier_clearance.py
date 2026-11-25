"""Read-only live GUI audit of the trade pier approach and moved shore rocks.

Calling the function reads raw meshes, transforms, the current design and prop
records. It never updates the depsgraph, modifies objects, saves or exports.
Only pier_clearance.json is written. Technical clearance is not visual approval.
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import numpy as np


def audit_structure25_pier_clearance(expected_pid):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    expected_source = Path('F:/马尼拉godot/manila-godot/demo/tropical_harbor_3d/source/harbor_shore_control_mcp.blend')
    root = expected_source.parent.parent
    log = root / 'captures/terrain_structure_20261123'
    read = lambda name: json.loads((log / name).read_text(encoding='utf8'))
    session, design, props = read('session_start.json'), read('design.json'), read('props.json')
    if (bpy.app.background or os.getpid() != expected_pid or expected_pid != session['pid']
            or Path(bpy.data.filepath).resolve() != expected_source.resolve()
            or bpy.types.blendermcp_server.port != session['port'] or session['port'] != 9881):
        raise RuntimeError('Owned GUI/source/PID/port mismatch')
    dirty_before = bool(bpy.data.is_dirty)
    report = {'read_only': True, 'visual_accepted': False, 'pid': os.getpid(),
              'port': session['port'], 'source': bpy.data.filepath,
              'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'dirty_before': dirty_before, 'failures': [], 'rock_checks': [],
              'target_rocks': [], 'horizontal_margin_m': .06,
              'protected_headroom_above_ground_m': [0.0, 1.8]}

    def check(ok, message):
        if not ok:
            report['failures'].append(message)

    def world(obj):
        vertices = np.empty((len(obj.data.vertices), 3), np.float32)
        obj.data.vertices.foreach_get('co', vertices.ravel())
        matrix = np.asarray(obj.matrix_world, float)
        return vertices.astype(float) @ matrix[:3, :3].T + matrix[:3, 3]

    def hull(points):
        pts = sorted(set(tuple(map(float, p)) for p in points))
        def cross(a, b, c):
            return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        lower, upper = [], []
        for p in pts:
            while len(lower) > 1 and cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)
        for p in reversed(pts):
            while len(upper) > 1 and cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)
        return np.asarray(lower[:-1]+upper[:-1], float)

    def sat_margin(a, b):
        # A separating-axis gap > .06 clears the pair. Smaller gaps are
        # conservatively checked in height; a diagonal gap may be stricter.
        maximum_gap = -1e9
        for poly in (a, b):
            for edge in np.roll(poly, -1, axis=0)-poly:
                length = np.linalg.norm(edge)
                if length < 1e-10:
                    continue
                axis = np.array([-edge[1], edge[0]]) / length
                aa, bb = a @ axis, b @ axis
                gap = max(float(aa.min()-bb.max()), float(bb.min()-aa.max()))
                maximum_gap = max(maximum_gap, gap)
        return maximum_gap <= .06, float(maximum_gap)

    def inside(point, poly):
        edges = np.roll(poly, -1, axis=0)-poly
        rel = point-poly
        c = edges[:, 0]*rel[:, 1]-edges[:, 1]*rel[:, 0]
        return bool(np.all(c >= -1e-7) or np.all(c <= 1e-7))

    def overlap_probes(a, b):
        result = [p for p in a if inside(p, b)] + [p for p in b if inside(p, a)]
        for p, p2 in zip(a, np.roll(a, -1, axis=0)):
            d = p2-p
            for q, q2 in zip(b, np.roll(b, -1, axis=0)):
                e = q2-q
                det = d[0]*e[1]-d[1]*e[0]
                if abs(det) < 1e-10:
                    continue
                rel = q-p
                t = (rel[0]*e[1]-rel[1]*e[0])/det
                u = (rel[0]*d[1]-rel[1]*d[0])/det
                if -1e-7 <= t <= 1+1e-7 and -1e-7 <= u <= 1+1e-7:
                    result.append(p+t*d)
        # Near but disjoint footprints can violate the .06 margin. Probe all
        # protected polygon corners conservatively instead of ignoring them.
        if not result:
            result = list(b)
        result = np.asarray(result, float)
        return np.concatenate([result, result.mean(0)[None]])

    terrain = bpy.data.objects['C25_ContourBuiltCoast']
    check(not any(m.show_viewport for m in terrain.modifiers), 'Terrain has active modifiers')
    terrain_world = world(terrain)
    faces = [list(p.vertices) for p in terrain.data.polygons]
    bvh = BVHTree.FromPolygons(terrain_world.tolist(), faces, all_triangles=True)
    base = np.load(log/'baseline.npz')
    old_bvh = BVHTree.FromPolygons(base['positions'].astype(float).tolist(), base['triangles'].tolist(), all_triangles=True)

    def ground(tree, xz):
        hit = tree.ray_cast(Vector((float(xz[0]), float(-xz[1]), 80)), Vector((0, 0, -1)), 200)[0]
        return None if hit is None else float(hit.z)

    route = next(r for r in design['routes'] if r['name'] == 'lower_trade_pier_descent')
    landing = next(p for p in design['platforms'] if p['name'] == 'trade_pier_sand_landing')
    zones = [{'name': landing['name'], 'polygon': hull(landing['polygon']), 'kind': 'landing'}]
    for i, (a, b) in enumerate(zip(route['points'], route['points'][1:])):
        a, b = np.asarray(a[:2], float), np.asarray(b[:2], float)
        tangent = b-a
        tangent /= np.linalg.norm(tangent)
        side = np.array([-tangent[1], tangent[0]]) * route['halfwidth']
        zones.append({'name': route['name']+':segment_'+str(i),
                      'polygon': hull([a-side, b-side, b+side, a+side]), 'kind': 'route'})
    report['protected_zones'] = [{'name': z['name'], 'polygon_xz': z['polygon'].tolist()} for z in zones]

    collection = bpy.data.collections.get('Reference_Rocks')
    check(collection is not None and not collection.hide_render, 'Reference_Rocks collection missing/hidden')
    rocks = [] if collection is None else [o for o in collection.all_objects
        if o.type == 'MESH' and not o.hide_render and o.name in bpy.context.scene.objects
        and not any(c.name.startswith('Archive_') or c.hide_render for c in o.users_collection)]
    check(bool(rocks), 'No active shore rocks were checked')
    check({'Bank_Boulder.015', 'Bank_Boulder.016'} <= {o.name for o in rocks},
          'Target shore rocks are not both active in Reference_Rocks')
    for obj in sorted(rocks, key=lambda o: o.name):
        check(not any(m.show_viewport for m in obj.modifiers), 'Rock has active modifiers: '+obj.name)
        vertices = world(obj)
        outline = hull(vertices[:, [0, 1]] * np.array([1, -1]))
        row = {'object': obj.name, 'world_vertex_count': len(vertices),
               'hull_vertex_count': len(outline), 'height_range_m': [float(vertices[:, 2].min()), float(vertices[:, 2].max())],
               'near_or_overlapping_zones': [], 'clear': True}
        if len(outline) < 3:
            check(False, 'Degenerate rock footprint: '+obj.name)
            row['clear'] = False
        else:
            for zone in zones:
                nearby, gap = sat_margin(outline, zone['polygon'])
                if not nearby:
                    continue
                probes = overlap_probes(outline, zone['polygon'])
                heights = [ground(bvh, q) for q in probes]
                missing = sum(h is None for h in heights)
                known = [h for h in heights if h is not None]
                low = min(known) if known else None
                high = max(known)+1.8 if known else None
                intersects = bool(not known or not (row['height_range_m'][1] < low-.001 or row['height_range_m'][0] > high+.001))
                passed = not intersects and missing == 0
                detail = {'zone': zone['name'], 'sat_maximum_separation_m': gap,
                          'ground_probe_count': len(probes), 'missing_ground': missing,
                          'protected_height_range_m': [low, high], 'height_intersects': intersects,
                          'result': 'clear_by_vertical_separation' if passed else 'obstruction_or_margin_violation'}
                row['near_or_overlapping_zones'].append(detail)
                if not passed:
                    row['clear'] = False
                    check(False, 'Rock blocks protected pier approach: '+obj.name+' / '+zone['name'])
        report['rock_checks'].append(row)

    check(props.get('pid') == expected_pid and props.get('applied') is True, 'Prop report is not applied in current session')
    records = {r['name']: r for r in read('objects_before.json')}
    group_map = {g['support_object']: g for g in props['groups']}
    for name in ['Bank_Boulder.015', 'Bank_Boulder.016']:
        obj, item, old = bpy.data.objects.get(name), group_map.get(name), records.get(name)
        if obj is None or item is None or old is None:
            check(False, 'Target rock or placement record missing: '+name)
            continue
        before = np.asarray(old['matrix'], float)
        expected = before.copy()
        expected[:3, 3] += np.asarray(item['delta_blender'], float)
        current = np.asarray(obj.matrix_world, float)
        matrix_error = float(np.max(abs(current-expected)))
        old_root = np.asarray(item['before_support_blender'], float)
        local_root = np.linalg.inv(before) @ np.r_[old_root, 1]
        current_root = (current @ local_root)[:3]
        current_ground = ground(bvh, [current_root[0], -current_root[1]])
        original_ground = ground(old_bvh, [old_root[0], -old_root[1]])
        height = float(np.ptp(world(obj)[:, 2]))
        burial_limits = [-max(.35, height*.30), .025]
        gap = None if current_ground is None else float(current_root[2]-current_ground)
        expected_gap = None if original_ground is None else float(np.clip(old_root[2]-original_ground, *burial_limits))
        gap_error = None if gap is None or expected_gap is None else abs(gap-expected_gap)
        recorded_root_error = float(np.max(abs(current_root-np.asarray(item['after_support_blender']))))
        passed = bool(matrix_error < .00003 and recorded_root_error < .00003 and gap_error is not None and gap_error < .0001)
        check(passed, 'Target rock live pose/root burial differs from current placement report: '+name)
        report['target_rocks'].append({'object': name, 'placement_status': item['status'],
            'matrix_max_error': matrix_error, 'recorded_root_max_error': recorded_root_error,
            'current_root_blender': current_root.tolist(), 'ground_height_m': current_ground,
            'root_gap_m': gap, 'expected_preserved_burial_m': expected_gap,
            'root_gap_error_m': gap_error, 'allowed_burial_range_m': burial_limits, 'passed': passed})
    report['active_rock_count'] = len(rocks)
    report['dirty_after'] = bool(bpy.data.is_dirty)
    check(report['dirty_after'] == dirty_before, 'Read-only pier audit changed dirty state')
    report['technical_pass'] = not report['failures']
    report['status'] = 'completed'
    (log/'pier_clearance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    print(json.dumps({'pier_clearance_pass': report['technical_pass'], 'active_rocks': len(rocks),
        'protected_zones': len(zones), 'target_rocks_verified': sum(r['passed'] for r in report['target_rocks']),
        'failures': report['failures'], 'dirty': report['dirty_after']}, ensure_ascii=False))
    return report
