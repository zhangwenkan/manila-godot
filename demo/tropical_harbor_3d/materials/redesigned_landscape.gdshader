shader_type spatial;

uniform sampler2D grass_albedo : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D soil_albedo : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D path_albedo : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D grass_normal : hint_normal, repeat_enable, filter_linear_mipmap_anisotropic;
varying vec3 world_position;
varying vec3 land_use;

void vertex() {
    world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
    land_use = COLOR.rgb;
}

void fragment() {
    vec2 ground_uv = world_position.xz / 2.4;
    vec3 grass = texture(grass_albedo, ground_uv).rgb;
    vec3 earth = texture(soil_albedo, vec2(world_position.z * .22, world_position.y * .36)).rgb;
    vec3 path = texture(path_albedo, ground_uv * .48).rgb;
    vec3 sand = vec3(.66, .50, .285);
    float wet = 1.0 - smoothstep(.01, .25, world_position.y);
    sand *= mix(1.0, .70, wet);
    // Normalize the authored material weights. Sequential mixes introduced
    // a false pale sand halo at the grass/earth boundary.
    vec3 weights = max(vec3(0.0), land_use);
    float beach = 1.0 - smoothstep(.02, .50, weights.r + weights.g + weights.b);
    float total = max(.001, weights.r + weights.g + weights.b + beach);
    ALBEDO = (grass * weights.r + earth * weights.g + path * weights.b + sand * beach) / total;
    NORMAL_MAP = mix(vec3(.5, .5, 1.0), texture(grass_normal, ground_uv).rgb, weights.r);
    NORMAL_MAP_DEPTH = .35;
    ROUGHNESS = .96;
    SPECULAR = .10;
}
