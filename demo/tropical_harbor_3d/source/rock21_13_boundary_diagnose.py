"""Read-only boundary diagnosis; no scene update, mutation, export, or save."""
import bpy
import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np


def diagnose_boundary_rock21():
    begun = time.perf_counter()
    log = Path(bpy.data.filepath).parent.parent / 'captures/rock_earth_rebuild_20261121'
    obj = bpy.data.objects['C25_ContourBuiltCoast']
    mesh = obj.data
    dirty = bool(bpy.data.is_dirty)
    matrix = np.asarray(obj.matrix_world, dtype=np.float64)
    coordinates = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get('co', coordinates)
    new_p = coordinates.reshape((-1, 3)).astype(np.float64)
    loops = np.empty(len(mesh.loops), dtype=np.int32)
    starts = np.empty(len(mesh.polygons), dtype=np.int32)
    sizes = np.empty(len(mesh.polygons), dtype=np.int32)
    mesh.loops.foreach_get('vertex_index', loops)
    mesh.polygons.foreach_get('loop_start', starts)
    mesh.polygons.foreach_get('loop_total', sizes)
    with np.load(str(log / 'terrain_before.npz')) as raw:
        old_p = np.asarray(raw['positions'], dtype=np.float64)
        old_l, old_s, old_n = raw['loops'].copy(), raw['starts'].copy(), raw['sizes'].copy()
    old_p = old_p @ matrix[:3, :3].T + matrix[:3, 3]
    new_p = new_p @ matrix[:3, :3].T + matrix[:3, 3]

    def get_boundary(indices, first, count):
        following = np.roll(indices, -1)
        following[first + count - 1] = indices[first]
        edges = np.sort(np.column_stack((indices, following)), axis=1)
        unique, counts = np.unique(edges, axis=0, return_counts=True)
        return {tuple(map(int, e)) for e in unique[counts == 1]}, int(np.count_nonzero(counts > 2))

    def p_record(p):
        return {'x': round(float(p[0]), 9), 'z': round(float(-p[1]), 9), 'height': round(float(p[2]), 9)}

    def geo_key(edge, pts):
        return tuple(sorted(tuple(np.round(pts[i], 5)) for i in edge))

    def ring_info(edges, pts):
        adjacency = defaultdict(list)
        for a, b in edges:
            adjacency[a].append(b)
            adjacency[b].append(a)
        unseen = set(adjacency)
        rings, owner, polygons, signatures = [], {}, [], []
        while unseen:
            pending, vertices = [min(unseen)], set()
            while pending:
                vertex = pending.pop()
                if vertex in vertices:
                    continue
                vertices.add(vertex)
                pending.extend(n for n in adjacency[vertex] if n not in vertices)
            unseen -= vertices
            component_edges = {e for e in edges if e[0] in vertices}
            closed = all(len(adjacency[v]) == 2 for v in vertices)
            ordered = []
            if closed:
                previous, current = None, min(vertices)
                for _ in range(len(vertices)):
                    ordered.append(current)
                    following = next(v for v in adjacency[current] if v != previous)
                    previous, current = current, following
                closed = current == ordered[0] and len(set(ordered)) == len(vertices)
            coordinates = pts[sorted(vertices)]
            planar = pts[ordered][:, [0, 1]] if closed else np.empty((0, 2))
            area = float(abs(np.sum(planar[:, 0] * np.roll(planar[:, 1], -1) -
                                    planar[:, 1] * np.roll(planar[:, 0], -1))) / 2) if closed else None
            rid = len(rings)
            rings.append({'component': rid, 'vertices': len(vertices), 'edges': len(component_edges),
                          'closed_simple_degree_two_cycle': closed,
                          'degree_counts': dict(Counter(len(adjacency[v]) for v in vertices)),
                          'projected_area': area,
                          'min_xyz_blender': coordinates.min(axis=0).tolist(),
                          'max_xyz_blender': coordinates.max(axis=0).tolist()})
            polygons.append(planar)
            signatures.append(frozenset(component_edges))
            owner.update({e: rid for e in component_edges})
        outer = max(range(len(rings)), key=lambda i: rings[i]['projected_area'] or 0) if rings else None

        def inside(point, polygon):
            x, y = point
            value = False
            for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
                if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
                    value = not value
            return value

        for i, ring in enumerate(rings):
            ring['largest_projected_outer_cycle'] = i == outer
            ring['inside_largest_outer_cycle'] = bool(
                i != outer and len(polygons[i]) and len(polygons[outer]) and
                inside(polygons[i][0], polygons[outer]))
        return rings, owner, signatures

    old_edges, old_nonmanifold = get_boundary(old_l, old_s, old_n)
    new_edges, new_nonmanifold = get_boundary(loops, starts, sizes)
    old_keys = {geo_key(e, old_p) for e in old_edges}
    new_keys = {geo_key(e, new_p) for e in new_edges}
    old_rings, old_owner, old_signatures = ring_info(old_edges, old_p)
    new_rings, new_owner, new_signatures = ring_info(new_edges, new_p)

    def describe(edge, points, owner, other_edges, other_points):
        item = {'vertex_ids': list(edge), 'component': owner[edge],
                'endpoints': [p_record(points[i]) for i in edge],
                'same_index_edge_in_other_mesh': edge in other_edges}
        if edge in other_edges:
            deltas = [points[i] - other_points[i] for i in edge]
            item['other_endpoints_same_vertex_ids'] = [p_record(other_points[i]) for i in edge]
            item['endpoint_displacements_xyz_blender'] = [p.tolist() for p in deltas]
            item['max_endpoint_displacement_m'] = max(float(np.linalg.norm(p)) for p in deltas)
        return item

    added = [describe(e, new_p, new_owner, old_edges, old_p) for e in sorted(new_edges)
             if geo_key(e, new_p) not in old_keys]
    removed = [describe(e, old_p, old_owner, new_edges, new_p) for e in sorted(old_edges)
               if geo_key(e, old_p) not in new_keys]
    added_index, removed_index = new_edges - old_edges, old_edges - new_edges
    unchanged_graph = not added_index and not removed_index
    report = {
        'source': bpy.data.filepath, 'pid': os.getpid(), 'elapsed_seconds': round(time.perf_counter()-begun, 3),
        'dirty_before': dirty, 'dirty_after': bool(bpy.data.is_dirty),
        'boundary_edges_old': len(old_edges), 'boundary_edges_new': len(new_edges),
        'coordinate_set_added_count': len(added), 'coordinate_set_removed_count': len(removed),
        'coordinate_set_added': added, 'coordinate_set_removed': removed,
        'index_set_added': [list(e) for e in sorted(added_index)],
        'index_set_removed': [list(e) for e in sorted(removed_index)],
        'old_boundary_components': old_rings, 'new_boundary_components': new_rings,
        'new_component_ids_with_no_identical_baseline_edge_graph': [
            i for i, signature in enumerate(new_signatures) if signature not in old_signatures],
        'old_nonmanifold_edges': old_nonmanifold, 'new_nonmanifold_edges': new_nonmanifold,
        'boundary_index_graph_unchanged': unchanged_graph,
        'interpretation': (
            'Coordinate differences only: all one-face edges and boundary cycles retain the same vertex IDs. '
            'Under the index-preserving rebuild/repair construction, these differences do not establish a new hole.'
            if unchanged_graph else
            'Boundary incidence changed. Inspect new components/edge endpoints; equal total edge counts alone do not rule out a hole.'),
        'internal_hole_evidence': (
            'A new closed boundary cycle inside the outer cycle, absent from the baseline, indicates a new hole. '
            'A same-graph cycle with shifted coordinates is an existing boundary, not a newly opened hole. '
            'This payload does not test overlap/self-intersection or infer visual acceptance.'),
        'identity_assumption': 'rock21_04/11/11b retain the baseline vertex index prefix; if later operations renumber vertices, compare spatially instead.',
    }
    (log / 'boundary_diagnose.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
    print(json.dumps(report, ensure_ascii=False), flush=True)


diagnose_boundary_rock21()
