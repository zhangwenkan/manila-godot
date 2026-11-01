shader_type spatial;
render_mode unshaded, cull_back;

// The geometry carries linear paint colours. Lighting uses each real normal,
// not a fixed face vector, so it continues to read correctly during rotation.
uniform vec3 light_direction = vec3(-0.45, 0.85, 0.55);
uniform bool matte = false;
uniform float shadow_floor : hint_range(0.0, 1.0) = 0.70;
uniform float band_softness : hint_range(0.01, 0.3) = 0.10;
varying vec3 world_normal;

void vertex() {
	world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
}

void fragment() {
	float incidence = dot(normalize(world_normal), normalize(light_direction));
	float mid_band = smoothstep(-0.12 - band_softness, -0.12 + band_softness, incidence);
	float lit_band = smoothstep(0.48 - band_softness, 0.48 + band_softness, incidence);
	float brightness = mix(shadow_floor, 0.91, mid_band);
	brightness = mix(brightness, 1.12, lit_band);
	vec3 shadow_tint = vec3(0.92, 0.95, 1.02);
	vec3 light_tint = vec3(1.025, 1.01, 0.97);
	vec3 tint = mix(shadow_tint, light_tint, mid_band * 0.65 + lit_band * 0.35);
	if (matte) {
		brightness = mix(0.68, 1.02, smoothstep(-0.25, 0.85, incidence));
		tint = vec3(1.0);
	}
	ALBEDO = COLOR.rgb * brightness * tint;
	ROUGHNESS = 0.88;
	SPECULAR = 0.12;
}
