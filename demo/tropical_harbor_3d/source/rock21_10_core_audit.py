"""Bounded, read-only core audit for the verified Blender MCP session.

No prop scan, dependency-graph update, scene mutation, export, or blend save.
Writes a small checkpoint/result to captures/rock_earth_rebuild_20261121/
core_audit.json. A result is valid only when status == 'completed'.
"""
import bpy
import json
import math
import os
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def audit_core_rock21():
    started = time.perf_counter()
    root = Path(bpy.data.filepath).parent.parent
    log = root / 'captures/rock_earth_rebuild_20261121'
    output = log / 'core_audit.json'
    baseline_path = log / 'terrain_before.npz'
    cache_path = root / 'assets/reference/shore_relief_height.json'
    dirty_before = bool(bpy.data.is_dirty)
    report = {
        'status': 'running', 'source': bpy.data.filepath, 'pid': os.getpid(),
        'baseline': str(baseline_path), 'dirty_before': dirty_before,
        'scope': 'Terrain topology/triangles, all Town_Floor objects (nine baseline buildings), legacy cargo samples, sparse height cache; no props.',
        'stage_seconds': {},
        'baseline_transform_assumption': 'Both meshes use current terrain.matrix_world; baseline stores local vertices only.',
        'boundary_identity_assumption': 'The rock21 rebuild/repair scripts preserve the baseline vertex-index prefix. Any boundary index or component change fails this audit and needs diagnosis; coordinate differences are reported separately.',
        'support_note': 'Floor gaps can include designed foundations. Old-terrain samples use current object poses.',
    }
    last_stage = started

    def checkpoint(stage):
        nonlocal last_stage
        now = time.perf_counter()
        report['stage_seconds'][stage] = round(now - last_stage, 3)
        report['elapsed_seconds'] = round(now - started, 3)
        report['stage'] = stage
        report['dirty_after'] = bool(bpy.data.is_dirty)
        if now - started > 30:
            raise TimeoutError('Core audit exceeded 30-second budget after ' + stage)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
        print('CORE_AUDIT ' + stage + ' ' + str(report['elapsed_seconds']) + 's', flush=True)
        last_stage = now

    def world_vertices(obj):
        coords = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
        obj.data.vertices.foreach_get('co', coords)
        coords = coords.reshape((-1, 3))
        matrix = np.asarray(obj.matrix_world, dtype=np.float64)
        return coords @ matrix[:3, :3].T + matrix[:3, 3]

    def mesh_indices(mesh):
        loops = np.empty(len(mesh.loops), dtype=np.int32)
        starts = np.empty(len(mesh.polygons), dtype=np.int32)
        sizes = np.empty(len(mesh.polygons), dtype=np.int32)
        mesh.loops.foreach_get('vertex_index', loops)
        mesh.polygons.foreach_get('loop_start', starts)
        mesh.polygons.foreach_get('loop_total', sizes)
        return loops, starts, sizes

    def topology(positions, loops, starts, sizes):
        following = np.roll(loops, -1)
        following[starts + sizes - 1] = loops[starts]
        edges = np.column_stack((loops, following))
        edges.sort(axis=1)
        unique, counts = np.unique(edges, axis=0, return_counts=True)
        boundary_indices = {tuple(map(int, edge)) for edge in unique[counts == 1]}
        boundary_coordinates = {
            tuple(sorted(tuple(np.round(positions[i], 5)) for i in edge))
            for edge in boundary_indices
        }
        adjacency = defaultdict(list)
        for a, b in boundary_indices:
            adjacency[a].append(b)
            adjacency[b].append(a)
        unseen = set(adjacency)
        components = []
        while unseen:
            pending, vertices = [min(unseen)], set()
            while pending:
                vertex = pending.pop()
                if vertex in vertices:
                    continue
                vertices.add(vertex)
                pending.extend(n for n in adjacency[vertex] if n not in vertices)
            unseen -= vertices
            degrees = [len(adjacency[v]) for v in vertices]
            components.append({'vertices': len(vertices), 'edges': sum(degrees) // 2,
                               'closed_cycle': all(d == 2 for d in degrees),
                               'degree_counts': dict(Counter(degrees))})
        return boundary_indices, boundary_coordinates, components, int(np.count_nonzero(counts > 2))

    def interval(values):
        return [round(float(min(values)), 6), round(float(max(values)), 6)] if values else None

    def point_record(p):
        return {'x': round(float(p[0]), 6), 'z': round(float(-p[1]), 6),
                'height': round(float(p[2]), 6)}

    try:
        terrain = bpy.data.objects['C25_ContourBuiltCoast']
        mesh = terrain.data
        matrix = np.asarray(terrain.matrix_world, dtype=np.float64)
        positions = world_vertices(terrain)
        loops, starts, sizes = mesh_indices(mesh)
        with np.load(str(baseline_path)) as raw:
            old_positions = np.asarray(raw['positions'], dtype=np.float64) @ matrix[:3, :3].T + matrix[:3, 3]
            old_loops = raw['loops'].copy()
            old_starts = raw['starts'].copy()
            old_sizes = raw['sizes'].copy()
        report['vertices'] = len(positions)
        old_boundary, old_coordinates, old_components, old_nonmanifold = topology(old_positions, old_loops, old_starts, old_sizes)
        new_boundary, new_coordinates, new_components, nonmanifold = topology(positions, loops, starts, sizes)
        added_boundary = new_boundary - old_boundary
        removed_boundary = old_boundary - new_boundary
        shared_boundary_vertices = sorted({i for edge in new_boundary & old_boundary for i in edge})
        boundary_displacements = np.linalg.norm(positions[shared_boundary_vertices] - old_positions[shared_boundary_vertices], axis=1)
        coordinate_added = sorted(new_coordinates - old_coordinates)
        coordinate_removed = sorted(old_coordinates - new_coordinates)
        report.update(
            boundary_edges=len(new_boundary), baseline_boundary_edges=len(old_boundary),
            boundary_index_edges_added=len(added_boundary),
            boundary_index_edges_removed=len(removed_boundary),
            boundary_index_added_examples=[list(edge) for edge in sorted(added_boundary)[:20]],
            boundary_index_removed_examples=[list(edge) for edge in sorted(removed_boundary)[:20]],
            boundary_index_graph_unchanged=not added_boundary and not removed_boundary,
            boundary_components=new_components, baseline_boundary_components=old_components,
            boundary_component_count=len(new_components), baseline_boundary_component_count=len(old_components),
            boundary_noncycle_components=sum(not item['closed_cycle'] for item in new_components),
            boundary_coordinate_edges_added=len(coordinate_added),
            boundary_coordinate_edges_removed=len(coordinate_removed),
            boundary_coordinate_added_examples=[[[float(v) for v in p] for p in edge] for edge in coordinate_added[:20]],
            boundary_coordinate_removed_examples=[[[float(v) for v in p] for p in edge] for edge in coordinate_removed[:20]],
            boundary_shared_vertex_max_displacement_m=float(boundary_displacements.max()) if len(boundary_displacements) else None,
            boundary_shared_vertices_moved=int(np.count_nonzero(boundary_displacements > 0)),
            boundary_coordinate_note='5-decimal world Blender xyz edge-set differences are geometric movement/rounding evidence, not hole counts. New holes expose new one-face edge incidence and fail the index/component checks.',
            nonmanifold_edges=nonmanifold, baseline_nonmanifold_edges=old_nonmanifold,
        )
        mesh.calc_loop_triangles()
        triangles = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
        mesh.loop_triangles.foreach_get('vertices', triangles)
        triangles = triangles.reshape((-1, 3))
        triangle_points = positions[triangles]
        crosses = np.cross(triangle_points[:, 1] - triangle_points[:, 0],
                           triangle_points[:, 2] - triangle_points[:, 0])
        negative = np.flatnonzero(crosses[:, 2] < -1e-6)
        degenerate = np.flatnonzero(np.einsum('ij,ij->i', crosses, crosses) < 1e-18)
        report['triangles'] = len(triangles)
        report['negative_triangle_count'] = len(negative)
        report['degenerate_triangle_count'] = len(degenerate)
        report['negative_triangles'] = [
            {'triangle': int(i), 'center': point_record(triangle_points[i].mean(axis=0))}
            for i in negative[:30]
        ]
        report['degenerate_triangles'] = [int(i) for i in degenerate[:30]]
        checkpoint('terrain_geometry')

        new_faces = [loops[s:s+n].tolist() for s, n in zip(starts, sizes)]
        old_faces = [old_loops[s:s+n].tolist() for s, n in zip(old_starts, old_sizes)]
        new_bvh = BVHTree.FromPolygons(positions.tolist(), new_faces)
        old_bvh = BVHTree.FromPolygons(old_positions.tolist(), old_faces)
        ray_top = float(max(positions[:, 2].max(), old_positions[:, 2].max()) + 50)
        ray_distance = ray_top - float(min(positions[:, 2].min(), old_positions[:, 2].min())) + 50
        down = Vector((0, 0, -1))

        def height(bvh, x, y):
            hit = bvh.ray_cast(Vector((float(x), float(y), ray_top)), down, ray_distance)[0]
            return float(hit.z) if hit is not None else None

        checkpoint('terrain_bvhs')

        required_floors = ('HarborTavern', 'RosiesDiner', 'SariSari', 'TravelOffice',
                           'SeaBreezeGrill', 'StaMariaChapel', 'IslaTradingPost',
                           'IslaSchool', 'IslaClinic')
        town = bpy.data.collections.get('Reference_Town')
        floors = sorted((obj for obj in town.all_objects
                         if obj.type == 'MESH' and obj.name.startswith('Town_Floor')),
                        key=lambda obj: obj.name) if town else []
        found_buildings = {str(obj.get('town_building') or obj.name) for obj in floors}
        support = {}
        for floor in floors:
            building = str(floor.get('town_building') or floor.name)
            key = building if building not in support else building + ':' + floor.name
            floor_matrix = np.asarray(floor.matrix_world, dtype=np.float64)
            corners = np.asarray(floor.bound_box, dtype=np.float64)
            corners = corners @ floor_matrix[:3, :3].T + floor_matrix[:3, 3]
            deltas, gaps, old_gaps = [], [], []
            misses = 0
            for p in corners:
                new_h, old_h = height(new_bvh, p[0], p[1]), height(old_bvh, p[0], p[1])
                if new_h is None or old_h is None:
                    misses += 1
                    continue
                deltas.append(new_h - old_h)
                gaps.append(p[2] - new_h)
                old_gaps.append(p[2] - old_h)
            support[key] = {
                'object': floor.name, 'town_building': building,
                'method': '8 world-transformed mesh bounding-box corners',
                'samples': len(deltas), 'missing_ground_hits': misses,
                'ground_delta_range': interval(deltas), 'gap_range': interval(gaps),
                'old_terrain_gap_range': interval(old_gaps),
            }
        report['building_floor_support'] = support
        report['building_floor_count'] = len(floors)
        report['building_floor_inspected_count'] = len(support)
        report['expected_baseline_building_floor_count'] = len(required_floors)
        report['missing_required_building_floors'] = sorted(set(required_floors) - found_buildings)

        # Exactly the prior audit's sampling: every face's vertices and face
        # center below height 0.6; duplicates intentionally retained (235 total).
        cargo, cargo_misses, missing_cargo = [], [], []
        for name in ('R20_UpperHull', 'R20_LowerHull', 'R20_HullBottom'):
            obj = bpy.data.objects.get(name)
            if obj is None:
                missing_cargo.append(name)
                continue
            if len(obj.data.vertices) > 5000 or len(obj.data.polygons) > 5000:
                raise RuntimeError('Legacy cargo mesh unexpectedly large: ' + name)
            pts = world_vertices(obj)
            obj_loops, obj_starts, obj_sizes = mesh_indices(obj.data)
            candidates = []
            for start, size in zip(obj_starts, obj_sizes):
                face_points = pts[obj_loops[start:start+size]]
                candidates.extend(face_points)
                candidates.append(face_points.mean(axis=0))
            for p in candidates:
                if p[2] >= .6:
                    continue
                ground = height(new_bvh, p[0], p[1])
                if ground is None:
                    cargo_misses.append({'object': name, **point_record(p)})
                else:
                    cargo.append({'object': name, **point_record(p), 'clearance': float(p[2] - ground)})
        cargo.sort(key=lambda r: r['clearance'])
        report['cargo_samples'] = len(cargo)
        report['cargo_expected_legacy_samples'] = 235
        report['cargo_min_clearance'] = cargo[0]['clearance'] if cargo else None
        report['cargo_penetration_samples'] = sum(r['clearance'] < 0 for r in cargo)
        report['cargo_worst_samples'] = cargo[:10]
        report['cargo_missing_hits'] = cargo_misses
        report['cargo_missing_objects'] = missing_cargo
        checkpoint('floors_and_cargo')

        cache = json.loads(cache_path.read_text(encoding='utf8'))
        rows, columns = int(cache['rows']), int(cache['columns'])
        if rows < 1 or columns < 1 or rows > 2000 or columns > 2000:
            raise RuntimeError('Unexpected height cache dimensions')
        errors, missing_cache_values, nonfinite, outside_domain = [], 0, 0, 0
        for row in range(0, rows, 17):
            z = float(cache['z0'] + row * cache['step'])
            t = min(1., max(0., (z + 18.7) / (-26. + 18.7)))
            shore_x = 7.8 + 1.45 * math.sin(z * .12) + .48 * math.sin(z * .29) - 21 * t * t * (3 - 2*t)
            for col in range(0, columns, 13):
                index = row * columns + col
                if index >= len(cache['heights']):
                    missing_cache_values += 1
                    continue
                value = float(cache['heights'][index])
                if not math.isfinite(value):
                    nonfinite += 1
                    continue
                x = shore_x + float(cache['d0'] + col * cache['step'])
                actual = height(new_bvh, x, -z)
                if actual is None:
                    actual = -15.
                    outside_domain += 1
                errors.append(abs(value - actual))
        report['height_cache_samples'] = len(errors)
        report['height_cache_max_error'] = max(errors) if errors else None
        report['height_cache'] = {
            'expected_values': rows * columns, 'actual_values': len(cache['heights']),
            'missing_sampled_values': missing_cache_values, 'nonfinite_sampled_values': nonfinite,
            'outside_mesh_fallback_samples': outside_domain,
            'errors_over_1mm': sum(error > .001 for error in errors),
        }
        checkpoint('sparse_height_cache')
        report['geometry_checks_pass'] = not any((
            report['boundary_index_edges_added'], report['boundary_index_edges_removed'],
            len(new_components) != len(old_components), report['boundary_noncycle_components'], nonmanifold,
            len(negative), len(degenerate), report['missing_required_building_floors'],
            len(support) != len(floors),
            any(item['missing_ground_hits'] or item['samples'] != 8 for item in support.values()),
            cargo_misses, missing_cargo, len(cargo) != 235, report['cargo_penetration_samples'],
            rows * columns != len(cache['heights']), missing_cache_values, nonfinite,
            not errors, any(error > .001 for error in errors), bool(bpy.data.is_dirty) != dirty_before,
        ))
        report['status'] = 'completed'
        report['elapsed_seconds'] = round(time.perf_counter() - started, 3)
        report['dirty_after'] = bool(bpy.data.is_dirty)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
        print(json.dumps({key: report[key] for key in (
            'status', 'elapsed_seconds', 'geometry_checks_pass', 'triangles',
            'boundary_index_edges_added', 'boundary_index_edges_removed', 'boundary_coordinate_edges_added',
            'building_floor_count', 'negative_triangle_count', 'degenerate_triangle_count',
            'cargo_samples', 'cargo_min_clearance', 'height_cache_samples', 'height_cache_max_error',
        )}, ensure_ascii=False), flush=True)
    except Exception as exc:
        report['status'] = 'failed'
        report['error'] = type(exc).__name__ + ': ' + str(exc)
        report['elapsed_seconds'] = round(time.perf_counter() - started, 3)
        report['dirty_after'] = bool(bpy.data.is_dirty)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
        raise


audit_core_rock21()
