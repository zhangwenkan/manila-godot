shader_type spatial;
render_mode cull_disabled;
uniform sampler2D water_noise : repeat_enable, filter_linear_mipmap;
varying vec3 world_position;
varying vec3 vertex_tint;
void vertex() {
    world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
    vertex_tint = COLOR.rgb;
}
void fragment() {
    float broad = texture(water_noise, world_position.xz * 0.045).r;
    float grain = texture(water_noise, world_position.xz * 3.5).b;
    ALBEDO = vertex_tint * (0.93 + broad * 0.13 + grain * 0.035);
    ROUGHNESS = 0.92;
    SPECULAR = 0.18;
}
