uniform sampler2D water_noise : repeat_enable, filter_linear_mipmap_anisotropic;
uniform float study_time = 0.0;
uniform vec4 coast_shape = vec4(8.0, 2.0, 0.6, 0.0);
uniform vec4 bay_shape = vec4(-2.5, 3.6, 2.2, 0.85);
uniform float wash_period = 4.8;

float shore(float z) {
    float bay = (z - bay_shape.x) / bay_shape.y;
    float point = (z - bay_shape.x - 5.0) / (bay_shape.y * 0.65);
    return coast_shape.x + sin(z * 0.14) * coast_shape.y
        + sin(z * 0.37 + 0.4) * coast_shape.z
        + bay_shape.z * exp(-bay * bay) - bay_shape.w * exp(-point * point);
}

float sand_height(float offset, float z) {
    if (offset < 0.0) {
        float d = -offset;
        return -0.11 * d - 0.013 * d * d / (1.0 + d * 0.025);
    }
    return min(offset * 0.20, 0.7)
        + smoothstep(2.0, 14.0, offset) * (0.2 + sin(z * 0.21) * 0.16);
}

float wash_phase(float z, float t) {
    return fract(t / wash_period + sin(z * 0.19) * 0.045 + z * 0.003);
}

float wash_front(float phase) {
    return -0.92 + 1.60 * pow(max(sin(phase * 3.14159265), 0.0), 0.9);
}

vec2 cell_hash(vec2 p) {
    return fract(sin(vec2(dot(p, vec2(127.1, 311.7)),
        dot(p, vec2(269.5, 183.3)))) * 43758.5453);
}

// Soft cell boundaries, not opaque white foam. Evaluated on the sea floor.
float sand_light_pattern(vec2 p, float t) {
    vec2 drift = vec2(sin(p.y * 0.71 + t * 0.21), cos(p.x * 0.63 - t * 0.17)) * 0.32;
    drift += texture(water_noise, p * 0.006 + vec2(t * 0.0004, -t * 0.0003)).rg * 0.50;
    vec2 q = p * 0.37 + drift;
    vec2 cell = floor(q);
    vec2 f = fract(q);
    float first = 8.0;
    float second = 8.0;
    for (int y = -1; y <= 1; y++) {
        for (int x = -1; x <= 1; x++) {
            vec2 offset = vec2(float(x), float(y));
            vec2 seed = cell_hash(cell + offset);
            vec2 point = offset + 0.5 + 0.30 * sin(seed * 6.2831853 + t * 0.19) - f;
            float d = dot(point, point);
            if (d < first) {
                second = first;
                first = d;
            } else {
                second = min(second, d);
            }
        }
    }
    return 1.0 - smoothstep(0.025, 0.19, sqrt(second) - sqrt(first));
}

// x: foam coverage, y: thin water coverage. Both follow the same advancing front.
vec2 swash_coverage(vec2 p, float offset, float t) {
    float phase = wash_phase(p.y, t);
    float noise = texture(water_noise, p * vec2(0.065, 0.080) + vec2(-t * 0.0024, t * 0.0018)).b;
    float front = wash_front(phase) + (texture(water_noise, p * 0.23).r - 0.5) * 0.12;
    float aa = max(fwidth(offset), 0.008);
    float behind = front - offset;
    float wet = smoothstep(-aa, aa * 2.0, behind);
    float envelope = pow(max(sin(phase * 3.14159265), 0.0), 0.65);
    float width = 0.12 + envelope * 0.86;
    float band = wet * (1.0 - smoothstep(width * 0.60, width, behind));
    float threshold = 0.40 + smoothstep(0.45, 0.97, phase) * 0.26;
    float holes = smoothstep(threshold - 0.04, threshold + 0.06, noise);
    float lip = 1.0 - smoothstep(aa, aa + 0.030, abs(behind));
    float remnant = (1.0 - smoothstep(0.05, 0.22, abs(offset - 0.48)))
        * smoothstep(0.55, 0.68, phase) * (1.0 - smoothstep(0.68, 0.98, phase))
        * smoothstep(0.52, 0.70, noise) * 0.45;
    float foam = max(lip * (0.40 + envelope * 0.45), band * holes * envelope);
    return vec2(max(foam, remnant), wet);
}
