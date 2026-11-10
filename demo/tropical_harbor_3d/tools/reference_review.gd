extends RefCounted

# Capture fixtures in the default scene without saving changes to scene assets.
# The detail mode temporarily overrides lighting and shadows for diagnosis.
# Reference video camera values are unknown; 55 degrees / 30 degree FOV is
# an explicit visual estimate, not a claim of exact camera calibration.
const PITCH := 55.0
const FOV := 30.0
const STEP := 0.10
const MOTION_FRAMES := 80

var host: Node
var harbor: Node3D
var pier: Node3D
var shots: Array[Dictionary] = []
var samples: Array[Dictionary] = []


func run(preview: Node, mode: String) -> void:
    host = preview
    harbor = host.harbor
    harbor.capture_lock = true
    harbor.configure_art_shadows()
    pier = harbor.get_node("TimberPiers/WorkingPier") as Node3D
    if mode == "layout":
        await layout_review()
        return
    if mode == "stills":
        harbor.camera.update_view(harbor.ships, 0, true)
        if not await shot("current_00_native", "Current default layout and camera"):
            return
    harbor.get_node("TimberPiers/BrokenPier").visible = false
    for i in [1, 2]:
        harbor.ships[i].visible = false
    if mode == "stills":
        await stills()
    elif mode == "detail":
        await detail()
    elif mode == "reflection":
        await reflection_review()
    else:
        await motion(mode)


func layout_review() -> void:
    harbor.camera.update_view(harbor.ships, 0, true)
    if not await shot("layout_01_departure", "Default opening fleet and shore piers"):
        return
    harbor.view_landing()
    if not await shot("layout_02_landing", "Permanent arrival landing connected to the shore"):
        return
    for i in 3:
        var data: Dictionary = harbor.state.ships[i]
        data.arrived = true
        data.progress = 14
        data.berth = i
        harbor.ships[i].position = harbor.state.world_position(data)
        harbor.ships[i].rotation = Vector3.ZERO
        harbor.ships[i].advance(0.0, harbor.time)
    harbor.camera.update_view(harbor.ships, 0, true)
    if not await shot("layout_03_arrived", "Three boats at the real destination berths; default overview camera"):
        return
    host.frame(Vector3(-3.0, 0.4, -14.8), Vector3(-10, 13, 14), 14.0)
    if not await shot("layout_04_berths", "Bow clearance, deep piles and timber deck at berth"):
        return
    host.frame(Vector3(1.0, 0, -3.5), Vector3(-25, 55, 31), 40.0)
    if not await shot("layout_05_full_route", "Whole harbor for layout review only; normal overview follows the fleet"):
        return
    finish("layout")


func camera(target: Vector3, span: float, azimuth: float = -90.0) -> void:
    var direction := Vector3(sin(deg_to_rad(azimuth)) * cos(deg_to_rad(PITCH)),
        sin(deg_to_rad(PITCH)), cos(deg_to_rad(azimuth)) * cos(deg_to_rad(PITCH)))
    var distance := span / (2.0 * tan(deg_to_rad(FOV) * 0.5))
    harbor.camera.projection = Camera3D.PROJECTION_PERSPECTIVE
    harbor.camera.fov = FOV
    host.frame(target, direction * distance, span)


func stage(pier_x: float, boat_position: Vector3, yaw: float = -90.0) -> void:
    pier.position = Vector3(pier_x, 0, 7.3)
    var ship: Node3D = harbor.ships[0]
    ship.position = boat_position
    ship.rotation = Vector3(0, deg_to_rad(yaw), 0)
    ship.waypoints.clear()
    ship.wake = 0.0
    ship.advance(0.0, harbor.time)
    # Rebuild contacts at the temporary transforms, excluding the hidden broken pier.
    var contacts: PackedVector4Array = harbor.environment.contact_objects.duplicate()
    for item in pier.find_children("*", "MeshInstance3D", true, false):
        if "waterpile_" in str(item.name).to_lower():
            var at: Vector3 = item.global_position
            if depth(at) > 0.0:
                contacts.append(Vector4(at.x, at.z, 0.13, 0.38))
    harbor.environment.set_contacts(contacts, 32)


func depth(point: Vector3) -> float:
    return maxf(0.0, -harbor.environment._sand_height(
        point.x - harbor.environment._shore(point.z), point.z))


func stills() -> void:
    stage(7.01, Vector3(4.0, 0, -1.0))
    camera(Vector3(6.0, 0, -2.5), 14.0, -70.0)
    if not await shot("current_01_shallows", "Original shore and stones; boat moved for waterline context"):
        return
    stage(7.01, Vector3(5.0, 0, 10.5))
    camera(Vector3(7.0, 0, 7.8), 16.0)
    if not await shot("current_02_shore_pier", "Original working pier; boat temporarily placed alongside"):
        return
    stage(-1.8, Vector3(-0.8, 0, 10.5))
    camera(Vector3(-2.2, 0, 7.8), 19.0)
    if not await shot("current_03_outer_pier", "Existing working pier and boat temporarily moved offshore"):
        return
    stage(-10.0, Vector3(-9.0, 0, 10.5))
    camera(Vector3(-10.6, 0, 7.8), 19.0)
    if not await shot("current_04_deep_pier", "Existing working pier and boat temporarily moved into deep water"):
        return
    stage(-1.8, Vector3(-0.8, 0, 10.5))
    camera(Vector3(-0.8, 0, 9.5), 9.0)
    if not await shot("current_05_boat", "Close comparison of existing hull, pier and waterline"):
        return
    camera(Vector3(-27.0, 0, 7.8), 16.0)
    if not await shot("current_06_open_sea", "Current open sea; no matching unobstructed reference footage"):
        return
    finish("stills")


func motion(mode: String) -> void:
    if mode != "idle" and mode != "sail":
        push_error("REFERENCE_REVIEW: unknown motion mode")
        host.get_tree().quit(2)
        return
    stage(-1.8, Vector3(-0.8, 0, 10.5))
    var ship: Node3D = harbor.ships[0]
    camera(Vector3(-0.8, 0, 9.5), 9.0 if mode == "idle" else 22.0)
    if mode == "sail":
        # Turn out into open water, then coast to a stop; use the real ship code.
        ship.travel_to(Vector3(-8.8, 0, 13.5), false)
    for i in MOTION_FRAMES:
        if i > 0:
            # Simulate at 60 Hz, sample at 10 Hz. Capture waits never advance time.
            for tick in 6:
                harbor.time += STEP / 6.0
                ship.advance(STEP / 6.0, harbor.time)
        if not await host.capture("current_%s_%03d" % [mode, i], false, 3):
            return
        var center: Vector2 = harbor.camera.unproject_position(ship.global_position)
        samples.append({"time": harbor.time, "position": vec(ship.position),
            "rotation_degrees": vec(ship.rotation_degrees), "wake": ship.wake,
            "moving": ship.moving, "waypoints": ship.waypoints.size(),
            "screen_center": [center.x, center.y]})
    finish(mode)


func detail() -> void:
    stage(-10.0, Vector3(-9.0, 0, 10.5))
    camera(Vector3(-9.0, 0, 9.5), 9.0)
    if not await shot("detail_01_native", "Identical near view for resolution and light comparisons"):
        return
    var env: Environment = harbor.get_world_3d().environment
    env.ssao_enabled = false
    if not await shot("detail_02_no_ssao", "Diagnostic: SSAO disabled only"):
        return
    env.ssao_enabled = true
    var water: ShaderMaterial = harbor.environment.water_material
    var original: Shader = water.shader
    var shadowless := Shader.new()
    shadowless.code = original.code.replace("cull_disabled;", "cull_disabled, shadows_disabled;")
    water.shader = shadowless
    if not await shot("detail_03_no_surface_shadow", "Diagnostic: water shadow receiving disabled; seabed still receives"):
        return
    water.shader = original
    var sun := harbor.get_node("WarmAfternoon") as DirectionalLight3D
    sun.shadow_enabled = false
    if not await shot("detail_04_no_cast_shadows", "Diagnostic: sun shadows disabled only"):
        return
    sun.shadow_enabled = true
    camera(Vector3(-9.0, 0, 9.5), 16.0)
    if not await shot("detail_05_context", "Same assets and angle, wider framing"):
        return
    finish("detail")


func reflection_review() -> void:
    stage(-1.8, Vector3(-0.8, 0, 10.5))
    harbor.camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    host.frame(Vector3(-1.3, 0.2, 9.5), Vector3(3, 1.5, 5) * 12.0, 9.0)
    var material: ShaderMaterial = harbor.environment.water_material
    if not await shot("reflection_01_on", "Current boat and pier reflection at a low angle"):
        return
    var reflection_image: Image = harbor.reflection.texture().get_image()
    if reflection_image.save_png(host.output + "/reflection_map.png") != OK:
        push_error("REFERENCE_REVIEW: cannot save reflection map")
        host.get_tree().quit(2)
        return
    material.set_shader_parameter("reflection_amount", 0.0)
    if not await shot("reflection_02_off", "Diagnostic: same frame with object reflection disabled"):
        return
    material.set_shader_parameter("reflection_amount", 4.0)
    if not await shot("reflection_03_amplified", "Diagnostic only: reflection amplified to check alignment"):
        return
    material.set_shader_parameter("reflection_amount", 0.65)
    for i in 3:
        if not await shot("reflection_paused_%d" % i, "Diagnostic: paused reflection stability"):
            return
    harbor.reflection.set_enabled(false)
    for i in 3:
        if not await shot("reflection_cached_%d" % i, "Diagnostic: paused reflection texture held"):
            return
    harbor.reflection.set_enabled(true)
    harbor.get_world_3d().environment.ssao_enabled = false
    for i in 3:
        if not await shot("reflection_no_ao_%d" % i, "Diagnostic: paused frame without AO"):
            return
    finish("reflection")


func shot(name_: String, arrangement: String) -> bool:
    if not await host.capture(name_):
        return false
    var ship: Node3D = harbor.ships[0]
    shots.append({"file": name_ + ".png", "arrangement": arrangement,
        "camera_position": vec(harbor.camera.position),
        "camera_rotation_degrees": vec(harbor.camera.rotation_degrees),
        "projection": harbor.camera.projection, "fov": harbor.camera.fov,
        "orthographic_size": harbor.camera.size, "boat_position": vec(ship.position),
        "boat_depth": depth(ship.position), "pier_position": vec(pier.position),
        "pier_center_depth": depth(pier.position)})
    return true


func vec(value: Vector3) -> Array:
    return [value.x, value.y, value.z]


func finish(mode: String) -> void:
    host.finish({"kind": "reference comparison " + mode, "main_scene": harbor.scene_file_path,
        "viewport": vec2(harbor.get_viewport().get_visible_rect().size),
        "render_texture": vec2(Vector2(harbor.get_viewport().get_texture().get_size())),
        "window": vec2(Vector2(harbor.get_window().size)),
        "shots": shots, "samples": samples, "motion_step_seconds": STEP,
        "comparison_pitch_degrees": PITCH, "comparison_fov_degrees": FOV,
        "temporary_placement_only": mode != "layout", "light_and_materials_unchanged": mode != "detail" and mode != "reflection",
        "diagnostic_overrides": mode == "detail" or mode == "reflection",
        "camera_match": "visual approximation; reference camera calibration unavailable"})


func vec2(value: Vector2) -> Array:
    return [value.x, value.y]
