"""Proposal builder only: never edits the active shader or Blender scene.

Input atlas: main cliff occupies U .02.. .66; tavern rear U .70.. .98.
Both charts use V .02.. .98 with PNG row zero at the chart's high edge.
Color is authored sRGB; height is an independent linear R float EXR.
Authoring and export remain the owned GUI Blender MCP caller's responsibility.
"""
from pathlib import Path


UNIFORMS = """
// C25 local, nonrepeating mineral planes; the existing LandUse still owns roles.
uniform bool cliff_region_enabled = false;
uniform sampler2D cliff_region_color : source_color, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D cliff_region_height : repeat_disable, filter_linear_mipmap_anisotropic;
uniform float cliff_region_height_range = 0.16;
uniform float cliff_micro_height_range = 0.020;
"""

REGIONAL_SAMPLE = """
    float cliff_mix = 0.0;
    float cliff_height_sample = 0.5;
    if (ground_surface_enabled && cliff_region_enabled) {
        float zone_main = smoothstep(21.8, 22.5, world_position.z)
            * (1.0 - smoothstep(33.5, 34.3, world_position.z));
        float zone_rear = smoothstep(37.4, 38.0, world_position.z)
            * (1.0 - smoothstep(44.4, 45.1, world_position.z));
        float zone_x = smoothstep(15.7, 16.7, world_position.x)
            * (1.0 - smoothstep(25.0, 26.0, world_position.x));
        float rear = step(36.0, world_position.z);
        float main_s = (world_position.z + 0.26 * (world_position.x - 20.0) - 22.0) / 12.8;
        float rear_s = (world_position.z - 0.24 * (world_position.x - 19.0) - 37.3) / 8.0;
        float main_v = (world_position.y - 0.9) / 4.0;
        float rear_v = (world_position.y - 1.25) / 3.4;
        float local_s = mix(main_s, rear_s, rear);
        float local_v = mix(main_v, rear_v, rear);
        float chart_margin = smoothstep(0.0, 0.035, local_s)
            * (1.0 - smoothstep(0.965, 1.0, local_s))
            * smoothstep(0.0, 0.035, local_v)
            * (1.0 - smoothstep(0.965, 1.0, local_v));
        vec2 cliff_uv = vec2(mix(0.02 + 0.64 * main_s, 0.70 + 0.28 * rear_s, rear),
            1.0 - (0.02 + 0.96 * local_v));
        // The two charts do not draw a rock layer across the protected uphill road.
        cliff_mix = max(zone_main, zone_rear) * zone_x * chart_margin;
        vec3 region_color = texture(cliff_region_color, cliff_uv).rgb;
        cliff_height_sample = texture(cliff_region_height, cliff_uv).r;
        rock = mix(rock, region_color, cliff_mix);
        // Old G23 is only a fine auxiliary height inside this local region.
        height_ranges.y = mix(height_ranges.y, cliff_micro_height_range, cliff_mix);
    }

"""

REGIONAL_DERIVATIVE = """
    // Differentiate the authored field, never its scope or LandUse weights.
    // Real major shoulders remain mesh geometry; these centimetres alter lighting only.
    surface_dx += dFdx(cliff_height_sample) * cliff_region_height_range * cliff_mix * weights.g;
    surface_dy += dFdy(cliff_height_sample) * cliff_region_height_range * cliff_mix * weights.g;
"""


def build_proposal(original: str) -> str:
    if "uniform bool cliff_region_enabled" in original:
        raise ValueError("Regional shader interface already exists; inspect instead of replay")
    header = "varying vec3 world_position;"
    marker = "    vec4 weights = max(land_use, vec4(0.0));"
    deriv = "    vec3 position_dx = dFdx(world_position);"
    for anchor in (header, marker, deriv):
        if original.count(anchor) != 1:
            raise ValueError("Active shader changed; proposal anchor is ambiguous: " + anchor)
    proposed = original.replace(header, UNIFORMS + "\n" + header)
    proposed = proposed.replace(marker, REGIONAL_SAMPLE + marker)
    return proposed.replace(deriv, REGIONAL_DERIVATIVE + deriv)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    active = root / "demo/tropical_harbor_3d/materials/landform_mass.gdshader"
    review = root / "docs/reference_review_20261125"
    review.mkdir(parents=True, exist_ok=True)
    destination = review / "landform_mass.cliff25.proposed.gdshader"
    destination.write_text(build_proposal(active.read_text(encoding="utf-8-sig")), encoding="utf-8")
    print(destination)
