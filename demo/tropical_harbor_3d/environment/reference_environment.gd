extends "res://demo/tropical_harbor_3d/environment/harbor_environment.gd"

const REFERENCE_WATER = preload("res://demo/tropical_harbor_3d/materials/reference_water.gdshader")
const REFERENCE_GROUND = preload("res://demo/tropical_harbor_3d/materials/landform_mass.gdshader")
const ART := "res://demo/tropical_harbor_3d/assets/reference/"
const RELIEF_HEIGHT_PATH := ART + "shore_relief_height.json"
const GRASS_ALBEDO = preload(ART + "L24_Grass.png")
const SOIL_ALBEDO = preload(ART + "R27_Earth_Albedo.png")
const SOIL_HEIGHT = preload(ART + "R27_Earth_Height.png")
const PATH_ALBEDO = preload(ART + "L24_Path.png")
const ROCK_ALBEDO = preload(ART + "R27_Rock_Albedo.png")
const ROCK_HEIGHT = preload(ART + "R27_Rock_Height.png")
const GROUND_SURFACE_TEXTURES := {
    "ground_land_use": ART + "G23_LandUse.png",
    "ground_grass": ART + "G23_Grass.png",
    "ground_rock": ART + "G23_Rock.png",
    "ground_path": ART + "G23_Path.png",
    "ground_soil": ART + "G23_Soil.png",
    "ground_sand": ART + "G23_Sand.png",
}
const CLIFF_REGION_TEXTURES := {
    "cliff_region_color": ART + "C25_CliffRegion_Color.png",
    "cliff_region_height": ART + "C25_CliffRegion_Height.exr",
}
const GROUND_DETAIL_TEXTURE := ART + "C25_GroundDetail.png"

var _relief_height_loaded := false
var _relief_heights := PackedFloat32Array()
var _relief_columns := 0
var _relief_rows := 0
var _relief_step := .25
var _relief_d0 := 0.0
var _relief_z0 := 0.0

func _build_environment() -> void:
    super._build_environment()
    var world := root.get_world_3d().environment
    world.ambient_light_color = Color("bdcfda")
    world.ambient_light_energy = 0.52
    world.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    world.tonemap_exposure = 0.82
    world.ssao_radius = 0.55
    world.ssao_intensity = 0.75
    var sun := root.get_node("WarmAfternoon") as DirectionalLight3D
    sun.rotation_degrees = Vector3(-51, -42, 0)
    sun.light_color = Color("fff1d3")
    sun.light_energy = 1.15
    # Filtered hard shadows keep small cabin eaves clean; PCSS produced
    # stippled self-shadows along their thin lips at the normal game scale.
    sun.light_angular_distance = 0.0

func _build_water() -> void:
    var instance := (load(ART + "ocean.glb") as PackedScene).instantiate() as Node3D
    instance.name = "ReferenceOcean"
    add_child(instance)
    sea = instance.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D
    water_material = ShaderMaterial.new()
    water_material.shader = REFERENCE_WATER
    water_material.set_shader_parameter("water_noise", NOISE)
    sea.material_override = water_material
    sea.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    # The final island composition exposes water beyond the original north edge.
    # Reuse the authored ocean tile at its exact border, with the same material.
    var far_ocean := (load(ART + "ocean.glb") as PackedScene).instantiate() as Node3D
    far_ocean.name = "ReferenceFarOcean"
    far_ocean.position.z = -193.5
    add_child(far_ocean)
    for item in far_ocean.find_children("*", "MeshInstance3D", true, false):
        var far_mesh := item as MeshInstance3D
        far_mesh.material_override = water_material
        far_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

func _build_sand() -> void:
    var instance := (load(ART + "terrain.glb") as PackedScene).instantiate() as Node3D
    instance.name = "ReferenceGround"
    add_child(instance)
    sand_material = ShaderMaterial.new()
    sand_material.shader = REFERENCE_GROUND
    sand_material.set_shader_parameter("grass_albedo", GRASS_ALBEDO)
    sand_material.set_shader_parameter("soil_albedo", SOIL_ALBEDO)
    sand_material.set_shader_parameter("soil_height", SOIL_HEIGHT)
    sand_material.set_shader_parameter("path_albedo", PATH_ALBEDO)
    sand_material.set_shader_parameter("rock_albedo", ROCK_ALBEDO)
    sand_material.set_shader_parameter("rock_height", ROCK_HEIGHT)
    _bind_ground_surfaces(sand_material)
    _bind_cliff_region(sand_material)
    _bind_ground_detail(sand_material)
    for item in instance.find_children("*", "MeshInstance3D", true, false):
        var mesh := item as MeshInstance3D
        # Authored grass, rock, path and soil weights share the same landform.
        for surface in mesh.mesh.get_surface_count():
            var material := mesh.get_active_material(surface) as BaseMaterial3D
            if material == null:
                continue
            material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
            if material.resource_name == "Ref_L24_Landform":
                mesh.set_surface_override_material(surface, sand_material)
        mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
        var body := StaticBody3D.new()
        body.collision_layer = 4
        body.collision_mask = 0
        mesh.add_child(body)
        var collision := CollisionShape3D.new()
        collision.shape = mesh.mesh.create_trimesh_shape()
        body.add_child(collision)
    # Compatibility fields for the shared time/presentation interface.
    if ResourceLoader.exists(ART + "ground_cover.glb"):
        var ground_cover := (load(ART + "ground_cover.glb") as PackedScene).instantiate() as Node3D
        ground_cover.name = "ReferenceGroundCover"
        add_child(ground_cover)
        for item in ground_cover.find_children("*", "MeshInstance3D", true, false):
            var cover_mesh := item as MeshInstance3D
            for surface in cover_mesh.mesh.get_surface_count():
                var cover_material := StandardMaterial3D.new()
                cover_material.vertex_color_use_as_albedo = true
                cover_material.vertex_color_is_srgb = false
                cover_material.roughness = 0.94
                cover_material.metallic_specular = 0.10
                cover_material.cull_mode = BaseMaterial3D.CULL_DISABLED
                cover_mesh.set_surface_override_material(surface, cover_material)
    # Exposed shoulders now belong to the continuous terrain. The intermediate
    # ground_rock asset is archived and deliberately has no runtime instance.

func _bind_ground_surfaces(material: ShaderMaterial) -> void:
    # Enable the complete set together: no old regional rock style remains inside
    # the new land-use map, and the same five surfaces continue beyond its bounds.
    var textures: Dictionary = {}
    for parameter in GROUND_SURFACE_TEXTURES:
        var path: String = GROUND_SURFACE_TEXTURES[parameter]
        if not ResourceLoader.exists(path):
            return
        var texture := load(path) as Texture2D
        if texture == null:
            return
        textures[parameter] = texture
    for parameter in textures:
        material.set_shader_parameter(parameter, textures[parameter])
    material.set_shader_parameter("ground_surface_enabled", true)

func _bind_cliff_region(material: ShaderMaterial) -> void:
    # This optional local pair never replaces the global land-use or surface set.
    # Keep the flag off if either color or linear float height is unavailable.
    material.set_shader_parameter("cliff_region_enabled", false)
    var textures: Dictionary = {}
    for parameter in CLIFF_REGION_TEXTURES:
        var path: String = CLIFF_REGION_TEXTURES[parameter]
        if not ResourceLoader.exists(path):
            return
        var texture := load(path) as Texture2D
        if texture == null:
            return
        textures[parameter] = texture
    for parameter in textures:
        material.set_shader_parameter(parameter, textures[parameter])
    material.set_shader_parameter("cliff_region_enabled", true)

func _bind_ground_detail(material: ShaderMaterial) -> void:
    material.set_shader_parameter("ground_detail_enabled", false)
    if not ResourceLoader.exists(GROUND_DETAIL_TEXTURE):
        return
    var texture := load(GROUND_DETAIL_TEXTURE) as Texture2D
    if texture == null:
        return
    material.set_shader_parameter("ground_detail_map", texture)
    material.set_shader_parameter("ground_detail_enabled", true)

func _build_swash() -> void:
    swash_material = ShaderMaterial.new()

func _build_contact_stones() -> void:
    pass

func sync_time(value: float) -> void:
    time = value
    water_material.set_shader_parameter("study_time", time)

func _shore(z: float) -> float:
    return 7.8 + 1.45 * sin(z * .12) + .48 * sin(z * .29) - 21.0 * smoothstep(-18.7, -26.0, z)

func _sand_height(d: float, z: float) -> float:
    _load_relief_height()
    if _relief_heights.is_empty():
        return _outside_landscape_height(d, z)
    var column := (d - _relief_d0) / _relief_step
    var row := (z - _relief_z0) / _relief_step
    if column < 0.0:
        return _outside_landscape_height(d, z)
    # The authored distant land is extended flat beyond the sampled perimeter.
    column = clampf(column, 0.0, _relief_columns - 1)
    row = clampf(row, 0.0, _relief_rows - 1)
    var x0 := mini(int(floor(column)), _relief_columns - 2)
    var z0 := mini(int(floor(row)), _relief_rows - 2)
    var tx := column - x0
    var tz := row - z0
    var first := z0 * _relief_columns + x0
    var next := first + _relief_columns
    return lerpf(lerpf(_relief_heights[first], _relief_heights[first + 1], tx),
        lerpf(_relief_heights[next], _relief_heights[next + 1], tx), tz)

func _load_relief_height() -> void:
    if _relief_height_loaded:
        return
    _relief_height_loaded = true
    if not FileAccess.file_exists(RELIEF_HEIGHT_PATH):
        return
    var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(RELIEF_HEIGHT_PATH))
    if not parsed is Dictionary:
        return
    var data: Dictionary = parsed
    var samples: Variant = data.get("heights", [])
    var columns := int(data.get("columns", 0))
    var rows := int(data.get("rows", 0))
    var step := float(data.get("step", 0.0))
    if not samples is Array or columns < 2 or rows < 2 or step <= 0.0 or not is_finite(step):
        return
    if samples.size() != columns * rows:
        return
    var heights := PackedFloat32Array()
    heights.resize(samples.size())
    for i in samples.size():
        if not (samples[i] is float or samples[i] is int):
            return
        var value := float(samples[i])
        if not is_finite(value):
            return
        heights[i] = value
    _relief_d0 = float(data.get("d0", 0.0))
    _relief_z0 = float(data.get("z0", 0.0))
    _relief_columns = columns
    _relief_rows = rows
    _relief_step = step
    _relief_heights = heights

func _outside_landscape_height(d: float, _z: float) -> float:
    # Deep sea beyond the authored height atlas; the visible landscape uses samples.
    if d < 0.0:
        return .13 * d - .013 * d * d / (1.0 - d * .025)
    return minf(d * .18, .4)
