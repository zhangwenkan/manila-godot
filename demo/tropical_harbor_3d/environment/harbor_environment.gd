extends RefCounted

const WATER_SHADER = preload("res://demo/tropical_harbor_3d/materials/tropical_water.gdshader")
const SAND_SHADER = preload("res://demo/tropical_harbor_3d/materials/sand.gdshader")
const NOISE = preload("res://demo/tropical_harbor_3d/assets/water_noise.png")
const SWASH_SHADER = preload("res://demo/tropical_harbor_3d/materials/shore_swash.gdshader")
const COAST_SHAPE := Vector4(8.0, 2.0, 0.6, 0.0)
const BAY_SHAPE := Vector4(-2.5, 3.6, 2.2, 0.85)
const WASH_PERIOD := 4.8

var root: Node3D
var water_shader: Shader = WATER_SHADER
var water_material: ShaderMaterial
var sand_material: ShaderMaterial
var swash_material: ShaderMaterial
var contact_objects := PackedVector4Array()
var sea: MeshInstance3D
var swash: MeshInstance3D
var time := 0.0


func _init(parent: Node3D) -> void:
    root = parent


func add_child(node: Node) -> void:
    root.add_child(node)


func sync_time(value: float) -> void:
    time = value
    for material in [water_material, sand_material, swash_material]:
        material.set_shader_parameter("study_time", time)


func set_contacts(objects: PackedVector4Array, capacity: int = 10) -> void:
    if objects.size() > capacity:
        push_error("Water contact capacity exceeded")
        return
    water_material.set_shader_parameter("contact_count", objects.size())
    var padded := objects.duplicate()
    padded.resize(capacity)
    water_material.set_shader_parameter("contact_objects", padded)


func _mat(hex: String, roughness: float = 0.85) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = Color(hex)
    material.roughness = roughness
    return material


func _build_environment() -> void:
    var environment := Environment.new()
    environment.background_mode = Environment.BG_SKY
    environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
    environment.ambient_light_energy = 0.42
    environment.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
    var sky := Sky.new()
    var sky_mat := ProceduralSkyMaterial.new()
    sky_mat.sky_top_color = Color("829faa")
    sky_mat.sky_horizon_color = Color("cad8d3")
    sky_mat.ground_bottom_color = Color("668c8b")
    sky_mat.ground_horizon_color = Color("bdccc4")
    sky.sky_material = sky_mat
    environment.sky = sky
    environment.tonemap_mode = Environment.TONE_MAPPER_ACES
    environment.tonemap_exposure = 1.0
    environment.ssao_enabled = true
    environment.ssao_radius = 1.25
    environment.ssao_intensity = 1.3
    environment.ssao_light_affect = 0.1
    environment.glow_enabled = false
    environment.volumetric_fog_enabled = false
    environment.sdfgi_enabled = false
    var world_environment := WorldEnvironment.new()
    world_environment.environment = environment
    add_child(world_environment)
    var sun := DirectionalLight3D.new()
    sun.name = "WarmAfternoon"
    sun.rotation_degrees = Vector3(-48, -145, 0)
    sun.light_color = Color("fff0d6")
    sun.light_energy = 1.05
    sun.light_angular_distance = 0.85
    sun.shadow_enabled = true
    sun.directional_shadow_max_distance = 100.0
    sun.shadow_bias = 0.04
    sun.shadow_normal_bias = 0.6
    add_child(sun)
    RenderingServer.directional_shadow_atlas_set_size(4096, true)
    RenderingServer.directional_soft_shadow_filter_set_quality(RenderingServer.SHADOW_QUALITY_SOFT_HIGH)


func _build_water() -> void:
    var mesh := PlaneMesh.new()
    mesh.size = Vector2(180, 180)
    mesh.subdivide_width = 260
    mesh.subdivide_depth = 260
    water_material = ShaderMaterial.new()
    water_material.shader = water_shader
    _configure_shore_material(water_material)
    sea = MeshInstance3D.new()
    sea.name = "Ocean"
    sea.mesh = mesh
    sea.material_override = water_material
    sea.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    add_child(sea)


func _configure_shore_material(material: ShaderMaterial) -> void:
    material.set_shader_parameter("water_noise", NOISE)
    material.set_shader_parameter("coast_shape", COAST_SHAPE)
    material.set_shader_parameter("bay_shape", BAY_SHAPE)
    material.set_shader_parameter("wash_period", WASH_PERIOD)
    material.set_shader_parameter("study_time", time)


func _shore(z: float) -> float:
    var bay := (z - BAY_SHAPE.x) / BAY_SHAPE.y
    var point := (z - BAY_SHAPE.x - 5.0) / (BAY_SHAPE.y * 0.65)
    return COAST_SHAPE.x + sin(z * 0.14) * COAST_SHAPE.y + sin(z * 0.37 + 0.4) * COAST_SHAPE.z + BAY_SHAPE.z * exp(-bay * bay) - BAY_SHAPE.w * exp(-point * point)


func wave_height(x: float, z: float, t: float) -> float:
    var dist := maxf(_shore(z) - x, 0.0)
    var amount := smoothstep(1.0, 5.0, dist)
    return (sin(x * 0.66 + z * 0.43 + t * 0.72) * 0.025
        + sin(z * 1.15 - x * 0.28 + t * 0.93) * 0.016) * amount


func _sand_height(offset: float, z: float) -> float:
    if offset < 0.0:
        var d := -offset
        return -0.11 * d - 0.013 * d * d / (1.0 + d * 0.025)
    return minf(offset * 0.20, 0.7) + smoothstep(2.0, 14.0, offset) * (0.2 + sin(z * 0.21) * 0.16)


func _build_sand() -> void:
    var vertices := PackedVector3Array()
    var colors := PackedColorArray()
    var indices := PackedInt32Array()
    var offsets := PackedFloat32Array([-160.0, -110.0, -80.0, -55.0, -38.0, -28.0, -22.0, -18.0])
    for i in range(173):
        offsets.append(-16.0 + i * 0.25)
    offsets.append_array(PackedFloat32Array([32.0, 45.0, 75.0, 110.0]))
    var width := offsets.size() - 1
    var length := 320
    for iz in range(length + 1):
        var z := -100.0 + iz * 200.0 / length
        for ix in range(width + 1):
            var offset := offsets[ix]
            vertices.append(Vector3(_shore(z) + offset, _sand_height(offset, z), z))
            var tint := Color("a39c80").lerp(Color("b3aa89"), smoothstep(-1.0, 3.0, offset))
            colors.append(tint.srgb_to_linear())
    for iz in range(length):
        for ix in range(width):
            var a := iz * (width + 1) + ix
            var b := a + width + 1
            indices.append_array(PackedInt32Array([a, a + 1, b, a + 1, b + 1, b]))
    var surface := SurfaceTool.new()
    surface.begin(Mesh.PRIMITIVE_TRIANGLES)
    for i in vertices.size():
        surface.set_color(colors[i])
        surface.add_vertex(vertices[i])
    for i in indices:
        surface.add_index(i)
    surface.generate_normals()
    var land := MeshInstance3D.new()
    land.name = "CurvedSandBank"
    land.mesh = surface.commit()
    sand_material = ShaderMaterial.new()
    sand_material.shader = SAND_SHADER
    _configure_shore_material(sand_material)
    land.material_override = sand_material
    add_child(land)


func _build_swash() -> void:
    var surface := SurfaceTool.new()
    surface.begin(Mesh.PRIMITIVE_TRIANGLES)
    var width := 36
    var length := 800
    for iz in range(length + 1):
        var z := -100.0 + iz * 200.0 / length
        for ix in range(width + 1):
            var offset := -1.8 + ix * 3.0 / width
            surface.add_vertex(Vector3(_shore(z) + offset, maxf(0.0, _sand_height(offset, z)) + 0.012, z))
    for iz in range(length):
        for ix in range(width):
            var a := iz * (width + 1) + ix
            var b := a + width + 1
            for index in [a, a + 1, b, a + 1, b + 1, b]:
                surface.add_index(index)
    surface.generate_normals()
    swash_material = ShaderMaterial.new()
    swash_material.shader = SWASH_SHADER
    swash_material.render_priority = 1
    _configure_shore_material(swash_material)
    swash = MeshInstance3D.new()
    swash.name = "ShallowSwashFilm"
    swash.layers = 2
    swash.mesh = surface.commit()
    swash.material_override = swash_material
    swash.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    add_child(swash)


func _build_contact_stones() -> void:
    var material := _mat("89988e")
    var stones := [
        Vector4(_shore(-2.5) - 0.65, -2.5, 0.90, 0.30),
        Vector4(_shore(0.4) - 2.0, 0.4, 0.48, 0.12),
        Vector4(_shore(-6.0) - 4.1, -6.0, 0.85, -0.88),
        Vector4(_shore(4.2) - 5.4, 4.2, 1.0, -1.32)
    ]
    for i in stones.size():
        var spec: Vector4 = stones[i]
        var mesh := SphereMesh.new()
        mesh.radius = 1.0
        mesh.height = 2.0
        mesh.radial_segments = 10
        mesh.rings = 5
        var rock := MeshInstance3D.new()
        rock.name = "ContactStone%d" % i
        rock.mesh = mesh
        rock.material_override = material
        rock.position = Vector3(spec.x, spec.w, spec.y)
        rock.scale = Vector3(spec.z, spec.z * 0.7, spec.z * 0.82)
        rock.rotation.y = i * 0.73
        add_child(rock)
        if spec.w >= 0.0:
            contact_objects.append(Vector4(spec.x, spec.y, spec.z, 1.0))


