"""Read-only current-round audit; define then call through verified GUI MCP.

No source mutation, save, export or historical production-script execution.
"""
from pathlib import Path
import hashlib
import json
import os
import numpy as np


def audit_cliff25(expected_pid, check_export=False, allow_town_props=False):
    import bpy
    root = Path(bpy.data.filepath).parent.parent
    log = root / "captures/cliff_contacts_20261125"
    read = lambda name: json.loads((log / name).read_text(encoding="utf-8-sig"))
    spec = read("audit_spec.json")
    assert not bpy.app.background
    assert os.getpid() == expected_pid == spec["session"]["pid"]
    assert bpy.types.blendermcp_server.port == spec["session"]["port"]
    assert Path(bpy.data.filepath).resolve() == Path(spec["session"]["source"]).resolve()
    sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    assert sha(log / "design.json") == spec["provenance"]["design_sha256"], "Audit design changed; prepare current spec explicitly"
    assert sha(log / "baseline.npz") == spec["provenance"]["baseline_sha256"], "Immutable terrain baseline changed"
    if allow_town_props:
        spec["preserved_hashes"] = [r for r in spec["preserved_hashes"] if Path(r["relative"]).name != "town.glb"]
    if check_export:
        spec["exported_terrain_glb"] = "assets/reference/terrain.glb"
    namespace = {}
    exec(compile((root / "source/structure23_audit.py").read_text(encoding="utf-8-sig"),
                 "structure23_audit.py", "exec"), namespace)
    structural = namespace["audit_structure23"](spec, log / "structure_audit.json")
    dirty_before = bool(bpy.data.is_dirty)
    mesh = bpy.data.objects["C25_ContourBuiltCoast"].data
    current = np.empty((len(mesh.vertices), 3), np.float32)
    mesh.vertices.foreach_get("co", current.ravel())
    loops = np.empty(len(mesh.loops), np.int32)
    mesh.loops.foreach_get("vertex_index", loops)
    current_tri = loops.reshape(-1, 3)
    baseline = np.load(log / "baseline.npz")
    lock = np.load(log / "protected_terrain_faces.npz")
    same_topology = np.array_equal(current_tri, baseline["triangles"])
    failures = []
    protected_error = None
    changed_count = None
    changed_ids = []
    if current.shape != baseline["positions"].shape or not same_topology:
        failures.append("Retained full-face protection requires baseline terrain vertex/triangle topology")
    else:
        ids = lock["vertex_ids"]
        error = np.max(abs(current[ids].astype(float) - baseline["positions"][ids]), axis=1)
        protected_error = float(error.max(initial=0))
        changed_count = int((error > .00002).sum())
        changed_ids = ids[error > .00002][:32].tolist()
        if changed_count:
            failures.append("Terrain vertices of full-width roads/courts/junction faces changed beyond 20um")
    if bool(bpy.data.is_dirty) != dirty_before:
        failures.append("Read-only protection audit changed dirty state")
    report = {"read_only": True, "visual_accepted": False, "pid": expected_pid,
              "technical_pass": structural["technical_pass"] is True and not failures,
              "structure_report": "structure_audit.json", "structure_pass": structural["technical_pass"],
              "structure_failures": structural["failures"], "structure_incomplete": structural["incomplete"],
              "road_court_junction_full_face_lock": {"same_topology": same_topology,
                  "protected_faces": len(lock["face_ids"]), "protected_vertices": len(lock["vertex_ids"]),
                  "maximum_coordinate_change_m": protected_error, "changed_vertices_over_20um": changed_count,
                  "first_changed_vertex_ids": changed_ids},
              "failures": failures, "dirty_before": dirty_before, "dirty_after": bool(bpy.data.is_dirty),
              "export_checked": bool(check_export), "town_prop_changes_explicitly_allowed": bool(allow_town_props)}
    (log / "cliff_structure_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return report
