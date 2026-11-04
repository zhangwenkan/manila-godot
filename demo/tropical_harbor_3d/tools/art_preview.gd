extends Node

var harbor: Node3D
var output := ""
var started := 0
var frames: Array[String] = []


func _process(_delta: float) -> void:
    if started > 0 and Time.get_ticks_msec() - started > 50000:
        push_error("ART_PREVIEW_TIMEOUT: 50-second limit")
        get_tree().quit(2)


func run(scene: Node3D) -> void:
    harbor = scene
    started = Time.get_ticks_msec()
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--art-output="):
            output = arg.trim_prefix("--art-output=")
    if output.is_empty() or DirAccess.make_dir_recursive_absolute(output) != OK:
        push_error("ART_PREVIEW: output directory unavailable")
        get_tree().quit(2)
        return
    harbor.paused = true
    harbor.time = 1.7
    harbor.ui.visible = false
    harbor.camera_override = true
    harbor.get_window().grab_focus()
    var boat: Node3D = harbor.ships[0]
    boat.position = Vector3(-3.0, 0, 4)
    boat.cargo_root.visible = false
    for i in [1, 2]:
        harbor.ships[i].visible = false
    var sun := harbor.get_node_or_null("WarmAfternoon") as DirectionalLight3D
    var world := harbor.get_world_3d().environment
    if sun == null or world == null:
        push_error("ART_PREVIEW: daylight environment unavailable")
        get_tree().quit(2)
        return
    frame(boat.position + Vector3(0, 0.28, 0), Vector3(5, 7, -7), 6.0)
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--art-diagnose="):
            await diagnose(arg.trim_prefix("--art-diagnose="), boat, sun, world)
            return
    if not await capture("01_godot_original_shadow"):
        return
    world.ssao_enabled = false
    if not await capture("02_godot_no_ssao"):
        return
    world.ssao_enabled = true
    sun.shadow_enabled = false
    if not await capture("03_godot_no_shadow"):
        return
    sun.shadow_enabled = true
    harbor.configure_art_shadows()
    if not await capture("04_godot_clean_shadow"):
        return
    boat.cargo_root.visible = true
    for i in harbor.state.ships[0].slots.size():
        harbor.state.ships[0].slots[i].owner = i % 3
    boat.sync_crew(harbor.state.ships[0])
    if not await capture("05_godot_cargo_crew"):
        return
    boat.visible = false
    frame(Vector3(7.0, 0.55, 9.4), Vector3(8, 12, 14), 8.2)
    if not await capture("06_godot_piers"):
        return
    frame(Vector3(5.4, 0.70, 11.6), Vector3(4, 5, 7), 4.0)
    if not await capture("07_godot_fracture"):
        return
    for i in harbor.ships.size():
        harbor.ships[i].visible = true
        harbor.ships[i].position = harbor.state.world_position(harbor.state.ships[i])
    harbor.camera.update_view(harbor.ships, 0, true)
    if not await capture("08_godot_overview"):
        return
    var file := FileAccess.open(output + "/art_result.json", FileAccess.WRITE)
    if file == null:
        push_error("ART_PREVIEW: cannot save result")
        get_tree().quit(2)
        return
    file.store_string(JSON.stringify({"frames": frames, "purpose": "visual art review only", "visual_accepted": false}, "  "))
    file.close()
    print("ART_PREVIEW_SAVED frames=", frames.size(), " output=", output)
    get_tree().quit()


func frame(target: Vector3, offset: Vector3, size_: float) -> void:
    harbor.camera.position = target + offset
    harbor.camera.look_at(target)
    harbor.camera.size = size_


func diagnose(kind: String, boat: Node3D, sun: DirectionalLight3D, world: Environment) -> void:
    harbor.paused = true
    harbor.configure_art_shadows()
    boat.position = Vector3(-3.0, 0, 4)
    boat.rotation = Vector3.ZERO
    if kind == "pier":
        boat.visible = false
        frame(Vector3(7.0, 0.05, 7.3), Vector3(2.4, 1.6, 3.2), 3.4)
    else:
        frame(Vector3(-3.0, 0.0, 4.0), Vector3(2.4, 0.72, 1.55), 2.05)
    var times := [0.00, 0.28, 0.56, 0.84, 1.12, 1.40]
    for i in times.size():
        if not await sample("both_%02d" % i, boat, times[i], times[i], true):
            return
    for i in [1, 3, 5]:
        if not await sample("water_%02d" % i, boat, times[i], 0.0, false):
            return
    for i in [1, 3, 5]:
        if not await sample("boat_%02d" % i, boat, 1.7, times[i], true):
            return
    if not await sample("frozen", boat, 1.7, 0.0, false):
        return
    sun.shadow_enabled = false
    if not await sample("no_shadow", boat, 0.84, 0.84, true):
        return
    sun.shadow_enabled = true
    world.ssao_enabled = false
    if not await sample("no_ssao", boat, 0.84, 0.84, true):
        return
    world.ssao_enabled = true
    var sea: MeshInstance3D = harbor.environment.sea
    sea.visible = false
    if not await sample("no_water", boat, 0.84, 0.84, true):
        return
    sea.visible = true
    sun.light_angular_distance = 1.6
    sun.shadow_normal_bias = 1.0
    RenderingServer.directional_shadow_atlas_set_size(2048, true)
    RenderingServer.directional_soft_shadow_filter_set_quality(RenderingServer.SHADOW_QUALITY_SOFT_LOW)
    if not await sample("orig_shadow", boat, 0.84, 0.84, true):
        return
    harbor.configure_art_shadows()
    var water_mat: ShaderMaterial = harbor.environment.water_material
    water_mat.set_shader_parameter("reflection_amount", 0.0)
    if not await sample("no_reflect", boat, 0.84, 0.84, true):
        return
    water_mat.set_shader_parameter("reflection_amount", 0.0)
    if kind != "pier":
        frame(Vector3(-3.0, 0.28, 4.0), Vector3(5, 7, -7), 6.0)
        if not await sample("hull_context", boat, 0.84, 0.84, true):
            return
        boat.visible = false
        frame(Vector3(7.0, 0.04, 7.3), Vector3(2.2, 1.15, 2.6), 3.1)
        if not await sample("pier_waterline", boat, 0.84, 0.84, false):
            return
        boat.visible = true
        for i in harbor.ships.size():
            harbor.ships[i].visible = true
            harbor.ships[i].position = harbor.state.world_position(harbor.state.ships[i])
        harbor.camera.update_view(harbor.ships, 0, true)
        harbor.camera_override = true
        if not await sample("overview_fusion", boat, 0.84, 0.84, true):
            return
    finish({
        "kind": kind,
        "viewport": [get_viewport().get_visible_rect().size.x, get_viewport().get_visible_rect().size.y],
        "window": [DisplayServer.window_get_size().x, DisplayServer.window_get_size().y],
        "camera_size": harbor.camera.size,
        "msaa": ProjectSettings.get_setting("rendering/anti_aliasing/quality/msaa_3d"),
        "shadow_atlas": 4096
    })


func sample(name_: String, boat: Node3D, water_time: float, boat_time: float, bob: bool) -> bool:
    harbor.time = water_time
    if bob:
        boat.advance(0.0, boat_time)
    else:
        boat.position.y = 0.0
        boat.rotation.x = 0.0
        boat.rotation.z = 0.0
    return await capture(name_, true)


func capture(name_: String, crop_center: bool = false) -> bool:
    harbor.sync_water()
    for i in 10:
        await get_tree().process_frame
    await RenderingServer.frame_post_draw
    var image := get_viewport().get_texture().get_image()
    if image == null or image.is_empty() or image.save_png(output + "/" + name_ + ".png") != OK:
        push_error("ART_PREVIEW: capture failed " + name_)
        get_tree().quit(2)
        return false
    frames.append(name_ + ".png")
    if not crop_center:
        return true
    var crop := Rect2i(int(image.get_width() / 2) - 220, int(image.get_height() * 0.62) - 160, 440, 320)
    crop = crop.intersection(Rect2i(0, 0, image.get_width(), image.get_height()))
    if crop.size.x > 0 and image.get_region(crop).save_png(output + "/" + name_ + "_crop.png") == OK:
        frames.append(name_ + "_crop.png")
    return true


func finish(extra: Dictionary) -> void:
    extra["frames"] = frames
    extra["purpose"] = "visual art review only"
    extra["visual_accepted"] = false
    var file := FileAccess.open(output + "/art_result.json", FileAccess.WRITE)
    if file == null:
        push_error("ART_PREVIEW: cannot save result")
        get_tree().quit(2)
        return
    file.store_string(JSON.stringify(extra, "  "))
    file.close()
    print("ART_PREVIEW_SAVED frames=", frames.size(), " output=", output)
    get_tree().quit()
