extends "res://demo/tropical_harbor_3d/environment/harbor_environment.gd"

const REFERENCE_WATER = preload("res://demo/tropical_harbor_3d/materials/reference_water.gdshader")
const REFERENCE_GROUND = preload("res://demo/tropical_harbor_3d/materials/landform_mass.gdshader")
const ART := "res://demo/tropical_harbor_3d/assets/reference/"
const RELIEF_HEIGHT_PATH := ART + "shore_relief_height.json"
const GRASS_ALBEDO = preload(ART + "L24_Grass.png")
const SOIL_ALBEDO = preload(ART + "L24_Earth.png")
const PATH_ALBEDO = preload(ART + "L24_Path.png")
const ROCK_ALBEDO = preload(ART + "L24_Rock.png")

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

func _build_sand() -> void:
    var instance := (load(ART + "terrain.glb") as PackedScene).instantiate() as Node3D
    instance.name = "ReferenceGround"
    add_child(instance)
    sand_material = ShaderMaterial.new()
    sand_material.shader = REFERENCE_GROUND
    sand_material.set_shader_parameter("grass_albedo", GRASS_ALBEDO)
    sand_material.set_shader_parameter("soil_albedo", SOIL_ALBEDO)
    sand_material.set_shader_parameter("path_albedo", PATH_ALBEDO)
    sand_material.set_shader_parameter("rock_albedo", ROCK_ALBEDO)
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
