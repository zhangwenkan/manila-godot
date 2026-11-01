shader_type spatial;
render_mode cull_back, ambient_light_disabled;

uniform sampler2D grain : source_color, filter_nearest, repeat_enable;
uniform bool use_grain = false;
uniform vec4 top_color : source_color = vec4(0.8, 0.85, 0.7, 1.0);
uniform vec4 base_color : source_color = vec4(0.6, 0.7, 0.55, 1.0);
uniform vec4 side_color : source_color = vec4(0.3, 0.45, 0.35, 1.0);
uniform vec3 face_axis = vec3(0.0);
uniform vec2 grain_scale = vec2(1.0);
varying vec3 world_normal;

void vertex() {
	vec3 authored_normal = length(face_axis) > 0.5 ? normalize(mix(NORMAL, face_axis, 0.72)) : NORMAL;
	world_normal = MODEL_NORMAL_MATRIX * authored_normal;
}

void fragment() {
	float shade = dot(normalize(world_normal), normalize(vec3(-0.45, 0.90, 0.20)));
	vec3 color = mix(side_color.rgb, base_color.rgb, smoothstep(-0.20, 0.35, shade));
	color = mix(color, top_color.rgb, smoothstep(0.50, 0.85, shade));
	if (use_grain) {
		color *= texture(grain, UV * grain_scale).rgb;
	}
	ALBEDO = color;
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
}

void light() {
	// Preserve the authored face palette, but let the pieces cast actual shadows.
	DIFFUSE_LIGHT += vec3(mix(0.50, 1.0, ATTENUATION));
}
