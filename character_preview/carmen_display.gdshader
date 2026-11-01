shader_type spatial;
render_mode unshaded, cull_back;

uniform sampler2D portrait : source_color, filter_linear_mipmap;
uniform float sheen = 0.0;

void fragment() {
	vec3 art = texture(portrait, UV).rgb;
	vec3 surface_normal = normalize(NORMAL);
	float diagonal = UV.x + UV.y * 0.38 + surface_normal.x * 0.45 + surface_normal.y * 0.15;
	float reflection = smoothstep(0.06, 0.15, diagonal) * (1.0 - smoothstep(0.19, 0.31, diagonal));
	float edge = pow(abs(UV.x - 0.5) * 2.0, 24.0);
	ALBEDO = art + vec3(0.84, 0.86, 0.90) * (reflection * 0.04 + edge * 0.02) * sheen;
	ROUGHNESS = 0.42;
}
