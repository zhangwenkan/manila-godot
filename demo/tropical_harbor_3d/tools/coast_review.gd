extends RefCounted

var host: Node
var harbor: Node3D
var observations: Array[Dictionary] = []
var checks := 0


func verify(value: bool, reason: String) -> bool:
    checks += 1
    if not value:
        push_error("COAST_REVIEW: " + reason)
        host.get_tree().quit(2)
    return value


func run(preview: Node) -> void:
    host = preview
    harbor = host.harbor
    harbor.capture_lock = true
    if "--terminal-review" in OS.get_cmdline_user_args():
        await review_terminal()
        return
    if "--surface-review" in OS.get_cmdline_user_args():
        await review_surfaces()
        return
    if "--coast-light-study" in OS.get_cmdline_user_args():
        await review_lighting()
        return
    var state_before: Array = harbor.state.ships.duplicate(true)
    var players_before: Array = harbor.state.players.duplicate(true)
    var positions_before: Array[Vector3] = []
    for ship in harbor.ships:
        positions_before.append(ship.position)
    harbor.overview()
    harbor.camera.update_view(harbor.ships, 0, true)
    await host.capture("coast_01_global")
    for spec in harbor.STATE.LAYOUT.COAST_BUILDINGS:
        var item := harbor.coast.root.get_node_or_null(NodePath(spec.id)) as Node3D
        if item == null:
            continue
        var area_label := item.get_node("AreaLabel") as Label3D
        area_label.modulate.a = 0.0
        area_label.outline_modulate.a = 0.0
        harbor.camera.leave_inspection()
        harbor.camera.projection = Camera3D.PROJECTION_PERSPECTIVE
        harbor.camera.fov = 42
        harbor.camera.position = spec.at + Vector3(-10, 7, 10)
        harbor.camera.look_at(spec.at + Vector3(0, 2.0, 0))
        harbor.coast.set_observing(true)
        await host.capture("building_" + str(spec.id))
        if spec.id == "HarborOffice":
            var views := [
                {"name": "craft_01_reference_angle", "eye": Vector3(-10, 12, 5), "target": Vector3(-1.2, 1.5, 0)},
                {"name": "craft_02_low_front", "eye": Vector3(-11, 3.1, 5), "target": Vector3(-1.4, 1.8, 0)},
                {"name": "craft_03_side_back", "eye": Vector3(8, 5.0, 10), "target": Vector3(0, 1.9, 0)},
                {"name": "craft_04_crate_net", "eye": Vector3(-7.0, 2.3, 4.0), "target": Vector3(-3.5, 0.8, 1.8)},
                {"name": "craft_05_door_timber", "eye": Vector3(-6.7, 3.0, -3.6), "target": Vector3(-2.5, 1.75, -0.8)}
            ]
            for view in views:
                harbor.camera.position = spec.at + view.eye
                harbor.camera.look_at(spec.at + view.target)
                await host.capture(view.name)
        area_label.modulate.a = 1.0
        area_label.outline_modulate.a = 1.0
    for i in 3:
        harbor.camera.inspect_ship(i)
        harbor.select_ship(i)
        harbor.camera.update_view(harbor.ships, 0, true)
        harbor.coast.set_observing(true)
        await host.capture("coast_ship_%d" % (i + 1))
        observations.append({"ship": i, "position": harbor.ships[i].position,
            "camera": harbor.camera.position, "projection": harbor.camera.projection})
        if not verify(harbor.camera.projection == Camera3D.PROJECTION_PERSPECTIVE, "ship inspection is perspective"):
            return
        if not verify(harbor.camera.position.y >= harbor.inspection_ground(harbor.camera.position) + 0.79, "camera clears terrain and water"):
            return
        if not verify(harbor.camera.is_position_in_frustum(harbor.ships[i].global_position + Vector3(0, .35, 0)), "observed boat must be visible"):
            return
    harbor.overview()
    harbor.camera.update_view(harbor.ships, 0, true)
    if not verify(harbor.state.ships == state_before and harbor.state.players == players_before, "camera switching preserves voyage and player resources"):
        return
    for i in 3:
        if not verify(harbor.ships[i].position == positions_before[i], "switching observation does not move ships"):
            return
    if not verify(not harbor.camera.inspecting and harbor.camera.projection == Camera3D.PROJECTION_ORTHOGONAL, "return restores overview projection"):
        return
    harbor.coast.set_observing(false)
    harbor.ui.visible = true
    await host.capture("coast_02_interface")
    harbor.ui.visible = false
    harbor.camera.inspect_ship(0)
    harbor.select_ship(0)
    harbor.ships[0].travel_to(harbor.ships[0].position * Vector3(1, 0, 1) + Vector3(0, 0, -6.0), false)
    var initial: Vector3 = harbor.ships[0].position
    for frame in range(12):
        for step in range(10):
            harbor.time += .05
            for ship in harbor.ships:
                ship.advance(.05, harbor.time)
            harbor.camera.update_view(harbor.ships, .05)
        await host.capture("coast_follow_%02d" % frame, false, 3)
    if not verify(harbor.ships[0].position.distance_to(initial) > 5.5, "follow capture must contain real ship travel"):
        return
    # Use the real ship movement to reach a review berth in this same world.
    # This fixture reviews scale and float motion, not game settlement rules.
    var review_berth := Vector3(4.7, 0, harbor.STATE.LAYOUT.BERTH_Z)
    harbor.ships[0].travel_to(review_berth, true)
    for step in range(640):
        harbor.time += .05
        for ship in harbor.ships:
            ship.advance(.05, harbor.time)
    if not verify(Vector2(harbor.ships[0].position.x, harbor.ships[0].position.z).distance_to(Vector2(review_berth.x, review_berth.z)) < .01, "review ship reaches the harbor through actual movement"):
        return
    harbor.camera.leave_inspection()
    harbor.camera_override = true
    harbor.camera.projection = Camera3D.PROJECTION_PERSPECTIVE
    harbor.camera.fov = 44
    harbor.camera.position = Vector3(-4.0, 5.4, -7.0)
    harbor.camera.look_at(Vector3(8.0, 1.4, -17.4))
    for building in harbor.coast.buildings:
        var area_label := building.get_node("AreaLabel") as Label3D
        area_label.modulate.a = 0.0
        area_label.outline_modulate.a = 0.0
    await host.capture("craft_06_ship_pier_house")
    var float_before: Transform3D = harbor.ships[0].transform
    for step in range(40):
        harbor.time += .05
        for ship in harbor.ships:
            ship.advance(.05, harbor.time)
    await host.capture("craft_07_berthed_float", false)
    if not verify(not harbor.ships[0].transform.is_equal_approx(float_before), "berthed ship retains water-driven float motion"):
        return
    host.finish({"kind": "single scene coastal harbor review", "buildings": harbor.coast.buildings.size(),
        "observations": observations, "checks": checks, "visual_accepted": false})


func review_terminal() -> void:
    var structure: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://demo/tropical_harbor_3d/assets/coast/harbor_terminal_structure.json"))
    if not verify(structure.pile_bases.size() == 28, "terminal retains its complete support grid"):
        return
    for pile in structure.pile_bases:
        var p: Array = pile.world_position
        var bed: float = harbor.environment._sand_height(p[0] - harbor.environment._shore(p[2]), p[2])
        if not verify(p[1] < bed - .20, "terminal support reaches below the runtime seabed: " + str(pile.name)):
            return
    harbor.camera_override = true
    harbor.coast.set_observing(true)
    for building in harbor.coast.buildings:
        var label := building.get_node("AreaLabel") as Label3D
        label.modulate.a = 0.0
        label.outline_modulate.a = 0.0
    harbor.camera.leave_inspection()
    harbor.camera.projection = Camera3D.PROJECTION_PERSPECTIVE
    harbor.camera.fov = 42
    var origin: Vector3 = harbor.STATE.LAYOUT.TERMINAL_ORIGIN
    var views := [
        {"name": "terminal_01_front", "eye": Vector3(0, 7.3, 25), "at": Vector3(0, 4.4, 0)},
        {"name": "terminal_02_reference", "eye": Vector3(-15, 15, 22), "at": Vector3(0, 3.5, 0)},
        {"name": "terminal_03_low", "eye": Vector3(-12, 3.6, 16), "at": Vector3(0, 3.5, 0)},
        {"name": "terminal_04_back", "eye": Vector3(16, 11, -20), "at": Vector3(0, 4.5, 0)},
        {"name": "terminal_05_joinery", "eye": Vector3(-8.4, 3.5, 9.5), "at": Vector3(-3.6, 1.4, 2.2)},
        {"name": "terminal_05b_crane", "eye": Vector3(-12.3, 4.0, 6.4), "at": Vector3(-7.4, 2.0, 0.45)},
        {"name": "terminal_05c_anchor", "eye": Vector3(1.4, 2.1, 6.0), "at": Vector3(4.3, 1.6, 0.95)}
    ]
    for view in views:
        harbor.camera.position = origin + view.eye
        harbor.camera.look_at(origin + view.at)
        await host.capture(view.name)
    harbor.camera.position = Vector3(-10.9, 3.5, -7.3)
    harbor.camera.look_at(Vector3(-6.65, .65, -15.8))
    await host.capture("terminal_05d_original_bridge")
    if "--terminal-structure" in OS.get_cmdline_user_args():
        host.finish({"kind": "terminal structure inspection", "lighting": "normal fixed daylight"})
        return
    harbor.overview()
    harbor.camera.update_view(harbor.ships, 0, true)
    await host.capture("terminal_06_overview")
    # Exercise the actual state transition and ship movement into all three berths.
    # Opening progress is [0, 4, 5]: the silk ship arrives first, then jade,
    # then ginseng. This also checks that berths are not tied to cargo lanes.
    for dice in [[6, 4, 3], [6, 6, 4], [2, 1, 2]]:
        if not verify(harbor.state.roll(dice).is_empty(), "review dice are accepted"):
            return
        for i in 3:
            harbor.ships[i].travel_to(harbor.state.world_position(harbor.state.ships[i]), harbor.state.ships[i].arrived)
        for step in range(900):
            harbor.time += .05
            for ship in harbor.ships:
                ship.advance(.05, harbor.time)
            if harbor.state.rolls == 2 and step == 60:
                harbor.view_landing()
                await host.capture("terminal_07_approach")
    for i in 3:
        var data: Dictionary = harbor.state.ships[i]
        var boat: Node3D = harbor.ships[i]
        if not verify(data.arrived and data.berth == [1, 0, 2][i], "berths follow arrival order rather than cargo lane"):
            return
        var target: Vector3 = harbor.state.world_position(data)
        if not verify(Vector2(boat.position.x, boat.position.z).distance_to(Vector2(target.x, target.z)) < .01, "ship reaches its assigned berth"):
            return
        if not verify(boat.position.z - 2.3672 > harbor.STATE.LAYOUT.APRON_FRONT_Z + .15, "berthed bow clears the terminal apron"):
            return
    harbor.view_landing()
    await host.capture("terminal_08_full_berths")
    for i in 3:
        harbor.camera.inspect_ship(i)
        harbor.select_ship(i)
        harbor.camera.orbit_yaw = -48.0
        harbor.camera.update_view(harbor.ships, 0, true)
        await host.capture("terminal_09_ship_%d" % (i + 1))
        for yaw in [-135.0, -90.0, -48.0, 0.0, 45.0, 90.0, 135.0, 180.0]:
            harbor.camera.orbit_yaw = yaw
            harbor.camera.update_view(harbor.ships, 0, true)
            if not verify(harbor.camera.is_position_in_frustum(harbor.ships[i].global_position + Vector3(0, .35, 0)), "boat remains visible during berth orbit"):
                return
            if not verify(harbor.camera.position.y >= harbor.inspection_ground(harbor.camera.position) + .79, "orbit camera clears the ground and water"):
                return
            var query := PhysicsRayQueryParameters3D.create(harbor.ships[i].position + Vector3(0, .45, 0), harbor.camera.position, 4)
            if not verify(harbor.get_world_3d().direct_space_state.intersect_ray(query).is_empty(), "orbit camera remains in front of buildings and pier surfaces"):
                return
    harbor.view_landing()
    var before: Array[Transform3D] = []
    for ship in harbor.ships:
        before.append(ship.transform)
    for step in range(40):
        harbor.time += .05
        for ship in harbor.ships:
            ship.advance(.05, harbor.time)
    for i in 3:
        if not verify(not harbor.ships[i].transform.is_equal_approx(before[i]), "berthed ships retain water-driven floating"):
            return
    await host.capture("terminal_10_berthed_float")
    harbor.ui.visible = true
    await host.capture("terminal_11_landing_interface")
    host.finish({"kind": "arrival terminal review in the single harbor", "checks": checks,
        "arrival_order": [harbor.state.ships[0].berth, harbor.state.ships[1].berth, harbor.state.ships[2].berth],
        "orbit_samples": 24, "lighting": "normal fixed daylight"})


func review_surfaces() -> void:
    # Inspect existing assets in the same harbor under the normal fixed daylight.
    harbor.camera_override = true
    harbor.camera.leave_inspection()
    harbor.camera.projection = Camera3D.PROJECTION_PERSPECTIVE
    harbor.camera.fov = 42
    for building in harbor.coast.buildings:
        var label := building.get_node("AreaLabel") as Label3D
        label.modulate.a = 0.0
        label.outline_modulate.a = 0.0
    var house := Vector3(13.2, .88, -19.2)
    var boat: Vector3 = harbor.ships[0].position
    var bridge: Vector3 = harbor.STATE.LAYOUT.WORKING_PIER
    var views := [
        {"name": "surface_01_house", "eye": house + Vector3(-6.7, 3.0, -3.6), "at": house + Vector3(-2.5, 1.75, -.8)},
        {"name": "surface_02_platform", "eye": house + Vector3(-7, 1.7, 2.8), "at": house + Vector3(-3.6, .55, .9)},
        {"name": "surface_03_boat", "eye": boat + Vector3(4.2, 2.3, 3.6), "at": boat + Vector3(0, .30, 0)},
        {"name": "surface_04_boat_side", "eye": boat + Vector3(3.6, 1.05, 1.3), "at": boat + Vector3(0, .37, 0)},
        {"name": "surface_05_bridge", "eye": bridge + Vector3(-2.2, 2.2, 3.0), "at": bridge + Vector3(0, .85, .3)},
        {"name": "surface_06_bridge_low", "eye": bridge + Vector3(1.1, 1.3, 2.0), "at": bridge + Vector3(0, .85, .3)}
    ]
    for view in views:
        harbor.camera.position = view.eye
        harbor.camera.look_at(view.at)
        await host.capture(view.name)
    host.finish({"kind": "wood surface review in the main harbor", "lighting": "normal fixed daylight"})


func review_lighting() -> void:
    # Compare lighting on the same authored material and geometry in the main scene.
    var sun := harbor.get_node("WarmAfternoon") as DirectionalLight3D
    var world := harbor.get_world_3d().environment
    var at := Vector3(13.2, .88, -19.2)
    harbor.camera_override = true
    harbor.camera.leave_inspection()
    harbor.camera.projection = Camera3D.PROJECTION_PERSPECTIVE
    harbor.camera.fov = 42
    for building in harbor.coast.buildings:
        var label := building.get_node("AreaLabel") as Label3D
        label.modulate.a = 0.0
        label.outline_modulate.a = 0.0
    for stage in range(5):
        if stage == 1:
            sun.rotation_degrees = Vector3(-48, -65, 0)
        elif stage == 2:
            world.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
            world.ambient_light_color = Color("c0c4c1")
            world.ambient_light_energy = .42
            world.ambient_light_sky_contribution = 0.0
        elif stage == 3:
            world.ssao_radius = .45
            world.ssao_intensity = .85
            sun.light_energy = 1.0
            sun.shadow_bias = .025
            sun.shadow_normal_bias = .25
            RenderingServer.environment_set_ssao_quality(RenderingServer.ENV_SSAO_QUALITY_MEDIUM, true, .5, 2, 50.0, 300.0)
        elif stage == 4:
            sun.rotation_degrees = Vector3(-42, -55, 0)
            sun.light_energy = .95
            sun.light_angular_distance = 1.15
        harbor.camera.position = at + Vector3(-10, 7, 10)
        harbor.camera.look_at(at + Vector3(0, 2, 0))
        await host.capture("light_%d_building" % stage)
        harbor.camera.position = at + Vector3(-7, 2.3, 4)
        harbor.camera.look_at(at + Vector3(-3.5, .8, 1.8))
        await host.capture("light_%d_joinery" % stage)
    host.finish({"kind": "lighting comparison with fixed craft asset", "visual_accepted": false})
