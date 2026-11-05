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
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--water-profile="):
            var profiler := load("res://demo/tropical_harbor_3d/tools/water_profile.gd").new() as RefCounted
            await profiler.run(self, arg.trim_prefix("--water-profile="))
            return
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--reference-review="):
            var review := load("res://demo/tropical_harbor_3d/tools/reference_review.gd").new() as RefCounted
            await review.run(self, arg.trim_prefix("--reference-review="))
            return
    if "--water-review" in OS.get_cmdline_user_args():
        await review_water()
        return
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
    harbor.ui.visible = true
    if not await capture("09_main_entry"):
        return
    var file := FileAccess.open(output + "/art_result.json", FileAccess.WRITE)
    if file == null:
        push_error("ART_PREVIEW: cannot save result")
        get_tree().quit(2)
        return
    file.store_string(JSON.stringify({
        "frames": frames,
        "main_scene": ProjectSettings.get_setting("application/run/main_scene"),
        "loaded_scene": harbor.scene_file_path,
        "materials": wood_material_report(),
        "purpose": "visual art review only",
        "visual_accepted": false,
    }, "  "))
    file.close()
    print("ART_PREVIEW_SAVED frames=", frames.size(), " output=", output)
    get_tree().quit()


func frame(target: Vector3, offset: Vector3, size_: float) -> void:
    harbor.camera.position = target + offset
    harbor.camera.look_at(target)
    harbor.camera.size = size_


func review_water() -> void:
    harbor.capture_lock = true
    harbor.camera.update_view(harbor.ships, 0, true)
    if not await capture("water_01_overview"):
        return
    var material: ShaderMaterial = harbor.environment.water_material
    if "--water-diagnose" in OS.get_cmdline_user_args():
        material.set_shader_parameter("glint_strength", 0.0)
        if not await capture("water_no_custom_glint"):
            return
        material.set_shader_parameter("glint_strength", 1.0)
        material.set_shader_parameter("sky_reflection_strength", 0.0)
        if not await capture("water_no_sky_reflection"):
            return
        material.set_shader_parameter("sky_reflection_strength", 1.0)
    frame(Vector3(3.0, 0.0, -2.5), Vector3(8, 15, 14), 13.0)
    if not await capture("water_02_shallows"):
        return
    frame(Vector3(7.0, 0.55, 9.4), Vector3(8, 12, 14), 8.2)
    if not await capture("water_03_piers"):
        return
    var boat: Node3D = harbor.ships[0]
    frame(boat.position + Vector3(0, 0.20, 0), Vector3(5, 7, -7), 6.0)
    if not await capture("water_04_boat"):
        return
    # Orthographic rays need to begin above the water, even at the image bottom.
    frame(Vector3(1.0, 0, 2), Vector3(5, 3, 9) * 6.0, 12.0)
    if not await capture("water_05_low_angle"):
        return
    if "--water-diagnose" in OS.get_cmdline_user_args():
        var sun := harbor.get_node("WarmAfternoon") as DirectionalLight3D
        sun.shadow_enabled = false
        if not await capture("water_low_no_shadow"):
            return
        sun.shadow_enabled = true
        material.set_shader_parameter("sky_reflection_strength", 0.0)
        if not await capture("water_low_no_sky"):
            return
        material.set_shader_parameter("sky_reflection_strength", 1.0)
        harbor.get_node("CurvedSandBank").visible = false
        if not await capture("water_low_no_sand"):
            return
        harbor.get_node("CurvedSandBank").visible = true
        harbor.environment.sea.visible = false
        harbor.environment.swash.visible = false
        if not await capture("water_low_seabed_only"):
            return
        finish({"kind": "water diagnostics", "main_scene": harbor.scene_file_path})
        return
    frame(Vector3(2.0, 0.0, -1.5), Vector3(8, 15, 14), 16.0)
    for i in 48:
        harbor.time = 1.7 + float(i) * 0.10
        for ship in harbor.ships:
            ship.advance(0.0, harbor.time)
        if not await capture("water_motion_%02d" % i):
            return
    finish({"kind": "water", "main_scene": harbor.scene_file_path,
        "motion_step_seconds": 0.10, "motion_frames": 48})


func wood_material_report() -> Array[Dictionary]:
    var result: Array[Dictionary] = []
    var seen: Dictionary = {}
    for item in harbor.find_children("*", "MeshInstance3D", true, false):
        var mesh := item as MeshInstance3D
        if mesh.mesh == null:
            continue
        for surface in mesh.mesh.get_surface_count():
            var material := mesh.get_active_material(surface) as StandardMaterial3D
            if material == null or material.albedo_texture == null or seen.has(material.resource_name):
                continue
            seen[material.resource_name] = true
            result.append({
                "name": material.resource_name,
                "albedo": material.albedo_texture.resource_path,
                "normal": material.normal_texture.resource_path if material.normal_texture != null else "",
                "normal_enabled": material.normal_enabled,
                "roughness": material.roughness,
                "specular": material.metallic_specular,
            })
    return result


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


func capture(name_: String, crop_center: bool = false, settle_frames: int = 10) -> bool:
    harbor.sync_water()
    for i in settle_frames:
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
