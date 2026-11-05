shader_type spatial;
render_mode cull_disabled;

#include "res://demo/tropical_harbor_3d/materials/shore_common.gdshaderinc"

varying vec3 world_position;
varying vec3 vertex_tint;
varying float submerged_scatter;

void vertex() {
    world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
    vertex_tint = COLOR.rgb;
}

void fragment() {
    vec2 p = world_position.xz;
    float offset = p.x - shore(p.y);
    float broad = texture(water_noise, p * 0.045).r;
    float grain = texture(water_noise, p * 3.5).b;
    float sand_ripple = sin(offset * 26.0 + sin(p.y * 1.8) * 0.65 + broad * 4.0);
    float depth = max(-world_position.y, 0.0);
    float underwater = smoothstep(0.01, 0.20, depth);
    submerged_scatter = smoothstep(0.35, 4.0, depth) * 0.28;
    vec3 color = vertex_tint * (0.94 + broad * 0.085 + grain * 0.023);
    color *= 1.0 + sand_ripple * 0.012 * (1.0 - smoothstep(1.0, 2.5, abs(offset)));
    float phase = wash_phase(p.y, study_time);
    float wet_front = max(wash_front(phase), wash_front(fract(phase - 0.16)));
    float wet_sand = (1.0 - smoothstep(wet_front, wet_front + 0.32, offset))
        * smoothstep(-0.15, 0.15, offset);
    color *= 1.0 - wet_sand * 0.14;
    // Broad, restrained light shapes remain attached to the ground and receive shadows.
    float pattern = sand_light_pattern(p, study_time);
    color = mix(color, color * vec3(0.18, 0.90, 1.13), smoothstep(0.02, 0.65, depth));
    color *= 1.0 + pattern * 0.13 * smoothstep(0.08, 0.45, depth) * exp(-depth * 0.20);
    ALBEDO = color;
    ROUGHNESS = mix(0.93, 0.58, max(wet_sand, underwater * 0.6));
    SPECULAR = 0.18;
}

void light() {
    // Light scattered through the water fills distant seabed shadows. Dry
    // sand and very shallow contacts retain their normal direct-light contrast.
    float illumination = mix(ATTENUATION, 1.0, submerged_scatter);
    DIFFUSE_LIGHT += LIGHT_COLOR * illumination * max(dot(NORMAL, LIGHT), 0.0) / 3.14159265;
}
