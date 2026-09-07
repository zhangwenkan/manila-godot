shader_type canvas_item;

uniform sampler2D screen_texture : hint_screen_texture, repeat_disable, filter_linear_mipmap;
uniform float blur_amount : hint_range(0.0, 15.0) = 8.0;
uniform vec4 tint : source_color = vec4(0.02, 0.02, 0.08, 0.55);

void fragment() {
	vec2 ps = SCREEN_PIXEL_SIZE * blur_amount;

	vec4 color = textureLod(screen_texture, SCREEN_UV, 2.5) * 4.0;
	color += textureLod(screen_texture, SCREEN_UV + vec2(ps.x, 0.0), 2.5);
	color += textureLod(screen_texture, SCREEN_UV + vec2(-ps.x, 0.0), 2.5);
	color += textureLod(screen_texture, SCREEN_UV + vec2(0.0, ps.y), 2.5);
	color += textureLod(screen_texture, SCREEN_UV + vec2(0.0, -ps.y), 2.5);
	color += textureLod(screen_texture, SCREEN_UV + vec2(ps.x * 0.7, ps.y * 0.7), 2.5);
	color += textureLod(screen_texture, SCREEN_UV + vec2(-ps.x * 0.7, ps.y * 0.7), 2.5);
	color += textureLod(screen_texture, SCREEN_UV + vec2(ps.x * 0.7, -ps.y * 0.7), 2.5);
	color += textureLod(screen_texture, SCREEN_UV + vec2(-ps.x * 0.7, -ps.y * 0.7), 2.5);
	color /= 12.0;

	COLOR = mix(color, tint, tint.a);
	COLOR.a = 1.0;
}
