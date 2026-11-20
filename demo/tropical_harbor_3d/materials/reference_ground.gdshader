shader_type spatial;
render_mode cull_disabled;

uniform sampler2D detail_noise : repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D bank_albedo : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
varying vec3 wp;
varying float bank_weight;

float bank(float z) {
    float t = clamp((z + 18.7) / (-26.0 + 18.7), 0.0, 1.0);
    return 7.8 + 1.45 * sin(z * .12) + .48 * sin(z * .29) - 21.0 * t * t * (3.0 - 2.0 * t);
}

void vertex() {
    wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
    bank_weight = COLOR.r;
}

void fragment() {
    float d = wp.x - bank(wp.z);
    float n = texture(detail_noise, wp.xz * .38).r;
    float broad = texture(detail_noise, wp.xz * .095).r;
    float fine = texture(detail_noise, wp.xz * 6.0).r;
    vec3 sand = mix(vec3(.56, .40, .20), vec3(.69, .52, .28), broad);
    vec3 earth = mix(vec3(.32, .185, .062), vec3(.44, .285, .105), broad);
    float wet = 1.0 - smoothstep(.015, .23, wp.y + (broad - .5) * .065);
    sand = mix(sand, vec3(.34, .255, .15), wet * .55);
    // The physical soil bank shares vertices with the walking surface. Its
    // authored weight blends across the shoulder without per-face saw teeth.
    float inland = smoothstep(1.05, 1.55, d + (n - .5) * .20) * smoothstep(.05, .32, wp.y);
    vec3 bare = mix(sand, earth, inland) * (.97 + .05 * n + .015 * fine);
    vec3 soil = texture(bank_albedo, vec2(wp.z * .62, wp.y * .75)).rgb;
    ALBEDO = mix(bare, soil, smoothstep(.06, .90, bank_weight));
    ROUGHNESS = .94;
    SPECULAR = .12;
}
