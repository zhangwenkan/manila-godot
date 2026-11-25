extends "res://demo/tropical_harbor_3d/tools/reference_pirate_review.gd"

# Current-scene integration only. The three future repair places are not gameplay.
var shipyard: Node3D
var shipyard_box := AABB()
var control_checks: Array[Dictionary] = []


func run(preview: Node) -> void:
    host = preview
    harbor = host.harbor
    harbor.capture_lock = true
    harbor.camera_override = true
    harbor.ui.visible = false
    if not verify(harbor.reference_art, "shipyard review uses the normal reference scene"):
        return
    var yards: Array[Node3D] = []
    for child in harbor.coast.root.get_children():
        if not child is Node3D:
            continue
        match child.get_meta("reference_asset", ""):
            "shipyard": yards.append(child)
            "terminal": terminal = child
            "pirate_island": pirate_island = child
    if not verify(yards.size() == 1 and is_instance_valid(terminal) and is_instance_valid(pirate_island),
            "one current yard, terminal and pirate island are loaded"):
        return
    shipyard = yards[0]
    shipyard_box = mesh_bounds(shipyard)
    terminal_box = mesh_bounds(terminal)
    if not verify(shipyard == harbor.coast.shipyard and shipyard.visible
            and shipyard.transform.is_equal_approx(Transform3D.IDENTITY),
            "authored yard is loaded once without another placement or scale transform"):
        return
    if not verify(shipyard_box.position.x > 3 and shipyard_box.end.x < 27
            and shipyard_box.position.z > -18 and shipyard_box.end.z < 3
            and shipyard_box.size.y > 6, "yard retains its authored scale on the terminal's right coast"):
        return
    if not verify(not harbor.blockout.has_node("RepairYard"), "reference scene has no old blank yard anchor"):
        return
    for mesh in shipyard.find_children("*", "MeshInstance3D", true, false):
        if not verify(not "M14_SculptedBank" in str(mesh.name), "archived old bank is absent from the runtime yard"):
            return
    fixture([13, 13, 13])
    harbor.camera_override = true
    await host.get_tree().physics_frame
    if "--reference-shipyard-back-contact" in OS.get_cmdline_user_args():
        var hidden_foliage: Array[Node3D] = []
        for child in harbor.coast.root.get_children():
            if child is Node3D and child.visible and child.get_meta("reference_asset", "") == "foliage":
                hidden_foliage.append(child)
                child.visible = false
        var captured := await capture_box("shipyard26_back_contact_foliage_hidden", shipyard_box, Vector3(1, .55, .35),
                "Diagnostic rear contact view: only the foliage asset is temporarily hidden; building, current ground and other art remain.")
        for child in hidden_foliage:
            child.visible = true
        if not captured or not verify(hidden_foliage.all(func(item: Node3D) -> bool: return item.visible),
                "diagnostic foliage visibility restored"):
            return
        host.finish({"kind": "shipyard rear contact diagnostic", "checks": checks, "views": views,
            "scope": "one labelled image with foliage temporarily hidden; no route, gameplay or timing checks",
            "screenshots_only": true, "visual_accepted": false})
        return

    var hidden: Array[Node3D] = []
    for child in harbor.coast.root.get_children():
        if child is Node3D and child.visible and child != shipyard:
            hidden.append(child)
            child.visible = false
    for ship in harbor.ships:
        if ship.visible:
            hidden.append(ship)
            ship.visible = false
    if not await capture_box("shipyard26_front_isolated", shipyard_box, Vector3(-1, .28, 0),
            "Front portrait: other coast assets and boats temporarily hidden; current ground and water remain."):
        return
    for child in hidden:
        child.visible = true
    if not verify(hidden.all(func(item: Node3D) -> bool: return item.visible), "portrait visibility restored"):
        return
    if not await capture_box("shipyard26_front_quarter", shipyard_box, Vector3(-1, .55, .8),
            "Current yard with complete neighboring scene, working court and submerged slip."):
        return
    if not await capture_box("shipyard26_landward_contact", shipyard_box, Vector3(1, .70, .45),
            "Landward access and building-ground contact in the actual scene."):
        return
    if not await capture_box("shipyard26_slip_contact", AABB(Vector3(4.5, -.3, -12.3), Vector3(10.5, 3.8, 6.6)),
            Vector3(-1, .65, .5), "Detail of the working platform, real submerged steps and present seabed."):
        return
    harbor.camera_override = false
    fixture([13, 13, 13])
    harbor.ui.visible = true
    await host.get_tree().physics_frame
    if not record_pirate_gameplay("shipyard26_normal13", [0, 1, 2]):
        return
    if not await host.capture("shipyard26_normal13"):
        return
    record_gameplay_view("shipyard26_normal13")
    if not await verify_controls():
        return
    if not await verify_late_camera() or not await route_clearance():
        return
    if not await arrival_case("right_first", [0, 3, 13], [6, 1, 1], [2]):
        return
    if not verify(harbor.state.ships[2].berth == 0, "rightmost first arrival occupies actual terminal A"):
        return
    if not await arrival_case("all_three", [13, 13, 13], [1, 6, 3], [0, 1, 2]):
        return
    var assigned: Array[int] = []
    for data in harbor.state.ships:
        assigned.append(data.berth)
    assigned.sort()
    if not verify(assigned == [0, 1, 2], "three arrivals still use distinct actual terminal A/B/C"):
        return
    harbor.camera_override = false
    harbor.camera.update_view(harbor.ships, 0, true)
    harbor.ui.visible = true
    await host.get_tree().physics_frame
    if not verify_arrived_visible("shipyard normal arrival", harbor.camera.framed_indices):
        return
    if not await host.capture("shipyard26_terminal_arrival"):
        return
    record_gameplay_view("shipyard26_terminal_arrival")
    var event_review := load("res://demo/tropical_harbor_3d/tools/reference_pirate_event_review.gd").new() as RefCounted
    var event_result: Dictionary = await event_review.run_sample(host, pirate_island)
    if not verify(not event_result.is_empty(), "pirate event camera remains clear with the current yard present"):
        return
    checks += event_result.checks
    host.finish({"kind": "current shipyard integration and view controls", "checks": checks,
        "scope": "yard portraits and actual scene contacts, button/J/V lifecycle, 792 hull samples, late normal cameras, two real terminal arrivals and explicit pirate camera; repair slots and return-to-yard gameplay remain planning only",
        "shipyard_asset": "res://demo/tropical_harbor_3d/assets/reference/shipyard.glb",
        "shipyard_bounds": str(shipyard_box), "views": views, "observations": observations,
        "arrivals": arrivals, "control_checks": control_checks, "event_camera": event_result,
        "screenshots_only": false, "visual_accepted": false})


func verify_controls() -> bool:
    fixture([13, 13, 13])
    harbor.camera_override = false
    var normal_pose: Transform3D = harbor.camera.global_transform
    var saved_rules: Array = harbor.state.ships.duplicate(true)
    var saved_ship_poses: Array[Transform3D] = []
    for ship in harbor.ships:
        saved_ship_poses.append(ship.global_transform)
    var buttons: Array[Button] = []
    for item in harbor.ui.find_children("*", "Button", true, false):
        if item.text == "修船厂":
            buttons.append(item)
    if not verify(buttons.size() == 1, "one actual shipyard UI button is connected"):
        return false
    harbor.select_ship(1)
    buttons[0].pressed.emit()
    var yard_pose: Transform3D = harbor.camera.global_transform
    if not verify(harbor.camera_override and harbor.selected == -1 and harbor.camera.focus_ship == -1
            and not harbor.camera.inspecting, "actual button takes camera control and clears ship selection"):
        return false
    var screen := host.get_viewport().get_visible_rect().grow(-25)
    for corner in 8:
        var point := shipyard_box.get_endpoint(corner)
        if not verify(not harbor.camera.is_position_behind(point)
                and screen.has_point(harbor.camera.unproject_position(point)), "whole shipyard fits its actual button view"):
            return false
    if not await host.capture("shipyard26_actual_button_J_view"):
        return false
    record_view("shipyard26_actual_button_J_view", shipyard_box, "Actual player button view; J must produce exactly this pose.")
    press_key(KEY_V)
    harbor.camera.update_view(harbor.ships, 0, true)
    if not verify(not harbor.camera_override and harbor.camera.global_transform.is_equal_approx(normal_pose),
            "V returns to the same ordinary sailing composition"):
        return false
    press_key(KEY_J)
    if not verify(harbor.camera_override and harbor.camera.global_transform.is_equal_approx(yard_pose),
            "actual J handler matches the UI button pose"):
        return false
    harbor.view_shipyard()
    if not verify(harbor.camera.global_transform.is_equal_approx(yard_pose), "repeated yard action is stable"):
        return false
    harbor.overview()
    harbor.camera.update_view(harbor.ships, 0, true)
    var token: int = harbor.camera.begin_pirate_event(harbor.ships[1])
    harbor.camera.update_view(harbor.ships, 0, true)
    press_key(KEY_J)
    if not verify(token > 0 and not harbor.camera.pirate_event_active()
            and not harbor.camera.end_pirate_event(token)
            and harbor.camera.global_transform.is_equal_approx(yard_pose), "J interrupts the event and invalidates its camera token"):
        return false
    press_key(KEY_V)
    harbor.camera.update_view(harbor.ships, 0, true)
    if not verify(not harbor.camera_override and harbor.camera.global_transform.is_equal_approx(normal_pose),
            "V after event-to-yard returns to normal sailing"):
        return false
    if not verify(harbor.state.ships == saved_rules, "all yard view controls preserve the rules"):
        return false
    for i in 3:
        if not verify(harbor.ships[i].global_transform.is_equal_approx(saved_ship_poses[i]), "yard view preserves ship %d position and heading" % i):
            return false
    fixture([8, 8, 8])
    if not verify(harbor.state.roll([1, 2, 3]).is_empty(), "movement guard uses a real accepted roll"):
        return false
    harbor._start_parallel_sailing()
    var moving_pose: Transform3D = harbor.camera.global_transform
    var moving_rules: Array = harbor.state.ships.duplicate(true)
    press_key(KEY_J)
    if not verify(harbor.is_moving() and not harbor.camera_override
            and harbor.camera.global_transform.is_equal_approx(moving_pose)
            and harbor.state.ships == moving_rules, "J during a live sailing interval leaves camera and rules alone"):
        return false
    control_checks.append({"actual_button": true, "actual_J_handler": true, "V_restores_normal_pose": true,
        "pirate_interruption": true, "sailing_guard": true, "ship_transforms_and_rules_unchanged": true})
    fixture([13, 13, 13])
    return true


func press_key(keycode: Key) -> void:
    var key := InputEventKey.new()
    key.keycode = keycode
    key.pressed = true
    harbor.capture_lock = false
    harbor._unhandled_input(key)
    harbor.capture_lock = true
