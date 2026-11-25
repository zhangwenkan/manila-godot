"""One-time rooting after the stronger G23 forms, only in the owned Blender MCP.

Only L24_GrassTuftClusters is changed. Whole independent blades translate
vertically; no other plant, terrain vertex, material, or object pose is edited.
No historical script is executed. No GLB export or blend save occurs here.
"""
import json
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(bpy.data.filepath).parent.parent
LOG = ROOT / 'captures/ground_integration_20261123'
terrain = bpy.data.objects['C25_ContourBuiltCoast']
growth = bpy.data.objects['L24_GrassTuftClusters']
assert terrain.get('ground23_integrated_shoulders'), 'Stronger ground forms must precede this grass rooting'
assert not growth.get('ground23_reground_integrated_shoulders'), 'Already applied; do not replay'
assert len(growth.data.polygons) == 7652, 'Unexpected stronger-pass grass population'
assert growth.type == 'MESH' and not growth.hide_render
assert not [m for m in growth.modifiers if m.show_viewport], 'Grass modifiers require explicit handling'
with np.load(str(LOG / 'land_data.npz')) as raw:
    land = raw['land'].copy()
assert land.shape == (2048, 2048, 4)
assert np.isfinite(land).all()
bpy.context.view_layer.update()
surface = BVHTree.FromObject(terrain, bpy.context.evaluated_depsgraph_get())
down = Vector((0, 0, -1))
matrix = growth.matrix_world.copy()
inverse_direction = matrix.to_3x3().inverted()


def hit_at(x, y):
    hit, normal, _, _ = surface.ray_cast(Vector((float(x), float(y), 50)), down, 200)
    assert hit is not None, 'Missing actual surface beneath an existing grass root'
    return float(hit.z), float(normal.z)


def role_at(x, z):
    # Pixel-centre bilinear sampling matches the authored G23 world rectangle.
    px = float(np.clip((x + 4) / 48 * 2048 - .5, 0, 2047 - 1e-7))
    pz = float(np.clip((z + 15) / 97 * 2048 - .5, 0, 2047 - 1e-7))
    ix, iz = int(px), int(pz)
    fx, fz = px - ix, pz - iz
    return ((land[iz, ix] * (1 - fx) + land[iz, ix + 1] * fx) * (1 - fz)
            + (land[iz + 1, ix] * (1 - fx) + land[iz + 1, ix + 1] * fx) * fz)


bm = bmesh.new()
bm.from_mesh(growth.data)
bm.faces.ensure_lookup_table()
before_count = len(bm.faces)
plans, removed, audit = [], [], []
outside_signatures = []
outside_gaps = []
reason_counts = {'path': 0, 'sand': 0, 'rock': 0, 'steep': 0}
try:
    for face in bm.faces:
        assert len(face.verts) == 3 and all(len(v.link_faces) == 1 for v in face.verts), \
            'Expected independent three-vertex blades'
        points = [matrix @ v.co for v in face.verts]
        root = (points[0] + points[1]) * .5
        # Verify the two first vertices are the basal edge, rather than guessing
        # a lowest object corner or using the blade centroid.
        assert abs(points[0].z - points[1].z) < .003, 'Nonhorizontal basal edge'
        assert points[2].z - max(points[0].z, points[1].z) > .025, 'First two vertices are not the root'
        assert .005 < (points[0] - points[1]).length < .30, 'Unexpected blade basal width'
        scope = 8 < root.x < 31 and -8 < -root.y < 62
        if not scope:
            outside_signatures.append(tuple(tuple(v.co) for v in face.verts))
            # A complete final report distinguishes unchanged outside-scope
            # legacy gaps from the roots actually re-planted in this pass.
            hit, _, _, _ = surface.ray_cast(Vector((root.x, root.y, 50)), down, 200)
            if hit is not None:
                outside_gaps.append(float(root.z - hit.z))
            continue
        role = role_at(root.x, -root.y)
        sand = max(0.0, 1.0 - float(role.sum()))
        ground, nz = hit_at(root.x, root.y)
        reasons = []
        if role[2] > .35:
            reasons.append('path')
        if sand > .45:
            reasons.append('sand')
        if role[1] > .50:
            reasons.append('rock')
        if nz < .60:
            reasons.append('steep')
        if reasons:
            removed.append(face)
            for reason in reasons:
                reason_counts[reason] += 1
            audit.append({'old_face': face.index, 'removed': reasons,
                          'root_godot': [root.x, root.z, -root.y],
                          'roles': role.tolist(), 'sand': sand, 'normal_z': nz})
            continue
        base_ground = [hit_at(p.x, p.y)[0] for p in points[:2]]
        # Embed both basal corners as well as the midpoint, preserving blade
        # shape. Midpoint-only planting can leave one end hanging on slopes.
        delta = min(ground - root.z, *(h - p.z for h, p in zip(base_ground, points[:2]))) - .012
        local_shift = inverse_direction @ Vector((0, 0, float(delta)))
        plans.append((face, local_shift, points, root, delta, ground, base_ground))

    retained_scoped_gaps, endpoint_gaps = [], []
    for face, shift, old_points, old_root, delta, ground, base_ground in plans:
        for vertex in face.verts:
            vertex.co += shift
        points = [matrix @ v.co for v in face.verts]
        root = (points[0] + points[1]) * .5
        assert max(abs(points[i][axis] - old_points[i][axis])
                   for i in range(3) for axis in (0, 1)) < 2e-5, 'Grass moved horizontally'
        gap = float(root.z - ground)
        bases = [float(p.z - h) for p, h in zip(points[:2], base_ground)]
        assert gap <= -.01198 and max(bases) <= -.01198, 'Retained root has a floating basal end'
        retained_scoped_gaps.append(gap)
        endpoint_gaps.extend(bases)
        audit.append({'old_face': face.index, 'removed': False,
                      'root_godot': [root.x, root.z, -root.y],
                      'vertical_delta_m': float(delta), 'root_gap_m': gap,
                      'basal_corner_gaps_m': bases})
    # Independent triangles allow removal of their three vertices together;
    # this avoids leaving isolated vertices behind after deleting a face.
    if removed:
        bmesh.ops.delete(bm, geom=[v for face in removed for v in face.verts], context='VERTS')
    bm.faces.ensure_lookup_table()
    after_outside = []
    for face in bm.faces:
        root = matrix @ ((face.verts[0].co + face.verts[1].co) * .5)
        if not (8 < root.x < 31 and -8 < -root.y < 62):
            after_outside.append(tuple(tuple(v.co) for v in face.verts))
    assert after_outside == outside_signatures, 'Out-of-scope blades changed'
    assert len(bm.faces) == before_count - len(removed)
    assert len(bm.verts) == 3 * len(bm.faces), 'Grass has shared/orphan vertices'
    report = {'object': growth.name, 'before_blades': before_count, 'pass': 'integrated_continuous_shoulders',
              'removed_blades': len(removed), 'removed_reason_counts': reason_counts,
              'remaining_blades': len(bm.faces), 'replanted_blades': len(plans),
              'scope_godot_x_z': [8, 31, -8, 62], 'scope_only': True,
              'unchanged_outside_blades': len(outside_signatures),
              'root_definition': 'midpoint of the first two verified basal vertices',
              'retained_root_gap_range_m': [min(retained_scoped_gaps), max(retained_scoped_gaps)] if plans else None,
              'retained_basal_corner_gap_range_m': [min(endpoint_gaps), max(endpoint_gaps)] if plans else None,
              'retained_scoped_floating_roots': 0,
              'unchanged_outside_root_gap_range_m': [min(outside_gaps), max(outside_gaps)] if outside_gaps else None,
              'unchanged_outside_roots_above_0_025m': sum(gap > .025 for gap in outside_gaps),
              'maximum_vertical_move_m': max((abs(row[4]) for row in plans), default=0),
              'saved_blend': False, 'exported_assets': False, 'blades': audit}
    # Commit to a copy only after all plans and scope checks pass. Existing
    # material slots, UVs and mesh attributes are preserved by BMesh.
    previous_mesh = growth.data
    staged_mesh = previous_mesh.copy()
    try:
        bm.to_mesh(staged_mesh)
        staged_mesh.update()
        assert len(staged_mesh.polygons) == report['remaining_blades']
        assert len(staged_mesh.vertices) == 3 * report['remaining_blades']
        growth.data = staged_mesh
        growth['ground23_reground_integrated_shoulders'] = True
        (LOG / 'grass_reground_integrated_shoulders.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
    except Exception:
        growth.data = previous_mesh
        if 'ground23_reground_integrated_shoulders' in growth:
            del growth['ground23_reground_integrated_shoulders']
        if staged_mesh.users == 0:
            bpy.data.meshes.remove(staged_mesh)
        raise
    print(json.dumps({k: v for k, v in report.items() if k != 'blades'}, ensure_ascii=False))
finally:
    bm.free()

