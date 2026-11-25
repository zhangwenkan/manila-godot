"""Read-only G23 texture/cache, preserved-asset and capture audit.

Never imports assets or launches Blender/Godot. Only --output writes a report.
Requires Pillow and NumPy to compare the actual lossless imported top mip.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import struct

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "demo/tropical_harbor_3d/assets/reference"
BASELINE = ROOT / "demo/tropical_harbor_3d/captures/ground_integration_20261123/before_hashes.json"
NAMES = ("Grass", "Rock", "Path", "Soil", "Sand", "LandUse")
PRESERVED = {"town.glb", "cargo_port.glb", "boat.glb", "cargo_ginseng.glb",
             "cargo_jade.glb", "cargo_nutmeg.glb", "cargo_silk.glb", "ocean.glb", "rocks.glb"}
EXPECTED = {
    "compress/mode": "0", "compress/normal_map": "2", "compress/channel_pack": "0",
    "mipmaps/generate": "true", "roughness/mode": "1",
    "process/channel_remap/red": "0", "process/channel_remap/green": "1",
    "process/channel_remap/blue": "2", "process/channel_remap/alpha": "3",
    "process/fix_alpha_border": "false", "process/premult_alpha": "false",
    "process/hdr_as_srgb": "false", "process/size_limit": "0", "detect_3d/compress_to": "0",
}


def digest(path: Path, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_glb(path: Path):
    raw = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", raw)
    assert magic == b"glTF" and version == 2 and length == len(raw)
    chunks, offset = {}, 12
    while offset < len(raw):
        size, kind = struct.unpack_from("<II", raw, offset)
        chunks[kind] = raw[offset + 8:offset + 8 + size]
        offset += 8 + size
    return json.loads(chunks[0x4E4F534A]), chunks[0x004E4942]


def read_accessor(document: dict, binary: bytes, index: int) -> np.ndarray:
    item = document["accessors"][index]
    assert "sparse" not in item, "Sparse GLB accessor requires separate handling"
    view = document["bufferViews"][item["bufferView"]]
    dtype = np.dtype({5120: "i1", 5121: "u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}[item["componentType"]])
    channels = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[item["type"]]
    stride = view.get("byteStride", dtype.itemsize * channels)
    offset = view.get("byteOffset", 0) + item.get("byteOffset", 0)
    values = np.ndarray((item["count"], channels), dtype=dtype, buffer=binary,
                        offset=offset, strides=(stride, dtype.itemsize)).copy()
    if item.get("normalized"):
        values = values.astype(np.float64) / np.iinfo(dtype).max
        if dtype.kind == "i":
            values = np.maximum(values, -1)
    return values


def import_cache_audit(path: Path) -> dict:
    config = path.with_suffix(path.suffix + ".import")
    result = {"source_md5": digest(path, "md5"), "config_exists": config.exists(), "pass": False}
    if not config.exists():
        return result
    params = dict(re.findall(r"^([^=\r\n]+)=([^\r\n]+)$", config.read_text(encoding="utf-8-sig"), re.M))
    result["uid"] = params.get("uid", "").strip('"')
    value = params.get("path", "").strip('"')
    if not value.startswith("res://"):
        return result
    cache = ROOT / value[6:]
    result["cache"] = str(cache)
    result["cache_exists"] = cache.exists()
    hash_path = cache.with_suffix(".md5")
    if hash_path.exists():
        match = re.search(r'source_md5="([a-f0-9]+)"', hash_path.read_text())
        result["cache_source_md5"] = match.group(1) if match else None
    result["pass"] = result["cache_exists"] and result.get("cache_source_md5") == result["source_md5"]
    return result


def new_ground_asset_audit(filename: str) -> dict:
    path = ART / filename
    output = {"path": str(path), "exists": path.exists(), "pass": False}
    if not path.exists():
        return output
    document, binary = read_glb(path)
    output.update({"sha256": digest(path), "mesh_count": len(document["meshes"]),
                   "materials": document.get("materials", []), "primitives": [],
                   "node_transforms": [{"name": node.get("name"), **{k: node[k] for k in ("matrix", "translation", "rotation", "scale") if k in node}}
                                       for node in document.get("nodes", []) if any(k in node for k in ("matrix", "translation", "rotation", "scale"))]})
    positions, triangle_sets = [], []
    vertices_before = 0
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            attributes = primitive["attributes"]
            p = read_accessor(document, binary, attributes["POSITION"])
            indices = read_accessor(document, binary, primitive["indices"]).ravel() if "indices" in primitive else np.arange(len(p))
            mode = primitive.get("mode", 4)
            assert mode == 4 and len(indices) % 3 == 0, "Audit expects triangle-list primitives"
            triangles = indices.reshape(-1, 3).astype(np.int64)
            row = {"mesh": mesh.get("name"), "vertices": len(p), "triangles": len(triangles),
                   "mode": mode, "attributes": list(attributes), "material": primitive.get("material"),
                   "positions_finite": bool(np.isfinite(p).all()), "indices_valid": bool(indices.max() < len(p) and indices.min() >= 0),
                   "bounds": [p.min(axis=0).tolist(), p.max(axis=0).tolist()]}
            if "COLOR_0" in attributes:
                color = read_accessor(document, binary, attributes["COLOR_0"])
                row["color"] = {"count": len(color), "channels": color.shape[1],
                                "finite": bool(np.isfinite(color).all()),
                                "min": color.min(axis=0).tolist(), "max": color.max(axis=0).tolist(),
                                "nonwhite": bool((color[:, :3] < .99).any()), "count_matches_position": len(color) == len(p)}
            output["primitives"].append(row)
            positions.append(p);triangle_sets.append(triangles + vertices_before);vertices_before += len(p)
    output["vertices"] = vertices_before
    output["triangles"] = sum(row["triangles"] for row in output["primitives"])
    if filename == "ground_rock.glb":
        # Flat-normal and UV seams split exported vertices. Weld matching positions
        # only for this small solid rock topology audit; do not alter the asset.
        p = np.concatenate(positions)
        welded, inverse = np.unique(np.round(p, 6), axis=0, return_inverse=True)
        faces = inverse[np.concatenate(triangle_sets)]
        edges = Counter(tuple(sorted((int(a), int(b)))) for tri in faces for a, b in zip(tri, np.roll(tri, -1)))
        parent = np.arange(len(welded))
        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return int(i)
        for a, b in edges:
            parent[find(a)] = find(b)
        areas = np.linalg.norm(np.cross(welded[faces[:, 1]] - welded[faces[:, 0]], welded[faces[:, 2]] - welded[faces[:, 0]]), axis=1) * .5
        output["welded_topology"] = {"rounding_decimal_places": 6, "vertices": len(welded),
                                      "components": len({find(i) for i in range(len(welded))}),
                                      "boundary_edges": sum(v == 1 for v in edges.values()),
                                      "nonmanifold_edges": sum(v > 2 for v in edges.values()),
                                      "degenerate_triangles": int((areas <= 1e-10).sum())}
        top = output["welded_topology"]
        authored = json.loads((BASELINE.parent / "rock_outcrops_revised.json").read_text(encoding="utf-8"))
        output["authored_geometry_metadata"] = {key: authored[key] for key in ("triangles", "count", "vertices")}
        output["geometry_expected"] = (output["triangles"] == authored["triangles"] and top["components"] == authored["count"]
                                       and top["boundary_edges"] == top["nonmanifold_edges"] == top["degenerate_triangles"] == 0)
    else:
        output["all_primitives_have_nonempty_color"] = bool(output["primitives"]) and all(
            row.get("color", {}).get("count_matches_position") and row["color"]["finite"] and row["color"]["nonwhite"]
            for row in output["primitives"])
        output["grass_triangles"] = sum(row["triangles"] for row in output["primitives"] if "Grass" in (row["mesh"] or ""))
        contacts = json.loads((BASELINE.parent / "contacts.json").read_text(encoding="utf-8"))
        output["geometry_expected"] = output["all_primitives_have_nonempty_color"] and output["grass_triangles"] == contacts["grass_triangles"]
        output["authored_contact_metadata"] = {key: contacts.get(key) for key in ("grass_clumps", "grass_triangles", "fragments")}
    output["import_cache"] = import_cache_audit(path)
    output["pass"] = (output["geometry_expected"] and output["import_cache"]["pass"]
                      and all(row["positions_finite"] and row["indices_valid"] for row in output["primitives"]))
    return output


def source_wiring_audit() -> dict:
    root_scene = (ROOT / "project.godot").read_text(encoding="utf-8")
    entry = (ROOT / "demo/tropical_harbor_3d/fleet_harbor.gd").read_text(encoding="utf-8")
    environment_path = ROOT / "demo/tropical_harbor_3d/environment/reference_environment.gd"
    shader_path = ROOT / "demo/tropical_harbor_3d/materials/landform_mass.gdshader"
    environment = "\n".join(line.split("#", 1)[0] for line in environment_path.read_text(encoding="utf-8").splitlines())
    shader = re.sub(r"//[^\n]*", "", shader_path.read_text(encoding="utf-8"))
    checks = {
        "root_main_scene": 'run/main_scene="res://demo/tropical_harbor_3d/fleet_harbor.tscn"' in root_scene,
        "default_reference_art": "var reference_art := true" in entry and "reference_art = not (" in entry,
        "reference_environment_selected": 'reference_environment.gd").new(self) if reference_art' in entry,
        "shared_ground_shader": 'materials/landform_mass.gdshader")' in environment,
        "continuous_terrain_loaded": 'load(ART + "terrain.glb")' in environment,
        "continuous_terrain_shader_override": 'mesh.set_surface_override_material(surface, sand_material)' in environment,
        "outcrop_scene_inactive": "ground_rock.glb" not in environment,
        "outcrop_override_removed": "mineral_material" not in environment and "ground_rock_only" not in environment,
        "cover_scene_loaded": 'load(ART + "ground_cover.glb")' in environment,
        "cover_linear_vertex_color": "cover_material.vertex_color_use_as_albedo = true" in environment and "cover_material.vertex_color_is_srgb = false" in environment,
        "rock_only_override_removed": "ground_rock_only" not in shader,
        "six_surface_bindings": all(f'ART + "G23_{name}.png"' in environment for name in NAMES),
        "complete_surface_set_enabled": '_bind_ground_surfaces(sand_material)' in environment and 'material.set_shader_parameter("ground_surface_enabled", true)' in environment,
        "world_rock_tile_8m": "surface_color_height(ground_rock, world_position, projection, 8.0, rock_samples)" in shader,
        "world_grass_tile_5m": "surface_color_height(ground_grass, world_position, projection, 5.0, grass_samples)" in shader,
        "grass_040_rock_24_path_012_soil_050": "height_ranges = vec4(0.040, 0.24, 0.012, 0.050)" in shader,
        "land_use_linear": bool(re.search(r"uniform sampler2D ground_land_use\s*:\s*(?![^;]*source_color)[^;]+;", shader)),
        "surface_rgb_srgb": all(bool(re.search(r"uniform sampler2D ground_" + role + r"\s*:\s*source_color", shader)) for role in ("grass", "rock", "path", "soil", "sand")),
    }
    return {"scope": "Read-only static wiring check; runtime compile is checked in capture logs",
            "environment_sha256": digest(environment_path), "shader_sha256": digest(shader_path),
            "checks": checks, "pass": all(checks.values())}


def texture_audit(name: str) -> dict:
    source = ART / f"G23_{name}.png"
    config = source.with_suffix(".png.import")
    result = {"source": str(source), "source_exists": source.exists(),
              "import_exists": config.exists(), "pass": False}
    if not (source.exists() and config.exists()):
        return result
    params = dict(re.findall(r"^([^=\r\n]+)=([^\r\n]+)$", config.read_text(encoding="utf-8-sig"), re.M))
    result["uid"] = params.get("uid", "").strip('"')
    result["settings"] = {key: params.get(key) for key in EXPECTED}
    result["settings_ok"] = all(params.get(key) == value for key, value in EXPECTED.items())
    source_rgba = np.array(Image.open(source))
    result["source_shape"] = list(source_rgba.shape)
    result["source_md5"] = digest(source, "md5")
    result["source_sha256"] = digest(source)
    if source_rgba.ndim != 3 or source_rgba.shape[-1] != 4:
        result["failure"] = "Authored source must retain RGBA."
        return result
    result["source_alpha_range"] = [int(source_rgba[:, :, 3].min()), int(source_rgba[:, :, 3].max())]
    result["source_alpha_unique"] = int(np.unique(source_rgba[:, :, 3]).size)
    cache_value = params.get("path", "").strip('"')
    if not cache_value.startswith("res://"):
        result["failure"] = "No unambiguous imported cache path."
        return result
    cache = ROOT / cache_value[6:]
    result["cache"] = str(cache)
    result["cache_exists"] = cache.exists()
    hash_path = Path(str(cache).removesuffix(".ctex").removesuffix(".s3tc").removesuffix(".bptc") + ".md5")
    if hash_path.exists():
        matched = re.search(r'source_md5="([a-f0-9]+)"', hash_path.read_text())
        result["cache_source_md5"] = matched.group(1) if matched else None
    result["cache_current"] = result.get("cache_source_md5") == result["source_md5"]
    if not cache.exists():
        return result
    raw = cache.read_bytes()
    result["cache_header"] = raw[:4].decode("ascii", errors="replace")
    offset = raw.find(b"RIFF")
    if offset < 0 or raw[offset + 8:offset + 12] != b"WEBP":
        result["failure"] = "Expected lossless embedded WebP top mip; inspect other format manually."
        return result
    length = struct.unpack_from("<I", raw, offset + 4)[0] + 8
    runtime_rgba = np.array(Image.open(io.BytesIO(raw[offset:offset + length])))
    result["runtime_shape"] = list(runtime_rgba.shape)
    result["runtime_rgba"] = runtime_rgba.ndim == 3 and runtime_rgba.shape[-1] == 4
    if runtime_rgba.shape != source_rgba.shape:
        result["failure"] = "Imported channels or dimensions differ from PNG."
        return result
    error = np.abs(runtime_rgba.astype(np.int16) - source_rgba.astype(np.int16))
    result["rgb_max_error"] = int(error[:, :, :3].max())
    result["alpha_max_error"] = int(error[:, :, 3].max())
    result["runtime_alpha_range"] = [int(runtime_rgba[:, :, 3].min()), int(runtime_rgba[:, :, 3].max())]
    result["runtime_alpha_unique"] = int(np.unique(runtime_rgba[:, :, 3]).size)
    result["pass"] = (result["settings_ok"] and result["cache_current"]
                      and result["runtime_rgba"] and int(error.max()) == 0)
    return result


def triangle_signature(points: np.ndarray) -> np.ndarray:
    """Compare exported faces without depending on glTF vertex/index ordering.

    Axis conversion is exact here; 10 micrometres only accommodates the
    exporter's float32 serialization. Winding is checked by the core audit.
    """
    values = np.rint(points * 100000).astype(np.int64)
    order = np.lexsort((values[:, :, 2], values[:, :, 1], values[:, :, 0]), axis=1)
    values = np.take_along_axis(values, order[:, :, None], axis=1).reshape(-1, 9)
    return values[np.lexsort(values[:, ::-1].T)]


def integrated_terrain_audit() -> dict:
    folder = BASELINE.parent
    source = folder / "integrated_shoulders.json"
    snapshot = folder / "integrated_shoulders_before_after.npz"
    path = ART / "terrain.glb"
    output = {"report": str(source), "snapshot": str(snapshot), "runtime_asset": str(path),
              "visual_accepted": False, "pass": False}
    if not all(p.exists() for p in (source, snapshot, path)):
        output["missing"] = [str(p) for p in (source, snapshot, path) if not p.exists()]
        return output
    authored = json.loads(source.read_text(encoding="utf-8"))
    output["authored"] = authored
    output["report_sha256"] = digest(source)
    output["snapshot_sha256"] = digest(snapshot)
    output["runtime_sha256"] = digest(path)
    with np.load(snapshot) as data:
        before, positions, triangles = data["before"].copy(), data["positions"].copy(), data["triangles"].copy()
        boundary, fixed, changed = data["boundary"].copy(), data["fixed"].copy(), data["changed"].copy()
    delta = positions.astype(np.float64) - before
    measured_changed = np.flatnonzero(np.linalg.norm(delta, axis=1) > 1e-6)
    vectors = positions[triangles]
    normals = np.cross(vectors[:, 1] - vectors[:, 0], vectors[:, 2] - vectors[:, 0])
    world = positions[:, [0, 2, 1]].copy()
    world[:, 2] *= -1
    document, binary = read_glb(path)
    exported = []
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            p = read_accessor(document, binary, primitive["attributes"]["POSITION"])
            ids = read_accessor(document, binary, primitive["indices"]).ravel().reshape(-1, 3)
            assert primitive.get("mode", 4) == 4
            exported.append(p[ids])
    exported = np.concatenate(exported)
    exported_normals = np.cross(exported[:, 1] - exported[:, 0], exported[:, 2] - exported[:, 0])
    transforms = [node for node in document["nodes"] if any(k in node for k in ("matrix", "translation", "rotation", "scale"))]
    output["exported_triangles"] = len(exported)
    output["source_vertices"] = len(positions)
    output["source_triangles"] = len(triangles)
    output["comparison_quantization_m"] = 0.00001
    output["checks"] = {
        "applied_six_groups": authored.get("applied") is True and len(authored.get("groups", [])) == 6,
        "reported_topology_preserved": authored.get("topology_unchanged") is True and authored.get("fixed_boundary") is True,
        "boundary_coordinates_unchanged": np.array_equal(positions[boundary], before[boundary]),
        "protected_coordinates_unchanged": np.array_equal(positions[fixed], before[fixed]),
        "only_x_changed": np.array_equal(positions[:, 1:], before[:, 1:]),
        "changed_count_matches": len(measured_changed) == authored.get("changed_vertices") and np.array_equal(measured_changed, changed),
        "finite_positions": bool(np.isfinite(positions).all()),
        "positive_projected_areas": bool((normals[:, 2] > 0).all()),
        "protected_support_unchanged": authored.get("protected_contacts", 0) > 0 and authored.get("max_support_delta_m", 1) < 0.00002,
        "runtime_identity_transforms": not transforms,
        "runtime_faces_finite_and_upward": bool(np.isfinite(exported).all() and (exported_normals[:, 1] > 0).all()),
        "runtime_faces_match_final_snapshot": np.array_equal(triangle_signature(exported), triangle_signature(world[triangles])),
    }
    output["import_cache"] = import_cache_audit(path)
    output["pass"] = all(output["checks"].values()) and output["import_cache"]["pass"]
    return output


def final_grounding_audit(cover: dict) -> dict:
    """Cross-check authored contact evidence against the actual exported counts.

    This preserves the modeling passes' stated tolerances; it does not replace
    their Blender ray casts or treat report metadata as new geometric samples.
    """
    folder = BASELINE.parent
    files = {"cover": folder / "contacts.json", "legacy_grass": folder / "grass_reground_integrated_shoulders.json",
             "core": folder / "core_audit.json", "rock_surface": folder / "rock_weathering_21.json",
             "foliage_export": folder / "foliage_export.json"}
    output = {"scope": "Authored final contact checks plus independent exported counts; no new ray casts",
              "visual_accepted": False, "pass": False,
              "files": {key: str(value) for key, value in files.items()}}
    if not all(path.exists() for path in files.values()):
        output["missing"] = [str(path) for path in files.values() if not path.exists()]
        return output
    reports = {key: json.loads(path.read_text(encoding="utf-8-sig")) for key, path in files.items()}
    output["report_sha256"] = {key: digest(path) for key, path in files.items()}
    contacts, grass, core, rock = (reports[key] for key in ("cover", "legacy_grass", "core", "rock_surface"))
    shoulder_report = folder / "integrated_shoulders.json"
    refreshed_after_shoulders = shoulder_report.exists() and all(
        files[key].stat().st_mtime_ns >= shoulder_report.stat().st_mtime_ns
        for key in ("cover", "legacy_grass", "core"))
    output["cover"] = {key: value for key, value in contacts.items() if key not in ("grounded_roots", "fragments_centers")}
    output["legacy_grass"] = {key: value for key, value in grass.items() if key != "blades"}
    output["core"] = {key: core.get(key) for key in ("status", "core_checks_pass", "failures", "topology", "floor_count", "step_count", "height_cache")}
    output["core"]["cargo"] = {key: value for key, value in core.get("cargo", {}).items() if key != "worst_samples"}
    output["rock_surface"] = rock
    foliage = ART / "foliage.glb"
    document, _ = read_glb(foliage)
    grass_meshes = [{"name": mesh.get("name"), "triangles": sum(document["accessors"][p["indices"]]["count"] // 3 for p in mesh["primitives"])}
                    for mesh in document["meshes"] if "Grass" in mesh.get("name", "")]
    output["exported_legacy_grass_meshes"] = grass_meshes
    output["foliage_export"] = reports["foliage_export"]
    output["foliage_import_cache"] = import_cache_audit(foliage)
    gap_max = lambda record, key: max(record[key]) if record.get(key) else float("inf")
    topology = core.get("topology", {})
    cargo, cache = core.get("cargo", {}), core.get("height_cache", {})
    retained = [row for row in grass.get("blades", []) if row.get("removed") is False]
    output["checks"] = {
        "contact_and_core_reports_follow_shoulders": refreshed_after_shoulders,
        "cover_triangle_count_matches": cover.get("grass_triangles") == contacts.get("grass_triangles"),
        "cover_roots_and_fragments_count_match": len(contacts.get("grounded_roots", [])) == contacts.get("grass_clumps") and len(contacts.get("fragments_centers", [])) == contacts.get("fragments"),
        "cover_roots_and_basal_corners_embedded": gap_max(contacts, "grass_root_gap_range_m") < 0 and gap_max(contacts, "grass_basal_corner_gap_range_m") < 0 and contacts.get("floating_basal_corners") == 0,
        "legacy_final_pass": grass.get("pass") == "integrated_continuous_shoulders",
        "legacy_population_consistent": grass.get("before_blades", -1) - grass.get("removed_blades", -1) == grass.get("remaining_blades") and grass.get("replanted_blades", -1) + grass.get("unchanged_outside_blades", -1) == grass.get("remaining_blades"),
        "legacy_export_count_matches": sum(row["triangles"] for row in grass_meshes) == grass.get("remaining_blades"),
        "legacy_export_matches_post_rooting_report": reports["foliage_export"].get("sha256") == digest(foliage) and files["foliage_export"].stat().st_mtime_ns >= files["legacy_grass"].stat().st_mtime_ns,
        "legacy_detail_count_matches": len(retained) == grass.get("replanted_blades"),
        "legacy_scoped_roots_embedded": gap_max(grass, "retained_root_gap_range_m") <= -0.01198 and gap_max(grass, "retained_basal_corner_gap_range_m") <= -0.01198 and grass.get("retained_scoped_floating_roots") == 0,
        "legacy_detail_roots_embedded": bool(retained) and all(row["root_gap_m"] <= -0.01198 and max(row["basal_corner_gaps_m"]) <= -0.01198 for row in retained),
        "legacy_outside_scope_preserved": grass.get("scope_only") is True and grass.get("unchanged_outside_roots_above_0_025m") == 0,
        "core_completed_without_failure": core.get("status") == "completed" and core.get("core_checks_pass") is True and core.get("failures") == [],
        "core_no_new_boundary_or_bad_faces": all(topology.get(key) == 0 for key in ("boundary_index_edges_added", "boundary_index_edges_removed", "new_nonmanifold_edges", "negative_triangles", "degenerate_triangles")),
        "core_nine_floors_eight_entrances": core.get("floor_count") == len(core.get("floors", [])) == 9 and core.get("step_count") == len(core.get("steps", [])) == 8 and all(row.get("supported") is True for row in core.get("steps", [])),
        "core_cargo_clear": cargo.get("samples") == cargo.get("expected_samples") == 235 and cargo.get("penetrations") == 0 and cargo.get("missing_ground_hits") == [] and cargo.get("minimum_clearance_m", -1) > 0,
        "core_height_cache_matches": cache.get("errors_over_1mm") == 0 and cache.get("maximum_error_m", 1) <= 0.001 and cache.get("outside_mesh_fallback_samples") == 0,
        "rock_surface_8m_024m": rock.get("tile_m") == 8 and rock.get("height_range_m") == 0.24,
    }
    output["pass"] = all(output["checks"].values()) and output["foliage_import_cache"]["pass"]
    return output


def capture_audit(folder: Path) -> dict:
    if not folder.is_absolute():
        folder = ROOT / folder
    output = {"path": str(folder), "exists": folder.exists(), "visual_accepted": False, "pass": False}
    result_path = folder / "art_result.json"
    if result_path.exists():
        result = json.loads(result_path.read_text(encoding="utf-8-sig"))
        frames = result.get("frames", [])
        output.update({"checks": result.get("checks"), "frame_count": len(frames),
                       "missing_frames": [name for name in frames if not (folder / name).is_file()],
                       "result_sha256": digest(result_path),
                       "duplicate_frames": len(frames) != len(set(frames)),
                       "timing": result.get("timing"), "kind": result.get("kind"),
                       "declared_visual_accepted": result.get("visual_accepted")})
        output["scope"] = "screenshot_only" if result.get("checks") == 0 else "runtime_checks"
    else:
        output["missing_result"] = True
    output["logs"] = {}
    log_text = {}
    for name in ("import.log", "preview.log"):
        path = folder / name
        if path.exists():
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
            log_text[name] = "\n".join(lines)
            output["logs"][name] = {
                "sha256": digest(path),
                "all_lines_scanned": len(lines), "bytes_scanned": path.stat().st_size,
                "error_lines": [line for line in lines if re.search(r"\bERROR\b|ART_PREVIEW_(?:FAILED|TIMEOUT)", line)],
                "warning_lines": [line for line in lines if "WARNING:" in line],
            }
    completions = re.findall(r"ART_PREVIEW_SAVED frames=(\d+) output=([^\r\n]+)", log_text.get("preview.log", ""))
    output["completion_markers"] = [{"frames": int(count), "output": location} for count, location in completions]
    output["log_checks"] = {
        "both_logs_present_and_scanned_in_full": set(output["logs"]) == {"import.log", "preview.log"} and all(row["all_lines_scanned"] > 0 for row in output["logs"].values()),
        "no_logged_errors": bool(output["logs"]) and not any(row["error_lines"] for row in output["logs"].values()),
        "one_matching_completion_marker": len(completions) == 1 and int(completions[0][0]) == output.get("frame_count") and Path(completions[0][1]).resolve() == folder.resolve(),
        "nonempty_unique_frames_present": output.get("frame_count", 0) > 0 and not output.get("missing_frames", True) and not output.get("duplicate_frames", True),
    }
    output["pass"] = all(output["log_checks"].values())
    output["full_runtime_checks_pass"] = output["pass"] and output.get("checks", 0) > 0 and output.get("kind") == "reference harbor runtime verification"
    return output


def audit(captures: list[Path]) -> dict:
    report = {"read_only": True, "visual_accepted": False,
              "checked_at_utc": datetime.now(timezone.utc).isoformat()}
    baseline = json.loads(BASELINE.read_text(encoding="utf-8-sig"))
    hashes = []
    for row in baseline:
        path = Path(row["Path"])
        current = digest(path) if path.exists() else None
        hashes.append({"path": str(path), "preserved": path.name in PRESERVED,
                       "sha256": current, "unchanged": current == row["Hash"].lower()})
    report["baseline_hashes"] = hashes
    retained = [row for row in hashes if row["preserved"]]
    report["preserved_glbs_ok"] = len(retained) == 9 and all(row["unchanged"] for row in retained)
    coast = [row for row in hashes if Path(row["path"]).name == "coast.glb"]
    report["coast_glb_unchanged"] = len(coast) == 1 and coast[0]["unchanged"]
    report["textures"] = {name: texture_audit(name) for name in NAMES}
    uids = [item.get("uid") for item in report["textures"].values()]
    report["unique_engine_uids"] = all(uids) and len(set(uids)) == len(NAMES)
    report["textures_ok"] = all(item["pass"] for item in report["textures"].values())
    first_report = BASELINE.parent / "first_independent_verification.json"
    if first_report.exists():
        first = json.loads(first_report.read_text(encoding="utf-8"))
        report["texture_import_identity_preserved"] = {
            name: {"uid_unchanged": row.get("uid") == first["textures"][name].get("uid"),
                   "settings_unchanged": row.get("settings") == first["textures"][name].get("settings")}
            for name, row in report["textures"].items()}
    report["new_ground_assets"] = {"ground_cover.glb": new_ground_asset_audit("ground_cover.glb")}
    archived_rock = new_ground_asset_audit("ground_rock.glb")
    archived_rock.update({"status": "archived_inactive", "runtime_asset": False,
                          "required_for_runtime_pass": False,
                          "note": "Intermediate V5 plates retained for history; no instance is loaded by the active environment."})
    report["archived_assets"] = {"ground_rock.glb": archived_rock}
    report["source_wiring"] = source_wiring_audit()
    report["integrated_terrain"] = integrated_terrain_audit()
    report["final_grounding"] = final_grounding_audit(report["new_ground_assets"]["ground_cover.glb"])
    authored_land = BASELINE.parent / "land_data.npz"
    land_png = ART / "G23_LandUse.png"
    if authored_land.exists() and land_png.exists():
        with np.load(authored_land) as data:
            expected = np.round(np.clip(data["land"][::-1], 0, 1) * 255).astype(np.uint8)
        actual = np.array(Image.open(land_png))
        report["land_use_orientation"] = {
            "authored_array_is_bottom_up": True,
            "shader_expected_v": "1 - (world_z + 15) / 97",
            "png_shape": list(actual.shape),
            "matches_flipped_quantized_authored_data": bool(np.array_equal(actual, expected)),
        }
    report["captures"] = [capture_audit(folder) for folder in captures]
    runtime_inputs = [ART / name for name in ("terrain.glb", "foliage.glb", "ground_cover.glb", "shore_relief_height.json")]
    runtime_inputs += [ART / f"G23_{name}.png" for name in NAMES]
    runtime_inputs += [ROOT / "demo/tropical_harbor_3d/environment/reference_environment.gd",
                       ROOT / "demo/tropical_harbor_3d/materials/landform_mass.gdshader"]
    latest_input = max(runtime_inputs, key=lambda path: path.stat().st_mtime_ns)
    report["latest_runtime_input_write"] = {"path": str(latest_input),
                                            "utc": datetime.fromtimestamp(latest_input.stat().st_mtime, timezone.utc).isoformat()}
    for item in report["captures"]:
        result_path = Path(item["path"]) / "art_result.json"
        item["postdates_current_runtime_inputs"] = result_path.exists() and result_path.stat().st_mtime_ns >= latest_input.stat().st_mtime_ns
        item["full_runtime_checks_pass"] = item["full_runtime_checks_pass"] and item["postdates_current_runtime_inputs"]
    report["runtime_assets_pass"] = all((report["preserved_glbs_ok"], report["textures_ok"], report["unique_engine_uids"],
                                         report["new_ground_assets"]["ground_cover.glb"]["pass"], report["source_wiring"]["pass"],
                                         report["integrated_terrain"]["pass"], report["final_grounding"]["pass"],
                                         report.get("land_use_orientation", {}).get("matches_flipped_quantized_authored_data", False)))
    report["full_runtime_capture_pass"] = any(item["full_runtime_checks_pass"] for item in report["captures"])
    report["technical_pass"] = report["runtime_assets_pass"] and report["full_runtime_capture_pass"] and all(item["pass"] for item in report["captures"])
    report["acceptance_boundary"] = "Technical pass only; screenshot-only runs cannot substitute for full runtime regression. No visual acceptance is claimed."
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.capture)
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
