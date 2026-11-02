shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_disabled;

#include "res://materials/shore_common.gdshaderinc"

uniform bool debug_foam_mask = false;
uniform vec3 foam_color : source_color = vec3(0.91, 0.94, 0.86);
uniform vec3 film_color : source_color = vec3(0.38, 0.59, 0.49);
varying vec3 world_position;

void vertex() {
    world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
    vec2 p = world_position.xz;
    float offset = p.x - shore(p.y);
    vec2 coverage = swash_coverage(p, offset, study_time);
    float bounds = smoothstep(-1.8, -1.35, offset) * (1.0 - smoothstep(0.90, 1.15, offset));
    float foam = clamp(coverage.x * bounds, 0.0, 1.0);
    float film = coverage.y * bounds * 0.075;
    ALBEDO = mix(film_color, foam_color, foam);
    ALPHA = max(film, foam * 0.94);
    ROUGHNESS = mix(0.32, 0.90, foam);
    SPECULAR = mix(0.38, 0.18, foam);
    METALLIC = 0.0;
    if (debug_foam_mask) {
        ALBEDO = vec3(0.0);
        EMISSION = vec3(foam);
        ALPHA = 1.0;
        SPECULAR = 0.0;
    }
}
