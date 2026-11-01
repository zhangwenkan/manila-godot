shader_type spatial;
render_mode cull_disabled;

uniform sampler2D atlas_texture : source_color, filter_nearest, repeat_disable;
uniform int tile_index : hint_range(0, 15) = 0;
uniform vec4 tint : source_color = vec4(1.0);

void fragment() {
	// Actual mesh UVs repeat inside a padded cell, preserving world texture density.
	int tile = clamp(tile_index, 0, 15);
	vec2 cell = vec2(float(tile % 4), floor(float(tile) / 4.0));
	vec2 interior = clamp(vec2(2.0) + fract(UV) * 60.0, vec2(2.5), vec2(61.5));
	vec4 color = texture(atlas_texture, (cell * 64.0 + interior) / 256.0) * tint;
	ALBEDO = color.rgb;
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
}
