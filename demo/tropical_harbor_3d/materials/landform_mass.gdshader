shader_type spatial;

uniform sampler2D grass_albedo : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D soil_albedo : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D path_albedo : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D rock_albedo : source_color, repeat_enable, filter_linear_mipmap_anisotropic;

varying vec3 world_position;
varying vec3 world_normal;
varying vec4 land_use;

void vertex() {
    world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
    world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
    // Authored weights: grass, rock, path, soil. Unassigned weight is beach.
    land_use = COLOR;
}

vec3 surface_color(sampler2D source, vec3 position, vec3 projection, float tile_size) {
    vec3 p = position / tile_size;
    return texture(source, p.zy).rgb * projection.x
        + texture(source, p.xz).rgb * projection.y
        + texture(source, p.xy).rgb * projection.z;
}

void fragment() {
    vec3 projection = pow(abs(normalize(world_normal)), vec3(4.0));
    projection /= max(dot(projection, vec3(1.0)), 0.0001);

    vec3 grass = surface_color(grass_albedo, world_position, projection, 2.4);
    vec3 rock = surface_color(rock_albedo, world_position, projection, 3.2);
    vec3 path = surface_color(path_albedo, world_position, projection, 4.8);
    vec3 soil = surface_color(soil_albedo, world_position, projection, 2.8);
    vec3 beach = vec3(0.66, 0.50, 0.285);

    vec4 weights = max(land_use, vec4(0.0));
    float assigned = dot(weights, vec4(1.0));
    float beach_weight = max(0.0, 1.0 - assigned);
    // Sharpen all authored roles equally, including the residual beach weight.
    weights = pow(weights, vec4(4.0));
    beach_weight = pow(beach_weight, 4.0);
    float total = max(dot(weights, vec4(1.0)) + beach_weight, 0.0001);
    ALBEDO = (grass * weights.r + rock * weights.g + path * weights.b
        + soil * weights.a + beach * beach_weight) / total;
    ROUGHNESS = 0.94;
    SPECULAR = 0.10;
}
