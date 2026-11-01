shader_type spatial;
render_mode cull_disabled;

uniform sampler2D water_noise : repeat_enable, filter_linear_mipmap_anisotropic;
uniform vec3 deep_color : source_color = vec3(0.025, 0.30, 0.58);
uniform vec3 middle_color : source_color = vec3(0.015, 0.51, 0.66);
uniform vec3 shallow_color : source_color = vec3(0.12, 0.73, 0.70);
uniform vec3 foam_color : source_color = vec3(0.85, 0.97, 0.88);
uniform float study_time = 0.0;
uniform vec3 boat_position = vec3(-4.0, 0.0, 3.0);
uniform float wake_strength = 0.0;
varying vec3 world_position;

float shore(float z) {
    return 8.0 + sin(z * 0.14) * 2.0 + sin(z * 0.37 + 0.4) * 0.6;
}

float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

float wavelets(vec2 p, float time) {
    vec2 grid = vec2(p.x * 0.83 + p.y * 0.24, p.y * 1.7 + time * 0.09);
    vec2 id = floor(grid);
    vec2 local = fract(grid) - 0.5;
    float random = hash21(id);
    local -= vec2(hash21(id + 5.8) - 0.5, hash21(id + 16.3) - 0.5) * 0.48;
    local.y += sin(local.x * 7.0 + random * 6.28) * 0.045;
    float width = mix(0.12, 0.34, random);
    float line = length(vec2(local.x / width, local.y / 0.035));
    float aa = max(fwidth(line), 0.2);
    float shape = 1.0 - smoothstep(0.7 - aa, 1.0 + aa, line);
    float life = pow(max(sin(time * 0.55 + random * 31.4), 0.0), 2.0);
    return shape * life * smoothstep(0.57, 0.78, random);
}

void vertex() {
    vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
    float dist = max(shore(wp.z) - wp.x, 0.0);
    float amount = smoothstep(0.0, 3.0, dist);
    VERTEX.y += (sin(wp.x * 0.66 + wp.z * 0.43 + study_time * 0.72) * 0.035
        + sin(wp.z * 1.15 - wp.x * 0.28 + study_time * 0.93) * 0.022) * amount;
    world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
    vec2 p = world_position.xz;
    float t = study_time;
    float dist = shore(p.y) - p.x;
    vec2 flow_a = p * 0.047 + vec2(t * 0.003, -t * 0.006);
    vec2 flow_b = p * vec2(0.10, 0.16) + vec2(-t * 0.007, t * 0.003);
    float large = texture(water_noise, flow_a).r;
    float small = texture(water_noise, flow_b).g;
    float depth = max(dist + (large - 0.5) * 2.4, 0.0);
    vec3 col = mix(shallow_color, middle_color, smoothstep(1.0, 9.5, depth));
    col = mix(col, deep_color, smoothstep(7.0, 24.0, depth));
    col *= 0.94 + large * 0.13 + (small - 0.5) * 0.045;

    float e = 0.012;
    float dx = (texture(water_noise, flow_b + vec2(e, 0)).g - texture(water_noise, flow_b - vec2(e, 0)).g);
    float dz = (texture(water_noise, flow_b + vec2(0, e)).g - texture(water_noise, flow_b - vec2(0, e)).g);
    dx += cos(p.x * 1.5 + p.y * 2.4 + t * 0.8) * 0.055;
    dz += sin(p.y * 3.0 - p.x * 0.6 + t * 1.1) * 0.075;
    vec3 wave_normal = normalize(vec3(-dx * 0.28, 1.0, -dz * 0.33));
    NORMAL = normalize(mat3(VIEW_MATRIX) * wave_normal);

    float coast_noise = texture(water_noise, vec2(p.y * 0.1, dist * 0.24 - t * 0.04)).b;
    float wash = 0.24 + 0.18 * sin(t * 0.9 + p.y * 0.22) + (coast_noise - 0.5) * 0.23;
    float lip = (1.0 - smoothstep(0.025, 0.17, abs(dist - wash)));
    float outer = 0.82 + sin(p.y * 0.53 - t * 0.85) * 0.12;
    float lace = (1.0 - smoothstep(0.025, 0.075, abs(dist - outer)))
        * smoothstep(0.43, 0.61, coast_noise) * (0.4 + 0.35 * sin(t * 0.9 + p.y));
    float foam = max(lip * 0.9, lace);
    foam = max(foam, wavelets(p, t) * 0.58 * smoothstep(1.0, 4.0, dist));

    vec2 rel = p - boat_position.xz;
    float behind = rel.y - 1.45;
    float spread = 0.58 + max(behind, 0.0) * 0.30;
    float wake_noise = texture(water_noise, p * vec2(0.75, 0.48) + vec2(0, -t * 0.11)).r;
    float edge = 1.0 - smoothstep(0.04, 0.24, abs(abs(rel.x) - spread + (wake_noise - 0.5) * 0.32));
    float decay = smoothstep(0.0, 0.6, behind) * (1.0 - smoothstep(1.0, 9.0, behind));
    float churn = smoothstep(0.52, 0.72, wake_noise) * (1.0 - smoothstep(0.15, spread, abs(rel.x)));
    foam = max(foam, (edge * 0.7 + churn * 0.33) * decay * wake_strength);
    float bow = length(vec2(rel.x / 0.8, (rel.y + 1.75) / 0.85));
    foam = max(foam, (1.0 - smoothstep(0.035, 0.12, abs(bow - 1.0)))
        * (1.0 - smoothstep(-1.4, -0.9, rel.y)) * wake_strength * 0.6);

    col = mix(col, foam_color, clamp(foam, 0.0, 0.93));
    ALBEDO = col;
    EMISSION = col * 0.18;
    ROUGHNESS = mix(0.27, 0.8, clamp(foam, 0.0, 1.0));
    SPECULAR = 0.36;
    METALLIC = 0.05;
}
