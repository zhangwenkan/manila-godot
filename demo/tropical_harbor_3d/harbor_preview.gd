extends Node3D

const WATER_SHADER = preload("res://materials/tropical_water.gdshader")
const SAND_SHADER = preload("res://materials/sand.gdshader")
const NOISE = preload("res://assets/water_noise.png")
const SWASH_SHADER = preload("res://materials/shore_swash.gdshader")
const COAST_SHAPE := Vector4(8.0, 2.0, 0.6, 0.0)
const BAY_SHAPE := Vector4(-2.5, 3.6, 2.2, 0.85)
const WASH_PERIOD := 4.8

var water_material: ShaderMaterial
var sand_material: ShaderMaterial
var swash_material: ShaderMaterial
var contact_objects := PackedVector4Array()
var camera_override := false
var sea: MeshInstance3D
var swash: MeshInstance3D
var camera: Camera3D
var boat: Node3D
var ui: CanvasLayer
var time := 0.0
var playing := true
var close_view := false
var sailing := true
var wake := 0.0
var camera_mix := 0.0
var pause_button: Button
var view_button: Button
var sail_button: Button
var reset_button: Button
var capture_mode := false
var demo_mode := false
var _capture_started := 0
var _samples: Array[float] = []
var _sampling := false
var _last_sample_usec := 0


func _ready() -> void:
    _build_environment()
    _build_water()
    _build_sand()
    _build_swash()
    _build_context()
    _build_contact_stones()
    water_material.set_shader_parameter("contact_count", contact_objects.size())
    contact_objects.resize(10)
    water_material.set_shader_parameter("contact_objects", contact_objects)
    _build_boat()
    _build_camera()
    _build_ui()
    for arg in OS.get_cmdline_user_args():
        if arg == "--capture":
            capture_mode = true
        elif arg == "--demo":
            demo_mode = true
    if capture_mode or demo_mode:
        _capture_started = Time.get_ticks_msec()
        if capture_mode:
            _run_capture.call_deferred()
        else:
            _run_demo.call_deferred()


func _build_environment() -> void:
    var environment := Environment.new()
    environment.background_mode = Environment.BG_COLOR
    environment.background_color = Color("a8c2c3")
    environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    environment.ambient_light_color = Color("d1dfda")
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
    environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    environment.tonemap_exposure = 1.0
    environment.ssao_enabled = true
    environment.ssao_radius = 1.25
    environment.ssao_intensity = 1.3
    environment.ssao_light_affect = 0.1
    environment.glow_enabled = false
    var world_environment := WorldEnvironment.new()
    world_environment.environment = environment
    add_child(world_environment)
    var sun := DirectionalLight3D.new()
    sun.name = "WarmAfternoon"
    sun.rotation_degrees = Vector3(-48, -145, 0)
    sun.light_color = Color("fff0d6")
    sun.light_energy = 1.05
    sun.light_angular_distance = 1.6
    sun.shadow_enabled = true
    sun.directional_shadow_max_distance = 100.0
    sun.shadow_bias = 0.04
    sun.shadow_normal_bias = 1.0
    add_child(sun)


func _build_water() -> void:
    var mesh := PlaneMesh.new()
    mesh.size = Vector2(180, 180)
    mesh.subdivide_width = 260
    mesh.subdivide_depth = 260
    water_material = ShaderMaterial.new()
    water_material.shader = WATER_SHADER
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


func _mat(hex: String, roughness: float = 0.85) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = Color(hex)
    material.roughness = roughness
    return material


func _box(parent: Node3D, label: String, position_: Vector3, size_: Vector3, material: Material) -> MeshInstance3D:
    var mesh := BoxMesh.new()
    mesh.size = size_
    var instance := MeshInstance3D.new()
    instance.name = label
    instance.mesh = mesh
    instance.position = position_
    instance.material_override = material
    parent.add_child(instance)
    return instance


func _cylinder(parent: Node3D, position_: Vector3, radius: float, height: float, material: Material) -> MeshInstance3D:
    var mesh := CylinderMesh.new()
    mesh.top_radius = radius * 0.92
    mesh.bottom_radius = radius
    mesh.height = height
    mesh.radial_segments = 10
    var instance := MeshInstance3D.new()
    instance.mesh = mesh
    instance.material_override = material
    instance.position = position_
    parent.add_child(instance)
    return instance


func _build_context() -> void:
    var rng := RandomNumberGenerator.new()
    rng.seed = 4421
    var wood := [_mat("a97139"), _mat("b88143"), _mat("bd8b4c"), _mat("c49558")]
    var dark_wood := _mat("755037")
    var cap_wood := _mat("cea56c")
    var pier := Node3D.new()
    pier.name = "WaterContactStudyPier"
    add_child(pier)
    for i in 17:
        var plank := _box(pier, "Timber", Vector3(3.3 + i * 0.43, 0.69 + rng.randf_range(-0.018, 0.018), 7.3), Vector3(0.405, 0.17, 2.25 + rng.randf_range(-0.09, 0.09)), wood[i % 4])
        plank.rotation.z = rng.randf_range(-0.01, 0.01)
    for z in [6.42, 8.18]:
        _box(pier, "CrossBeam", Vector3(6.7, 0.46, z), Vector3(7.9, 0.24, 0.22), dark_wood)
        for x in [3.5, 6.25, 9.3]:
            var post_bottom := minf(_sand_height(x - _shore(z), z) - 0.15, -0.80)
            var post := _cylinder(pier, Vector3(x, (post_bottom + 1.345) * 0.5, z), 0.15, 1.345 - post_bottom, dark_wood)
            contact_objects.append(Vector4(x, z, 0.18, 0.50))
            post.rotation.z = rng.randf_range(-0.025, 0.025)
            _cylinder(pier, Vector3(x, 1.37, z), 0.175, 0.07, cap_wood)
            for band in 3:
                _cylinder(pier, Vector3(x, 1.11 + band * 0.045, z), 0.162, 0.025, _mat("c4a66d"))
    var stone_colors := [_mat("989c8c"), _mat("b2b29b"), _mat("c0ba9e")]
    for cluster in [Vector3(10.5, 0, -10.5), Vector3(12.5, 0, 12.8)]:
        for i in 5:
            var rock := MeshInstance3D.new()
            var sphere := SphereMesh.new()
            sphere.radial_segments = 8
            sphere.rings = 4
            sphere.radius = 1.0
            sphere.height = 2.0
            rock.mesh = sphere
            rock.material_override = stone_colors[i % 3]
            rock.position = cluster + Vector3(rng.randf_range(-1.6, 1.6), 0.15 + i * 0.025, rng.randf_range(-1.9, 1.9))
            rock.scale = Vector3(rng.randf_range(0.65, 1.65), rng.randf_range(0.45, 1.2), rng.randf_range(0.6, 1.2))
            rock.rotation = Vector3(rng.randf_range(-0.2, 0.2), rng.randf_range(0, TAU), 0)
            add_child(rock)
    for i in 17:
        var z := rng.randf_range(-16, 17)
        var offset := rng.randf_range(1.0, 4.5)
        var pebble := MeshInstance3D.new()
        var sphere := SphereMesh.new()
        sphere.radial_segments = 6
        sphere.rings = 3
        pebble.mesh = sphere
        pebble.material_override = stone_colors[i % 3]
        pebble.position = Vector3(_shore(z) + offset, _sand_height(offset, z) + 0.03, z)
        pebble.scale = Vector3(0.15, 0.09, 0.22) * rng.randf_range(0.7, 1.8)
        add_child(pebble)


func _build_boat() -> void:
    boat = Node3D.new()
    boat.name = "WaterTestBoat"
    add_child(boat)
    if ResourceLoader.exists("res://assets/test_boat.glb"):
        var packed := load("res://assets/test_boat.glb") as PackedScene
        boat.add_child(packed.instantiate())
    else:
        _box(boat, "TemporaryHull", Vector3(0, 0.18, 0), Vector3(1.6, 0.55, 4.4), _mat("903e31"))
        _box(boat, "Deck", Vector3(0, 0.49, 0), Vector3(1.4, 0.12, 4.1), _mat("ba8745"))
    boat.position = Vector3(-4.5, 0, 2)


func _build_camera() -> void:
    camera = Camera3D.new()
    camera.name = "StudyCamera"
    camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    camera.size = 25.0
    camera.near = 0.2
    camera.far = 250.0
    add_child(camera)
    camera.make_current()
    _update_camera(0)


func _update_camera(delta: float) -> void:
    if camera_override:
        return
    camera_mix = move_toward(camera_mix, 1.0 if close_view else 0.0, delta * 1.1)
    var blend := smoothstep(0.0, 1.0, camera_mix)
    var target := Vector3(-0.8, 0, 0).lerp(Vector3(4.0, 0, 2.8), blend)
    camera.position = Vector3(15, 27, 33).lerp(Vector3(16, 18, 23), blend)
    camera.look_at(target)
    camera.size = lerpf(25.0, 16.5, blend)


func _build_ui() -> void:
    ui = CanvasLayer.new()
    add_child(ui)
    var root := Control.new()
    root.name = "StudyControls"
    root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    root.mouse_filter = Control.MOUSE_FILTER_IGNORE
    ui.add_child(root)
    var title := Label.new()
    title.text = "海水习作  /  02"
    title.position = Vector2(30, 25)
    title.add_theme_color_override("font_color", Color("fff4db"))
    title.add_theme_color_override("font_shadow_color", Color(0.02, 0.12, 0.19, 0.55))
    title.add_theme_constant_override("shadow_offset_y", 2)
    title.add_theme_font_size_override("font_size", 23)
    root.add_child(title)
    var subtitle := Label.new()
    subtitle.text = "TROPICAL WATER  ·  实时 3D 样片"
    subtitle.position = Vector2(31, 61)
    subtitle.add_theme_font_size_override("font_size", 12)
    subtitle.modulate = Color("d7f1eb")
    root.add_child(subtitle)
    var row := HBoxContainer.new()
    row.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
    row.offset_left = -450
    row.offset_top = -64
    row.offset_right = -26
    row.offset_bottom = -24
    row.add_theme_constant_override("separation", 7)
    root.add_child(row)
    pause_button = _button("暂停", _toggle_playing)
    view_button = _button("岸边近看", _toggle_view)
    sail_button = _button("停船", _toggle_sailing)
    row.add_child(pause_button)
    row.add_child(view_button)
    row.add_child(sail_button)
    reset_button = _button("复位", reset_study)
    row.add_child(reset_button)
    var help := Label.new()
    help.text = "空格 暂停   ·   V 视角   ·   H 隐藏界面   ·   Esc 退出"
    help.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
    help.position = Vector2(30, -41)
    help.add_theme_font_size_override("font_size", 12)
    help.modulate = Color("d7eeeb")
    root.add_child(help)


func _button(text: String, callback: Callable) -> Button:
    var button := Button.new()
    button.text = text
    button.custom_minimum_size = Vector2(98, 40)
    button.add_theme_font_size_override("font_size", 15)
    button.add_theme_color_override("font_color", Color("f9f0d9"))
    var style := StyleBoxFlat.new()
    style.bg_color = Color(0.025, 0.16, 0.22, 0.8)
    style.set_corner_radius_all(9)
    style.content_margin_left = 14
    style.content_margin_right = 14
    button.add_theme_stylebox_override("normal", style)
    var hover := style.duplicate() as StyleBoxFlat
    hover.bg_color = Color(0.06, 0.29, 0.32, 0.95)
    button.add_theme_stylebox_override("hover", hover)
    button.add_theme_stylebox_override("pressed", hover)
    button.pressed.connect(callback)
    return button


func _toggle_playing() -> void:
    playing = not playing
    pause_button.text = "暂停" if playing else "继续"


func _toggle_view() -> void:
    close_view = not close_view
    view_button.text = "整体查看" if close_view else "岸边近看"


func _toggle_sailing() -> void:
    sailing = not sailing
    if sailing and boat.position.z <= -8.5:
        boat.position = Vector3(-4.5, 0, 2)
        wake = 0.0
    sail_button.text = "停船" if sailing else "航行"


func reset_study() -> void:
    camera_override = false
    camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    time = 0.0
    playing = true
    sailing = true
    close_view = false
    wake = 0.0
    boat.position = Vector3(-4.5, 0, 2)
    pause_button.text = "暂停"
    view_button.text = "岸边近看"
    sail_button.text = "停船"


func _unhandled_key_input(event: InputEvent) -> void:
    if not event is InputEventKey or not event.pressed or event.echo:
        return
    match event.keycode:
        KEY_SPACE: _toggle_playing()
        KEY_V: _toggle_view()
        KEY_H: ui.visible = not ui.visible
        KEY_R: reset_study()
        KEY_ESCAPE: get_tree().quit()


func _process(delta: float) -> void:
    if _sampling:
        var now := Time.get_ticks_usec()
        _samples.append(float(now - _last_sample_usec) / 1000.0)
        _last_sample_usec = now
    _update_camera(delta)
    if playing:
        time += delta
        var speed := 0.5 if sailing else 0.0
        boat.position.z = maxf(boat.position.z - speed * delta, -8.5)
        if sailing and boat.position.z <= -8.5:
            sailing = false
            sail_button.text = "航行"
        wake = move_toward(wake, 1.0 if sailing else 0.0, delta * 0.35)
        boat.position.y = sin(time * 1.1) * 0.034
        boat.rotation.z = sin(time * 0.92) * 0.012
        boat.rotation.x = sin(time * 0.77 + 0.7) * 0.009
    _sync_water_materials()
    if (capture_mode or demo_mode) and Time.get_ticks_msec() - _capture_started > 150000:
        push_error("WATER_STUDY_FAIL: 150 second watchdog")
        get_tree().quit(2)


func _sync_water_materials() -> void:
    for material in [water_material, sand_material, swash_material]:
        material.set_shader_parameter("study_time", time)
    water_material.set_shader_parameter("boat_position", boat.position)
    water_material.set_shader_parameter("wake_strength", wake)


func _run_capture() -> void:
    if DisplayServer.get_name() == "headless":
        push_error("WATER_STUDY_FAIL: screenshots require a graphical renderer")
        get_tree().quit(2)
        return
    var output := "res://captures/" + Time.get_datetime_string_from_system().replace(":", "-")
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):
            output = arg.trim_prefix("--output=")
    if DirAccess.dir_exists_absolute(output):
        push_error("WATER_STUDY_FAIL: output directory already exists")
        get_tree().quit(2)
        return
    if DirAccess.make_dir_recursive_absolute(output) != OK:
        get_tree().quit(2)
        return
    await get_tree().create_timer(2.0).timeout
    reset_study()
    await get_tree().create_timer(3.0).timeout
    if not await _save_clean_frame(output + "/01_water_overview.png"):
        return
    var overview_performance := await _measure_frames(5.0)
    if not await _click_button(pause_button):
        return
    var paused_time := time
    var paused_position := boat.position
    await get_tree().create_timer(0.3).timeout
    if not _check(time == paused_time and boat.position == paused_position, "pause must freeze water and boat"):
        return
    if not await _click_button(pause_button):
        return
    await get_tree().create_timer(1.0).timeout
    if not _check(time > paused_time and boat.position.z < paused_position.z, "resume must move water and boat"):
        return
    if not await _save_clean_frame(output + "/02_water_motion.png"):
        return
    if not await _click_button(view_button):
        return
    await get_tree().create_timer(1.2).timeout
    if not _check(close_view and camera_mix >= 0.99, "near camera did not settle"):
        return
    if not await _save_clean_frame(output + "/03_shore_closeup.png"):
        return
    var near_performance := await _measure_frames(5.0)
    if not await _save_clean_frame(output + "/06_wake_moving.png"):
        return
    if not await _click_button(sail_button):
        return
    var stopped_z := boat.position.z
    var moving_wake := wake
    await get_tree().create_timer(1.0).timeout
    if not _check(wake > 0.0 and wake < moving_wake, "wake must decay gradually after stopping"):
        return
    if not await _save_clean_frame(output + "/07_wake_fading.png"):
        return
    await get_tree().create_timer(2.1).timeout
    if not _check(not sailing and wake <= 0.01 and boat.position.z == stopped_z, "stop must freeze travel and fade wake"):
        return
    if not await _save_clean_frame(output + "/08_wake_stopped.png"):
        return
    if not await _save_frame(output + "/04_controls.png"):
        return
    # Exercise the endpoint at late study time without a long unattended wait.
    boat.position.z = -8.49
    time = 35.0
    if not await _click_button(sail_button):
        return
    await get_tree().create_timer(0.2).timeout
    if not _check(not sailing and sail_button.text == "航行", "endpoint must update sailing control"):
        return
    if not await _click_button(sail_button):
        return
    if not _check(sailing and boat.position.z > 1.0, "sailing must restart after the endpoint"):
        return
    if not await _click_button(reset_button):
        return
    if not _check(time < 0.5 and sailing and playing and not close_view and boat.position.z > 1.5, "reset state failed"):
        return
    await get_tree().create_timer(1.2).timeout
    if not _check(camera_mix <= 0.01, "reset camera did not return to wide"):
        return
    if not await _save_frame(output + "/05_reset.png"):
        return
    var low_performance := await _capture_water_details(output)
    if low_performance.is_empty():
        return
    var metadata := {
        "study_version": 2,
        "water_model": "alpha blended depth attenuation; opaque sea floor; no refraction distortion",
        "water_style": "calm mid/deep surfaces; broken sun ribbons; preserved shore swash",
        "shore_phases_seconds": [0.25, 0.95, 1.7, 2.4, 3.4, 4.4],
        "surface_diagnostics": {
            "overview_seconds": [1.7, 3.4], "low_seconds": 1.7,
            "boat_position": [-4.5, 0.0, 0.5], "boat_rotation": [0.0, 0.0, 0.0], "wake": 0.0,
            "overview_position": [15.0, 27.0, 33.0], "overview_target": [-0.8, 0.0, 0.0], "overview_size": 25.0,
            "low_position": [-2.0, 6.5, 14.0], "low_target": [4.0, 0.0, 4.0], "low_fov": 44.0
        },
        "contact_objects": int(water_material.get_shader_parameter("contact_count")),
        "renderer": RenderingServer.get_current_rendering_method(),
        "size": str(get_viewport().get_visible_rect().size),
        "window_pixels": str(DisplayServer.window_get_size()),
        "frames": Engine.get_frames_drawn(),
        "boat_asset": ResourceLoader.exists("res://assets/test_boat.glb"),
        "controls": "viewport mouse press/release: pause/resume, near view, stop/wake decay, endpoint restart, reset/wide view",
        "frame_timing": {"method": "monotonic process-to-process milliseconds; no screenshot or recording during measurement; includes VSync and desktop scheduling", "overview": overview_performance, "near": near_performance, "low": low_performance},
        "visual_acceptance": "awaiting user"
    }
    var file := FileAccess.open(output + "/result.json", FileAccess.WRITE)
    if file == null:
        get_tree().quit(2)
        return
    file.store_string(JSON.stringify(metadata, "  "))
    file.close()
    print("WATER_STUDY_CAPTURE_PASS ", ProjectSettings.globalize_path(output))
    get_tree().quit()


func _capture_surface_details(output: String) -> bool:
    playing = false
    sailing = false
    wake = 0.0
    boat.position = Vector3(-4.5, 0.0, 0.5)
    boat.rotation = Vector3.ZERO
    camera_override = true
    camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    camera.size = 25.0
    camera.position = Vector3(15.0, 27.0, 33.0)
    camera.look_at(Vector3(-0.8, 0.0, 0.0))
    var phases := [1.7, 3.4]
    for i in phases.size():
        time = phases[i]
        _sync_water_materials()
        await get_tree().process_frame
        await get_tree().process_frame
        if not await _save_clean_frame(output + "/surface_fixed_%02d.png" % i):
            return false
        if not _check(time == phases[i] and boat.position == Vector3(-4.5, 0.0, 0.5) and boat.rotation == Vector3.ZERO and wake == 0.0, "surface diagnostic must remain frozen"):
            return false
    camera.projection = Camera3D.PROJECTION_PERSPECTIVE
    camera.fov = 44.0
    camera.position = Vector3(-2.0, 6.5, 14.0)
    camera.look_at(Vector3(4.0, 0.0, 4.0))
    time = 1.7
    _sync_water_materials()
    await get_tree().process_frame
    await get_tree().process_frame
    return await _save_clean_frame(output + "/surface_fixed_low.png")


func _capture_water_details(output: String) -> Dictionary:
    if not await _capture_surface_details(output):
        return {}
    _sync_water_materials()
    for material in [water_material, sand_material, swash_material]:
        if not _check(material.get_shader_parameter("coast_shape") == COAST_SHAPE and material.get_shader_parameter("bay_shape") == BAY_SHAPE, "shore materials must share geometry parameters"):
            return {}
        if not _check(is_equal_approx(float(material.get_shader_parameter("study_time")), time), "all water layers must share paused time"):
            return {}
    if not _check(is_equal_approx(_sand_height(0.0, 0.0), 0.0) and absf(_sand_height(-0.001, 0.0) - _sand_height(0.001, 0.0)) < 0.001, "shore surface must be continuous"):
        return {}
    var ground := get_node("CurvedSandBank") as MeshInstance3D
    var ground_bounds := ground.mesh.get_aabb()
    if not _check(ground_bounds.position.x < -90.0 and ground_bounds.position.z <= -100.0 and ground_bounds.end.z >= 100.0, "sea floor must cover the visible water"):
        return {}
    if not _check(int(water_material.get_shader_parameter("contact_count")) == 8, "expected six pier posts and two emergent stones"):
        return {}
    camera_override = true
    camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    camera.size = 12.0
    var target := Vector3(_shore(-2.5) - 1.2, 0.0, -2.5)
    camera.position = target + Vector3(7.0, 12.0, 13.0)
    camera.look_at(target)
    var phases := [0.25, 0.95, 1.7, 2.4, 3.4, 4.4]
    for i in phases.size():
        time = phases[i]
        _sync_water_materials()
        await get_tree().process_frame
        await get_tree().process_frame
        if not await _save_clean_frame(output + "/shore_phase_%02d.png" % i):
            return {}
    var original_cull_mask := camera.cull_mask
    camera.cull_mask = 2
    swash_material.set_shader_parameter("debug_foam_mask", true)
    var mask_phases := [0.25, 2.4, 4.4]
    for i in mask_phases.size():
        time = mask_phases[i]
        _sync_water_materials()
        await get_tree().process_frame
        await get_tree().process_frame
        if not await _save_clean_frame(output + "/foam_mask_%02d.png" % i):
            return {}
    camera.cull_mask = original_cull_mask
    swash_material.set_shader_parameter("debug_foam_mask", false)
    time = 1.7
    _sync_water_materials()
    sea.visible = false
    swash.visible = false
    if not await _save_clean_frame(output + "/09_seafloor_diagnostic.png"):
        return {}
    sea.visible = true
    swash.visible = true
    camera.projection = Camera3D.PROJECTION_PERSPECTIVE
    camera.fov = 44.0
    camera.position = Vector3(-2.0, 6.5, 14.0)
    camera.look_at(Vector3(4.0, 0.0, 4.0))
    playing = true
    await get_tree().create_timer(0.6).timeout
    if not await _save_clean_frame(output + "/10_low_angle.png"):
        return {}
    var performance := await _measure_frames(5.0)
    reset_study()
    await get_tree().create_timer(1.2).timeout
    if not _check(not camera_override and camera.projection == Camera3D.PROJECTION_ORTHOGONAL and camera_mix <= 0.01, "diagnostic camera must restore normal controls"):
        return {}
    return performance


func _check(condition: bool, message: String) -> bool:
    if not condition:
        push_error("WATER_STUDY_FAIL: " + message)
        get_tree().quit(2)
    return condition


func _click_button(button: Button) -> bool:
    ui.visible = true
    await get_tree().process_frame
    var point := button.get_global_rect().get_center()
    if not _check(get_viewport().get_visible_rect().has_point(point), "button is outside the viewport: " + button.text):
        return false
    var clicks := [0]
    var count_click := func() -> void: clicks[0] += 1
    button.pressed.connect(count_click)
    var motion := InputEventMouseMotion.new()
    motion.position = point
    get_viewport().push_input(motion, true)
    for down in [true, false]:
        var event := InputEventMouseButton.new()
        event.position = point
        event.button_index = MOUSE_BUTTON_LEFT
        event.pressed = down
        get_viewport().push_input(event, true)
    # Keep the synthetic press/release atomic; desktop mouse motion must not split it.
    await get_tree().process_frame
    button.pressed.disconnect(count_click)
    print("WATER_CLICK ", button.text, " count=", clicks[0], " center=", point, " time=", time, " sailing=", sailing)
    return _check(clicks[0] == 1, "mouse click failed: " + button.text)


func _measure_frames(seconds: float) -> Dictionary:
    _samples.clear()
    _last_sample_usec = Time.get_ticks_usec()
    _sampling = true
    await get_tree().create_timer(seconds).timeout
    _sampling = false
    var sorted := _samples.duplicate()
    sorted.sort()
    if sorted.is_empty():
        return {}
    var total := 0.0
    var slow := 0
    for value in sorted:
        total += value
        if value > 33.333:
            slow += 1
    var mean := total / sorted.size()
    return {"frames": sorted.size(), "mean_ms": mean, "p95_ms": sorted[int(ceil(sorted.size() * 0.95)) - 1], "max_ms": sorted.back(), "over_33ms": slow, "mean_fps": 1000.0 / mean}


func _run_demo() -> void:
    if not _check(DisplayServer.get_name() != "headless", "demo requires a graphical renderer"):
        return
    await get_tree().create_timer(2.0).timeout
    reset_study()
    ui.visible = false
    await get_tree().create_timer(7.0).timeout
    _toggle_view()
    await get_tree().create_timer(4.0).timeout
    _toggle_sailing()
    await get_tree().create_timer(4.0).timeout
    _toggle_view()
    await get_tree().create_timer(3.0).timeout
    print("WATER_STUDY_DEMO_PASS: 18 second preview completed")
    get_tree().quit()


func _save_clean_frame(path: String) -> bool:
    ui.visible = false
    var saved := await _save_frame(path)
    ui.visible = true
    return saved


func _save_frame(path: String) -> bool:
    await RenderingServer.frame_post_draw
    var image := get_viewport().get_texture().get_image()
    if image == null or image.is_empty() or image.save_png(path) != OK:
        push_error("WATER_STUDY_FAIL: could not save " + path)
        get_tree().quit(2)
        return false
    return true
