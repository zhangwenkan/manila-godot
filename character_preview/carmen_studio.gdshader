shader_type sky;
render_mode use_debanding;

// Reflection-only studio; the SubViewport background remains transparent.
float softbox(vec3 ray, vec3 center, vec2 extent, float softness) {
	vec3 forward = normalize(center);
	vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), forward));
	vec3 up = cross(forward, right);
	float facing = dot(ray, forward);
	vec2 plane = vec2(dot(ray, right), dot(ray, up)) / max(facing, 0.001);
	vec2 mask = vec2(1.0) - smoothstep(extent, extent + vec2(softness), abs(plane));
	return mask.x * mask.y * step(0.0, facing);
}

void sky() {
	vec3 ray = normalize(EYEDIR);
	float ceiling = smoothstep(-0.55, 0.8, ray.y);
	vec3 studio = mix(vec3(0.025), vec3(0.16), ceiling);
	float key = softbox(ray, vec3(-0.72, 0.48, 0.72), vec2(0.22, 0.85), 0.10);
	float strip = softbox(ray, vec3(0.85, 0.12, 0.52), vec2(0.07, 1.1), 0.045);
	float overhead = softbox(ray, vec3(0.08, 0.95, 0.30), vec2(0.85, 0.15), 0.08);
	float fill = softbox(ray, vec3(0.18, -0.35, 0.92), vec2(0.45, 0.28), 0.18);
	// Steep edge normals reflect behind the card, unlike its nearly flat lip.
	float left_return = softbox(ray, vec3(-0.70, 0.10, -0.71), vec2(0.14, 0.95), 0.07);
	float right_return = softbox(ray, vec3(0.70, -0.10, -0.71), vec2(0.09, 0.95), 0.05);
	float top_return = softbox(ray, vec3(0.0, 0.68, -0.74), vec2(0.85, 0.12), 0.07);
	COLOR = studio + vec3(key * 3.8 + strip * 5.0 + overhead * 3.0 + fill * 0.65
		+ left_return * 3.2 + right_return * 4.0 + top_return * 2.4);
}
