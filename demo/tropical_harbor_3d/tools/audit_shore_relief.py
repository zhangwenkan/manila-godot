"""Read exported shore assets and write a validation report; never edits source assets."""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import struct
import sys


ART = Path(__file__).resolve().parents[1]
EXPECTED_ASSETS = {
    "boat", "cargo_ginseng", "cargo_jade", "cargo_nutmeg", "cargo_silk",
    "coast", "town", "cargo_port", "foliage", "ocean", "rocks", "terrain",
}
UPDATED_ASSETS = {"terrain", "coast", "town", "foliage", "rocks"}
RELIEF_MATERIALS = {"Ref_R21_Turf", "Ref_R21_TurfRoot", "Ref_R21_BankSoil"}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_glb(path):
    """Use the same primitive checks as audit_reference_assets, plus image bytes."""
    blob = path.read_bytes()
    assert len(blob) >= 20 and blob[:4] == b"glTF", f"Invalid GLB: {path.name}"
    version, length = struct.unpack_from("<II", blob, 4)
    assert version == 2 and length == len(blob), f"Invalid GLB header: {path.name}"
    chunks = {}
    offset = 12
    while offset < len(blob):
        size, kind = struct.unpack_from("<II", blob, offset)
        offset += 8
        assert offset + size <= len(blob), f"Truncated chunk: {path.name}"
        chunks[kind] = blob[offset:offset + size]
        offset += size
    doc = json.loads(chunks[0x4E4F534A])
    binary = chunks.get(0x004E4942, b"")
    assert doc.get("meshes") and doc.get("nodes"), f"Empty geometry: {path.name}"
    triangles = 0
    for mesh in doc["meshes"]:
        for primitive in mesh["primitives"]:
            attributes = primitive["attributes"]
            assert {"POSITION", "NORMAL", "TEXCOORD_0"} <= attributes.keys(), path.name
            count = doc["accessors"][attributes["POSITION"]]["count"]
            assert count > 0 and primitive.get("mode", 4) == 4, path.name
            index_count = doc["accessors"][primitive["indices"]]["count"]
            assert index_count % 3 == 0, path.name
            triangles += index_count // 3
    images = []
    for image in doc.get("images", []):
        assert "bufferView" in image, f"Image is not embedded: {path.name}"
        view = doc["bufferViews"][image["bufferView"]]
        assert view.get("buffer", 0) == 0, path.name
        start = view.get("byteOffset", 0)
        end = start + view["byteLength"]
        assert 0 <= start < end <= len(binary), path.name
        images.append(sha256(binary[start:end]))
    return {
        "file": path.name,
        "sha256": sha256(blob),
        "bytes": len(blob),
        "meshes": len(doc["meshes"]),
        "triangles": triangles,
        "materials": len(doc.get("materials", [])),
        "material_names": [item.get("name", "") for item in doc.get("materials", [])],
        "images": len(images),
        "unique_image_hashes": sorted(set(images)),
    }


def height_audit(path):
    if not path.is_file():
        return {"present": False, "valid": False, "reason": "Height export not present"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return {"present": True, "valid": False, "reason": str(error)}
    if not isinstance(data, dict):
        return {"present": True, "valid": False, "reason": "Height export must be an object"}
    expected = {"d0": 0, "z0": 0, "step": .25, "columns": 145, "rows": 329}
    metadata_matches = all(data.get(key) == value for key, value in expected.items())
    heights = data.get("heights")
    count = len(heights) if isinstance(heights, list) else 0
    finite = isinstance(heights, list) and all(
        isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        for value in heights
    )
    valid = metadata_matches and count == 145 * 329 and finite
    return {
        "present": True,
        "valid": valid,
        "sha256": sha256(path.read_bytes()),
        "metadata": {key: data.get(key) for key in expected},
        "metadata_matches": metadata_matches,
        "samples": count,
        "expected_samples": 145 * 329,
        "all_finite_numbers": finite,
        "minimum": min(heights) if finite and count else None,
        "maximum": max(heights) if finite and count else None,
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ART / "captures/shore_relief_20261120")
    parser.add_argument("--phase", choices=["pending-export", "final"], default="pending-export",
                        help="Use final only after every Blender export has completed.")
    args = parser.parse_args()
    before = args.output / "before"
    errors = []
    assets = []
    for path in sorted((ART / "assets/reference").glob("*.glb")):
        try:
            current = read_glb(path)
            baseline = before / path.name
            if baseline.is_file():
                old = read_glb(baseline)
                missing = set(old["unique_image_hashes"]) - set(current["unique_image_hashes"])
                current["baseline"] = {
                    "sha256": old["sha256"],
                    "changed": old["sha256"] != current["sha256"],
                    "images": old["images"],
                    "unique_images": len(old["unique_image_hashes"]),
                    "all_original_images_preserved": not missing,
                    "missing_image_hashes": sorted(missing),
                }
                if missing:
                    errors.append(f"Original embedded image content missing: {path.name}")
            assets.append(current)
        except (AssertionError, ValueError, KeyError, struct.error) as error:
            errors.append(f"{path.name}: {error}")
    by_name = {Path(asset["file"]).stem: asset for asset in assets}
    if set(by_name) != EXPECTED_ASSETS:
        errors.append("Runtime GLB set does not match the reference harbor assembly")
    preserved = {}
    for filename, relative in {
        "fleet_camera.gd": "fleet/fleet_camera.gd",
        "harbor_route.gd": "fleet/harbor_route.gd",
        "cargo_port.glb": "assets/reference/cargo_port.glb",
    }.items():
        baseline = before / filename
        current = ART / relative
        if not baseline.is_file() or not current.is_file():
            errors.append(f"Missing file for preservation check: {filename}")
            preserved[filename] = {"equal": False, "missing": True}
            continue
        old_hash, current_hash = sha256(baseline.read_bytes()), sha256(current.read_bytes())
        preserved[filename] = {"equal": old_hash == current_hash,
                               "before_sha256": old_hash, "current_sha256": current_hash}
        if old_hash != current_hash:
            errors.append(f"Preserved file changed: {filename}")
    height = height_audit(ART / "assets/reference/shore_relief_height.json")
    terrain_materials = set(by_name.get("terrain", {}).get("material_names", []))
    missing_materials = sorted(RELIEF_MATERIALS - terrain_materials)
    unchanged_exports = sorted(name for name in UPDATED_ASSETS
                               if not by_name.get(name, {}).get("baseline", {}).get("changed", False))
    blockers = []
    if not height["valid"]:
        blockers.append("New height export is missing or invalid")
    if missing_materials:
        blockers.append("Terrain export lacks new turf/root/soil materials")
    if unchanged_exports:
        blockers.append("Expected updated exports still equal the before backup")
    if args.phase == "final":
        errors.extend(blockers)
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": args.phase,
        "status": ("pending_export" if args.phase == "pending-export"
                   else "passed" if not errors else "failed"),
        "is_final": args.phase == "final",
        "passed": args.phase == "final" and not errors,
        "visual_accepted": False,
        "assets": assets,
        "preserved_files": preserved,
        "height_grid": height,
        "missing_relief_materials": missing_materials,
        "expected_exports_still_unchanged": unchanged_exports,
        "export_readiness_issues": blockers,
        "errors": errors,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / "asset_validation.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "assets": len(assets),
                      "height_valid": height["valid"], "pending": blockers,
                      "errors": errors, "report": str(target)}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
