extends "res://demo/tropical_harbor_3d/tools/reference_terminal_review.gd"

# Bounded views of the authored island plus an explicit event-camera demonstration.
# Reuse current-terminal capture helpers; no historical terminal asset is loaded.
# Authored front points +X at yaw90, around (-17.5, 0, -14).
# Actual mesh bounds include any pier and wreckage that extends beyond the rock rim.
const FRONT_DIRECTION := Vector3(1, .56, 0)
const REFERENCE_DIRECTION := Vector3(22, 17, 21)
const OVERVIEW_DIRECTION := Vector3(-20, 25, 24)

var pirate_island: Node3D
var island_box := AABB()


func run(preview: Node) -> void:
    host = preview
    harbor = host.harbor
    harbor.capture_lock = true
    harbor.camera_override = true
    harbor.ui.visible = false
    if not verify(harbor.reference_art, "pirate review uses the current reference scene"):
        return
    if not verify(FRONT_DIRECTION.length_squared() > .1 and REFERENCE_DIRECTION.length_squared() > .1
            and OVERVIEW_DIRECTION.length_squared() > .1, "island inspection directions were confirmed"):
        return
    var islands: Array[Node3D] = []
    var terminals: Array[Node3D] = []
    for child in harbor.coast.root.get_children():
        if not child is Node3D:
            continue
        if child.get_meta("reference_asset", "") == "pirate_island":
            islands.append(child)
        if child.get_meta("reference_asset", "") == "terminal":
            terminals.append(child)
    if not verify(islands.size() == 1 and terminals.size() == 1,
            "one current pirate island and one current terminal are loaded"):
        return
    pirate_island = islands[0]
    terminal = terminals[0]
    if not verify(pirate_island.visible and terminal.visible, "island and terminal are visible"):
        return
    island_box = mesh_bounds(pirate_island)
    terminal_box = mesh_bounds(terminal)
    if not verify(island_box.size.x > 4 and island_box.size.y > 3 and island_box.size.z > 4,
            "island has its authored three-dimensional extent"):
        return
    fixture([13, 13, 13])
    harbor.camera_override = true
    await host.get_tree().physics_frame

    if not await capture_box("pirate25_front", island_box, FRONT_DIRECTION,
            "Island front with the real surrounding scene and sea retained."):
        return
    if not await capture_box("pirate25_reference_angle", island_box, REFERENCE_DIRECTION,
            "Island front quarter to inspect cave, rock masses, beach and broken pier."):
        return
    if not await capture_box("pirate25_terminal_overview", island_box.merge(terminal_box), OVERVIEW_DIRECTION,
            "Island and current terminal together in a labelled inspection view."):
        return

    # Ship poses and camera are supplied by the unmodified gameplay code.
    harbor.camera_override = false
    fixture([12, 12, 12])
    harbor.ui.visible = true
    await host.get_tree().physics_frame
    if not await host.capture("pirate25_progress12_partial_island"):
        return
    observations.append({"view": "pirate25_progress12_partial_island",
        "note": "The normal camera prioritizes boats; the island is partially outside the frame at progress 12."})
    fixture([13, 13, 13])
    harbor.ui.visible = true
    await host.get_tree().physics_frame
    if not verify(harbor.camera.framed_indices.size() == 3, "progress 13 normal framing includes all three ships"):
        return
    if not record_pirate_gameplay("pirate25_progress13_gameplay", [0, 1, 2]):
        return
    if not await host.capture("pirate25_progress13_gameplay"):
        return
    record_gameplay_view("pirate25_progress13_gameplay")
    if not await verify_area_view(13.0, [0, 1, 2]):
        return
    if not await verify_late_camera():
        return

    # Sample all three actual approach lanes with the island collision present.
    if not await route_clearance():
        return
    if not await arrival_case("right_first", [0, 3, 13], [6, 1, 1], [2]):
        return
    if not verify(harbor.state.ships[2].berth == 0, "rightmost first arrival occupies actual berth A"):
        return
    if not await arrival_case("all_three", [13, 13, 13], [1, 6, 3], [0, 1, 2]):
        return
    var assigned: Array[int] = []
    for data in harbor.state.ships:
        assigned.append(data.berth)
    assigned.sort()
    if not verify(assigned == [0, 1, 2], "all three arrivals occupy distinct actual A/B/C berths"):
        return
    harbor.camera_override = false
    harbor.camera.update_view(harbor.ships, 0, true)
    harbor.ui.visible = true
    await host.get_tree().physics_frame
    if not verify_arrived_visible("pirate normal arrival", harbor.camera.framed_indices):
        return
    if not await host.capture("pirate25_arrival_gameplay"):
        return
    record_gameplay_view("pirate25_arrival_gameplay")
    if not await verify_area_view(14.5, [0, 1, 2]):
        return
    var event_review := load("res://demo/tropical_harbor_3d/tools/reference_pirate_event_review.gd").new() as RefCounted
    var event_result: Dictionary = await event_review.run_sample(host, pirate_island)
    if not verify(not event_result.is_empty(), "explicit event camera sample completed"):
        return
    checks += event_result.checks
    host.finish({"kind": "current pirate island route and arrival sample", "checks": checks,
        "scope": "current-island views, 792 hull sweep samples, five late camera positions across three primaries, two area views, two real arrival cases and explicit camera API demonstration; no full regression or timing sample",
        "pirate_asset": "res://demo/tropical_harbor_3d/assets/reference/pirate_island.glb",
        "island_bounds": str(island_box), "terminal_bounds": str(terminal_box),
        "views": views, "observations": observations, "arrivals": arrivals, "event_camera": event_result,
        "screenshots_only": false, "visual_accepted": false})


func record_gameplay_view(id: String) -> void:
    views.append({"id": id, "eye": str(harbor.camera.position),
        "rotation": str(harbor.camera.rotation_degrees), "projection": harbor.camera.projection,
        "framed_indices": harbor.camera.framed_indices.duplicate(), "uses_current_player_camera": true})


func record_pirate_gameplay(label: String, subjects: Array) -> bool:
    var screen := host.get_viewport().get_visible_rect()
    var report: Array[Dictionary] = []
    for index in subjects:
        var ship: Node3D = harbor.ships[index]
        var rect := bounds(ship)
        if not verify(screen.grow(-25).encloses(rect), label + ": ship %d envelope fits viewport" % index):
            return false
        # This requested island+terminal composition uses a wider end view.
        # Keep the historical full-regression readability threshold unchanged.
        var longest_axis := maxf(rect.size.x, rect.size.y)
        if not verify(longest_axis >= screen.size.y * (128.0 / 900.0),
                label + ": ship %d remains readable, %.2f pixels" % [index, longest_axis]):
            return false
        for local in [Vector3(0, .5, -1.8), Vector3(0, .5, 0), Vector3(0, .5, 1.8)]:
            var ray := PhysicsRayQueryParameters3D.create(harbor.camera.position, ship.to_global(local), 4)
            var hit := harbor.get_world_3d().direct_space_state.intersect_ray(ray)
            if not verify(hit.is_empty(), label + ": ship %d unoccluded %s" % [index, hit]):
                return false
        report.append({"ship": index, "rect": str(rect), "longest_axis_px": longest_axis})
    observations.append({"view": label, "camera": str(harbor.camera.position),
        "rotation": str(harbor.camera.rotation_degrees), "subjects": report,
        "minimum_ship_axis_at_900px": 128.0})
    return true


func verify_area_view(progress: float, subjects: Array) -> bool:
    harbor.view_local_area(progress)
    harbor.camera.update_view(harbor.ships, 0, true)
    await host.get_tree().physics_frame
    if not verify(is_equal_approx(harbor.camera.area_progress, progress), "actual area view request applied"):
        return false
    var subject := ROUTE.center(progress) if progress < 14.0 else Vector3(-.85, 0, -16.6)
    var expected: Vector3 = harbor.camera._reference_origin(subject, progress) + harbor.camera._reference_aim(progress) + harbor.camera._reference_offset(progress)
    if not verify(harbor.camera.position.distance_to(expected) < .001, "area view uses the current reference composition"):
        return false
    return record_pirate_gameplay("pirate25_area_%.1f" % progress, subjects)


func verify_late_camera() -> bool:
    for progress in [11.5, 12.0, 12.5, 13.0, 13.12]:
        fixture([progress, progress, progress])
        for primary in 3:
            harbor.camera.auto_subject = primary
            harbor.camera.update_view(harbor.ships, 0, true)
            await host.get_tree().physics_frame
            if progress >= 13 and not verify(harbor.camera.framed_indices.size() == 3,
                    "final approach includes all three ships"):
                return false
            if not record_pirate_gameplay("late_%.2f_primary_%d" % [progress, primary], harbor.camera.framed_indices):
                return false
    return true
