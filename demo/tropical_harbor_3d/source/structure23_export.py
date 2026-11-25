"""Explicit final structure23 export through the owned GUI Blender MCP.

Defines export_structure23 only; loading the file does not export or mutate.
Call export_structure23(expected_pid=12164, changed_collections=[...]) once the
new structure/material/grounding work is ready. The passed collection names
must describe actual mesh/material edits not detectable from saved object
matrix/bounds/count metadata. Moves, additions and removals are auto-detected.
Supported collections: Reference_Coast, Reference_Foliage, Reference_Rocks,
Reference_GroundCover, plus Reference_Town only when explicitly declared.
Town props may move, but all nine original floor meshes and transforms are
checked before/after export. Terrain is compared with this round's raw NPZ.

No historical production script is imported or executed. Export copies are
evaluated and joined by material tuple/leaf category. All copies are discarded;
source material links, selection and visibility are restored before save.

After a completed first export, only_collections=[...] limits subsequent runs
to those collections. Terrain is skipped in that mode unless force_terrain is
true; only_collections=[] plus force_terrain=True exports terrain alone. The
caller must declare actual newly edited collections; original-round metadata
cannot distinguish every internal edit. Skipped runtime files are hash-locked
to the previous completed export. export_progress.json records live phases.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from pathlib import Path

import numpy as np


def _sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):h.update(block)
    return h.hexdigest()


def _object_metadata(obj):
    matrix=np.asarray(obj.matrix_world,float)
    box=np.asarray(obj.bound_box,float)@matrix[:3,:3].T+matrix[:3,3]
    return {"matrix":matrix.tolist(),"bounds":[box.min(0).tolist(),box.max(0).tolist()],"vertices":len(obj.data.vertices)}


def export_structure23(expected_pid, changed_collections=(), log_path=None,
                       force_terrain=False, terrain_object="C25_ContourBuiltCoast",
                       only_collections=None):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    if bpy.app.background or os.getpid()!=expected_pid:
        raise RuntimeError("Owned GUI Blender PID does not match")
    root=Path(bpy.data.filepath).parent.parent
    if Path(bpy.data.filepath).name!="harbor_shore_control_mcp.blend":
        raise RuntimeError("Wrong source blend")
    log=Path(log_path) if log_path else root/"captures/terrain_structure_20261123"
    if not log.is_absolute():log=root/log
    if json.loads((log/"session_start.json").read_text(encoding="utf-8"))["pid"]!=expected_pid:
        raise RuntimeError("Current round session does not match")
    out=root/"assets/reference";started=time.perf_counter()
    mapping={"Reference_Coast":"coast.glb","Reference_Foliage":"foliage.glb",
             "Reference_Rocks":"rocks.glb","Reference_GroundCover":"ground_cover.glb",
             "Reference_Town":"town.glb"}
    declared=set(changed_collections)
    if not declared<=set(mapping):raise ValueError("Unsupported explicitly changed collections: "+str(declared-set(mapping)))
    limited=only_collections is not None
    scope=set(mapping) if not limited else set(only_collections)
    if not scope<=set(mapping):raise ValueError("Unsupported only_collections: "+str(scope-set(mapping)))
    if limited and not declared<=scope:raise ValueError("Explicitly changed collections must be inside only_collections")
    before=json.loads((log/"objects_before.json").read_text(encoding="utf-8"))
    known={row["name"]:row for row in before}
    manifest=json.loads((log/"before_manifest.json").read_text(encoding="utf-8"))
    expected_runtime={Path(row["relative"]).name:row["sha256"] for row in manifest
                      if Path(row["relative"]).parent.as_posix()=="assets/reference"}
    previous=None
    if limited:
        previous=json.loads((log/"export.json").read_text(encoding="utf-8"))
        if previous.get("status")!="completed" or not previous.get("source_saved"):
            raise RuntimeError("Scoped export requires a completed, saved first export")
        if Path(previous["source"])!=Path(bpy.data.filepath):raise RuntimeError("Previous export belongs to another source")
        expected_runtime.update(previous.get("runtime_asset_hashes",{}))
        expected_runtime.update({row["file"]:row["sha256"] for row in previous["exported"]})
        if not previous.get("runtime_asset_hashes"):
            required={"terrain.glb",*mapping.values()}
            if not required<=set(expected_runtime):raise RuntimeError("Previous export lacks a complete runtime hash baseline")
        for filename in ({"terrain.glb","shore_relief_height.json",*mapping.values()}):
            digest=expected_runtime.get(filename)
            if digest and _sha256(out/filename)!=digest.lower():
                raise RuntimeError("Runtime asset changed since previous completed export: "+filename)
    # The recorded absolute paths contain literal unicode escapes; relative is authoritative.
    fixed_names={"town.glb","cargo_port.glb","boat.glb","cargo_ginseng.glb","cargo_jade.glb",
                 "cargo_nutmeg.glb","cargo_silk.glb","ocean.glb","ground_rock.glb"}
    if "Reference_Town" in declared:fixed_names.remove("town.glb")
    elif limited:fixed_names.remove("town.glb")
    fixed=[row for row in manifest if Path(row["relative"]).name in fixed_names]
    if len(fixed)!=len(fixed_names):raise RuntimeError("Preserved asset manifest incomplete")
    for row in fixed:
        if _sha256(root/row["relative"])!=row["sha256"].lower():
            raise RuntimeError("Preserved asset changed before export: "+row["relative"])
    if limited:
        for cname in set(mapping)-scope:
            filename=mapping[cname]
            fixed.append({"relative":"assets/reference/"+filename,"sha256":expected_runtime[filename]})
        if not force_terrain:
            for filename in ("terrain.glb","shore_relief_height.json"):
                if filename not in expected_runtime:raise RuntimeError("Previous export lacks hash for skipped "+filename)
                fixed.append({"relative":"assets/reference/"+filename,"sha256":expected_runtime[filename]})
    foundations=json.loads((root/"captures/rock_path_sample_20261123/foundations.json").read_text(encoding="utf-8"))
    def floor_checks():
        expected_names={row["object"] for row in foundations}
        current_names={obj.name for obj in bpy.data.collections["Reference_Town"].all_objects
                       if obj.type=="MESH" and obj.name.startswith("Town_Floor")}
        if len(expected_names)!=9 or current_names!=expected_names:
            raise RuntimeError("Nine original Town floors are not preserved as a set")
        results=[]
        for row in foundations:
            obj=bpy.data.objects[row["object"]];matrix=np.asarray(obj.matrix_world,float)
            coords=np.empty((len(obj.data.vertices),3),np.float32);obj.data.vertices.foreach_get("co",coords.ravel())
            current=coords.astype(float)@matrix[:3,:3].T+matrix[:3,3];prior=np.asarray(row["corners"],float)
            if current.shape!=prior.shape:raise RuntimeError("Town floor topology changed: "+obj.name)
            error=float(np.max(abs(current-prior)))
            saved=known.get(obj.name)
            if saved is None:raise RuntimeError("Town floor absent from current-round transform snapshot: "+obj.name)
            transform_error=float(np.max(abs(matrix-np.asarray(saved["matrix"],float))))
            if error>.00002 or transform_error>1e-7:raise RuntimeError("Town floor geometry/pose changed: "+obj.name)
            results.append({"object":obj.name,"world_vertex_max_error_m":error,"matrix_max_error":transform_error})
        return results
    floors_before=floor_checks()
    collection_changes={}
    for cname in mapping:
        if cname not in scope:continue
        source=bpy.data.collections.get(cname)
        if source is None:raise RuntimeError("Missing export collection "+cname)
        current={o.name:o for o in source.objects if o.type=="MESH"}
        old={r["name"] for r in before if cname in r["collections"]}
        changed=[]
        for name,obj in current.items():
            if name not in old:changed.append({"object":name,"kind":"added"});continue
            a,b=_object_metadata(obj),known[name]
            if (a["vertices"]!=b["vertices"] or np.max(abs(np.asarray(a["matrix"])-b["matrix"]))>1e-6
                    or np.max(abs(np.asarray(a["bounds"])-b["bounds"]))>1e-6):
                changed.append({"object":name,"kind":"matrix_bounds_or_count"})
        changed.extend({"object":name,"kind":"removed_from_collection"} for name in sorted(old-set(current)))
        if cname=="Reference_Town" and cname not in declared:
            if changed:raise RuntimeError("Town source changes require explicit Reference_Town declaration after prop review")
            continue
        if changed or cname in declared:
            collection_changes[cname]={"detected_changes":changed,"explicit_internal_mesh_or_material_change":cname in declared}
    terrain=bpy.data.objects[terrain_object]
    if terrain.mode!="OBJECT" or any(m.show_viewport for m in terrain.modifiers):
        raise RuntimeError("Terrain must be unmodified raw mesh in Object mode")
    if np.max(abs(np.asarray(terrain.matrix_world)-np.eye(4)))>1e-8:
        raise RuntimeError("Terrain transform must remain identity")
    mesh=terrain.data;p=np.empty((len(mesh.vertices),3),np.float32);mesh.vertices.foreach_get("co",p.ravel())
    loops=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get("vertex_index",loops)
    sizes=np.empty(len(mesh.polygons),np.int32);mesh.polygons.foreach_get("loop_total",sizes)
    if not np.all(sizes==3):raise RuntimeError("Terrain export expects explicit triangles")
    with np.load(log/"baseline.npz") as data:
        terrain_changed=not(np.array_equal(data["positions"],p) and np.array_equal(data["triangles"],loops.reshape(-1,3)))
    report={"status":"running","pid":os.getpid(),"source":bpy.data.filepath,"visual_accepted":False,
            "terrain_geometry_changed":terrain_changed,"force_terrain_declared":bool(force_terrain),
            "collections":collection_changes,"exported":[],"source_saved":False,
            "town_export_explicitly_allowed":"Reference_Town" in declared,"floors_before":floors_before,
            "only_collections":sorted(scope) if limited else None,
            "terrain_export_requested":bool(force_terrain or (not limited and terrain_changed)),
            "stages":[]}
    def progress(phase,collection=None,**detail):
        event={"phase":phase,"collection":collection,"elapsed_seconds":time.perf_counter()-started,
               "time_unix":time.time(),**detail}
        report["current_stage"]=event
        if not detail.get("heartbeat"):report["stages"].append(event)
        data={"status":report["status"],"pid":os.getpid(),"source":bpy.data.filepath,
              "only_collections":report["only_collections"],"current_stage":event,
              "stages":report["stages"],"source_saved":report["source_saved"],
              "exported":report["exported"]}
        temporary=log/"export_progress.tmp.json";temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        temporary.replace(log/"export_progress.json")
    progress("preflight_complete")
    selected=list(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
    object_hide={o.name:o.hide_get() for o in selected+[terrain]}
    collection_hide={c:bpy.data.collections[c].hide_viewport for c in mapping}
    staged=[];preview_socket=None;principled=None;land_material=None
    temporary_collection_name="STRUCTURE23_EXPORT_TEMP"
    if bpy.data.collections.get(temporary_collection_name):raise RuntimeError("Previous temporary export collection exists")
    # Blender's bulk-ID API avoids a full user remap for every orphan mesh.
    # Require it before creating any export copies, including on another build.
    batch_remove=getattr(bpy.data,"batch_remove",None)
    if not callable(batch_remove):raise RuntimeError("This Blender build lacks bpy.data.batch_remove; export not started")

    def export_selected(path,vertex_colors=True):
        opts=dict(filepath=str(path),export_format="GLB",use_selection=True,export_apply=True,
                  export_yup=True,export_texcoords=True,export_normals=True,export_materials="EXPORT")
        rna=bpy.ops.export_scene.gltf.get_rna_type().properties
        if "export_all_uvs" in rna:opts["export_all_uvs"]=True
        if vertex_colors and "export_vertex_color" in rna:opts["export_vertex_color"]="ACTIVE"
        bpy.ops.export_scene.gltf(**opts)
        if not path.is_file() or path.stat().st_size<100:raise RuntimeError("Export did not create valid-sized GLB")

    def export_collection(cname,path):
        source=bpy.data.collections[cname];source.hide_viewport=False
        progress("evaluate_source",cname)
        bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
        # Do not link temporary objects into the evaluated scene while still
        # requesting source evaluated meshes. Take the entire immutable mesh
        # snapshot first, then link the copies in a separate phase.
        source_objects=[obj for obj in source.objects if obj.type=="MESH"]
        evaluated=[(obj,obj.evaluated_get(dg),obj.matrix_world.copy()) for obj in source_objects]
        created_mesh_ids={};groups={};objects_count=0;snapshots=[];temp=None
        phase_started=time.perf_counter();timings={}
        try:
            progress("snapshot_evaluated_meshes",cname,total=len(evaluated))
            for i,(obj,evaluated_obj,matrix) in enumerate(evaluated):
                data=bpy.data.meshes.new_from_object(evaluated_obj,preserve_all_data_layers=True,depsgraph=dg)
                created_mesh_ids[data.name]=data.as_pointer()
                category="Leaf" if any(token in obj.name for token in ("Crown","Frond","Tuft","Coconut")) else "Solid"
                key=(category,tuple(m.name if m else "None" for m in data.materials))
                snapshots.append((obj.name,data,matrix,key))
                if (i+1)%100==0:progress("snapshot_evaluated_meshes",cname,completed=i+1,total=len(evaluated),heartbeat=True)
            timings["snapshot_evaluated_meshes_seconds"]=time.perf_counter()-phase_started
            evaluated.clear();dg=None
            progress("link_export_copies",cname,total=len(snapshots));phase_started=time.perf_counter()
            temp=bpy.data.collections.new(temporary_collection_name);bpy.context.scene.collection.children.link(temp)
            for name,data,matrix,key in snapshots:
                copy=bpy.data.objects.new(name+"_structure23_export",data);temp.objects.link(copy)
                copy.matrix_world=matrix;objects_count+=1
                groups.setdefault(key,[]).append(copy)
            if not groups:raise RuntimeError("Export collection has no meshes: "+cname)
            bpy.context.view_layer.update()
            timings["link_export_copies_seconds"]=time.perf_counter()-phase_started
            progress("join_material_groups",cname,total=len(groups));phase_started=time.perf_counter()
            result=[]
            for i,((category,materials),objects) in enumerate(groups.items()):
                bpy.ops.object.select_all(action="DESELECT")
                for obj in objects:obj.select_set(True)
                bpy.context.view_layer.objects.active=objects[0]
                if len(objects)>1:bpy.ops.object.join()
                joined=objects[0];joined.name=category+"_"+(materials[0] if materials else "Untextured");result.append(joined)
                progress("join_material_groups",cname,completed=i+1,total=len(groups),heartbeat=True)
            timings["join_material_groups_seconds"]=time.perf_counter()-phase_started
            bpy.ops.object.select_all(action="DESELECT")
            for obj in result:obj.select_set(True)
            bpy.context.view_layer.objects.active=result[0]
            triangles=sum(sum(len(poly.vertices)-2 for poly in obj.data.polygons) for obj in result)
            progress("write_glb",cname,triangles=triangles,mesh_groups=len(result));phase_started=time.perf_counter()
            export_selected(path)
            timings["write_glb_seconds"]=time.perf_counter()-phase_started
            progress("glb_staged",cname,path=str(path),bytes=path.stat().st_size,timings=timings)
            return {"source_mesh_objects":objects_count,"export_mesh_groups":len(result),"evaluated_triangles":triangles,"timings":timings}
        finally:
            phase_started=time.perf_counter()
            progress("cleanup_export_copies",cname,created_meshes=len(created_mesh_ids))
            try:
                # Only IDs allocated by this export may enter the removal set.
                # Joining removes some objects but leaves many unused meshes;
                # resolve names afresh instead of dereferencing deleted RNA.
                temp_objects=list(temp.objects) if temp is not None else []
                temp_mesh_users={}
                for obj in temp_objects:
                    if obj.type!="MESH" or created_mesh_ids.get(obj.data.name)!=obj.data.as_pointer():
                        raise RuntimeError("Unexpected non-export data in temporary collection")
                    ptr=obj.data.as_pointer();temp_mesh_users[ptr]=temp_mesh_users.get(ptr,0)+1
                meshes=[]
                for name,pointer in created_mesh_ids.items():
                    data=bpy.data.meshes.get(name)
                    if data is None:continue
                    if data.as_pointer()!=pointer:
                        raise RuntimeError("Temporary mesh ID changed identity: "+name)
                    if data.users!=temp_mesh_users.get(pointer,0):
                        raise RuntimeError("Temporary mesh has an unexpected user; refusing removal: "+name)
                    meshes.append(data)
                ids=[*temp_objects,*meshes]
                if temp is not None:ids.append(temp)
                if ids:batch_remove(ids=ids)
                residual_meshes=[name for name in created_mesh_ids if bpy.data.meshes.get(name) is not None]
                if bpy.data.collections.get(temporary_collection_name) or residual_meshes:
                    raise RuntimeError("Temporary export IDs remain after batch cleanup: "+str(residual_meshes[:12]))
                timings["cleanup_export_copies_seconds"]=time.perf_counter()-phase_started
                timings["cleanup_removed_objects"]=len(temp_objects)
                timings["cleanup_removed_meshes"]=len(meshes)
                progress("cleanup_export_copies_complete",cname,timings=timings,
                         temporary_collection_removed=True,temporary_meshes_remaining=0)
            finally:
                source.hide_viewport=collection_hide[cname]

    try:
        if force_terrain or (not limited and terrain_changed):
            progress("prepare_terrain")
            for name,uv in {"UVMap":np.column_stack(((p[loops,0]-8)/26,(-p[loops,1]-10)/45)),
                            "RockRegion":np.column_stack(((-p[loops,1]-10)/45,(p[loops,2]-.7)/4.4)),
                            "GroundRegion":np.column_stack(((p[loops,0]+4)/48,(-p[loops,1]+15)/97))}.items():
                layer=mesh.uv_layers.get(name)
                if layer is None:raise RuntimeError("Missing established terrain UV layer "+name)
                layer.data.foreach_set("uv",uv.astype(np.float32).ravel())
            land_material=mesh.materials[0];nodes=land_material.node_tree.nodes
            principled=next(n for n in nodes if n.type=="BSDF_PRINCIPLED");land=nodes.get("G23_LandUse")
            if land is None or not land.image:raise RuntimeError("Current land-use node missing")
            links=principled.inputs["Base Color"].links
            if len(links)!=1:raise RuntimeError("Unexpected source preview material link")
            preview_socket=links[0].from_socket
            land_material.node_tree.links.new(land.outputs["Color"],principled.inputs["Base Color"])
            bpy.ops.object.select_all(action="DESELECT");terrain.hide_set(False);terrain.select_set(True);bpy.context.view_layer.objects.active=terrain
            stage=log/"staged_terrain.glb";progress("write_terrain_glb");export_selected(stage);staged.append((stage,out/"terrain.glb"))
            land_material.node_tree.links.new(preview_socket,principled.inputs["Base Color"])
            bvh=BVHTree.FromPolygons(p.tolist(),loops.reshape(-1,3).tolist(),all_triangles=True)
            values=[];top=float(p[:,2].max()+50);reach=top-float(p[:,2].min())+50
            progress("sample_height_cache",total_rows=481)
            for iz,z in enumerate(np.arange(-30,90.001,.25)):
                q=float(np.clip((z+18.7)/(-26+18.7),0,1));shore=7.8+1.45*math.sin(z*.12)+.48*math.sin(z*.29)-21*q*q*(3-2*q)
                for d in np.arange(-20,50.001,.25):
                    hit=bvh.ray_cast(Vector((float(shore+d),float(-z),top)),Vector((0,0,-1)),reach)[0]
                    values.append(round(float(hit.z) if hit is not None else -15.,5))
                if (iz+1)%40==0:progress("sample_height_cache",completed_rows=iz+1,total_rows=481,heartbeat=True)
            stage=log/"staged_shore_relief_height.json"
            stage.write_text(json.dumps({"d0":-20,"z0":-30,"step":.25,"columns":281,"rows":481,"heights":values}),encoding="utf-8")
            staged.append((stage,out/"shore_relief_height.json"));report["height_values"]=len(values)
        for cname in collection_changes:
            stage=log/("staged_"+mapping[cname]);detail=export_collection(cname,stage)
            collection_changes[cname].update(detail);staged.append((stage,out/mapping[cname]))
        for stage,destination in staged:
            progress("commit_staged_asset",file=destination.name)
            stage.replace(destination)
            report["exported"].append({"file":destination.name,"sha256":_sha256(destination),"bytes":destination.stat().st_size})
        for row in fixed:
            if _sha256(root/row["relative"])!=row["sha256"].lower():raise RuntimeError("Preserved asset changed during export")
        report["floors_after"]=floor_checks()
        report["nine_original_floors_geometry_and_pose_preserved"]=True
        report["preserved_asset_count"]=len(fixed);report["preserved_assets_match"]=True
        report["runtime_asset_hashes"]={filename:_sha256(out/filename) for filename in
                                       ("terrain.glb","shore_relief_height.json",*mapping.values())}
    except Exception as exc:
        report["status"]="failed";report["error"]=type(exc).__name__+": "+str(exc)
        progress("failed",error=report["error"])
        raise
    finally:
        if preview_socket is not None:land_material.node_tree.links.new(preview_socket,principled.inputs["Base Color"])
        for cname,hidden in collection_hide.items():bpy.data.collections[cname].hide_viewport=hidden
        bpy.ops.object.select_all(action="DESELECT")
        for obj in selected:
            if bpy.data.objects.get(obj.name)==obj:obj.select_set(True)
        if active and bpy.data.objects.get(active.name)==active:bpy.context.view_layer.objects.active=active
        for name,hidden in object_hide.items():
            if bpy.data.objects.get(name):bpy.data.objects[name].hide_set(hidden)
        report["source_material_restored"]=preview_socket is None or principled.inputs["Base Color"].links[0].from_socket==preview_socket
        report["temporary_collection_removed"]=bpy.data.collections.get(temporary_collection_name) is None
        report["elapsed_seconds"]=time.perf_counter()-started
        (log/"export.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    if not report["source_material_restored"] or not report["temporary_collection_removed"]:
        raise RuntimeError("Source export state did not restore; source not saved")
    progress("save_source")
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    report.update(status="completed",source_saved=True,dirty=bool(bpy.data.is_dirty),source_sha256=_sha256(bpy.data.filepath))
    report["elapsed_seconds"]=time.perf_counter()-started
    progress("completed")
    (log/"export.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="collections"},ensure_ascii=False))
    return report
