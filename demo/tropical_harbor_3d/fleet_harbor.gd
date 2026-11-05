extends Node3D

const ENVIRONMENT = preload("res://demo/tropical_harbor_3d/environment/harbor_environment.gd")
const STATE = preload("res://demo/tropical_harbor_3d/fleet/fleet_state.gd")
const SHIP = preload("res://demo/tropical_harbor_3d/ships/ship_view.gd")
const CAMERA = preload("res://demo/tropical_harbor_3d/fleet/fleet_camera.gd")
const UI = preload("res://demo/tropical_harbor_3d/ui/fleet_interaction.gd")
const PIER = preload("res://demo/tropical_harbor_3d/environment/pier_builder.gd")
const WATER = preload("res://demo/tropical_harbor_3d/materials/fleet_water.gdshader")
const REFLECTION = preload("res://demo/tropical_harbor_3d/environment/water_reflection.gd")

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


func _ready() -> void:
    environment = ENVIRONMENT.new(self)
    environment.water_shader = WATER
    environment._build_environment()
    if not "--art-preview" in OS.get_cmdline_user_args():
        configure_art_shadows()
    environment._build_water()
    environment._build_sand()
    environment._build_swash()
    environment._build_contact_stones()
    var pier := PIER.new()
    pier.build(self, environment)
    var contacts: PackedVector4Array = environment.contact_objects.duplicate()
    contacts.append_array(pier.contacts)
    environment.set_contacts(contacts, 32)
    camera = CAMERA.new()
    camera.name = "FleetCamera"
    add_child(camera)
    reflection = REFLECTION.new()
    add_child(reflection)
    reflection.setup(self, camera)
    reflection.set_enabled(false)
    rng.randomize()
    state.start_voyage(["jade", "silk", "ginseng"], [0, 4, 5])
    rebuild_ships()
    var piers := get_node_or_null("TimberPiers")
    if piers != null:
        reflection.add_subject(piers)
    environment.water_material.set_shader_parameter("reflection_tex", reflection.texture())
    ui = UI.new()
    add_child(ui)
    ui.build(self)
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
    sun.light_angular_distance = 0.85
    sun.directional_shadow_max_distance = 100.0
    sun.shadow_normal_bias = 0.6
    RenderingServer.directional_shadow_atlas_set_size(4096, true)
    RenderingServer.directional_soft_shadow_filter_set_quality(RenderingServer.SHADOW_QUALITY_SOFT_HIGH)


func rebuild_ships() -> void:
    selected = -1
    camera.focus_ship = -1
    for ship in ships:
        remove_child(ship)
        ship.queue_free()
    ships.clear()
    for data in state.ships:
        var ship := SHIP.new()
        add_child(ship)
        ship.build(data)
        ship.wave_sample = Callable(environment, "wave_height")
        ship.position = state.world_position(data)
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
    for i in 3:
        var target: Vector3 = state.world_position(state.ships[i])
        if Vector3(ships[i].position.x, 0, ships[i].position.z).distance_to(target) > 0.01:
            ships[i].travel_to(target, state.ships[i].arrived)
    ui.refresh()


func select_ship(index: int) -> void:
    selected = index
    camera.focus_ship = index
    camera_override = false
    ui.selected_slot = -1
    ui.info = false
    for i in 3:
        ships[i].set_selected(i == index)
    ui.refresh()


func overview() -> void:
    selected = -1
    camera.focus_ship = -1
    camera_override = false
    ui.selected_slot = -1
    ui.info = false
    for ship in ships:
        ship.set_selected(false)
    ui.refresh()


func view_piers() -> void:
    overview()
    camera_override = true
    camera.position = Vector3(15, 12.55, 23.4)
    camera.look_at(Vector3(7, 0.55, 9.4))
    camera.size = 8.2


func toggle_pause() -> void:
    paused = not paused
    ui.refresh()


func is_moving() -> bool:
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
            KEY_SPACE: toggle_pause()
            KEY_ESCAPE: get_tree().quit()
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
        if not camera_override:
            camera.update_view(ships, delta)
    sync_water()
    if ui != null:
        ui.refresh()
