"""Read-only GLB geometry audit. Never opens Blender or Godot.

Writes its own evidence JSON. The route equations mirror the unchanged current
harbor_route.gd; calculations use float64, unlike Godot's ordinary Vector3.
"""
from pathlib import Path
import hashlib
import json
import math
import struct
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "demo/tropical_harbor_3d/assets/reference"
OUT = ROOT / "demo/tropical_harbor_3d/captures/lighthouse_integration_20261126"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def glb_triangles(path):
    raw = path.read_bytes()
    length, kind = struct.unpack_from("<II", raw, 12)
    assert kind == 0x4E4F534A
    doc = json.loads(raw[20:20 + length])
    size, kind = struct.unpack_from("<II", raw, 20 + length)
    assert kind == 0x004E4942
    binary = raw[28 + length:28 + length + size]

    def accessor(index):
        a = doc["accessors"][index]
        assert "sparse" not in a
        view = doc["bufferViews"][a["bufferView"]]
        count = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
        dtype = {5126: "<f4", 5123: "<u2", 5125: "<u4", 5121: "u1"}[a["componentType"]]
        stride = np.dtype(dtype).itemsize
        return np.ndarray((a["count"], count), dtype=dtype, buffer=binary,
                          offset=view.get("byteOffset", 0) + a.get("byteOffset", 0),
                          strides=(view.get("byteStride", count * stride), stride)).copy()

    def local_matrix(node):
        if "matrix" in node:
            return np.asarray(node["matrix"], float).reshape(4, 4).T
        x, y, z, w = node.get("rotation", [0, 0, 0, 1])
        rotation = np.array([[1 - 2*y*y - 2*z*z, 2*x*y - 2*z*w, 2*x*z + 2*y*w],
                             [2*x*y + 2*z*w, 1 - 2*x*x - 2*z*z, 2*y*z - 2*x*w],
                             [2*x*z - 2*y*w, 2*y*z + 2*x*w, 1 - 2*x*x - 2*y*y]])
        result = np.eye(4)
        result[:3, :3] = rotation @ np.diag(node.get("scale", [1, 1, 1]))
        result[:3, 3] = node.get("translation", [0, 0, 0])
        return result

    triangles, names = [], []

    def visit(index, parent):
        node = doc["nodes"][index]
        matrix = parent @ local_matrix(node)
        if "mesh" in node:
            for primitive in doc["meshes"][node["mesh"]]["primitives"]:
                assert primitive.get("mode", 4) == 4
                vertices = accessor(primitive["attributes"]["POSITION"])
                vertices = vertices @ matrix[:3, :3].T + matrix[:3, 3]
                indices = accessor(primitive["indices"]).reshape(-1, 3)
                tri = vertices[indices]
                triangles.append(tri)
                names.extend([node.get("name", str(index))] * len(tri))
        for child in node.get("children", []):
            visit(child, matrix)

    for index in doc["scenes"][doc.get("scene", 0)]["nodes"]:
        visit(index, np.eye(4))
    return np.concatenate(triangles), np.asarray(names)


def clip_below(triangles, names, ceiling):
    """Clip actual triangles at Y=ceiling, including all underwater geometry."""
    full = triangles[:, :, 1].max(axis=1) <= ceiling
    crossing = (triangles[:, :, 1].min(axis=1) <= ceiling) & ~full
    output = [triangles[full]]
    labels = [names[full]]
    for tri, name in zip(triangles[crossing], names[crossing]):
        polygon = []
        for i in range(3):
            a, b = tri[i], tri[(i + 1) % 3]
            ai, bi = a[1] <= ceiling, b[1] <= ceiling
            if ai:
                polygon.append(a)
            if ai != bi:
                polygon.append(a + (b - a) * ((ceiling - a[1]) / (b[1] - a[1])))
        for i in range(1, len(polygon) - 1):
            output.append(np.array([[polygon[0], polygon[i], polygon[i + 1]]]))
            labels.append(np.array([name]))
    return np.concatenate(output), np.concatenate(labels)


def cross(a, b):
    return a[..., 0]*b[..., 1] - a[..., 1]*b[..., 0]


def hull(points):
    ordered = sorted(set(map(tuple, points)))
    def build(items):
        result = []
        for point in items:
            while len(result) >= 2 and cross(np.subtract(result[-1], result[-2]), np.subtract(point, result[-1])) <= 1e-12:
                result.pop()
            result.append(point)
        return result
    return np.asarray(build(ordered)[:-1] + build(ordered[::-1])[:-1])


def point_segment_squared(point, a, b):
    edge = b - a
    length = np.sum(edge*edge, axis=-1)
    numerator = np.sum((point - a)*edge, axis=-1)
    ratio = np.divide(numerator, length, out=np.zeros_like(numerator), where=length > 1e-24)
    closest = a + np.clip(ratio, 0, 1)[..., None]*edge
    return np.sum((closest - point)**2, axis=-1)


def polygon_triangle_squared(polygon, triangles):
    """Exact projected distance from one convex polygon to each triangle."""
    count = len(triangles)
    distances = np.full(count, np.inf)
    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    denominator = cross(b - a, c - a)
    overlaps = np.zeros(count, bool)
    # Polygon vertices to triangle edges; polygon vertex within triangle.
    for point in polygon:
        u = np.divide(cross(point - a, c - a), denominator, out=np.full(count, np.nan), where=abs(denominator) > 1e-20)
        v = np.divide(cross(b - a, point - a), denominator, out=np.full(count, np.nan), where=abs(denominator) > 1e-20)
        overlaps |= (u >= 0) & (v >= 0) & (u + v <= 1)
        for i in range(3):
            distances = np.minimum(distances, point_segment_squared(point, triangles[:, i], triangles[:, (i + 1) % 3]))
    # Triangle vertices to polygon edges, including point-in-convex-polygon.
    sign_positive = np.ones((count, 3), bool)
    sign_negative = np.ones((count, 3), bool)
    for k in range(len(polygon)):
        p, q = polygon[k], polygon[(k + 1) % len(polygon)]
        area = cross(q - p, triangles - p)
        sign_positive &= area >= -1e-12
        sign_negative &= area <= 1e-12
        distances = np.minimum(distances, point_segment_squared(triangles, p, q).min(axis=1))
        for i in range(3):
            aa, bb = triangles[:, i], triangles[:, (i + 1) % 3]
            edge = bb - aa
            denom = cross(edge, q - p)
            t = np.divide(cross(p - aa, q - p), denom, out=np.full(count, np.nan), where=abs(denom) > 1e-20)
            u = np.divide(cross(p - aa, edge), denom, out=np.full(count, np.nan), where=abs(denom) > 1e-20)
            overlaps |= (t >= 0) & (t <= 1) & (u >= 0) & (u <= 1)
    if abs(sum(cross(polygon[k], polygon[(k + 1) % len(polygon)]) for k in range(len(polygon)))) > 1e-16:
        overlaps |= (sign_positive | sign_negative).any(axis=1)
    distances[overlaps] = 0
    return distances


def smooth(a, b, value):
    t = min(max((value - a)/(b - a), 0), 1)
    return t*t*(3 - 2*t)


def center(progress):
    clearance = 2.2*smooth(3, 5, progress)*(1 - smooth(10.5, 13, progress))
    return np.array([-28 + 25*smooth(0, 4.2, progress) - clearance,
                     76 - 6.45*progress + 4*(1 - smooth(3, 6, progress))])


def route_point(lane, progress):
    forward = center(progress + .01) - center(progress - .01)
    forward /= np.linalg.norm(forward)
    across = np.array([-forward[1], forward[0]])
    spacing = 4.4 + 3.6*math.exp(-((progress - 7.5)/1.8)**2)
    return center(progress) + across*((lane - 1)*spacing)


def boat_polygon(lane, progress):
    direction = route_point(lane, progress + .01) - route_point(lane, progress - .01)
    heading = math.atan2(-direction[0], -direction[1])
    cosine, sine = math.cos(heading), math.sin(heading)
    rotation = np.array([[cosine, sine], [-sine, cosine]])
    corners = np.array([[-1.05, -2.55], [1.05, -2.55], [1.05, 2.55], [-1.05, 2.55]])
    return corners @ rotation.T + route_point(lane, progress)


def run():
    began = time.perf_counter()
    lighthouse, names = glb_triangles(ART / "lighthouse.glb")
    low, low_names = clip_below(lighthouse, names, 2.0)
    projected = low[:, :, [0, 2]]
    convex = hull(projected.reshape(-1, 2))
    hull_fan = np.array([[convex[0], convex[i], convex[i + 1]] for i in range(1, len(convex) - 1)])
    report = {
        "status": "running", "method": "actual GLB triangles clipped at Y<=2.0, all underwater geometry retained; projected exact distance; convex hull only used as conservative pruning lower bound",
        "float_precision": "Python float64 route port; runtime physical shape test remains authoritative",
        "source_files": {name: sha(ART / (name + ".glb")) for name in ["lighthouse", "coast", "rocks", "town"]},
        "route_sha256": sha(ROOT / "demo/tropical_harbor_3d/fleet/harbor_route.gd"),
        "total_lighthouse_triangles": len(lighthouse), "low_clipped_triangles": len(low),
        "world_bounds": [lighthouse.min(axis=(0, 1)).tolist(), lighthouse.max(axis=(0, 1)).tolist()],
        "low_convex_hull": convex.tolist(), "boat_rectangle": {"width": 2.1, "length": 5.1, "margin_included": False},
    }
    candidates = []
    for lane in range(3):
        for step in range(657):
            progress = min(step*.02, 13.12)
            rectangle = boat_polygon(lane, progress)
            lower = float(np.min(polygon_triangle_squared(rectangle, hull_fan)))
            candidates.append((lower, lane, progress, rectangle))
    candidates.sort(key=lambda row: row[0])
    best, best_row, tested = np.inf, None, 0
    for lower, lane, progress, rectangle in candidates:
        if lower > best + 1e-12:
            break
        distances = polygon_triangle_squared(rectangle, projected)
        index = int(np.argmin(distances))
        tested += 1
        if distances[index] < best:
            best = float(distances[index])
            best_row = {"lane": lane, "progress": progress, "ship_center_xz": route_point(lane, progress).tolist(),
                        "ship_rectangle_xz": rectangle.tolist(), "lighthouse_node": str(low_names[index]),
                        "lighthouse_triangle": low[index].tolist()}
    report["route"] = {"samples": len(candidates), "convex_pruning_lower_bound": math.sqrt(candidates[0][0]),
                       "actual_triangle_samples_evaluated": tested, "pruned_samples": len(candidates)-tested,
                       "minimum_actual_horizontal_gap": math.sqrt(best), "nearest": best_row,
                       "all_samples_positive": best > 0}
    print("ROUTE", report["route"], flush=True)
    contacts = {}
    for asset in ["coast", "rocks", "town"]:
        external, external_names = glb_triangles(ART / (asset + ".glb"))
        # Include every actual external triangle with any vertex below 3m;
        # do not clip external structures, making this projection conservative.
        mask = external[:, :, 1].min(axis=1) < 3.0
        external, external_names = external[mask], external_names[mask]
        ext_proj = external[:, :, [0, 2]]
        lower = polygon_triangle_squared(convex, ext_proj)
        order = np.argsort(lower)
        best, nearest, evaluated = np.inf, None, 0
        for index in order:
            if lower[index] > best + 1e-12:
                break
            distances = polygon_triangle_squared(ext_proj[index], projected)
            internal = int(np.argmin(distances))
            evaluated += 1
            if distances[internal] < best:
                best = float(distances[internal])
                nearest = {"external_node": str(external_names[index]), "external_triangle": external[index].tolist(),
                           "lighthouse_node": str(low_names[internal]), "lighthouse_triangle": low[internal].tolist()}
        contacts[asset] = {"external_triangle_count": len(external), "convex_pruning_lower_bound": float(np.sqrt(lower.min())),
                           "actual_triangle_pairs_batches_evaluated": evaluated, "minimum_actual_horizontal_gap": math.sqrt(best),
                           "positive": best > 0, "nearest": nearest}
        print("CONTACT", asset, contacts[asset]["minimum_actual_horizontal_gap"], "batches", evaluated, flush=True)
    report["contacts"] = contacts
    report["elapsed_seconds"] = time.perf_counter()-began
    report["status"] = "completed"
    report["passed"] = report["route"]["all_samples_positive"] and all(row["positive"] for row in contacts.values())
    (OUT / "actual_geometry_clearance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    print("DONE", report["passed"], report["elapsed_seconds"], flush=True)


if __name__ == "__main__":
    run()
