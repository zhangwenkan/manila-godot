shader_type spatial;

uniform sampler2D grass_albedo : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D soil_albedo : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D path_albedo : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D rock_albedo : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D soil_height : repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D rock_height : repeat_enable, filter_linear_mipmap_anisotropic;
uniform float soil_bump_strength = 0.018;
uniform float rock_bump_strength = 0.12;
uniform bool ground_surface_enabled = false;
// Land use is linear RGBA data. The surface maps carry sRGB color in RGB and
// linear height in alpha; source_color decodes RGB without changing alpha.
uniform sampler2D ground_land_use : repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D ground_grass : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D ground_rock : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D ground_path : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D ground_soil : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D ground_sand : source_color, repeat_enable, filter_linear_mipmap_anisotropic;

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

vec3 surface_heights(sampler2D source, vec3 position, float tile_size) {
    vec3 p = position / tile_size;
    return vec3(texture(source, p.zy).r, texture(source, p.xz).r,
        texture(source, p.xy).r);
}

vec3 surface_color_height(sampler2D source, vec3 position, vec3 projection,
        float tile_size, out vec3 height_samples) {
    vec3 p = position / tile_size;
    vec4 sample_x = texture(source, p.zy);
    vec4 sample_y = texture(source, p.xz);
    vec4 sample_z = texture(source, p.xy);
    // Keep the three heights separate until after differentiation, so changes
    // in projection weights cannot invent bumps at rounded terrain corners.
    height_samples = vec3(sample_x.a, sample_y.a, sample_z.a);
    return sample_x.rgb * projection.x + sample_y.rgb * projection.y
        + sample_z.rgb * projection.z;
}

void fragment() {
    vec3 base_normal = normalize(world_normal);
    vec3 projection = pow(abs(base_normal), vec3(4.0));
    projection /= max(dot(projection, vec3(1.0)), 0.0001);

    vec3 grass;
    vec3 rock;
    vec3 path;
    vec3 soil;
    vec3 beach;
    vec3 grass_samples = vec3(0.5);
    vec3 rock_samples;
    vec3 path_samples = vec3(0.5);
    vec3 soil_samples;
    vec3 beach_samples = vec3(0.5);
    vec4 height_ranges = vec4(0.0, rock_bump_strength, 0.0, soil_bump_strength);
    float beach_height_range = 0.0;
    if (ground_surface_enabled) {
        grass = surface_color_height(ground_grass, world_position, projection, 5.0, grass_samples);
        rock = surface_color_height(ground_rock, world_position, projection, 8.0, rock_samples);
        path = surface_color_height(ground_path, world_position, projection, 4.0, path_samples);
        soil = surface_color_height(ground_soil, world_position, projection, 4.0, soil_samples);
        beach = surface_color_height(ground_sand, world_position, projection, 6.0, beach_samples);
        height_ranges = vec4(0.040, 0.24, 0.012, 0.050);
        beach_height_range = 0.012;
    } else {
        // Compatibility fallback is used only while the complete G23 set is absent.
        grass = surface_color(grass_albedo, world_position, projection, 2.4);
        rock = surface_color(rock_albedo, world_position, projection, 3.2);
        path = surface_color(path_albedo, world_position, projection, 4.8);
        soil = surface_color(soil_albedo, world_position, projection, 2.8);
        beach = vec3(0.66, 0.50, 0.285);
        rock_samples = surface_heights(rock_height, world_position, 3.2);
        soil_samples = surface_heights(soil_height, world_position, 2.8);
    }

    vec4 weights = max(land_use, vec4(0.0));
    // Keep grass on the crown of the older coast where its sparse mesh blends
    // a grass vertex down a steep rock face. Authored soil slopes are unaffected.
    float steep_rock = (1.0 - smoothstep(0.58, 0.85, base_normal.y))
        * smoothstep(0.01, 0.20, weights.g);
    float crown_grass = weights.r * steep_rock;
    weights.r -= crown_grass;
    weights.g += crown_grass;
    if (ground_surface_enabled) {
        vec2 land_min = vec2(-4.0, -15.0);
        vec2 land_max = vec2(44.0, 82.0);
        vec2 edge_distance = min(world_position.xz - land_min, land_max - world_position.xz);
        float map_mix = smoothstep(0.0, 1.0, min(edge_distance.x, edge_distance.y));
        vec2 land_uv = (world_position.xz - land_min) / (land_max - land_min);
        // The PNG's first row is the northern edge; world Z grows from its bottom.
        land_uv.y = 1.0 - land_uv.y;
        weights = mix(weights, max(texture(ground_land_use, land_uv), vec4(0.0)), map_mix);
    }
    float assigned = dot(weights, vec4(1.0));
    float beach_weight = max(0.0, 1.0 - assigned);
    weights /= max(assigned, 1.0);
    vec4 material_heights = vec4(dot(grass_samples, projection), dot(rock_samples, projection),
        dot(path_samples, projection), dot(soil_samples, projection));
    float beach_height = dot(beach_samples, projection);
    if (ground_surface_enabled) {
        // Disturb only mixed grass margins. Solid grass areas retain their authored
        // shape, and the remaining materials keep their relative proportions.
        float grass_edge = smoothstep(0.05, 0.30, weights.r)
            * (1.0 - smoothstep(0.70, 0.95, weights.r));
        float grass_weight = clamp(weights.r + (material_heights.r - 0.5) * 0.38 * grass_edge, 0.0, 1.0);
        float other_scale = (1.0 - grass_weight) / max(1.0 - weights.r, 0.0001);
        weights.gba *= other_scale;
        beach_weight *= other_scale;
        weights.r = grass_weight;
        // Limit contact to competing materials near the leading weight. This
        // keeps soil, sand and exposed rock from forming wide translucent bands.
        float leading_weight = max(max(weights.r, weights.g), max(weights.b, weights.a));
        leading_weight = max(leading_weight, beach_weight);
        weights = smoothstep(vec4(0.0), vec4(0.28), max(weights - vec4(leading_weight - 0.28), vec4(0.0)));
        beach_weight = smoothstep(0.0, 0.28, max(beach_weight - (leading_weight - 0.28), 0.0));
    } else {
        weights = pow(weights, vec4(2.0));
        beach_weight = pow(beach_weight, 2.0);
    }
    float total = max(dot(weights, vec4(1.0)) + beach_weight, 0.0001);
    weights /= total;
    beach_weight /= total;
    ALBEDO = grass * weights.r + rock * weights.g + path * weights.b
        + soil * weights.a + beach * beach_weight;

    // Differentiate each texture's height before any projection or land-use blend.
    // Neither a material border nor its grass-edge variation creates a raised seam.
    vec4 height_dx = vec4(dot(dFdx(grass_samples), projection), dot(dFdx(rock_samples), projection),
        dot(dFdx(path_samples), projection), dot(dFdx(soil_samples), projection));
    vec4 height_dy = vec4(dot(dFdy(grass_samples), projection), dot(dFdy(rock_samples), projection),
        dot(dFdy(path_samples), projection), dot(dFdy(soil_samples), projection));
    float surface_dx = dot(height_dx * height_ranges, weights)
        + dot(dFdx(beach_samples), projection) * beach_height_range * beach_weight;
    float surface_dy = dot(height_dy * height_ranges, weights)
        + dot(dFdy(beach_samples), projection) * beach_height_range * beach_weight;
    vec3 position_dx = dFdx(world_position);
    vec3 position_dy = dFdy(world_position);
    vec3 tangent_x = cross(position_dy, base_normal);
    vec3 tangent_y = cross(base_normal, position_dx);
    float determinant = dot(position_dx, tangent_x);
    float inverse_det = sign(determinant) / max(abs(determinant), 0.0000000001);
    vec3 height_gradient = (tangent_x * surface_dx + tangent_y * surface_dy) * inverse_det;
    // Heights are metres; this changes light response, never terrain or silhouette.
    vec3 bumped_normal = normalize(base_normal - height_gradient);
    NORMAL = normalize((VIEW_MATRIX * vec4(bumped_normal, 0.0)).xyz);
    ROUGHNESS = 0.94;
    if (ground_surface_enabled) {
        vec4 roughness = vec4(0.96, 0.87, 0.92, 0.97)
            + (material_heights - vec4(0.5)) * vec4(0.03, 0.055, 0.025, 0.025);
        float beach_roughness = 0.91 + (beach_height - 0.5) * 0.03;
        float mineral_contact = clamp(4.0 * (beach_weight * (weights.g + weights.a)
            + weights.g * weights.a), 0.0, 1.0);
        ALBEDO *= 1.0 - mineral_contact * 0.025;
        ROUGHNESS = clamp(dot(roughness, weights) + beach_roughness * beach_weight
            + mineral_contact * 0.012, 0.0, 1.0);
    }
    SPECULAR = 0.10;
}
