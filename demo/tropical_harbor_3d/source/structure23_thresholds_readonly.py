"""Read actual live source step vertices and top-edge candidates; no scene edits.

Load/exec only defines the function. Call inspect_structure23_thresholds(pid).
The only optional write is its JSON evidence. Candidates remain proposals until
their outward direction is checked against the approach design.
"""
import json
import os
from pathlib import Path

import numpy as np


def inspect_structure23_thresholds(expected_pid, output_path=None):
    import bpy
    if bpy.app.background or os.getpid()!=expected_pid:
        raise RuntimeError("Owned GUI Blender PID does not match")
    if Path(bpy.data.filepath).name!="harbor_shore_control_mcp.blend":
        raise RuntimeError("Wrong source blend")
    root=Path(bpy.data.filepath).parent.parent
    log=root/"captures/terrain_structure_20261123"
    if json.loads((log/"session_start.json").read_text(encoding="utf8"))["pid"]!=expected_pid:
        raise RuntimeError("Current round session does not match")
    names=["Town_Step"]+["Town_Step.%03d"%i for i in range(1,9)]
    names += ["Hut_EntrySteps.043","Hut_EntrySteps.051"]
    rows=[]
    for name in names:
        obj=bpy.data.objects.get(name)
        if obj is None or obj.type!="MESH":raise RuntimeError("Missing actual entry mesh "+name)
        raw=np.empty((len(obj.data.vertices),3),np.float32);obj.data.vertices.foreach_get("co",raw.ravel())
        matrix=np.asarray(obj.matrix_world,float);world=raw.astype(float)@matrix[:3,:3].T+matrix[:3,3]
        godot=world[:,[0,2,1]].copy();godot[:,2]*=-1
        top=float(world[:,2].max());top_faces=[];edges={}
        for poly in obj.data.polygons:
            ids=list(poly.vertices);p=world[ids]
            if np.max(abs(p[:,2]-top))>.00002:continue
            top_faces.append(ids)
            for a,b in zip(ids,ids[1:]+ids[:1]):
                key=tuple(sorted((a,b)));edges[key]=edges.get(key,0)+1
        centre=godot[:,[0,2]].mean(0);candidates=[]
        for (a,b),count in edges.items():
            if count!=1:continue
            pair=godot[[a,b]];xz=pair[:,[0,2]];d=xz[1]-xz[0];length=float(np.linalg.norm(d))
            if length<1e-8:continue
            outside=np.array([-d[1],d[0]])/length
            if np.dot(outside,xz.mean(0)-centre)<0:outside*=-1
            candidates.append({"threshold_vertex_indices":[a,b],"endpoints_godot":pair.tolist(),
                "length_m":length,"outside_direction_xz":outside.tolist()})
        candidates.sort(key=lambda c:c["outside_direction_xz"][0])
        rows.append({"object":name,"town_building":obj.get("town_building"),"source_vertex_count":len(raw),
            "vertices_godot":[{"index":i,"position":v.tolist()} for i,v in enumerate(godot)],
            "source_top_faces":top_faces,"top_boundary_edge_candidates":candidates,
            "seaward_candidate":candidates[0] if candidates and candidates[0]["outside_direction_xz"][0]<-.7 else None,
            "height_bounds_m":[float(world[:,2].min()),top],
            "active_modifiers":[{"name":m.name,"type":m.type} for m in obj.modifiers if m.show_viewport],
            "note":"Candidate source edge is indexed in the live mesh; match direction to the designed approach before adopting."})
    report={"pid":os.getpid(),"source":bpy.data.filepath,"readonly":True,"steps":rows,"visual_accepted":False}
    path=Path(output_path) if output_path else log/"threshold_edges.json"
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf8")
    print(json.dumps({"output":str(path),"steps":len(rows),"with_candidate":sum(r["seaward_candidate"] is not None for r in rows)}))
    return report
