shader_type spatial;
render_mode cull_disabled, depth_draw_never;

uniform sampler2D detail_noise : repeat_enable, filter_linear_mipmap_anisotropic;
varying vec3 wp;

void vertex() {
    wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
    float n = texture(detail_noise, wp.xz * .38).r;
    float fine = texture(detail_noise, wp.xz * 6.0).r;
    float edge = min(min(UV.x, 1.0 - UV.x), min(UV.y, 1.0 - UV.y));
    float broad = texture(detail_noise, wp.xz * .095).r;
    ALBEDO = mix(vec3(.32, .185, .062), vec3(.44, .285, .105), broad) * (.97 + .05 * n + .015 * fine);
    ROUGHNESS = .94;
    SPECULAR = .12;
    ALPHA = smoothstep(.005, .13, edge + (n - .5) * .045);
}
