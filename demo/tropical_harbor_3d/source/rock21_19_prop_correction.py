# Execute once via verified Blender MCP. Reverse only recorded architectural
# pieces misclassified as ground props in steps 12 and 15; never re-ground all props.
from pathlib import Path
exec((Path(bpy.data.filepath).parent / 'shore_21_context.py').read_text(encoding='utf8'), globals())
import hashlib
LOG = ROOT / 'captures/rock_earth_rebuild_20261121'
assert terrain.get('rock21_wide_regrounded'), 'Step 15 has not completed'
assert not terrain.get('rock21_prop_misclassification_corrected'), 'Prop correction already applied'

prefixes = ('D19_RidgeBinding', 'D19_EaveRafter', 'D19_DoorHinge', 'D19_DoorPull', 'D19_DoorJoint')
evidence = [
    ('grounding_changes.json', 'eafc5dbc09b323a55f5fb6a37953fbf653fdb84cd3914c0c6a923848a6bd137a', 10, 15),
    ('reground_final.json', '82bce0f01295472619c556209c936ff7d8218e55770f76df95ddfe84e7e46088', 29, 37),
]
records = []
total_deltas = {}
sources = {}
for filename, expected_hash, expected_groups, expected_objects in evidence:
    payload = (LOG / filename).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == expected_hash, 'Movement evidence changed: ' + filename
    data = json.loads(payload)
    if filename == 'reground_final.json':
        assert data['exports_completed'] and data['source_saved'], 'Step 15 was not fully saved'
        assert all(any(name.startswith(prefixes) for name in move['objects'])
                   for move in data['moves'] if move['old_gap'] > 1), 'Unreviewed high-gap group'
    selected = [move for move in data['moves']
                if any(name.startswith(prefixes) for name in move['objects'])]
    names = {name for move in selected for name in move['objects']}
    assert len(selected) == expected_groups and len(names) == expected_objects, 'Reviewed evidence count changed'
    sources[filename] = {'sha256': expected_hash, 'groups': len(selected), 'components': len(names)}
    seen = set()
    for move in selected:
        assert all(name.startswith(prefixes) for name in move['objects']), 'Mixed ground and architectural group'
        if filename == 'grounding_changes.json':
            delta = Vector(move['delta'])
        else:
            assert move['kind'] == 'coast_prop_group'
            delta = Vector((0, 0, move['delta_z']))
        assert abs(delta.x) < 1e-8 and abs(delta.y) < 1e-8, 'Expected vertical-only historical translation'
        assert not (set(move['objects']) & seen), 'Duplicate object movement within one historical step'
        seen.update(move['objects'])
        for name in move['objects']:
            total_deltas.setdefault(name, Vector())
            total_deltas[name] += delta
        records.append({'source': filename, 'objects': move['objects'], 'recorded_delta': list(delta)})

assert len(total_deltas) == 42, 'Expected 42 unique architectural components'
coast = bpy.data.collections['Reference_Coast']
coast_names = {o.name for o in coast.objects}
before = {}
targets = {}
for name, delta in total_deltas.items():
    assert name in coast_names and name in bpy.data.objects, 'Missing current coast piece: ' + name
    o = bpy.data.objects[name]
    # Step 12 moved local locations and step 15 world matrices. These loose
    # architectural pieces have no parent; otherwise do not guess a conversion.
    assert o.parent is None and not o.constraints, 'Unexpected transform hierarchy: ' + name
    matrix = o.matrix_world.copy()
    before[name] = [list(row) for row in matrix]
    matrix.translation -= delta
    targets[name] = matrix

report = {'status': 'prepared', 'evidence': sources, 'records_reversed': records,
          'components_restored': len(targets), 'historical_group_records': len(records),
          'repeated_components_across_steps': 10,
          'objects': [{'name': name, 'summed_historical_delta': list(total_deltas[name]),
                       'correction_delta': list(-total_deltas[name]),
                       'before_matrix_world': before[name],
                       'target_matrix_world': [list(row) for row in targets[name]]}
                      for name in sorted(targets)],
          'coast_exported': False, 'source_saved': False}
report_path = LOG / 'prop_correction.json'
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
for name, matrix in targets.items():
    bpy.data.objects[name].matrix_world = matrix
bpy.context.view_layer.update()
for name, matrix in targets.items():
    actual = bpy.data.objects[name].matrix_world
    assert max(abs(actual[r][c] - matrix[r][c]) for r in range(4) for c in range(4)) < 2e-5, name
terrain['rock21_prop_misclassification_corrected'] = True
report['status'] = 'restored_in_memory'
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
export_collection('Reference_Coast', 'coast.glb')
report['coast_exported'] = True
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'source/harbor_shore_control_mcp.blend'))
report['source_saved'] = True
report['status'] = 'completed'
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps({'architectural_components_restored': len(targets),
                  'step12_groups_reversed': sources['grounding_changes.json']['groups'],
                  'step15_groups_reversed': sources['reground_final.json']['groups'],
                  'coast_exported': True, 'saved': True}))
