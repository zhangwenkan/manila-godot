shader_type canvas_item;

uniform vec3 light_key : source_color = vec3(0.95, 0.95, 0.95);
uniform float light_threshold = 0.22;

void fragment() {
	vec4 color = texture(TEXTURE, UV);
	float light_distance = distance(color.rgb, light_key);
	if (light_distance < light_threshold) {
		discard;
	}
	COLOR = color;
}
