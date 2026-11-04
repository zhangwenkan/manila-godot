shader_type spatial;
render_mode blend_mul, unshaded, shadows_disabled, depth_draw_never, cull_disabled;

varying float world_y;

void vertex() {
	world_y = (MODEL_MATRIX * vec4(VERTEX, 1.0)).y;
}

void fragment() {
	float wet = 1.0 - smoothstep(-0.01, 0.045, world_y);
	float band = 1.0 - smoothstep(0.0, 0.022, abs(world_y - 0.008));
	vec3 mul = mix(vec3(1.0), vec3(0.52, 0.47, 0.42), wet);
	mul *= mix(vec3(1.0), vec3(0.76, 0.74, 0.70), band);
	ALBEDO = mul;
	ALPHA = 1.0;
}
