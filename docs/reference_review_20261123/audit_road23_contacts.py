"""Read-only road-contact audit. Never launches or imports Blender/Godot.

Only --output writes a report. Requires NumPy/Pillow and the adjacent G23
audit's pure GLB, texture-cache and capture readers. Technical results do not
establish visual acceptance, especially for the already connected clinic road.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
from PIL import Image

from audit_ground23_runtime import (
    ART, ROOT, NAMES, capture_audit, digest, import_cache_audit,
    read_accessor, read_glb, source_wiring_audit, texture_audit, triangle_signature,
)

LOG = ROOT / "demo/tropical_harbor_3d/captures/road_contacts_20261123"
EDITABLE = {"terrain.glb", "foliage.glb", "ground_cover.glb",
            "G23_LandUse.png", "shore_relief_height.json"}


def read_json(name):
    return json.loads((LOG / name).read_text(encoding="utf-8-sig"))


def guarded(function):
    try:
        return function()
    except Exception as exc:
        return {"pass": False, "error": f"{type(exc).__name__}: {exc}"}


def preserved_audit():
    rows = []
    for row in read_json("before_hashes.json"):
        path = Path(row["path"])
        required = path.suffix.lower() != ".blend" and path.name not in EDITABLE
        actual = digest(path) if path.is_file() else None
        rows.append({"path": str(path), "preserved_required": required,
                     "sha256": actual, "unchanged": actual == row["sha256"].lower()})
    required = [row for row in rows if row["preserved_required"]]
    return {"assets": rows, "required_count": len(required),
            "pass": bool(required) and all(row["unchanged"] for row in required)}


def glb_geometry(filename):
    document, binary = read_glb(ART / filename)
    faces, rows = [], []
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            assert primitive.get("mode", 4) == 4, "Expected triangle lists"
            attributes = primitive["attributes"]
            points = read_accessor(document, binary, attributes["POSITION"])
            ids = (read_accessor(document, binary, primitive["indices"]).ravel()
                   if "indices" in primitive else np.arange(len(points)))
            assert len(ids) % 3 == 0 and ids.size > 0
            assert ids.min() >= 0 and ids.max() < len(points) and np.isfinite(points).all()
            faces.append(points[ids.reshape(-1, 3)])
            row = {"mesh": mesh.get("name", ""), "triangles": len(ids) // 3}
            if "COLOR_0" in attributes:
                colors = read_accessor(document, binary, attributes["COLOR_0"])
                row["colors_valid"] = bool(len(colors) == len(points) and np.isfinite(colors).all())
            rows.append(row)
    transforms = [node for node in document.get("nodes", [])
                  if any(k in node for k in ("matrix", "translation", "rotation", "scale"))]
    return np.concatenate(faces), rows, transforms


def terrain_audit():
    grade = read_json("grade.json")
    with np.load(LOG / "baseline.npz") as raw:
        initial, initial_tri = raw["positions"].copy(), raw["loops"].copy().reshape(-1, 3)
        initial_sizes = raw["sizes"].copy()
    with np.load(LOG / "grade_before_after.npz") as raw:
        before, after, tri = (raw[k].copy() for k in ("before", "positions", "triangles"))
        boundary, fixed, reported_changed = (raw[k].copy() for k in ("boundary", "fixed", "changed"))
    delta = after.astype(float) - before
    changed = np.flatnonzero(np.linalg.norm(delta, axis=1) > 1e-6)
    triangles = after[tri]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    old_triangles = before[tri]
    old_normals = np.cross(old_triangles[:, 1] - old_triangles[:, 0], old_triangles[:, 2] - old_triangles[:, 0])
    world = after[:, [0, 2, 1]].copy(); world[:, 2] *= -1
    exported, rows, transforms = glb_geometry("terrain.glb")
    exported_normals = np.cross(exported[:, 1] - exported[:, 0], exported[:, 2] - exported[:, 0])
    checks = {
        "applied_report": grade.get("applied") is True and grade.get("mesh_modified") is True,
        "snapshot_starts_at_this_turn_baseline": np.array_equal(before, initial),
        "topology_matches_baseline": np.array_equal(tri, initial_tri) and bool((initial_sizes == 3).all()),
        "finite_positions": bool(np.isfinite(after).all()),
        "only_vertical_lowering": np.array_equal(before[:, :2], after[:, :2]) and bool((delta[:, 2] <= 2e-7).all()),
        "lowering_at_most_038m": bool((-delta[:, 2].min()) <= .380001),
        "boundary_unchanged": np.array_equal(before[boundary], after[boundary]),
        "protected_vertices_unchanged": np.array_equal(before[fixed], after[fixed]),
        "water_and_low_sand_unchanged": np.array_equal(before[before[:, 2] <= .30], after[before[:, 2] <= .30]),
        "changed_count_and_indices_match": len(changed) == grade.get("changed_vertices") and np.array_equal(changed, reported_changed),
        "source_faces_upward_without_normal_reversal": bool((normals[:, 2] > 0).all() and (np.einsum("ij,ij->i", normals, old_normals) > 0).all()),
        "protected_support_unchanged": grade.get("protected_contacts", 0) > 0 and grade.get("maximum_support_delta_m", 1) < 2e-5,
        "export_has_identity_nodes": not transforms,
        "export_faces_upward": bool((exported_normals[:, 1] > 0).all()),
        "export_faces_match_final_grade": np.array_equal(triangle_signature(exported), triangle_signature(world[tri])),
    }
    cache = import_cache_audit(ART / "terrain.glb")
    return {"checks": checks, "vertices": len(after), "triangles": len(tri),
            "changed_vertices": len(changed), "max_blender_xyz_delta_m": abs(delta).max(0).tolist(),
            "comparison_quantization_m": .00001, "export_primitives": rows, "import_cache": cache,
            "pass": all(checks.values()) and cache["pass"]}


def sample(array, points):
    points = np.asarray(points, float); rows, columns = array.shape[:2]
    x = np.clip((points[:, 0] + 4) / 48 * columns - .5, 0, columns - 1.00001)
    z = np.clip((points[:, 1] + 15) / 97 * rows - .5, 0, rows - 1.00001)
    ix, iz = x.astype(int), z.astype(int); fx, fz = x - ix, z - iz
    if array.ndim == 3: fx, fz = fx[:, None], fz[:, None]
    return ((array[iz, ix] * (1-fx) + array[iz, ix+1] * fx) * (1-fz)
            + (array[iz+1, ix] * (1-fx) + array[iz+1, ix+1] * fx) * fz)


def occupancy_audit():
    report = read_json("occupancy.json")
    with np.load(LOG / "land_data.npz") as raw:
        land, scope = raw["land"].copy(), raw["scope"].copy()
    with np.load(LOG / "preview1/land_data.npz") as raw:
        first_land = raw["land"].copy()
    previous = ROOT / "demo/tropical_harbor_3d/captures/ground_integration_20261123/land_data.npz"
    with np.load(previous) as raw: before = raw["land"].copy()
    image = np.asarray(Image.open(ART / "G23_LandUse.png"))
    expected = np.round(np.clip(land[::-1], 0, 1) * 255).astype(np.uint8)
    routes = []
    selected = {"trading_lower_lane", "clinic_ramp", "restaurant_entry"}
    for route in report["routes"]:
        if route["name"] not in selected: continue
        points = []
        for a, b in zip(route["points"], route["points"][1:]):
            a, b = np.asarray(a, float), np.asarray(b, float)
            count = max(1, int(np.ceil(np.linalg.norm(b-a)/.05)))
            points.extend(a+(b-a)*i/count for i in range(count))
        points.append(route["points"][-1]); points = np.asarray(points)
        weights = sample(land, points); path = weights[:, 2]
        first_path = sample(first_land, points)[:, 2]
        all_weights = np.column_stack((weights, np.maximum(0, 1-weights.sum(1))))
        worst = int(np.argmin(path))
        routes.append({"name": route["name"], "samples": len(points),
                       "sampling_interval_at_most_m": .05, "minimum_path_weight": float(path.min()),
                       "first_pass_minimum_path_weight": float(first_path.min()),
                       "path_weights_unchanged_by_cleanup": bool(np.array_equal(path, first_path)),
                       "worst_xz": points[worst].tolist(), "samples_below_090": int((path < .90).sum()),
                       "path_is_leading_at_every_sample": bool((all_weights.argmax(1) == 2).all()),
                       "pass": bool((path >= .90).all())})
    checks = {
        "finite_and_normalized": bool(np.isfinite(land).all() and land.min() >= 0 and land.max() <= 1 and land.sum(2).max() <= 1.00001),
        "png_matches_flipped_quantized_map": np.array_equal(image, expected),
        "outside_scope_unchanged": np.array_equal(land[scope == 0], before[scope == 0]),
        "report_has_no_global_height_or_slope_clipping": report.get("absolute_height_clipping") is False and report.get("global_slope_clipping") is False,
        "key_route_set_complete": {r["name"] for r in routes} == selected and len(routes) == len(selected),
        "key_route_centrelines_continuous": bool(routes) and all(r["pass"] for r in routes),
    }
    return {"checks": checks, "routes": routes, "pass": all(checks.values()),
            "interpretation": "Weight continuity only. Clinic centreline already connected before this pass; this does not establish visual correctness, slope walkability, or route width."}


def edge_cleanup_audit():
    report = read_json("edge_cleanup.json")
    first_report, current_report = read_json("preview1/occupancy.json"), read_json("occupancy.json")
    with np.load(LOG / "preview1/land_data.npz") as raw:
        first = {key: raw[key].copy() for key in raw.files}
    with np.load(LOG / "land_data.npz") as raw:
        current = {key: raw[key].copy() for key in raw.files}
    before, after, cleanup = first["land"], current["land"], current["edge_cleanup"]
    changed = np.any(before != after, axis=2)
    old_png = np.asarray(Image.open(LOG / "preview1/G23_LandUse.png"))
    checks = {
        "two_reviewed_patches": len(report.get("patches", [])) == 2,
        "first_pass_png_matches_saved_map": np.array_equal(old_png, np.round(np.clip(before[::-1], 0, 1) * 255).astype(np.uint8)),
        "height_normal_scope_unchanged": all(np.array_equal(first[key], current[key]) for key in ("height", "normal", "scope")),
        "path_and_rock_unchanged": np.array_equal(before[..., 1:3], after[..., 1:3]),
        "outside_cleanup_unchanged": np.array_equal(before[cleanup == 0], after[cleanup == 0]),
        "cleanup_stays_in_original_scope": bool((cleanup[current["scope"] == 0] == 0).all()),
        "grass_only_reduced_soil_only_increased": bool((after[..., 0] <= before[..., 0]).all() and (after[..., 3] >= before[..., 3]).all()),
        "changed_pixel_count_matches": int(changed.sum()) == report.get("changed_pixels"),
        "route_definitions_unchanged": first_report["routes"] == current_report["routes"],
        "reports_link_to_first_pass_and_cleanup": current_report.get("edge_cleanup_report") == "edge_cleanup.json" and current_report.get("first_pass_report") == "preview1/occupancy.json",
        "original_contact_report_preserved": digest(LOG / "grass_contacts.json") == digest(LOG / "preview1/grass_contacts.json"),
    }
    return {"checks": checks, "changed_pixels": int(changed.sum()), "patches": report.get("patches"),
            "authored_geometry_unchanged": report.get("geometry_unchanged"),
            "authored_retained_grass_positions_unchanged": [row.get("retained_positions_unchanged") for row in report.get("grass", [])],
            "pass": all(checks.values()),
            "scope": "Independent before/after occupancy comparison. Actual terrain is separately compared with grade; retained grass position preservation is authored evidence."}


def contact_export_audit():
    grass, export, core = (read_json(name) for name in ("grass_contacts.json", "export.json", "core_audit.json"))
    cleanup = read_json("edge_cleanup.json")
    cleanup_grass = {row["name"]: row for row in cleanup["grass"]}
    exported = {}
    for filename in ("foliage.glb", "ground_cover.glb"):
        _, primitives, transforms = glb_geometry(filename)
        exported[filename] = {"primitives": primitives, "import_cache": import_cache_audit(ART / filename),
                              "grass_triangles": sum(row["triangles"] for row in primitives if "Grass" in row["mesh"])}
    populations = []
    mapping = {"L24_GrassTuftClusters": "foliage.glb", "G23_RootedGrassMargins": "ground_cover.glb"}
    for row in grass["grass"]:
        final = cleanup_grass[row["name"]]
        gap_ok = all(row.get(key) is None or max(row[key]) < 0 for key in ("root_gap_range", "basal_gap_range"))
        populations.append({**row, "edge_cleanup": final, "final_triangles": final["after_triangles"],
                            "pass": row["before_triangles"] - row["removed"] == row["after_triangles"]
                            and row["regrounded"] + row["unchanged"] == row["after_triangles"]
                            and final["before_triangles"] == row["after_triangles"]
                            and final["before_triangles"] - final["removed"] == final["after_triangles"]
                            and final.get("retained_positions_unchanged") is True
                            and exported[mapping[row["name"]]]["grass_triangles"] == final["after_triangles"] and gap_ok})
    assets = {}
    for name in EDITABLE:
        recorded = export.get("assets", {}).get(name, {})
        path = ART / name
        assets[name] = {"sha256": digest(path), "bytes": path.stat().st_size,
                        "matches_export_report": recorded.get("sha256") == digest(path) and recorded.get("bytes") == path.stat().st_size}
    stage_names = ("grade.json", "preview1/occupancy.json", "grass_contacts.json",
                   "preview1/export.json", "preview1/core_audit.json", "edge_cleanup.json",
                   "occupancy.json", "export.json", "core_audit.json")
    times = [(LOG / name).stat().st_mtime_ns for name in stage_names]
    topology, cargo, cache = (core.get(key, {}) for key in ("topology", "cargo", "height_cache"))
    remaining_fragments = grass["fragments_before"] - grass["fragments_removed"]
    fragment_triangles = sum(row["triangles"] for row in exported["ground_cover.glb"]["primitives"] if "Fragment" in row["mesh"])
    checks = {
        "source_saved_clean_with_preview_restored": export.get("source_saved") is True and export.get("dirty") is False and export.get("source_material_restored") is True,
        "all_changed_assets_match_final_export": all(row["matches_export_report"] for row in assets.values()),
        "reports_follow_first_pass_then_cleanup_final_export_order": all(a <= b for a, b in zip(times, times[1:])),
        "exports_follow_edge_cleanup": all((ART/name).stat().st_mtime_ns >= times[5] for name in ("terrain.glb", "foliage.glb", "ground_cover.glb", "shore_relief_height.json")),
        "two_grass_populations_consistent": len(populations) == len(cleanup_grass) == 2 and {r["name"] for r in populations} == set(mapping) == set(cleanup_grass) and all(r["pass"] for r in populations),
        "fragment_count_matches": remaining_fragments >= 0 and fragment_triangles == remaining_fragments * 22,
        "cover_vertex_colors_present": all(row.get("colors_valid") for row in exported["ground_cover.glb"]["primitives"]),
        "core_completed_without_failure": core.get("status") == "completed" and core.get("core_checks_pass") is True and core.get("failures") == [],
        "core_no_new_boundary_or_bad_faces": all(topology.get(key) == 0 for key in ("boundary_index_edges_added", "boundary_index_edges_removed", "new_nonmanifold_edges", "negative_triangles", "degenerate_triangles")),
        "core_nine_floors_eight_entrances": core.get("floor_count") == len(core.get("floors", [])) == 9 and core.get("step_count") == len(core.get("steps", [])) == 8 and all(row.get("supported") is True for row in core.get("steps", [])),
        "core_cargo_clear": cargo.get("samples") == cargo.get("expected_samples") == 235 and cargo.get("penetrations") == 0 and cargo.get("missing_ground_hits") == [] and cargo.get("minimum_clearance_m", -1) > 0,
        "core_height_cache_current": cache.get("errors_over_1mm") == 0 and cache.get("maximum_error_m", 1) <= .001 and cache.get("outside_mesh_fallback_samples") == 0,
    }
    return {"checks": checks, "grass": populations, "exported_assets": exported, "asset_hashes": assets,
            "chronology": list(stage_names),
            "pass": all(checks.values()) and all(row["import_cache"]["pass"] for row in exported.values()),
            "scope": "Independent exported counts, hashes, and chronology; source support rays are corroborating authored evidence, not new rays."}


def audit(captures, intermediate_captures=()):
    result = {"read_only": True, "visual_accepted": False,
              "checked_at_utc": datetime.now(timezone.utc).isoformat()}
    for name, function in (("preserved", preserved_audit), ("terrain", terrain_audit),
                           ("occupancy", occupancy_audit), ("edge_cleanup", edge_cleanup_audit),
                           ("contacts_export", contact_export_audit),
                           ("source_wiring", source_wiring_audit)):
        result[name] = guarded(function)
    result["textures"] = {name: guarded(lambda name=name: texture_audit(name)) for name in NAMES}
    uids = [row.get("uid") for row in result["textures"].values()]
    result["unique_texture_uids"] = bool(all(uids) and len(set(uids)) == len(NAMES))
    result["runtime_assets_pass"] = all(result[name]["pass"] for name in ("preserved", "terrain", "occupancy", "edge_cleanup", "contacts_export", "source_wiring")) and all(row["pass"] for row in result["textures"].values()) and result["unique_texture_uids"]
    inputs = [ART/name for name in EDITABLE] + [ART/f"G23_{name}.png" for name in NAMES]
    inputs += [ROOT/"demo/tropical_harbor_3d/materials/landform_mass.gdshader", ROOT/"demo/tropical_harbor_3d/environment/reference_environment.gd"]
    latest = max((p.stat().st_mtime_ns for p in inputs if p.exists()), default=0)
    result["captures"] = [guarded(lambda folder=folder: capture_audit(folder)) for folder in captures]
    for row in result["captures"]:
        path = Path(row.get("path", "")) / "art_result.json"
        row["postdates_runtime_inputs"] = path.is_file() and path.stat().st_mtime_ns >= latest
        row["full_runtime_checks_pass"] = row.get("full_runtime_checks_pass", False) and row["postdates_runtime_inputs"]
    result["intermediate_captures"] = [guarded(lambda folder=folder: capture_audit(folder)) for folder in intermediate_captures]
    for row in result["intermediate_captures"]:
        row["role"] = "intermediate_visual_review_only"
        row["required_to_postdate_final_assets"] = False
        row["counts_as_final_runtime_check"] = False
    result["full_runtime_capture_pass"] = any(row["full_runtime_checks_pass"] for row in result["captures"])
    result["technical_pass"] = result["runtime_assets_pass"] and result["full_runtime_capture_pass"] and all(row["pass"] and row["postdates_runtime_inputs"] for row in result["captures"]) and all(row["pass"] for row in result["intermediate_captures"])
    result["acceptance_boundary"] = "Technical consistency only. No visual acceptance or resolved-performance claim; screenshot-only captures do not replace a full runtime check."
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="append", type=Path, default=[])
    parser.add_argument("--intermediate-capture", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.capture, args.intermediate_capture)
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output: args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
