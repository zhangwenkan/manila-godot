extends "res://demo/tropical_harbor_3d/tools/local_voyage_review.gd"

func run(preview: Node) -> void:
    host = preview
    harbor = host.harbor
    harbor.capture_lock = true
    harbor.camera_override = false
    harbor.ui.visible = false
    if "--reference-lighthouse-sample" in OS.get_cmdline_user_args():
        var lighthouse_review := load("res://demo/tropical_harbor_3d/tools/reference_lighthouse_review.gd").new() as RefCounted
        await lighthouse_review.run(preview)
        return
    if "--reference-shipyard-sample" in OS.get_cmdline_user_args():
        var shipyard_review := load("res://demo/tropical_harbor_3d/tools/reference_shipyard_review.gd").new() as RefCounted
        await shipyard_review.run(preview)
        return
    if "--reference-pirate-sample" in OS.get_cmdline_user_args():
        var pirate_review := load("res://demo/tropical_harbor_3d/tools/reference_pirate_review.gd").new() as RefCounted
        await pirate_review.run(preview)
        return
    if "--reference-terminal-sample" in OS.get_cmdline_user_args():
        var terminal_review := load("res://demo/tropical_harbor_3d/tools/reference_terminal_review.gd").new() as RefCounted
        await terminal_review.run(preview)
        return
    var clay_review := "--reference-landform-clay" in OS.get_cmdline_user_args()
    if clay_review and not prepare_landform_clay():
        return
    if "--reference-shore-sample" in OS.get_cmdline_user_args():
        await reference_shore_sample()
        return
    if "--reference-composition-study" in OS.get_cmdline_user_args():
        await reference_composition_study()
        return
    for stage in [{"id": "01_gameplay_initial", "p": 3.0}, {"id": "02_town_waterfront", "p": 5.6},
            {"id": "03_mid_coast", "p": 7.5}, {"id": "04_later_coast", "p": 10.0}]:
        fixture([stage.p, stage.p, stage.p])
        for data in harbor.state.ships:
            for slot in data.slots:
                slot.owner = -1
            harbor.ships[data.ship_id].sync_crew(data)
        await host.get_tree().physics_frame
        if not await host.capture(stage.id):
            return
        if not record(stage.id, harbor.camera.framed_indices):
            return
        if stage.id == "01_gameplay_initial":
            if not verify(harbor.camera.framed_indices.size() == 3, "opening includes all three boats"):
                return
            for ship in harbor.ships:
                var stern: Vector2 = harbor.camera.unproject_position(ship.to_global(Vector3(0, 0, 2)))
                var bow: Vector2 = harbor.camera.unproject_position(ship.to_global(Vector3(0, 0, -2)))
                if not verify(bow.x > stern.x and bow.y < stern.y, "opening boat points from lower left toward upper right"):
                    return
    fixture([3, 3, 3])
    for data in harbor.state.ships:
        for slot in data.slots:
            slot.owner = -1
        harbor.ships[data.ship_id].sync_crew(data)
    harbor.camera_override = true
    harbor.camera.position = Vector3(-13, 8, 59)
    harbor.camera.look_at(Vector3(16, 2, 52))
    await host.capture("05_waterfront_low")
    harbor.camera.position = Vector3(1, 5, 47)
    harbor.camera.look_at(Vector3(8, 1, 42))
    await host.capture("06_hut_pier_detail")
    harbor.camera.position = Vector3(33, 12, 48)
    harbor.camera.look_at(Vector3(18, 3, 43))
    await host.capture("07_landward_connections")
    harbor.camera.position = harbor.ships[0].position + Vector3(-4.4, 3.7, 5.0)
    harbor.camera.look_at(harbor.ships[0].position + Vector3(0, .65, 0))
    await host.capture("detail_boat_cargo")
    if "--reference-detail-shadows" in OS.get_cmdline_user_args():
        var sun := harbor.get_node("WarmAfternoon") as DirectionalLight3D
        var world := harbor.get_world_3d().environment
        var original_angle := sun.light_angular_distance
        world.ssao_enabled = false
        await host.capture("diagnose_no_ao")
        world.ssao_enabled = true
        sun.shadow_enabled = false
        await host.capture("diagnose_no_shadows")
        sun.shadow_enabled = true
        RenderingServer.directional_soft_shadow_filter_set_quality(RenderingServer.SHADOW_QUALITY_SOFT_ULTRA)
        await host.capture("diagnose_shadow_ultra")
        for angle in [0.0, 0.25, 0.5]:
            sun.light_angular_distance = angle
            await host.capture("diagnose_shadow_angle_" + str(angle))
        sun.light_angular_distance = original_angle
        RenderingServer.directional_soft_shadow_filter_set_quality(RenderingServer.SHADOW_QUALITY_SOFT_HIGH)
        host.finish({"kind": "reference detail shadow diagnosis", "checks": checks})
        return
    harbor.camera.position = Vector3(1, 3.3, 49)
    harbor.camera.look_at(Vector3(5.5, .6, 44))
    await host.capture("detail_pier_joinery")
    for view in [
            {"id": "town_north_shops", "eye": Vector3(-4, 13, 66), "target": Vector3(19, 4, 52)},
            {"id": "town_civic_street", "eye": Vector3(-2, 13, 43), "target": Vector3(19, 4, 29)},
            {"id": "town_market_chapel", "eye": Vector3(-4, 12, 26), "target": Vector3(20, 4, 15)},
            {"id": "town_landward", "eye": Vector3(39, 16, 67), "target": Vector3(18, 3, 53)},
            {"id": "port_whole", "eye": Vector3(-15, 13, 73), "target": Vector3(12, 4, 65)},
            {"id": "port_town_scale_front", "eye": Vector3(-16, 10, 64.8), "target": Vector3(16, 4.6, 59)},
            {"id": "terrace_cross_street", "eye": Vector3(7, 7, 48), "target": Vector3(24, 4, 44)},
            {"id": "shore_grass_bank", "eye": Vector3(-2, 6, 60), "target": Vector3(15, 1.5, 54)},
            {"id": "shared_supply_yard", "eye": Vector3(7, 9, 57), "target": Vector3(18, 2.3, 53)},
            {"id": "fishing_working_court", "eye": Vector3(-3, 8, 49), "target": Vector3(12, 1.2, 41)}]:
        harbor.camera.position = view.eye
        harbor.camera.look_at(view.target)
        await host.capture(view.id)
    if clay_review:
        host.finish({"kind": "reference landform clay inspection", "observations": observations,
            "checks": checks, "terrain_material": "plain gray", "foliage_hidden": true})
        return
    # Single-asset inspection: keep the same world lighting, ground and water.
    # Hide surrounding art only for this labelled view, then restore it before navigation checks.
    var hidden_for_portrait: Array[Node3D] = []
    for child in harbor.coast.root.get_children():
        if child is Node3D and child.visible and child.get_meta("reference_asset", "") != "cargo_port":
            hidden_for_portrait.append(child)
            child.visible = false
    for ship in harbor.ships:
        if ship.visible:
            hidden_for_portrait.append(ship)
            ship.visible = false
    harbor.camera.position = Vector3(-23.0, 11.0, 64.6)
    harbor.camera.look_at(Vector3(8.8, 7.0, 64.6))
    await host.capture("port_front_isolated")
    harbor.camera.position = Vector3(-9.0, 12.5, 64.6)
    harbor.camera.look_at(Vector3(11.6, 8.0, 64.6))
    await host.capture("port_upper_front_isolated")
    harbor.camera.position = Vector3(-12.0, 6.0, 66.0)
    harbor.camera.look_at(Vector3(8.8, 2.7, 65.2))
    await host.capture("port_vessel_front_isolated")
    var portrait_projection: int = harbor.camera.projection
    var portrait_size: float = harbor.camera.size
    harbor.camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    harbor.camera.size = 21.0
    harbor.camera.position = Vector3(-24.0, 12.5, 81.4)
    harbor.camera.look_at(Vector3(8.8, 5.5, 64.7))
    await host.capture("port_reference_angle_isolated")
    harbor.camera.projection = portrait_projection
    harbor.camera.size = portrait_size
    for child in hidden_for_portrait:
        child.visible = true
    harbor.camera_override = false
    if "--reference-rebuild-sample" in OS.get_cmdline_user_args():
        host.finish({"kind": "reference harbor first whole-screen baseline", "observations": observations, "checks": checks})
        return
    await host.get_tree().physics_frame
    if not await route_clearance() or not lane_separation():
        return
    if not await camera_route_checks():
        return
    if not await gameplay_checks():
        return
    fixture([3, 3, 3])
    harbor.camera.update_view(harbor.ships, 0, true)
    var before: Basis = harbor.camera.basis
    harbor.camera.orbit(Vector2(250, 150))
    harbor.camera.zoom_inspection(3)
    harbor.camera.update_view(harbor.ships, 0, true)
    if not verify(before.is_equal_approx(harbor.camera.basis), "directed camera remains locked"):
        return
    for i in 3:
        harbor.select_ship(i)
        harbor.camera.update_view(harbor.ships, 0, true)
        await host.get_tree().physics_frame
        var hit: Dictionary = harbor.pick(harbor.camera.unproject_position(harbor.ships[i].position + Vector3(0, .5, 0)))
        if not verify(hit.get("ship_id", -1) == i, "reference boat remains selectable"):
            return
    var timing := await measure_local_view()
    host.finish({"kind": "reference harbor runtime verification", "checks": checks, "observations": observations, "timing": timing})


func reference_shore_sample() -> void:
    # Six existing poses for surface review; no navigation or timing checks.
    for stage in [{"id": "02_town_waterfront", "p": 5.6}, {"id": "03_mid_coast", "p": 7.5}]:
        fixture([stage.p, stage.p, stage.p])
        for data in harbor.state.ships:
            for slot in data.slots:
                slot.owner = -1
            harbor.ships[data.ship_id].sync_crew(data)
        await host.get_tree().physics_frame
        if not await host.capture(stage.id):
            return
    fixture([3, 3, 3])
    for data in harbor.state.ships:
        for slot in data.slots:
            slot.owner = -1
        harbor.ships[data.ship_id].sync_crew(data)
    harbor.camera_override = true
    for view in [
            {"id": "terrace_cross_street", "eye": Vector3(7, 7, 48), "target": Vector3(24, 4, 44)},
            {"id": "shore_grass_bank", "eye": Vector3(-2, 6, 60), "target": Vector3(15, 1.5, 54)},
            {"id": "town_civic_street", "eye": Vector3(-2, 13, 43), "target": Vector3(19, 4, 29)},
            {"id": "town_market_chapel", "eye": Vector3(-4, 12, 26), "target": Vector3(20, 4, 15)}]:
        harbor.camera.position = view.eye
        harbor.camera.look_at(view.target)
        if not await host.capture(view.id):
            return
    host.finish({"kind": "reference shore surface sample", "checks": 0,
        "screenshots_only": true, "visual_accepted": false})


func prepare_landform_clay() -> bool:
    # Capture-only diagnostic: preserve the authored shape, cameras and lighting.
    var ground := harbor.get_node_or_null("ReferenceGround")
    if not verify(ground != null, "clay inspection finds the reference terrain"):
        return false
    var material := StandardMaterial3D.new()
    material.albedo_color = Color(0.48, 0.48, 0.48)
    material.roughness = 1.0
    material.metallic_specular = 0.0
    var meshes := ground.find_children("*", "MeshInstance3D", true, false)
    if not verify(not meshes.is_empty(), "clay inspection finds terrain meshes"):
        return false
    for item in meshes:
        (item as MeshInstance3D).material_override = material
    for child in harbor.coast.root.get_children():
        if child is Node3D and child.get_meta("reference_asset", "") == "foliage":
            child.visible = false
    return true


func reference_composition_study() -> void:
    fixture([3, 3, 3])
    harbor.camera_override = true
    for pose in [
            {"id": "layout_01", "aim": Vector3(12, 3, -7), "offset": Vector3(-10, 21, 23), "fov": 48.0},
            {"id": "layout_02", "aim": Vector3(13, 3, -6), "offset": Vector3(-12, 22, 23), "fov": 48.0},
            {"id": "layout_03", "aim": Vector3(12, 3, -6), "offset": Vector3(-9, 20, 22), "fov": 50.0}]:
        var target: Vector3 = ROUTE.center(3) + pose.aim
        harbor.camera.position = target + pose.offset
        harbor.camera.look_at(target)
        harbor.camera.fov = pose.fov
        await host.capture(pose.id)
        observations.append({"view": pose.id, "eye": str(harbor.camera.position), "target": str(target),
            "boats": [str(bounds(harbor.ships[0])), str(bounds(harbor.ships[1])), str(bounds(harbor.ships[2]))]})
    host.finish({"kind": "reference coastal composition study", "observations": observations, "checks": checks})
