shader_type canvas_item;
render_mode unshaded;

// The layout is geometry data only. All water colors and marks below are generated.
uniform sampler2D layout_map : filter_nearest, repeat_disable;
uniform vec2 ocean_size = vec2(6144.0, 1152.0);
uniform bool use_layout = true;
uniform float ocean_time = 0.0;

group_uniforms Pixel_Waves;
uniform float pixel_size : hint_range(1.0, 6.0, 1.0) = 2.0;
uniform float animation_fps : hint_range(1.0, 30.0, 1.0) = 12.0;
uniform float flow_speed : hint_range(0.0, 20.0, 0.5) = 5.0;
uniform float ripple_density : hint_range(0.0, 1.0, 0.01) = 0.42;
uniform float ripple_strength : hint_range(0.0, 1.0, 0.01) = 0.95;
uniform float grain_strength : hint_range(0.0, 0.04, 0.001) = 0.009;

group_uniforms Depth_and_Shore;
uniform float deep_start : hint_range(0.0, 2048.0, 1.0) = 1064.0;
uniform float deep_transition : hint_range(12.0, 256.0, 1.0) = 60.0;
uniform float foam_strength : hint_range(0.0, 1.0, 0.01) = 0.72;
uniform float shadow_strength : hint_range(0.0, 1.0, 0.01) = 0.78;

group_uniforms Palette;
uniform vec4 harbor_color : source_color = vec4(0.3451, 0.5529, 0.6824, 1.0);
uniform vec4 sea_color : source_color = vec4(0.3020, 0.5529, 0.7098, 1.0);
uniform vec4 deep_harbor_color : source_color = vec4(0.2980, 0.4588, 0.5686, 1.0);
uniform vec4 deep_sea_color : source_color = vec4(0.2471, 0.4627, 0.6039, 1.0);
uniform vec4 shallow_color : source_color = vec4(0.4902, 0.6431, 0.6745, 1.0);
uniform vec4 ripple_color : source_color = vec4(0.5255, 0.7843, 0.8196, 1.0);
uniform vec4 foam_color : source_color = vec4(0.7529, 0.7922, 0.7176, 1.0);
group_uniforms;

varying vec2 surface_position;

float hash21(vec2 p) {
	// Small multipliers retain fractional precision across the 6144 px world.
	vec3 p3 = fract(vec3(p.x, p.y, p.x) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

float value_noise(vec2 p) {
	vec2 cell = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash21(cell), hash21(cell + vec2(1.0, 0.0)), f.x),
		mix(hash21(cell + vec2(0.0, 1.0)), hash21(cell + vec2(1.0, 1.0)), f.x), f.y);
}

// A staggered, sparse distribution of short horizontal strokes, with occasional
// broken companion strokes. The grid moves in water space, never screen space.
float short_ripples(vec2 p, float t) {
	vec2 cell_size = vec2(104.0, 54.0);
	vec2 moving = p + vec2(t * flow_speed, 0.0);
	float row = floor(moving.y / cell_size.y);
	moving.x += hash21(vec2(row, 13.0)) * cell_size.x;
	vec2 cell = floor(moving / cell_size);
	vec2 local = mod(moving, cell_size);
	float pick = hash21(cell + vec2(7.3, 31.7));
	float density_pick = hash21(cell + vec2(91.7, 17.1));
	vec2 center = vec2(16.0 + hash21(cell) * 68.0,
		10.0 + hash21(cell + 71.0) * 34.0);
	float wave_phase = t * 0.72 + pick * 6.283185;
	center.y += floor(sin(wave_phase) * 1.5) * pixel_size;
	center = floor(center / pixel_size) * pixel_size;
	float length_px = floor(mix(4.0, 22.0, pick) / pixel_size) * pixel_size;
	float line = step(abs(local.x - center.x), length_px * 0.5)
		* (1.0 - step(pixel_size, abs(local.y - center.y)));
	float broken = step(0.68, pick) * step(abs(local.x - center.x + length_px * 0.5 + 6.0), 1.0)
		* (1.0 - step(pixel_size, abs(local.y - center.y)));
	float visibility = 0.85 + 0.15 * smoothstep(-0.75, 0.8, sin(wave_phase));
	return max(line, broken) * step(density_pick, ripple_density) * visibility;
}

void vertex() {
	surface_position = VERTEX;
}

void fragment() {
	vec4 layout = vec4(1.0, 1.0, 1.0, 0.0);
	if (use_layout) {
		layout = texture(layout_map, surface_position / ocean_size);
	}
	if (layout.r < 0.01) {
		discard;
	}
	vec2 p = floor(surface_position / pixel_size) * pixel_size;
	float t = floor(ocean_time * animation_fps) / animation_fps;
	float east = smoothstep(0.0, ocean_size.x, p.x);
	vec3 base = mix(harbor_color.rgb, sea_color.rgb, east);
	base += vec3(0.010, 0.004, 0.015) * sin(east * 3.141593);
	vec3 deep = mix(deep_harbor_color.rgb, deep_sea_color.rgb, east);
	float edge_distance = layout.g * 128.0;
	float beach_distance = layout.b * 192.0;

	// Quiet, broad water color variation with a fine stationary paper-like grain.
	float broad = value_noise(p / vec2(240.0, 110.0));
	float detail = value_noise(p / vec2(52.0, 28.0));
	base += (broad - 0.5) * 0.018 + (detail - 0.5) * 0.010;
	float grain = (hash21(p + 0.37) - 0.5) * grain_strength;
	base += grain;
	deep += grain * 0.8 + (broad - 0.5) * 0.006;

	// A shallow sandy shelf becomes blue gradually, in broken horizontal washes.
	float tide = sin(t * 0.65) * 3.0;
	float wash_noise = value_noise((p + vec2(t * 2.0, 0.0)) / vec2(64.0, 9.0));
	float shallows = 1.0 - smoothstep(0.0, 110.0, beach_distance + (wash_noise - 0.5) * 25.0 + tide);
	vec3 water = mix(base, shallow_color.rgb, shallows * 0.67);

	// The reference's deep-water boundary consists of narrow, interlocking pixel
	// bars. Thresholding stretched noise preserves their stepped silhouettes.
	vec2 bands = vec2((p.x + t * flow_speed * 0.7) / 40.0, floor(p.y / 6.0) * 37.0);
	float band_noise = value_noise(bands) * 0.94
		+ value_noise(p / vec2(12.0, 3.0) + 53.0) * 0.06;
	band_noise = smoothstep(0.18, 0.82, band_noise);
	float depth = clamp((p.y - deep_start + sin(t * 0.47) * 3.0) / deep_transition, 0.0, 1.0);
	float deep_mask = step(band_noise, depth) * step(deep_start, p.y);
	water = mix(water, deep, deep_mask);

	// Contact darkening and pixel reflections at stone walls and wooden posts.
	float row_noise = value_noise(vec2((p.x + t * 2.0) / 34.0, floor(p.y / 4.0) * 19.0));
	float shadow_coverage = 0.0;
	if (use_layout) {
		vec2 reflection_position = p + vec2(floor((row_noise - 0.5) * 8.0) * pixel_size, 0.0);
		shadow_coverage = texture(layout_map, reflection_position / ocean_size).a;
	}
	float reflection = step(0.22 + row_noise * 0.54, shadow_coverage);
	reflection *= 1.0 - step(0.76, row_noise) * 0.65;
	water = mix(water, deep * vec3(0.86, 0.91, 0.98), reflection * shadow_strength);
	float contact = (1.0 - smoothstep(0.0, 5.0, edge_distance))
		* smoothstep(5.0, 24.0, beach_distance);
	water = mix(water, ripple_color.rgb, contact * 0.36 * step(0.36, row_noise));

	float ripple = short_ripples(p, t) * ripple_strength
		* smoothstep(8.0, 30.0, edge_distance)
		* (1.0 - smoothstep(deep_start - 12.0, deep_start + 8.0, p.y));
	water = mix(water, ripple_color.rgb, ripple);

	// Several incomplete foam ribbons follow real shore distance, not a flat
	// horizontal sine wave. Their short stepped fragments drift towards the sand.
	float foam_offset = (wash_noise - 0.5) * 7.0;
	float distance = beach_distance + foam_offset + tide;
	float shore_lip = (1.0 - smoothstep(1.5, 6.0, distance));
	float ribbon_phase = mod(distance + t * 3.0, 23.0);
	float ribbon = (1.0 - step(4.5, ribbon_phase)) * step(0.57, row_noise)
		* (1.0 - smoothstep(12.0, 82.0, beach_distance));
	float flecks = step(0.55, row_noise) * (1.0 - smoothstep(4.0, 85.0, beach_distance));
	float foam = max(shore_lip, max(ribbon * 0.75, flecks * 0.50)) * foam_strength;
	water = mix(water, foam_color.rgb, foam);
	COLOR = vec4(water, layout.r);
}
