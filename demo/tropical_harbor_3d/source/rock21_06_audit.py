"""Read-only scene audit. Execute only in the verified Blender MCP session.

Writes geometry_audit.json; never moves objects, exports assets, or saves the blend.
The baseline contains terrain-local vertices, so the current terrain transform is
used for both versions. Grounding findings are candidates for visual inspection,
not instructions to lower complete prop assemblies or to accept the art.
"""
import bpy
import json
import math
import os
from collections import Counter
from pathlib import Path

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def audit_rock21():
    root = Path(bpy.data.filepath).parent.parent
    log = root / 'captures/rock_earth_rebuild_20261121'
    output = log / 'geometry_audit.json'
    baseline_path = log / 'terrain_before.npz'
    height_path = root / 'assets/reference/shore_relief_height.json'
    terrain = bpy.data.objects['C25_ContourBuiltCoast']
    mesh = terrain.data
    dirty_before = bool(bpy.data.is_dirty)
    world = terrain.matrix_world.copy()
    with np.load(str(baseline_path)) as baseline:
        old_positions = [world @ Vector(v) for v in baseline['positions']]
        old_faces = [baseline['loops'][s:s+n].tolist()
                     for s, n in zip(baseline['starts'], baseline['sizes'])]
    positions = [world @ v.co for v in mesh.vertices]
    faces = [list(p.vertices) for p in mesh.polygons]
    new_bvh = BVHTree.FromPolygons(positions, faces)
    old_bvh = BVHTree.FromPolygons(old_positions, old_faces)
    all_heights = [p.z for p in positions] + [p.z for p in old_positions]
    ray_top = max(all_heights) + 50.0
    ray_distance = ray_top - min(all_heights) + 50.0

    def rounded(value):
        return round(float(value), 6)

    def point_record(p):
        return {'x': rounded(p.x), 'z': rounded(-p.y), 'height': rounded(p.z)}

    def height(bvh, x, y):
        hit = bvh.ray_cast(Vector((x, y, ray_top)), Vector((0, 0, -1)), ray_distance)[0]
        return float(hit.z) if hit is not None else None

    def interval(values):
        return [rounded(min(values)), rounded(max(values))] if values else None

    def shore(z):
        t = min(1.0, max(0.0, (z + 18.7) / (-26.0 + 18.7)))
        return 7.8 + 1.45 * math.sin(z * .12) + .48 * math.sin(z * .29) - 21 * t * t * (3 - 2 * t)

    def topology(vs, fs):
        edges = Counter()
        directed = Counter()
        used = set()
        for face in fs:
            used.update(face)
            for a, b in zip(face, face[1:] + face[:1]):
                edges[tuple(sorted((a, b)))] += 1
                directed[(a, b)] += 1
        def edge_geometry(edge):
            return tuple(sorted(tuple(round(float(c), 5) for c in vs[i]) for i in edge))
        boundary = {edge_geometry(edge) for edge, count in edges.items() if count == 1}
        nonmanifold = [edge for edge, count in edges.items() if count > 2]
        bad_winding = [edge for edge, count in edges.items()
                       if count == 2 and (directed[edge] == 2 or directed[edge[::-1]] == 2)]
        return boundary, nonmanifold, bad_winding, len(vs) - len(used)

    old_boundary, old_nonmanifold, _, _ = topology(old_positions, old_faces)
    new_boundary, nonmanifold, bad_winding, loose_vertices = topology(positions, faces)
    mesh.calc_loop_triangles()
    negative, degenerate = [], []
    for triangle in mesh.loop_triangles:
        a, b, c = [positions[i] for i in triangle.vertices]
        cross = (b - a).cross(c - a)
        record = {'polygon': triangle.polygon_index, 'center': point_record((a+b+c)/3)}
        if cross.z < -1e-6:
            negative.append({**record, 'normal_z': rounded(cross.normalized().z)})
        if cross.length < 1e-9:
            degenerate.append(record)

    def world_points(obj):
        return [obj.matrix_world @ v.co for v in obj.data.vertices]

    def in_region(obj):
        corners = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
        return corners and min(-p.y for p in corners) <= 66 and max(-p.y for p in corners) >= 35

    def bottom_samples(obj, divisions=4):
        """Actual lower envelope at XY grid sites plus lowest vertices/face centers.

        Raycasts from below against the object's own mesh avoid treating bounding
        box corners outside rotated/irregular geometry as real contact points.
        """
        pts = world_points(obj)
        if not pts or not obj.data.polygons:
            return []
        low, high = min(p.z for p in pts), max(p.z for p in pts)
        band = min(.04, max(.005, (high-low)*.08))
        candidates = [p for p in pts if p.z <= low + band]
        # Wide floor bottom faces get perimeter midpoints as well as a grid.
        for poly in obj.data.polygons:
            poly_pts = [pts[i] for i in poly.vertices]
            if max(p.z for p in poly_pts) <= low + band:
                candidates.append(sum(poly_pts, Vector()) / len(poly_pts))
                candidates.extend((a+b)/2 for a, b in zip(poly_pts, poly_pts[1:]+poly_pts[:1]))
        object_bvh = BVHTree.FromPolygons(pts, [list(p.vertices) for p in obj.data.polygons])
        x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
        y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
        for ix in range(divisions + 1):
            for iy in range(divisions + 1):
                x = x0 + (x1-x0) * (.02 + .96*ix/divisions)
                y = y0 + (y1-y0) * (.02 + .96*iy/divisions)
                hit = object_bvh.ray_cast(Vector((x, y, low-1)), Vector((0, 0, 1)), high-low+2)[0]
                if hit is not None:
                    candidates.append(hit)
        unique = {tuple(round(float(c), 5) for c in p): p for p in candidates}
        return list(unique.values())

    def contact_report(obj, kind='prop', divisions=4):
        pts = bottom_samples(obj, divisions)
        records, missing = [], 0
        for p in pts:
            new_h, old_h = height(new_bvh, p.x, p.y), height(old_bvh, p.x, p.y)
            if new_h is None or old_h is None:
                missing += 1
                continue
            records.append((p, p.z-new_h, p.z-old_h, new_h-old_h))
        if not records:
            return {'object': obj.name, 'kind': kind, 'samples': 0, 'missing_ground_hits': missing,
                    'flags': ['no_ground_samples'], 'priority': 4}
        gaps = [r[1] for r in records]
        old_gaps = [r[2] for r in records]
        deltas = [r[3] for r in records]
        embedding_limit = {'rock': .60, 'shrub': .40, 'trunk': .25, 'floor': .10}.get(kind, .12)
        # Lower-envelope points on upper curved sides need not touch the ground.
        # Only all-positive gaps imply that the entire sampled object floats.
        floating = min(gaps) > .10
        sinking = min(gaps) < -embedding_limit
        changed = max(abs(v) for v in deltas) > .04
        new_float = floating and any(g > .10 and old <= .10 and delta < -.04
                                    for _, g, old, delta in records)
        new_sink = sinking and any(g < -embedding_limit and delta > .04
                                   for _, g, _, delta in records)
        flags = []
        if new_float:
            flags.append('new_floating_after_terrain_drop')
        if new_sink:
            flags.append('increased_burial_after_terrain_rise')
        if changed and not (new_float or new_sink):
            flags.append('terrain_changed_check_contact')
        if floating and not new_float:
            flags.append('baseline_or_supported_above_ground')
        if sinking and not new_sink:
            flags.append('baseline_embedding_check_if_intentional')
        if missing:
            flags.append('missing_ground_hits')
        priority = 4 if missing else (3 if new_float or new_sink else (2 if changed else (1 if flags else 0)))
        low_point = min(records, key=lambda r: r[1])
        high_point = max(records, key=lambda r: r[1])
        delta_point = max(records, key=lambda r: abs(r[3]))
        return {'object': obj.name, 'kind': kind, 'samples': len(records), 'missing_ground_hits': missing,
                'gap_range': interval(gaps), 'old_terrain_gap_range': interval(old_gaps),
                'ground_delta_range': interval(deltas), 'gap_median': rounded(np.median(gaps)),
                'lowest_gap_at': point_record(low_point[0]), 'highest_gap_at': point_record(high_point[0]),
                'largest_ground_change_at': point_record(delta_point[0]),
                'flags': flags, 'priority': priority}

    town = bpy.data.collections.get('Reference_Town')
    foundations = {}
    if town:
        for obj in sorted(town.all_objects, key=lambda o: o.name):
            if obj.type == 'MESH' and obj.name.startswith('Town_Floor'):
                key = str(obj.get('town_building') or obj.name)
                foundations[key] = contact_report(obj, 'floor', divisions=6)
                foundations[key]['in_rebuild_region'] = bool(in_region(obj))

    cargo_samples, cargo_missing, cargo_missing_objects = [], [], []
    for name in ('R20_UpperHull', 'R20_LowerHull', 'R20_HullBottom'):
        obj = bpy.data.objects.get(name)
        if obj is None:
            cargo_missing_objects.append(name)
            continue
        pts = world_points(obj)
        candidates = list(pts)
        for poly in obj.data.polygons:
            poly_pts = [pts[i] for i in poly.vertices]
            candidates.append(sum(poly_pts, Vector())/len(poly_pts))
            candidates.extend((a+b)/2 for a, b in zip(poly_pts, poly_pts[1:]+poly_pts[:1]))
        unique = {tuple(round(float(c), 5) for c in p): p for p in candidates if p.z < .6}
        for p in unique.values():
            new_h, old_h = height(new_bvh, p.x, p.y), height(old_bvh, p.x, p.y)
            if new_h is None or old_h is None:
                cargo_missing.append({'object': name, **point_record(p)})
            else:
                cargo_samples.append({'object': name, **point_record(p),
                                      'clearance': p.z-new_h, 'old_clearance': p.z-old_h})

    cache_report = {'path': str(height_path), 'exists': height_path.is_file()}
    if height_path.is_file():
        cache = json.loads(height_path.read_text(encoding='utf8'))
        expected = int(cache['rows']) * int(cache['columns'])
        cache_report['expected_values'] = expected
        cache_report['actual_values'] = len(cache['heights'])
        errors, misses, nonfinite, outside_domain = [], [], [], 0
        for row in range(int(cache['rows'])):
            z = cache['z0'] + row*cache['step']
            for col in range(int(cache['columns'])):
                d = cache['d0'] + col*cache['step']
                broad = row % 17 == 0 and col % 13 == 0
                local = 35 <= z <= 66 and -1 <= d <= 30 and row % 4 == 0 and col % 4 == 0
                if not (broad or local):
                    continue
                index = row*int(cache['columns']) + col
                if index >= len(cache['heights']):
                    misses.append({'row': row, 'col': col, 'reason': 'missing_cache_value'})
                    continue
                cached = float(cache['heights'][index])
                if not math.isfinite(cached):
                    nonfinite.append({'row': row, 'col': col})
                    continue
                actual = height(new_bvh, shore(z)+d, -z)
                if actual is None:
                    # refresh_height() deliberately stores -15 outside the mesh.
                    outside_domain += 1
                    actual = -15.0
                errors.append({'row': row, 'col': col, 'x': rounded(shore(z)+d), 'z': rounded(z),
                               'error': abs(cached-actual)})
        errors.sort(key=lambda r: r['error'], reverse=True)
        cache_report.update(samples=len(errors), max_error=rounded(errors[0]['error']) if errors else None,
                            p95_error=rounded(np.percentile([r['error'] for r in errors], 95)) if errors else None,
                            errors_over_1mm=sum(r['error'] > .001 for r in errors),
                            worst_samples=errors[:10], missing_hits=misses, nonfinite_values=nonfinite,
                            outside_mesh_fallback_samples=outside_domain)

    local_contacts = {}
    excluded_coast = ('Hut_', 'D19_Hut', 'D19_Thatch', 'D19_Reed', 'Pier_', 'D19_Deck', 'D19_Pile')
    for cname in ('Reference_Foliage', 'Reference_Rocks', 'Reference_Coast'):
        collection = bpy.data.collections.get(cname)
        records = []
        skipped = Counter()
        if collection:
            for obj in sorted(collection.all_objects, key=lambda o: o.name):
                if obj.type != 'MESH' or not in_region(obj):
                    continue
                lower_name = obj.name.lower()
                if cname == 'Reference_Foliage':
                    if 'trunk' in lower_name:
                        kind = 'trunk'
                    elif 'shrub' in lower_name or 'bush' in lower_name:
                        kind = 'shrub'
                    else:
                        skipped['canopies_branches_grass_or_other'] += 1
                        continue
                elif cname == 'Reference_Rocks':
                    kind = 'rock'
                else:
                    if obj.name.startswith(excluded_coast):
                        skipped['houses_and_pier_components'] += 1
                        continue
                    kind = 'prop'
                records.append(contact_report(obj, kind))
        records.sort(key=lambda r: (-r['priority'], r['object']))
        flags = Counter(flag for r in records for flag in r['flags'])
        local_contacts[cname] = {'collection_exists': collection is not None,
                                'inspected_objects': len(records), 'skipped': dict(skipped),
                                'counts_by_kind': dict(Counter(r['kind'] for r in records)),
                                'flags': dict(flags), 'actionable_candidates': sum(r['priority'] >= 3 for r in records),
                                'objects': records}

    cargo_samples.sort(key=lambda r: r['clearance'])
    cargo_minimum = rounded(cargo_samples[0]['clearance']) if cargo_samples else None
    report = {
        'source': bpy.data.filepath, 'pid': os.getpid(), 'baseline': str(baseline_path),
        'dirty_before': dirty_before, 'dirty_after': bool(bpy.data.is_dirty),
        'coordinates': 'Godot x,z,height; Blender world (x,-z,height)',
        'baseline_transform_assumption': 'Baseline local coordinates use current terrain.matrix_world; baseline has no transform metadata.',
        'terrain_matrix_world': [list(row) for row in world],
        'vertices': len(positions), 'triangles': len(mesh.loop_triangles),
        'boundary_edges': len(new_boundary), 'baseline_boundary_edges': len(old_boundary),
        'new_internal_boundary_edges': len(new_boundary-old_boundary),
        'removed_boundary_edges': len(old_boundary-new_boundary),
        'new_boundary_examples': list(sorted(new_boundary-old_boundary))[:20],
        'nonmanifold_edges': len(nonmanifold), 'baseline_nonmanifold_edges': len(old_nonmanifold),
        'inconsistent_winding_edges': len(bad_winding), 'loose_vertices': loose_vertices,
        'negative_triangle_count': len(negative), 'negative_triangles': negative,
        'degenerate_triangle_count': len(degenerate), 'degenerate_triangles': degenerate,
        'building_floor_support': foundations,
        'missing_required_building_floors': sorted(set(('HarborTavern', 'RosiesDiner', 'SariSari',
                                                       'TravelOffice', 'IslaSchool')) - set(foundations)),
        'building_support_note': 'Floor gaps include designed foundation/plinth height; compare terrain deltas and inspect assemblies before moving buildings.',
        'cargo_samples': len(cargo_samples), 'cargo_min_clearance': cargo_minimum,
        'cargo_penetration_samples': sum(r['clearance'] < 0 for r in cargo_samples),
        'cargo_worst_samples': cargo_samples[:10], 'cargo_missing_hits': cargo_missing,
        'cargo_missing_objects': cargo_missing_objects, 'height_cache': cache_report,
        'height_cache_samples': cache_report.get('samples', 0),
        'height_cache_max_error': cache_report.get('max_error'),
        'local_grounding_region': {'z_min': 35, 'z_max': 66}, 'local_grounding': local_contacts,
        'grounding_note': 'Positive gap means above terrain; negative means embedded. Upper props can rest on other props. Old-gap samples use current object pose on the old terrain and do not prove old object transforms were identical.',
    }
    report['geometry_checks_pass'] = not any((
        report['new_internal_boundary_edges'], report['removed_boundary_edges'], len(nonmanifold),
        len(bad_winding), len(negative), len(degenerate), cargo_missing, cargo_missing_objects,
        report['missing_required_building_floors'],
        not cargo_samples, cargo_minimum is not None and cargo_minimum < 0,
        not cache_report.get('exists'), cache_report.get('actual_values') != cache_report.get('expected_values'),
        not cache_report.get('samples'), cache_report.get('errors_over_1mm', 0),
        cache_report.get('missing_hits', []), cache_report.get('nonfinite_values', []),
        bool(bpy.data.is_dirty) != dirty_before,
    ))
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
    print(json.dumps({
        'report': str(output), 'geometry_checks_pass': report['geometry_checks_pass'],
        'triangles': report['triangles'], 'new_internal_boundary_edges': report['new_internal_boundary_edges'],
        'negative_triangles': len(negative), 'degenerate_triangles': len(degenerate),
        'cargo_min_clearance': cargo_minimum, 'height_cache_max_error': report['height_cache_max_error'],
        'building_ground_delta': {k: v.get('ground_delta_range') for k, v in foundations.items()},
        'local_grounding': {k: {'inspected': v['inspected_objects'], 'flags': v['flags'],
                                'priority_objects': [{'object': r['object'], 'flags': r['flags'],
                                                      'gap': r.get('gap_range'), 'delta': r.get('ground_delta_range')}
                                                     for r in v['objects'] if r['priority'] >= 2][:20]}
                            for k, v in local_contacts.items()},
    }, ensure_ascii=False))


audit_rock21()
