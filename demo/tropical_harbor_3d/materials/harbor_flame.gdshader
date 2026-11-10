shader_type spatial;
render_mode unshaded, cull_disabled;

uniform float live_time = 0.0;
instance uniform float flame_phase = 0.0;

void vertex() {
    float tip = clamp(UV.y, 0.0, 1.0);
    float flicker = sin(live_time * 9.3 + flame_phase) * 0.09 + sin(live_time * 15.7 + flame_phase * 2.0) * 0.035;
    VERTEX.y *= 1.0 + flicker;
    VERTEX.x += tip * tip * (0.006 * sin(live_time * 7.1 + flame_phase) + 0.003 * sin(live_time * 13.0));
    VERTEX.z += tip * tip * 0.0035 * sin(live_time * 8.7 + flame_phase);
}

void fragment() {
    float flicker = 1.0 + 0.10 * sin(live_time * 9.3 + flame_phase) + 0.045 * sin(live_time * 15.7 + flame_phase * 2.0);
    vec3 fire = mix(vec3(1.0, 0.77, 0.25), vec3(1.0, 0.18, 0.015), smoothstep(0.28, 1.0, UV.y));
    ALBEDO = fire;
    EMISSION = fire * flicker * 2.5;
}
