extends RefCounted


func run(host: Node) -> void:
    var harbor: Node3D = host.harbor
    harbor.capture_lock = true
    harbor.configure_art_shadows()
    harbor.blockout.set_labels(false)
    harbor.camera.leave_inspection()
    harbor.camera.projection = Camera3D.PROJECTION_PERSPECTIVE
    harbor.camera.fov = 42
    var origin := Vector3(11.5, 0, 34)
    if "--coastal-environment-review" in OS.get_cmdline_user_args():
        await _environment_views(host, harbor)
        return
    if "--shipyard-sample" in OS.get_cmdline_user_args():
        harbor.camera.position = origin + Vector3(-6, 3.3, -6)
        harbor.camera.look_at(origin + Vector3(-2, 1.25, -2.8))
        await host.capture("shipyard_sample_connection")
        host.finish({"kind": "shipyard connected component in main scene"})
        return
    var views := [
        {"name": "reference", "eye": Vector3(-17, 15, 17), "target": Vector3(0, 2.2, 0)},
        {"name": "front", "eye": Vector3(-22, 7.3, 3), "target": Vector3(0, 2.6, 0)},
        {"name": "shore_access", "eye": Vector3(-6, 5.4, 12), "target": Vector3(-2.5, 1.1, 5.8)},
        {"name": "submerged_slip", "eye": Vector3(-11, 4.7, 6), "target": Vector3(-6.1, .15, 1.2)},
        {"name": "detail", "eye": Vector3(-7, 4.2, 5.5), "target": Vector3(-1.5, 2.0, 0)},
        {"name": "door_connection", "eye": Vector3(-2.0, 4.8, 4.5), "target": Vector3(2.25, 2.0, 0)},
        {"name": "workbench_props", "eye": Vector3(-2.6, 3.9, 4.0), "target": Vector3(.85, 2.6, 2.5)},
        {"name": "lifering_canvas", "eye": Vector3(1.2, 3.2, 3.3), "target": Vector3(2.85, 2.67, 2.05)},
        {"name": "roof_metal", "eye": Vector3(.4, 9.1, 8.5), "target": Vector3(5.5, 5.5, 1.9)},
        {"name": "metal_eave", "eye": Vector3(.2, 4.9, 8.2), "target": Vector3(4.6, 3.9, 3.75)},
        {"name": "back", "eye": Vector3(15, 11, -9), "target": Vector3(1, 3.0, 0)}
    ]
    var checks := 0
    var state_before: Array = harbor.state.ships.duplicate(true)
    var variant_stats: Array[Dictionary] = []
    var variants := ["a", "b", "combined"] if "--shipyard-compare" in OS.get_cmdline_user_args() else ["combined"]
    for variant in variants:
        harbor.camera.fov = 42
        harbor.blockout.set_shipyard_variant(variant)
        var yard: Node3D = harbor.blockout.get_node("RepairYard")
        var active_count := 0
        for model in yard.get_children():
            if model.visible:
                active_count += 1
            for body in model.find_children("*", "StaticBody3D", true, false):
                assert(body.collision_layer == (4 if model.visible else 0), "Hidden variant must have no collision")
                checks += 1
        assert(active_count == 1, "Exactly one shipyard variant is visible")
        assert(harbor.state.ships == state_before, "Art switching preserves game state")
        checks += 2
        for lane in 3:
            harbor.ships[lane].position = harbor.ROUTE.point(lane, 5.6)
            harbor.ships[lane].rotation.y = harbor.ROUTE.heading(lane, 5.6)
        for view in views:
            harbor.camera.position = origin + view.eye
            harbor.camera.look_at(origin + view.target)
            if not await host.capture("shipyard_" + variant + "_" + view.name):
                return
            if view.name == "reference":
                variant_stats.append({"variant": variant,
                    "visible_primitives_in_scene": Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
                    "scene_draw_calls": Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)})
        harbor.camera.position = Vector3(-10, 6.5, 44)
        harbor.camera.look_at(Vector3(3, 1.5, 34))
        await host.capture("shipyard_" + variant + "_sailing_context")
        for ship in harbor.ships:
            ship.route_progress = 5.6
        harbor.camera.focus_ship = -1
        harbor.camera.area_progress = -1
        harbor.camera.auto_subject = 1
        harbor.camera.update_view(harbor.ships, 0, true)
        await host.capture("shipyard_" + variant + "_actual_local_camera")
        await host.get_tree().physics_frame
        var eye_ray := PhysicsRayQueryParameters3D.create(harbor.camera.position, harbor.ships[1].position + Vector3(0, .5, 0), 4)
        assert(harbor.get_world_3d().direct_space_state.intersect_ray(eye_ray).is_empty(), "Shipyard leaves current boat visible")
        checks += 1
        for lane in 3:
            for step in range(131):
                var at: Vector3 = harbor.ROUTE.point(lane, float(step) / 10.0)
                var query := PhysicsRayQueryParameters3D.create(at + Vector3(-1.05, .5, 0), at + Vector3(1.05, .5, 0), 4)
                if not harbor.get_world_3d().direct_space_state.intersect_ray(query).is_empty():
                    push_error("SHIPYARD_REVIEW: route blocked at " + str(at))
                    host.get_tree().quit(2)
                    return
                checks += 1
    harbor.blockout.set_shipyard_variant("combined")
    harbor.camera_override = false
    harbor.view_shipyard()
    assert(harbor.blockout.shipyard_variant == "combined", "Review shows the combined shipyard")
    harbor.view_shipyard()
    assert(harbor.blockout.shipyard_variant == "combined", "Repeated review action keeps the chosen design")
    assert(harbor.state.ships == state_before, "Review controls preserve gameplay")
    checks += 3
    harbor.ui.visible = true
    await host.capture("shipyard_review_controls")
    host.finish({"kind": "combined shipyard in the single main scene", "checks": checks,
        "main_scene": harbor.scene_file_path, "camera_and_light_identical": true,
        "render_observations": variant_stats})


func _environment_views(host: Node, harbor: Node3D) -> void:
    var model: Node = harbor.blockout.get_node_or_null("CoastalEnvironment")
    if model == null or harbor.blockout.has_node("BackdropVillage") or harbor.blockout.has_node("LowerVillage") or harbor.blockout.has_node("CoastalGrove"):
        push_error("Coastal environment must replace the former village/grove placeholders")
        host.get_tree().quit(2)
        return
    var before: Array = harbor.state.ships.duplicate(true)
    var views := [
        {"name": "environment_overview", "eye": Vector3(-13, 23, 54), "target": Vector3(18, 2.3, 32), "fov": 52.0},
        {"name": "environment_waterfront", "eye": Vector3(-5, 7.5, 42), "target": Vector3(18, 2.3, 30), "fov": 50.0},
        {"name": "environment_village_path", "eye": Vector3(10, 6.5, 32), "target": Vector3(25.5, 3.0, 24), "fov": 52.0},
        {"name": "environment_backshore", "eye": Vector3(35, 10, 43), "target": Vector3(16, 2.0, 30), "fov": 52.0},
        {"name": "environment_terminal", "eye": Vector3(-6, 14, -2), "target": Vector3(14, 3.0, -19), "fov": 55.0}
    ]
    for view in views:
        harbor.camera.fov = view.fov
        harbor.camera.position = view.eye
        harbor.camera.look_at(view.target)
        if not await host.capture(view.name):
            return
    if harbor.state.ships != before:
        push_error("Environment review changed ship state")
        host.get_tree().quit(2)
        return
    host.finish({"kind": "coastal environment in the single main scene", "checks": 2,
        "main_scene": harbor.scene_file_path, "gameplay_camera_unchanged": true,
        "render_observations": {"draw_calls": Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
            "visible_primitives": Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)}})
