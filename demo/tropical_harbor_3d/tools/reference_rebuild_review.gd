extends "res://demo/tropical_harbor_3d/tools/local_voyage_review.gd"

func run(preview: Node) -> void:
    host = preview
    harbor = host.harbor
    harbor.capture_lock = true
    harbor.camera_override = false
    harbor.ui.visible = false
    for stage in [{"id": "01_gameplay_initial", "p": 3.0}, {"id": "02_coastal_work", "p": 5.6},
            {"id": "03_mid_coast", "p": 7.5}, {"id": "04_later_coast", "p": 10.0}]:
        fixture([stage.p, stage.p, stage.p])
        for data in harbor.state.ships:
            for slot in data.slots:
                slot.owner = -1
            harbor.ships[data.ship_id].sync_crew(data)
        await host.get_tree().physics_frame
        if not await host.capture(stage.id):
            return
        observations.append({"view": stage.id, "camera": str(harbor.camera.position)})
    fixture([3, 3, 3])
    for data in harbor.state.ships:
        for slot in data.slots:
            slot.owner = -1
        harbor.ships[data.ship_id].sync_crew(data)
    harbor.camera_override = true
    harbor.camera.position = Vector3(-13, 9, 54)
    harbor.camera.look_at(Vector3(6, 1.2, 44))
    await host.capture("05_waterfront_low")
    harbor.camera.position = Vector3(1, 5, 47)
    harbor.camera.look_at(Vector3(13, 2.4, 43))
    await host.capture("06_hut_pier_detail")
    harbor.camera.position = Vector3(24, 11, 46)
    harbor.camera.look_at(Vector3(12, 2, 43))
    await host.capture("07_landward_connections")
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
