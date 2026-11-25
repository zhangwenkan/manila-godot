"""Read-only review of this round's bounded runtime diff; never runs Godot."""
from pathlib import Path
import hashlib
import difflib
import json


ROOT = Path(__file__).resolve().parents[2] / "demo/tropical_harbor_3d"
LOG = ROOT / "captures/lighthouse_integration_20261126"
EXPECTED_CHANGES = {
    "environment/reference_coast.gd",
    "tools/reference_rebuild_review.gd",
    "tools/capture_art.py",
}
PROTECTED = {
    "fleet_harbor.gd", "fleet/fleet_camera.gd", "fleet/harbor_route.gd",
    "fleet/fleet_state.gd", "fleet_harbor.tscn", "materials/reference_water.gdshader",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run():
    manifest = json.loads((LOG / "runtime_before_manifest.json").read_text(encoding="utf8"))
    records, diffs, changed = [], [], set()
    for item in manifest:
        relative = item["relative"]
        if relative not in EXPECTED_CHANGES | PROTECTED:
            continue
        before = (LOG / "runtime_before" / relative).read_bytes()
        current = (ROOT / relative).read_bytes()
        records.append({"relative": relative, "snapshot_verified": sha(before) == item["sha256"],
                        "before_sha256": item["sha256"], "after_sha256": sha(current),
                        "unchanged": sha(current) == item["sha256"]})
        if current != before:
            changed.add(relative)
            diffs.extend(difflib.unified_diff(before.decode("utf8").splitlines(True),
                                            current.decode("utf8").splitlines(True),
                                            fromfile="before/" + relative, tofile=relative))
    coast = (ROOT / "environment/reference_coast.gd").read_text(encoding="utf8")
    original = (LOG / "runtime_before/environment/reference_coast.gd").read_text(encoding="utf8")
    additions = [line[1:] for line in difflib.ndiff(original.splitlines(), coast.splitlines()) if line.startswith("+ ")]
    new_fixture = ROOT / "tools/reference_lighthouse_review.gd"
    environment_snapshot = json.loads((LOG / "before_manifest.json").read_text(encoding="utf8"))
    environment = next(item for item in environment_snapshot if item["relative"] == "environment/reference_environment.gd")
    checks = {
        "all_nine_round_snapshots_verified": len(records) == 9 and all(row["snapshot_verified"] for row in records),
        "only_three_allowed_existing_files_changed": changed == EXPECTED_CHANGES,
        "six_protected_runtime_files_unchanged": all(row["unchanged"] for row in records if row["relative"] in PROTECTED),
        "environment_unchanged": sha((ROOT / environment["relative"]).read_bytes()) == environment["sha256"],
        "no_light_animation_or_ship_mutation_in_coast_additions": not any(
            token in line for token in ("Light3D", "create_tween", "AnimationPlayer", ".roll(", "place_on_route(", "sail_route(", "camera_override", "emit_signal")
            for line in additions),
        "world_asset_single_load_entry": coast.count('"lighthouse",') == 1,
        "new_fixture_present": new_fixture.is_file(),
    }
    report = {
        "passed": all(checks.values()), "checks": checks, "records": records,
        "new_fixture_sha256": sha(new_fixture.read_bytes()),
        "reviewed_behavior": [
            "ReferenceCoast loads the world-baked asset once and retains the existing layer-4 static mesh collision path.",
            "Only Assembly/Emitter node lookup is exposed; consumers in this round are review code only.",
            "The two existing review entry files add an explicitly selected lighthouse inspection mode.",
            "New review fixture performs isolated diagnostic images, normal-camera samples, temporary collision-mask checks and existing actual arrival-case calls.",
        ],
        "runtime_test_pass_claimed": False,
        "limits": [
            "This report audits the bounded source diff and file hashes; actual Godot captures and physics coverage remain separate.",
            "The camera audit uses synchronous ship progress and sampled primary subjects, not all unequal-progress and camera-smoothing combinations.",
            "No visual acceptance or performance improvement follows from a source review.",
        ],
    }
    (LOG / "independent_runtime_review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    (LOG / "independent_runtime_diff.patch").write_text("".join(diffs), encoding="utf8")
    print(json.dumps({"passed": report["passed"], "checks": checks, "changed": sorted(changed)}))
    return report


if __name__ == "__main__":
    run()
