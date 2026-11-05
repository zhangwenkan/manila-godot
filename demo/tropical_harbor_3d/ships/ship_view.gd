extends Node3D

const GEOMETRY = preload("res://demo/tropical_harbor_3d/ships/cargo_factory.gd")
const STATE = preload("res://demo/tropical_harbor_3d/fleet/fleet_state.gd")
const BOAT = preload("res://demo/tropical_harbor_3d/assets/fleet_boat_mcp.glb")
# Replacement models use feet at Y=0 and face -Z; these are maximum body envelopes.
const PAWN_SIZE := Vector3(0.42, 0.90, 0.38)
const DECK_HEIGHT := 0.28
const SLOT_POINTS := [Vector3(-0.48, DECK_HEIGHT, -0.67), Vector3(0.48, DECK_HEIGHT, -0.67),
    Vector3(-0.48, DECK_HEIGHT, 0.67), Vector3(0.48, DECK_HEIGHT, 0.67)]
const SUPPORTS := [Vector3(0, 0, -2.05), Vector3(0, 0, 2.05), Vector3(-0.72, 0, 0),
    Vector3(0.72, 0, 0), Vector3(0, 0, 0)]

var ship_id := -1
var cargo_id := ""
var slot_roots: Array[Node3D] = []
var slot_areas: Array[Area3D] = []
var indicators: Array[Node3D] = []
var pawn_roots: Array[Node3D] = []
var selected := false
var wake := 0.0
var moving := false
var waypoints: Array[Vector3] = []
var selected_slot := -1
var hull_area: Area3D
var cargo_root: Node3D
var wave_sample: Callable


func build(data: Dictionary) -> void:
    ship_id = data.ship_id
    cargo_id = data.cargo_id
    name = "Ship%d" % ship_id
    var hull := BOAT.instantiate()
    add_child(hull)
    _tune_boat_wood(hull)
    cargo_root = GEOMETRY.make(cargo_id)
    cargo_root.position = Vector3(0, DECK_HEIGHT, 0)
    add_child(cargo_root)
    hull_area = _area(self, Vector3(0, 0.30, 0), Vector3(1.9, 0.65, 4.7), 1, -1)
    var flag_mat := StandardMaterial3D.new()
    flag_mat.albedo_color = STATE.CARGO[cargo_id].color
    GEOMETRY.box(self, Vector3(0.14, 0.97, 1.91), Vector3(0.26, 0.16, 0.018), flag_mat)
    for i in data.slots.size():
        var anchor := Node3D.new()
        anchor.name = "CrewAnchor%d" % i
        anchor.position = SLOT_POINTS[i]
        add_child(anchor)
        slot_roots.append(anchor)
        var pawn := Node3D.new()
        pawn.name = "PawnRoot"
        anchor.add_child(pawn)
        pawn_roots.append(pawn)
        var marker := Node3D.new()
        marker.name = "Vacancy"
        anchor.add_child(marker)
        var ring := TorusMesh.new()
        ring.inner_radius = 0.15
        ring.outer_radius = 0.19
        ring.rings = 20
        ring.ring_segments = 8
        GEOMETRY.mesh(marker, ring, Vector3(0, 0.025, 0), GEOMETRY.material("f4d79c"))
        var label := Label3D.new()
        label.text = str(i + 1)
        label.font_size = 48
        label.pixel_size = 0.004
        label.position = Vector3(0, 0.23, 0)
        label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
        label.modulate = Color("fff0c4")
        marker.add_child(label)
        indicators.append(marker)
        slot_areas.append(_area(anchor, Vector3(0, 0.23, 0), Vector3(0.46, 0.48, 0.46), 0, i))
    sync_crew(data)
    set_selected(false)


func _area(parent: Node3D, at: Vector3, size_: Vector3, layer: int, slot_id: int) -> Area3D:
    var area := Area3D.new()
    area.position = at
    area.collision_layer = layer
    area.collision_mask = 0
    area.set_meta("ship_id", ship_id)
    area.set_meta("slot_id", slot_id)
    parent.add_child(area)
    var collision := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = size_
    collision.shape = shape
    area.add_child(collision)
    return area


func sync_crew(data: Dictionary) -> void:
    for i in pawn_roots.size():
        var pawn := pawn_roots[i]
        var owner: int = data.slots[i].owner
        if pawn.get_meta("owner", -2) == owner:
            continue
        for child in pawn.get_children():
            pawn.remove_child(child)
            child.queue_free()
        pawn.set_meta("owner", owner)
        if owner < 0:
            continue
        var coat := StandardMaterial3D.new()
        coat.albedo_color = STATE.PLAYER_COLORS[owner % STATE.PLAYER_COLORS.size()]
        var skin := GEOMETRY.material("d7aa7e")
        var dark := GEOMETRY.material("514436")
        for side in [-1, 1]:
            GEOMETRY.box(pawn, Vector3(side * 0.075, 0.13, 0), Vector3(0.105, 0.25, 0.13), dark)
            var arm := GEOMETRY.cylinder(pawn, Vector3(side * 0.155, 0.43, 0), 0.035, 0.27, coat)
            arm.rotation.z = side * 0.12
        GEOMETRY.cylinder(pawn, Vector3(0, 0.43, 0), 0.13, 0.32, coat, 0.11)
        GEOMETRY.sphere(pawn, Vector3(0, 0.69, -0.005), Vector3(0.23, 0.25, 0.22), skin)
        GEOMETRY.cylinder(pawn, Vector3(0, 0.81, 0), 0.15, 0.035, dark)
        GEOMETRY.cylinder(pawn, Vector3(0, 0.855, 0), 0.10, 0.07, coat)
    set_selected(selected)


func set_selected(value: bool, slot: int = -1) -> void:
    selected = value
    selected_slot = slot
    for i in indicators.size():
        indicators[i].visible = selected and int(pawn_roots[i].get_meta("owner", -1)) == -1
        indicators[i].scale = Vector3.ONE * (1.15 if selected_slot == i else 1.0)
        slot_areas[i].collision_layer = 2 if selected else 0


func travel_to(target: Vector3, arrived: bool) -> void:
    waypoints.clear()
    if arrived and position.z > -11.0:
        waypoints.append(Vector3(position.x, 0, -11.0))
    waypoints.append(target)


func advance(delta: float, time_: float) -> void:
    moving = not waypoints.is_empty()
    if moving:
        var target := waypoints[0]
        var flat := Vector3(position.x, 0, position.z)
        var next := flat.move_toward(target, delta * 2.0)
        var direction := next - flat
        if direction.length_squared() > 0.000001:
            rotation.y = lerp_angle(rotation.y, atan2(-direction.x, -direction.z), minf(1, delta * 5))
        position.x = next.x
        position.z = next.z
        if next.distance_to(target) < 0.001:
            waypoints.pop_front()
    elif position.z < -11.0:
        rotation.y = lerp_angle(rotation.y, 0, minf(1, delta * 4))
    wake = move_toward(wake, 1.0 if moving else 0.0, delta * 0.8)
    _float_on_water(time_)


func _float_on_water(time_: float) -> void:
    if not wave_sample.is_valid():
        position.y = sin(time_ * 1.1 + ship_id * 1.8) * 0.034
        rotation.z = sin(time_ * 0.92 + ship_id) * 0.012
        rotation.x = sin(time_ * 0.77 + ship_id + 0.7) * 0.009
        return
    var yaw := Basis(Vector3.UP, rotation.y)
    var origin := Vector3(position.x, 0.0, position.z)
    var heights: Array[float] = []
    for local in SUPPORTS:
        var world: Vector3 = origin + yaw * local
        heights.append(float(wave_sample.call(world.x, world.z, time_)))
    position.y = (heights[0] + heights[1] + heights[2] + heights[3] + heights[4]) * 0.17
    rotation.x = clampf(atan2(heights[0] - heights[1], 4.1) * 0.55, -0.04, 0.04)
    rotation.z = clampf(atan2(heights[2] - heights[3], 1.44) * 0.55, -0.05, 0.05)


func _tune_boat_wood(root: Node) -> void:
    var tuned: Dictionary = {}
    for item in root.find_children("*", "MeshInstance3D", true, false):
        var mesh := item as MeshInstance3D
        if mesh.mesh == null:
            continue
        for surf in mesh.mesh.get_surface_count():
            var src := mesh.get_active_material(surf)
            if src == null or not (src is StandardMaterial3D):
                continue
            if not tuned.has(src):
                var wood := (src as StandardMaterial3D).duplicate() as StandardMaterial3D
                wood.vertex_color_use_as_albedo = false
                wood.metallic = 0.0
                wood.roughness = 0.90
                wood.metallic_specular = 0.2
                wood.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
                wood.albedo_color = Color.WHITE
                tuned[src] = wood
            mesh.set_surface_override_material(surf, tuned[src])


func envelope_points() -> Array[Vector3]:
    var result: Array[Vector3] = []
    for x in [-1.0, 1.0]:
        for y in [-0.35, DECK_HEIGHT + PAWN_SIZE.y + 0.05]:
            for z in [-2.5, 2.5]:
                result.append(to_global(Vector3(x, y, z)))
    return result
