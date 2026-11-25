"""Independent read-only check of the completed structure revision.

Never opens Blender/Godot or changes assets. --output writes only this audit.
Uses this revision's baseline/export records, not historical G23 acceptance.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

import numpy as np
from PIL import Image

from audit_ground23_runtime import (
    ROOT, ART, NAMES, digest, read_glb, read_accessor,
    import_cache_audit, texture_audit, capture_audit,
)

SCENE = ROOT / 'demo/tropical_harbor_3d'
LOG = SCENE / 'captures/terrain_structure_20261123'
FIXED = {'cargo_port.glb', 'boat.glb', 'cargo_ginseng.glb', 'cargo_jade.glb',
         'cargo_nutmeg.glb', 'cargo_silk.glb', 'ocean.glb', 'ground_rock.glb'}
RUNTIME = {'terrain.glb', 'coast.glb', 'foliage.glb', 'rocks.glb',
           'ground_cover.glb', 'town.glb', 'shore_relief_height.json'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def guarded(fn):
    try:
        return fn()
    except Exception as exc:
        return {'pass': False, 'error': type(exc).__name__+': '+str(exc)}


def preserved_audit():
    rows = []
    for item in read(LOG/'before_manifest.json'):
        relative = Path(item['relative'])
        if relative.name not in FIXED:
            continue
        original, actual = LOG/'before'/relative, SCENE/relative
        base, now = digest(original), digest(actual)
        rows.append({'file': relative.as_posix(), 'baseline_sha256': base,
                     'sha256': now, 'baseline_matches_manifest': base == item['sha256'].lower(),
                     'unchanged': base == now})
    return {'count': len(rows), 'assets': rows,
            'pass': len(rows) == 8 and all(x['baseline_matches_manifest'] and x['unchanged'] for x in rows),
            'note': 'ground_rock.glb is retained for history and is not loaded by the current scene.'}


def export_audit():
    export, final, core = (read(LOG/name) for name in ('export.json','final_readonly.json','final_structure_audit.json'))
    session = read(LOG/'session_start.json')
    expected = dict(export.get('runtime_asset_hashes', {}))
    expected.update({item['file']: item['sha256'] for item in export.get('exported', [])})
    rows = [{'file': name, 'sha256': digest(ART/name),
             'matches_export': digest(ART/name) == expected.get(name, '').lower()}
            for name in sorted(RUNTIME)]
    source = SCENE/'source/harbor_shore_control_mcp.blend'
    checks = {
        'export_completed_saved_clean': export.get('status') == 'completed' and export.get('source_saved') is True and export.get('dirty') is False,
        'current_session_identity': export.get('pid') == final.get('pid') == core.get('pid') == session.get('pid'),
        'saved_source_hash_matches': digest(source) == export.get('source_sha256'),
        'all_runtime_hashes_recorded': RUNTIME <= set(expected),
        'all_runtime_hashes_match': all(x['matches_export'] for x in rows),
        'final_source_integrity_and_structure_pass': final.get('integrity_pass') is True and final.get('technical_pass') is True and final.get('dirty_after') is False,
        'core_completed_without_failure': core.get('status') == 'completed' and core.get('technical_pass') is True and core.get('failures') == [] and core.get('incomplete') == [],
        'live_source_export_triangle_match': core.get('exported_terrain',{}).get('matches_source_at_20um') is True,
        'live_core_hash_is_current': core.get('exported_terrain',{}).get('sha256') == digest(ART/'terrain.glb'),
        'final_review_follows_export': (LOG/'final_readonly.json').stat().st_mtime_ns >= (LOG/'export.json').stat().st_mtime_ns,
        'packed_land_matches_current_png': final.get('source_state',{}).get('land_packed_matches_disk') is True and final.get('source_state',{}).get('land_disk_sha256') == digest(ART/'G23_LandUse.png'),
        'whole_pier_rock_clearance_pass': final.get('pier_clearance',{}).get('passed') is True,
        'nine_floors_preserved': export.get('nine_original_floors_geometry_and_pose_preserved') is True and len(export.get('floors_after',[])) == 9,
    }
    return {'checks': checks, 'runtime_hashes': rows, 'source_sha256': digest(source),
            'report_hashes': {name:digest(LOG/name) for name in ('export.json','final_readonly.json','final_structure_audit.json')},
            'limitations': final.get('limitations', []), 'pass': all(checks.values())}


def signature(faces):
    q = np.rint(faces.astype(float)/.00002).astype(np.int64)
    order = np.lexsort((q[:,:,2],q[:,:,1],q[:,:,0]),axis=1)
    q = np.take_along_axis(q,order[:,:,None],axis=1).reshape(-1,9)
    return q[np.lexsort(q[:,::-1].T)]


def geometry_audit():
    data = np.load(LOG/'slope_cleanup.npz')
    p, tri = data['positions'], data['triangles']
    world = p[:,[0,2,1]].copy(); world[:,2] *= -1
    document, binary = read_glb(ART/'terrain.glb')
    faces, rows = [], []
    for mesh in document['meshes']:
        for item in mesh['primitives']:
            points = read_accessor(document,binary,item['attributes']['POSITION'])
            ids = read_accessor(document,binary,item['indices']).ravel() if 'indices' in item else np.arange(len(points))
            assert item.get('mode',4)==4 and len(ids)%3==0
            assert len(ids)>0 and ids.min()>=0 and ids.max()<len(points) and np.isfinite(points).all()
            faces.append(points[ids.reshape(-1,3)])
            rows.append({'mesh':mesh.get('name'),'vertices':len(points),'triangles':len(ids)//3})
    actual = np.concatenate(faces)
    identity = True
    for node in document.get('nodes',[]):
        if 'matrix' in node: identity &= np.allclose(np.array(node['matrix']).reshape(4,4),np.eye(4),atol=1e-8)
        if 'translation' in node: identity &= np.allclose(node['translation'],[0,0,0],atol=1e-8)
        if 'rotation' in node: identity &= np.allclose(node['rotation'],[0,0,0,1],atol=1e-8)
        if 'scale' in node: identity &= np.allclose(node['scale'],[1,1,1],atol=1e-8)
    matching = len(actual)==len(tri) and np.array_equal(signature(actual),signature(world[tri]))
    return {'source_snapshot_sha256':digest(LOG/'slope_cleanup.npz'),
            'source_vertices':len(p),'source_triangles':len(tri),'exported_triangles':len(actual),
            'primitives':rows,'node_transforms_identity':bool(identity),
            'matches_authored_triangles_at_20um':matching,'pass':bool(identity and matching)}


def wiring_audit():
    project=(ROOT/'project.godot').read_text(encoding='utf8')
    entry=(SCENE/'fleet_harbor.gd').read_text(encoding='utf8')
    env_path=SCENE/'environment/reference_environment.gd'
    shader_path=SCENE/'materials/landform_mass.gdshader'
    env='\n'.join(x.split('#',1)[0] for x in env_path.read_text(encoding='utf8').splitlines())
    shader=re.sub(r'//[^\n]*','',shader_path.read_text(encoding='utf8'))
    checks={
        'unique_default_scene': 'run/main_scene="res://demo/tropical_harbor_3d/fleet_harbor.tscn"' in project,
        'default_reference_art': 'var reference_art := true' in entry and 'reference_art = not (' in entry,
        'reference_environment_selected': 'reference_environment.gd").new(self) if reference_art' in entry,
        'current_shader_loaded': 'materials/landform_mass.gdshader")' in env,
        'terrain_loaded_and_material_assigned': 'load(ART + "terrain.glb")' in env and 'mesh.set_surface_override_material(surface, sand_material)' in env,
        'archived_rock_asset_inactive': 'ground_rock.glb' not in env,
        'ground_cover_loaded': 'load(ART + "ground_cover.glb")' in env,
        'six_surface_bindings': all(f'ART + "G23_{name}.png"' in env for name in NAMES),
        'surface_binding_enabled': '_bind_ground_surfaces(sand_material)' in env and 'material.set_shader_parameter("ground_surface_enabled", true)' in env,
        'land_use_linear': bool(re.search(r'uniform sampler2D ground_land_use\s*:\s*(?![^;]*source_color)[^;]+;',shader)),
        'five_color_surfaces_srgb': all(bool(re.search(r'uniform sampler2D ground_'+role+r'\s*:\s*source_color',shader)) for role in ('grass','rock','path','soil','sand')),
    }
    return {'checks':checks,'environment_sha256':digest(env_path),'shader_sha256':digest(shader_path),
            'scope':'Current static scene and shader wiring; runtime compilation is checked in capture logs.',
            'pass':all(checks.values())}


def land_data_audit():
    with np.load(LOG/'land_data.npz') as data:
        expected=np.round(np.clip(data['land'][::-1],0,1)*255).astype(np.uint8)
    actual=np.array(Image.open(ART/'G23_LandUse.png'))
    return {'authored_array_bottom_up':True,'source_array_sha256':digest(LOG/'land_data.npz'),
            'png_sha256':digest(ART/'G23_LandUse.png'),'png_shape':list(actual.shape),
            'matches_flipped_quantized_authored_data':bool(np.array_equal(actual,expected)),
            'pass':bool(np.array_equal(actual,expected))}


def captures_audit(folder):
    item=capture_audit(folder)
    folder=Path(item['path'])
    inputs=[ART/name for name in RUNTIME]+[ART/f'G23_{name}.png' for name in NAMES]
    inputs += [SCENE/'environment/reference_environment.gd',SCENE/'materials/landform_mass.gdshader']
    latest=max(inputs,key=lambda p:p.stat().st_mtime_ns)
    result_path=folder/'art_result.json'
    result=read(result_path)
    required={'runtime_unequal_dice.png','runtime_wide_gap.png','runtime_right_lane_passage.png',
              'runtime_left_lane_passage.png','runtime_catch_up.png','runtime_right_arrives_first.png','runtime_all_arrive.png'}
    item['full_33_frame_set']=len(result.get('frames',[]))==33 and required<=set(result.get('frames',[]))
    item['postdates_current_runtime_inputs']=result_path.stat().st_mtime_ns>=latest.stat().st_mtime_ns
    item['latest_runtime_input']={'path':str(latest),'sha256':digest(latest)}
    frame_paths=[folder/name for name in result.get('frames',[])]
    export_completed=LOG/'export.json'
    item['all_frames_postdate_completed_export']=bool(frame_paths) and all(
        p.exists() and p.stat().st_mtime_ns>=export_completed.stat().st_mtime_ns for p in frame_paths)
    item['all_frames_postdate_current_runtime_inputs']=bool(frame_paths) and all(
        p.exists() and p.stat().st_mtime_ns>=latest.stat().st_mtime_ns for p in frame_paths)
    close_path=LOG/'session_close.json'
    closed=read(close_path) if close_path.exists() else {}
    item['owned_blender_closed_before_capture']=(closed.get('normal_quit_requested') is True and closed.get('process_exited') is True
         and bool(frame_paths) and all(p.exists() and close_path.stat().st_mtime_ns<=p.stat().st_mtime_ns for p in frame_paths))
    item['timing_note']='About five seconds at the reported gameplay location; not whole-game performance or a cause attribution.'
    timing=result.get('timing') or {}
    item['timing_sample_present']=(timing.get('frames',0)>0 and timing.get('wall_seconds',0)>0
        and all(isinstance(timing.get(key),(int,float)) and np.isfinite(timing[key]) and timing[key]>0
                for key in ('mean_ms','p95_ms')))
    item['full_runtime_checks_pass']=all((item.get('full_runtime_checks_pass',False),item['full_33_frame_set'],
            item['postdates_current_runtime_inputs'],item['all_frames_postdate_completed_export'],
            item['all_frames_postdate_current_runtime_inputs'],item['owned_blender_closed_before_capture'],item['timing_sample_present']))
    item['pass']=item['full_runtime_checks_pass']
    return item


def audit(capture):
    report={'read_only':True,'visual_accepted':False,'checked_at_utc':datetime.now(timezone.utc).isoformat()}
    report['preserved_assets']=guarded(preserved_audit)
    report['current_export_and_live_report']=guarded(export_audit)
    report['terrain_geometry']=guarded(geometry_audit)
    report['textures']={name:guarded(lambda name=name:texture_audit(name)) for name in NAMES}
    report['land_data']=guarded(land_data_audit)
    report['current_wiring']=guarded(wiring_audit)
    report['glb_import_caches']={name:guarded(lambda name=name:import_cache_audit(ART/name)) for name in sorted(RUNTIME) if name.endswith('.glb')}
    report['capture']=guarded(lambda:captures_audit(capture))
    uids=[x.get('uid') for x in report['textures'].values()]
    report['texture_uids_unique']=bool(all(uids) and len(set(uids))==len(NAMES))
    groups=['preserved_assets','current_export_and_live_report','terrain_geometry','land_data','current_wiring','capture']
    report['failed_sections']=[name for name in groups if not report[name].get('pass')]
    report['failed_sections'] += ['texture:'+name for name,row in report['textures'].items() if not row.get('pass')]
    report['failed_sections'] += ['glb_cache:'+name for name,row in report['glb_import_caches'].items() if not row.get('pass')]
    if not report['texture_uids_unique']:report['failed_sections'].append('texture_uids_unique')
    report['technical_pass']=not report['failed_sections']
    report['acceptance_boundary']='Technical consistency and regression only. The appearance remains subject to visual review.'
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=audit(args.capture)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'technical_pass':result['technical_pass'],'failed_sections':result['failed_sections'],
        'capture':result['capture'],'output':str(args.output)},ensure_ascii=False,indent=2))
    raise SystemExit(0 if result['technical_pass'] else 1)
