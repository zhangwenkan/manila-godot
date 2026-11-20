extends Node3D

const ENVIRONMENT = preload("res://demo/tropical_harbor_3d/environment/harbor_environment.gd")
const STATE = preload("res://demo/tropical_harbor_3d/fleet/fleet_state.gd")
const SHIP = preload("res://demo/tropical_harbor_3d/ships/ship_view.gd")
const CAMERA = preload("res://demo/tropical_harbor_3d/fleet/fleet_camera.gd")
const UI = preload("res://demo/tropical_harbor_3d/ui/fleet_interaction.gd")
const PIER = preload("res://demo/tropical_harbor_3d/environment/pier_builder.gd")
const WATER = preload("res://demo/tropical_harbor_3d/materials/fleet_water.gdshader")
const REFLECTION = preload("res://demo/tropical_harbor_3d/environment/water_reflection.gd")
const COAST = preload("res://demo/tropical_harbor_3d/environment/coastal_town.gd")
const BLOCKOUT = preload("res://demo/tropical_harbor_3d/environment/harbor_blockout.gd")
const ROUTE = preload("res://demo/tropical_harbor_3d/fleet/harbor_route.gd")

var state := STATE.new()
var environment: RefCounted
var ships: Array[Node3D] = []
var camera: Camera3D
var reflection: Node
var ui: CanvasLayer
var selected := -1
var time := 0.0
var paused := false
var capture_lock := false
var camera_override := false
var test_mode := false
var started := 0
var rng := RandomNumberGenerator.new()
var inspection_dragging := false
var coast: RefCounted
var blockout: Node3D
var arrival_transition := false
var arrival_elapsed := 0.0
var arrival_cover: ColorRect
var pending_berths: Array[int] = []
var sailing_ships: Array[int] = []
var sailing_targets: Dictionary = {}
var shot_hold := 0.0
var local_settling := false
var reference_art := true


func _ready() -> void:
    var args := OS.get_cmdline_user_args()
    reference_art = not ("--art-preview" in args or "--fleet-capture" in args or "--fleet-demo" in args) or "--reference-rebuild" in args
    state.scenic_routes = not ("--fleet-capture" in args or "--art-preview" in args) or "--local-voyage-review" in args or "--layout-review" in args or "--shipyard-review" in args
    if reference_art:
        state.scenic_routes = true
    environment = load("res://demo/tropical_harbor_3d/environment/reference_environment.gd").new(self) if reference_art else ENVIRONMENT.new(self)
    environment.water_shader = WATER
    environment._build_environment()
    if not "--art-preview" in OS.get_cmdline_user_args():
        configure_art_shadows()
    environment._build_water()
    environment._build_sand()
    environment._build_swash()
    environment._build_contact_stones()
    var pier := PIER.new()
    if not reference_art:
        pier.build(self, environment)
    if state.scenic_routes and not reference_art:
        get_node("TimberPiers/WorkingPier").position.z += 55.0
        get_node("TimberPiers/BrokenPier").position.z += 55.0
        for i in pier.contacts.size():
            if pier.contacts[i].y > 0:
                pier.contacts[i].y += 55.0
    coast = load("res://demo/tropical_harbor_3d/environment/reference_coast.gd").new() if reference_art else COAST.new()
    coast.build(self)
    blockout = BLOCKOUT.new()
    blockout.name = "HarborBlockout"
    add_child(blockout)
    if reference_art:
        var yard_anchor := Node3D.new()
        yard_anchor.name = "RepairYard"
        yard_anchor.position = Vector3(13, 0, 34)
        blockout.add_child(yard_anchor)
    else:
        blockout.build(state.scenic_routes)
    var contacts: PackedVector4Array = environment.contact_objects.duplicate()
    contacts.append_array(pier.contacts)
    environment.set_contacts(contacts, 32)
    camera = CAMERA.new()
    camera.name = "FleetCamera"
    add_child(camera)
    # Historical capture fixtures retain their established camera, while F5
    # and the new composition review exercise the proposed player view.
    camera.local_harbor = state.scenic_routes
    camera.reference_art = reference_art
    camera.ground_sample = Callable(self, "inspection_ground")
    camera.harbor_points = coast.landmarks
    reflection = REFLECTION.new()
    add_child(reflection)
    reflection.setup(self, camera)
    reflection.set_enabled(true)
    rng.randomize()
    state.start_voyage(["jade", "silk", "ginseng"], [3, 3, 3])
    rebuild_ships()
    var piers := get_node_or_null("TimberPiers")
    if piers != null:
        reflection.add_subject(piers)
    reflection.add_subject(coast.root)
    reflection.add_subject(blockout)
    environment.water_material.set_shader_parameter("reflection_tex", reflection.texture())
    ui = UI.new()
    add_child(ui)
    ui.build(self)
    var transition_layer := CanvasLayer.new()
    transition_layer.layer = 20
    add_child(transition_layer)
    arrival_cover = ColorRect.new()
    arrival_cover.color = Color(0.025, .045, .055, 0)
    arrival_cover.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    arrival_cover.mouse_filter = Control.MOUSE_FILTER_IGNORE
    transition_layer.add_child(arrival_cover)
    for arg in OS.get_cmdline_user_args():
        if arg == "--art-preview":
            var art := load("res://demo/tropical_harbor_3d/tools/art_preview.gd").new() as Node
            add_child(art)
            art.run.call_deferred(self)
            return
        if arg == "--fleet-capture" or arg == "--fleet-demo":
            test_mode = true
    if test_mode:
        started = Time.get_ticks_msec()
        var runner := load("res://demo/tropical_harbor_3d/tests/fleet_capture.gd").new() as Node
        add_child(runner)
        runner.run.call_deferred(self)


func configure_art_shadows() -> void:
    # Same values as harbor_environment._build_environment(); kept for art_preview A/B frames.
    var sun := get_node("WarmAfternoon") as DirectionalLight3D
    sun.light_angular_distance = 0.0 if reference_art else 0.85
    sun.directional_shadow_max_distance = 100.0
    sun.shadow_normal_bias = 0.6
    RenderingServer.directional_shadow_atlas_set_size(4096, true)
    RenderingServer.directional_soft_shadow_filter_set_quality(RenderingServer.SHADOW_QUALITY_SOFT_HIGH)


func rebuild_ships() -> void:
    local_settling = false
    sailing_ships.clear()
    sailing_targets.clear()
    shot_hold = 0
    selected = -1
    inspection_dragging = false
    camera.leave_inspection()
    camera.focus_ship = -1
    camera.shot_indices.clear()
    camera.area_progress = -1
    camera.auto_subject = 1
    for ship in ships:
        remove_child(ship)
        ship.queue_free()
    ships.clear()
    for data in state.ships:
        var ship := SHIP.new()
        add_child(ship)
        ship.reference_art = reference_art
        ship.build(data)
        ship.wave_sample = Callable(environment, "wave_height")
        ship.position = state.world_position(data)
        if state.scenic_routes:
            if not data.arrived:
                ship.place_on_route(data.progress)
            else:
                ship.scenic_route = true
                ship.route_progress = 14.5
        ships.append(ship)
        if reflection != null:
            reflection.add_subject(ship)
    camera.update_view(ships, 0, true)
    if ui != null:
        ui.selected_slot = -1
        ui.info = false
        ui.refresh()


func new_voyage() -> void:
    if is_moving():
        return
    var ids: Array = STATE.CARGO.keys()
    var offset: int = state.voyage % 4
    state.start_voyage([ids[offset], ids[(offset + 1) % 4], ids[(offset + 2) % 4]], [3, 3, 3])
    rebuild_ships()


func roll_dice() -> void:
    if is_moving() or paused:
        return
    var dice := [rng.randi_range(1, 6), rng.randi_range(1, 6), rng.randi_range(1, 6)]
    if not state.roll(dice).is_empty():
        return
    if state.scenic_routes:
        _start_parallel_sailing()
        ui.refresh()
        return
    for i in 3:
        var target: Vector3 = state.world_position(state.ships[i])
        if Vector3(ships[i].position.x, 0, ships[i].position.z).distance_to(target) > 0.01:
            ships[i].travel_to(target, state.ships[i].arrived)
    ui.refresh()


func _start_parallel_sailing() -> void:
    var subject: int = camera.focus_ship if camera.focus_ship >= 0 else camera.auto_subject
    overview()
    sailing_ships.clear()
    sailing_targets.clear()
    for i in 3:
        if ships[i].route_progress >= 14.0:
            continue
        var target: float = ROUTE.ENTRY if state.ships[i].arrived else state.ships[i].progress
        if is_equal_approx(target, ships[i].route_progress):
            continue
        sailing_ships.append(i)
        sailing_targets[i] = target
    if sailing_ships.is_empty():
        return
    # Keep the viewed area for this roll. If its ship is already berthed,
    # choose the middle-progress active ship before any movement starts.
    if not subject in sailing_ships:
        var ordered := sailing_ships.duplicate()
        ordered.sort_custom(func(a, b): return ships[a].route_progress < ships[b].route_progress)
        subject = ordered[ordered.size() / 2]
    camera.auto_subject = subject
    camera.shot_indices.assign([subject])
    camera.area_progress = -1
    camera_override = false
    shot_hold = .6


func _advance_local_sailing(delta: float) -> void:
    if sailing_ships.is_empty():
        return
    if shot_hold > 0:
        shot_hold = maxf(.001, shot_hold - delta)
        if shot_hold <= .001 and camera.settled:
            shot_hold = 0
            var max_steps := 0.0
            for i in sailing_ships:
                max_steps = maxf(max_steps, absf(sailing_targets[i] - ships[i].route_progress))
            var duration := 1.6 + max_steps * .45
            # Shared interval: different dice change distance and speed,
            # never the order in which boats are shown moving.
            for i in sailing_ships:
                ships[i].sail_route(sailing_targets[i], duration)
                if state.ships[i].arrived:
                    pending_berths.append(i)
        return
    for i in sailing_ships:
        if ships[i].route_travelling:
            return
    sailing_ships.clear()
    camera.shot_indices.clear()
    local_settling = pending_berths.is_empty()


func select_ship(index: int) -> void:
    if state.scenic_routes and is_moving():
        return
    selected = index
    camera.focus_ship = index
    camera.area_progress = -1
    camera_override = false
    ui.selected_slot = -1
    ui.info = false
    for i in 3:
        ships[i].set_selected(i == index and not camera.inspecting)
    if camera.inspecting:
        camera.update_view(ships, 0, true)
    ui.refresh()


func overview() -> void:
    if camera.local_harbor and is_moving():
        return
    inspection_dragging = false
    camera.leave_inspection()
    selected = -1
    camera.focus_ship = -1
    camera.area_progress = -1
    camera_override = false
    ui.selected_slot = -1
    ui.info = false
    for ship in ships:
        ship.set_selected(false)
    ui.refresh()


func toggle_inspection() -> void:
    if camera.local_harbor:
        if camera.focus_ship >= 0:
            overview()
        else:
            select_ship(maxi(selected, 0))
        return
    if camera.inspecting:
        overview()
        return
    camera.inspect_ship(maxi(selected, 0))
    select_ship(camera.focus_ship)


func view_shipyard() -> void:
    if not state.scenic_routes or is_moving():
        return
    var eye := Vector3(-5.5, 13, 51)
    camera.leave_inspection()
    camera_override = true
    camera.projection = Camera3D.PROJECTION_PERSPECTIVE
    camera.fov = 42
    camera.position = eye
    camera.look_at(blockout.get_node("RepairYard").global_position + Vector3(0, 2.5, 0))
    ui.selected_slot = -1
    ui.info = false
    ui.refresh()


func inspection_ground(at: Vector3) -> float:
    return maxf(0.0, environment._sand_height(at.x - environment._shore(at.z), at.z))


func _notification(what: int) -> void:
    if what == NOTIFICATION_WM_WINDOW_FOCUS_OUT or what == NOTIFICATION_APPLICATION_FOCUS_OUT:
        inspection_dragging = false


func _input(event: InputEvent) -> void:
    if not inspection_dragging:
        return
    if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_RIGHT and not event.pressed:
        inspection_dragging = false
    elif event is InputEventMouseMotion and camera.inspecting and not capture_lock:
        camera.orbit(event.relative)
        get_viewport().set_input_as_handled()


func view_piers() -> void:
    if camera.local_harbor:
        view_local_area(5.6)
        return
    overview()
    camera_override = true
    camera.position = Vector3(15, 12.55, 23.4)
    camera.look_at(Vector3(7, 0.55, 9.4))
    camera.size = 8.2


func view_landing() -> void:
    if camera.local_harbor:
        view_local_area(14.5)
        return
    overview()
    camera_override = true
    camera.position = STATE.LAYOUT.TERMINAL_ORIGIN + Vector3(-17, 19, 27)
    camera.look_at(STATE.LAYOUT.TERMINAL_ORIGIN + Vector3(1.5, 3.0, 3.5))
    var points: Array[Vector3] = coast.landmarks.duplicate()
    for lane in STATE.LAYOUT.BERTH_X:
        for side in [-1.0, 1.0]:
            points.append(Vector3(lane + side, 1.1, STATE.LAYOUT.BERTH_Z + 2.6))
    for post in STATE.LAYOUT.PORT_POSTS:
        points.append(post + Vector3(0, 1.2, 0))
    points.append(STATE.LAYOUT.LANDING_BOUNDS.end)
    camera.frame_points(points, 0, true)


func view_local_area(progress: float) -> void:
    if is_moving():
        return
    overview()
    camera.area_progress = progress


func toggle_pause() -> void:
    paused = not paused
    ui.refresh()


func is_moving() -> bool:
    if local_settling:
        return true
    if not sailing_ships.is_empty():
        return true
    if arrival_transition or not pending_berths.is_empty():
        return true
    for ship in ships:
        if not ship.waypoints.is_empty():
            return true
    return false


func pick(point: Vector2) -> Dictionary:
    var origin := camera.project_ray_origin(point)
    var query := PhysicsRayQueryParameters3D.create(origin, origin + camera.project_ray_normal(point) * 250, 7)
    query.collide_with_areas = true
    query.collide_with_bodies = true
    var result := get_world_3d().direct_space_state.intersect_ray(query)
    if result.is_empty() or not result.collider.has_meta("ship_id"):
        return {}
    return {"ship_id": int(result.collider.get_meta("ship_id")), "slot_id": int(result.collider.get_meta("slot_id"))}


func _unhandled_input(event: InputEvent) -> void:
    if capture_lock:
        return
    if event is InputEventKey and event.pressed and not event.echo:
        match event.keycode:
            KEY_V: overview()
            KEY_P: view_piers()
            KEY_H: view_landing()
            KEY_C: toggle_inspection()
            KEY_L: blockout.set_labels(not blockout.labels_visible)
            KEY_J:
                view_shipyard()
            KEY_B:
                if not state.scenic_routes:
                    blockout.set_western_land(not blockout.western_land)
            KEY_1, KEY_2, KEY_3:
                if camera.inspecting or camera.local_harbor:
                    select_ship(event.keycode - KEY_1)
            KEY_SPACE: toggle_pause()
            KEY_ESCAPE:
                if camera.inspecting:
                    overview()
                else:
                    get_tree().quit()
    if camera.inspecting and event is InputEventMouseButton:
        if event.button_index == MOUSE_BUTTON_RIGHT:
            inspection_dragging = event.pressed
            get_viewport().set_input_as_handled()
        elif event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
            camera.zoom_inspection(-1.0 if event.button_index == MOUSE_BUTTON_WHEEL_UP else 1.0)
            get_viewport().set_input_as_handled()
        return
    if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
        var hit := pick(event.position)
        if hit.is_empty():
            return
        if hit.ship_id == selected and hit.slot_id >= 0:
            ui.select_slot(hit.slot_id)
        else:
            select_ship(hit.ship_id)
        get_viewport().set_input_as_handled()


func sync_water() -> void:
    coast.sync_life(time, not paused and not capture_lock)
    environment.sync_time(time)
    var positions := PackedVector4Array()
    var directions := PackedVector2Array()
    for ship in ships:
        var p: Vector3 = ship.global_position
        var wake: float = ship.wake if ship.visible else -1.0
        positions.append(Vector4(p.x, p.y, p.z, wake))
        var stern: Vector3 = ship.global_basis.z
        directions.append(Vector2(stern.x, stern.z).normalized())
    environment.water_material.set_shader_parameter("boats", positions)
    environment.water_material.set_shader_parameter("stern_directions", directions)
    if reflection != null:
        reflection.sync()


func _process(delta: float) -> void:
    if test_mode and Time.get_ticks_msec() - started > 150000:
        push_error("FLEET_FAIL: internal 150-second watchdog")
        get_tree().quit(2)
    if not capture_lock:
        if not paused:
            time += delta
            for ship in ships:
                ship.advance(delta, time)
            if camera.local_harbor:
                _advance_local_sailing(delta)
                _advance_arrival_transition(delta)
        if not camera_override:
            camera.update_view(ships, delta)
            if local_settling and camera.settled:
                local_settling = false
    sync_water()
    if ui != null:
        coast.set_observing(camera.inspecting or camera.local_harbor)
        ui.refresh()


func _advance_arrival_transition(delta: float) -> void:
    if pending_berths.is_empty():
        return
    if not arrival_transition:
        if not sailing_ships.is_empty():
            return
        for ship in ships:
            if not ship.waypoints.is_empty():
                return
        arrival_transition = true
        arrival_elapsed = 0.0
    var before := arrival_elapsed
    # A stalled frame must not skip the opaque interval and expose a berth jump.
    arrival_elapsed += minf(delta, .1)
    var alpha := clampf(arrival_elapsed / .25, 0, 1) if arrival_elapsed < .45 else clampf((.75 - arrival_elapsed) / .30, 0, 1)
    arrival_cover.color.a = alpha
    if before < .3 and arrival_elapsed >= .3:
        for i in pending_berths:
            ships[i].position = state.world_position(state.ships[i])
            ships[i].rotation = Vector3.ZERO
            ships[i].wake = 0.0
            ships[i].route_progress = 14.5
        camera.auto_subject = pending_berths[-1]
        if not camera_override:
            camera.update_view(ships, 0, true)
    if arrival_elapsed >= .75:
        pending_berths.clear()
        arrival_transition = false
        arrival_cover.color.a = 0.0
        local_settling = true
