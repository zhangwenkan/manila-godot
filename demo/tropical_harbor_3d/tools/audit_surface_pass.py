"""Read-only checks of this pass's exported geometry, material roles and source images."""
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / 'captures/surface_pass_20261113'


def read_glb(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from('<III', data)
    assert (magic, version, length) == (0x46546C67, 2, len(data))
    size, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4E4F534A
    doc = json.loads(data[20:20 + size])
    offset = 20 + size
    size, kind = struct.unpack_from('<II', data, offset)
    assert kind == 0x004E4942
    return doc, data[offset + 8:offset + 8 + size]


report = {}
for asset in ['coast/shipyard_combined.glb', 'fleet_boat_mcp.glb']:
    doc, binary = read_glb(ROOT / 'assets' / asset)
    old, _ = read_glb(CAP / 'before' / Path(asset).name)
    materials = {}
    texture_results = []
    for mat in doc['materials']:
        name = mat['name']
        if not name.startswith('SP13_'):
            continue
        pbr = mat['pbrMetallicRoughness']
        materials[name] = {'factor': pbr.get('baseColorFactor', [1, 1, 1, 1]),
                           'metallic_factor': pbr.get('metallicFactor', 1),
                           'normal_scale': mat.get('normalTexture', {}).get('scale', 1)}
        if name != 'SP13_BoatIronFastenings':
            assert pbr.get('baseColorTexture') and pbr.get('metallicRoughnessTexture'), name
            assert mat.get('normalTexture'), name
    for image in doc['images']:
        name = image.get('name', '')
        if name in ['boat_wood_albedo', 'boat_wood_normal']:
            view = doc['bufferViews'][image['bufferView']]
            start = view.get('byteOffset', 0)
            blob = binary[start:start + view['byteLength']]
            source = ROOT / 'assets' / (name + '.png')
            assert hashlib.sha256(blob).digest() == hashlib.sha256(source.read_bytes()).digest(), name
            texture_results.append({'name': name, 'retained_original_png': True, 'bytes': len(blob)})
        if not name.startswith('SP13_'):
            continue
        view = doc['bufferViews'][image['bufferView']]
        start = view.get('byteOffset', 0)
        blob = binary[start:start + view['byteLength']]
        source = ROOT / 'assets/coast/textures' / (name + '.png')
        assert source.is_file(), source
        assert hashlib.sha256(blob).digest() == hashlib.sha256(source.read_bytes()).digest(), name
        texture_results.append({'name': name, 'embedded_matches_source': True, 'bytes': len(blob)})
    for mesh in doc['meshes']:
        for prim in mesh['primitives']:
            assert {'POSITION', 'NORMAL', 'TEXCOORD_0'} <= set(prim['attributes']), mesh['name']
            assert doc['accessors'][prim['indices']]['count'] > 0
    assert len(materials) >= 5
    assert materials['SP13_BoatHullTimber']['normal_scale'] != materials['SP13_BoatWornRail']['normal_scale']
    report[asset] = {
        'meshes': len(doc['meshes']), 'before_meshes': len(old['meshes']),
        'triangles': sum(doc['accessors'][p['indices']]['count'] // 3
                         for m in doc['meshes'] for p in m['primitives']),
        'materials': materials, 'textures': texture_results,
    }

for name in ['harbor_terminal.glb']:
    current = ROOT / 'assets/coast' / name
    backup = CAP / 'before' / name
    assert hashlib.sha256(current.read_bytes()).digest() == hashlib.sha256(backup.read_bytes()).digest()
report['terminal_unchanged'] = True
(CAP / 'asset_audit.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print(json.dumps({k: {q: v[q] for q in ['meshes', 'triangles']} for k, v in report.items()
                  if isinstance(v, dict)}, ensure_ascii=False))
print('Embedded textures, role factors and exported attributes verified.')
