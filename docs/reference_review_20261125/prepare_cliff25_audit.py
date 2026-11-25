"""Prepare read-only audit inputs from snapshots; never edits scene or assets.

Run with ordinary Python only after the current-round Blender snapshot exists.
The output records the retained structure25 route design, without changing any
of its thresholds. The optional protection NPZ is diagnostic vertex/face IDs.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "demo/tropical_harbor_3d"
LOG = ROOT / "captures/cliff_contacts_20261125"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def intersect_polygon(triangles, polygon):
    """Every triangle touching any simple polygon; allows concave polygons."""
    poly = np.asarray(polygon, float)
    mask = (triangles.max(1) >= poly.min(0) - 1e-8).all(1)
    mask &= (triangles.min(1) <= poly.max(0) + 1e-8).all(1)
    ids = np.flatnonzero(mask)
    t = triangles[ids]
    hit = np.zeros(len(ids), bool)
    inside = np.zeros((len(ids), 3), bool)
    for a, b in zip(poly, np.roll(poly, -1, axis=0)):
        if abs(b[1] - a[1]) > 1e-12:
            inside ^= ((a[1] > t[..., 1]) != (b[1] > t[..., 1])) & (
                t[..., 0] < (b[0] - a[0]) * (t[..., 1] - a[1]) / (b[1] - a[1]) + a[0])
    hit |= inside.any(1)

    def cross(a, b):
        return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]

    for point in poly:
        c = np.stack([cross(t[:, (i+1) % 3] - t[:, i], point-t[:, i]) for i in range(3)], axis=1)
        hit |= (c >= -1e-8).all(1) | (c <= 1e-8).all(1)
    for i in range(3):
        a, b = t[:, i], t[:, (i+1) % 3]
        for c, d in zip(poly, np.roll(poly, -1, axis=0)):
            box = ((np.maximum(a, b) >= np.minimum(c, d)-1e-8) &
                   (np.minimum(a, b) <= np.maximum(c, d)+1e-8)).all(1)
            ca, cb = cross(b-a, c-a), cross(b-a, d-a)
            cc, cd = cross(d-c, a-c), cross(d-c, b-c)
            hit |= box & (ca*cb <= 1e-12) & (cc*cd <= 1e-12)
    mask[:] = False
    mask[ids[hit]] = True
    return mask


def prepare():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, default=9864)
    parser.add_argument("--port", type=int, default=9881)
    args = parser.parse_args()
    session = read(LOG / "session_start.json")
    assert session["pid"] == args.pid and session["port"] == args.port
    design = read(LOG / "design.json")
    assert (len(design["routes"]), len(design["platforms"]), len(design["junctions"]), len(design["entrances"])) == (15, 22, 15, 12)
    manifest = read(LOG / "before_manifest.json")
    fixed = {"town.glb", "cargo_port.glb", "boat.glb", "cargo_ginseng.glb", "cargo_jade.glb",
             "cargo_nutmeg.glb", "cargo_silk.glb", "ocean.glb", "ground_rock.glb"}
    retained = [r for r in manifest if Path(r["relative"]).name in fixed]
    assert len(retained) == len(fixed)
    limits = design["audit_limits"]
    routes = []
    for r in design["routes"]:
        row = dict(r)
        row["points_xzh"] = row["points"]
        row["width_m"] = (np.asarray(row["halfwidth"]) * 2).tolist()
        row["limits"] = dict(limits["routes"], **row.get("limits", {}))
        routes.append(row)
    platforms = []
    for r in design["platforms"]:
        row = dict(r)
        row["limits"] = dict(limits["platforms"], **row.get("limits", {}))
        platforms.append(row)
    spec = {"schema_version": 1, "session": {"pid": args.pid, "port": args.port,
            "source": str(ROOT / "source/harbor_shore_control_mcp.blend")},
            "baseline_npz": str(LOG / "baseline.npz"), "routes": routes,
            "platforms": platforms, "junctions": design["junctions"], "entrances": design["entrances"],
            "foundations_json": "captures/rock_path_sample_20261123/foundations.json",
            "foundations_objects_snapshot": str(LOG / "objects_before.json"),
            "preserved_hashes": retained,
            "cargo": {"objects": ["R20_UpperHull", "R20_LowerHull", "R20_HullBottom"],
                      "expected_samples": 235, "below_height_m": .6,
                      "minimum_clearance_m": limits["cargo_minimum_clearance_m"]},
            "provenance": {"design_sha256": sha(LOG / "design.json"),
                           "baseline_sha256": sha(LOG / "baseline.npz"),
                           "note": "Retained reviewed route/court/entrance limits; current-round terrain baseline."}}
    (LOG / "audit_spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    base = np.load(LOG / "baseline.npz")
    p, triangles = base["positions"], base["triangles"]
    q = p[:, :2].astype(float).copy()
    q[:, 1] *= -1
    qt = q[triangles]
    masks = {}
    for r in routes:
        rr = np.zeros(len(triangles), bool)
        points = np.asarray(r["points"], float)
        widths = np.broadcast_to(np.asarray(r["halfwidth"], float), (len(points),))
        for a, b, wa, wb in zip(points, points[1:], widths, widths[1:]):
            a, b = a[:2], b[:2]
            d = b-a
            side = np.array([-d[1], d[0]]) / np.linalg.norm(d)
            poly = [a-side*wa, b-side*wb, b+side*wb, a+side*wa]
            rr |= intersect_polygon(qt, poly)
        masks["route:" + r["name"]] = rr
    for r in platforms:
        masks["platform:" + r["name"]] = intersect_polygon(qt, r["polygon"])
    for r in design["junctions"]:
        masks["junction:" + r["name"]] = intersect_polygon(qt, r["polygon_xz"])
    protected = np.logical_or.reduce(list(masks.values()))
    vertices = np.unique(triangles[protected])
    np.savez_compressed(LOG / "protected_terrain_faces.npz", face_ids=np.flatnonzero(protected),
                        vertex_ids=vertices, positions=p[vertices], triangles=triangles[protected])
    report = {"read_only_preparation": True, "design_sha256": spec["provenance"]["design_sha256"],
              "baseline_sha256": spec["provenance"]["baseline_sha256"],
              "routes": len(routes), "platforms": len(platforms), "junctions": len(design["junctions"]),
              "gates": sum(len(j["gates"]) for j in design["junctions"]), "entrances": len(design["entrances"]),
              "protected_faces": int(protected.sum()), "protected_vertices": len(vertices),
              "whole_intersecting_faces_by_area": {k: int(v.sum()) for k, v in masks.items()},
              "limitations": ["No live Blender audit performed by this preparation.",
                              "Protection footprint includes all road rectangles, complete court polygons and reviewed junction polygons.",
                              "Foundation protection is independently checked from 9 real floor meshes by the live audit."]}
    (LOG / "audit_preparation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k != "whole_intersecting_faces_by_area"}, ensure_ascii=False))


if __name__ == "__main__":
    prepare()
