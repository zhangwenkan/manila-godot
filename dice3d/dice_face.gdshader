shader_type spatial;
render_mode unshaded, cull_back;

uniform sampler2D face_mask : filter_nearest, repeat_disable;
uniform vec3 face_normal = vec3(0.0, 1.0, 0.0);
uniform vec4 top_color : source_color = vec4(0.75, 0.85, 0.71, 1.0);
uniform vec4 base_color : source_color = vec4(0.60, 0.76, 0.61, 1.0);
uniform vec4 side_color : source_color = vec4(0.47, 0.64, 0.49, 1.0);
uniform vec4 separator_color : source_color = vec4(0.82, 0.91, 0.78, 1.0);
uniform vec4 dot_color : source_color = vec4(0.26, 0.34, 0.76, 1.0);

varying vec3 world_face_normal;

void vertex() {
	world_face_normal = MODEL_NORMAL_MATRIX * face_normal;
}

void fragment() {
	vec2 masks = texture(face_mask, UV).rg;
	float shade = dot(normalize(world_face_normal), normalize(vec3(-0.45, 0.90, 0.20)));
	vec3 face_color = mix(side_color.rgb, base_color.rgb, smoothstep(-0.20, 0.35, shade));
	face_color = mix(face_color, top_color.rgb, smoothstep(0.50, 0.85, shade));
	vec3 pip_color = dot_color.rgb * mix(0.83, 1.08, clamp(shade * 0.5 + 0.5, 0.0, 1.0));
	ALBEDO = mix(mix(separator_color.rgb, face_color, masks.r), pip_color, masks.g);
}
