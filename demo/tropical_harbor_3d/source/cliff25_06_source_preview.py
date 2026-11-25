"""Bind C25 regional color/height into the editable source via owned GUI MCP.

This file is prepared externally but must only execute in the verified Blender
GUI through MCP. It neither writes runtime assets nor exports/saves the source.
It retains all existing nodes and replaces only its own C25Preview node set.
The original G23 BOX projections and original land-role preview remain intact.
"""
import bpy
import hashlib
import json
import os
import re
from pathlib import Path

assert not bpy.app.background and os.getpid() == 9864
assert bpy.types.blendermcp_server.port == 9881
ROOT = Path(bpy.data.filepath).parent.parent
assert Path(bpy.data.filepath).resolve() == (ROOT / 'source/harbor_shore_control_mcp.blend').resolve()
LOG = ROOT / 'captures/cliff_contacts_20261125'
shader_path = ROOT / 'materials/landform_mass.gdshader'
shader_text = shader_path.read_text(encoding='utf-8-sig')
required_chart_terms = (
    'smoothstep(21.8, 22.5, world_position.z)',
    'smoothstep(33.5, 34.3, world_position.z)',
    'smoothstep(37.4, 38.0, world_position.z)',
    'smoothstep(44.4, 45.1, world_position.z)',
    'smoothstep(15.7, 16.7, world_position.x)',
    'smoothstep(25.0, 26.0, world_position.x)',
    '(world_position.z + 0.26 * (world_position.x - 20.0) - 22.0) / 12.8',
    '(world_position.z - 0.24 * (world_position.x - 19.0) - 37.3) / 8.0',
    '(world_position.y - 0.9) / 4.0',
    '(world_position.y - 1.25) / 3.4',
)
assert all(term in shader_text for term in required_chart_terms), 'Runtime chart mapping changed; review source preview mapping'


def uniform(name):
    match = re.search(r'uniform\s+float\s+' + re.escape(name) + r'\s*=\s*([0-9.]+)', shader_text)
    assert match, 'Runtime default missing: ' + name
    return float(match.group(1))


region_range = uniform('cliff_region_height_range')
micro_range = uniform('cliff_micro_height_range')
terrain = bpy.data.objects['C25_ContourBuiltCoast']
material = terrain.data.materials[0]
assert material.name == 'Ref_L24_Landform' and material.use_nodes
nodes, links = material.node_tree.nodes, material.node_tree.links
required = ('G23_LandUse', 'G23Preview world', 'G23Preview Rock', 'G23Preview Rock weight',
            'G23Preview DIVIDE.001', 'G23Preview MULTIPLY.007', 'G23Preview preview microrelief',
            'Principled BSDF')
assert all(nodes.get(name) is not None for name in required)
color_image = bpy.data.images.get('C25_CliffRegion_Color')
height_image = bpy.data.images.get('C25_CliffRegion_Height')
assert color_image and height_image and color_image.packed_file and height_image.packed_file
assert color_image.colorspace_settings.name == 'sRGB'
assert height_image.colorspace_settings.name in ('Non-Color', 'Raw')
assert nodes['G23_LandUse'].image and nodes['G23_LandUse'].image.packed_file

# Restore only the known original attachment points before rebuilding this
# script's own nodes. No original preview node is deleted or renamed.
for old in list(nodes):
    if old.name.startswith('C25Preview '):
        nodes.remove(old)
links.new(nodes['G23Preview Rock'].outputs['Color'], nodes['G23Preview Rock weight'].inputs[1])
links.new(nodes['G23Preview preview microrelief'].outputs['Normal'], nodes['Principled BSDF'].inputs['Normal'])
for role in ('Grass', 'Path', 'Soil', 'Sand'):
    links.new(nodes['G23Preview ' + role].outputs['Color'], nodes['G23Preview ' + role + ' weight'].inputs[1])


def node(kind, label):
    result = nodes.new(kind)
    result.name = 'C25Preview ' + label
    result.label = label
    return result


def inp(target, socket, value):
    if hasattr(value, 'is_output'):
        links.new(value, target.inputs[socket])
    else:
        target.inputs[socket].default_value = value


def mathop(operation, a, b=0, label=None):
    n = node('ShaderNodeMath', label or operation)
    n.operation = operation
    inp(n, 0, a)
    inp(n, 1, b)
    return n.outputs[0]


def vecop(operation, a, b=None, label=None):
    n = node('ShaderNodeVectorMath', label or operation)
    n.operation = operation
    inp(n, 0, a)
    if b is not None:
        inp(n, 'Scale' if operation == 'SCALE' else 1, b)
    return n.outputs['Value' if operation == 'DOT_PRODUCT' else 'Vector']


def smooth(value, low, high, label):
    n = node('ShaderNodeMapRange', label)
    n.data_type = 'FLOAT'
    n.interpolation_type = 'SMOOTHSTEP'
    n.clamp = True
    inp(n, 'Value', value)
    inp(n, 'From Min', low)
    inp(n, 'From Max', high)
    inp(n, 'To Min', 0.0)
    inp(n, 'To Max', 1.0)
    return n.outputs['Result']


def mul(*args):
    result = args[0]
    for arg in args[1:]:
        result = mathop('MULTIPLY', result, arg)
    return result


def one_minus(value):
    return mathop('SUBTRACT', 1.0, value)


def blend_value(a, b, factor, label):
    return mathop('ADD', mul(a, one_minus(factor)), mul(b, factor), label)


def blend_color(a, b, factor, label):
    n = node('ShaderNodeMixRGB', label)
    n.blend_type = 'MIX'
    inp(n, 0, factor)
    inp(n, 1, a)
    inp(n, 2, b)
    return n.outputs['Color']


def color_multiply(a, b, label):
    n = node('ShaderNodeMixRGB', label)
    n.blend_type = 'MULTIPLY'
    inp(n, 0, 1.0)
    inp(n, 1, a)
    inp(n, 2, b)
    return n.outputs['Color']


def combine(x, y, z=0, label='UV'):
    n = node('ShaderNodeCombineXYZ', label)
    inp(n, 'X', x)
    inp(n, 'Y', y)
    inp(n, 'Z', z)
    return n.outputs['Vector']


def texture(image, uv, label):
    n = node('ShaderNodeTexImage', label)
    n.image = image
    n.extension = 'EXTEND'
    n.projection = 'FLAT'
    n.interpolation = 'Linear'
    links.new(uv, n.inputs['Vector'])
    return n


def red(color, label):
    n = node('ShaderNodeSeparateColor', label)
    n.mode = 'RGB'
    links.new(color, n.inputs[0])
    return n.outputs[0]


geometry = nodes['G23Preview world']
axes = node('ShaderNodeSeparateXYZ', 'Blender world axes')
links.new(geometry.outputs['Position'], axes.inputs[0])
x = axes.outputs['X']
z = mathop('MULTIPLY', axes.outputs['Y'], -1.0, 'Godot world Z')
h = axes.outputs['Z']
normal = geometry.outputs['Normal']
rear = one_minus(mathop('LESS_THAN', z, 36.0, 'Main chart selector'))
main_s = mathop('DIVIDE', mathop('SUBTRACT', mathop('ADD', z,
    mul(.26, mathop('SUBTRACT', x, 20.0))), 22.0), 12.8, 'Main chart S')
rear_s = mathop('DIVIDE', mathop('SUBTRACT', mathop('SUBTRACT', z,
    mul(.24, mathop('SUBTRACT', x, 19.0))), 37.3), 8.0, 'Rear chart S')
main_v = mathop('DIVIDE', mathop('SUBTRACT', h, .9), 4.0, 'Main chart V')
rear_v = mathop('DIVIDE', mathop('SUBTRACT', h, 1.25), 3.4, 'Rear chart V')
local_s = blend_value(main_s, rear_s, rear, 'Selected chart S')
local_v = blend_value(main_v, rear_v, rear, 'Selected chart V')
zone_main = mul(smooth(z, 21.8, 22.5, 'Main south fade'), one_minus(smooth(z, 33.5, 34.3, 'Main north fade')))
zone_rear = mul(smooth(z, 37.4, 38.0, 'Rear south fade'), one_minus(smooth(z, 44.4, 45.1, 'Rear north fade')))
zone_x = mul(smooth(x, 15.7, 16.7, 'West fade'), one_minus(smooth(x, 25.0, 26.0, 'East fade')))
chart_margin = mul(smooth(local_s, 0.0, .035, 'Chart left fade'),
    one_minus(smooth(local_s, .965, 1.0, 'Chart right fade')),
    smooth(local_v, 0.0, .035, 'Chart lower fade'),
    one_minus(smooth(local_v, .965, 1.0, 'Chart upper fade')))
cliff_mix = mul(mathop('MAXIMUM', zone_main, zone_rear), zone_x, chart_margin)
uv = combine(blend_value(mathop('ADD', .02, mul(.64, main_s)),
    mathop('ADD', .70, mul(.28, rear_s)), rear, 'Atlas U'),
    mathop('ADD', .02, mul(.96, local_v), 'Atlas V without Godot flip'), label='Cliff chart UV')
region_color = texture(color_image, uv, 'Regional mineral color')
region_height = texture(height_image, uv, 'Regional mineral height')
rock_color = blend_color(nodes['G23Preview Rock'].outputs['Color'],
    region_color.outputs['Color'], cliff_mix, 'Regional rock RGB')
links.new(rock_color, nodes['G23Preview Rock weight'].inputs[1])


def bump_gradient(height, distance, label):
    """Recover tangent height gradient without differentiating a role/scope mask."""
    bump = node('ShaderNodeBump', label + ' independent bump')
    inp(bump, 'Strength', 1.0)
    inp(bump, 'Distance', distance)
    inp(bump, 'Height', height)
    inp(bump, 'Normal', normal)
    n = bump.outputs['Normal']
    den = mathop('MAXIMUM', vecop('DOT_PRODUCT', n, normal), .0001)
    # For n_b=normalize(n_base-gradient), n_b/dot(n_b,n_base)
    # recovers n_base-gradient. No mask enters the Bump Height socket.
    return vecop('SUBTRACT', normal, vecop('SCALE', n, mathop('DIVIDE', 1.0, den)), label=label + ' gradient')


base_n = nodes['G23Preview preview microrelief'].outputs['Normal']
base_denom = mathop('MAXIMUM', vecop('DOT_PRODUCT', base_n, normal), .0001)
base_gradient = vecop('SUBTRACT', normal, vecop('SCALE', base_n, mathop('DIVIDE', 1.0, base_denom)), label='Existing preview gradient')
old_scale_node = nodes['G23Preview MULTIPLY.007']
assert old_scale_node.operation == 'MULTIPLY'
old_constants = [float(s.default_value) for s in old_scale_node.inputs[:2] if not s.is_linked]
assert len(old_constants) == 1 and abs(old_constants[0] - .24) < 1e-5, 'Existing rock height range changed'
old_range = old_constants[0]
assert 0 <= micro_range <= old_range
removed_old_gradient = bump_gradient(nodes['G23Preview Rock'].outputs['Alpha'], old_range-micro_range, 'Retired coarse rock')
regional_gradient = bump_gradient(red(region_height.outputs['Color'], 'Regional height R'), region_range, 'Regional mineral')
rock_weight = nodes['G23Preview DIVIDE.001'].outputs[0]
rock_delta = vecop('SUBTRACT', regional_gradient, removed_old_gradient, label='Regional gradient replacement')
combined_gradient = vecop('ADD', base_gradient, vecop('SCALE', rock_delta, mul(cliff_mix, rock_weight)), label='Local rock plus existing ground gradient')

# The final GroundDetail binding is optional while its independent authoring
# stage is pending. Only its RGB variation and independent B height are added
# here; the older source role-preview formula is intentionally preserved.
ground_image = bpy.data.images.get('C25_GroundDetail')
ground_enabled = bool(ground_image and ground_image.packed_file)
if ground_enabled:
    assert ground_image.colorspace_settings.name in ('Non-Color', 'Raw')
    gd_uv = combine(mathop('DIVIDE', mathop('SUBTRACT', x, 7.0), 20.0),
                    mathop('DIVIDE', mathop('SUBTRACT', z, 22.0), 23.0), label='Ground detail UV without Godot flip')
    gd = texture(ground_image, gd_uv, 'Ground detail RGBA data')
    gd_sep = node('ShaderNodeSeparateColor', 'Ground detail RGB data')
    gd_sep.mode = 'RGB'
    links.new(gd.outputs['Color'], gd_sep.inputs[0])
    scope = mul(smooth(x, 7.0, 8.0, 'Ground west fade'), one_minus(smooth(x, 26.0, 27.0, 'Ground east fade')),
                smooth(z, 22.0, 23.0, 'Ground south fade'), one_minus(smooth(z, 44.0, 45.0, 'Ground north fade')))
    luminance = mathop('ADD', 1.0, mul(mathop('SUBTRACT', gd_sep.outputs['Red'], .5), .48, scope))
    warmth = mul(mathop('SUBTRACT', gd_sep.outputs['Green'], .5), scope)
    tint = combine(mathop('ADD', 1.0, mul(warmth, .15)),
                   mathop('ADD', 1.0, mul(warmth, .025)),
                   mathop('ADD', 1.0, mul(warmth, -.12)), label='Ground linear RGB warmth')
    local_multiplier = vecop('SCALE', tint, luminance, label='Ground scoped RGB multiplier')
    for role in ('Grass', 'Path', 'Soil', 'Sand'):
        rgb = color_multiply(nodes['G23Preview '+role].outputs['Color'], local_multiplier, role+' ground detail RGB')
        links.new(rgb, nodes['G23Preview '+role+' weight'].inputs[1])
    detail_gradient = bump_gradient(gd_sep.outputs['Blue'], .020, 'Ground detail')
    nonrock_weight = mathop('ADD', nodes['G23Preview DIVIDE'].outputs[0], nodes['G23Preview DIVIDE.002'].outputs[0])
    nonrock_weight = mathop('ADD', nonrock_weight, nodes['G23Preview DIVIDE.003'].outputs[0])
    nonrock_weight = mathop('ADD', nonrock_weight, nodes['G23Preview DIVIDE.004'].outputs[0])
    combined_gradient = vecop('ADD', combined_gradient,
        vecop('SCALE', detail_gradient, mul(scope, nonrock_weight)), label='Regional rock and ground gradient')
final_normal = vecop('NORMALIZE', vecop('SUBTRACT', normal, combined_gradient), label='Final preview normal')
links.new(final_normal, nodes['Principled BSDF'].inputs['Normal'])

material['C25_source_preview'] = 'Two world-coordinate mineral charts plus optional GroundDetail RGB/B. Original global G23 BOX and role preview retained; no scope-mask derivatives in new relief.'
material['C25_source_preview_contact_alpha_applied'] = False
report = {'applied': True, 'pid': os.getpid(), 'source': bpy.data.filepath,
          'runtime_assets_written': False, 'source_saved': False, 'old_preview_nodes_retained': True,
          'new_nodes': sum(n.name.startswith('C25Preview ') for n in nodes),
          'regional_images': [color_image.name, height_image.name],
          'regional_height_range_m': region_range, 'old_rock_auxiliary_range_m': micro_range,
          'mapping': 'Blender (X,-Z,H) -> Godot (X,H,Z); identical two charts, no Blender V flip',
          'grounddetail_rgb_and_height_applied': ground_enabled, 'grounddetail_contact_alpha_applied': False,
          'shader_sha256': hashlib.sha256(shader_text.encode('utf-8')).hexdigest(),
          'land_use_export_node_retained': nodes.get('G23_LandUse') is not None,
          'limitations': ['Existing source G23 BOX projection and squared role weights are retained; this is not a pixel-equivalent replacement for Godot triplanar and competitive land-use mixing.',
                          'GroundDetail A contact-width relaxation remains runtime-only; no claim of source preview contact-alpha parity.',
                          'Original G23 preview height-mask derivative behavior remains; newly added regional and GroundDetail relief never differentiates its scope/role mask.'],
          'visual_accepted': False}
(LOG / 'source_preview.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
