extends RefCounted

# All probes run inside the root main scene and exit through the art watchdog.
var host: Node
var harbor: Node3D


func run(preview: Node, mode: String) -> void:
    host = preview
    harbor = host.harbor
    harbor.capture_lock = true
    harbor.configure_art_shadows()
    harbor.camera.update_view(harbor.ships, 0.0, true)
    var viewport := harbor.get_viewport().get_viewport_rid()
    RenderingServer.viewport_set_measure_render_time(viewport, true)
    DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
    var env: Environment = harbor.get_world_3d().environment
    var sun: DirectionalLight3D = harbor.get_node("WarmAfternoon")
    var sand: MeshInstance3D = harbor.get_node("CurvedSandBank")
    if mode == "compare":
        await compare(viewport, sand)
        return
    if mode == "stability":
        await stability()
        return
    var result: Dictionary = {}
    result["baseline"] = await measure(viewport)
    if not await host.capture("profile_baseline"):
        return
    if mode == "diagnose":
        harbor.environment.sea.visible = false
        result["no_water"] = await measure(viewport)
        harbor.environment.sea.visible = true
        sand.visible = false
        result["no_seabed"] = await measure(viewport)
        sand.visible = true
        sun.shadow_enabled = false
        result["no_sun_shadows"] = await measure(viewport)
        sun.shadow_enabled = true
        env.ssao_enabled = false
        result["no_ssao"] = await measure(viewport)
        env.ssao_enabled = true
        RenderingServer.environment_set_ssao_quality(RenderingServer.ENV_SSAO_QUALITY_LOW, true, 0.5, 2, 50.0, 300.0)
        result["low_sample_ssao"] = await measure(viewport)
        if not await host.capture("profile_low_ssao"):
            return
        sand.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        result["low_ssao_no_sand_cast"] = await measure(viewport)
        if not await host.capture("profile_low_ssao_no_sand_cast"):
            return
        sand.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        harbor.environment.configure_ambient_occlusion()
        var original: Shader = harbor.environment.water_material.shader
        var simple := Shader.new()
        simple.code = "shader_type spatial; render_mode blend_mix, depth_draw_never, cull_disabled; void fragment() { ALBEDO = vec3(0.02, 0.4, 0.4); ALPHA = 0.6; ROUGHNESS = 0.3; }"
        harbor.environment.water_material.shader = simple
        result["simple_water"] = await measure(viewport)
        harbor.environment.water_material.shader = original
        result["baseline_repeat"] = await measure(viewport)
    else:
        harbor.camera.focus_ship = 0
        harbor.camera.update_view(harbor.ships, 0.0, true)
        result["close"] = await measure(viewport)
        if not await host.capture("profile_close"):
            return
    host.finish({"kind": "water performance " + mode, "timing": result,
        "resolution": [harbor.get_window().size.x, harbor.get_window().size.y],
        "vsync": "disabled for this measurement process only", "seconds_per_probe": 2.0})


func stability() -> void:
    var window := harbor.get_window()
    var original: Vector2i = window.size
    var sizes: Array[Vector2i] = [Vector2i(1440, 810), Vector2i(1440, 745),
        Vector2i(900, 900), Vector2i(675, 1000), Vector2i(1000, 625), Vector2i(1600, 900)]
    var probes: Array[Dictionary] = []
    for i in 24:
        window.size = sizes[i % sizes.size()]
        if i % 6 == 0:
            harbor.new_voyage()
        if i % 3 == 0:
            harbor.view_piers()
        else:
            harbor.camera.focus_ship = 0 if i % 3 == 1 else -1
            harbor.camera.update_view(harbor.ships, 0.0, true)
        var started := Time.get_ticks_msec()
        while Time.get_ticks_msec() - started < 350:
            harbor.time += 1.0 / 60.0
            for ship in harbor.ships:
                ship.advance(1.0 / 60.0, harbor.time)
            await host.get_tree().process_frame
        var reflected: Vector2i = harbor.reflection.viewport.size
        if reflected.x > 512 or reflected.y > 512 or reflected.x < 1 or reflected.y < 1:
            push_error("WATER_STABILITY: reflection texture exceeded its budget")
            host.get_tree().quit(2)
            return
        probes.append({"window": [window.size.x, window.size.y],
            "reflection": [reflected.x, reflected.y], "voyage": harbor.state.voyage})
    window.size = original
    harbor.camera.focus_ship = -1
    harbor.camera.update_view(harbor.ships, 0.0, true)
    if not await host.capture("stability_final", false, 12):
        return
    if not await host.capture("stability_paused_repeat", false, 12):
        return
    host.finish({"kind": "bounded water resize and rebuild stability check", "probes": probes,
        "note": "24 real window resizes, portrait and landscape, four voyage rebuilds; this cannot prove a driver crash is fixed."})


func compare(viewport: RID, sand: MeshInstance3D) -> void:
    var baseline := ""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--profile-baseline="):
            baseline = arg.trim_prefix("--profile-baseline=")
    var old_shaders: Array[Shader] = []
    var current_shaders: Array[Shader] = [harbor.environment.water_material.shader, harbor.environment.sand_material.shader]
    for file in ["fleet_water.gdshader", "sand.gdshader"]:
        var path := baseline.path_join("materials").path_join(file)
        if baseline.is_empty() or not FileAccess.file_exists(path):
            push_error("WATER_PROFILE: missing baseline shader " + path)
            host.get_tree().quit(2)
            return
        var shader := Shader.new()
        shader.code = FileAccess.get_file_as_string(path)
        old_shaders.append(shader)
    var settings: Dictionary = {}
    for key in ["quality", "half_size", "adaptive_target", "blur_passes", "fadeout_from", "fadeout_to"]:
        settings[key] = ProjectSettings.get_setting("rendering/environment/ssao/" + key)
    var result: Dictionary = {}
    for pass_name in ["before_1", "after_1", "before_2", "after_2"]:
        var before: bool = pass_name.begins_with("before")
        harbor.environment.water_material.shader = old_shaders[0] if before else current_shaders[0]
        harbor.environment.sand_material.shader = old_shaders[1] if before else current_shaders[1]
        sand.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if before else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        harbor.reflection.set_enabled(not before)
        if before:
            RenderingServer.environment_set_ssao_quality(settings.quality, settings.half_size, settings.adaptive_target,
                settings.blur_passes, settings.fadeout_from, settings.fadeout_to)
        else:
            harbor.environment.configure_ambient_occlusion()
        result[pass_name] = await measure(viewport, 3.0, 1.0)
        if not await host.capture("profile_" + pass_name):
            return
    host.finish({"kind": "water optimization paired benchmark", "timing": result,
        "baseline_ao": settings, "baseline_source": baseline,
        "resolution": [harbor.get_window().size.x, harbor.get_window().size.y],
        "vsync": "disabled for both versions", "seconds_per_probe": 3.0,
        "note": "Identical camera, ships and time; alternates saved baseline shaders/settings with current water, AO and reflections."})


func measure(viewport: RID, seconds: float = 2.0, warmup_seconds: float = 0.45) -> Dictionary:
    var warmup := Time.get_ticks_msec()
    while Time.get_ticks_msec() - warmup < warmup_seconds * 1000.0:
        await host.get_tree().process_frame
    var start := Time.get_ticks_usec()
    var previous := start
    var frames: Array[float] = []
    var gpu: Array[float] = []
    var cpu: Array[float] = []
    var focused := 0
    while Time.get_ticks_usec() - start < seconds * 1000000.0:
        await host.get_tree().process_frame
        var now := Time.get_ticks_usec()
        frames.append(float(now - previous) / 1000.0)
        gpu.append(RenderingServer.viewport_get_measured_render_time_gpu(viewport))
        cpu.append(RenderingServer.viewport_get_measured_render_time_cpu(viewport))
        previous = now
        focused += int(harbor.get_window().has_focus())
    return {"frame_ms": stats(frames), "gpu_ms": stats(gpu), "render_cpu_ms": stats(cpu),
        "focus_fraction": float(focused) / frames.size(),
        "draw_calls": Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
        "primitives": Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)}


func stats(values: Array[float]) -> Dictionary:
    var total := 0.0
    for value in values:
        total += value
    values.sort()
    return {"mean": total / values.size(), "p95": values[int(ceil(values.size() * 0.95)) - 1],
        "count": values.size()}
