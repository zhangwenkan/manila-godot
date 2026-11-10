shader_type spatial;
render_mode cull_disabled;

uniform sampler2D cloth_albedo : source_color, filter_linear_mipmap_anisotropic;
uniform sampler2D cloth_normal : hint_normal, filter_linear_mipmap_anisotropic;
uniform sampler2D cloth_roughness : filter_linear_mipmap_anisotropic;
uniform vec3 plain_color : source_color = vec3(0.23, 0.18, 0.11);
uniform bool textured = true;
uniform float live_time = 0.0;
uniform float wind_amount = 1.0;
varying float face_side;

void vertex() {
    // Blender-authored weights keep every suspension tab attached to its rod.
    float w = pow(COLOR.r, 1.35);
    float phase = COLOR.g * 5.7;
    float gust = 0.66 + 0.22 * sin(live_time * 0.81) + 0.12 * sin(live_time * 1.37 + 1.1);
    float wave = sin(live_time * 3.2 - COLOR.r * 5.4 + VERTEX.x * 1.8 + phase);
    float ripple = sin(live_time * 6.8 - COLOR.r * 9.0 + phase) * 0.018;
    float amount = wind_amount * COLOR.b;
    VERTEX.z += amount * w * (0.16 + gust * 0.13 * wave + ripple);
    VERTEX.x += amount * w * (0.055 + 0.038 * sin(live_time * 2.1 + phase - COLOR.r * 3.0));
    VERTEX.y += amount * w * (0.055 + 0.035 * wave);
}

void fragment() {
    ALBEDO = textured ? texture(cloth_albedo, UV).rgb : plain_color;
    ROUGHNESS = textured ? texture(cloth_roughness, UV).g : 0.86;
    SPECULAR = 0.18;
    if (textured) {
        NORMAL_MAP = texture(cloth_normal, UV).rgb;
        NORMAL_MAP_DEPTH = 0.5;
    }
}
