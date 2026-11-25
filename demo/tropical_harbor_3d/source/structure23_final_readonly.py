"""Final independent read-only review; call final_structure23_readonly(12164).

No scene mutation, evaluation update, save, export, or historical authoring
scripts. Only final JSON reports are written. Known slope failures remain
failures, even when export integrity and explicitly placed props pass.
"""
from pathlib import Path
import hashlib
import json
import os
import time
import numpy as np


def final_structure23_readonly(expected_pid):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    root=Path(bpy.data.filepath).parent.parent
    log=root/'captures/terrain_structure_20261123'
    read=lambda name:json.loads((log/name).read_text(encoding='utf8'))
    session=read('session_start.json')
    if (bpy.app.background or os.getpid()!=expected_pid or expected_pid!=session['pid']
            or bpy.types.blendermcp_server.port!=session['port']
            or Path(bpy.data.filepath).name!='harbor_shore_control_mcp.blend'):
        raise RuntimeError('Owned GUI/source/port does not match')
    started=time.perf_counter();dirty_before=bool(bpy.data.is_dirty)
    report={'status':'running','read_only':True,'visual_accepted':False,
            'pid':os.getpid(),'port':session['port'],'source':bpy.data.filepath,
            'dirty_before':dirty_before,'integrity_failures':[],'limitations':[]}
    def check(ok,message):
        if not ok:report['integrity_failures'].append(message)
    def sha(path):
        h=hashlib.sha256()
        with Path(path).open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
        return h.hexdigest()
    def world(obj):
        v=np.empty((len(obj.data.vertices),3),np.float32);obj.data.vertices.foreach_get('co',v.ravel())
        m=np.asarray(obj.matrix_world,float)
        return v.astype(float)@m[:3,:3].T+m[:3,3]

    # Full structural review includes real entrances, floor geometry/support,
    # cargo clearance, fixed GLBs, and source/export triangle equivalence.
    namespace={}
    exec(compile((root/'source/structure23_audit.py').read_text(encoding='utf8'),
                 'structure23_audit.py','exec'),namespace)
    structural=namespace['audit_structure23_design'](
        log/'design.json',expected_pid,output_path=log/'final_structure_audit.json',
        changed_collections=['Reference_Town'],check_export=True)
    report['structural']={'report':'final_structure_audit.json',
                          'technical_pass':structural['technical_pass'],
                          'failures':structural['failures'],'incomplete':structural['incomplete']}
    export=read('export.json')
    check(export.get('status')=='completed' and export.get('source_saved'),
          'Final export is not completed and saved')
    check(not dirty_before and export.get('dirty') is False,'Source is dirty')
    check(export.get('source_sha256')==sha(Path(bpy.data.filepath)),
          'Saved source hash differs from export report')
    report['runtime_hashes']=[]
    hashes=dict(export.get('runtime_asset_hashes',{}))
    hashes.update({r['file']:r['sha256'] for r in export.get('exported',[])})
    check(len(hashes)>=7,'Export runtime hash record incomplete')
    for name,digest in hashes.items():
        actual=sha(root/'assets/reference'/name);matches=actual==digest.lower()
        report['runtime_hashes'].append({'file':name,'sha256':actual,'matches_export':matches})
        check(matches,'Runtime asset differs from export: '+name)

    terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
    material=mesh.materials[0]
    shader=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    links=shader.inputs['Base Color'].links
    preview_node=links[0].from_node.name if len(links)==1 else None
    land=material.node_tree.nodes.get('G23_LandUse')
    preview_ok=bool(preview_node and preview_node.startswith('G23Preview '))
    check(preview_ok,'Source preview Base Color is not restored')
    check(land is not None and land.image is not None and bool(land.image.packed_file),
          'Current land-use image is not packed')
    temp=bpy.data.collections.get('STRUCTURE23_EXPORT_TEMP')
    check(temp is None,'Temporary export collection remains')
    report['source_state']={'preview_from_node':preview_node,'preview_restored':preview_ok,
                            'land_image_packed':bool(land and land.image and land.image.packed_file),
                            'temporary_collection_removed':temp is None}
    if land is not None and land.image is not None and land.image.packed_file:
        packed_sha=hashlib.sha256(bytes(land.image.packed_file.data)).hexdigest()
        disk_sha=sha(root/'assets/reference/G23_LandUse.png')
        report['source_state']['land_packed_sha256']=packed_sha
        report['source_state']['land_disk_sha256']=disk_sha
        report['source_state']['land_packed_matches_disk']=packed_sha==disk_sha
        check(packed_sha==disk_sha,'Packed and external land-use images differ')

    # Resolve exactly the current automatic pass's unresolved groups against
    # explicit manual jobs. Read live final matrices and actual support points.
    props=read('props.json');manual=read('manual_props.json')
    check(props.get('applied') and manual.get('applied'),'Prop placement report not applied')
    check(not manual.get('problems'),'Manual placement report contains problems')
    records={r['name']:r for r in read('objects_before.json')}
    bvh=BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],
                            [list(p.vertices) for p in mesh.polygons],all_triangles=True)
    jobs=[];manual_names=set();verified_names=set()
    for job in manual['jobs']:
        names=set(job['objects']);manual_names.update(names)
        errors=[]
        for name in job['objects']:
            obj=bpy.data.objects.get(name)
            errors.append(float(np.max(abs(np.asarray(obj.matrix_world)-np.asarray(job['after_matrices'][name])))) if obj else 1e9)
        matrix_error=max(errors,default=1e9);gaps=[];misses=0
        for name in job['supports']:
            obj=bpy.data.objects[name]
            raw=np.empty((len(obj.data.vertices),3),np.float32);obj.data.vertices.foreach_get('co',raw.ravel())
            old=np.asarray(records[name]['matrix'],float)
            old_world=raw.astype(float)@old[:3,:3].T+old[:3,3]
            contact=world(obj)[old_world[:,2]<=old_world[:,2].min()+.025]
            for point in contact:
                hit=bvh.ray_cast(Vector((float(point[0]),float(point[1]),80)),Vector((0,0,-1)),200)[0]
                if hit is None:misses+=1
                else:gaps.append(float(point[2]-hit.z))
        gap_range=[min(gaps),max(gaps)] if gaps else None
        gap_match=bool(gap_range and np.max(abs(np.asarray(gap_range)-np.asarray(job['contact_gap_range'])))<.00005)
        grounded=bool(gap_range and gap_range[0]>=-.075 and gap_range[1]<=.075 and misses==0)
        passed=matrix_error<.00003 and gap_match and grounded
        check(passed,'Manual placement live pose/contact mismatch: '+job['name'])
        if passed:verified_names.update(names)
        jobs.append({'job':job['name'],'components':len(names),'matrix_max_error':matrix_error,
                     'contact_samples':len(gaps),'missing_ground':misses,'contact_gap_range':gap_range,
                     'matches_reported_gap':gap_match,'grounded_within_75mm':grounded,'passed':passed})
    group_map={g['group']:g for g in props['groups']};closures=[]
    for group_name in props['unresolved_groups']:
        names=set(group_map[group_name]['objects']);closed=names<=verified_names
        closures.append({'group':group_name,'components':len(names),'manual_components':len(names&manual_names),
                         'verified_components':len(names&verified_names),'resolved_by_manual_jobs':closed,
                         'jobs':[j['name'] for j in manual['jobs'] if names&set(j['objects'])]})
        check(closed,'Automatic unresolved group not completely resolved: '+group_name)
    report['manual_props']={'report':'manual_props.json','jobs':jobs,'total_components':len(manual_names),
                            'current_automatic_unresolved_count':len(closures),'closures':closures,
                            'all_current_unresolved_resolved':all(c['resolved_by_manual_jobs'] for c in closures),
                            'collision_review':'Explicit manual report problems checked; collision search not rerun'}

    # Use actual snapshots only. Missing pre-round navigation/camera files are
    # reported as a limitation, never labelled preserved from current hashes.
    preserved=[];manifest=read('before_manifest.json')
    for row in manifest:
        rel=Path(row['relative']);backup=log/'before'/rel
        if rel.suffix not in ('.gd','.tscn','.gdshader'):continue
        baseline=sha(backup);current=sha(root/rel)
        ok=baseline==row['sha256'].lower() and current==baseline
        preserved.append({'file':rel.as_posix(),'baseline_source':str(backup),'sha256':current,'unchanged':ok})
        check(ok,'Preserved runtime source differs from actual snapshot: '+str(rel))
    wanted=['fleet/harbor_route.gd','fleet/fleet_camera.gd','fleet/fleet_state.gd',
            'fleet_harbor.gd','fleet_harbor.tscn','environment/reference_environment.gd',
            'environment/harbor_environment.gd']
    prior=root/'captures/road_contacts_20261123/before_hashes.json'
    previous=json.loads(prior.read_text(encoding='utf8')) if prior.is_file() else []
    for rel in wanted:
        path=root/rel;match=next((r for r in previous if Path(r['path'])==path),None)
        row={'file':rel,'sha256':sha(path),'baseline_source':str(prior) if match else None,
             'unchanged':sha(path)==match['sha256'].lower() if match else None}
        preserved.append(row)
        if match:check(row['unchanged'],'Runtime source differs from prior-round hash: '+rel)
    missing=[r['file'] for r in preserved if r['baseline_source'] is None]
    if missing:report['limitations'].append('No actual pre-round file snapshot/hash for: '+', '.join(missing))
    report['preserved_runtime_sources']=preserved
    clearance_namespace={}
    exec(compile((root/'source/structure25_pier_clearance.py').read_text(encoding='utf8'),
                 'structure25_pier_clearance.py','exec'),clearance_namespace)
    clearance=clearance_namespace['audit_structure25_pier_clearance'](expected_pid)
    report['pier_clearance']={'report':'pier_clearance.json','passed':clearance['technical_pass']}
    check(clearance['technical_pass'],'Live pier landing/route rock clearance failed')
    report['dirty_after']=bool(bpy.data.is_dirty)
    check(report['dirty_after']==dirty_before,'Read-only audit changed dirty state')
    report['integrity_pass']=not report['integrity_failures']
    report['technical_pass']=bool(report['integrity_pass'] and structural['technical_pass'] is True)
    report['status']='completed';report['elapsed_seconds']=time.perf_counter()-started
    (log/'final_readonly.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    print(json.dumps({'integrity_pass':report['integrity_pass'],'technical_pass':report['technical_pass'],
                      'structural_failures':structural['failures'],'integrity_failures':report['integrity_failures'],
                      'manual_jobs':len(jobs),'manual_components':len(manual_names),'unresolved_closures':closures,
                      'dirty':report['dirty_after'],'limitations':report['limitations']},ensure_ascii=False))
    return report
