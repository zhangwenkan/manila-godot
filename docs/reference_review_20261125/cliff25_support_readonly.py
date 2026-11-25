"""Read-only live support scan. Define then call audit_cliff25_support(owned_pid).

Uses older reports ONLY as semantic membership catalogues. No old placement
scripts or old transforms are executed/applied. Bottom support geometry is
sampled in this round's immutable pose and the current live pose.
"""
from pathlib import Path
import hashlib
import json
import os
import numpy as np


def audit_cliff25_support(expected_pid):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    root = Path(bpy.data.filepath).parent.parent
    log = root / 'captures/cliff_contacts_20261125'
    previous = root / 'captures/terrain_structure_20261123'
    read = lambda p: json.loads(Path(p).read_text(encoding='utf-8-sig'))
    session = read(log/'session_start.json')
    assert not bpy.app.background and os.getpid() == expected_pid == session['pid']
    assert bpy.types.blendermcp_server.port == session['port']
    dirty_before = bool(bpy.data.is_dirty)
    terrain = bpy.data.objects['C25_ContourBuiltCoast']
    assert np.max(abs(np.asarray(terrain.matrix_world)-np.eye(4))) < 1e-7
    mesh = terrain.data
    base = np.load(log/'baseline.npz')
    old_bvh = BVHTree.FromPolygons([Vector(p) for p in base['positions']], base['triangles'].tolist(), all_triangles=True)
    new_bvh = BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices], [list(p.vertices) for p in mesh.polygons], all_triangles=True)
    records = {r['name']:r for r in read(log/'objects_before.json')}
    catalog = read(previous/'props.json')
    manual = read(previous/'manual_props.json')
    manual_names = {n for j in manual['jobs'] for n in j['objects']}
    groups = []
    for g in catalog['groups']:
        names = [n for n in g['objects'] if n not in manual_names]
        if names:
            groups.append({'group':g['group'],'kind':g['kind'],'objects':names,
                           'explicit_supports':[g['support_object']] if g['support_object'] in names else []})
    for job in manual['jobs']:
        groups.append({'group':'manual:'+job['name'],'kind':'manual_prop',
                       'objects':job['objects'],'explicit_supports':job['supports']})
    claimed = [n for g in groups for n in g['objects']]
    assert len(claimed) == len(set(claimed)), 'Semantic catalogue has duplicate memberships'
    cache = {}
    def pts(name):
        if name not in cache:
            obj = bpy.data.objects[name]
            assert name in records and obj.type == 'MESH'
            assert len(obj.data.vertices) == records[name]['vertices'], 'Non-grass component mesh changed: '+name
            raw = np.empty((len(obj.data.vertices),3), np.float32)
            obj.data.vertices.foreach_get('co', raw.ravel())
            old = np.asarray(records[name]['matrix'],float)
            now = np.asarray(obj.matrix_world,float)
            cache[name] = (raw.astype(float)@old[:3,:3].T+old[:3,3], raw.astype(float)@now[:3,:3].T+now[:3,3])
        return cache[name]
    def ray(bvh, q):
        hit = bvh.ray_cast(Vector((float(q[0]),float(q[1]),80)),Vector((0,0,-1)),200)[0]
        return None if hit is None else float(hit.z)
    def samples(name, indices):
        before, now = pts(name)
        rows = []
        for a,b in zip(before[indices],now[indices]):
            old = ray(old_bvh,a); changed = ray(new_bvh,a); current = ray(new_bvh,b)
            if old is None or changed is None or current is None:
                rows.append({'missing':True});continue
            rows.append({'old_gap':float(a[2]-old),'new_gap':float(b[2]-current),
                         'terrain_delta_at_old_foot':changed-old,
                         'old_position':a.tolist(),'current_position':b.tolist()})
        return rows
    def summarize(g, support_points):
        missing = sum(bool(r.get('missing')) for r in support_points)
        valid = [r for r in support_points if not r.get('missing')]
        affected = [r for r in valid if abs(r['terrain_delta_at_old_foot']) > .00002]
        gaps = [r['new_gap'] for r in valid]
        oldg = [r['old_gap'] for r in valid]
        affected_gaps = [r['new_gap'] for r in affected]
        rigid = g['kind'] not in ('tree','palm','shrub','rock','building_supported_goods')
        # Existing embedding and an intentionally sunk root are not new errors.
        worsened = [r for r in affected if
            (r['new_gap'] > .075 and r['new_gap'] > r['old_gap']+.01) or
            (rigid and r['new_gap'] < -.075 and r['new_gap'] < r['old_gap']-.01)]
        return {**g,'support_sample_count':len(support_points),'missing_ground':missing,
                'affected_samples':len(affected),'affected_by_new_terrain':bool(affected),
                'old_gap_range_m':[min(oldg),max(oldg)] if oldg else None,
                'current_gap_range_m':[min(gaps),max(gaps)] if gaps else None,
                'affected_current_gap_range_m':[min(affected_gaps),max(affected_gaps)] if affected else None,
                'max_abs_terrain_change_m':max((abs(r['terrain_delta_at_old_foot']) for r in valid),default=0),
                'new_or_worsened_support_failures':len(worsened),'failure_examples':worsened[:12],
                'component_matrices_changed':[n for n in g['objects'] if np.max(abs(np.asarray(bpy.data.objects[n].matrix_world)-np.asarray(records[n]['matrix'])))>.00002]}
    results = []; excluded = []; errors = []
    for g in groups:
        if g['kind'] == 'building_supported_goods':
            excluded.append({'group':g['group'],'objects':g['objects'],'reason':'Hanging goods are building-supported, not ground furniture.'});continue
        try:
            names = g['objects']
            if g['kind'] in ('tree','palm'):
                supports = g['explicit_supports']
            elif g['kind'] == 'manual_prop':
                supports = g['explicit_supports']
            else:
                bottom = min(float(pts(n)[0][:,2].min()) for n in names)
                supports = [n for n in names if float(pts(n)[0][:,2].min()) <= bottom+.08]
                supports = sorted(set(supports+g['explicit_supports']))
            support_points = []
            for name in supports:
                p = pts(name)[0]
                ids = np.flatnonzero(p[:,2] <= p[:,2].min()+.025)
                support_points.extend(samples(name,ids))
            results.append(summarize({**g,'actual_support_components':supports},support_points))
        except Exception as exc:
            errors.append({'group':g['group'],'error':str(exc)})
    # Inventory gaps are reported, never silently treated as free-standing props.
    # Query actual bottom vertices for unclassified meshes intersecting changed
    # ground. Building/grass names are excluded explicitly and listed below.
    exclusions = ('Town_','TR20_','Hut_','D19_Hut','D19_Thatch','D19_Reed','D19_RidgeBinding',
                  'D19_EaveRafter','D19_Door','Pier_','Arrival_','Pile_Lashing','S20_DeckPeg',
                  'S20_PileEndGrain','S20_MooringKnot','S20_RopeTail','S20_PileBracket',
                  'D19_Deck','D19_Pile','D19_Mooring','D19_RopeTail','C25_','G23_','L24_')
    unclassified = []
    for name in sorted(set(records)-set(claimed)):
        if name.startswith(exclusions):continue
        try:
            p = pts(name)[0]
            ids = np.flatnonzero(p[:,2] <= p[:,2].min()+.025)
            row = summarize({'group':'unclassified:'+name,'kind':'unclassified','objects':[name]},samples(name,ids))
            if row['affected_by_new_terrain']:unclassified.append(row)
        except Exception as exc:errors.append({'group':'unclassified:'+name,'error':str(exc)})
    dirty_after = bool(bpy.data.is_dirty)
    failures = [r['group'] for r in results if r['new_or_worsened_support_failures'] or r['missing_ground']]
    report = {'read_only':True,'visual_accepted':False,'pid':expected_pid,'dirty_before':dirty_before,'dirty_after':dirty_after,
              'semantic_catalogues':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (previous/'props.json',previous/'manual_props.json')],
              'baseline_this_round':str(log/'objects_before.json'),'groups':results,'excluded':excluded,
              'affected_groups':[r['group'] for r in results if r['affected_by_new_terrain']],
              'support_failure_groups':failures,'unclassified_affected':unclassified,'errors':errors,
              'excluded_unclassified_name_prefixes':list(exclusions),
              'limitations':['Bottom 25mm of actual support components is checked, not object centers.',
                             'Existing building floors are audited separately; hanging goods are excluded from ground support.',
                             'The catalogue groups are semantic selections only. No old transforms or authoring scripts run.',
                             'Positive gap over75mm or new deeper rigid penetration over75mm is flagged only when worsened by at least10mm.',
                             'This support scan does not replace visibility/collision review or all surface-interior contact checks.'],
              'technical_pass':not(failures or errors or unclassified or dirty_after!=dirty_before)}
    (log/'support_readonly.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:report[k] for k in ('technical_pass','affected_groups','support_failure_groups','errors','dirty_after')},ensure_ascii=False))
    return report
