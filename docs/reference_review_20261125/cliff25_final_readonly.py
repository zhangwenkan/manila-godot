"""Final independent live audit; define and call final_cliff25_readonly(pid).

No Blender mutation, update, save, export or production-script replay. Only
audit JSON files in this round's capture directory are written.
"""
from pathlib import Path
import hashlib
import json
import os
import time


def final_cliff25_readonly(expected_pid):
    import bpy
    root = Path(bpy.data.filepath).parent.parent
    log = root/'captures/cliff_contacts_20261125'
    reviews = root.parents[1]/'docs/reference_review_20261125'
    read = lambda name:json.loads((log/name).read_text(encoding='utf-8-sig'))
    sha = lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
    session = read('session_start.json')
    assert not bpy.app.background and os.getpid() == expected_pid == session['pid']
    assert bpy.types.blendermcp_server.port == session['port']
    assert Path(bpy.data.filepath).resolve() == (root/'source/harbor_shore_control_mcp.blend').resolve()
    started = time.perf_counter()
    dirty_before = bool(bpy.data.is_dirty)
    failures = []
    def check(ok, message):
        if not ok:failures.append(message)
    report = {'read_only':True,'status':'running','visual_accepted':False,'pid':expected_pid,
              'port':session['port'],'dirty_before':dirty_before,'source':bpy.data.filepath}
    namespace = {}
    exec(compile((reviews/'cliff25_live_audit.py').read_text(encoding='utf8'),'cliff25_live_audit.py','exec'),namespace)
    structural = namespace['audit_cliff25'](expected_pid,check_export=True)
    core = read('structure_audit.json')
    # Retain final, explicitly export-enabled snapshots independent of any
    # later preparatory call which may overwrite the working report names.
    for name,value in [('final_cliff_structure_audit.json',structural),('final_structure_audit.json',core)]:
        (log/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
    check(structural['technical_pass'] is True,'Final full-face and structure audit failed')
    export = read('export.json')
    check(export.get('status') == 'completed' and export.get('source_saved') is True,'Export not completed and saved')
    check(not dirty_before,'Source dirty at independent final audit')
    check(sha(bpy.data.filepath) == export.get('source_sha256'),'Saved source differs from export hash')
    report['export_observation'] = {'source_saved':export.get('source_saved'),'immediate_dirty':export.get('dirty'),
                                   'independent_live_dirty':dirty_before,'source_hash_matches':sha(bpy.data.filepath)==export.get('source_sha256'),
                                   'note':'Immediate exporter dirty flag and later independent live state are preserved as separate observations; no causal inference.'}
    hashes = dict(export.get('runtime_asset_hashes',{}))
    hashes.update({r['file']:r['sha256'] for r in export.get('exported',[])})
    runtime = {'terrain.glb','coast.glb','foliage.glb','rocks.glb','ground_cover.glb','town.glb','shore_relief_height.json'}
    check(runtime <= set(hashes),'Missing runtime asset hashes in export record')
    rows = []
    for name in sorted(runtime):
        actual = sha(root/'assets/reference'/name)
        matches = actual == hashes.get(name,'').lower()
        rows.append({'file':name,'sha256':actual,'matches_export':matches})
        check(matches,'Runtime hash differs: '+name)
    report['runtime_hashes'] = rows
    check(export.get('nine_original_floors_geometry_and_pose_preserved') is True and len(export.get('floors_after',[])) == 9,'Nine floor preservation evidence incomplete')
    terrain = bpy.data.objects['C25_ContourBuiltCoast']
    mat = terrain.data.materials[0]
    nodes = mat.node_tree.nodes
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    from_node = lambda socket:socket.links[0].from_node.name if len(socket.links)==1 else None
    base_node = from_node(bsdf.inputs['Base Color'])
    normal_node = from_node(bsdf.inputs['Normal'])
    rock_node = from_node(nodes['G23Preview Rock weight'].inputs[1])
    preview_ok = bool(base_node and base_node.startswith('G23Preview ') and normal_node and normal_node.startswith('C25Preview ') and rock_node and rock_node.startswith('C25Preview '))
    check(preview_ok,'Source regional color/normal material is not restored')
    temp = bpy.data.collections.get('STRUCTURE23_EXPORT_TEMP')
    check(temp is None,'Export temporary collection remains')
    image_specs = [(f'G23_{n}',f'G23_{n}.png') for n in ('Grass','Rock','Path','Soil','Sand','LandUse')]
    image_specs += [('C25_CliffRegion_Color','C25_CliffRegion_Color.png'),('C25_CliffRegion_Height','C25_CliffRegion_Height.exr'),('C25_GroundDetail','C25_GroundDetail.png')]
    images = []
    for name,filename in image_specs:
        im = bpy.data.images.get(name)
        if im is None:
            matches = [n.image for n in nodes if n.type=='TEX_IMAGE' and n.image and Path(bpy.path.abspath(n.image.filepath)).name == filename]
            im = matches[0] if matches else None
        packed = bool(im and im.packed_file)
        packed_sha = hashlib.sha256(bytes(im.packed_file.data)).hexdigest() if packed else None
        disk_sha = sha(root/'assets/reference'/filename)
        used = bool(im and any(n.type=='TEX_IMAGE' and n.image==im for n in nodes))
        item = {'file':filename,'image':im.name if im else None,'packed':packed,'used_by_source_material':used,
                'colorspace':im.colorspace_settings.name if im else None,'packed_sha256':packed_sha,
                'disk_sha256':disk_sha,'packed_matches_disk':packed_sha==disk_sha}
        images.append(item)
        check(packed and used and packed_sha==disk_sha,'Packed/material/disk image mismatch: '+filename)
    report['source_state'] = {'base_color_from_node':base_node,'normal_from_node':normal_node,
                              'rock_color_from_node':rock_node,'preview_restored':preview_ok,
                              'temporary_collection_removed':temp is None,'images':images,
                              'all_nine_images_packed_used_match_disk':len(images)==9 and all(r['packed_matches_disk'] and r['used_by_source_material'] for r in images)}
    wanted = {'fleet/harbor_route.gd','fleet/fleet_camera.gd','fleet/fleet_state.gd','fleet_harbor.gd','fleet_harbor.tscn',
              'environment/reference_environment.gd','environment/harbor_environment.gd','materials/landform_mass.gdshader'}
    allowed = {'environment/reference_environment.gd','materials/landform_mass.gdshader'}
    source_rows = []
    for r in read('before_manifest.json'):
        rel = r['relative']
        if rel not in wanted:continue
        backup = log/'before'/rel
        baseline,current = sha(backup),sha(root/rel)
        ok = baseline==r['sha256'].lower()
        changed = current != baseline
        source_rows.append({'file':rel,'baseline_source':str(backup),'baseline_sha256':baseline,'sha256':current,
                            'baseline_matches_manifest':ok,'changed':changed,'change_explicitly_allowed':rel in allowed})
        check(ok and (not changed or rel in allowed),'Runtime source baseline/preservation failed: '+rel)
    check({r['file'] for r in source_rows} == wanted,'Missing actual new-round runtime code snapshots')
    report['runtime_sources'] = source_rows
    report['seven_runtime_sources_have_actual_round_baseline'] = (wanted-{'materials/landform_mass.gdshader'}) <= {r['file'] for r in source_rows}
    namespace = {}
    exec(compile((reviews/'cliff25_support_readonly.py').read_text(encoding='utf8'),'cliff25_support_readonly.py','exec'),namespace)
    support = namespace['audit_cliff25_support'](expected_pid)
    report['support_review'] = {'report':'support_readonly.json','technical_pass':support['technical_pass'],
                                'affected_groups':support['affected_groups'],'support_failure_groups':support['support_failure_groups']}
    check(support['technical_pass'] is True,'New terrain support review failed or is incomplete')
    report['dirty_after'] = bool(bpy.data.is_dirty)
    check(report['dirty_after'] is False and report['dirty_after']==dirty_before,'Read-only final audit has a dirty source')
    report['source_sha256'] = sha(bpy.data.filepath)
    report['integrity_failures'] = failures
    # Stable summary key for the caller's assert, alongside the precise
    # integrity name retained by the independent runtime audit.
    report['failures'] = failures[:]
    report['integrity_pass'] = not failures
    report['technical_pass'] = not failures
    report['status'] = 'completed'
    report['elapsed_seconds'] = time.perf_counter()-started
    report['limitations'] = read('source_preview.json').get('limitations',[]) + support.get('limitations',[])
    (log/'final_readonly.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:report[k] for k in ('technical_pass','integrity_failures','dirty_after','source_sha256')},ensure_ascii=False))
    return report
