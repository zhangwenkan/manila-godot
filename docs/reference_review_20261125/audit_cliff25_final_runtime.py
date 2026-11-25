"""Independent final runtime audit for cliff25; never launches Blender/Godot.

Only --output writes a report. Requires final owned-session close and complete
post-export capture; screenshot-only preview runs cannot pass this audit.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'docs/reference_review_20261123'))
from audit_ground23_runtime import ART, NAMES, EXPECTED, digest, read_glb, read_accessor, import_cache_audit, texture_audit, capture_audit
SCENE = REPO/'demo/tropical_harbor_3d'
LOG = SCENE/'captures/cliff_contacts_20261125'
FIXED = {'town.glb','cargo_port.glb','boat.glb','cargo_ginseng.glb','cargo_jade.glb',
         'cargo_nutmeg.glb','cargo_silk.glb','ocean.glb','ground_rock.glb'}
RUNTIME = {'terrain.glb','coast.glb','foliage.glb','rocks.glb','ground_cover.glb','town.glb','shore_relief_height.json'}
NEW_IMAGES = {'C25_CliffRegion_Color.png','C25_CliffRegion_Height.exr','C25_GroundDetail.png'}

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def guarded(fn):
    try:return fn()
    except Exception as exc:return {'pass':False,'error':type(exc).__name__+': '+str(exc)}

def preserved_audit():
    rows = []
    for r in read(LOG/'before_manifest.json'):
        rel = Path(r['relative'])
        if rel.name not in FIXED:continue
        before,now = digest(LOG/'before'/rel),digest(SCENE/rel)
        rows.append({'file':rel.as_posix(),'baseline_sha256':before,'sha256':now,
                     'baseline_matches_manifest':before==r['sha256'].lower(),'unchanged':before==now})
    return {'count':len(rows),'assets':rows,'pass':len(rows)==9 and all(r['baseline_matches_manifest'] and r['unchanged'] for r in rows),
            'note':'Nine preserved GLBs include town and archived ground_rock, which is not loaded.'}

def export_audit():
    export,final,core,lock = [read(LOG/p) for p in ('export.json','final_readonly.json','final_structure_audit.json','final_cliff_structure_audit.json')]
    session = read(LOG/'session_start.json')
    expected = dict(export.get('runtime_asset_hashes',{}))
    expected.update({r['file']:r['sha256'] for r in export.get('exported',[])})
    rows = [{'file':n,'sha256':digest(ART/n),'matches_export':digest(ART/n)==expected.get(n,'').lower()} for n in sorted(RUNTIME)]
    images = final.get('source_state',{}).get('images',[])
    checks = {
        'export_completed_and_saved':export.get('status')=='completed' and export.get('source_saved') is True,
        'independent_final_source_clean':final.get('dirty_before') is False and final.get('dirty_after') is False,
        'current_session_identity':export.get('pid')==final.get('pid')==core.get('pid')==lock.get('pid')==session.get('pid'),
        'source_hash_matches_export_and_final':digest(SCENE/'source/harbor_shore_control_mcp.blend')==export.get('source_sha256')==final.get('source_sha256'),
        'all_runtime_hashes_recorded':RUNTIME<=set(expected),
        'all_runtime_hashes_match':all(r['matches_export'] for r in rows),
        'final_live_audit_pass':final.get('status')=='completed' and final.get('integrity_pass') is True and final.get('technical_pass') is True,
        'core_completed_without_failure':core.get('status')=='completed' and core.get('technical_pass') is True and core.get('failures')==[] and core.get('incomplete')==[],
        'whole_face_lock_pass':lock.get('technical_pass') is True and lock.get('export_checked') is True and lock.get('road_court_junction_full_face_lock',{}).get('changed_vertices_over_20um')==0,
        'live_export_triangle_equivalence':core.get('exported_terrain',{}).get('matches_source_at_20um') is True and core.get('exported_terrain',{}).get('sha256')==digest(ART/'terrain.glb'),
        'final_live_audit_postdates_export':(LOG/'final_readonly.json').stat().st_mtime_ns>=(LOG/'export.json').stat().st_mtime_ns,
        'source_preview_restored':final.get('source_state',{}).get('preview_restored') is True,
        'all_nine_packed_images_match_current_disk':len(images)==9 and final.get('source_state',{}).get('all_nine_images_packed_used_match_disk') is True and all(r.get('disk_sha256')==digest(ART/r['file']) for r in images),
        'nine_original_floors_preserved':export.get('nine_original_floors_geometry_and_pose_preserved') is True and len(export.get('floors_after',[]))==9,
        'semantic_support_review_pass':final.get('support_review',{}).get('technical_pass') is True,
        'seven_runtime_sources_real_round_baselines':final.get('seven_runtime_sources_have_actual_round_baseline') is True,
    }
    return {'checks':checks,'runtime_hashes':rows,'source_sha256':digest(SCENE/'source/harbor_shore_control_mcp.blend'),
            'export_observation':final.get('export_observation'),
            'report_hashes':{n:digest(LOG/n) for n in ('export.json','final_readonly.json','final_structure_audit.json','final_cliff_structure_audit.json')},
            'limitations':final.get('limitations',[]),'pass':all(checks.values())}

def runtime_sources_audit():
    wanted = {'fleet/harbor_route.gd','fleet/fleet_camera.gd','fleet/fleet_state.gd','fleet_harbor.gd','fleet_harbor.tscn',
              'environment/reference_environment.gd','environment/harbor_environment.gd','materials/landform_mass.gdshader'}
    allowed = {'environment/reference_environment.gd','materials/landform_mass.gdshader'}
    rows = []
    for r in read(LOG/'before_manifest.json'):
        rel = r['relative']
        if rel not in wanted:continue
        before,now = digest(LOG/'before'/rel),digest(SCENE/rel)
        rows.append({'file':rel,'baseline_sha256':before,'sha256':now,'baseline_matches_manifest':before==r['sha256'].lower(),
                     'changed':before!=now,'change_explicitly_allowed':rel in allowed})
    final = {r['file']:r['sha256'] for r in read(LOG/'final_readonly.json').get('runtime_sources',[])}
    for r in rows:r['matches_final_live_audit']=r['sha256']==final.get(r['file'])
    return {'sources':rows,'pass':{r['file'] for r in rows}==wanted and all(r['baseline_matches_manifest'] and r['matches_final_live_audit'] and (not r['changed'] or r['change_explicitly_allowed']) for r in rows)}

def signature(faces):
    q = np.rint(faces.astype(float)/.00002).astype(np.int64)
    order = np.lexsort((q[:,:,2],q[:,:,1],q[:,:,0]),axis=1)
    q = np.take_along_axis(q,order[:,:,None],axis=1).reshape(-1,9)
    return q[np.lexsort(q[:,::-1].T)]

def geometry_audit():
    with np.load(LOG/'sculpt.npz') as data:p,tri=data['positions'],data['triangles']
    world=p[:,[0,2,1]].copy();world[:,2]*=-1
    doc,binary=read_glb(ART/'terrain.glb')
    faces=[];rows=[]
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            points=read_accessor(doc,binary,primitive['attributes']['POSITION'])
            ids=read_accessor(doc,binary,primitive['indices']).ravel() if 'indices' in primitive else np.arange(len(points))
            assert primitive.get('mode',4)==4 and len(ids)%3==0 and len(ids)>0 and ids.min()>=0 and ids.max()<len(points) and np.isfinite(points).all()
            faces.append(points[ids.reshape(-1,3)])
            rows.append({'mesh':mesh.get('name'),'vertices':len(points),'triangles':len(ids)//3})
    actual=np.concatenate(faces);identity=True
    for node in doc.get('nodes',[]):
        for key,value in [('matrix',np.eye(4).ravel()),('translation',[0,0,0]),('rotation',[0,0,0,1]),('scale',[1,1,1])]:
            if key in node:identity &= np.allclose(node[key],value,atol=1e-8)
    matching=len(actual)==len(tri) and np.array_equal(signature(actual),signature(world[tri]))
    return {'source_snapshot_sha256':digest(LOG/'sculpt.npz'),'source_vertices':len(p),'source_triangles':len(tri),'exported_triangles':len(actual),
            'primitives':rows,'node_transforms_identity':bool(identity),'matches_authored_triangles_at_20um':matching,'pass':bool(identity and matching)}

def land_data_audit():
    with np.load(LOG/'land_data.npz') as data:expected=np.uint8(np.clip(data['land'][::-1],0,1)*255+.5)
    actual=np.asarray(Image.open(ART/'G23_LandUse.png'))
    return {'source_sha256':digest(LOG/'land_data.npz'),'png_sha256':digest(ART/'G23_LandUse.png'),
            'matches_flipped_quantized_authored_data':bool(np.array_equal(actual,expected)),'pass':bool(np.array_equal(actual,expected))}

def new_textures_audit():
    audit=read(LOG/'runtime_texture_audit.json')
    rows=[];checks={}
    checks['exact_three_new_images']=set(audit.get('textures',{}))==NEW_IMAGES
    for name,r in audit.get('textures',{}).items():
        source=ART/name
        cfg=source.with_suffix(source.suffix+'.import')
        params=dict(re.findall(r'^([^=\r\n]+)=([^\r\n]+)$',cfg.read_text(encoding='utf-8-sig'),re.M))
        cache=REPO/params['path'].strip('"')[6:]
        settings=dict(EXPECTED)
        if name.endswith('.exr'):settings['compress/mode']='3'
        ok_settings=all(params.get(k)==v for k,v in settings.items())
        raw_current=True
        probe=read(LOG/'godot_texture_cache_probe.json')['textures'][name]
        for part in ('source','cache'):
            raw_path=LOG/probe[part]['raw_file']
            raw_current &= raw_path.is_file() and raw_path.stat().st_mtime_ns>=source.stat().st_mtime_ns
        row={'file':name,'uid':params.get('uid','').strip('"'),'sha256':digest(source),
             'settings_ok':ok_settings,'cache_current':import_cache_audit(source).get('pass',False),
             'report_pass':r.get('pass') is True,'current_source_matches_report':digest(source)==r.get('source_sha256'),
             'current_cache_matches_report':digest(cache)==r.get('cache_sha256'),'raw_probe_postdates_source':bool(raw_current)}
        row['pass']=all(v for k,v in row.items() if k not in ('file','uid','sha256'))
        rows.append(row)
    wiring=audit.get('wiring',{})
    checks['texture_report_pass']=audit.get('pass') is True
    checks['shader_matches_texture_audit']=digest(SCENE/'materials/landform_mass.gdshader')==wiring.get('shader_sha256')
    checks['environment_matches_texture_audit']=digest(SCENE/'environment/reference_environment.gd')==wiring.get('environment_sha256')
    return {'checks':checks,'images':rows,'report_sha256':digest(LOG/'runtime_texture_audit.json'),
            'limitations':audit.get('limitations',[]),'pass':all(checks.values()) and all(r['pass'] for r in rows)}

def wiring_audit():
    project=(REPO/'project.godot').read_text(encoding='utf8');entry=(SCENE/'fleet_harbor.gd').read_text(encoding='utf8')
    env='\n'.join(x.split('#',1)[0] for x in (SCENE/'environment/reference_environment.gd').read_text(encoding='utf8').splitlines())
    shader=re.sub(r'//[^\n]*','',(SCENE/'materials/landform_mass.gdshader').read_text(encoding='utf8'))
    checks={
      'unique_default_scene':'run/main_scene="res://demo/tropical_harbor_3d/fleet_harbor.tscn"' in project,
      'reference_art_default':'var reference_art := true' in entry and 'reference_art = not (' in entry,
      'reference_environment_selected':'reference_environment.gd").new(self) if reference_art' in entry,
      'current_shader_loaded':'materials/landform_mass.gdshader")' in env,
      'terrain_material_applied':'load(ART + "terrain.glb")' in env and 'mesh.set_surface_override_material(surface, sand_material)' in env,
      'archived_rock_inactive':'ground_rock.glb' not in env,
      'ground_cover_loaded':'load(ART + "ground_cover.glb")' in env,
      'six_surface_bindings':all(f'ART + "G23_{n}.png"' in env for n in NAMES),
      'surface_bind_enabled':'_bind_ground_surfaces(sand_material)' in env and 'material.set_shader_parameter("ground_surface_enabled", true)' in env,
      'land_use_linear':bool(re.search(r'uniform sampler2D ground_land_use\s*:\s*(?![^;]*source_color)[^;]+;',shader)),
      'five_color_surfaces_srgb':all(bool(re.search(r'uniform sampler2D ground_'+role+r'\s*:\s*source_color',shader)) for role in ('grass','rock','path','soil','sand')),
    }
    return {'checks':checks,'pass':all(checks.values())}

def captures_audit(folder):
    item=capture_audit(folder);folder=Path(item['path']);result_path=folder/'art_result.json';result=read(result_path)
    inputs=[ART/n for n in RUNTIME|NEW_IMAGES]+[ART/f'G23_{n}.png' for n in NAMES]
    inputs += [SCENE/'environment/reference_environment.gd',SCENE/'materials/landform_mass.gdshader']
    latest=max(inputs,key=lambda p:p.stat().st_mtime_ns)
    required={'runtime_unequal_dice.png','runtime_wide_gap.png','runtime_right_lane_passage.png','runtime_left_lane_passage.png',
              'runtime_catch_up.png','runtime_right_arrives_first.png','runtime_all_arrive.png'}
    frames=[folder/n for n in result.get('frames',[])]
    item['full_33_frame_set']=len(frames)==33 and required<=set(result.get('frames',[]))
    item['all_frames_postdate_runtime_and_export']=bool(frames) and all(p.exists() and p.stat().st_mtime_ns>=max(latest.stat().st_mtime_ns,(LOG/'export.json').stat().st_mtime_ns) for p in frames)
    close_path=LOG/'session_close.json';closed=read(close_path) if close_path.exists() else {}
    session=read(LOG/'session_start.json');export=read(LOG/'export.json')
    item['owned_blender_closed_before_capture']=bool(closed.get('normal_quit_requested') is True and closed.get('process_exited') is True
        and closed.get('pid')==session.get('pid') and closed.get('port')==session.get('port')
        and closed.get('dirty') is False and closed.get('source_sha256')==export.get('source_sha256')
        and frames and all(p.exists() and close_path.stat().st_mtime_ns<=p.stat().st_mtime_ns for p in frames))
    timing=result.get('timing') or {}
    item['timing_sample_present']=timing.get('frames',0)>0 and timing.get('wall_seconds',0)>0 and all(isinstance(timing.get(k),(int,float)) and np.isfinite(timing[k]) and timing[k]>0 for k in ('mean_ms','p95_ms'))
    item['latest_runtime_input']={'path':str(latest),'sha256':digest(latest)}
    item['timing_note']='About five seconds at the reported gameplay location; no full-game performance or causal attribution.'
    item['pass']=all(item.get(k,False) for k in ('full_runtime_checks_pass','full_33_frame_set','all_frames_postdate_runtime_and_export','owned_blender_closed_before_capture','timing_sample_present'))
    return item

def audit(capture):
    report={'read_only':True,'visual_accepted':False,'checked_at_utc':datetime.now(timezone.utc).isoformat()}
    for key,fn in [('preserved_assets',preserved_audit),('current_export_and_live_report',export_audit),('runtime_sources',runtime_sources_audit),
                   ('terrain_geometry',geometry_audit),('land_data',land_data_audit),('new_textures',new_textures_audit),('current_wiring',wiring_audit)]:report[key]=guarded(fn)
    report['textures']={name:guarded(lambda name=name:texture_audit(name)) for name in NAMES}
    report['glb_import_caches']={name:guarded(lambda name=name:import_cache_audit(ART/name)) for name in sorted(RUNTIME) if name.endswith('.glb')}
    report['capture']=guarded(lambda:captures_audit(capture))
    uids=[r.get('uid') for r in report['textures'].values()]+[r.get('uid') for r in report['new_textures'].get('images',[])]
    report['texture_uids_unique']=len(uids)==9 and bool(all(uids) and len(set(uids))==9)
    groups=['preserved_assets','current_export_and_live_report','runtime_sources','terrain_geometry','land_data','new_textures','current_wiring','capture']
    failed=[name for name in groups if not report[name].get('pass')]
    failed += ['texture:'+n for n,r in report['textures'].items() if not r.get('pass')]
    failed += ['glb_cache:'+n for n,r in report['glb_import_caches'].items() if not r.get('pass')]
    if not report['texture_uids_unique']:failed.append('texture_uids_unique')
    report['failed_sections']=failed;report['technical_pass']=not failed
    report['acceptance_boundary']='Technical consistency and regression only. Visual review remains separate.'
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=audit(args.capture)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'technical_pass':report['technical_pass'],'failed_sections':report['failed_sections'],'capture':report['capture'],'output':str(args.output)},ensure_ascii=False,indent=2))
    raise SystemExit(0 if report['technical_pass'] else 1)
