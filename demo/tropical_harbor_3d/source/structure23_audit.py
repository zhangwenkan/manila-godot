"""Independent read-only structural road audit for an owned live Blender MCP.

Import/exec only defines functions. Explicitly call audit_structure23(spec, out).
Never imports a previous production script, updates a depsgraph, changes scene
data, exports, saves a blend, or launches an application. Its sole optional
write is the caller-specified JSON report. Technical pass is not visual pass.

Spec schema (all paths absolute or relative to the blend's parent.parent):
  schema_version: 1
  session: {pid: current owned PID, source: exact opened .blend path}
  terrain_object: "C25_ContourBuiltCoast"
  baseline_npz: current-round snapshot with positions/triangles (or loops)
  routes: [{name, points_xzh: [[x,z,height], ...], width_m: scalar OR per-point,
            crossfall: optional scalar height-rise/metre toward left,
            station_step_m: .10, cross_samples: 11,
            limits: {cross_slope_deg, longitudinal_slope_deg,
                     target_height_error_m, cross_section_relief_m}}]
  junctions: [{name, polygon_xz: [[x,z], ...], grid_step_m: .12,
               gates: [{route: route name, end: "start"|"end"}],
               # A gate within a route can instead use segment_index and at
               # (0..1 fraction along that exact reviewed segment).
               limits: {face_slope_deg, gate_inside_fraction,
                        gate_target_height_error_m}}]
  entrances: [{name, object: actual lowest step object,
               threshold_vertex_indices: [two actual edge vertex indices],
               outside_direction_xz: [x,z], approach_depth_m: .50,
               expected_rise_m: actual intended rise above the approach,
               limits: {rise_error_m, approach_cross_slope_deg,
                        approach_longitudinal_slope_deg}}]
  foundations_json: optional saved 9-floor world vertices/corners
  foundations_objects_snapshot: current-round objects_before.json for poses
  preserved_hashes: optional [{path, sha256}] OR a JSON file with that list
  cargo: optional {objects: [...], expected_samples: 235,
                   below_height_m: .6, minimum_clearance_m: value}
  exported_terrain_glb: optional final exported GLB, checked only when provided

Height and slope limits must come from the reviewed design, not this audit.
Routes with missing limits remain incomplete; color continuity never passes a
road. Entrance segments are selected from real mesh vertices, not a bounding
box/floor guessed to be the actual threshold. Coordinates explicitly use
Godot planar X,Z plus height; Blender mesh coords are X,-Z,height.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def _stats(values):
    a = np.asarray(values, float)
    a = a[np.isfinite(a)]
    if not len(a): return None
    return dict(zip(("min", "median", "p95", "max"), np.quantile(a, [0, .5, .95, 1]).tolist()))


def _hash(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): result.update(chunk)
    return result.hexdigest()


def _world_vertices(obj):
    values = np.empty((len(obj.data.vertices), 3), np.float32)
    obj.data.vertices.foreach_get("co", values.ravel())
    matrix = np.asarray(obj.matrix_world, float)
    return values.astype(float) @ matrix[:3, :3].T + matrix[:3, 3]


def _mesh_indices(mesh):
    loops = np.empty(len(mesh.loops), np.int32)
    starts = np.empty(len(mesh.polygons), np.int32)
    sizes = np.empty(len(mesh.polygons), np.int32)
    mesh.loops.foreach_get("vertex_index", loops)
    mesh.polygons.foreach_get("loop_start", starts)
    mesh.polygons.foreach_get("loop_total", sizes)
    return loops, starts, sizes


def _boundary(points, triangles):
    # Baseline NPZ is float32; live world coordinates are float64. Quantize in
    # the same precision so identical saved vertices cannot straddle a bin.
    points = np.asarray(points, np.float64)
    edges = np.sort(np.concatenate((triangles[:, :2], triangles[:, 1:], triangles[:, (2, 0)])), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    border = unique[counts == 1]
    coordinates = np.rint(points[border] / .00002).astype(np.int64)
    signatures = {tuple(sorted(tuple(v) for v in pair)) for pair in coordinates}
    return border, signatures, int((counts > 2).sum())


def _inside(points, polygon, tolerance=.0001):
    points = np.asarray(points, float); polygon = np.asarray(polygon, float)
    x, z = points[:, 0], points[:, 1]
    inside = np.zeros(len(points), bool); distance = np.full(len(points), np.inf)
    for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
        d = b-a; den = float(d@d)
        if den < 1e-15: continue
        t = np.clip(((points-a)*d).sum(1)/den, 0, 1)
        distance = np.minimum(distance, np.linalg.norm(points-a-t[:, None]*d, axis=1))
        if abs(d[1]) > 1e-12:
            inside ^= ((a[1] > z) != (b[1] > z)) & (x < d[0]*(z-a[1])/d[1]+a[0])
    return inside | (distance <= tolerance)


def _convex_hull(points):
    points=sorted(set(tuple(map(float,p)) for p in points))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lower=[];upper=[]
    for point in points:
        while len(lower)>1 and cross(lower[-2],lower[-1],point)<=0:lower.pop()
        lower.append(point)
    for point in reversed(points):
        while len(upper)>1 and cross(upper[-2],upper[-1],point)<=0:upper.pop()
        upper.append(point)
    return np.asarray(lower[:-1]+upper[:-1],float)


def _glb_faces(path):
    raw = Path(path).read_bytes()
    magic, version, total = struct.unpack_from("<III", raw)
    if magic != 0x46546C67 or version != 2 or total != len(raw): raise ValueError("Invalid GLB")
    pos = 12; document = binary = None
    while pos < len(raw):
        length, kind = struct.unpack_from("<II", raw, pos); pos += 8
        data = raw[pos:pos+length]; pos += length
        if kind == 0x4E4F534A: document = json.loads(data)
        elif kind == 0x004E4942: binary = data
    if document is None or binary is None: raise ValueError("GLB lacks JSON/BIN")
    for node in document.get("nodes", []):
        if any(k in node for k in ("matrix", "translation", "rotation", "scale")):
            raise ValueError("Export comparison requires identity GLB nodes")
    def access(index):
        acc = document["accessors"][index]; view = document["bufferViews"][acc["bufferView"]]
        if "sparse" in acc or acc.get("normalized"): raise ValueError("Unexpected sparse/normalized geometry accessor")
        dtype = np.dtype({5121:"u1",5123:"<u2",5125:"<u4",5126:"<f4"}[acc["componentType"]])
        width = {"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4}[acc["type"]]
        offset = view.get("byteOffset",0)+acc.get("byteOffset",0)
        return np.ndarray((acc["count"],width), dtype=dtype, buffer=binary, offset=offset,
                          strides=(view.get("byteStride",width*dtype.itemsize),dtype.itemsize)).copy()
    result=[]
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            if primitive.get("mode",4) != 4: raise ValueError("Export contains non-triangles")
            p=access(primitive["attributes"]["POSITION"])
            ids=access(primitive["indices"]).ravel() if "indices" in primitive else np.arange(len(p))
            result.append(p[ids.reshape(-1,3)])
    return np.concatenate(result)


def _triangle_signature(faces):
    values=np.rint(np.asarray(faces,np.float64)/.00002).astype(np.int64)
    rows=np.sort(values.view(np.dtype((np.void, values.dtype.itemsize*3))).reshape(-1,3),axis=1)
    return np.sort(rows.reshape(-1,3).view(np.dtype((np.void, rows.dtype.itemsize*3))).ravel())


def audit_structure23(spec, output_path=None):
    """Read current raw terrain and caller's reviewed targets; return a report."""
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    started=time.perf_counter(); root=Path(bpy.data.filepath).parent.parent
    if isinstance(spec,(str,Path)):
        source_spec=Path(spec)
        spec=json.loads(source_spec.read_text(encoding="utf-8"))
    else: source_spec=None
    def resolve(value):
        p=Path(value)
        return p if p.is_absolute() else root/p
    dirty_before=bool(bpy.data.is_dirty)
    report={"status":"running","read_only":True,"visual_accepted":False,
            "source":bpy.data.filepath,"pid":os.getpid(),"checked_at_utc":datetime.now(timezone.utc).isoformat(),
            "spec_source":str(source_spec) if source_spec else "caller object",
            "dirty_before":dirty_before,"failures":[],"incomplete":[],"routes":[],"junctions":[],"entrances":[]}
    def check(condition, message):
        if not condition: report["failures"].append(message)
    def limits_for(row, required, title):
        limits=row.get("limits",{})
        for key in required:
            if key not in limits: report["incomplete"].append(title+": missing reviewed limit "+key)
        return limits
    def limit(limits,key,actual,title):
        if key in limits: check(actual is not None and math.isfinite(float(actual)) and actual<=limits[key]+1e-6,title+": "+key+" exceeded")
    def finish():
        report["elapsed_seconds"]=time.perf_counter()-started
        report["dirty_after"]=bool(bpy.data.is_dirty)
        check(report["dirty_after"]==dirty_before,"Audit changed dirty state")
        report["technical_pass"]=False if report["failures"] else (None if report["incomplete"] else True)
        if output_path:
            destination=resolve(output_path)
            if destination.suffix.lower()!=".json": raise ValueError("Audit output must be JSON")
            destination.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
        return report

    try:
        if bpy.app.background: raise RuntimeError("Run through the owned GUI Blender MCP")
        if spec.get("schema_version")!=1: raise ValueError("Unknown structural audit schema")
        session=spec.get("session",{})
        if session.get("pid")!=os.getpid() or Path(session.get("source","")).resolve()!=Path(bpy.data.filepath).resolve():
            raise RuntimeError("Owned process/source must be explicit and match this session")
        terrain=bpy.data.objects[spec.get("terrain_object","C25_ContourBuiltCoast")]
        if terrain.type!="MESH" or terrain.mode!="OBJECT": raise RuntimeError("Terrain must be a mesh in Object mode")
        if any(m.show_viewport for m in terrain.modifiers): raise RuntimeError("Active terrain modifiers are unsupported by raw-mesh audit")
        positions=_world_vertices(terrain);loops,starts,sizes=_mesh_indices(terrain.data)
        if not np.all(sizes==3): raise RuntimeError("Current structural audit requires explicit triangles")
        triangles=loops.reshape(-1,3);faces=positions[triangles]
        normals=np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0])
        border,border_geometry,nonmanifold=_boundary(positions,triangles)
        check(bool(np.isfinite(positions).all()),"Terrain has nonfinite positions")
        check(bool((normals[:,2]>1e-9).all()),"Terrain has degenerate/downward projected triangles")
        check(nonmanifold==0,"Terrain has nonmanifold edges")
        report["geometry"]={"vertices":len(positions),"triangles":len(triangles),"boundary_edges":len(border),"nonmanifold_edges":nonmanifold}
        baseline=spec.get("baseline_npz");baseline_bvh=None
        if baseline:
            with np.load(resolve(baseline)) as data:
                old=data["positions"].copy()
                old_tri=data["triangles"].copy() if "triangles" in data else data["loops"].reshape(-1,3).copy()
            # Snapshot positions follow the existing identity-transform terrain convention.
            check(np.max(abs(np.asarray(terrain.matrix_world)-np.eye(4)))<1e-8,"Baseline comparison requires identity terrain transform")
            old_border,old_geometry,_=_boundary(old,old_tri)
            report["geometry"].update(boundary_coordinate_edges_added=len(border_geometry-old_geometry),
                boundary_coordinate_edges_removed=len(old_geometry-border_geometry),baseline_boundary_edges=len(old_border))
            check(border_geometry==old_geometry,"Outer boundary geometry changed or new opening exists")
            baseline_bvh=BVHTree.FromPolygons(old.astype(float).tolist(),old_tri.tolist(),all_triangles=True)
        else: report["incomplete"].append("Missing current-round baseline_npz for outer-boundary comparison")
        bvh=BVHTree.FromPolygons(positions.tolist(),triangles.tolist(),all_triangles=True)
        top=float(positions[:,2].max()+50);reach=top-float(positions[:,2].min())+50
        down=Vector((0,0,-1))
        gradient=np.column_stack((-normals[:,0]/normals[:,2],normals[:,1]/normals[:,2]))
        face_slope=np.degrees(np.arctan(np.linalg.norm(gradient,axis=1)))
        def query(xz):
            xz=np.asarray(xz,float); h=np.full(len(xz),np.nan); ids=np.full(len(xz),-1,int)
            for i,(x,z) in enumerate(xz):
                hit,_,face_id,_=bvh.ray_cast(Vector((float(x),float(-z),top)),down,reach)
                if hit is not None: h[i]=hit.z;ids[i]=face_id
            valid=ids>=0;grad=np.full((len(xz),2),np.nan);slope=np.full(len(xz),np.nan)
            grad[valid]=gradient[ids[valid]];slope[valid]=face_slope[ids[valid]]
            return h,grad,slope,ids
        def scalar_max(a):
            a=np.asarray(a,float)
            return float(np.max(a[np.isfinite(a)])) if np.isfinite(a).any() else None
        route_lookup={}
        for route in spec.get("routes",[]):
            name=route["name"];p=np.asarray(route["points_xzh"],float)
            if p.ndim!=2 or p.shape[1]!=3 or len(p)<2: raise ValueError("Route needs >=2 X,Z,height targets: "+name)
            widths=np.broadcast_to(np.asarray(route["width_m"],float),(len(p),))
            if np.any(widths<=0): raise ValueError("Route widths must be positive")
            count=int(route.get("cross_samples",11));step=float(route.get("station_step_m",.10))
            if count<5 or count%2!=1 or not .02<=step<=.25: raise ValueError("Use odd >=5 cross samples and .02..25m stations")
            crossfall=float(route.get("crossfall",0));centres=[];width=[];directions=[];distance=[];accum=0
            for a,b,wa,wb in zip(p,p[1:],widths,widths[1:]):
                d=b[:2]-a[:2];length=np.linalg.norm(d)
                if length<1e-6: raise ValueError("Duplicate route points: "+name)
                n=max(1,int(np.ceil(length/step)))
                for t in np.arange(n)/n:
                    centres.append(a*(1-t)+b*t);width.append(wa*(1-t)+wb*t);directions.append(d/length);distance.append(accum+t*length)
                accum+=length
            centres.append(p[-1]);width.append(widths[-1]);directions.append(d/length);distance.append(accum)
            centres=np.asarray(centres);width=np.asarray(width);directions=np.asarray(directions)
            sideways=np.column_stack((-directions[:,1],directions[:,0]));fractions=np.linspace(-.5,.5,count)
            offsets=width[:,None]*fractions
            sample_xz=(centres[:,None,:2]+sideways[:,None,:]*offsets[:,:,None]).reshape(-1,2)
            expected=(centres[:,2,None]+crossfall*offsets).ravel()
            h,g,slope,ids=query(sample_xz)
            longitudinal=np.degrees(np.arctan(abs(np.sum(g*np.repeat(directions,count,axis=0),axis=1))))
            cross=np.degrees(np.arctan(abs(np.sum(g*np.repeat(sideways,count,axis=0),axis=1))))
            error=abs(h-expected);matrix_h=h.reshape(-1,count)
            relief=np.max(matrix_h,axis=1)-np.min(matrix_h,axis=1)
            missing=int((ids<0).sum());check(missing==0,name+": road footprint has missing ground hits")
            limits=limits_for(route,("cross_slope_deg","longitudinal_slope_deg","target_height_error_m"),name)
            for key,value in (("cross_slope_deg",scalar_max(cross)),("longitudinal_slope_deg",scalar_max(longitudinal)),
                              ("target_height_error_m",scalar_max(error)),("cross_section_relief_m",scalar_max(relief))):limit(limits,key,value,name)
            worst=np.argsort(np.nan_to_num(cross,nan=1000))[-12:][::-1]
            def samples_at(indices):
                return [{"xz":sample_xz[i].tolist(),"height_m":float(h[i]) if ids[i]>=0 else None,
                    "target_height_m":float(expected[i]),"face_slope_deg":float(slope[i]) if ids[i]>=0 else None,
                    "cross_slope_deg":float(cross[i]) if ids[i]>=0 else None,
                    "longitudinal_slope_deg":float(longitudinal[i]) if ids[i]>=0 else None,
                    "target_height_error_m":float(error[i]) if ids[i]>=0 else None,"triangle":int(ids[i])} for i in indices]
            row={"name":name,"length_m":float(accum),"stations":len(centres),"cross_samples_per_station":count,
                 "footprint_samples":len(sample_xz),"missing_hits":missing,"width_m":_stats(width),
                 "face_slope_deg":_stats(slope),"cross_slope_deg":_stats(cross),"longitudinal_slope_deg":_stats(longitudinal),
                 "target_height_error_m":_stats(error),"cross_section_relief_m":_stats(relief),"limits":limits,
                 "worst_crossfall_samples":samples_at(worst),
                 "worst_longitudinal_samples":samples_at(np.argsort(np.nan_to_num(longitudinal,nan=1000))[-6:][::-1]),
                 "worst_height_error_samples":samples_at(np.argsort(np.nan_to_num(error,nan=1000))[-6:][::-1])}
            report["routes"].append(row)
            route_lookup[name]={"targets":p,"widths":widths,"directions":directions,"crossfall":crossfall}
        if not report["routes"]: report["incomplete"].append("No reviewed full-width route design supplied")

        for junction in spec.get("junctions",[]):
            name=junction["name"];poly=np.asarray(junction["polygon_xz"],float);step=float(junction.get("grid_step_m",.12))
            if len(poly)<3 or not .02<=step<=.25: raise ValueError("Invalid junction footprint/grid")
            xx,zz=np.meshgrid(np.arange(poly[:,0].min(),poly[:,0].max()+step*.5,step),np.arange(poly[:,1].min(),poly[:,1].max()+step*.5,step))
            q=np.column_stack((xx.ravel(),zz.ravel()));q=np.concatenate((q[_inside(q,poly)],poly))
            h,g,slope,ids=query(q);check(bool((ids>=0).all()),name+": junction lacks complete terrain support")
            limits=limits_for(junction,("face_slope_deg","gate_inside_fraction","gate_target_height_error_m"),name)
            limit(limits,"face_slope_deg",scalar_max(slope),name);gates=[]
            for gate in junction.get("gates",[]):
                route=route_lookup[gate["route"]];targets=route["targets"];widths=route["widths"]
                if "segment_index" in gate:
                    index=int(gate["segment_index"]);at=float(gate.get("at",0))
                    if not 0<=index<len(targets)-1 or not 0<=at<=1:raise ValueError("Invalid reviewed junction segment gate")
                else:
                    end=gate.get("end")
                    if end not in ("start","end"):raise ValueError("Junction gate requires end or segment_index+at")
                    index=0 if end=="start" else len(targets)-2;at=0 if end=="start" else 1
                a,b=targets[index],targets[index+1];point=a*(1-at)+b*at
                direction=b[:2]-a[:2];direction/=np.linalg.norm(direction);side=np.array([-direction[1],direction[0]])
                width=widths[index]*(1-at)+widths[index+1]*at
                offsets=np.linspace(-.5,.5,15)*width;gate_q=point[:2]+offsets[:,None]*side
                inside=_inside(gate_q,poly,.025);gh,_,_,gi=query(gate_q)
                error=abs(gh-point[2]-route["crossfall"]*offsets)
                fraction=float(inside.mean())
                if "gate_inside_fraction" in limits:check(fraction>=limits["gate_inside_fraction"],name+": gate does not join across its full intended width: "+gate["route"])
                limit(limits,"gate_target_height_error_m",scalar_max(error),name+" gate "+gate["route"])
                check(bool((gi>=0).all()),name+": gate lacks ground")
                gates.append({"route":gate["route"],"end":gate.get("end"),"segment_index":index,"at":at,
                    "target_centre_xzh":point.tolist(),"target_width_m":float(width),"inside_fraction":fraction,
                    "height_range_m":_stats(gh),"target_error_m":_stats(error)})
            if len(gates)<2:report["incomplete"].append(name+": junction needs at least two reviewed route gates")
            report["junctions"].append({"name":name,"samples":len(q),"face_slope_deg":_stats(slope),"height_m":_stats(h),"gates":gates})
        report["platforms"]=[]
        for platform in spec.get("platforms",[]):
            name=platform["name"];poly=np.asarray(platform["polygon"],float);step=float(platform.get("grid_step_m",.12))
            if len(poly)<3 or not .02<=step<=.25:raise ValueError("Invalid platform footprint/grid")
            xx,zz=np.meshgrid(np.arange(poly[:,0].min(),poly[:,0].max()+step*.5,step),np.arange(poly[:,1].min(),poly[:,1].max()+step*.5,step))
            q=np.column_stack((xx.ravel(),zz.ravel()));q=np.concatenate((q[_inside(q,poly)],poly))
            h,g,slope,ids=query(q);check(bool((ids>=0).all()),name+": platform lacks complete terrain support")
            error=abs(h-float(platform["height"]))
            flat=np.ones(len(q),bool)
            for exclusion in platform.get("graded_route_overrides",[]):
                route_name=exclusion["route"];margin=float(exclusion.get("margin_m",0))
                route=route_lookup[route_name];distance=np.full(len(q),np.inf)
                for a,b,wa,wb in zip(route["targets"],route["targets"][1:],route["widths"],route["widths"][1:]):
                    d=b[:2]-a[:2];t=np.clip(((q-a[:2])*d).sum(1)/(d@d),0,1)
                    radius=(wa*(1-t)+wb*t)*.5+margin
                    distance=np.minimum(distance,np.linalg.norm(q-a[:2]-t[:,None]*d,axis=1)-radius)
                flat &= distance>0
            if not flat.any():report["incomplete"].append(name+": no flat plateau samples remain after reviewed graded-route exclusions")
            limits=limits_for(platform,("face_slope_deg","target_height_error_m"),name)
            limit(limits,"face_slope_deg",scalar_max(slope[flat]),name)
            limit(limits,"target_height_error_m",scalar_max(error[flat]),name)
            connected=[]
            for route_name,route in route_lookup.items():
                for end,index in (("start",0),("end",-1)):
                    point=route["targets"][index]
                    if not _inside([point[:2]],poly,.025)[0]:continue
                    direction=route["directions"][index];side=np.array([-direction[1],direction[0]])
                    offsets=np.linspace(-.5,.5,15)*route["widths"][index];gate_q=point[:2]+offsets[:,None]*side
                    gh,_,gs,gi=query(gate_q);fraction=float(_inside(gate_q,poly,.025).mean())
                    check(bool((gi>=0).all()),name+": candidate route gate lacks ground")
                    connected.append({"route":route_name,"end":end,"whole_width_inside_platform_fraction":fraction,
                        "height_m":_stats(gh),"face_slope_deg":_stats(gs),"route_platform_target_difference_m":abs(float(point[2])-float(platform["height"])),
                        "note":"Geometric candidate only; reviewed junction gates determine intended topology."})
            report["platforms"].append({"name":name,"kind":platform.get("kind"),"samples":len(q),"face_slope_deg":_stats(slope),
                "height_m":_stats(h),"target_height_error_m":_stats(error),"route_gate_candidates":connected,
                "flat_plateau_samples":int(flat.sum()),"graded_route_samples_excluded_from_flat_limits":int((~flat).sum()),
                "flat_plateau_face_slope_deg":_stats(slope[flat]),"flat_plateau_target_height_error_m":_stats(error[flat]),
                "graded_route_overrides":platform.get("graded_route_overrides",[])})
        if not report["junctions"]:
            report["incomplete"].append("No reviewed junction gates supplied; platform endpoint overlaps are diagnostic candidates only")

        for entry in spec.get("entrances",[]):
            name=entry["name"];obj=bpy.data.objects[entry["object"]];p=_world_vertices(obj)
            edge=p[np.asarray(entry["threshold_vertex_indices"],int)]
            if edge.shape!=(2,3):raise ValueError("Entrance needs two selected actual edge vertices")
            edge=edge[:,[0,2,1]];edge[:,2]*=-1
            if entry.get("expected_threshold_endpoints_godot") is not None:
                evidence=np.asarray(entry["expected_threshold_endpoints_godot"],float)
                check(evidence.shape==(2,3) and float(np.max(abs(edge-evidence)))<=.00002,
                      name+": actual threshold edge differs from reviewed live-index evidence")
            edge_xz=edge[:,[0,2]];toward=np.asarray(entry["outside_direction_xz"],float);toward/=np.linalg.norm(toward)
            across=edge_xz[1]-edge_xz[0];across/=np.linalg.norm(across)
            along=np.linspace(0,1,11);edge_points=edge_xz[0]+along[:,None]*(edge_xz[1]-edge_xz[0])
            edge_height=edge[0,1]+along*(edge[1,1]-edge[0,1]);depth=float(entry.get("approach_depth_m",.5))
            distances=np.linspace(.025,depth,5)
            q=(edge_points[None,:,:]+distances[:,None,None]*toward).reshape(-1,2)
            h,g,slope,ids=query(q);check(bool((ids>=0).all()),name+": entrance approach lacks ground")
            rise=edge_height-h.reshape(5,11)[0]
            error=abs(rise-float(entry["expected_rise_m"]))
            cross=np.degrees(np.arctan(abs(g@across)));longitudinal=np.degrees(np.arctan(abs(g@toward)))
            limits=limits_for(entry,("rise_error_m","approach_cross_slope_deg","approach_longitudinal_slope_deg"),name)
            for key,value in (("rise_error_m",scalar_max(error)),("approach_cross_slope_deg",scalar_max(cross)),("approach_longitudinal_slope_deg",scalar_max(longitudinal))):limit(limits,key,value,name)
            report["entrances"].append({"name":name,"object":obj.name,"actual_threshold_endpoints_godot":edge.tolist(),
                "approach_samples":len(q),"threshold_rise_m":_stats(rise),"expected_rise_m":entry["expected_rise_m"],
                "rise_error_m":_stats(error),"approach_cross_slope_deg":_stats(cross),"approach_longitudinal_slope_deg":_stats(longitudinal)})
        if not report["entrances"]:report["incomplete"].append("No actual entrance threshold edges supplied")

        if spec.get("foundations_json"):
            floors=json.loads(resolve(spec["foundations_json"]).read_text(encoding="utf-8"));report["floors"]=[]
            expected_names={floor["object"] for floor in floors}
            current_names={obj.name for obj in bpy.data.collections["Reference_Town"].all_objects
                           if obj.type=="MESH" and obj.name.startswith("Town_Floor")}
            check(len(expected_names)==9 and current_names==expected_names,"Nine original Town floors are not preserved as a set")
            poses={}
            if spec.get("foundations_objects_snapshot"):
                poses={row["name"]:row for row in json.loads(resolve(spec["foundations_objects_snapshot"]).read_text(encoding="utf-8"))}
            else:report["incomplete"].append("Missing current-round floor pose snapshot")
            for floor in floors:
                obj=bpy.data.objects[floor["object"]];actual=_world_vertices(obj);prior=np.asarray(floor["corners"])
                error=float(np.max(abs(actual-prior))) if actual.shape==prior.shape else None
                check(error is not None and error<=.00002,"Preserved floor changed: "+floor["object"])
                transform_error=None
                if poses:
                    saved=poses.get(obj.name)
                    transform_error=float(np.max(abs(np.asarray(obj.matrix_world)-np.asarray(saved["matrix"])))) if saved else None
                    check(transform_error is not None and transform_error<=1e-7,"Preserved floor pose changed or absent from snapshot: "+obj.name)
                support={}
                if baseline_bvh is not None:
                    bottom=float(actual[:,2].min());foot=actual[abs(actual[:,2]-bottom)<=.00002][:,[0,1]];foot[:,1]*=-1
                    poly=_convex_hull(foot)
                    if len(poly)<3:raise ValueError("Floor lacks a horizontal bottom footprint: "+obj.name)
                    step=.20;xx,zz=np.meshgrid(np.arange(poly[:,0].min(),poly[:,0].max()+step*.5,step),np.arange(poly[:,1].min(),poly[:,1].max()+step*.5,step))
                    q=np.column_stack((xx.ravel(),zz.ravel()));q=np.concatenate((q[_inside(q,poly)],poly))
                    gh,_,_,gi=query(q);old_h=[]
                    for x,z in q:
                        hit=baseline_bvh.ray_cast(Vector((float(x),float(-z),top)),down,reach)[0]
                        old_h.append(float(hit.z) if hit is not None else np.nan)
                    old_h=np.asarray(old_h);valid=np.isfinite(old_h)&(gi>=0)
                    check(bool(valid.all()),"Floor footprint lacks ground query: "+obj.name)
                    delta=gh-old_h;gap=bottom-gh;old_gap=bottom-old_h
                    new_intrusion=np.maximum(-gap,0)-np.maximum(-old_gap,0)
                    tolerance=float(spec.get("floor_contact_change_tolerance_m",.02))
                    check(bool(valid.all()) and float(np.min(delta))>=-tolerance,"Ground excavated below preserved floor footprint: "+obj.name)
                    check(bool(valid.all()) and float(np.max(new_intrusion))<=tolerance,"New terrain intrusion into preserved floor: "+obj.name)
                    support={"samples":len(q),"underside_height_m":bottom,"gap_m":_stats(gap),"baseline_gap_m":_stats(old_gap),
                        "terrain_height_change_m":_stats(delta),"added_intrusion_m":_stats(new_intrusion),"change_tolerance_m":tolerance,
                        "note":"Relative checks detect new excavation/intrusion; existing gaps are reported and do not prove physical foundation support."}
                report["floors"].append({"object":floor["object"],"world_vertex_max_error_m":error,"matrix_max_error":transform_error,"terrain_contact":support})
        else:report["incomplete"].append("Missing foundation preservation evidence")
        if spec.get("cargo"):
            cargo=spec["cargo"];clearance=[];misses=0
            for name in cargo["objects"]:
                obj=bpy.data.objects[name];vertices=_world_vertices(obj);il,st,sz=_mesh_indices(obj.data)
                for start,size in zip(st,sz):
                    face=vertices[il[start:start+size]]
                    for p in list(face)+[face.mean(0)]:
                        if p[2]>=cargo.get("below_height_m",.6):continue
                        h,_,_,ids=query([[p[0],-p[1]]])
                        if ids[0]<0:misses+=1
                        else:clearance.append(float(p[2]-h[0]))
            check(len(clearance)==cargo["expected_samples"] and misses==0,"Cargo sample set incomplete")
            check(bool(clearance) and min(clearance)>=cargo["minimum_clearance_m"],"Cargo clearance reduced below reviewed limit")
            report["cargo"]={"samples":len(clearance),"misses":misses,"clearance_m":_stats(clearance)}
        else:report["incomplete"].append("Missing cargo protection sample specification")
        hashes=spec.get("preserved_hashes")
        if isinstance(hashes,(str,Path)):hashes=json.loads(resolve(hashes).read_text(encoding="utf-8"))
        report["preserved_hashes"]=[]
        for row in hashes or []:
            path=row.get("relative",row.get("path"));actual=_hash(resolve(path));same=actual==row["sha256"].lower()
            check(same,"Preserved asset changed: "+path)
            report["preserved_hashes"].append({"path":path,"sha256":actual,"matches":same})
        if not hashes:report["incomplete"].append("Missing preserved-asset hashes")
        if spec.get("exported_terrain_glb"):
            exported=_glb_faces(resolve(spec["exported_terrain_glb"]));world=positions[:,[0,2,1]].copy();world[:,2]*=-1
            same=np.array_equal(_triangle_signature(exported),_triangle_signature(world[triangles]))
            check(same,"Exported GLB geometry differs from current source")
            report["exported_terrain"]={"triangles":len(exported),"matches_source_at_20um":same,"sha256":_hash(resolve(spec["exported_terrain_glb"]))}
        report["status"]="completed"
        return finish()
    except Exception as exc:
        report["status"]="failed";report["error"]=type(exc).__name__+": "+str(exc)
        report["failures"].append("Audit did not complete")
        finish()
        raise


def audit_structure23_design(design, expected_pid, output_path=None, overrides=None,
                             check_export=False, log_path=None, changed_collections=()):
    """Adapter for this round's shared routes/platforms JSON.

    Uniform design routes use points=[[x,z,h]], halfwidth, shoulder_width,
    kind. Platforms use polygon=[[x,z]], height, blend_width, kind. Their
    per-item limits or top-level audit_limits supply the reviewed tolerances.
    overrides can add actual entrance edges, explicit junction gates, etc.
    The adapter does not invent missing tolerances or assume all proximity is
    an intended junction. `check_export` is false until the new export exists.
    `changed_collections` must explicitly contain Reference_Town to allow its
    prop export; the nine original floor geometries and poses stay protected.
    """
    import bpy
    root=Path(bpy.data.filepath).parent.parent
    log=Path(log_path) if log_path else root/"captures/terrain_structure_20261123"
    if not log.is_absolute():log=root/log
    if isinstance(design,(str,Path)):
        path=Path(design);path=path if path.is_absolute() else root/path
        design=json.loads(path.read_text(encoding="utf-8"))
    common=design.get("audit_limits",{})
    routes=[]
    for route in design.get("routes",[]):
        row=dict(route);row["points_xzh"]=row["points"]
        halfwidth=np.asarray(row["halfwidth"],float)
        row["width_m"]=(halfwidth*2).tolist()
        row["limits"]=dict(common.get("routes",{}));row["limits"].update(route.get("limits",{}))
        routes.append(row)
    platforms=[]
    for platform in design.get("platforms",[]):
        row=dict(platform);row["limits"]=dict(common.get("platforms",{}));row["limits"].update(platform.get("limits",{}));platforms.append(row)
    manifest=json.loads((log/"before_manifest.json").read_text(encoding="utf-8"))
    fixed={"town.glb","cargo_port.glb","boat.glb","cargo_ginseng.glb","cargo_jade.glb","cargo_nutmeg.glb","cargo_silk.glb","ocean.glb","ground_rock.glb"}
    declared=set(changed_collections)
    supported={"Reference_Coast","Reference_Foliage","Reference_Rocks","Reference_GroundCover","Reference_Town"}
    if not declared<=supported:raise ValueError("Unsupported explicitly changed collections: "+str(declared-supported))
    if "Reference_Town" in declared:fixed.remove("town.glb")
    preserved=[row for row in manifest if Path(row["relative"]).name in fixed]
    if len(preserved)!=len(fixed):raise RuntimeError("Preserved asset manifest incomplete")
    spec={"schema_version":1,"session":{"pid":expected_pid,"source":bpy.data.filepath},
          "baseline_npz":str(log/"baseline.npz"),"routes":routes,"platforms":platforms,
          "junctions":design.get("junctions",[]),"entrances":design.get("entrances",[]),
          "foundations_json":"captures/rock_path_sample_20261123/foundations.json",
          "foundations_objects_snapshot":str(log/"objects_before.json"),
          "preserved_hashes":preserved,
          "cargo":{"objects":["R20_UpperHull","R20_LowerHull","R20_HullBottom"],"expected_samples":235,
                   "below_height_m":.6,"minimum_clearance_m":float(common.get("cargo_minimum_clearance_m",0))}}
    if check_export:spec["exported_terrain_glb"]="assets/reference/terrain.glb"
    if overrides:spec.update(overrides)
    return audit_structure23(spec, output_path or log/"structure_audit.json")
