"""Bounded read-only S23 core audit, invoked only by the owner's live MCP.

Reads each NPZ field once. Does not update the dependency graph, mutate scene
data, export assets, save the blend, or execute any previous modeling script.
Only a completed report with core_checks_pass=true constitutes technical pass.
"""
import json
import math
import os
import time
from collections import Counter, defaultdict
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def audit_sample23_core():
    started = time.perf_counter()
    root = Path(bpy.data.filepath).parent.parent
    log = root / 'captures/rock_path_sample_20261123'
    output = log / 'core_audit.json'
    dirty_before = bool(bpy.data.is_dirty)
    report = {
        'status': 'running', 'source': bpy.data.filepath, 'pid': os.getpid(),
        'dirty_before': dirty_before, 'visual_accepted': False,
        'scope': 'Current terrain versus this turn terrain_baseline.npz; nine original floors; eight entrance steps; legacy 235 cargo samples; height cache; 45m UV mapping.',
        'baseline_npz_fields_read_once': ['positions', 'loops', 'starts', 'sizes'],
        'stage_seconds': {}, 'failures': [],
        'tolerances': {'floor_world_vertex_m': 0.00002, 'step_gap_m': [-0.035, 0.020],
                       'height_cache_m': 0.001, 'uv_absolute': 0.00002},
    }
    previous = started

    def checkpoint(stage):
        nonlocal previous
        now = time.perf_counter()
        report['stage_seconds'][stage] = round(now - previous, 3)
        report['stage'] = stage
        report['elapsed_seconds'] = round(now - started, 3)
        report['dirty_after'] = bool(bpy.data.is_dirty)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
        print('S23_CORE ' + stage + ' ' + str(report['elapsed_seconds']) + 's', flush=True)
        previous = now
        if now - started > 35:
            raise TimeoutError('Core audit exceeded 35 seconds after ' + stage)

    def check(condition, message):
        if not condition:
            report['failures'].append(message)

    def bounds(values):
        return [round(float(min(values)), 7), round(float(max(values)), 7)] if len(values) else None

    def world_vertices(obj):
        coords = np.empty((len(obj.data.vertices), 3), np.float32)
        obj.data.vertices.foreach_get('co', coords.ravel())
        matrix = np.asarray(obj.matrix_world, np.float64)
        return coords.astype(np.float64) @ matrix[:3, :3].T + matrix[:3, 3]

    def indices(mesh):
        loops = np.empty(len(mesh.loops), np.int32)
        starts = np.empty(len(mesh.polygons), np.int32)
        sizes = np.empty(len(mesh.polygons), np.int32)
        mesh.loops.foreach_get('vertex_index', loops)
        mesh.polygons.foreach_get('loop_start', starts)
        mesh.polygons.foreach_get('loop_total', sizes)
        return loops, starts, sizes

    def topology(loops, starts, sizes):
        following = np.roll(loops, -1)
        following[starts + sizes - 1] = loops[starts]
        edges = np.sort(np.column_stack((loops, following)), axis=1)
        unique, counts = np.unique(edges, axis=0, return_counts=True)
        boundary = {tuple(map(int, edge)) for edge in unique[counts == 1]}
        nonmanifold = {tuple(map(int, edge)) for edge in unique[counts > 2]}
        adjacency = defaultdict(list)
        for a, b in boundary:
            adjacency[a].append(b)
            adjacency[b].append(a)
        unseen = set(adjacency)
        components = []
        while unseen:
            pending = [next(iter(unseen))]
            vertices = set()
            while pending:
                vertex = pending.pop()
                if vertex in vertices:
                    continue
                vertices.add(vertex)
                pending.extend(n for n in adjacency[vertex] if n not in vertices)
            unseen.difference_update(vertices)
            degrees = [len(adjacency[v]) for v in vertices]
            components.append({'vertices': len(vertices), 'edges': sum(degrees) // 2,
                               'closed_cycle': all(d == 2 for d in degrees),
                               'degree_counts': dict(Counter(degrees))})
        return boundary, nonmanifold, sorted(components, key=lambda x: (x['vertices'], x['edges']))

    def triangle_quality(positions, triangles):
        points = positions[triangles]
        cross = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
        inverted = np.flatnonzero(cross[:, 2] < -1e-7)
        degenerate = np.flatnonzero(np.einsum('ij,ij->i', cross, cross) < 1e-18)
        return inverted, degenerate

    try:
        terrain = bpy.data.objects['C25_ContourBuiltCoast']
        mesh = terrain.data
        matrix = np.asarray(terrain.matrix_world, np.float64)
        session = json.loads((log / 'session_start.json').read_text(encoding='utf8'))
        old_matrix = np.asarray(session['terrain_transform'], np.float64)
        positions = world_vertices(terrain)
        loops, starts, sizes = indices(mesh)
        with np.load(str(log / 'terrain_baseline.npz')) as raw:
            old_local = raw['positions'].copy()
            old_loops = raw['loops'].copy()
            old_starts = raw['starts'].copy()
            old_sizes = raw['sizes'].copy()
        old_positions = old_local.astype(np.float64) @ old_matrix[:3, :3].T + old_matrix[:3, 3]
        report['terrain_transform_max_delta'] = float(np.max(abs(matrix - old_matrix)))
        report['active_terrain_modifiers'] = [m.name for m in terrain.modifiers if m.show_viewport]
        check(report['terrain_transform_max_delta'] < 1e-8, 'Terrain transform differs from this turn baseline')
        check(not report['active_terrain_modifiers'], 'Active modifiers are not represented by raw mesh BVH')
        check(bool(np.isfinite(positions).all()), 'Terrain has nonfinite coordinates')
        if not np.all(sizes == 3) or not np.all(old_sizes == 3):
            raise RuntimeError('This audit expects current and baseline triangle meshes')
        triangles = loops.reshape((-1, 3))
        old_triangles = old_loops.reshape((-1, 3))
        same_indices = (np.array_equal(loops, old_loops) and np.array_equal(starts, old_starts)
                        and np.array_equal(sizes, old_sizes) and len(positions) == len(old_positions))
        report['topology_arrays_unchanged'] = bool(same_indices)
        boundary, nonmanifold, components = topology(loops, starts, sizes)
        old_boundary, old_nonmanifold, old_components = topology(old_loops, old_starts, old_sizes)
        added = boundary - old_boundary
        removed = old_boundary - boundary
        shared = sorted({i for edge in boundary & old_boundary for i in edge})
        shifts = np.linalg.norm(positions[shared] - old_positions[shared], axis=1) if shared else np.array([])
        inverted, degenerate = triangle_quality(positions, triangles)
        old_inverted, old_degenerate = triangle_quality(old_positions, old_triangles)
        report['topology'] = {
            'vertices': len(positions), 'triangles': len(triangles),
            'baseline_vertices': len(old_positions), 'baseline_triangles': len(old_triangles),
            'boundary_edges': len(boundary), 'baseline_boundary_edges': len(old_boundary),
            'boundary_index_edges_added': len(added), 'boundary_index_edges_removed': len(removed),
            'added_boundary_examples': [list(e) for e in sorted(added)[:12]],
            'removed_boundary_examples': [list(e) for e in sorted(removed)[:12]],
            'boundary_components': components, 'baseline_boundary_components': old_components,
            'shared_boundary_max_displacement_m': float(shifts.max()) if len(shifts) else None,
            'shared_boundary_vertices_moved_over_20um': int(np.sum(shifts > .00002)),
            'nonmanifold_edges': len(nonmanifold), 'baseline_nonmanifold_edges': len(old_nonmanifold),
            'new_nonmanifold_edges': len(nonmanifold - old_nonmanifold),
            'negative_triangles': len(inverted), 'baseline_negative_triangles': len(old_inverted),
            'degenerate_triangles': len(degenerate), 'baseline_degenerate_triangles': len(old_degenerate),
            'negative_triangle_examples': [int(x) for x in inverted[:12]],
            'degenerate_triangle_examples': [int(x) for x in degenerate[:12]],
            'boundary_note': 'Only changes to one-face edge incidence imply new openings; coordinate movement alone is not an opening count.',
        }
        check(not added and not removed and components == old_components, 'Boundary index graph or components changed')
        check(not nonmanifold, 'Terrain contains nonmanifold edges')
        check(len(inverted) == 0, 'Terrain contains downward projected triangles')
        check(len(degenerate) == 0, 'Terrain contains degenerate triangles')
        checkpoint('topology_and_triangles')

        new_bvh = BVHTree.FromPolygons(positions.tolist(), triangles.tolist(), all_triangles=True)
        old_bvh = BVHTree.FromPolygons(old_positions.tolist(), old_triangles.tolist(), all_triangles=True)
        ray_top = max(float(positions[:, 2].max()), float(old_positions[:, 2].max())) + 50
        ray_distance = ray_top - min(float(positions[:, 2].min()), float(old_positions[:, 2].min())) + 50
        down = Vector((0, 0, -1))

        def height(bvh, x, y):
            hit = bvh.ray_cast(Vector((float(x), float(y), ray_top)), down, ray_distance)[0]
            return float(hit.z) if hit is not None else None

        checkpoint('terrain_bvhs')
        foundations = json.loads((log / 'foundations.json').read_text(encoding='utf8'))
        floor_rows = []
        for saved in foundations:
            obj = bpy.data.objects.get(saved['object'])
            if obj is None:
                floor_rows.append({'object': saved['object'], 'missing': True})
                check(False, 'Missing baseline floor ' + saved['object'])
                continue
            current = world_vertices(obj)
            prior = np.asarray(saved['corners'], np.float64)
            same_shape = current.shape == prior.shape
            error = float(np.max(abs(current - prior))) if same_shape else None
            corners = np.unique(current[current[:, 2] <= current[:, 2].min() + .001], axis=0)
            samples = list(corners) + [corners.mean(axis=0)]
            new_gaps, old_gaps, deltas = [], [], []
            missing = 0
            for p in samples:
                a, b = height(old_bvh, p[0], p[1]), height(new_bvh, p[0], p[1])
                if a is None or b is None:
                    missing += 1
                    continue
                new_gaps.append(p[2] - b)
                old_gaps.append(p[2] - a)
                deltas.append(b - a)
            unchanged = same_shape and error <= .00002
            row = {'object': obj.name, 'building': saved['name'], 'vertices': len(current),
                   'max_world_vertex_delta_m': error, 'geometry_and_pose_unchanged': bool(unchanged),
                   'bottom_and_center_samples': len(samples), 'missing_ground_hits': missing,
                   'terrain_delta_range_m': bounds(deltas), 'gap_range_m': bounds(new_gaps),
                   'baseline_gap_range_m': bounds(old_gaps),
                   'support_note': 'Floor gaps may contain authored foundation; unchanged floor geometry is checked independently.'}
            floor_rows.append(row)
            check(unchanged, 'Baseline floor geometry/pose changed: ' + obj.name)
            check(missing == 0, 'Missing ground sample at floor: ' + obj.name)
        current_floor_names = {o.name for o in bpy.data.collections['Reference_Town'].all_objects
                               if o.type == 'MESH' and o.name.startswith('Town_Floor')}
        baseline_floor_names = {r['object'] for r in foundations}
        report['floors'] = floor_rows
        report['floor_count'] = len(floor_rows)
        check(len(floor_rows) == 9 and current_floor_names == baseline_floor_names, 'Nine original floors not preserved as a set')

        # Six explicit town entrances plus the two lowest hut stairs selected in 11.
        stepnames = ['Town_Step.001', 'Town_Step.002', 'Town_Step.003',
                     'Town_Step.004', 'Town_Step.005', 'Town_Step.008']
        expected_huts = [(22.44397, 36.49067, 4.00032), (24.95671, 19.49066, 4.09074)]
        hut_matches = {str(p): [] for p in expected_huts}
        for obj in bpy.data.collections['Reference_Coast'].all_objects:
            if obj.type != 'MESH' or not obj.name.startswith('Hut_EntrySteps'):
                continue
            matrix_obj = np.asarray(obj.matrix_world, np.float64)
            corners = np.asarray(obj.bound_box, np.float64) @ matrix_obj[:3, :3].T + matrix_obj[:3, 3]
            center = corners.mean(axis=0)
            for x, z, h in expected_huts:
                if abs(center[0] - x) < .05 and abs(-center[1] - z) < .05 and abs(center[2] - h) < .04:
                    hut_matches[str((x, z, h))].append(obj.name)
        for names in hut_matches.values():
            check(len(names) == 1, 'Lowest hut stair match is missing or ambiguous: ' + str(names))
            stepnames.extend(names)
        step_rows = []
        for name in stepnames:
            obj = bpy.data.objects.get(name)
            if obj is None:
                check(False, 'Missing step ' + name)
                step_rows.append({'object': name, 'missing': True})
                continue
            box = np.asarray(obj.bound_box, np.float64)
            lo, hi = box.min(axis=0), box.max(axis=0)
            transform = np.asarray(obj.matrix_world, np.float64)
            samples = []
            for tx in (0, .5, 1):
                for ty in (0, .5, 1):
                    local = np.array([lo[0] + tx * (hi[0] - lo[0]), lo[1] + ty * (hi[1] - lo[1]), lo[2]])
                    p = local @ transform[:3, :3].T + transform[:3, 3]
                    current_h, old_h = height(new_bvh, p[0], p[1]), height(old_bvh, p[0], p[1])
                    samples.append({'godot': [float(p[0]), float(p[2]), float(-p[1])],
                                    'gap_m': float(p[2] - current_h) if current_h is not None else None,
                                    'baseline_gap_m': float(p[2] - old_h) if old_h is not None else None})
            gaps = [r['gap_m'] for r in samples if r['gap_m'] is not None]
            supported = len(gaps) == 9 and min(gaps) >= -.035 and max(gaps) <= .020
            step_rows.append({'object': name, 'building': obj.get('town_building'),
                              'samples': samples, 'gap_range_m': bounds(gaps), 'supported': bool(supported)})
            check(supported, 'Step support outside -35/+20 mm tolerance: ' + name)
        report['steps'] = step_rows
        report['step_count'] = len(step_rows)
        check(len(step_rows) == 8, 'Expected eight entrance steps')
        checkpoint('floors_and_steps')

        cargo = []
        cargo_misses = []
        for name in ('R20_UpperHull', 'R20_LowerHull', 'R20_HullBottom'):
            obj = bpy.data.objects.get(name)
            if obj is None:
                check(False, 'Missing cargo hull object ' + name)
                continue
            points = world_vertices(obj)
            obj_loops, obj_starts, obj_sizes = indices(obj.data)
            if len(points) > 5000 or len(obj_starts) > 5000:
                raise RuntimeError('Unexpectedly large legacy cargo hull ' + name)
            for start, size in zip(obj_starts, obj_sizes):
                face = points[obj_loops[start:start + size]]
                for p in list(face) + [face.mean(axis=0)]:
                    if p[2] >= .6:
                        continue
                    ground = height(new_bvh, p[0], p[1])
                    row = {'object': name, 'godot': [float(p[0]), float(p[2]), float(-p[1])]}
                    if ground is None:
                        cargo_misses.append(row)
                    else:
                        row['clearance_m'] = float(p[2] - ground)
                        cargo.append(row)
        cargo.sort(key=lambda r: r['clearance_m'])
        report['cargo'] = {'samples': len(cargo), 'expected_samples': 235,
                           'minimum_clearance_m': cargo[0]['clearance_m'] if cargo else None,
                           'penetrations': sum(row['clearance_m'] < 0 for row in cargo),
                           'missing_ground_hits': cargo_misses, 'worst_samples': cargo[:10],
                           'method': 'Every hull face vertex plus centroid below world Blender Z .6; duplicates retained.'}
        check(len(cargo) == 235 and not cargo_misses, 'Legacy cargo sampling is not the complete 235')
        check(bool(cargo) and cargo[0]['clearance_m'] >= 0, 'Cargo hull penetrates terrain')
        checkpoint('cargo_clearance')

        cache = json.loads((root / 'assets/reference/shore_relief_height.json').read_text(encoding='utf8'))
        rows, columns = int(cache['rows']), int(cache['columns'])
        values = np.asarray(cache['heights'], np.float64)
        if rows < 2 or columns < 2 or rows > 2000 or columns > 2000:
            raise RuntimeError('Unexpected height cache dimensions')
        check(len(values) == rows * columns, 'Height cache dimensions do not match values')
        check(bool(np.isfinite(values).all()), 'Height cache has nonfinite values')
        selected = {(row, col) for row in range(0, rows, 17) for col in range(0, columns, 13)}
        selected.add((rows - 1, columns - 1))
        # Add a denser sparse grid over the actual modified sample rectangle.
        for row in range(0, rows, 8):
            z = cache['z0'] + row * cache['step']
            if not 10 <= z <= 55:
                continue
            t = min(1., max(0., (z + 18.7) / (-26. + 18.7)))
            shore = 7.8 + 1.45 * math.sin(z * .12) + .48 * math.sin(z * .29) - 21 * t * t * (3 - 2*t)
            for col in range(0, columns, 8):
                x = shore + cache['d0'] + col * cache['step']
                if 8 <= x <= 34:
                    selected.add((row, col))
        cache_errors, cache_fallbacks, worst = [], 0, []
        for row, col in sorted(selected):
            index = row * columns + col
            if index >= len(values):
                continue
            z = float(cache['z0'] + row * cache['step'])
            t = min(1., max(0., (z + 18.7) / (-26. + 18.7)))
            shore = 7.8 + 1.45 * math.sin(z * .12) + .48 * math.sin(z * .29) - 21 * t*t*(3 - 2*t)
            x = shore + float(cache['d0'] + col * cache['step'])
            actual = height(new_bvh, x, -z)
            if actual is None:
                actual = -15.
                cache_fallbacks += 1
            error = abs(float(values[index]) - actual)
            cache_errors.append(error)
            if error > .001:
                worst.append({'row': row, 'col': col, 'godot_xz': [x, z],
                              'cached': float(values[index]), 'actual': actual, 'error_m': error})
        report['height_cache'] = {'rows': rows, 'columns': columns, 'values': len(values),
                                 'samples': len(cache_errors), 'maximum_error_m': max(cache_errors),
                                 'errors_over_1mm': len(worst), 'outside_mesh_fallback_samples': cache_fallbacks,
                                 'worst_samples': sorted(worst, key=lambda x: -x['error_m'])[:12]}
        check(bool(cache_errors) and max(cache_errors) <= .001, 'Height cache differs from current source mesh')
        checkpoint('height_cache')

        points_at_loops = positions[loops]
        uv_expected = {
            'UVMap': np.column_stack(((points_at_loops[:, 0] - 8) / 26, (-points_at_loops[:, 1] - 10) / 45)),
            'RockRegion': np.column_stack(((-points_at_loops[:, 1] - 10) / 45, (points_at_loops[:, 2] - .7) / 4.4)),
        }
        uv_rows = {}
        for name, expected in uv_expected.items():
            layer = mesh.uv_layers.get(name)
            if layer is None:
                check(False, 'Missing UV layer ' + name)
                uv_rows[name] = {'missing': True}
                continue
            actual = np.empty((len(mesh.loops), 2), np.float32)
            layer.data.foreach_get('uv', actual.ravel())
            finite = bool(np.isfinite(actual).all())
            error = float(np.max(abs(actual - expected)))
            uv_rows[name] = {'maximum_error': error, 'finite': finite,
                             'out_of_tolerance_loops': int(np.sum(np.max(abs(actual - expected), axis=1) > .00002))}
            check(finite and error <= .00002, 'UV mapping stale or incorrect: ' + name)
        report['uv'] = {'layers': [u.name for u in mesh.uv_layers], 'mappings': uv_rows,
                        'source_convention': 'Blender V grows upward; glTF export reverses V for PNG/EXR top-first image rows.',
                        'extent': 'Godot x8..34,z10..55; rock height0.7..5.1'}
        check(len(mesh.uv_layers) >= 2 and mesh.uv_layers[0].name == 'UVMap'
              and mesh.uv_layers[1].name == 'RockRegion', 'GLB UV2 source layer order is incorrect')
        check(bool(bpy.data.is_dirty) == dirty_before, 'Audit changed Blender dirty state')
        report['core_checks_pass'] = not report['failures']
        report['status'] = 'completed'
        checkpoint('complete')
        print(json.dumps({'status': report['status'], 'core_checks_pass': report['core_checks_pass'],
                          'failures': report['failures'], 'elapsed_seconds': report['elapsed_seconds'],
                          'vertices': len(positions), 'triangles': len(triangles),
                          'floor_count': len(floor_rows), 'step_count': len(step_rows),
                          'cargo_samples': len(cargo), 'cargo_minimum_clearance_m': report['cargo']['minimum_clearance_m'],
                          'cache_max_error_m': report['height_cache']['maximum_error_m'],
                          'report': str(output)}, ensure_ascii=False), flush=True)
    except Exception as exc:
        report['status'] = 'failed'
        report['core_checks_pass'] = False
        report['error'] = type(exc).__name__ + ': ' + str(exc)
        report['dirty_after'] = bool(bpy.data.is_dirty)
        report['elapsed_seconds'] = round(time.perf_counter() - started, 3)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
        raise


audit_sample23_core()
