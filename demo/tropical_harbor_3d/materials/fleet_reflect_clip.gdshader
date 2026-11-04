shader_type spatial;
render_mode cull_back, shadows_disabled, depth_draw_opaque;

uniform vec4 albedo_tint : source_color = vec4(1.0);
uniform float clip_y = 0.03;
varying vec3 world_pos;
varying vec3 vcolor;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vcolor = COLOR.rgb;
}

void fragment() {
	if (world_pos.y < clip_y) {
		discard;
	}
	float wet = 1.0 - smoothstep(clip_y, clip_y + 0.14, world_pos.y);
	ALBEDO = vcolor * albedo_tint.rgb * mix(1.0, 0.78, wet);
	ROUGHNESS = 0.68;
	SPECULAR = 0.26;
	METALLIC = 0.0;
}
