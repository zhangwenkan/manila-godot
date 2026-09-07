shader_type spatial;
render_mode cull_disabled, ambient_light_disabled;

uniform sampler2D surface_texture : source_color, filter_nearest, repeat_enable;
uniform vec4 tint : source_color = vec4(1.0);

void fragment() {
	ALBEDO = texture(surface_texture, UV).rgb * tint.rgb * COLOR.rgb;
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
}

void light() {
	DIFFUSE_LIGHT += vec3(mix(0.52, 1.0, ATTENUATION));
}
