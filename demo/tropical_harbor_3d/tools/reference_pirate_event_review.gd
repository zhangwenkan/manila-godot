extends "res://demo/tropical_harbor_3d/tools/reference_terminal_review.gd"

# Exercise the explicit camera API only. This is not pirate gameplay or a trigger.
const ISLAND_CENTER := Vector3(-17.5, 0, -14)
var event_island: Node3D


func run_sample(preview: Node, island: Node3D) -> Dictionary:
    host = preview
    harbor = host.harbor
    event_island = island
    harbor.camera_override = false
    harbor.ui.visible = true
    var cases := [
        {"id": "three", "p": [13, 13, 13], "subject": 1, "involved": [0, 1, 2]},
        {"id": "left_only", "p": [13, 6, 7], "subject": 0, "involved": [0]},
        {"id": "middle_only", "p": [8, 13, 10], "subject": 1, "involved": [1]},
        {"id": "right_only", "p": [6, 7, 13], "subject": 2, "involved": [2]},
        {"id": "left_middle", "p": [13, 13, 8], "subject": 0, "involved": [0, 1]},
        {"id": "middle_right", "p": [8, 13, 13], "subject": 2, "involved": [1, 2]},
        {"id": "left_right", "p": [13, 8, 13], "subject": 0, "involved": [0, 2]},
    ]
    for sample in cases:
        fixture(sample.p, sample.subject)
        harbor.camera.focus_ship = -1 if sample.id == "three" else sample.subject
        harbor.camera.area_progress = 13.0 if sample.id == "middle_only" else -1.0
        if sample.id == "left_middle":
            harbor.camera.shot_indices.assign([0, 1])
        harbor.camera.update_view(harbor.ships, 0, true)
        await host.get_tree().physics_frame
        var saved_view := view_state()
        var saved_pose: Transform3D = harbor.camera.global_transform
        var saved_rules: Array = harbor.state.ships.duplicate(true)
        var saved_transforms: Array[Transform3D] = []
        for ship in harbor.ships:
            saved_transforms.append(ship.global_transform)
        if sample.id == "three" and not await host.capture("pirate_event_01_normal"):
            return {}
        var token: int = harbor.camera.begin_pirate_event(harbor.ships[sample.subject], ISLAND_CENTER)
        if not verify(token > 0 and harbor.camera.pirate_event_active(), sample.id + ": explicit begin accepted"):
            return {}
        if not verify(harbor.camera.global_transform.is_equal_approx(saved_pose), sample.id + ": begin does not teleport camera"):
            return {}
        if not move_camera(180, sample.id + " enter"):
            return {}
        if not verify_event_view(sample.id, sample.involved):
            return {}
        if sample.id == "three" and not await host.capture("pirate_event_02_island_front"):
            return {}
        if sample.id in ["left_only", "right_only", "left_middle"]:
            if not await host.capture("pirate_event_" + sample.id):
                return {}
        if not verify(harbor.camera.end_pirate_event(token), sample.id + ": matching end accepted"):
            return {}
        if not verify(view_state() == saved_view, sample.id + ": focus area shot and view settings restored exactly"):
            return {}
        if not move_camera(180, sample.id + " restore"):
            return {}
        if not verify(harbor.camera.global_transform.origin.distance_to(saved_pose.origin) < .002
                and harbor.camera.global_basis.is_equal_approx(saved_pose.basis), sample.id + ": prior composition restored"):
            return {}
        if not verify(harbor.state.ships == saved_rules, sample.id + ": rules untouched"):
            return {}
        for i in 3:
            if not verify(harbor.ships[i].global_transform.is_equal_approx(saved_transforms[i]), sample.id + ": ship %d position and heading untouched" % i):
                return {}
        if sample.id == "three" and not await host.capture("pirate_event_03_restored"):
            return {}
        if not verify(not harbor.camera.end_pirate_event(token), sample.id + ": repeated end is harmless"):
            return {}
    if not interruption_checks():
        return {}
    return {"checks": checks, "views": observations,
        "scope": "explicit camera demo, seven legal one/two/three-ship progress-13 arrangements, smooth return and interruption lifecycle; no pirate rule trigger or interception animation"}


func view_state() -> Dictionary:
    return {"focus": harbor.camera.focus_ship, "auto": harbor.camera.auto_subject,
        "area": harbor.camera.area_progress, "shot": harbor.camera.shot_indices.duplicate(),
        "framed": harbor.camera.framed_indices.duplicate(), "inspecting": harbor.camera.inspecting,
        "projection": harbor.camera.projection, "fov": harbor.camera.fov, "size": harbor.camera.size}


func move_camera(steps: int, label: String) -> bool:
    for step in steps:
        var before: Vector3 = harbor.camera.position
        harbor.camera.update_view(harbor.ships, 1.0 / 60.0)
        var after: Vector3 = harbor.camera.position
        if not verify(after.is_finite() and after.y >= 20.0, label + ": camera remains on high flight path"):
            return false
        if before.distance_to(after) > .00001:
            var query := PhysicsRayQueryParameters3D.create(before, after, 4)
            if not verify(harbor.get_world_3d().direct_space_state.intersect_ray(query).is_empty(), label + ": flight segment clears environment"):
                return false
    return verify(harbor.camera.settled, label + ": camera settled")


func verify_event_view(label: String, involved: Array) -> bool:
    var screen := host.get_viewport().get_visible_rect().grow(-25)
    var island_rect := Rect2()
    var first := true
    for mesh in event_island.find_children("*", "MeshInstance3D", true, false):
        if mesh.mesh == null or str(mesh.name).begins_with("ReflectProxy"):
            continue
        for corner in 8:
            var point: Vector3 = mesh.global_transform * mesh.mesh.get_aabb().get_endpoint(corner)
            if not verify(not harbor.camera.is_position_behind(point), label + ": island ahead of camera"):
                return false
            var pixel: Vector2 = harbor.camera.unproject_position(point)
            island_rect = Rect2(pixel, Vector2.ZERO) if first else island_rect.expand(pixel)
            first = false
    if not verify(screen.encloses(island_rect), label + ": whole island in event frame"):
        return false
    var to_eye: Vector3 = harbor.camera.position - ISLAND_CENTER
    to_eye.y = 0
    var cave_dot := Vector3.RIGHT.dot(to_eye.normalized())
    if not verify(cave_dot > .65, label + ": cave front readable from lane side"):
        return false
    var reports: Array[Dictionary] = []
    for i in involved:
        var ship: Node3D = harbor.ships[i]
        var rect := bounds(ship)
        if not verify(screen.encloses(rect) and maxf(rect.size.x, rect.size.y) >= 128,
                label + ": involved ship %d complete and at least 128px" % i):
            return false
        var stern: Vector3 = ship.to_global(Vector3(0, .5, 2))
        var bow: Vector3 = ship.to_global(Vector3(0, .5, -2))
        if not verify(harbor.camera.position.distance_to(stern) < harbor.camera.position.distance_to(bow),
                label + ": ship %d stern nearer camera without rotating ship" % i):
            return false
        for local in [Vector3(0, .5, -1.8), Vector3(0, .5, 0), Vector3(0, .5, 1.8)]:
            var query := PhysicsRayQueryParameters3D.create(harbor.camera.position, ship.to_global(local), 4)
            if not verify(harbor.get_world_3d().direct_space_state.intersect_ray(query).is_empty(), label + ": involved ship unoccluded"):
                return false
        reports.append({"ship": i, "rect": str(rect)})
    observations.append({"id": label, "camera": str(harbor.camera.position), "look": str(harbor.camera.local_look),
        "island_rect": str(island_rect), "cave_front_dot": cave_dot, "ships": reports})
    return true


func interruption_checks() -> bool:
    fixture([13, 13, 13])
    var saved := view_state()
    var first: int = harbor.camera.begin_pirate_event(harbor.ships[0])
    harbor.camera.update_view(harbor.ships, .1)
    var second: int = harbor.camera.begin_pirate_event(harbor.ships[2])
    if not verify(second > first and not harbor.camera.end_pirate_event(first)
            and harbor.camera.pirate_event_active(), "stale end cannot cancel replacement event"):
        return false
    if not verify(harbor.camera.end_pirate_event(second) and view_state() == saved,
            "replacement restores original pre-event camera owner"):
        return false
    var temporary := Node3D.new()
    harbor.add_child(temporary)
    temporary.position = harbor.ships[1].position
    harbor.camera.begin_pirate_event(temporary)
    temporary.free()
    harbor.camera.update_view(harbor.ships, .016)
    if not verify(not harbor.camera.pirate_event_active() and view_state() == saved,
            "removed target interrupts and restores safely"):
        return false
    if not verify(harbor.camera.begin_pirate_event(null) == 0 and not harbor.camera.pirate_event_active(),
            "invalid target cannot acquire event camera"):
        return false
    harbor.camera.begin_pirate_event(harbor.ships[1])
    harbor.select_ship(0)
    harbor.camera.update_view(harbor.ships, .016)
    if not verify(not harbor.camera.pirate_event_active() and harbor.camera.focus_ship == 0,
            "new ship focus interrupts without restoring stale focus"):
        return false
    harbor.camera.begin_pirate_event(harbor.ships[1])
    harbor.view_local_area(10.0)
    harbor.camera.update_view(harbor.ships, .016)
    if not verify(not harbor.camera.pirate_event_active() and is_equal_approx(harbor.camera.area_progress, 10.0),
            "new area view interrupts without restoring stale area"):
        return false
    harbor.camera.begin_pirate_event(harbor.ships[1])
    harbor.camera.inspect_ship(2)
    harbor.camera.update_view(harbor.ships, .016)
    if not verify(not harbor.camera.pirate_event_active() and harbor.camera.inspecting and harbor.camera.focus_ship == 2,
            "new inspection interrupts without restoring stale inspection"):
        return false
    harbor.camera.leave_inspection()
    harbor.select_ship(1)
    harbor.camera.begin_pirate_event(harbor.ships[1])
    harbor.select_ship(1)
    if not verify(not harbor.camera.pirate_event_active() and harbor.camera.focus_ship == 1,
            "explicit selection of the same ship also takes control"):
        return false
    harbor.overview()
    harbor.camera.begin_pirate_event(harbor.ships[1])
    harbor.overview()
    if not verify(not harbor.camera.pirate_event_active() and harbor.camera.focus_ship == -1
            and harbor.camera.area_progress == -1 and not harbor.camera.inspecting,
            "explicit overview takes control even if already the saved view"):
        return false
    harbor.camera.begin_pirate_event(harbor.ships[1])
    harbor.camera.leave_inspection()
    if not verify(not harbor.camera.pirate_event_active() and not harbor.camera.inspecting,
            "explicit exit inspection takes control"):
        return false
    return true
