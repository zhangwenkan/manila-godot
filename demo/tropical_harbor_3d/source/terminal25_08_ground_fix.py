"""Local core-footprint subdivision; default is array-only dry run.

Owned Blender MCP only. Set TN25_GROUND_FIX_APPLY=True explicitly to apply a
previous successful dry-run plan. No save or export is performed here.
Current-round terrain_before.npz is the sole reference geometry. This file
never imports any old terminal asset or replays a construction script.
"""

import hashlib
import json
import os
from pathlib import Path

import numpy as np

CORE = (-.03, 2.93, 23.57, 26.98)
CEILING = 1.63


def geometry_hash(p, tri):
    return hashlib.sha256(np.asarray(p, np.float32).tobytes() + np.asarray(tri, np.int32).ravel().tobytes()).hexdigest()


def barycentric(xy, triangle):
    e, f = triangle[1, :2] - triangle[0, :2], triangle[2, :2] - triangle[0, :2]
    r = np.asarray(xy) - triangle[0, :2]
    determinant = e[0] * f[1] - e[1] * f[0]
    a = (r[..., 0] * f[1] - r[..., 1] * f[0]) / determinant
    b = (e[0] * r[..., 1] - e[1] * r[..., 0]) / determinant
    return np.stack([1 - a - b, a, b], axis=-1)


def clip_polygon(poly, axis, value, sign):
    result = []
    if not poly:
        return result
    for a, b in zip(poly, poly[1:] + poly[:1]):
        da, db = sign * (a[axis] - value), sign * (b[axis] - value)
        inside_a, inside_b = da >= -1e-10, db >= -1e-10
        if inside_a:
            result.append(a)
        if inside_a != inside_b:
            result.append(a + (b - a) * da / (da - db))
    cleaned = []
    for p in result:
        if not cleaned or np.linalg.norm(p[:2] - cleaned[-1][:2]) > 1e-8:
            cleaned.append(p)
    if len(cleaned) > 1 and np.linalg.norm(cleaned[0][:2] - cleaned[-1][:2]) < 1e-8:
        cleaned.pop()
    return cleaned


def area(poly):
    if len(poly) < 3:
        return 0.0
    return .5 * abs(sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(poly, poly[1:] + poly[:1])))


def edges_report(tri):
    es = np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
    unique, counts = np.unique(es, axis=0, return_counts=True)
    return unique[counts == 1], int(np.count_nonzero(counts > 2))


def build_local_cut(p0_input, tri_input):
    """Pure NumPy plan. Shared cut points and centroid fans retain all edge nodes."""
    p0 = np.asarray(p0_input, np.float32)
    original = p0.astype(np.float64)
    tri0 = np.asarray(tri_input, np.int32)
    points = [v.copy() for v in original]
    point_faces, point_weights = [], []
    # Original points use their exact indices; appended shared intersections use
    # rounded XY keys. All geometry ultimately uses Blender float32 coordinates.
    keys = {(round(float(v[0]), 6), round(float(v[1]), 6)): i for i, v in enumerate(points)}
    cut_polys = {}
    cut_faces = []
    planes = [(0, CORE[0], 1), (0, CORE[1], -1), (1, CORE[2], 1), (1, CORE[3], -1)]

    def add_point(xy, source_face, merge=True):
        xy = np.asarray(xy, np.float32).astype(float)
        key = (round(float(xy[0]), 6), round(float(xy[1]), 6))
        if merge and key in keys:
            return keys[key]
        weights = barycentric(xy, original[tri0[source_face]])
        z = float(weights @ original[tri0[source_face], 2])
        index = len(points)
        points.append(np.array([xy[0], xy[1], z]))
        point_faces.append(int(source_face))
        point_weights.append(weights)
        if merge:
            keys[key] = index
        return index

    t = original[tri0]
    lo, hi = t[:, :, :2].min(1), t[:, :, :2].max(1)
    candidates = np.flatnonzero((lo[:, 0] < CORE[1]) & (hi[:, 0] > CORE[0]) &
                               (lo[:, 1] < CORE[3]) & (hi[:, 1] > CORE[2]))
    for face in candidates:
        original_poly = [v.copy() for v in t[face, :, :2]]
        inside = original_poly
        pieces = []
        for axis, value, sign in planes:
            outside = clip_polygon(inside, axis, value, -sign)
            if area(outside) > 1e-9:
                pieces.append(outside)
            inside = clip_polygon(inside, axis, value, sign)
        if area(inside) <= 1e-9:
            continue
        pieces.append(inside)
        cut_faces.append(int(face))
        cut_polys[int(face)] = [[add_point(q, int(face)) for q in poly] for poly in pieces]

    n_original = len(p0)
    shared_indices = np.arange(n_original, len(points), dtype=np.int32)
    shared_xy = np.asarray(points)[shared_indices, :2]
    # Propagate every new point along any incident original or clipped edge.
    # Only faces in this small envelope can have such an edge.
    affected = set(cut_polys)
    if len(shared_xy):
        nl, nh = shared_xy.min(0), shared_xy.max(0)
        neighbors = np.flatnonzero((lo[:, 0] <= nh[0] + 1e-6) & (hi[:, 0] >= nl[0] - 1e-6) &
                                   (lo[:, 1] <= nh[1] + 1e-6) & (hi[:, 1] >= nl[1] - 1e-6))
    else:
        neighbors = []
    expanded = {}
    for face in sorted(set(neighbors) | affected):
        source_polys = cut_polys.get(int(face), [tri0[face].tolist()])
        output_polys, any_insert = [], False
        for poly in source_polys:
            full = []
            for a, b in zip(poly, poly[1:] + poly[:1]):
                full.append(a)
                pa, pb = points[a][:2], points[b][:2]
                edge = pb - pa
                length2 = float(edge @ edge)
                assert length2 > 1e-14, ("zero clipped edge", int(face), a, b)
                if len(shared_xy):
                    delta = shared_xy - pa
                    along = (delta @ edge) / length2
                    cross = np.abs(delta[:, 0] * edge[1] - delta[:, 1] * edge[0])
                    selected = np.flatnonzero((along > 1e-6) & (along < 1 - 1e-6) &
                                               (cross < 7e-7 * math_sqrt(length2)))
                    selected = sorted(selected, key=lambda k: along[k])
                    for k in selected:
                        n = int(shared_indices[k])
                        if n not in (a, b) and (not full or n != full[-1]):
                            full.append(n)
                            any_insert = True
            cleaned = []
            for i in full:
                if not cleaned or i != cleaned[-1]:
                    cleaned.append(i)
            if len(cleaned) > 1 and cleaned[0] == cleaned[-1]:
                cleaned.pop()
            output_polys.append(cleaned)
        if int(face) in cut_polys or any_insert:
            expanded[int(face)] = output_polys

    new_triangles, sources, changed_faces = [], [], []
    for face, old_tri in enumerate(tri0):
        polys = expanded.get(face)
        if polys is None or (len(polys) == 1 and len(polys[0]) == 3 and set(polys[0]) == set(old_tri)):
            new_triangles.append(old_tri.tolist())
            sources.append(face)
            continue
        changed_faces.append(face)
        for poly in polys:
            # A centroid is strictly interior to a positive-area convex polygon;
            # every boundary edge segment gets its own nondegenerate triangle.
            center = np.mean([points[i][:2] for i in poly], axis=0)
            ci = add_point(center, face, merge=False)
            for a, b in zip(poly, poly[1:] + poly[:1]):
                cross = np.cross(points[b][:2] - points[a][:2], points[ci][:2] - points[a][:2])
                if cross < 0:
                    a, b = b, a
                new_triangles.append([a, b, ci])
                sources.append(face)

    p = np.asarray(points, np.float32)
    core = ((p[:, 0] >= CORE[0] - 2e-6) & (p[:, 0] <= CORE[1] + 2e-6) &
            (p[:, 1] >= CORE[2] - 2e-6) & (p[:, 1] <= CORE[3] + 2e-6))
    p[core, 2] = np.minimum(p[core, 2], CEILING)
    tri = np.asarray(new_triangles, np.int32)
    sources = np.asarray(sources, np.int32)
    boundary0, nm0 = edges_report(tri0)
    boundary, nm = edges_report(tri)
    v = p[tri].astype(float)
    cross = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    area0 = np.abs(np.cross(original[tri0[:, 1], :2] - original[tri0[:, 0], :2], original[tri0[:, 2], :2] - original[tri0[:, 0], :2])) * .5
    area1 = np.bincount(sources, weights=np.abs(cross[:, 2]) * .5, minlength=len(tri0))
    changed_original = np.flatnonzero(np.abs(p[:n_original, 2] - p0[:, 2]) > 1e-7)
    report = {
        "core_blender_xy": list(CORE), "ceiling_m": CEILING,
        "before_vertices": len(p0), "before_triangles": len(tri0),
        "after_vertices": len(p), "after_triangles": len(tri),
        "added_vertices": len(p) - len(p0), "added_triangles": len(tri) - len(tri0),
        "positive_area_core_faces": cut_faces, "subdivided_source_faces": changed_faces,
        "shared_intersection_vertices": len(shared_indices),
        "changed_original_vertex_ids": changed_original.tolist(),
        "max_original_lowering_m": float(np.max(p0[:, 2] - p[:n_original, 2])),
        "original_xy_unchanged": bool(np.array_equal(p[:n_original, :2], p0[:, :2])),
        "outside_original_vertices_restored": bool(np.array_equal(p[:n_original][~core[:n_original]], p0[~core[:n_original]])),
        "boundary_edges_before": len(boundary0), "boundary_edges_after": len(boundary),
        "boundary_indices_unchanged": bool(np.array_equal(boundary, boundary0)),
        "boundary_coordinates_unchanged": bool(np.array_equal(p[np.unique(boundary0)], p0[np.unique(boundary0)])),
        "nonmanifold_edges": nm, "degenerate_triangles": int(np.count_nonzero(np.linalg.norm(cross, axis=1) < 1e-10)),
        "downward_triangles": int(np.count_nonzero(cross[:, 2] <= 1e-10)),
        "maximum_source_face_area_error": float(np.max(np.abs(area1 - area0))),
        "terrain_before_sha256": geometry_hash(p0, tri0), "terrain_after_sha256": geometry_hash(p, tri),
    }
    report["passed"] = all([report["original_xy_unchanged"], report["outside_original_vertices_restored"],
                             report["boundary_indices_unchanged"], report["boundary_coordinates_unchanged"],
                             len(boundary) == len(boundary0) == 1020, nm == nm0 == 0,
                             report["degenerate_triangles"] == report["downward_triangles"] == 0,
                             report["maximum_source_face_area_error"] < 2e-5])
    return p, tri, sources, np.asarray(point_faces, np.int32), np.asarray(point_weights, np.float64), report


def math_sqrt(value):
    return float(np.sqrt(value))


def main(apply=False):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    root = Path(bpy.data.filepath).parent.parent
    log = root / "captures/terminal_rebuild_20261125"
    session = json.loads((log / "session_start.json").read_text(encoding="utf8"))
    assert os.getpid() == session["pid"] and not bpy.app.background
    assert bpy.types.blendermcp_server.port == session["port"]
    assert Path(bpy.data.filepath).resolve() == Path(session["source"]).resolve()
    assert not (log / "ground_fix.json").exists(), "Ground fix already applied; inspect instead of replay"
    ob = bpy.data.objects["C25_ContourBuiltCoast"]
    mesh = ob.data
    before = np.load(log / "terrain_before.npz")
    p0, tri0 = before["positions"], before["triangles"]
    current = np.empty((len(mesh.vertices), 3), np.float32)
    mesh.vertices.foreach_get("co", current.ravel())
    loops = np.empty(len(mesh.loops), np.int32)
    mesh.loops.foreach_get("vertex_index", loops)
    assert current.shape == p0.shape and np.array_equal(loops.reshape(-1, 3), tri0)
    assert np.array_equal(current[:, :2], p0[:, :2])
    assert np.max(np.abs(np.asarray(ob.matrix_world) - np.eye(4))) < 1e-7
    assert not ob.vertex_groups, "Unexpected terrain vertex groups need explicit remapping"
    p, tri, sources, new_faces, new_weights, report = build_local_cut(p0, tri0)
    if apply:
        dryrun_path = log / "ground_fix_dryrun.json"
        assert dryrun_path.exists(), "Run default dry-run before explicit apply"
        approved = json.loads(dryrun_path.read_text(encoding="utf8"))
        assert approved.get("passed") and approved.get("terrain_after_sha256") == report["terrain_after_sha256"], "Dry-run plan is missing, failed, or differs"
        assert approved.get("current_pre_fix_sha256") == geometry_hash(current, tri0), "Live pre-fix terrain changed since dry-run"
    report["status"] = "dry_run"
    report["current_pre_fix_sha256"] = geometry_hash(current, tri0)
    report["restored_prior_site_vertices"] = np.flatnonzero((np.abs(current[:, 2] - p0[:, 2]) > 1e-7) & (np.abs(p[:len(p0), 2] - p0[:, 2]) <= 1e-7)).tolist()

    # Prepare all data layer mappings before any scene mutation.
    attr_data, unsupported, edge_data = [], [], []
    uv_names = {uv.name for uv in mesh.uv_layers}
    descriptors = {"FLOAT": ("value", 1, np.float32), "INT": ("value", 1, np.int32),
                   "BOOLEAN": ("value", 1, np.bool_), "FLOAT_VECTOR": ("vector", 3, np.float32),
                   "FLOAT_COLOR": ("color", 4, np.float32), "BYTE_COLOR": ("color", 4, np.float32),
                   "FLOAT2": ("vector", 2, np.float32)}
    # Per-loop barycentrics use their original source triangle, preserving seams.
    corner_weights = np.tile(np.eye(3), (len(tri), 1, 1))
    for face in report["subdivided_source_faces"]:
        lo, hi = np.searchsorted(sources, [face, face + 1])
        corner_weights[lo:hi] = barycentric(p[tri[lo:hi], :2], p0[tri0[face]].astype(float))

    def remap(values, domain, integer=False):
        if domain == "POINT":
            additions = values[tri0[new_faces]]
            added = additions[np.arange(len(additions)), np.argmax(new_weights, axis=1)] if integer else np.einsum("ij,ijk->ik", new_weights, additions)
            return np.concatenate([values, added])
        if domain == "FACE":
            return values[sources]
        if domain == "CORNER":
            base = values.reshape(len(tri0), 3, -1)[sources]
            if integer:
                mapped = np.take_along_axis(base[:, None, :, :], np.argmax(corner_weights, axis=2)[:, :, None, None], axis=2)[:, :, 0, :]
            else:
                mapped = np.einsum("tij,tjk->tik", corner_weights, base)
            return mapped.reshape(-1, values.shape[1])
        raise ValueError(domain)

    for attr in mesh.attributes:
        if attr.name in uv_names or attr.name.startswith(".") or attr.name == "position" or getattr(attr, "is_internal", False):
            continue
        if attr.name == "sharp_edge" and attr.domain == "EDGE" and attr.data_type == "BOOLEAN":
            old_flags = np.empty(len(attr.data), np.bool_)
            attr.data.foreach_get("value", old_flags)
            old_edges = np.empty((len(mesh.edges), 2), np.int32)
            mesh.edges.foreach_get("vertices", old_edges.ravel())
            old_flags_by_pair = {tuple(sorted(pair)): bool(flag) for pair, flag in zip(old_edges, old_flags)}
            new_edges = np.unique(np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1), axis=0)
            sharp_pairs = set()
            for a, b in new_edges:
                pair = (int(a), int(b))
                if pair in old_flags_by_pair:
                    if old_flags_by_pair[pair]:
                        sharp_pairs.add(pair)
                    continue
                candidates = set()
                for vi in (a, b):
                    if vi >= len(p0):
                        original_tri = tri0[new_faces[vi - len(p0)]]
                        for i, j in ((0, 1), (1, 2), (2, 0)):
                            candidates.add(tuple(sorted((int(original_tri[i]), int(original_tri[j])))))
                for va, vb in candidates:
                    if not old_flags_by_pair.get((va, vb), False):
                        continue
                    first, last = p0[va, :2].astype(float), p0[vb, :2].astype(float)
                    delta = last - first
                    length2 = float(delta @ delta)
                    q = p[[a, b], :2].astype(float) - first
                    u = q @ delta / length2
                    distance = np.abs(q[:, 0] * delta[1] - q[:, 1] * delta[0]) / np.sqrt(length2)
                    if np.all(distance <= 1.2e-6) and np.all(u >= -1e-6) and np.all(u <= 1 + 1e-6):
                        sharp_pairs.add(pair)
                        break
            edge_data.append((attr.name, sharp_pairs))
            report["sharp_edge_mapping"] = {"old_true_count": int(np.count_nonzero(old_flags)), "new_true_count": len(sharp_pairs), "policy": "Unchanged edges preserve flags; split original-edge segments inherit flags; newly interior edges false."}
            continue
        if attr.data_type not in descriptors or attr.domain not in {"POINT", "FACE", "CORNER"}:
            unsupported.append([attr.name, attr.domain, attr.data_type])
            continue
        field, width, dtype = descriptors[attr.data_type]
        values = np.empty((len(attr.data), width), dtype)
        attr.data.foreach_get(field, values.ravel())
        mapped = remap(values, attr.domain, np.issubdtype(dtype, np.integer) or dtype == np.bool_).astype(dtype)
        attr_data.append((attr.name, attr.data_type, attr.domain, field, mapped))
    uv_data = []
    for uv in mesh.uv_layers:
        values = np.empty((len(uv.data), 2), np.float32)
        uv.data.foreach_get("uv", values.ravel())
        uv_data.append((uv.name, remap(values, "CORNER").astype(np.float32), uv.active_render))
    report["unsupported_attributes"] = unsupported
    report["attribute_mapping"] = [{"name": name, "type": kind, "domain": domain, "elements": len(a)} for name, kind, domain, field, a in attr_data]
    land = mesh.color_attributes.get("LandUse")
    if land is not None:
        colors = np.array([v.color[:] for v in land.data])
        ids = np.asarray(report["changed_original_vertex_ids"], np.int32)
        if land.domain == "POINT":
            report["old_landuse_at_changed_vertices"] = [{"vertex": int(i), "grass_rock_path_soil": colors[i].tolist()} for i in ids]
        report["landuse_domain"] = land.domain
    locks_path = root / "captures/cliff_contacts_20261125/protected_terrain_faces.npz"
    if locks_path.exists():
        locks = np.load(locks_path)
        report["old_road_court_locked_vertices_changed"] = sorted(set(report["changed_original_vertex_ids"]) & set(locks["vertex_ids"].tolist()))
    report["passed"] = report["passed"] and not unsupported and not report.get("old_road_court_locked_vertices_changed", [])

    bvh = BVHTree.FromPolygons(p.tolist(), tri.tolist(), all_triangles=True)
    foundations = []
    for part in bpy.data.collections["Reference_Terminal"].objects:
        if part.type != "MESH" or not ("GroundStone" in part.name or part.name.startswith(("TN25_PorchFoundation", "TN25_WorkDeckPier"))):
            continue
        ps = np.asarray([(part.matrix_world @ Vector(v))[:] for v in part.bound_box])
        low, high = ps.min(0), ps.max(0)
        heights = []
        for x in np.linspace(low[0], high[0], 9):
            for y in np.linspace(low[1], high[1], 9):
                hit = bvh.ray_cast(Vector((float(x), float(y), 40)), Vector((0, 0, -1)), 160)[0]
                assert hit is not None, (part.name, x, y)
                heights.append(float(hit.z))
        new_bottom = min(float(low[2]), min(heights) - .12)
        foundations.append({"name": part.name, "samples": 81, "before_bottom": float(low[2]), "after_bottom": new_bottom,
                            "top": float(high[2]), "extension_m": float(low[2]) - new_bottom,
                            "minimum_ground": min(heights), "maximum_ground": max(heights)})
    report["foundations"] = foundations
    report["foundation_extended_count"] = sum(r["extension_m"] > 1e-6 for r in foundations)

    # Terrain-vs-tread samples distinguish visible deck from a ground intrusion.
    treads = []
    for step in bpy.data.collections["Reference_Terminal"].objects:
        if not step.name.startswith("TN25_WideEntryStep"):
            continue
        ps = np.asarray([(step.matrix_world @ Vector(v))[:] for v in step.bound_box])
        low, high = ps.min(0), ps.max(0)
        violations = []
        minimum = 1e9
        for x in np.linspace(low[0] + .025, high[0] - .025, 9):
            for y in np.linspace(low[1] + .025, high[1] - .025, 5):
                hit = bvh.ray_cast(Vector((float(x), float(y), 40)), Vector((0, 0, -1)), 160)[0]
                assert hit is not None
                clearance = float(high[2] - hit.z)
                minimum = min(minimum, clearance)
                if clearance < .025:
                    violations.append([float(x), float(y), float(hit.z), clearance])
        treads.append({"name": step.name, "top": float(high[2]), "minimum_ground_clearance": minimum, "bad_samples": violations})
    report["tread_ground_samples"] = treads
    report["tread_intrusion_count"] = sum(bool(row["bad_samples"]) for row in treads)
    # Tread findings are surfaced separately; this fix is deliberately confined to
    # the small tower footprint and foundation extensions, with no stair regrade.
    np.savez_compressed(log / "ground_fix_dryrun.npz", positions=p, triangles=tri, source_faces=sources,
                        new_point_faces=new_faces, new_point_weights=new_weights)
    (log / "ground_fix_dryrun.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    if not apply:
        print(json.dumps({"status": "dry_run", "passed": report["passed"], "before_vertices": len(p0), "after_vertices": len(p),
                          "before_triangles": len(tri0), "after_triangles": len(tri), "foundation_extended_count": report["foundation_extended_count"],
                          "tread_intrusion_count": report["tread_intrusion_count"], "report": str(log / "ground_fix_dryrun.json")}))
        return
    assert report["passed"], "Dry-run geometry/attributes/old-road protection checks failed; no scene changes applied"

    # Save an exact repair boundary before the single object-data replacement.
    np.savez_compressed(log / "ground_fix_before.npz", positions=current, triangles=tri0)
    new_mesh = bpy.data.meshes.new(mesh.name + "_TN25LocalCut")
    new_mesh.from_pydata(p.tolist(), [], tri.tolist())
    for material in mesh.materials:
        new_mesh.materials.append(material)
    indices = np.array([f.material_index for f in mesh.polygons], np.int32)[sources]
    smooth = np.array([f.use_smooth for f in mesh.polygons], bool)[sources]
    new_mesh.polygons.foreach_set("material_index", indices)
    new_mesh.polygons.foreach_set("use_smooth", smooth)
    for name, kind, domain, field, mapped in attr_data:
        a = new_mesh.attributes.new(name=name, type=kind, domain=domain)
        a.data.foreach_set(field, mapped.ravel())
    for name, sharp_pairs in edge_data:
        a = new_mesh.attributes.get(name) or new_mesh.attributes.new(name=name, type="BOOLEAN", domain="EDGE")
        actual_edges = np.empty((len(new_mesh.edges), 2), np.int32)
        new_mesh.edges.foreach_get("vertices", actual_edges.ravel())
        flags = np.array([tuple(sorted(pair)) in sharp_pairs for pair in actual_edges], np.bool_)
        a.data.foreach_set("value", flags)
    for name, mapped, render in uv_data:
        a = new_mesh.uv_layers.new(name=name)
        a.data.foreach_set("uv", mapped.ravel())
        a.active_render = render
    if mesh.uv_layers.active:
        new_mesh.uv_layers.active_index = next(i for i, uv in enumerate(new_mesh.uv_layers) if uv.name == mesh.uv_layers.active.name)
    for key in mesh.keys():
        new_mesh[key] = mesh[key]
    new_mesh.update()
    mesh.use_fake_user = True
    ob.data = new_mesh
    for record in foundations:
        if record["extension_m"] <= 1e-6:
            continue
        part = bpy.data.objects[record["name"]]
        inv = part.matrix_world.inverted()
        old_bottom, top, new_bottom = record["before_bottom"], record["top"], record["after_bottom"]
        for vertex in part.data.vertices:
            world = part.matrix_world @ vertex.co
            factor = (world.z - old_bottom) / (top - old_bottom)
            world.z = new_bottom + factor * (top - new_bottom)
            vertex.co = inv @ world
        part.data.update()
    bpy.context.view_layer.update()
    report["status"] = "applied"
    report["prior_mesh_datablock_retained"] = mesh.name
    np.savez_compressed(log / "terrain_after.npz", positions=p, triangles=tri)
    (log / "ground_fix.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    print(json.dumps({"status": "applied", "terrain_after_sha256": report["terrain_after_sha256"],
                      "vertices": len(p), "triangles": len(tri), "report": str(log / "ground_fix.json")}))


if globals().get("TN25_GROUND_FIX_RUN", True):
    main(bool(globals().get("TN25_GROUND_FIX_APPLY", False)))
