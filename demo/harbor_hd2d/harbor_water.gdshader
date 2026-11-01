shader_type spatial;
render_mode cull_disabled;

uniform vec3 deep_color : source_color = vec3(0.24, 0.49, 0.66);
uniform vec3 shoal_color : source_color = vec3(0.18, 0.74, 0.75);
uniform vec3 glint_color : source_color = vec3(0.74, 0.93, 0.89);
varying vec3 world_position;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = floor(world_position.xz * 10.0) / 10.0;
	float t = floor(TIME * 8.0) / 8.0;
	float side = p.x < 0.0 ? -1.0 : 1.0;
	float shore_x = 10.9 + sin(p.y * 0.30 + side * 0.6) * 1.05 + sin(p.y * 0.67) * 0.35;
	float distance_to_shore = shore_x - abs(p.x);
	float shallows = 1.0 - smoothstep(0.0, 3.0, distance_to_shore);
	float patches = floor((sin(p.x * 0.38 + p.y * 0.20) + sin(p.y * 0.61)) * 3.0) / 3.0;
	vec3 water = mix(deep_color, shoal_color, shallows * 0.86) + patches * 0.012;
	vec2 cell = floor(vec2(p.x * 0.58 + t * 0.08, p.y * 2.0));
	float ripple = step(0.92, hash(cell)) * step(0.80, sin(p.y * 18.0 + t * 0.55));
	float coast = (1.0 - smoothstep(0.08, 0.22, abs(distance_to_shore - 0.27 - sin(p.y * 3.0 + t) * 0.07)));
	float coast2 = (1.0 - smoothstep(0.02, 0.10, abs(distance_to_shore - 0.60))) * step(0.0, sin(p.y * 4.4));
	water = mix(water, glint_color, clamp(ripple * 0.37 + coast * 0.92 + coast2 * 0.43, 0.0, 1.0));
	ALBEDO = water;
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
	NORMAL = normalize(mat3(VIEW_MATRIX) * vec3(0.01 * sin(p.x + t), 1.0, 0.015 * cos(p.y + t)));
}
