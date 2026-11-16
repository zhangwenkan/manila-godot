"""Read-only semantic GLB audit for the 2026-11-13 terminal entry/deck pass.

Only writes the requested JSON report. Never imports Blender or changes assets.
Compare decoded data and named node/material identities, not GLB buffer offsets.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / "captures/terminal_surface_20261113"
RIGS = ["Load", "Fall", "Drum", "HeadWheel", "LeadWheel", "Flags",
        "FlameWest", "FlameEast", "FlameGalleryL", "FlameGalleryR"]
OLD_GROUPS = ["TerminalMesh_HarborCraft_WorkingTimber",
              "TerminalMesh_HarborCraft_WeatheredTimber"]
NEW_GROUPS = ["TerminalMesh_HarborCraft_T13_ApronTimber",
              "TerminalMesh_HarborCraft_T13_EntryWood",
              "TerminalMesh_HarborCraft_T13_PostIron"]
T13 = {
    "HarborCraft_T13_ApronTimber": ("HarborCraft_WorkingTimber", [.82625, .86175, .90225]),
    "HarborCraft_T13_EntryWood": ("HarborCraft_WeatheredTimber", [.86, .875, .895]),
    "HarborCraft_T13_PostIron": ("HarborCraft_CraneForgedIron", None),
}
DTYPES = {5120: "i1", 5121: "u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
WIDTHS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def sha(data):
    return hashlib.sha256(data).hexdigest()


class GLB:
    def __init__(self, path):
        self.path = Path(path)
        data = self.path.read_bytes()
        magic, version, length = struct.unpack_from("<III", data)
        if (magic, version, length) != (0x46546C67, 2, len(data)):
            raise ValueError(f"Invalid or incomplete GLB: {path}")
        self.sha256 = sha(data)
        self.bytes = len(data)
        self.doc, self.binary = None, None
        offset = 12
        while offset < len(data):
            size, kind = struct.unpack_from("<II", data, offset)
            chunk = data[offset + 8:offset + 8 + size]
            if kind == 0x4E4F534A:
                self.doc = json.loads(chunk)
            elif kind == 0x004E4942:
                self.binary = chunk
            offset += 8 + size
        if self.doc is None or self.binary is None:
            raise ValueError("GLB JSON/BIN chunk missing")
        self.nodes = self.named(self.doc["nodes"])
        self.materials = self.named(self.doc["materials"])
        self.parents = {}
        for parent in self.doc["nodes"]:
            for child in parent.get("children", []):
                name = self.doc["nodes"][child]["name"]
                if name in self.parents:
                    raise ValueError("Node has multiple parents: " + name)
                self.parents[name] = parent["name"]
        self._arrays = {}
        self._image_data = {}

    @staticmethod
    def named(items):
        result = {}
        for item in items:
            name = item.get("name")
            if not name or name in result:
                raise ValueError("Missing/duplicate GLB name: " + str(name))
            result[name] = item
        return result

    def array(self, index):
        if index in self._arrays:
            return self._arrays[index]
        accessor = self.doc["accessors"][index]
        if "sparse" in accessor or accessor["type"] not in WIDTHS:
            raise ValueError("Unsupported accessor layout; do not silently skip")
        view = self.doc["bufferViews"][accessor["bufferView"]]
        if view.get("buffer", 0) != 0:
            raise ValueError("External buffer unsupported")
        dtype = np.dtype(DTYPES[accessor["componentType"]])
        width = WIDTHS[accessor["type"]]
        offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        stride = view.get("byteStride", dtype.itemsize * width)
        arr = np.ndarray((accessor["count"], width), dtype=dtype, buffer=self.binary,
                         offset=offset, strides=(stride, dtype.itemsize)).copy()
        if accessor.get("normalized", False):
            if dtype.kind == "u":
                arr = arr.astype(np.float64) / np.iinfo(dtype).max
            elif dtype.kind == "i":
                arr = np.maximum(arr.astype(np.float64) / np.iinfo(dtype).max, -1)
        self._arrays[index] = arr
        return arr

    def image(self, index):
        if index in self._image_data:
            return self._image_data[index]
        im = self.doc["images"][index]
        if "bufferView" not in im:
            raise ValueError("Expected embedded image: " + im.get("name", ""))
        view = self.doc["bufferViews"][im["bufferView"]]
        start = view.get("byteOffset", 0)
        blob = self.binary[start:start + view["byteLength"]]
        result = {"name": im.get("name"), "bytes": len(blob), "encoded_sha256": sha(blob), "blob": blob}
        self._image_data[index] = result
        return result

    def texture(self, index):
        tex = self.doc["textures"][index]
        source = tex.get("source")
        if source is None:
            raise ValueError("Unexpected texture extension/source")
        sampler = self.doc.get("samplers", [])[tex["sampler"]] if "sampler" in tex else {}
        return {"image_sha256": self.image(source)["encoded_sha256"],
                "image_name": self.image(source)["name"], "sampler": sampler}

    def material(self, name):
        def normalize(value):
            if isinstance(value, dict):
                result = {}
                for key, child in value.items():
                    if key.endswith("Texture") and isinstance(child, dict) and "index" in child:
                        result[key] = {k: normalize(v) for k, v in child.items() if k != "index"}
                        result[key]["texture_identity"] = self.texture(child["index"])
                    elif key != "name":
                        result[key] = normalize(child)
                return result
            if isinstance(value, list):
                return [normalize(v) for v in value]
            return value
        return normalize(self.materials[name])

    def node_identity(self, name):
        node = self.nodes[name]
        return {"parent": self.parents.get(name),
                "children": sorted(self.doc["nodes"][i]["name"] for i in node.get("children", [])),
                "matrix": node.get("matrix"), "translation": node.get("translation", [0, 0, 0]),
                "rotation": node.get("rotation", [0, 0, 0, 1]), "scale": node.get("scale", [1, 1, 1]),
                "extras": node.get("extras"), "extensions": node.get("extensions")}

    def primitives(self, node):
        return self.doc["meshes"][self.nodes[node]["mesh"]]["primitives"]

    def triangles(self, node):
        return sum(self.array(p["indices"]).size // 3 for p in self.primitives(node))


def compare_mesh(old, new, name, allow_slate_color=False):
    issues = []
    tolerated = []
    a, b = old.primitives(name), new.primitives(name)
    if old.node_identity(name) != new.node_identity(name):
        issues.append("node transform/parent/metadata changed")
    if len(a) != len(b):
        return issues + ["primitive count changed"], tolerated
    for i, (p, q) in enumerate(zip(a, b)):
        pm = old.doc["materials"][p["material"]]["name"]
        qm = new.doc["materials"][q["material"]]["name"]
        om, nm = old.material(pm), new.material(qm)
        if allow_slate_color and pm == qm == "HarborCraft_Terminal_Slate":
            # The replacement is checked independently against its source PNG.
            nm["pbrMetallicRoughness"]["baseColorTexture"] = om["pbrMetallicRoughness"]["baseColorTexture"]
        if pm != qm or om != nm:
            issues.append(f"primitive {i}: material binding/properties changed")
        if p.get("mode", 4) != q.get("mode", 4):
            issues.append(f"primitive {i}: mode changed")
        if set(p["attributes"]) != set(q["attributes"]):
            issues.append(f"primitive {i}: attribute set changed")
        for semantic in sorted(set(p["attributes"]) | set(q["attributes"])):
            if semantic not in p["attributes"] or semantic not in q["attributes"]:
                continue
            x, y = old.array(p["attributes"][semantic]), new.array(q["attributes"][semantic])
            if x.shape != y.shape or not np.array_equal(x, y):
                tangent_ok = (semantic == "TANGENT" and x.shape == y.shape and x.shape[1] == 4
                    and np.isfinite(x).all() and np.isfinite(y).all()
                    and np.array_equal(x[:, 3], y[:, 3])
                    and np.max(np.abs(x[:, :3] - y[:, :3])) <= .00011)
                if tangent_ok:
                    tolerated.append({"primitive": i, "semantic": semantic,
                        "changed_components": int(np.count_nonzero(x != y)),
                        "maximum_absolute_difference": float(np.max(np.abs(x - y))),
                        "allowance": .00011, "handedness_exact": True})
                else:
                    issues.append(f"primitive {i}: {semantic} decoded values changed")
        if not np.array_equal(old.array(p["indices"]), new.array(q["indices"])):
            issues.append(f"primitive {i}: decoded indices changed")
        if p.get("targets") != q.get("targets"):
            issues.append(f"primitive {i}: morph targets changed")
    return issues, tolerated


def triangle_inventory(glb, nodes, attributes):
    """Sorted triangle corner tuples, independent of vertex/index/group ordering.

    Vertex order inside a triangle is ignored for this position/UV preservation
    check. This does not substitute for the strict dynamic mesh comparisons.
    """
    blocks = []
    for node in nodes:
        for prim in glb.primitives(node):
            if prim.get("mode", 4) != 4:
                raise ValueError("Nontriangle primitive in affected group")
            indices = glb.array(prim["indices"]).ravel()
            corners = np.concatenate([glb.array(prim["attributes"][s])[indices] for s in attributes], axis=1)
            # Float32 GLTF round-off from rebaking the same world geometry.
            corners = np.rint(corners * 1e6).astype("<i8")
            corner_bytes = np.ascontiguousarray(corners).view(np.dtype((np.void, corners.shape[1] * 8))).ravel()
            triangles = np.sort(corner_bytes.reshape(-1, 3), axis=1)
            blocks.append(np.ascontiguousarray(triangles).view(np.dtype((np.void, corners.shape[1] * 8 * 3))).ravel())
    rows = np.sort(np.concatenate(blocks))
    return {"triangles": int(rows.size), "sha256": sha(rows.tobytes()), "quantization": "1e-6"}


def surface_correspondence(old, new, old_nodes, new_nodes, semantics):
    """Bidirectional nearest joint attribute correspondence, no triangle ordering.

    Compare POSITION+UV together for apron; UV only for intentionally deformed
    posts/treads. UV-only cannot certify entry positions. Triangle totals must
    also match. Small bins accelerate the search; unmatched boundary points are
    checked against the full opposite cloud, never accepted by bin alone.
    """
    def points(glb, nodes):
        rows = [np.concatenate([glb.array(p["attributes"][s]) for s in semantics], axis=1)
                for node in nodes for p in glb.primitives(node)]
        return np.unique(np.concatenate(rows).astype(np.float64), axis=0)

    x, y = points(old, old_nodes), points(new, new_nodes)
    widths = [3 if s == "POSITION" else 2 for s in semantics]
    tolerance = np.concatenate([np.full(w, 2e-6 if s == "POSITION" else 1e-6)
                                for s, w in zip(semantics, widths)])

    def buckets(values):
        result = {}
        for i, key in enumerate(np.rint(values / 1e-4).astype(np.int64)):
            result.setdefault(tuple(key), []).append(i)
        return result

    bx, by = buckets(x), buckets(y)

    def direction(a, b, ba, bb):
        maximum = np.zeros(a.shape[1])
        pending = []
        for key, ai in ba.items():
            if key not in bb:
                pending.extend(ai)
                continue
            bi = bb[key]
            delta = np.abs(a[ai, None, :] - b[None, bi, :])
            distance = (delta / tolerance).max(axis=2)
            closest = distance.argmin(axis=1)
            for j, row in enumerate(ai):
                if distance[j, closest[j]] <= 1:
                    maximum = np.maximum(maximum, delta[j, closest[j]])
                else:
                    pending.append(row)
        failed = 0
        for start in range(0, len(pending), 8):
            block = a[pending[start:start + 8]]
            delta = np.abs(block[:, None, :] - b[None, :, :])
            distance = (delta / tolerance).max(axis=2)
            closest = distance.argmin(axis=1)
            chosen = delta[np.arange(len(block)), closest]
            maximum = np.maximum(maximum, chosen.max(axis=0))
            failed += int(np.count_nonzero(distance[np.arange(len(block)), closest] > 1))
        return maximum, failed, len(pending)

    forward, fa, pa = direction(x, y, bx, by)
    reverse, fb, pb = direction(y, x, by, bx)
    nt_old = sum(old.triangles(n) for n in old_nodes)
    nt_new = sum(new.triangles(n) for n in new_nodes)
    return {"preserved": fa == fb == 0 and nt_old == nt_new, "attributes": semantics,
            "old_unique_values": len(x), "new_unique_values": len(y),
            "maximum_bidirectional_delta": np.maximum(forward, reverse).tolist(),
            "absolute_tolerance": tolerance.tolist(), "unmatched_old": fa, "unmatched_new": fb,
            "full_cloud_boundary_queries": [pa, pb], "old_triangles": nt_old, "new_triangles": nt_new,
            "limitation": "Joint vertex attribute correspondence; triangle ordering/diagonals intentionally not required"}


def run(old, new, stage="final"):
    report = {"scope": "Read-only GLB audit; no source Blender/GUI/runtime edits; not visual acceptance",
              "baseline": {"path": str(old.path), "sha256": old.sha256, "bytes": old.bytes},
              "candidate": {"path": str(new.path), "sha256": new.sha256, "bytes": new.bytes},
              "checks": [], "rigs": {}, "dynamic_meshes": {}, "untouched_static_meshes": {},
              "original_images": [], "t13": {}, "stage": stage}

    def check(name, condition, details=None):
        report["checks"].append({"name": name, "passed": bool(condition), "details": details})

    check("candidate_changed", old.sha256 != new.sha256)
    expected = {"TerminalRig_" + key for key in RIGS}
    check("exact_ten_rig_nodes", {n for n in new.nodes if n.startswith("TerminalRig_")} == expected)
    for name in sorted(expected):
        good = name in old.nodes and name in new.nodes and old.node_identity(name) == new.node_identity(name)
        report["rigs"][name] = {"unchanged": good, "candidate": new.node_identity(name) if name in new.nodes else None}
    check("rig_parent_children_transforms_unchanged", all(x["unchanged"] for x in report["rigs"].values()))

    dynamic = sorted(n for n in old.nodes if n.startswith("TerminalLive_") and "mesh" in old.nodes[n])
    check("dynamic_node_set_unchanged", set(dynamic) == {n for n in new.nodes if n.startswith("TerminalLive_") and "mesh" in new.nodes[n]})
    static = sorted(n for n in old.nodes if n.startswith("TerminalMesh_") and n not in OLD_GROUPS)
    for names, key in [(dynamic, "dynamic_meshes"), (static, "untouched_static_meshes")]:
        for name in names:
            errors, tolerated = compare_mesh(old, new, name, stage == "final") if name in new.nodes else (["node missing"], [])
            report[key][name] = {"preserved": not errors, "issues": errors, "tolerated_tangent_drift": tolerated}
        check(key + "_surface_and_materials_preserved", all(x["preserved"] for x in report[key].values()))
    check("roof_geometry_uv_normal_roughness_preserved", report["untouched_static_meshes"].get("TerminalMesh_HarborCraft_Terminal_Slate", {}).get("preserved", False))
    check("only_expected_three_nodes_added", set(new.nodes) - set(old.nodes) == set(NEW_GROUPS), sorted(set(new.nodes) - set(old.nodes)))
    check("no_existing_nodes_removed", set(old.nodes) <= set(new.nodes))
    for name in OLD_GROUPS + NEW_GROUPS:
        identity = new.node_identity(name) if name in new.nodes else {}
        check(name + "_static_identity", name in new.nodes and identity.get("parent") is None
              and identity.get("matrix") is None and identity.get("translation") == [0, 0, 0]
              and identity.get("rotation") == [0, 0, 0, 1] and identity.get("scale") == [1, 1, 1])

    flag_names = ["TerminalLive_Flags_HarborCraft_CanvasHem", "TerminalLive_Flags_HarborCraft_WeatheredCanvas"]
    check("both_flag_COLOR_0_preserved", all(n in new.nodes and all("COLOR_0" in p["attributes"] for p in new.primitives(n))
          and report["dynamic_meshes"].get(n, {}).get("preserved", False) for n in flag_names),
          "COLOR_0 is HarborWind pin/phase/mobility data; exact decoded comparison, never treated as tint")

    new_images = {new.image(i)["name"]: new.image(i) for i in range(len(new.doc["images"]))}
    for i in range(len(old.doc["images"])):
        src = old.image(i)
        if stage == "final" and src["name"] == "HarborCraft_NavySlate_albedo":
            report["original_images"].append({"name": src["name"], "allowed_replacement": "HarborCraft_T13_NavySlate_albedo"})
            continue
        dst = new_images.get(src["name"])
        encoded = dst is not None and src["encoded_sha256"] == dst["encoded_sha256"]
        pixel = encoded
        if dst and not encoded:
            with Image.open(io.BytesIO(src["blob"])) as a, Image.open(io.BytesIO(dst["blob"])) as b:
                pixel = a.size == b.size and a.convert("RGBA").tobytes() == b.convert("RGBA").tobytes()
        report["original_images"].append({"name": src["name"], "encoded_identical": encoded,
            "pixels_identical": pixel, "before_sha256": src["encoded_sha256"],
            "after_sha256": dst["encoded_sha256"] if dst else None})
    retained = [i for i in report["original_images"] if "allowed_replacement" not in i]
    check("all_retained_original_image_pixels_identical", all(i["pixels_identical"] for i in retained))
    check("all_retained_original_image_bytes_identical", all(i["encoded_identical"] for i in retained))
    untouched_materials = [n for n in old.materials if not (stage == "final" and n == "HarborCraft_Terminal_Slate")]
    check("all_untouched_original_materials_unchanged", all(n in new.materials and old.material(n) == new.material(n) for n in untouched_materials))

    def source_png_match(identity, required_prefix, packed_roughness=False):
        image_name = identity["texture_identity"]["image_name"]
        src = ROOT / "assets/coast/textures" / (image_name if image_name.endswith(".png") else image_name + ".png")
        result = {"image_name": image_name, "source_png": str(src), "source_exists": src.is_file()}
        source_bytes = src.read_bytes() if src.is_file() else None
        result["source_sha256"] = sha(source_bytes) if source_bytes else None
        result["embedded_sha256"] = identity["texture_identity"]["image_sha256"]
        result["matches_source_bytes"] = source_bytes is not None and result["source_sha256"] == result["embedded_sha256"]
        result["expected_name"] = image_name.startswith(required_prefix)
        if packed_roughness and source_bytes is not None and not result["matches_source_bytes"]:
            embedded = new_images[image_name]["blob"]
            with Image.open(io.BytesIO(embedded)) as a, Image.open(io.BytesIO(source_bytes)) as b:
                x, y = np.array(a.convert("RGBA")), np.array(b.convert("RGBA"))
                same_size = a.size == b.size
                green_exact = same_size and np.array_equal(x[:, :, 1], y[:, :, 1])
                result["gltf_roughness_repacking"] = {
                    "embedded_mode": a.mode, "source_mode": b.mode, "size": list(a.size),
                    "same_size": same_size, "green_channel_exact": green_exact,
                    "green_pixels_compared": int(x.shape[0] * x.shape[1]) if same_size else 0,
                    "red_blue_white": bool(np.all(x[:, :, 0] == 255) and np.all(x[:, :, 2] == 255)),
                    "alpha_opaque": bool(np.all(x[:, :, 3] == 255) and np.all(y[:, :, 3] == 255)),
                    "note": "Not byte-identical: glTF uses G for roughness; other channels are neutral"}
        return result

    if stage == "final":
        slate = new.material("HarborCraft_Terminal_Slate")
        original = old.material("HarborCraft_Terminal_Slate")
        replacement = source_png_match(slate["pbrMetallicRoughness"]["baseColorTexture"], "HarborCraft_T13_NavySlate_albedo")
        report["slate_albedo_replacement"] = replacement
        check("slate_new_albedo_matches_authorized_source_png", replacement["matches_source_bytes"] and replacement["expected_name"])
        check("slate_original_normal_roughness_exact", slate.get("normalTexture") == original.get("normalTexture")
              and slate["pbrMetallicRoughness"].get("metallicRoughnessTexture") == original["pbrMetallicRoughness"].get("metallicRoughnessTexture"))

    for name, (source, lower) in T13.items():
        node = "TerminalMesh_" + name
        entry = {"source_material": source, "node": node}
        report["t13"][name] = entry
        if name not in new.materials or node not in new.nodes:
            check(name + "_present", False)
            continue
        material, original = new.material(name), old.material(source)
        channels = ["baseColorTexture", "metallicRoughnessTexture"]
        pbr, old_pbr = material.get("pbrMetallicRoughness", {}), original.get("pbrMetallicRoughness", {})
        entry["texture_bindings"] = {k: pbr.get(k) for k in channels}
        entry["texture_bindings"]["normalTexture"] = material.get("normalTexture")
        if stage == "final" and name == "HarborCraft_T13_ApronTimber":
            matches = {k: source_png_match(entry["texture_bindings"][k], "HarborCraft_T13_ApronFinal_",
                                          k == "metallicRoughnessTexture")
                       for k in channels + ["normalTexture"]}
            entry["authorized_source_pngs"] = matches
            rough = matches["metallicRoughnessTexture"]
            packing = rough.get("gltf_roughness_repacking", {})
            packing["metallic_factor_zero"] = pbr.get("metallicFactor", 1) == 0
            packing["roughness_factor_one"] = pbr.get("roughnessFactor", 1) == 1
            rough_ok = rough["matches_source_bytes"] or all(packing.get(k, False) for k in
                ["same_size", "green_channel_exact", "red_blue_white", "alpha_opaque", "metallic_factor_zero", "roughness_factor_one"])
            textures_ok = all(v["expected_name"] for v in matches.values()) and rough_ok
            textures_ok &= all(matches[k]["matches_source_bytes"] for k in ["baseColorTexture", "normalTexture"])
            check(name + "_new_base_normal_roughness_preserved", textures_ok)
        else:
            textures_ok = all(k in pbr and pbr[k] == old_pbr.get(k) for k in channels)
            textures_ok &= "normalTexture" in material and material["normalTexture"] == original.get("normalTexture")
            check(name + "_original_base_normal_roughness_bound", textures_ok)
        prims = new.primitives(node)
        check(name + "_primitive_material_binding", all(new.doc["materials"][p["material"]]["name"] == name for p in prims))
        check(name + "_base_vertex_attributes", all({"POSITION", "NORMAL", "TEXCOORD_0", "TANGENT"} <= set(p["attributes"]) for p in prims))
        if lower is not None:
            present = all("COLOR_0" in p["attributes"] for p in prims)
            check(name + "_COLOR_0_present_alongside_base_texture", present and "baseColorTexture" in pbr)
            if present:
                arrays = [new.array(p["attributes"]["COLOR_0"]) for p in prims]
                colors = np.concatenate(arrays)
                if colors.shape[1] == 3:
                    colors = np.column_stack([colors, np.ones(len(colors))])
                minimum, maximum = colors.min(0), colors.max(0)
                entry["COLOR_0"] = {"count": len(colors), "min_rgba": minimum.tolist(), "max_rgba": maximum.tolist(),
                    "component_types": [new.doc["accessors"][p["attributes"]["COLOR_0"]]["componentType"] for p in prims],
                    "source_conservative_min_rgb": lower, "quantization_allowance": .005}
                check(name + "_COLOR_0_source_range", np.isfinite(colors).all() and np.all(minimum[:3] >= np.array(lower) - .005)
                      and np.all(maximum[:3] <= 1.00001) and np.all(np.abs(colors[:, 3] - 1) <= 1e-5), entry["COLOR_0"])
                check(name + "_COLOR_0_nonuniform_wear", np.ptp(colors[:, :3], axis=0).max() > .005)

    for source, added, semantics, label in [
        (OLD_GROUPS[0], NEW_GROUPS[0], ["POSITION", "TEXCOORD_0"], "apron_plus_remaining_crane_position_uv_triangles"),
        (OLD_GROUPS[1], NEW_GROUPS[1], ["TEXCOORD_0"], "entry_plus_remaining_weathered_uv_triangles")]:
        correspondence = surface_correspondence(old, new, [source], [source, added], semantics)
        correspondence["scope"] = "UV-only for entry because post/tread positions intentionally changed" if semantics == ["TEXCOORD_0"] else "position and UV jointly"
        check(label.replace("triangles", "correspondence") + "_preserved", correspondence["preserved"], correspondence)

    report["summary"] = {"baseline_meshes": len(old.doc["meshes"]), "candidate_meshes": len(new.doc["meshes"]),
        "rigs_checked": len(expected), "dynamic_meshes_checked": len(dynamic), "untouched_static_meshes_checked": len(static),
        "original_images_checked": len(report["original_images"]), "passed": sum(c["passed"] for c in report["checks"]),
        "total": len(report["checks"])}
    report["failures"] = [c["name"] for c in report["checks"] if not c["passed"]]
    report["ok"] = not report["failures"]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=CAP / "before/harbor_terminal.glb")
    parser.add_argument("--candidate", type=Path, default=ROOT / "assets/coast/harbor_terminal.glb")
    parser.add_argument("--report", type=Path, default=CAP / "glb_surface_final_audit.json")
    parser.add_argument("--stage", choices=["initial", "final"], default="final",
                        help="final permits authorized Apron PNGs and Slate albedo replacement")
    args = parser.parse_args()
    try:
        report = run(GLB(args.baseline), GLB(args.candidate), args.stage)
    except Exception as error:
        report = {"ok": False, "error": type(error).__name__ + ": " + str(error)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "summary": report.get("summary"), "failures": report.get("failures"),
                      "error": report.get("error"), "report": str(args.report)}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
