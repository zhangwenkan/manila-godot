shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_disabled, ambient_light_disabled;

void fragment() {
	ALBEDO = vec3(0.0);
	SPECULAR = 0.0;
	ALPHA = 0.0;
}

void light() {
	ALPHA = max(ALPHA, (1.0 - ATTENUATION) * 0.28);
	DIFFUSE_LIGHT = vec3(0.0);
	SPECULAR_LIGHT = vec3(0.0);
}
