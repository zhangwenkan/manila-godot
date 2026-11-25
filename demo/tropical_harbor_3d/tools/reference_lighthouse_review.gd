extends "res://demo/tropical_harbor_3d/tools/reference_terminal_review.gd"

# Inspection of the authored tower in the normal scene. No pilot rules or beam
# animation are installed by this fixture or by the runtime locator interface.
var lighthouse: Node3D
var lighthouse_box := AABB()
var navigation: Dictionary = {}


func run(preview: Node) -> void:
    host = preview
    harbor = host.harbor
    harbor.capture_lock = true
    harbor.camera_override = true
    harbor.ui.visible = false
    if not verify(harbor.reference_art, "lighthouse review uses the current reference scene"):
        return
    var towers: Array[Node3D] = []
    for child in harbor.coast.root.get_children():
        if not child is Node3D:
            continue
        match child.get_meta("reference_asset", ""):
            "lighthouse": towers.append(child)
            "terminal": terminal = child
    if not verify(towers.size() == 1 and is_instance_valid(terminal), "one new lighthouse and current terminal are loaded"):
        return
    lighthouse = towers[0]
    lighthouse_box = mesh_bounds(lighthouse)
    terminal_box = mesh_bounds(terminal)
    if not verify(lighthouse == harbor.coast.lighthouse and lighthouse.visible
            and lighthouse.transform.is_equal_approx(Transform3D.IDENTITY),
            "world-baked lighthouse is loaded once without extra transform"):
        return
    if not verify(lighthouse_box.position.x >= 2.9 and lighthouse_box.end.x <= 8.1
            and lighthouse_box.position.z >= 12.4 and lighthouse_box.end.z <= 17.6
            and lighthouse_box.end.y > 9.0 and lighthouse_box.end.y < 10.2,
            "actual tower and complete reef remain within the selected envelope"):
        return
    if not verify(not harbor.blockout.has_node("PilotLighthouse"), "historical lighthouse is absent from reference scene"):
        return
    var assembly: Node3D = harbor.coast.get_lighthouse_anchor()
    var emitter: Node3D = harbor.coast.get_lighthouse_emitter()
    if not verify(is_instance_valid(assembly) and is_instance_valid(emitter), "authored assembly and light-source markers are available"):
        return
    if not verify(assembly.global_position.distance_to(Vector3(5.5, 0, 15)) < .001
            and emitter.global_position.distance_to(Vector3(5.5, 7.43, 15)) < .001,
            "locator interface returns actual authored world positions"):
        return
    fixture([8.5, 8.5, 8.5])
    harbor.camera_override = true
    await host.get_tree().physics_frame
    var hidden: Array[Node3D] = []
    for child in harbor.coast.root.get_children():
        if child is Node3D and child.visible and child != lighthouse:
            hidden.append(child)
            child.visible = false
    for ship in harbor.ships:
        if ship.visible:
            hidden.append(ship)
            ship.visible = false
    if not await capture_box("lighthouse26_front_isolated", lighthouse_box, Vector3(0, .25, 1),
            "Authored +Z front; other coast assets and boats temporarily hidden, actual water and ground retained."):
        return
    for child in hidden:
        child.visible = true
    if not verify(hidden.all(func(item: Node3D) -> bool: return item.visible), "portrait visibility restored"):
        return
    if not await capture_box("lighthouse26_front_quarter", lighthouse_box, Vector3(-1, .48, 1),
            "Front quarter with complete current scene retained."):
        return
    if not await capture_box("lighthouse26_lantern_detail", AABB(Vector3(3.6, 5.8, 13.1), Vector3(3.8, 4.0, 3.8)),
            Vector3(-.7, .3, 1), "Lantern glass, gallery, blue roof and authored emitter; detail view does not frame the whole tower."):
        return
    if not await capture_box("lighthouse26_reef_shore_contact", AABB(Vector3(2.8, -.45, 11.8), Vector3(10.5, 3.0, 8.0)),
            Vector3(-.5, 1.25, 1), "Actual reef, shallow water separation from beach and neighboring timber pier."):
        return
    harbor.camera_override = false
    for progress in [7.5, 8.5, 9.5]:
        fixture([progress, progress, progress])
        harbor.ui.visible = true
        await host.get_tree().physics_frame
        if not record("lighthouse26_normal_%.1f" % progress, harbor.camera.framed_indices):
            return
        var rect := projected_box(lighthouse_box)
        if not verify(host.get_viewport().get_visible_rect().grow(-20).encloses(rect),
                "whole authored lighthouse fits ordinary middle-subject camera at %.1f" % progress):
            return
        if not await host.capture("lighthouse26_normal_" + str(progress).replace(".", "_")):
            return
        views.append({"id": "normal_%.1f" % progress, "eye": str(harbor.camera.position),
            "lighthouse_rect": str(rect), "framed_indices": harbor.camera.framed_indices.duplicate(),
            "ordinary_camera_unchanged": true})
    fixture([8.62, 8.62, 8.62], 2)
    harbor.ui.visible = true
    await host.get_tree().physics_frame
    if not record("lighthouse26_nearest_right_lane", harbor.camera.framed_indices):
        return
    if not await host.capture("lighthouse26_nearest_right_lane"):
        return
    if not await actual_navigation():
        return
    if not await arrival_case("right_first", [0, 3, 13], [6, 1, 1], [2]):
        return
    if not verify(harbor.state.ships[2].berth == 0, "rightmost first arrival still uses real berth A"):
        return
    if not await arrival_case("all_three", [13, 13, 13], [1, 6, 3], [0, 1, 2]):
        return
    var assigned: Array[int] = []
    for data in harbor.state.ships:
        assigned.append(data.berth)
    assigned.sort()
    if not verify(assigned == [0, 1, 2], "all arrivals still use distinct actual A/B/C berths"):
        return
    harbor.camera_override = false
    harbor.camera.update_view(harbor.ships, 0, true)
    harbor.ui.visible = true
    await host.get_tree().physics_frame
    if not verify_arrived_visible("lighthouse normal arrival", harbor.camera.framed_indices):
        return
    if not await host.capture("lighthouse26_terminal_arrival"):
        return
    host.finish({"kind": "current lighthouse integration and lane clearance", "checks": checks,
        "scope": "authored tower and reef views, ordinary cameras, 1971 actual geometry hull samples, normal-camera lighthouse occlusion and unchanged framing, two real terminal arrival cases; no pilot rules or beam animation",
        "asset": "res://demo/tropical_harbor_3d/assets/reference/lighthouse.glb",
        "bounds": str(lighthouse_box), "assembly": str(assembly.global_position), "emitter": str(emitter.global_position),
        "views": views, "observations": observations, "navigation": navigation, "arrivals": arrivals,
        "screenshots_only": false, "visual_accepted": false})


func projected_box(box: AABB) -> Rect2:
    var rect := Rect2()
    for corner in 8:
        var pixel: Vector2 = harbor.camera.unproject_position(box.get_endpoint(corner))
        rect = Rect2(pixel, Vector2.ZERO) if corner == 0 else rect.expand(pixel)
    return rect


func actual_navigation() -> bool:
    var bodies: Array[StaticBody3D] = []
    for body in lighthouse.find_children("*", "StaticBody3D", true, false):
        bodies.append(body)
        body.collision_layer = 12
    await host.get_tree().physics_frame
    var shape := BoxShape3D.new()
    shape.size = Vector3(2.1, 2.4, 5.1)
    var query := PhysicsShapeQueryParameters3D.new()
    query.shape = shape
    query.collision_mask = 8
    query.margin = .06
    var hull_samples := 0
    var camera_samples := 0
    var visibility_rays := 0
    var passed := true
    for lane in 3:
        for step in 657:
            var progress := minf(step * .02, ROUTE.ENTRY)
            query.transform = Transform3D(Basis(Vector3.UP, ROUTE.heading(lane, progress)),
                ROUTE.point(lane, progress) + Vector3(0, .8, 0))
            var hits := harbor.get_world_3d().direct_space_state.intersect_shape(query, 1)
            hull_samples += 1
            if not verify(hits.is_empty(), "actual lighthouse clear at lane %d progress %.2f: %s" % [lane, progress, hits]):
                passed = false
                break
        if not passed:
            break
    if passed:
        fixture([0, 0, 0])
        for step in 67:
            var progress := minf(step * .2, ROUTE.ENTRY)
            for ship in harbor.ships:
                ship.place_on_route(progress)
            for primary in 3:
                harbor.camera.auto_subject = primary
                # Baseline comparison uses identical scene and camera with only
                # this tower excluded from the camera's environment mask.
                for body in bodies:
                    body.collision_layer = 8
                harbor.camera.update_view(harbor.ships, 0, true)
                var original_indices: Array[int] = harbor.camera.framed_indices.duplicate()
                var original_pose: Transform3D = harbor.camera.global_transform
                for body in bodies:
                    body.collision_layer = 12
                harbor.camera.update_view(harbor.ships, 0, true)
                camera_samples += 1
                if not verify(harbor.camera.framed_indices == original_indices
                        and harbor.camera.global_transform.is_equal_approx(original_pose),
                        "lighthouse preserves ordinary framing at %.2f primary %d" % [progress, primary]):
                    passed = false
                    break
                for index in original_indices:
                    for local in [Vector3(0, .5, -1.8), Vector3(0, .5, 0), Vector3(0, .5, 1.8)]:
                        var ray := PhysicsRayQueryParameters3D.create(harbor.camera.position, harbor.ships[index].to_global(local), 8)
                        visibility_rays += 1
                        if not verify(harbor.get_world_3d().direct_space_state.intersect_ray(ray).is_empty(),
                                "lighthouse does not occlude ordinary framed ship %d at %.2f primary %d" % [index, progress, primary]):
                            passed = false
                            break
                    if not passed:
                        break
                if not passed:
                    break
            if not passed:
                break
    for body in bodies:
        body.collision_layer = 4
    if not verify(bodies.all(func(body: StaticBody3D) -> bool: return body.collision_layer == 4),
            "temporary lighthouse audit collision layer restored"):
        return false
    navigation = {"hull_samples": hull_samples, "camera_samples": camera_samples,
        "visibility_rays": visibility_rays, "hull_shape": str(shape.size), "margin": .06,
        "collision_layers_restored": true, "all_clear": passed}
    return passed
