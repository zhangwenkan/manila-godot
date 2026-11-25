"""One-time connected ground forms; execute ONLY in the owned Blender MCP.

This script edits the existing C25 terrain only. It never executes historical
scripts, moves scene objects, changes topology, exports, or saves the blend.
The old S23 foundations/contact/section files are read as evidence; the actual
contact locks and before/after support checks use the current live scene.

Coordinates in calculations are Blender world coordinates: Godot (x, y, z)
is Blender (x, z, -y). The terrain is required to have an identity transform.
"""
import json
import time
from pathlib import Path

import numpy as np


def smoothstep(a, b, value):
    t = np.clip((value - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def signed_xy(positions, triangles):
    a = positions[triangles[:, 1]] - positions[triangles[:, 0]]
    b = positions[triangles[:, 2]] - positions[triangles[:, 0]]
    return a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]


def vertex_roles(vertex_count, loops, colors):
    roles = np.zeros((vertex_count, 4), dtype=np.float64)
    counts = np.zeros(vertex_count, dtype=np.float64)
    np.add.at(roles, loops, colors)
    np.add.at(counts, loops, 1)
    return roles / np.maximum(counts, 1.0)[:, None]


def unique_edges(triangles):
    edges = np.sort(np.concatenate((triangles[:, [0, 1]],
                                   triangles[:, [1, 2]],
                                   triangles[:, [2, 0]])), axis=1)
    return np.unique(edges, axis=0, return_counts=True)


def propose_forms(before, roles, normals, edges, clearance):
    """Deterministic broad masses, with no periodic wave/noise displacement."""
    x, z, height = before[:, 0], -before[:, 1], before[:, 2]
    region = (smoothstep(8, 9.2, x) * (1 - smoothstep(28.5, 30, x))
              * smoothstep(-8, -6, z) * (1 - smoothstep(51.5, 54, z))
              * smoothstep(.28, .60, height))
    # Two adjacency rings connect the exposed face into its grass crown and
    # toe. A face-only green-channel mask would retain the old parallel bands.
    rock = roles[:, 1].copy()
    for attenuation in (.78, .68):
        spread = rock.copy()
        np.maximum.at(spread, edges[:, 0], rock[edges[:, 1]] * attenuation)
        np.maximum.at(spread, edges[:, 1], rock[edges[:, 0]] * attenuation)
        rock = spread
    rock *= 1 - smoothstep(.12, .65, roles[:, 2])
    rock *= np.maximum(smoothstep(.03, .42, roles[:, 1]),
                       smoothstep(.01, .25, 1 - normals[:, 2]))
    rock *= region * clearance

    # Infer the local foot/crown from this turn's baseline, independently in
    # each alongshore bin. This follows the existing nonuniform large relief.
    bins, low, high = [], [], []
    for center in np.arange(-7, 55, 1.5):
        ids = ((abs(z - center) < 1.25) & (roles[:, 1] > .45)
               & (x > 8) & (x < 30) & (height > .6))
        if np.count_nonzero(ids) < 5:
            continue
        bins.append(float(center))
        a, b = np.quantile(height[ids], [.04, .96])
        low.append(float(a - .08))
        high.append(float(max(b + .08, a + .85)))
    if len(bins) < 20:
        raise RuntimeError('Insufficient baseline rock sections for form design')
    foot, crown = np.interp(z, bins, low), np.interp(z, bins, high)
    q = np.clip((height - foot) / np.maximum(crown - foot, .85), -.25, 1.25)

    # center_z, half-length, outward reach, diagonal lean, alongshore shift,
    # q-profile. Unequal lengths and offsets produce groups, not brick courses.
    groups = [
        (-4.0, 4.0, .46,  1.10,  .12, [0, .20, .88, 1, .52, .18, 0]),
        ( 3.8, 5.2, .51, -1.45, -.12, [0, .32, 1, .78, .57, .12, 0]),
        (12.8, 4.2, .53,  1.25,  .10, [0, .16, .78, 1, .41, .25, 0]),
        (24.0, 4.5, .55, -1.50, -.13, [0, .28, 1, .87, .49, .14, 0]),
        (29.1, 3.3, .43,   .95,  .10, [0, .22, .70, 1, .68, .20, 0]),
        (38.2, 4.1, .54,  1.55,  .14, [0, .24, .92, 1, .36, .20, 0]),
        (43.6, 3.5, .48, -1.20, -.11, [0, .16, 1, .80, .61, .12, 0]),
        (50.1, 4.2, .49,  1.30,  .10, [0, .30, .82, 1, .44, .22, 0]),
    ]
    displacement = np.zeros_like(before)
    contribution = np.zeros(len(before))
    group_reports = []
    for center, radius, reach, lean, slide, profile in groups:
        t = (z - center - lean * (q - .45)) / radius
        # Asymmetric piecewise planar flanks meet one broad shoulder.
        along = np.interp(t, [-1, -.57, -.10, .38, 1], [0, .78, 1, .83, 0])
        along *= (abs(t) < 1)
        vertical = np.interp(q, [-.15, 0, .24, .55, .81, 1, 1.15], profile)
        amount = rock * along * vertical
        # Choose the stronger authored mass where group ends overlap, avoiding
        # doubled protrusions and retaining a clear broad turn between groups.
        take = amount * reach > contribution
        outward = amount * reach
        displacement[take, 0] = -outward[take]
        displacement[take, 1] = -(amount * slide * (.25 + .75 * q))[take]
        lift_profile = np.interp(q, [-.15, 0, .28, .64, 1, 1.15],
                                 [0, -.035, .09, .035, -.055, 0])
        displacement[take, 2] = (rock * along * lift_profile)[take]
        contribution[take] = outward[take]
        group_reports.append({'center_godot_z': center, 'half_length_m': radius,
                              'nominal_outward_m': reach,
                              'candidate_vertices': int(np.count_nonzero(amount > .03))})

    # A shallow sand cove reaches obliquely toward the slope foot between the
    # trading post and grill; a neighbouring grass shoulder advances toward
    # the sea. Both are true broad ground forms, at different positions.
    bay_cx = 12.2 + .22 * (z - 12.8)
    bay_r = np.sqrt(((x - bay_cx) / 2.2) ** 2 + ((z - 12.8) / 2.0) ** 2)
    bay = (1 - smoothstep(.16, 1, bay_r)) * region * clearance
    bay *= (1 - smoothstep(.12, .58, roles[:, 2]))
    bay *= (1 - smoothstep(.04, .35, roles[:, 1]))
    bay *= (1 - smoothstep(1.05, 1.50, height))
    shoulder_r = np.sqrt(((x - 14.4 - .12 * (z - 15.1)) / 1.9) ** 2
                         + ((z - 15.1) / 1.7) ** 2)
    shoulder = (1 - smoothstep(.12, 1, shoulder_r)) * region * clearance
    shoulder *= smoothstep(.10, .75, roles[:, 0])
    shoulder *= (1 - smoothstep(.10, .60, roles[:, 2]))
    shoulder *= (1 - smoothstep(.10, .50, roles[:, 1]))
    shoulder *= (1 - smoothstep(1.45, 1.95, height))
    displacement[:, 0] += .16 * bay - .23 * shoulder
    displacement[:, 2] += -.19 * bay + .18 * shoulder
    displacement[(height <= .28) | (z >= 54) | (z <= -8)
                 | (x <= 8) | (x >= 30)] = 0
    return displacement, {'rock_groups': group_reports,
                          'section_profile_godot_z_foot_crown': list(zip(bins, low, high)),
                          'bay_candidate_vertices': int(np.count_nonzero(bay > .03)),
                          'shoulder_candidate_vertices': int(np.count_nonzero(shoulder > .03))}


def reduce_local_folds(before, proposed, triangles, frozen):
    """Locally backtrack displacement until every projected triangle is legal.

    Reduction propagates to neighbours, so an isolated pinned vertex does not
    form a needle-shaped recess. Float32 round-trip is checked each iteration.
    """
    old_area = signed_xy(before, triangles)
    if np.any(old_area <= 0):
        raise RuntimeError('Baseline already contains nonpositive XY triangles')
    minimum = np.maximum(old_area * .16, 1e-8)
    factor = np.ones(len(before))
    factor[frozen] = 0
    reductions = []
    for iteration in range(80):
        after = (before + proposed * factor[:, None]).astype(np.float32).astype(np.float64)
        bad = np.flatnonzero(signed_xy(after, triangles) < minimum)
        if not len(bad):
            return after, factor, reductions
        touched = np.unique(triangles[bad])
        movable = touched[(np.linalg.norm(proposed[touched], axis=1) > 1e-12)
                          & ~frozen[touched]]
        if not len(movable):
            raise RuntimeError('No movable vertices for local projected-area repair')
        factor[movable] *= .55
        # Backtracking neighbouring moved vertices avoids pinched isolated edits.
        for _ in range(2):
            face_limit = np.min(factor[triangles], axis=1)
            neighbour_limit = np.ones(len(before))
            np.minimum.at(neighbour_limit, triangles.ravel(),
                          np.repeat(np.minimum(1, face_limit + .22), 3))
            factor = np.minimum(factor, neighbour_limit)
            factor[frozen] = 0
        reductions.append({'iteration': iteration + 1, 'small_or_negative_triangles': int(len(bad)),
                           'vertices_reduced': int(len(movable))})
    raise RuntimeError('Local fold backtracking did not converge; terrain left unchanged')


def run_ground23_forms():
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    started = time.perf_counter()
    root = Path(bpy.data.filepath).parent.parent
    log = root / 'captures/ground_integration_20261123'
    old_log = root / 'captures/rock_path_sample_20261123'
    terrain = bpy.data.objects['C25_ContourBuiltCoast']
    mesh = terrain.data
    assert not terrain.get('ground23_forms'), 'Already applied; do not replay ground23 forms'
    assert Path(bpy.data.filepath).name == 'harbor_shore_control_mcp.blend'
    assert np.max(abs(np.asarray(terrain.matrix_world) - np.eye(4))) < 1e-8
    assert not [m for m in terrain.modifiers if m.show_viewport], 'Raw mesh must be rendered mesh'
    with np.load(str(log / 'baseline.npz')) as raw:
        before = raw['positions'].astype(np.float64)
        loops = raw['loops'].copy()
        colors = raw['colors'].copy()
        normals = raw['normals'].astype(np.float64)
        sizes = raw['sizes'].copy()
        starts = raw['starts'].copy()
    current = np.empty((len(mesh.vertices), 3), np.float32)
    current_loops = np.empty(len(mesh.loops), np.int32)
    mesh.vertices.foreach_get('co', current.ravel())
    mesh.loops.foreach_get('vertex_index', current_loops)
    assert current.shape == before.shape and len(current) == 66230
    assert len(mesh.polygons) == 114226 and np.all(sizes == 3)
    assert np.array_equal(current_loops, loops), 'Topology differs from this turn baseline'
    assert np.max(abs(current.astype(float) - before)) < 1e-7, 'Terrain already edited after baseline'
    assert np.array_equal(starts, np.arange(len(sizes)) * 3)
    triangles = loops.reshape((-1, 3))
    edges, incidence = unique_edges(triangles)
    assert not np.any(incidence > 2), 'Baseline has nonmanifold edges'
    boundary = np.unique(edges[incidence == 1])
    roles = vertex_roles(len(before), loops, colors)

    foundations = json.loads((old_log / 'foundations.json').read_text(encoding='utf8'))
    contact_evidence = json.loads((old_log / 'contacts_current.json').read_text(encoding='utf8'))
    section_evidence = json.loads((old_log / 'sections_before.json').read_text(encoding='utf8'))
    assert len(foundations) == 9 and len(section_evidence) >= 10
    old_bvh = BVHTree.FromPolygons(before.tolist(), triangles.tolist(), all_triangles=True)
    down = Vector((0, 0, -1))

    def ground(bvh, x, y):
        hit = bvh.ray_cast(Vector((float(x), float(y), 50)), down, 200)[0]
        return None if hit is None else float(hit.z)

    def world_vertices(obj):
        values = np.empty((len(obj.data.vertices), 3), np.float32)
        obj.data.vertices.foreach_get('co', values.ravel())
        matrix = np.asarray(obj.matrix_world, dtype=np.float64)
        return values.astype(np.float64) @ matrix[:3, :3].T + matrix[:3, 3]

    def box_points(lo, hi):
        return [(lo[0], lo[1]), (lo[0], hi[1]), (hi[0], lo[1]),
                (hi[0], hi[1]), ((lo[0] + hi[0]) * .5, (lo[1] + hi[1]) * .5)]

    floor_names = {f['object'] for f in foundations}
    step_names = ['Town_Step.001', 'Town_Step.002', 'Town_Step.003',
                  'Town_Step.004', 'Town_Step.005', 'Town_Step.008']
    # Resolve the two lowest hut stairs by the audited current positions, not
    # guessed numbering.
    for expected in ((22.44397, 36.49067, 4.00032), (24.95671, 19.49066, 4.09074)):
        matches = []
        for obj in bpy.data.collections['Reference_Coast'].all_objects:
            if obj.type != 'MESH' or not obj.name.startswith('Hut_EntrySteps'):
                continue
            coords = world_vertices(obj)
            center = (coords.min(axis=0) + coords.max(axis=0)) * .5
            if (abs(center[0] - expected[0]) < .05
                    and abs(-center[1] - expected[1]) < .05
                    and abs(center[2] - expected[2]) < .04):
                matches.append(obj.name)
        assert len(matches) == 1, 'Lowest hut step match is missing or ambiguous'
        step_names.extend(matches)
    assert len(step_names) == 8 and all(bpy.data.objects.get(n) for n in step_names)

    support_rows, protected_boxes, captured_objects = [], [], {}
    semantic_support = ('Town_Floor', 'Town_Step', 'Hut_Floor', 'Hut_EntrySteps',
                        'Hut_StairStringer', 'Town_TavernPorch', 'Town_Stone',
                        'Tree_Trunk', 'Palm_Trunk', 'Tree_Root', 'Palm_Root')
    seen = set()
    for cname in ('Reference_Town', 'Reference_Coast', 'Reference_Foliage', 'Reference_Rocks'):
        coll = bpy.data.collections.get(cname)
        if coll is None:
            continue
        for obj in coll.all_objects:
            if obj.name in seen or obj.type != 'MESH' or obj.hide_render or 'Grass' in obj.name:
                continue
            seen.add(obj.name)
            coords = world_vertices(obj)
            if not len(coords):
                continue
            lo, hi = coords.min(axis=0), coords.max(axis=0)
            mandatory = obj.name in floor_names or obj.name in step_names
            intersects = (hi[0] > 7 and lo[0] < 31 and -lo[1] > -9 and -hi[1] < 55)
            if not mandatory and (not intersects or lo[2] > 7):
                continue
            samples = box_points(lo, hi)
            heights = [ground(old_bvh, x, y) for x, y in samples]
            gaps = [float(lo[2] - h) for h in heights if h is not None]
            semantic = obj.name.startswith(semantic_support)
            # Protect actual ground contacts, including partially buried rocks.
            # Elevated doors, signs, eaves, coconuts and branches cannot be
            # mistaken for movable props: no scene object is ever moved here.
            contact = any(-1.5 <= gap <= .55 for gap in gaps)
            if not (mandatory or semantic or contact):
                continue
            # Tree crowns are not soil footprints. The lower trunk/root mesh
            # supplies a compact real root footprint even for leaning palms.
            if obj.name.startswith(('Tree_Trunk', 'Palm_Trunk', 'Tree_Root', 'Palm_Root')):
                root_points = coords[coords[:, 2] <= lo[2] + max(.22, (hi[2] - lo[2]) * .13)]
                if len(root_points) >= 3:
                    lo, hi = root_points.min(axis=0), root_points.max(axis=0)
                    samples = box_points(lo, hi)
                    heights = [ground(old_bvh, x, y) for x, y in samples]
            protected_boxes.append((lo[:2] - .16, hi[:2] + .16, obj.name))
            captured_objects[obj.name] = coords
            support_rows.append({'object': obj.name, 'collection': cname,
                                 'floor': obj.name in floor_names, 'step': obj.name in step_names,
                                 'xy_samples': samples, 'before_height': heights})

    assert floor_names <= set(captured_objects), 'Every original town floor must be protected'
    assert set(step_names) <= set(captured_objects), 'Every audited entry must be protected'
    triangle_xy = before[triangles, :2]
    tri_lo, tri_hi = triangle_xy.min(axis=1), triangle_xy.max(axis=1)
    frozen = np.zeros(len(before), dtype=bool)
    frozen[boundary] = True
    clearance = np.ones(len(before))
    for lo, hi, _ in protected_boxes:
        overlap = np.all(tri_hi >= lo, axis=1) & np.all(tri_lo <= hi, axis=1)
        frozen[np.unique(triangles[overlap])] = True
        dx = np.maximum(np.maximum(lo[0] - before[:, 0], before[:, 0] - hi[0]), 0)
        dy = np.maximum(np.maximum(lo[1] - before[:, 1], before[:, 1] - hi[1]), 0)
        clearance = np.minimum(clearance, smoothstep(.10, .85, np.hypot(dx, dy)))
    clearance[frozen] = 0
    displacement, design = propose_forms(before, roles, normals, edges, clearance)
    displacement[frozen] = 0
    after, scales, reductions = reduce_local_folds(before, displacement, triangles, frozen)
    new_bvh = BVHTree.FromPolygons(after.tolist(), triangles.tolist(), all_triangles=True)
    # Audit before committing; frozen intersecting triangles keep every sampled
    # contact surface unchanged, including its real foundation gaps.
    max_contact_delta = 0.0
    for row in support_rows:
        current_heights = [ground(new_bvh, x, y) for x, y in row['xy_samples']]
        deltas = []
        for old_height, new_height in zip(row['before_height'], current_heights):
            assert (old_height is None) == (new_height is None), 'Contact ray coverage changed'
            if old_height is not None:
                deltas.append(new_height - old_height)
        row['after_height'] = current_heights
        row['maximum_height_delta_m'] = max(map(abs, deltas), default=0.0)
        max_contact_delta = max(max_contact_delta, row['maximum_height_delta_m'])
        assert row['maximum_height_delta_m'] <= 2e-5, 'Contact changed: ' + row['object']
    assert np.array_equal(before[boundary], after[boundary]), 'Boundary moved'
    untouched = ((before[:, 2] <= .28) | (-before[:, 1] >= 54)
                 | (-before[:, 1] <= -8) | (before[:, 0] <= 8) | (before[:, 0] >= 30))
    assert np.array_equal(before[untouched], after[untouched]), 'Protected scope changed'
    cross = np.cross(after[triangles[:, 1]] - after[triangles[:, 0]],
                     after[triangles[:, 2]] - after[triangles[:, 0]])
    assert np.all(cross[:, 2] > 0) and np.all(np.linalg.norm(cross, axis=1) > 1e-9)
    for name, old_coords in captured_objects.items():
        assert np.array_equal(old_coords, world_vertices(bpy.data.objects[name])), 'Scene object changed'
    delta = after - before
    changed = np.flatnonzero(np.linalg.norm(delta, axis=1) > 1e-6)
    assert len(changed) > 100, 'Protection suppressed essentially all intended terrain work'
    report = {'status': 'validated_before_commit', 'visual_accepted': False,
              'source': bpy.data.filepath, 'design': design,
              'vertices': len(before), 'triangles': len(triangles),
              'changed_vertices': int(len(changed)),
              'maximum_absolute_blender_xyz_delta_m': abs(delta).max(axis=0).tolist(),
              'changed_bounds_godot_xyz': [np.min(before[changed][:, [0, 2, 1]] * [1, 1, -1], axis=0).tolist(),
                                         np.max(before[changed][:, [0, 2, 1]] * [1, 1, -1], axis=0).tolist()],
              'outward_vertices_over_0_20m': int(np.count_nonzero(delta[:, 0] < -.20)),
              'frozen_vertices': int(np.count_nonzero(frozen)),
              'boundary_vertices': len(boundary), 'boundary_max_delta_m': 0,
              'local_area_backtracking': reductions,
              'negative_xy_triangles': int(np.count_nonzero(cross[:, 2] <= 0)),
              'floor_count': sum(r['floor'] for r in support_rows),
              'step_count': sum(r['step'] for r in support_rows),
              'protected_contact_objects': len(support_rows),
              'maximum_contact_ground_delta_m': max_contact_delta,
              'read_only_historical_evidence': {'foundations': len(foundations),
                    'contact_rows': len(contact_evidence['contacts_on_changed_ground']),
                    'sections': len(section_evidence)},
              'contacts': support_rows, 'elapsed_seconds': round(time.perf_counter() - started, 3),
              'saved_blend': False, 'exported_assets': False}
    np.savez_compressed(str(log / 'forms_before_after.npz'), before=before.astype(np.float32),
                        positions=after.astype(np.float32), displacement=delta.astype(np.float32),
                        proposed_displacement=displacement.astype(np.float32),
                        local_scales=scales.astype(np.float32), changed=changed,
                        boundary=boundary, frozen=np.flatnonzero(frozen), triangles=triangles)
    try:
        mesh.vertices.foreach_set('co', after.astype(np.float32).ravel())
        mesh.update()
        actual = np.empty_like(current)
        mesh.vertices.foreach_get('co', actual.ravel())
        assert np.array_equal(actual, after.astype(np.float32)), 'Mesh commit did not match verified positions'
        terrain['ground23_forms'] = True
        terrain['ground23_forms_note'] = 'Eight broad grouped shoulders and one sand cove/grass shoulder; current scene contact triangles fixed; no export/save'
        report['status'] = 'applied_and_verified'
        (log / 'forms.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
    except Exception:
        mesh.vertices.foreach_set('co', before.astype(np.float32).ravel())
        mesh.update()
        for key in ('ground23_forms', 'ground23_forms_note'):
            if key in terrain:
                del terrain[key]
        raise
    print(json.dumps({k: v for k, v in report.items() if k not in ('contacts', 'design')}, ensure_ascii=False))


run_ground23_forms()
