"""One low grass shoulder, authored once through the owned GUI Blender MCP.

Baseline is the current stronger_forms positions. No topology, material, object,
export or source-save changes. Pure functions can be inspected offline; run()
uses current live objects and BVHs and refuses stale geometry or lost supports.
"""
import ast
import json
from pathlib import Path

import numpy as np


def smooth(a, b, values):
    q = np.clip((values - a) / (b - a), 0, 1)
    return q * q * (3 - 2 * q)


def band(values, a, b, c, d):
    return smooth(a, b, values) * (1 - smooth(c, d, values))


def signed_area(positions, triangles):
    a = positions[triangles[:, 1]] - positions[triangles[:, 0]]
    b = positions[triangles[:, 2]] - positions[triangles[:, 0]]
    return a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]


def sample_land(array, x, z):
    rows, columns = array.shape[:2]
    u = np.clip((x + 4) / 48 * columns - .5, 0, columns - 1.0001)
    v = np.clip((z + 15) / 97 * rows - .5, 0, rows - 1.0001)
    ix, iy = u.astype(int), v.astype(int)
    tx, ty = u - ix, v - iy
    if array.ndim == 3:
        tx, ty = tx[:, None], ty[:, None]
    return ((array[iy, ix] * (1 - tx) + array[iy, ix + 1] * tx) * (1 - ty)
            + (array[iy + 1, ix] * (1 - tx) + array[iy + 1, ix + 1] * tx) * ty)


def protect_footprints(before, triangles, boundary, footprints):
    fixed = before[:, 2] <= .30
    fixed[boundary] = True
    freedom = np.ones(len(before))
    xy = before[triangles, :2]
    lo_tri, hi_tri = xy.min(1), xy.max(1)
    for low, high, _ in footprints:
        low, high = np.asarray(low), np.asarray(high)
        overlap = np.all(hi_tri >= low, axis=1) & np.all(lo_tri <= high, axis=1)
        fixed[np.unique(triangles[overlap])] = True
        dx = np.maximum(np.maximum(low[0] - before[:, 0], before[:, 0] - high[0]), 0)
        dy = np.maximum(np.maximum(low[1] - before[:, 1], before[:, 1] - high[1]), 0)
        freedom = np.minimum(freedom, smooth(.02, .48, np.hypot(dx, dy)))
    freedom[fixed] = 0
    return fixed, freedom


def design_positions(before, roles, freedom):
    """Single broad lowered landform, ending in unchanged short banks at both sides."""
    x, z, height = before[:, 0], -before[:, 1], before[:, 2]
    along = band(z, 54.2, 55.0, 57.1, 58.1)
    across = band(x, 10.10, 10.55, 12.35, 13.00)
    # A roughly 1:4.5 plane reaches the sand, independently of the old crown.
    # Keep an existing lower sand point; never raise a berm over the beach.
    target = .34 + .22 * np.maximum(x - 10.25, 0)
    exposure = smooth(.30, .41, height) * (1 - smooth(1.30, 1.55, height))
    exposure *= 1 - smooth(.30, .70, roles[:, 1])
    amount = along * across * exposure * freedom
    displacement = np.zeros_like(before)
    displacement[:, 2] = amount * np.clip(target - height, -.38, 0)
    displacement[height <= .30] = 0
    pieces = [{
        'name': 'sari_sari_low_grass_shoulder',
        'godot_bounds_xz': [10.10, 54.20, 13.00, 58.10],
        'godot_full_weight_xz': [10.55, 55.00, 12.35, 57.10],
        'target_height': '.34 + .22 * max(x-10.25, 0)',
        'maximum_lowering_m': .38,
        'material_guidance': 'grass mainly x10.2..12.4 continues across the lowered shoulder to the sand foot; retain soil at two side ends; inner path x13.0..13.8 stays outside deformation',
        'floor_note': 'Sari-Sari floor starts x14.556; current floor and step contacts receive exact triangle locks',
    }]
    return displacement, pieces


def run():
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    assert not bpy.app.background, 'Use the owned GUI Blender MCP'
    root = Path(bpy.data.filepath).parent.parent
    log = root / 'captures/ground_integration_20261123'
    terrain = bpy.data.objects['C25_ContourBuiltCoast']
    mesh = terrain.data
    assert terrain.get('ground23_stronger_forms'), 'Apply stronger forms first'
    assert not terrain.get('ground23_low_shoulder_18'), 'One-time pass already applied'
    assert np.max(abs(np.asarray(terrain.matrix_world) - np.eye(4))) < 1e-8
    with np.load(log / 'stronger_forms_before_after.npz') as data:
        before = data['positions'].astype(float)
        triangles = data['triangles'].copy()
        boundary = data['boundary'].copy()
    current = np.empty((len(mesh.vertices), 3), np.float32)
    mesh.vertices.foreach_get('co', current.ravel())
    assert np.array_equal(current, before.astype(np.float32)), 'Current mesh differs from stronger_forms baseline'
    loops = np.empty(len(mesh.loops), np.int32)
    mesh.loops.foreach_get('vertex_index', loops)
    assert np.array_equal(loops.reshape(-1, 3), triangles), 'Topology differs from baseline'
    with np.load(log / 'land_data.npz') as data:
        roles = sample_land(data['land'], before[:, 0], -before[:, 1])
        atlas_height = sample_land(data['height'], before[:, 0], -before[:, 1])

    # Only pure safety helpers are reused, not step 10's run or design.
    source = ast.parse((root / 'source/ground23_10_stronger_forms.py').read_text(encoding='utf8'))
    helper_namespace = {'np': np, 'signed_area': signed_area}
    for helper in source.body:
        if isinstance(helper, ast.FunctionDef) and helper.name == 'safe_local_displacement':
            exec(compile(ast.Module(body=[helper], type_ignores=[]), 'G23 pure backtracking helper', 'exec'), helper_namespace)

    old_bvh = BVHTree.FromPolygons(before.tolist(), triangles.tolist(), all_triangles=True)
    down = Vector((0, 0, -1))

    def ray_height(bvh, x, y):
        hit = bvh.ray_cast(Vector((float(x), float(y), 60)), down, 250)[0]
        return None if hit is None else float(hit.z)

    def coordinates(obj):
        p = np.empty((len(obj.data.vertices), 3), np.float32)
        obj.data.vertices.foreach_get('co', p.ravel())
        matrix = np.asarray(obj.matrix_world, float)
        return p.astype(float) @ matrix[:3, :3].T + matrix[:3, 3]

    mandatory = ('Town_Floor', 'Town_Step', 'Hut_Floor', 'Hut_EntrySteps',
                 'Hut_StairStringer', 'Town_TavernPorch')
    root_names = ('Tree_Trunk', 'Palm_Trunk', 'Tree_Root', 'Palm_Root')
    ignore = ('Grass', 'Blade', 'Tuft', 'Crown', 'Frond', 'Leaf', 'Coconut',
              'Canopy', 'Roof', 'Rafter', 'Eave', 'Bargeboard', 'Sign', 'DoorHandle')
    footprints, contacts = [], []
    # Search all current scene objects, including newly added rocks and cargo
    # props. No dependence on a historical region-limited contact manifest.
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or obj == terrain or obj.hide_render:
            continue
        required = obj.name.startswith(mandatory)
        tree = obj.name.startswith(root_names)
        if not required and any(word in obj.name for word in ignore):
            continue
        bounds = np.array([obj.matrix_world @ Vector(corner) for corner in obj.bound_box])
        low, high = bounds.min(0), bounds.max(0)
        nearby = high[0] > 9.3 and low[0] < 15.1 and -low[1] > 53.4 and -high[1] < 58.9
        if not required and not nearby:
            continue
        p = coordinates(obj)
        if not len(p):
            continue
        low, high = p.min(0), p.max(0)
        if tree:
            base = p[p[:, 2] < low[2] + max(.20, (high[2] - low[2]) * .12)]
            if len(base) >= 3:
                low, high = base.min(0), base.max(0)
        samples = [(float(x), float(y)) for x in np.linspace(low[0], high[0], 3)
                   for y in np.linspace(low[1], high[1], 3)]
        heights = [ray_height(old_bvh, x, y) for x, y in samples]
        touching = any(-1.1 < low[2] - h < .28 for h in heights if h is not None)
        if not (required or tree or touching):
            continue
        # Oversized unrelated envelopes do not count as a compact prop support.
        if not required and not tree and max(high[:2] - low[:2]) > 8:
            continue
        footprints.append((low[:2] - .10, high[:2] + .10, obj.name))
        contacts.append({'object': obj.name, 'samples_xy': samples, 'before_heights': heights})
    assert sum(row['object'].startswith('Town_Floor') for row in contacts) == 9
    for name in ('Town_Step', 'Town_Step.001', 'Town_Step.002', 'Town_Step.003',
                 'Town_Step.004', 'Town_Step.005', 'Town_Step.007', 'Town_Step.008'):
        assert any(row['object'] == name for row in contacts), 'Missing protected step: ' + name

    fixed, freedom = protect_footprints(before, triangles, boundary, footprints)
    displacement, pieces = design_positions(before, roles, freedom)
    displacement[fixed] = 0
    after, factors, backtracking = helper_namespace['safe_local_displacement'](before, displacement, triangles, fixed)
    old_normals = np.cross(before[triangles[:, 1]] - before[triangles[:, 0]],
                           before[triangles[:, 2]] - before[triangles[:, 0]])
    # Height-only edits cannot fold XY, but pinned prop footprints can create
    # an abrupt opposing local slope. Reduce only those local transitions.
    for iteration in range(70):
        normals = np.cross(after[triangles[:, 1]] - after[triangles[:, 0]],
                           after[triangles[:, 2]] - after[triangles[:, 0]])
        bad = np.flatnonzero(np.einsum('ij,ij->i',old_normals,normals)<=0)
        if not len(bad):break
        affected=np.unique(triangles[bad]);factors[affected]*=.62
        limits=np.ones(len(before))
        np.minimum.at(limits,triangles.ravel(),np.repeat(np.minimum(1,np.min(factors[triangles],axis=1)+.22),3))
        factors=np.minimum(factors,limits);factors[fixed]=0
        after=(before+displacement*factors[:,None]).astype(np.float32).astype(float)
        backtracking.append({'normal_transition_iteration':iteration+1,'faces_before_reduction':int(len(bad))})
    delta = after - before
    changed = np.flatnonzero(np.linalg.norm(delta, axis=1) > 1e-6)
    assert len(changed) >= 20 and -delta[:, 2].min() > .20, 'Current support locks leave no useful low shoulder'
    assert np.linalg.norm(delta, axis=1).max() < .50
    assert np.array_equal(after[fixed], before[fixed])
    assert np.array_equal(after[boundary], before[boundary])
    assert np.array_equal(after[before[:, 2] <= .30], before[before[:, 2] <= .30])
    assert np.all(signed_area(after, triangles) > 0)
    old_normals = np.cross(before[triangles[:, 1]] - before[triangles[:, 0]],
                           before[triangles[:, 2]] - before[triangles[:, 0]])
    new_normals = np.cross(after[triangles[:, 1]] - after[triangles[:, 0]],
                           after[triangles[:, 2]] - after[triangles[:, 0]])
    assert np.all(np.einsum('ij,ij->i', old_normals, new_normals) > 0), 'A face rotated through its old back side'
    assert np.all(np.linalg.norm(new_normals, axis=1) > 1e-9), 'Degenerate face'
    new_bvh = BVHTree.FromPolygons(after.tolist(), triangles.tolist(), all_triangles=True)
    maximum_support_delta = 0
    for row in contacts:
        updated = [ray_height(new_bvh, x, y) for x, y in row['samples_xy']]
        differences = []
        for a, b in zip(row['before_heights'], updated):
            assert (a is None) == (b is None)
            if a is not None:
                differences.append(abs(a - b))
        row['max_height_delta_m'] = max(differences, default=0)
        maximum_support_delta = max(maximum_support_delta, row['max_height_delta_m'])
    assert maximum_support_delta <= 2e-5, 'Protected current support changed'
    godot_xz = np.column_stack((after[changed, 0], -after[changed, 1]))
    report = {
        'applied': True, 'visual_accepted': False, 'design': pieces,
        'changed_vertices': len(changed), 'max_abs_xyz_delta_m': abs(delta).max(0).tolist(),
        'actual_godot_bounds_xz': [*godot_xz.min(0).tolist(), *godot_xz.max(0).tolist()],
        'lowered_over_0_20m': int(np.count_nonzero(delta[:, 2] < -.20)),
        'height_before_after': [before[changed, 2].tolist(), after[changed, 2].tolist()],
        'atlas_height_difference_max_m': float(np.max(abs(atlas_height[changed] - before[changed, 2]))),
        'protected_contacts': contacts, 'protected_floor_count': 9,
        'max_support_delta_m': maximum_support_delta, 'fixed_boundary': True, 'fixed_water': True,
        'topology_unchanged': True, 'negative_xy_triangles': 0, 'backtracking': backtracking,
        'saved_blend': False, 'exported_assets': False,
    }
    np.savez_compressed(log / 'low_shoulder_18_before_after.npz',
                        before=before.astype(np.float32), positions=after.astype(np.float32),
                        delta=delta.astype(np.float32), triangles=triangles, boundary=boundary,
                        changed=changed, fixed=np.flatnonzero(fixed), factors=factors.astype(np.float32))
    try:
        mesh.vertices.foreach_set('co', after.astype(np.float32).ravel())
        mesh.update()
        terrain['ground23_low_shoulder_18'] = True
        (log / 'low_shoulder_18.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
    except Exception:
        mesh.vertices.foreach_set('co', before.astype(np.float32).ravel())
        mesh.update()
        if 'ground23_low_shoulder_18' in terrain:
            del terrain['ground23_low_shoulder_18']
        raise
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ('protected_contacts', 'height_before_after')}, ensure_ascii=False))


run()
