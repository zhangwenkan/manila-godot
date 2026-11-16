extends RefCounted

const ROUTE = preload("res://demo/tropical_harbor_3d/fleet/harbor_route.gd")
var host: Node
var harbor: Node3D
var checks := 0
var observations: Array[Dictionary] = []


func verify(ok: bool, message: String) -> bool:
    checks += 1
    if not ok:
        push_error("LOCAL_VOYAGE: " + message)
        host.get_tree().quit(2)
    return ok


func fixture(progress: Array, subject: int = 1) -> void:
    harbor.sailing_ships.clear()
    harbor.sailing_targets.clear()
    harbor.pending_berths.clear()
    harbor.arrival_transition = false
    harbor.arrival_cover.color.a = 0
    harbor.state.start_voyage(["jade", "silk", "ginseng"], [3, 3, 3])
    for i in 3:
        harbor.state.ships[i].progress = progress[i]
        for j in mini(i + 1, harbor.state.ships[i].slots.size()):
            harbor.state.ships[i].slots[j].owner = (i + j) % 3
    harbor.camera.shot_indices.clear()
    harbor.camera.area_progress = -1
    harbor.camera.auto_subject = subject
    harbor.rebuild_ships()
    harbor.camera.auto_subject = subject
    harbor.camera.update_view(harbor.ships, 0, true)


func bounds(ship: Node3D) -> Rect2:
    var min_ := Vector2(INF, INF)
    var max_ := Vector2(-INF, -INF)
    for point in ship.envelope_points():
        var projected: Vector2 = harbor.camera.unproject_position(point)
        min_ = min_.min(projected)
        max_ = max_.max(projected)
    return Rect2(min_, max_ - min_)


func record(label: String, subjects: Array) -> bool:
    var screen := host.get_viewport().get_visible_rect()
    var report: Array = []
    for i in subjects:
        var ship: Node3D = harbor.ships[i]
        var rect := bounds(ship)
        if not verify(screen.grow(-25).encloses(rect), label + ": current boat fully visible " + str(rect)):
            return false
        if not verify(maxf(rect.size.x, rect.size.y) >= screen.size.y * .16, label + ": boat remains readable within the waterfront composition"):
            return false
        var ray := PhysicsRayQueryParameters3D.create(harbor.camera.position, ship.position + Vector3(0, .5, 0), 4)
        var hit := harbor.get_world_3d().direct_space_state.intersect_ray(ray)
        if not verify(hit.is_empty(), label + ": current boat not blocked by environment " + str(hit)):
            return false
        report.append({"ship": i, "rect": str(rect)})
    observations.append({"view": label, "camera": str(harbor.camera.position), "rotation": str(harbor.camera.rotation_degrees), "subjects": report})
    if label in ["06_initial", "02_coastal_work", "04_insurance"]:
        var yard := label != "04_insurance"
        var building := harbor.blockout.get_node("RepairYard" if yard else "InsuranceOffice") as Node3D
        var features := [Vector3(0, 1.8, 1.0), Vector3(-2.8, 1.05, 3.0), Vector3(2.8, 1.05, 3.0), Vector3(0, 4.0, -2.1)] if yard else [Vector3(-2.85, 1.4, -1), Vector3(-2.85, 1.4, 1), Vector3(-2.4, 2.7, 0), Vector3(-2.8, .7, 0)]
        var visible_features := 0
        for point in features:
            if screen.grow(-40).has_point(harbor.camera.unproject_position(building.to_global(point))):
                visible_features += 1
        if not verify(visible_features >= 3, label + ": waterfront front and work area remain in frame"):
            return false
        var front: Vector3 = building.global_basis * (Vector3.BACK if yard else Vector3.LEFT)
        if not verify(front.dot(harbor.camera.position - building.position) > 0, label + ": camera is on the front side of the waterfront building"):
            return false
        if label == "06_initial":
            var to_eye: Vector3 = harbor.camera.position - building.position
            to_eye.y = 0
            if not verify(front.normalized().dot(to_eye.normalized()) >= .5,
                    "initial work opening is seen from its front quarter, not grazing its side"):
                return false
    return true


func run(preview: Node) -> void:
    host = preview
    harbor = host.harbor
    harbor.configure_art_shadows()
    harbor.capture_lock = true
    harbor.camera_override = false
    harbor.coast.set_observing(true)
    harbor.blockout.set_labels(false)
    if "--coastal-composition-study" in OS.get_cmdline_user_args():
        await composition_study()
        return
    if "--local-voyage-motion" in OS.get_cmdline_user_args() or "--layout-motion" in OS.get_cmdline_user_args():
        await motion()
        return
    for stage in [{"id": "01_departure", "p": 0}, {"id": "02_coastal_work", "p": 5.6},
            {"id": "03_lighthouse", "p": 7.5}, {"id": "04_insurance", "p": 10.0}, {"id": "05_pirates", "p": 12.8}]:
        fixture([stage.p, stage.p, stage.p])
        await host.get_tree().physics_frame
        await host.capture(stage.id)
        if not record(stage.id, harbor.camera.framed_indices):
            return
        if stage.p == 0:
            var terminal := harbor.get_node("CoastalTown/ArrivalTerminal") as Node3D
            var terminal_rect := Rect2()
            var first := true
            for mesh in terminal.find_children("*", "MeshInstance3D", true, false):
                if mesh.name == "ReflectProxy":
                    continue
                for corner in 8:
                    var p: Vector3 = mesh.global_transform * mesh.mesh.get_aabb().get_endpoint(corner)
                    var projected: Vector2 = harbor.camera.unproject_position(p)
                    terminal_rect = Rect2(projected, Vector2.ZERO) if first else terminal_rect.expand(projected)
                    first = false
            if not verify(not host.get_viewport().get_visible_rect().intersects(terminal_rect), "departure excludes the terminal building"):
                return
    fixture([3, 3, 3])
    await host.capture("06_initial")
    if not record("06_initial", harbor.camera.framed_indices):
        return
    harbor.ui.visible = true
    harbor.blockout.set_labels(true)
    await host.capture("07_interface")
    if "--local-voyage-frames" in OS.get_cmdline_user_args():
        host.finish({"kind": "close waterfront composition", "checks": checks, "observations": observations, "visual_accepted": false})
        return
    if not await route_clearance():
        return
    if not await camera_route_checks():
        return
    if not await gameplay_checks():
        return
    if not lane_separation():
        return
    fixture([5, 5, 5])
    harbor.select_ship(2)
    harbor.camera.update_view(harbor.ships, 0, true)
    await host.get_tree().physics_frame
    await host.capture("09_selected_coast")
    if not record("09_selected_coast", [2]):
        return
    var slot: Vector3 = harbor.ships[2].slot_roots[0].global_position + Vector3(0, .15, 0)
    var picked: Dictionary = harbor.pick(harbor.camera.unproject_position(slot))
    if not verify(picked.get("ship_id", -1) == 2, "local camera retains ship and crew picking"):
        return
    var basis_before: Basis = harbor.camera.basis
    harbor.camera.orbit(Vector2(250, 150))
    harbor.camera.zoom_inspection(3)
    harbor.camera.update_view(harbor.ships, 0, true)
    if not verify(basis_before.is_equal_approx(harbor.camera.basis), "player cannot freely orbit the directed camera"):
        return
    var timing := await measure_local_view()
    host.finish({"kind": "local voyage camera and route study", "checks": checks, "observations": observations, "timing": timing, "visual_accepted": false})


func composition_study() -> void:
    # Same world, boat state, daylight and resolution; only the viewing pose varies.
    fixture([3, 3, 3])
    await host.capture("00_current")
    var poses := [
        {"id": "17_forward", "aim": Vector3(3, 1.5, -8), "eye": Vector3(2, 16, 21), "fov": 48.0},
        {"id": "18_seaward", "aim": Vector3(6, 1.5, -8), "eye": Vector3(-10, 16, 19), "fov": 48.0},
        {"id": "19_front", "aim": Vector3(7, 1.5, -7), "eye": Vector3(-14, 16, 17), "fov": 48.0}
    ]
    var study: Array = []
    harbor.camera_override = true
    for pose in poses:
        var target: Vector3 = ROUTE.center(3) + pose.aim
        harbor.camera.position = target + pose.eye
        harbor.camera.look_at(target)
        harbor.camera.fov = pose.fov
        await host.capture(pose.id)
        study.append({"id": pose.id, "eye": str(harbor.camera.position), "target": str(target),
            "fov": pose.fov, "boats": [str(bounds(harbor.ships[0])), str(bounds(harbor.ships[1])), str(bounds(harbor.ships[2]))]})
    host.finish({"kind": "waterfront composition candidates", "candidates": study, "visual_accepted": false})


func measure_local_view() -> Dictionary:
    fixture([7.5, 7.5, 7.5])
    harbor.paused = false
    harbor.capture_lock = false
    var samples: Array[float] = []
    var focused := 0
    var start := Time.get_ticks_usec()
    var previous := start
    while Time.get_ticks_usec() - start < 5000000:
        await host.get_tree().process_frame
        var now := Time.get_ticks_usec()
        samples.append((now - previous) / 1000.0)
        previous = now
        if harbor.get_window().has_focus():
            focused += 1
    harbor.capture_lock = true
    samples.sort()
    var total := 0.0
    for value in samples:
        total += value
    return {"frames": samples.size(), "wall_seconds": (previous - start) / 1000000.0,
        "mean_ms": total / samples.size(), "p95_ms": samples[int(samples.size() * .95)],
        "focus_fraction": focused / float(samples.size()), "view": "local lighthouse", "resolution": str(host.get_viewport().get_visible_rect().size)}


func route_clearance() -> bool:
    var shape := BoxShape3D.new()
    shape.size = Vector3(2.0, .9, 4.9)
    var query := PhysicsShapeQueryParameters3D.new()
    query.shape = shape
    query.collision_mask = 4
    query.margin = .06
    for lane in 3:
        for step in 264:
            var progress := minf(step * .05, ROUTE.ENTRY)
            var at := ROUTE.point(lane, progress) + Vector3(0, .25, 0)
            query.transform = Transform3D(Basis(Vector3.UP, ROUTE.heading(lane, progress)), at)
            var hit := harbor.get_world_3d().direct_space_state.intersect_shape(query, 2)
            var hit_paths: Array[String] = []
            for contact in hit:
                hit_paths.append(str(contact.collider.get_path()))
            if not verify(hit.is_empty(), "swept hull clearance lane %d at %.2f: %s" % [lane, progress, hit_paths]):
                return false
    return true


func hull_polygon(lane: int, progress: float) -> PackedVector2Array:
    var polygon := PackedVector2Array()
    var basis_ := Basis(Vector3.UP, ROUTE.heading(lane, progress))
    for corner in [Vector3(-1.05, 0, -2.55), Vector3(1.05, 0, -2.55), Vector3(1.05, 0, 2.55), Vector3(-1.05, 0, 2.55)]:
        var at: Vector3 = ROUTE.point(lane, progress) + basis_ * corner
        polygon.append(Vector2(at.x, at.z))
    return polygon


func lane_separation() -> bool:
    for lane in 2:
        for step in 132:
            var progress := minf(step * .1, ROUTE.ENTRY)
            var hull := hull_polygon(lane, progress)
            for other in range(lane + 1, 3):
                for relative in range(-10, 11):
                    var other_progress := clampf(progress + relative * .1, 0, ROUTE.ENTRY)
                    if not verify(Geometry2D.intersect_polygons(hull, hull_polygon(other, other_progress)).is_empty(),
                            "independent lane hulls remain separated at different progress"):
                        return false
    return true


func camera_route_checks() -> bool:
    fixture([0, 0, 0])
    for step in 66:
        var progress := step * .2
        for ship in harbor.ships:
            ship.place_on_route(progress)
        for primary in 3:
            harbor.camera.auto_subject = primary
            harbor.camera.update_view(harbor.ships, 0, true)
            for i in harbor.camera.framed_indices:
                var ship: Node3D = harbor.ships[i]
                if not verify(host.get_viewport().get_visible_rect().grow(-20).encloses(bounds(ship)), "continuous composition at %.1f lane %d" % [progress, i]):
                    return false
                for point in [Vector3(0, .5, -1.8), Vector3(0, .5, 0), Vector3(0, .5, 1.8)]:
                    var ray := PhysicsRayQueryParameters3D.create(harbor.camera.position, ship.to_global(point), 4)
                    var hit := harbor.get_world_3d().direct_space_state.intersect_ray(ray)
                    if not verify(hit.is_empty(), "boat visibility at %.1f lane %d primary %d %s" % [progress, i, primary, hit]):
                        return false
    return true


func simulate(delta: float) -> void:
    harbor.capture_lock = false
    harbor._process(delta)
    harbor.capture_lock = true


func gameplay_checks() -> bool:
    harbor.ui.visible = true
    harbor.blockout.set_labels(false)
    for scenario in [
            {"name": "unequal_dice", "p": [3, 3, 3], "dice": [1, 6, 3], "subject": 1},
            {"name": "wide_gap", "p": [0, 6, 12], "dice": [1, 6, 2], "subject": 1},
            {"name": "right_lane_passage", "p": [4, 4, 4], "dice": [6, 1, 6], "subject": 2},
            {"name": "left_lane_passage", "p": [4, 4, 4], "dice": [6, 1, 2], "subject": 0},
            {"name": "catch_up", "p": [9, 5, 2], "dice": [1, 6, 6], "subject": 0},
            {"name": "right_arrives_first", "p": [0, 3, 13], "dice": [6, 1, 1], "subject": 1},
            {"name": "all_arrive", "p": [13, 13, 13], "dice": [1, 6, 3], "subject": 2}]:
        fixture(scenario.p, scenario.subject)
        harbor.paused = false
        if not verify(harbor.state.roll(scenario.dice).is_empty(), "simultaneous dice accepted"):
            return false
        harbor._start_parallel_sailing()
        var expected: Array = harbor.state.ships.duplicate(true)
        var seen: Array[int] = []
        var pause_checked := false
        var opaque_jump := false
        var first_start := -1
        var first_finish := -1
        var moving_capture := false
        var anchor: int = harbor.camera.auto_subject
        var initial_fov: float = harbor.camera.local_fov
        for step in 800:
            var before: Array[Vector3] = []
            for ship in harbor.ships:
                before.append(ship.position)
            simulate(.025)
            var moving_count := 0
            for ship in harbor.ships:
                moving_count += int(ship.route_travelling)
            if moving_count > 0:
                if first_start < 0:
                    first_start = step
                if not verify(moving_count == 3, scenario.name + ": every unberthed boat moves in the same interval"):
                    return false
                if not verify(harbor.camera.auto_subject == anchor and harbor.camera.local_fov == initial_fov,
                        "large ship gaps never change the shot anchor or zoom out to the map"):
                    return false
                for i in 3:
                    var ship: Node3D = harbor.ships[i]
                    if not i in seen:
                        seen.append(i)
                    if not verify(is_equal_approx(ship.route_elapsed, harbor.ships[0].route_elapsed)
                            and is_equal_approx(ship.route_duration, harbor.ships[0].route_duration),
                            "all three boat animation clocks are synchronized"):
                        return false
                    if step % 8 == 0:
                        if not verify(is_equal_approx(harbor.ui.ship_progress[i].value, minf(ship.route_progress, 13.0)),
                                "all three progress tracks update from displayed movement, including offscreen boats"):
                            return false
                if step % 8 == 0:
                    var ship: Node3D = harbor.ships[anchor]
                    if not verify(host.get_viewport().get_visible_rect().grow(-20).encloses(bounds(ship)),
                            scenario.name + ": current subject remains in close view"):
                        return false
                    var ray := PhysicsRayQueryParameters3D.create(harbor.camera.position, ship.position + Vector3(0, .5, 0), 4)
                    if not verify(harbor.get_world_3d().direct_space_state.intersect_ray(ray).is_empty(),
                            scenario.name + ": current subject not hidden by scenery"):
                        return false
                if not moving_capture and harbor.ships[0].route_elapsed > 1.5 and scenario.name in ["unequal_dice", "wide_gap"]:
                    await host.capture("moving_" + scenario.name)
                    moving_capture = true
            elif first_start >= 0 and first_finish < 0:
                first_finish = step
            for i in 3:
                if harbor.ships[i].position.distance_to(before[i]) > 3.0:
                    opaque_jump = true
                    if not verify(harbor.arrival_cover.color.a >= .99, "berth relocation is completely covered"):
                        return false
            if not pause_checked and moving_count == 3 and step > 70:
                var time_before: float = harbor.time
                var hold_before: float = harbor.shot_hold
                var elapsed_before: float = harbor.ships[0].route_elapsed
                harbor.ui.pause_button.pressed.emit()
                simulate(.4)
                if not verify(harbor.time == time_before and harbor.shot_hold == hold_before
                        and harbor.ships[0].route_elapsed == elapsed_before and harbor.ships[2].route_elapsed == elapsed_before,
                        "pause freezes every ship and the shared sailing interval"):
                    return false
                harbor.ui.pause_button.pressed.emit()
                pause_checked = true
            if not harbor.is_moving():
                break
        if not verify(not harbor.is_moving() and seen.size() == 3 and first_finish > first_start,
                "one simultaneous round starts and completes all three ships"):
            return false
        if not verify(harbor.state.ships == expected and harbor.state.rolls == 1, "presentation never advances rules a second time"):
            return false
        for i in 3:
            var at: Vector3 = harbor.ships[i].position
            at.y = 0
            if not verify(at.distance_to(harbor.state.world_position(harbor.state.ships[i])) < .01, "visual position agrees with rule progress or berth"):
                return false
        for settle in 120:
            simulate(.025)
        await host.capture("runtime_" + scenario.name)
        if scenario.name == "right_arrives_first":
            if not verify(opaque_jump and harbor.state.ships[2].berth == 0, "rightmost first arrival occupies actual berth A"):
                return false
            harbor.ui.roll_button.pressed.emit()
            if not verify(not 2 in harbor.sailing_targets, "later dice never move an already berthed ship"):
                return false
            for step in 800:
                simulate(.025)
                if not verify(not harbor.ships[2].route_travelling and harbor.ships[2].route_progress >= 14,
                        "berthed boat stays at the dock while the remaining boats sail together"):
                    return false
                if not harbor.is_moving():
                    break
    harbor.ui.visible = false
    fixture([7, 7, 7])
    harbor.camera.focus_ship = 2
    harbor.camera.update_view(harbor.ships, 0, true)
    var state_before: Array = harbor.state.ships.duplicate(true)
    harbor.ships[2].sail_route(5, 2.5)
    for step in 120:
        harbor.time += .025
        harbor.ships[2].advance(.025, harbor.time)
        harbor.camera.update_view(harbor.ships, .025)
    if not verify(absf(harbor.ships[2].route_progress - 5.0) < .001 and state_before == harbor.state.ships,
            "reverse travel stays on its own curve and presentation does not implement pilot rules"):
        return false
    await host.capture("08_reverse_route")
    return true


func motion() -> void:
    # Two consecutive real rounds: unequal dice from a valid start, then an
    # already spread fleet. All world movement and UI use the runtime update.
    fixture([3, 3, 3])
    harbor.ui.visible = true
    harbor.paused = false
    var frames := 0
    var rounds := [[1, 6, 3], [1, 3, 6]]
    var snapshots: Array = []
    for dice in rounds:
        harbor.state.roll(dice)
        harbor._start_parallel_sailing()
        var quiet_frames := 0
        for frame in 160:
            for step in 2:
                simulate(1.0 / 16.0)
            await host.capture("voyage_%03d" % frames, false, 2)
            snapshots.append({"frame": frames, "progress": [harbor.ships[0].route_progress, harbor.ships[1].route_progress, harbor.ships[2].route_progress],
                "moving": [harbor.ships[0].route_travelling, harbor.ships[1].route_travelling, harbor.ships[2].route_travelling],
                "subject": harbor.camera.auto_subject})
            frames += 1
            quiet_frames = quiet_frames + 1 if not harbor.is_moving() else 0
            if quiet_frames >= 12:
                break
        if not verify(not harbor.is_moving(), "recorded simultaneous round settles completely"):
            return
    host.finish({"kind": "simultaneous unequal dice and persistent local view", "frames_per_second": 8,
        "duration": frames / 8.0, "rounds": rounds, "timeline": snapshots, "visual_accepted": false})
