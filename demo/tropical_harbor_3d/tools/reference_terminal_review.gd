extends "res://demo/tropical_harbor_3d/tools/local_voyage_review.gd"

# Review the new reference-style terminal in the normal project entry.
# This fixture never loads the previous terminal model or changes player cameras.
var terminal: Node3D
var terminal_box := AABB()
var views: Array[Dictionary] = []
var arrivals: Array[Dictionary] = []


func run(preview: Node) -> void:
    host = preview
    harbor = host.harbor
    harbor.capture_lock = true
    harbor.camera_override = true
    harbor.ui.visible = false
    if not verify(harbor.reference_art, "terminal review uses the current reference scene"):
        return
    var candidates: Array[Node3D] = []
    for child in harbor.coast.root.get_children():
        if child is Node3D and child.get_meta("reference_asset", "") == "terminal":
            candidates.append(child)
    if not verify(candidates.size() == 1, "one current terminal instance is loaded"):
        return
    terminal = candidates[0]
    if not verify(terminal.visible, "current terminal is visible"):
        return
    terminal_box = mesh_bounds(terminal)
    if not verify(terminal_box.size.x > 5.0 and terminal_box.size.y > 5.0, "terminal has its authored building extent"):
        return
    fixture([3, 3, 3])
    harbor.camera_override = true
    await host.get_tree().physics_frame

    # Keep the existing coast asset so the real apron and left bridge remain.
    # Other art and boats are hidden only for the labelled portrait.
    var hidden: Array[Node3D] = []
    for child in harbor.coast.root.get_children():
        if child is Node3D and child.visible and child.get_meta("reference_asset", "") not in ["terminal", "coast"]:
            hidden.append(child)
            child.visible = false
    for ship in harbor.ships:
        if ship.visible:
            hidden.append(ship)
            ship.visible = false
    var portrait_box := terminal_box.merge(AABB(Vector3(-8.2, 0.0, -25.0), Vector3(12.8, 1.3, 5.8)))
    if not await capture_box("terminal25_front_isolated", portrait_box, Vector3(0, .23, 1),
            "Front portrait; terminal and existing coast apron retained, other asset groups and boats temporarily hidden."):
        return
    for child in hidden:
        child.visible = true
    if not verify(hidden.all(func(item: Node3D) -> bool: return item.visible), "portrait visibility restored before scene and arrival checks"):
        return

    if not await capture_box("terminal25_reference_angle", portrait_box, Vector3(-.65, .50, 1),
            "Front quarter in the complete current scene."):
        return
    if not await capture_box("terminal25_back", terminal_box, Vector3(.55, .38, -1),
            "Landward face of the current building; no surrounding objects hidden."):
        return
    var contact_box := AABB(Vector3(-8.0, .0, -24.7), Vector3(12.8, 4.4, 5.7))
    if not await capture_box("terminal25_platform_contact", contact_box, Vector3(-.35, .50, 1),
            "Entrance, apron and existing bridge connection; detail view does not claim the whole building is in frame."):
        return

    # Exercise the same state and visual arrival code as regular gameplay.
    if not await arrival_case("right_first", [0, 3, 13], [6, 1, 1], [2]):
        return
    if not verify(harbor.state.ships[2].berth == 0, "rightmost first arrival occupies actual berth A"):
        return
    if not await arrival_case("all_three", [13, 13, 13], [1, 6, 3], [0, 1, 2]):
        return
    harbor.camera_override = false
    harbor.camera.update_view(harbor.ships, 0, true)
    harbor.ui.visible = true
    await host.get_tree().physics_frame
    if not verify_arrived_visible("normal arrival", harbor.camera.framed_indices):
        return
    if not await host.capture("terminal25_arrival_gameplay"):
        return
    views.append({"id": "terminal25_arrival_gameplay", "eye": str(harbor.camera.position),
        "rotation": str(harbor.camera.rotation_degrees), "projection": harbor.camera.projection,
        "framed_indices": harbor.camera.framed_indices.duplicate(), "player_camera_unchanged": true})

    harbor.ui.visible = false
    harbor.camera_override = true
    var berth_box := terminal_box.merge(AABB(Vector3(-8.3, -.45, -20.5), Vector3(12.0, 2.5, 9.4)))
    if not frame_box(berth_box, Vector3(-.35, .65, 1)):
        return
    await host.get_tree().physics_frame
    if not verify_arrived_visible("three berth view", [0, 1, 2]):
        return
    if not await host.capture("terminal25_three_berths"):
        return
    record_view("terminal25_three_berths", berth_box, "All three real berths and the left bridge in a labelled inspection view.")
    host.finish({"kind": "current terminal architecture and arrival sample", "checks": checks,
        "scope": "six views and two real arrival cases; full rebuild regression remains separate",
        "terminal_asset": "res://demo/tropical_harbor_3d/assets/reference/terminal.glb",
        "terminal_bounds": str(terminal_box), "views": views, "arrivals": arrivals,
        "screenshots_only": false, "visual_accepted": false})


func mesh_bounds(node: Node3D) -> AABB:
    var result := AABB()
    var first := true
    for item in node.find_children("*", "MeshInstance3D", true, false):
        var mesh := item as MeshInstance3D
        if mesh.mesh == null or str(mesh.name).begins_with("ReflectProxy"):
            continue
        var local_box := mesh.mesh.get_aabb()
        for corner in 8:
            var point: Vector3 = mesh.global_transform * local_box.get_endpoint(corner)
            result = AABB(point, Vector3.ZERO) if first else result.expand(point)
            first = false
    return result


func frame_box(box: AABB, direction: Vector3) -> bool:
    var target := box.get_center()
    var distance := maxf(box.size.length(), 12.0)
    harbor.camera.projection = Camera3D.PROJECTION_PERSPECTIVE
    harbor.camera.fov = 48.0
    for attempt in 40:
        harbor.camera.position = target + direction.normalized() * distance
        harbor.camera.look_at(target)
        var contained := true
        var screen := host.get_viewport().get_visible_rect().grow(-40)
        for corner in 8:
            var point := box.get_endpoint(corner)
            if harbor.camera.is_position_behind(point) or not screen.has_point(harbor.camera.unproject_position(point)):
                contained = false
                break
        if contained:
            return verify(true, "inspection extent fits the viewport")
        distance *= 1.07
    return verify(false, "inspection extent cannot be framed")


func capture_box(id: String, box: AABB, direction: Vector3, note: String) -> bool:
    if not frame_box(box, direction):
        return false
    if not await host.capture(id):
        return false
    record_view(id, box, note)
    return true


func record_view(id: String, box: AABB, note: String) -> void:
    views.append({"id": id, "eye": str(harbor.camera.position), "target": str(box.get_center()),
        "fov": harbor.camera.fov, "projection": harbor.camera.projection, "framed_bounds": str(box), "note": note})


func arrival_case(label: String, progress: Array, dice: Array, expected_arrived: Array) -> bool:
    harbor.camera_override = false
    fixture(progress)
    harbor.paused = false
    if not verify(harbor.state.roll(dice).is_empty(), label + ": real rules accepted dice"):
        return false
    harbor._start_parallel_sailing()
    var expected: Array = harbor.state.ships.duplicate(true)
    var opaque_relocation := false
    for step in 800:
        var before: Array[Vector3] = []
        for ship in harbor.ships:
            before.append(ship.position)
        simulate(.025)
        for i in 3:
            if harbor.ships[i].position.distance_to(before[i]) > 3.0:
                opaque_relocation = true
                if not verify(harbor.arrival_cover.color.a >= .99, label + ": berth relocation covered"):
                    return false
        if not harbor.is_moving():
            break
    if not verify(not harbor.is_moving() and opaque_relocation, label + ": real arrival transition completed"):
        return false
    if not verify(harbor.state.ships == expected and harbor.state.rolls == 1, label + ": visual arrival preserved rules"):
        return false
    for settle in 120:
        simulate(.025)
    harbor.paused = true
    await host.get_tree().physics_frame
    var berthed: Array[Dictionary] = []
    for i in 3:
        var data: Dictionary = harbor.state.ships[i]
        if not verify(data.arrived == (i in expected_arrived), label + ": expected arrived ship set"):
            return false
        var at: Vector3 = harbor.ships[i].position
        at.y = 0
        if not verify(at.distance_to(harbor.state.world_position(data)) < .01, label + ": visual position agrees with rules"):
            return false
        if data.arrived:
            if not verify_berth_clearance(i):
                return false
            berthed.append({"ship": i, "berth": data.berth, "position": str(at)})
    arrivals.append({"case": label, "dice": dice, "berthed": berthed, "opaque_relocation": opaque_relocation})
    return true


func verify_berth_clearance(ship_id: int) -> bool:
    var ship: Node3D = harbor.ships[ship_id]
    var shape := BoxShape3D.new()
    shape.size = Vector3(2.0, .9, 4.9)
    var query := PhysicsShapeQueryParameters3D.new()
    query.shape = shape
    query.collision_mask = 4
    query.margin = .06
    var at := Vector3(ship.position.x, .25, ship.position.z)
    query.transform = Transform3D(Basis(Vector3.UP, ship.rotation.y), at)
    var hits := harbor.get_world_3d().direct_space_state.intersect_shape(query, 16)
    var paths: Array[String] = []
    for hit in hits:
        paths.append(str(hit.collider.get_path()))
    return verify(hits.is_empty(), "actual berth hull is clear for ship %d: %s" % [ship_id, paths])


func verify_arrived_visible(label: String, subjects: Array) -> bool:
    for index in subjects:
        var ship: Node3D = harbor.ships[index]
        if not verify(host.get_viewport().get_visible_rect().grow(-20).encloses(bounds(ship)),
                label + ": ship %d fits viewport" % index):
            return false
        for local in [Vector3(0, .5, -1.8), Vector3(0, .5, 0), Vector3(0, .5, 1.8)]:
            var ray := PhysicsRayQueryParameters3D.create(harbor.camera.position, ship.to_global(local), 4)
            var hit := harbor.get_world_3d().direct_space_state.intersect_ray(ray)
            if not verify(hit.is_empty(), label + ": ship %d visible through full environment %s" % [index, hit]):
                return false
    return true
