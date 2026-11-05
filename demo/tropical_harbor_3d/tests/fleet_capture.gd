extends Node

const STATE = preload("res://demo/tropical_harbor_3d/fleet/fleet_state.gd")
var harbor: Node3D
var output := ""
var checks := 0
var captures: Array[Dictionary] = []
var timing: Dictionary = {}


func verify(condition: bool, message: String) -> bool:
    checks += 1
    if not condition:
        push_error("FLEET_FAIL: " + message)
        get_tree().quit(2)
    return condition


func run(scene: Node3D) -> void:
    harbor = scene
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):
            output = arg.trim_prefix("--output=")
    if not verify(DisplayServer.get_name() != "headless", "graphical renderer required"):
        return
    if not verify(not output.is_empty() and not DirAccess.dir_exists_absolute(output), "new output directory required"):
        return
    if not verify(DirAccess.make_dir_recursive_absolute(output) == OK, "cannot create output directory"):
        return
    await wait(1.2)
    await fixture(["jade", "silk", "ginseng"], [3, 3, 3])
    if not await capture("01_parallel_overview"):
        return
    if not check_overview():
        return
    if not check_reflection_alignment():
        return
    if not await click_ship(0):
        return
    if not await click_slot(3):
        return
    if not verify(harbor.ui.confirm.disabled, "expensive seat must be unavailable first"):
        return
    for slot in [0, 1, 3, 2]:
        if not await click_slot(slot):
            return
        if not await click_button(harbor.ui.confirm):
            return
        if not verify(harbor.state.ships[0].slots[slot].owner >= 0, "dispatch did not occupy seat"):
            return
    if not verify(harbor.state.ships[0].slots[0].owner == 0, "player zero lost"):
        return
    if not check_crew_space():
        return
    if not await capture("02_jade_full_crew"):
        return
    timing["close"] = await measure(5.0)
    if not await click_button(harbor.ui.overview):
        return
    await fixture(["jade", "silk", "ginseng"], [0, 7, 14], true)
    if not check_overview():
        return
    if not await capture("03_extreme_overview"):
        return
    timing["overview"] = await measure(5.0)
    for i in 3:
        if not await click_button(harbor.ui.ship_buttons[i]):
            return
        if not verify(harbor.selected == i and harbor.camera.focus_ship == i, "remote ship switch"):
            return
        if not await capture("cargo_" + str(harbor.state.ships[i].cargo_id)):
            return
    if not await click_slot(0):
        return
    if not verify(harbor.ui.confirm.disabled, "arrived ship must reject crew"):
        return
    await fixture(["nutmeg", "jade", "silk"], [5, 4, 0], true)
    if not await click_ship(0):
        return
    if not await capture("cargo_nutmeg"):
        return
    # Resize the actual window, then click through freshly laid out UI and 3D targets.
    var original_size: Vector2i = harbor.get_window().size
    harbor.get_window().size = Vector2i(1000, 625)
    await wait(1.0)
    if not await click_button(harbor.ui.ship_buttons[1]):
        return
    if not await click_slot(2):
        return
    if not check_reflection_alignment():
        return
    harbor.get_window().size = original_size
    await wait(1.0)
    # Actual dice button, independent travel, pause/resume, then fresh hit targets.
    await fixture(["jade", "silk", "ginseng"], [0, 4, 5])
    harbor.rng.seed = 4421
    if not await click_button(harbor.ui.pause_button):
        return
    if not await click_button(harbor.ui.roll_button):
        return
    if not verify(harbor.state.rolls == 1 and harbor.is_moving(), "dice input must start travel"):
        return
    await wait(0.8)
    if not await capture("04_three_wakes"):
        return
    if not await click_button(harbor.ui.pause_button):
        return
    var frozen := snapshot()
    await wait(0.25)
    if not verify(snapshot() == frozen, "pause must freeze water and all boats"):
        return
    if not await click_button(harbor.ui.pause_button):
        return
    var deadline := Time.get_ticks_msec() + 15000
    while harbor.is_moving() and Time.get_ticks_msec() < deadline:
        await get_tree().process_frame
    if not verify(not harbor.is_moving(), "travel did not end"):
        return
    await wait(1.4)
    for ship in harbor.ships:
        if not verify(ship.wake <= 0.01, "stopped wake must decay"):
            return
    if not await click_ship(0):
        return
    if not await click_slot(0):
        return
    if not await click_button(harbor.ui.confirm):
        return
    if not await capture("05_moved_ship_dispatch"):
        return
    for expected_roll in [2, 3]:
        if not await click_button(harbor.ui.roll_button):
            return
        var end := Time.get_ticks_msec() + 15000
        while harbor.is_moving() and Time.get_ticks_msec() < end:
            await get_tree().process_frame
        if not verify(not harbor.is_moving() and harbor.state.rolls == expected_roll, "complete independent voyage roll"):
            return
    if not await click_button(harbor.ui.overview):
        return
    if not check_overview():
        return
    if not await capture("11_completed_voyage"):
        return
    var prior_voyage: int = harbor.state.voyage
    if not await click_button(harbor.ui.restart):
        return
    var expected_cargo: String = STATE.CARGO.keys()[prior_voyage % 4]
    if not verify(harbor.selected == -1 and harbor.state.rolls == 0 and harbor.state.ships[0].cargo_id == expected_cargo, "new voyage refreshes cargo and selection"):
        return
    if not await capture("12_new_cargo_voyage"):
        return
    # Only one boat wakes: one material must not leak a strength into its neighbors.
    await fixture(["jade", "silk", "ginseng"], [3, 3, 3])
    harbor.paused = false
    harbor.ships[1].travel_to(harbor.ships[1].position + Vector3(0, 0, -4), false)
    await wait(0.6)
    if not verify(harbor.ships[1].wake > 0.2 and harbor.ships[0].wake == 0 and harbor.ships[2].wake == 0, "independent wake strengths"):
        return
    if not await capture("06_single_wake"):
        return
    await fixture(["jade", "silk", "ginseng"], [3, 3, 3])
    harbor.select_ship(0)
    harbor.ships[0].set_selected(false)
    harbor.ships[0].cargo_root.visible = false
    harbor.ui.visible = false
    harbor.camera_override = true
    harbor.camera.position = harbor.ships[0].position + Vector3(6, 5, -7)
    harbor.camera.look_at(harbor.ships[0].position + Vector3(0, 0.28, 0))
    harbor.camera.frame_points(harbor.ships[0].envelope_points(), 0, true, 70)
    if not await capture("13_open_hull_structure"):
        return
    harbor.ships[0].cargo_root.visible = true
    harbor.ui.visible = true
    harbor.overview()
    harbor.camera.update_view(harbor.ships, 0, true)
    harbor.camera_override = true
    var points: Array[Vector3] = [Vector3(2.2, -1, 5.8), Vector3(11.4, 1.6, 12.8)]
    harbor.camera.frame_points(points, 0, true, 70)
    if not await capture("07_timber_and_broken_pier"):
        return
    # Check the active water: paused frames must hold, and a wake must only
    # change water around its boat. The retired study shader is not a baseline.
    harbor.overview()
    harbor.camera.update_view(harbor.ships, 0, true)
    harbor.camera_override = true
    harbor.ui.visible = false
    if not await capture("08_fleet_water_no_wake"):
        return
    if not await capture("09_fleet_water_paused_repeat"):
        return
    harbor.ships[1].wake = 1.0
    if not await capture("10_fleet_water_single_wake"):
        return
    harbor.ships[1].wake = 0.0
    if not await capture("14_fleet_water_wake_cleared"):
        return
    # A generous screen-space bound around the chosen boat, bow and trailing water.
    var wake_min := Vector2(INF, INF)
    var wake_max := Vector2(-INF, -INF)
    for x in [-5.0, 5.0]:
        for z in [-3.5, 12.0]:
            var point: Vector2 = harbor.camera.unproject_position(
                harbor.ships[1].to_global(Vector3(x, 0.0, z)))
            wake_min = wake_min.min(point)
            wake_max = wake_max.max(point)
    var result := {"checks": checks, "frames": captures, "timing": timing,
        "renderer": RenderingServer.get_current_rendering_method(), "resolution": [original_size.x, original_size.y],
        "contact_count": harbor.environment.water_material.get_shader_parameter("contact_count"),
        "wake_bounds": [wake_min.x - 4, wake_min.y - 4, wake_max.x + 4, wake_max.y + 4],
        "scope": "fleet spatial, interaction and active-water regression, not complete game rules",
        "visual_acceptance": false, "pressure_fixture": [0, 7, 14]}
    var file := FileAccess.open(output + "/result.json", FileAccess.WRITE)
    if not verify(file != null, "result file"):
        return
    result["checks"] = checks
    file.store_string(JSON.stringify(result, "  "))
    file.close()
    print("FLEET_CAPTURE_PASS checks=", checks, " output=", output)
    get_tree().quit()


func fixture(cargos: Array, progress: Array, full: bool = false) -> void:
    harbor.paused = true
    harbor.time = 1.7
    for player in harbor.state.players:
        player.cash = 30
    harbor.state.start_voyage(cargos, [3, 3, 3])
    var berth := 0
    for i in 3:
        var ship: Dictionary = harbor.state.ships[i]
        ship.progress = progress[i]
        ship.arrived = progress[i] > 13
        if ship.arrived:
            ship.berth = berth
            berth += 1
        if full:
            for j in ship.slots.size():
                ship.slots[j].owner = j % 3
                harbor.state.players[j % 3].cash -= ship.slots[j].cost
                harbor.state.players[j % 3].available -= 1
    harbor.rebuild_ships()
    await get_tree().physics_frame
    await get_tree().physics_frame
    await wait(0.15)


func wait(seconds: float) -> void:
    await get_tree().create_timer(seconds).timeout


func snapshot() -> Array:
    var result: Array = [harbor.time]
    for ship in harbor.ships:
        result.append(ship.transform)
        result.append(ship.wake)
    return result


func capture(name_: String) -> bool:
    var before := snapshot()
    var camera_transform: Transform3D = harbor.camera.transform
    var size_: float = harbor.camera.size
    harbor.capture_lock = true
    harbor.sync_water()
    # Let render-thread material updates settle without advancing the simulation.
    for i in 3:
        await get_tree().process_frame
    while true:
        while DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_MINIMIZED:
            await get_tree().process_frame
        await RenderingServer.frame_post_draw
        if DisplayServer.window_get_mode() != DisplayServer.WINDOW_MODE_MINIMIZED:
            break
    var image := get_viewport().get_texture().get_image()
    var saved := image != null and not image.is_empty() and image.save_png(output + "/" + name_ + ".png") == OK
    var frozen: bool = before == snapshot() and camera_transform == harbor.camera.transform and size_ == harbor.camera.size
    harbor.capture_lock = false
    if not verify(saved and frozen, "frozen capture " + name_):
        return false
    captures.append({"file": name_ + ".png", "frozen": frozen, "width": image.get_width(), "height": image.get_height()})
    return true


func click(point: Vector2) -> void:
    var motion := InputEventMouseMotion.new()
    motion.position = point
    get_viewport().push_input(motion, true)
    for down in [true, false]:
        var event := InputEventMouseButton.new()
        event.position = point
        event.button_index = MOUSE_BUTTON_LEFT
        event.pressed = down
        get_viewport().push_input(event, true)
    await get_tree().process_frame


func click_button(button: Button) -> bool:
    await get_tree().process_frame
    if not verify(button.is_visible_in_tree() and not button.disabled, "button unavailable: " + button.text):
        return false
    var clicks := [0]
    var counted := func() -> void: clicks[0] += 1
    button.pressed.connect(counted)
    await click(button.get_global_rect().get_center())
    button.pressed.disconnect(counted)
    await wait(0.65)
    return verify(clicks[0] == 1, "real UI input: " + button.text)


func click_ship(index: int) -> bool:
    if harbor.selected != -1:
        if not await click_button(harbor.ui.overview):
            return false
    var point: Vector2 = harbor.camera.unproject_position(harbor.ships[index].to_global(Vector3(0, 0.55, -1.55)))
    var hit: Dictionary = harbor.pick(point)
    if not verify(not hit.is_empty() and hit.ship_id == index, "ship must have visible clickable hull"):
        return false
    await click(point)
    await wait(0.9)
    return verify(harbor.selected == index, "3D ship click")


func click_slot(index: int) -> bool:
    await get_tree().physics_frame
    var ship: Node3D = harbor.ships[harbor.selected]
    var point: Vector2 = harbor.camera.unproject_position(ship.slot_areas[index].global_position + Vector3(0, 0.20, 0))
    var hit: Dictionary = harbor.pick(point)
    if not verify(not hit.is_empty() and hit.ship_id == harbor.selected and hit.slot_id == index, "moving 3D slot hit: " + str(index)):
        return false
    await click(point)
    return verify(harbor.ui.selected_slot == index, "slot click must select before dispatch")


func check_overview() -> bool:
    var visible := get_viewport().get_visible_rect().grow(-20)
    for ship in harbor.ships:
        for point in ship.envelope_points():
            if not verify(visible.has_point(harbor.camera.unproject_position(point)), "ship clipped in overview"):
                return false
    return true


func check_reflection_alignment() -> bool:
    # A point reflected below y=0 must land at the same screen position as the
    # corresponding point in the mirror camera after the horizontal UV flip.
    # Check both camera types and call again after changing the window aspect.
    var camera: Camera3D = harbor.camera
    var original_projection := camera.projection
    var screen: Vector2 = camera.get_viewport().get_visible_rect().size
    for projection in [Camera3D.PROJECTION_ORTHOGONAL, Camera3D.PROJECTION_PERSPECTIVE]:
        camera.projection = projection
        harbor.reflection.sync()
        var mirror: Camera3D = harbor.reflection.camera
        var mirror_size := Vector2(harbor.reflection.viewport.size)
        for ship in harbor.ships:
            var above: Vector3 = ship.global_position + Vector3(0.6, 0.9, -0.8)
            var below := Vector3(above.x, -above.y, above.z)
            var expected: Vector2 = camera.unproject_position(below)
            var uv := mirror.unproject_position(above) / mirror_size
            var actual := Vector2(1.0 - uv.x, uv.y) * screen
            if not verify(actual.distance_to(expected) < 2.0, "object reflection alignment after projection/aspect change"):
                camera.projection = original_projection
                harbor.reflection.sync()
                return false
    camera.projection = original_projection
    harbor.reflection.sync()
    return true


func check_crew_space() -> bool:
    var pawn_size: Vector3 = harbor.SHIP.PAWN_SIZE
    for ship in harbor.ships:
        for i in ship.slot_roots.size():
            var a: Vector3 = ship.slot_roots[i].position
            if not verify(is_equal_approx(a.y, ship.DECK_HEIGHT), "crew feet must match the new floor"):
                return false
            for j in range(i + 1, ship.slot_roots.size()):
                var b: Vector3 = ship.slot_roots[j].position
                if not verify(absf(a.x - b.x) > pawn_size.x or absf(a.z - b.z) > pawn_size.z, "pawn envelopes overlap"):
                    return false
    return true


func measure(seconds: float) -> Dictionary:
    await get_tree().process_frame
    await get_tree().process_frame
    var start := Time.get_ticks_usec()
    var previous := start
    var drawn := Engine.get_frames_drawn()
    var samples: Array[float] = []
    var focused := 0
    var minimized := 0
    while Time.get_ticks_usec() - start < seconds * 1000000:
        await get_tree().process_frame
        var now := Time.get_ticks_usec()
        samples.append(float(now - previous) / 1000.0)
        previous = now
        focused += int(harbor.get_window().has_focus())
        minimized += int(DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_MINIMIZED)
    samples.sort()
    var elapsed := float(Time.get_ticks_usec() - start) / 1000000.0
    return {"wall_seconds": elapsed, "frames": samples.size(), "drawn_frames": Engine.get_frames_drawn() - drawn,
        "mean_ms": elapsed * 1000 / samples.size(), "p95_ms": samples[int(ceil(samples.size() * 0.95)) - 1],
        "max_ms": samples.back(), "focus_fraction": float(focused) / samples.size(), "minimized_frames": minimized}
