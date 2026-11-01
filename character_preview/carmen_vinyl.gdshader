shader_type spatial;
render_mode unshaded, cull_back;

uniform vec3 light_direction = vec3(-0.45, 0.85, 0.55);
varying vec3 world_normal;

void vertex() {
	world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
}

void fragment() {
	vec3 n = normalize(world_normal);
	float diffuse = smoothstep(-0.32, 0.85, dot(n, normalize(light_direction)));
	float softbox = pow(max(dot(n, normalize(vec3(-0.35, 0.65, 0.95))), 0.0), 22.0);
	float rim = pow(1.0 - max(dot(normalize(NORMAL), normalize(VIEW)), 0.0), 3.5);
	vec3 paint = COLOR.rgb * mix(0.64, 1.06, diffuse);
	// Neutral softbox highlights distinguish the display figure from matte tokens.
	ALBEDO = paint + vec3(1.0, 0.97, 0.94) * softbox * 0.13
		+ vec3(0.72, 0.74, 0.78) * rim * 0.03;
	ROUGHNESS = 0.34;
	SPECULAR = 0.38;
}
