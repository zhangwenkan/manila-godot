extends "res://demo/tropical_harbor_3d/environment/harbor_environment.gd"

const REFERENCE_WATER = preload("res://demo/tropical_harbor_3d/materials/reference_water.gdshader")
const REFERENCE_GROUND = preload("res://demo/tropical_harbor_3d/materials/reference_ground.gdshader")
const ART := "res://demo/tropical_harbor_3d/assets/reference/"

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
    sand_material.set_shader_parameter("detail_noise", NOISE)
    for item in instance.find_children("*", "MeshInstance3D", true, false):
        var mesh := item as MeshInstance3D
        mesh.material_override = sand_material
        mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
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
    if d < 0:
        return .13 * d - .013 * d * d / (1.0 - d * .025)
    return minf(d * .23, .8) + smoothstep(2.8, 5, d) * .48 + smoothstep(9, 13, d) * 1.55 + .10 * sin(z * .29) * smoothstep(2, 5, d) + .18 * sin(z * .14 + d * .45) * smoothstep(6, 13, d)
