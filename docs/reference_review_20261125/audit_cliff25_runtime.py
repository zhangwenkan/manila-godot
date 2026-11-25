"""Compare independently decoded Godot cache pixels with source/authoring data."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / 'demo/tropical_harbor_3d'
LOG = ROOT / 'captures/cliff_contacts_20261125'
ART = ROOT / 'assets/reference'
def digest(path, algorithm='sha256'):
    return hashlib.new(algorithm, Path(path).read_bytes()).hexdigest()
def pixels(row):
    size = row['width'] * row['height'] * row['format']['channels']
    return np.fromfile(LOG / row['raw_file'], dtype=row['format']['dtype'], count=size).reshape(row['height'], row['width'], row['format']['channels'])
probe = json.loads((LOG/'godot_texture_cache_probe.json').read_text())
report = {'date':datetime.now(timezone.utc).isoformat(), 'scope':'Independent read-only cache and shader audit; no visual acceptance', 'godot':probe['godot'], 'textures':{}}
for name, value in probe['textures'].items():
    source, cached = pixels(value['source']), pixels(value['cache'])
    path = ART/name
    config = path.with_suffix(path.suffix+'.import').read_text(encoding='utf-8-sig')
    params = dict(re.findall(r'^([^=\r\n]+)=([^\r\n]+)$', config, re.M))
    cache = REPO / params['path'].strip('"')[6:]
    md5_text = cache.with_suffix('.md5').read_text()
    md5_match = re.search(r'source_md5="([a-f0-9]+)"', md5_text)
    row = {'source_sha256':digest(path), 'cache_sha256':digest(cache), 'source_format':value['source']['format'],
           'cache_format':value['cache']['format'], 'width':source.shape[1], 'height':source.shape[0],
           'mipmaps':value['cache']['mipmaps'], 'source_md5_matches_cache':bool(md5_match and md5_match.group(1)==digest(path,'md5')),
           'cache_source_pixels_exact':bool(np.array_equal(source,cached)), 'max_cache_source_error':float(np.abs(source.astype(float)-cached).max()),
           'import_params':{k:v for k,v in params.items() if k.startswith(('compress/','process/','mipmaps/','detect_3d/'))}}
    if name.endswith('.png'):
        original = np.asarray(Image.open(path))
        row['pillow_source_pixels_exact'] = bool(np.array_equal(original,source))
        row['channel_minmax'] = [source.min(axis=(0,1)).tolist(), source.max(axis=(0,1)).tolist()]
        row['pass'] = row['pillow_source_pixels_exact'] and row['cache_source_pixels_exact'] and row['source_md5_matches_cache']
    else:
        authored = np.load(LOG/'mineral_fields.npz')['height'][::-1]
        error = np.abs(source[...,0]-authored)
        row['authored_R_exact'] = bool(np.array_equal(source[...,0],authored))
        row['authored_R_max_error'] = float(error.max())
        row['authored_R_rmse'] = float(np.sqrt(np.mean(error.astype(float)**2)))
        row['authored_minmax'] = [float(authored.min()),float(authored.max())]
        row['cache_minmax'] = [float(cached[...,0].min()),float(cached[...,0].max())]
        row['float32_preserved'] = value['cache']['format']['dtype'] == '<f4'
        row['replicated_rgb_equal'] = bool(np.array_equal(source[...,0],source[...,1]) and np.array_equal(source[...,1],source[...,2]))
        row['pass'] = row['authored_R_exact'] and row['float32_preserved'] and row['cache_source_pixels_exact'] and row['source_md5_matches_cache']
    report['textures'][name] = row
shader_path = ROOT/'materials/landform_mass.gdshader'
env_path = ROOT/'environment/reference_environment.gd'
shader, env = shader_path.read_text(), env_path.read_text()
checks = {
    'cliff_color_srgb':bool(re.search(r'uniform sampler2D cliff_region_color\s*:\s*source_color',shader)),
    'cliff_height_linear':bool(re.search(r'uniform sampler2D cliff_region_height\s*:\s*(?![^;]*source_color)[^;]+;',shader)),
    'ground_detail_linear':bool(re.search(r'uniform sampler2D ground_detail_map\s*:\s*(?![^;]*source_color)[^;]+;',shader)),
    'region_requires_global_and_local_flags':'if (ground_surface_enabled && cliff_region_enabled)' in shader,
    'detail_requires_global_and_local_flags':'if (ground_surface_enabled && ground_detail_enabled)' in shader,
    'all_bind_functions_called':all(f'    {fn}(sand_material)' in env for fn in ['_bind_ground_surfaces','_bind_cliff_region','_bind_ground_detail']),
    'cliff_pair_exact':all(f'ART + "{x}"' in env for x in ['C25_CliffRegion_Color.png','C25_CliffRegion_Height.exr']),
    'detail_binding_exact':'const GROUND_DETAIL_TEXTURE := ART + "C25_GroundDetail.png"' in env,
    'differentiates_height_before_scope':'dFdx(cliff_height_sample) * cliff_region_height_range * cliff_mix * weights.g' in shader,
    'detail_differentiates_height_before_scope':'dFdx(ground_detail_sample.b) * ground_height_weight' in shader,
    'detail_does_not_tint_rock':'rock *= ground_color_factor' not in shader,
}
report['wiring'] = {'shader_sha256':digest(shader_path),'environment_sha256':digest(env_path),'checks':checks,'pass':all(checks.values())}
report['pass'] = all(r['pass'] for r in report['textures'].values()) and report['wiring']['pass']
report['limitations'] = ['Static bindings and source/cache pixels only; GPU material appearance judged separately from capture.',
    'The EXR contains three replicated float32 channels, not single-channel RF; the sampled red channel is exact.',
    'Mipmaps presence checked, all top-mip texels compared; every mip texel is not independently compared.',
    'This report is bound to the listed source/cache/shader hashes and must be regenerated after texture changes.']
(LOG/'runtime_texture_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'pass':report['pass'],'textures':{k:{p:r.get(p) for p in ['pass','cache_source_pixels_exact','authored_R_exact','authored_R_max_error','float32_preserved']} for k,r in report['textures'].items()}},indent=2))
