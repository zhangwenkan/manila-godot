shader_type canvas_item;
render_mode unshaded;

uniform float flow_speed = 0.18;
uniform float pixel_size = 2.0;
uniform float base_distortion = 3.0;
uniform float vertical_ratio = 0.55;
uniform float harbor_strength = 0.35;
uniform float sparkle_strength = 0.12;
uniform float sparkle_threshold = 0.82;
uniform vec2 uv_world_origin = vec2(0.0, 0.0);

float hash21(vec2 p) {
	p = fract(p * vec2(123.34, 456.21));
	p += dot(p, p + 45.32);
	return fract(p.x * p.y);
}

void fragment() {
	vec2 world_uv = UV - uv_world_origin;
	vec2 world_px = floor(world_uv / TEXTURE_PIXEL_SIZE / pixel_size);
	float t = TIME * flow_speed;

	float harbor_mask = 1.0 - smoothstep(360.0, 520.0, world_uv.x);
	float open_water_mask = 1.0 - harbor_mask * (1.0 - harbor_strength);

	float patch_a = sin(world_px.x * 0.018 + world_px.y * 0.011 + t * 1.4);
	float patch_b = sin(world_px.x * -0.013 + world_px.y * 0.017 - t * 1.1);
	float patch_c = sin((world_px.x + world_px.y) * 0.010 + t * 1.7);
	float patch_mix = patch_a * 0.45 + patch_b * 0.35 + patch_c * 0.20;

	float drift_x = sin(world_px.y * 0.015 + patch_mix * 2.2 + t * 1.5);
	float drift_y = sin(world_px.x * 0.012 - patch_mix * 1.8 - t * 1.3);
	vec2 offset_px = vec2(drift_x, drift_y * vertical_ratio) * base_distortion * open_water_mask;
	vec2 snapped = floor(offset_px / pixel_size + 0.5) * pixel_size;
	vec2 sample_uv = UV + snapped * TEXTURE_PIXEL_SIZE;
	vec4 color = texture(TEXTURE, sample_uv);

	float sparkle_band = smoothstep(0.35, 0.75, patch_mix);
	vec2 sparkle_cell = floor(world_px * vec2(0.10, 0.14) + vec2(t * 0.35, -t * 0.22));
	float sparkle = step(sparkle_threshold, hash21(sparkle_cell)) * sparkle_band * open_water_mask;
	color.rgb += vec3(sparkle * sparkle_strength);

	COLOR = color;
}
