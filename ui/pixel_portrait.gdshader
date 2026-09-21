shader_type canvas_item;
render_mode unshaded;

uniform vec4 source_region = vec4(0.0, 0.0, 1.0, 1.0);
uniform float pixel_grid = 42.0;
uniform vec2 draw_size = vec2(106.0);
uniform float portrait_diameter = 84.0;
uniform bool has_portrait = false;
uniform vec4 background_color : source_color = vec4(0.718, 0.604, 0.435, 1.0);
uniform vec4 outline_color : source_color;
uniform vec4 rim_color : source_color;
uniform vec4 wood_color : source_color;
uniform vec4 shadow_color : source_color;

float disc_coverage(float radius, float distance_from_center, float aa) {
	return 1.0 - smoothstep(radius - aa, radius + aa, distance_from_center);
}

void fragment() {
	vec2 position = (UV - vec2(0.5)) * draw_size;
	float radius = portrait_diameter * 0.5;
	float distance_from_center = length(position);
	float aa = max(fwidth(distance_from_center) * 0.5, 0.001);

	// Quantize the artwork only. All circular edges share continuous coordinates.
	vec2 portrait_uv = position / portrait_diameter + vec2(0.5);
	vec2 pixel_uv = (floor(portrait_uv * pixel_grid) + 0.5) / pixel_grid;
	pixel_uv = clamp(pixel_uv, vec2(0.5 / pixel_grid), vec2(1.0 - 0.5 / pixel_grid));
	vec3 interior = background_color.rgb;
	if (has_portrait) {
		vec4 portrait = texture(TEXTURE, source_region.xy + pixel_uv * source_region.zw);
		interior = mix(interior, portrait.rgb, portrait.a);
	}

	// Composite the opaque interior and concentric rim before applying outer alpha.
	vec3 frame = outline_color.rgb;
	frame = mix(frame, rim_color.rgb, disc_coverage(radius + 4.0, distance_from_center, aa));
	frame = mix(frame, wood_color.rgb, disc_coverage(radius + 2.0, distance_from_center, aa));
	frame = mix(frame, outline_color.rgb, disc_coverage(radius + 1.0, distance_from_center, aa));
	frame = mix(frame, interior, disc_coverage(radius, distance_from_center, aa));
	float frame_alpha = disc_coverage(radius + 6.0, distance_from_center, aa);
	float shadow_distance = length(position - vec2(0.0, 3.0));
	float shadow_aa = max(fwidth(shadow_distance) * 0.5, 0.001);
	float shadow_alpha = shadow_color.a * disc_coverage(radius + 7.0, shadow_distance, shadow_aa);
	float alpha = frame_alpha + shadow_alpha * (1.0 - frame_alpha);
	vec3 color = (frame * frame_alpha + shadow_color.rgb * shadow_alpha * (1.0 - frame_alpha)) / max(alpha, 0.0001);
	COLOR = vec4(color, alpha);
}
