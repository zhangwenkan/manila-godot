shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_disabled;

#include "res://demo/tropical_harbor_3d/materials/shore_common.gdshaderinc"

uniform sampler2D scene_depth : hint_depth_texture, repeat_disable, filter_nearest;
uniform vec3 deep_color : source_color = vec3(0.025, 0.40, 0.46);
uniform vec3 middle_color : source_color = vec3(0.035, 0.63, 0.58);
uniform vec3 shallow_color : source_color = vec3(0.065, 0.67, 0.57);
uniform vec3 foam_color : source_color = vec3(0.91, 0.94, 0.86);
// xyz = position, w = wake strength; hidden boats use w < 0.
uniform vec4 boats[3];
uniform vec2 stern_directions[3];
uniform vec4 contact_objects[32];
uniform int contact_count = 0;
uniform sampler2D reflection_tex : source_color, repeat_disable, filter_linear;
uniform float reflection_amount = 0.65;
uniform float glint_strength : hint_range(0.0, 2.0) = 1.0;
uniform float sky_reflection_strength : hint_range(0.0, 1.0) = 1.0;
uniform float surface_shadow_strength : hint_range(0.0, 1.0) = 0.035;
varying vec3 world_position;
varying vec3 glint_view;
varying float foam_coverage;
varying float open_water;
varying float glint_style;
varying vec3 sparkle_normal;
varying float sparkle_power;
varying float hull_contact;
varying float glint_breakup;

vec2 ripple_gradient(vec2 uv) {
    float step_uv = 2.0 / 512.0;
    return vec2(
        texture(water_noise, uv + vec2(step_uv, 0.0)).g - texture(water_noise, uv - vec2(step_uv, 0.0)).g,
        texture(water_noise, uv + vec2(0.0, step_uv)).g - texture(water_noise, uv - vec2(0.0, step_uv)).g
    ) / (2.0 * step_uv);
}

float hull_field(vec2 p) {
    float best = 0.0;
    for (int i = 0; i < 3; i++) {
        if (boats[i].w < 0.0) { continue; }
        vec2 stern = stern_directions[i];
        if (dot(stern, stern) < 0.01) { continue; }
        vec2 delta = p - boats[i].xz;
        vec2 right = vec2(stern.y, -stern.x);
        vec2 rel = vec2(dot(delta, right), dot(delta, stern));
        float e = length(vec2(rel.x / 0.92, rel.y / 2.32));
        best = max(best, 1.0 - smoothstep(0.98, 1.10, e));
    }
    return best;
}

float pile_field(vec2 p) {
    float best = 0.0;
    for (int i = 0; i < 32; i++) {
        if (i >= contact_count) { break; }
        vec4 object = contact_objects[i];
        float d = length(p - object.xy);
        best = max(best, (1.0 - smoothstep(object.z, object.z + 0.14, d)) * object.w);
    }
    return best;
}

void vertex() {
    vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
    float dist = max(shore(wp.z) - wp.x, 0.0);
    float amount = smoothstep(1.0, 5.0, dist);
    VERTEX.y += (sin(wp.x * 0.66 + wp.z * 0.43 + study_time * 0.72) * 0.025
        + sin(wp.z * 1.15 - wp.x * 0.28 + study_time * 0.93) * 0.016
        + sin(wp.x * 0.28 + wp.z * 0.19 + study_time * 0.64) * 0.035) * amount;
    float contact = max(hull_field(wp.xz), pile_field(wp.xz));
    VERTEX.y += contact * 0.010 * amount;
    world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
    vec2 p = world_position.xz;
    float t = study_time;
    float dist = shore(p.y) - p.x;
    vec2 flow = p * vec2(0.040, 0.052) + vec2(-t * 0.0027, t * 0.0021);
    vec2 broad_flow = p * 0.057 + vec2(t * 0.004, -t * 0.003);
    float large = texture(water_noise, broad_flow).r;
    float e = 0.012;
    float dx = texture(water_noise, flow + vec2(e, 0)).g - texture(water_noise, flow - vec2(e, 0)).g;
    float dz = texture(water_noise, flow + vec2(0, e)).g - texture(water_noise, flow - vec2(0, e)).g;
    dx += cos(p.x * 1.5 + p.y * 2.4 + t * 0.8) * 0.025;
    dz += sin(p.y * 3.0 - p.x * 0.6 + t * 1.1) * 0.032;
    vec3 wave_normal = normalize(vec3(-dx * 0.42, 1.0, -dz * 0.46));
    // Style follows the sea floor, not the view ray or the depth of passing objects.
    float bed_depth = max(-sand_height(-dist, p.y), 0.0);
    open_water = smoothstep(0.8, 3.0, bed_depth);
    vec2 slow_flow = p * vec2(0.009, 0.012) + vec2(-t * 0.00065, t * 0.00050);
    float broad_dx = texture(water_noise, slow_flow + vec2(0.022, 0)).g
        - texture(water_noise, slow_flow - vec2(0.022, 0)).g;
    float broad_dz = texture(water_noise, slow_flow + vec2(0, 0.022)).g
        - texture(water_noise, slow_flow - vec2(0, 0.022)).g;
    vec2 long_wave = vec2(sin(p.x * 0.48 + p.y * 0.33 + t * 0.45),
        cos(p.y * 0.61 - p.x * 0.21 - t * 0.39));
    vec3 calm_normal = normalize(vec3(-broad_dx * 0.24 + long_wave.x * 0.030,
        1.0, -broad_dz * 0.26 + long_wave.y * 0.035));
    NORMAL = normalize(mat3(VIEW_MATRIX) * mix(wave_normal, calm_normal, open_water));
    glint_style = smoothstep(0.25, 1.5, bed_depth);
    // Crossing height fields change the reflecting facets, not a painted white pattern.
    vec2 ripple_a = p * 0.055 + vec2(-t * 0.0066, t * 0.0035);
    vec2 rotated_p = vec2(p.x * 0.8 - p.y * 0.6, p.x * 0.6 + p.y * 0.8);
    vec2 ripple_b = rotated_p * 0.038 + vec2(t * 0.0031, t * 0.0051) + vec2(0.37, 0.71);
    vec2 slope_a = ripple_gradient(ripple_a) * (0.055 * 0.44);
    vec2 slope_b = ripple_gradient(ripple_b) * (0.038 * 0.58);
    vec2 slope = slope_a + vec2(slope_b.x * 0.8 + slope_b.y * 0.6,
        -slope_b.x * 0.6 + slope_b.y * 0.8);
    slope *= 0.28;
    slope += vec2(cos(p.x * 0.66 + p.y * 0.43 + t * 0.72) * 0.0165
        - cos(p.y * 1.15 - p.x * 0.28 + t * 0.93) * 0.00448,
        cos(p.x * 0.66 + p.y * 0.43 + t * 0.72) * 0.01075
        + cos(p.y * 1.15 - p.x * 0.28 + t * 0.93) * 0.0184);
    slope += vec2(0.0098, 0.00665) * cos(p.x * 0.28 + p.y * 0.19 + t * 0.64);
    sparkle_normal = normalize(mat3(VIEW_MATRIX) * normalize(vec3(-slope.x, 1.0, -slope.y)));
    vec3 pixel_dx = dFdx(sparkle_normal);
    vec3 pixel_dy = dFdy(sparkle_normal);
    float slope_variance = dot(pixel_dx, pixel_dx) + dot(pixel_dy, pixel_dy);
    sparkle_power = 3400.0 / (1.0 + 600.0 * slope_variance);
    // A finite reflection eye gives an orthographic view a localized sun path.
    // Keep its distance stable when switching overview / close-up camera positions.
    vec3 camera_axis = INV_VIEW_MATRIX[2].xyz;
    vec3 water_focus = CAMERA_POSITION_WORLD - camera_axis
        * (CAMERA_POSITION_WORLD.y / max(camera_axis.y, 0.15));
    vec3 reflection_eye = water_focus + camera_axis * 32.0;
    glint_view = normalize(mat3(VIEW_MATRIX) * (reflection_eye - world_position));
    glint_breakup = smoothstep(0.40, 0.70,
        texture(water_noise, p * 0.085 + vec2(-t * 0.003, t * 0.002)).r);

    // Reverse Z: farther samples are smaller. Use the farthest neighbor so a hull
    // silhouette does not collapse the water column to a sparkling thin film.
    vec2 pixel = vec2(dFdx(SCREEN_UV.x), dFdy(SCREEN_UV.y));
    float d0 = texture(scene_depth, SCREEN_UV).r;
    float d1 = texture(scene_depth, SCREEN_UV + vec2(pixel.x, 0.0)).r;
    float d2 = texture(scene_depth, SCREEN_UV - vec2(pixel.x, 0.0)).r;
    float d3 = texture(scene_depth, SCREEN_UV + vec2(0.0, pixel.y)).r;
    float d4 = texture(scene_depth, SCREEN_UV - vec2(0.0, pixel.y)).r;
    float far_depth = min(d0, min(min(d1, d2), min(d3, d4)));
    vec4 bottom_view = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, far_depth, 1.0);
    bottom_view.xyz /= max(bottom_view.w, 0.00001);
    vec3 bottom_world = (INV_VIEW_MATRIX * vec4(bottom_view.xyz, 1.0)).xyz;
    vec3 surface_view = (VIEW_MATRIX * vec4(world_position, 1.0)).xyz;
    float sampled_thickness = clamp(world_position.y - bottom_world.y, 0.0, 35.0);
    float contact = max(hull_field(p), pile_field(p));
    // Use the actual ray to submerged geometry. A footprint projected onto the
    // surface misses submerged hulls/piles at grazing angles and creates a cuff.
    float short_column = 1.0 - smoothstep(0.08, 0.65, sampled_thickness);
    float path_length = clamp(length(bottom_view.xyz - surface_view), 0.0, 65.0);
    if (far_depth < 0.000001) {
        path_length = 65.0;
    }
    // Palette follows the water beneath this point. At low viewing angles the
    // depth buffer can jump between seabed ridges; that must not change its hue.
    vec3 col = mix(shallow_color, middle_color, smoothstep(0.25, 2.8, bed_depth));
    col = mix(col, deep_color, smoothstep(3.0, 11.0, bed_depth));
    float broad_height = texture(water_noise, slow_flow).g;
    float broad_ribbon = 1.0 - smoothstep(0.012, 0.075, abs(broad_height - 0.50));
    col *= mix(0.97 + large * 0.055, 0.96 + broad_height * 0.07 + broad_ribbon * 0.035, open_water);
    // Short columns stay clear, so submerged wood, stones and their shadows
    // retain contrast. Long columns still absorb enough light to read as deep sea.
    float absorption = mix(0.24, 0.40, smoothstep(2.0, 10.0, bed_depth));
    float opacity = 1.0 - exp(-path_length * absorption);
    float fresnel = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 5.0);
    // A grazing view of submerged timber must not turn the short water column
    // into an opaque cyan cuff. Reserve the extra surface haze for open water.
    opacity = clamp(opacity + fresnel * 0.30 * (1.0 - short_column), 0.015, 0.98);

    float waterline = contact * (1.0 - contact) * 4.0;
    waterline = clamp(waterline, 0.0, 1.0);
    // Interior of the hull must stay a short, clear column so wet wood
    // reads through. Only the meniscus ring picks up extra water.
    col *= 1.0 - waterline * 0.08;
    opacity = max(opacity, waterline * 0.10);

    float foam = 0.0;
    for (int i = 0; i < 3; i++) {
        if (boats[i].w <= 0.0) { continue; }
        vec2 delta = p - boats[i].xz;
        vec2 stern = stern_directions[i];
        vec2 right = vec2(stern.y, -stern.x);
        vec2 rel = vec2(dot(delta, right), dot(delta, stern));
        float wake_strength = boats[i].w;
        float behind = rel.y - 1.45;
        float spread = 0.58 + max(behind, 0.0) * 0.30;
        float wake_noise = texture(water_noise, p * vec2(0.75, 0.48) + vec2(0, -t * 0.11)).r;
        float edge = 1.0 - smoothstep(0.06, 0.34, abs(abs(rel.x) - spread + (wake_noise - 0.5) * 0.42));
        float crest = mix(0.18, 1.0, smoothstep(0.28, 0.64, wake_noise));
        float decay = smoothstep(0.0, 0.6, behind) * (1.0 - smoothstep(1.0, 7.0, behind));
        float churn = smoothstep(0.52, 0.72, wake_noise) * (1.0 - smoothstep(0.15, spread, abs(rel.x)));
        foam = max(foam, (edge * crest * 0.46 + churn * 0.22) * decay * wake_strength);
        float bow = length(vec2(rel.x / 0.8, (rel.y + 1.75) / 0.85));
        foam = max(foam, (1.0 - smoothstep(0.035, 0.12, abs(bow - 1.0)))
            * (1.0 - smoothstep(-1.4, -0.9, rel.y)) * wake_strength * 0.30);
    }

    foam = clamp(foam, 0.0, 0.95);
    foam_coverage = foam;
    hull_contact = contact;
    ALBEDO = mix(col, foam_color, foam);
    if (reflection_amount > 0.001) {
        vec2 warp = (mat3(VIEW_MATRIX) * vec3(slope.x, 0.0, slope.y)).xy * 0.014;
        // Mirroring the camera basis flips horizontal handedness, not height.
        vec2 ruv = vec2(1.0 - SCREEN_UV.x, SCREEN_UV.y) + warp;
        vec4 refl = texture(reflection_tex, ruv);
        float edge = step(0.0, ruv.x) * step(ruv.x, 1.0) * step(0.0, ruv.y) * step(ruv.y, 1.0);
        float refl_w = (0.035 + fresnel * 0.65) * reflection_amount * (1.0 - foam) * refl.a * edge;
        refl_w *= smoothstep(0.12, 0.8, bed_depth) * (1.0 - hull_contact);
        ALBEDO = mix(ALBEDO, refl.rgb, clamp(refl_w, 0.0, 0.32));
    }
    ALPHA = mix(opacity, 0.97, foam) * smoothstep(0.0, 0.18, dist);
    ROUGHNESS = mix(mix(0.24, 0.34, open_water), 0.85, foam);
    SPECULAR = mix(0.50, 0.24, open_water * (1.0 - foam)) * sky_reflection_strength
        * mix(1.0, 0.12, short_column);
    METALLIC = 0.0;
}

void light() {
    float diffuse = max(dot(NORMAL, LIGHT), 0.0);
    // Clear water is not an opaque shadow receiver. Keep only a little surface
    // darkening; the seabed retains the full projected shadow through the water.
    // Sun glitter still receives full occlusion beneath boats and piers.
    float surface_light = mix(1.0, ATTENUATION, surface_shadow_strength);
    DIFFUSE_LIGHT += LIGHT_COLOR * surface_light * diffuse / 3.14159265;
    vec3 halfway = normalize(LIGHT + glint_view);
    float sparkle = pow(max(dot(sparkle_normal, halfway), 0.0), sparkle_power);
    sparkle *= (sparkle_power / 3400.0) * mix(0.18, 0.25, glint_style) * glint_breakup;
    sparkle *= (1.0 - hull_contact) * glint_strength;
    SPECULAR_LIGHT += LIGHT_COLOR * ATTENUATION * sparkle * (1.0 - foam_coverage);
}
