extends RefCounted

var host: Node
var harbor: Node3D
var life: Node3D
var checks := 0
var benchmark_start := 0


func verify(ok: bool, reason: String) -> bool:
    checks += 1
    if not ok:
        push_error("TERMINAL_LIFE: " + reason)
        host.get_tree().quit(2)
    return ok


func view(eye: Vector3, target: Vector3) -> void:
    var origin: Vector3 = harbor.STATE.LAYOUT.TERMINAL_ORIGIN
    harbor.camera.position = origin + eye
    harbor.camera.look_at(origin + target)


func run(preview: Node, benchmark: bool) -> void:
    host = preview
    harbor = host.harbor
    life = harbor.coast.life
    harbor.capture_lock = true
    harbor.camera.leave_inspection()
    harbor.camera.projection = Camera3D.PROJECTION_PERSPECTIVE
    harbor.camera.fov = 42
    for building in harbor.coast.buildings:
        building.get_node("AreaLabel").hide()
    if benchmark:
        await performance_review()
        return
    life.set_mode("live")
    var poses: Array[Dictionary] = []
    for t in [0.0, 2.0, 4.5, 7.5, 10.5, 12.0]:
        harbor.time = t
        harbor.sync_water()
        var fall: Node3D = life.rigs.Fall
        var load_: Node3D = life.rigs.Load
        var rope_end: Vector3 = fall.to_global(Vector3(0, -2.56, 0))
        if not verify(rope_end.distance_to(load_.global_position) < .001, "hoist rope stays attached to the moving hook"):
            return
        if not verify(life.height >= 0.0 and life.height <= .241, "load keeps its platform clearance"):
            return
        poses.append(life.snapshot())
    if not verify(poses[0].load_position.is_equal_approx(poses[-1].load_position), "hoist cycle closes without a jump"):
        return
    if not verify(not poses[0].drum_rotation.is_equal_approx(poses[2].drum_rotation), "drum and crank turn while lifting"):
        return
    harbor.time = 2.0
    harbor.sync_water()
    var held: Transform3D = life.rigs.Load.transform
    var held_energy: float = life.lights[0].light_energy
    for i in 8:
        await host.get_tree().process_frame
    if not verify(held.is_equal_approx(life.rigs.Load.transform) and is_equal_approx(held_energy, life.lights[0].light_energy), "pause freezes machinery and lamp flicker"):
        return
    # A complete 12-second hoist cycle, using the real runtime controller.
    view(Vector3(-12.3, 4.0, 6.4), Vector3(-7.4, 2.0, .45))
    for i in 72:
        harbor.time = float(i) / 6.0
        if not await host.capture("life_crane_%03d" % i, false, 2):
            return
    # Same normal daylight: flames and wind must read at the actual scene scale.
    view(Vector3(1.6, 3.1, 6.7), Vector3(3.1, 3.7, .8))
    for i in 36:
        harbor.time = float(i) / 12.0
        if not await host.capture("life_flags_lamps_%03d" % i, false, 2):
            return
    host.finish({"kind": "terminal live motion", "checks": checks, "poses": poses,
        "crane_frames": 72, "crane_fps": 6, "cloth_lamp_frames": 36, "cloth_lamp_fps": 12,
        "lighting": "normal fixed daylight", "audio": "motion-linked spatial winch creak, muted during deterministic capture"})


func performance_review() -> void:
    DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
    var viewport: RID = harbor.get_viewport().get_viewport_rid()
    RenderingServer.viewport_set_measure_render_time(viewport, true)
    var profiler := load("res://demo/tropical_harbor_3d/tools/water_profile.gd").new() as RefCounted
    profiler.host = host
    profiler.harbor = harbor
    var results: Array[Dictionary] = []
    var shots := [
        {"name": "close", "eye": Vector3(-8.4, 3.5, 9.5), "target": Vector3(-3.6, 1.4, 2.2)},
        {"name": "whole", "eye": Vector3(-15, 15, 22), "target": Vector3(0, 3.5, 0)}]
    # Alternate ordering to reduce warmup/clock bias; all versions use the same asset.
    for shot in shots:
        view(shot.eye, shot.target)
        for round_ in 2:
            var modes := ["static", "frozen", "live"] if round_ == 0 else ["live", "frozen", "static"]
            for mode_ in modes:
                life.set_mode(mode_)
                harbor.time = 1.7
                harbor.sync_water()
                if mode_ == "live":
                    benchmark_start = Time.get_ticks_usec()
                    host.get_tree().process_frame.connect(_advance_life)
                var timing: Dictionary = await profiler.measure(viewport, 2.0, .30)
                if mode_ == "live":
                    host.get_tree().process_frame.disconnect(_advance_life)
                life.time_override = -1.0
                timing["view"] = shot.name
                timing["mode"] = mode_
                timing["round"] = round_
                results.append(timing)
        await host.capture("life_perf_" + shot.name, false, 2)
    life.set_mode("live")
    host.finish({"kind": "paired terminal animation cost", "timing": results,
        "resolution": [harbor.get_window().size.x, harbor.get_window().size.y],
        "vsync": "disabled", "samples_per_mode_view": 2, "seconds_per_sample": 2.0,
        "static": "same current meshes; standard cloth, fixed machinery, fire and local lights hidden",
        "frozen": "all effects visible but animation time fixed",
        "live": "all effects visible and moving; water, ships and main scene time stay fixed",
        "note": "Short same-session comparison; does not measure the older merged asset or future workers."})


func _advance_life() -> void:
    life.time_override = 1.7 + float(Time.get_ticks_usec() - benchmark_start) / 1000000.0
