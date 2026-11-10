extends Camera3D

const OVERVIEW_OFFSET := Vector3(-20, 46, 24)
const LAYOUT = preload("res://demo/tropical_harbor_3d/environment/harbor_layout.gd")

var focus_ship := -1
var settled := false
var target_position := Vector3.ZERO
var target_size := 30.0
var inspecting := false
var orbit_yaw := -48.0
var orbit_pitch := 20.0
var orbit_distance := 11.5
var ground_sample: Callable
var harbor_points: Array[Vector3] = []


func _ready() -> void:
    projection = Camera3D.PROJECTION_ORTHOGONAL
    keep_aspect = Camera3D.KEEP_HEIGHT
    near = 0.2
    far = 250.0
    position = OVERVIEW_OFFSET
    look_at(Vector3.ZERO)
    make_current()


func update_view(ships: Array, delta: float, snap: bool = false) -> void:
    if inspecting and focus_ship >= 0 and focus_ship < ships.size():
        _update_inspection(ships[focus_ship], delta, snap)
        return
    projection = Camera3D.PROJECTION_ORTHOGONAL
    # Approach selected boats from the open water so the terminal roof cannot
    # hide a berthed hull or intercept clicks on its crew slots.
    var offset := Vector3(-12, 30, 24) if focus_ship >= 0 else OVERVIEW_OFFSET
    var desired := Basis.looking_at(-offset.normalized())
    var rotation_weight := 1.0 if snap else 1.0 - exp(-delta * 7.0)
    global_basis = global_basis.slerp(desired, rotation_weight).orthonormalized()
    var points: Array[Vector3] = []
    if focus_ship >= 0 and focus_ship < ships.size():
        points.append_array(ships[focus_ship].envelope_points())
    else:
        var fleet_center_z := 0.0
        for ship in ships:
            points.append_array(ship.envelope_points())
            fleet_center_z += ship.global_position.z
        fleet_center_z /= maxf(ships.size(), 1)
        points.append_array(LAYOUT.overview_landmarks(fleet_center_z))
        points.append_array(harbor_points)
    frame_points(points, delta, snap, 170.0 if focus_ship >= 0 else 80.0)


func inspect_ship(index: int) -> void:
    inspecting = true
    focus_ship = index
    projection = Camera3D.PROJECTION_PERSPECTIVE
    fov = 45.0


func leave_inspection() -> void:
    inspecting = false
    projection = Camera3D.PROJECTION_ORTHOGONAL


func orbit(relative: Vector2) -> void:
    orbit_yaw = wrapf(orbit_yaw - relative.x * 0.22, -180.0, 180.0)
    orbit_pitch = clampf(orbit_pitch + relative.y * 0.18, 12.0, 65.0)


func zoom_inspection(direction: float) -> void:
    orbit_distance = clampf(orbit_distance * exp(direction * 0.10), 7.0, 24.0)


func _update_inspection(ship: Node3D, delta: float, snap: bool) -> void:
    # Follow the voyage, while allowing the hull to float independently of the eye.
    var target := Vector3(ship.global_position.x, 0.45, ship.global_position.z)
    var yaw := deg_to_rad(orbit_yaw)
    var pitch := deg_to_rad(orbit_pitch)
    var offset := Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch)) * orbit_distance
    var desired := target + offset
    if ground_sample.is_valid():
        desired.y = maxf(desired.y, float(ground_sample.call(desired)) + 0.8)
    var query := PhysicsRayQueryParameters3D.create(target, desired, 4)
    var hit := get_world_3d().direct_space_state.intersect_ray(query)
    if not hit.is_empty():
        desired = hit.position + hit.normal * 0.45
    var weight := 1.0 if snap else 1.0 - exp(-delta * 9.0)
    # Check the final smoothed position too: orbiting must not cut through a pier.
    var candidate := global_position.lerp(desired, weight)
    query.to = candidate
    hit = get_world_3d().direct_space_state.intersect_ray(query)
    if not hit.is_empty():
        candidate = hit.position + hit.normal * 0.45
    if ground_sample.is_valid():
        candidate.y = maxf(candidate.y, float(ground_sample.call(candidate)) + 0.8)
    global_position = candidate
    look_at(target)
    target_position = desired
    settled = global_position.distance_to(desired) < 0.03


func frame_points(points: Array[Vector3], delta: float, snap: bool, bottom: float = 80.0) -> void:
    if points.is_empty():
        return
    var viewport := get_viewport().get_visible_rect().size
    var x_min := INF
    var x_max := -INF
    var y_min := INF
    var y_max := -INF
    var center := Vector3.ZERO
    for point in points:
        center += point
        var x := global_basis.x.dot(point)
        var y := global_basis.y.dot(point)
        x_min = minf(x_min, x)
        x_max = maxf(x_max, x)
        y_min = minf(y_min, y)
        y_max = maxf(y_max, y)
    center /= points.size()
    center += global_basis.x * ((x_min + x_max) * 0.5 - global_basis.x.dot(center))
    center += global_basis.y * ((y_min + y_max) * 0.5 - global_basis.y.dot(center))
    var top := 72.0
    var usable_height := maxf(200.0, viewport.y - top - bottom)
    var usable_width := maxf(300.0, viewport.x - 96.0)
    var fit_height := (y_max - y_min + 1.2) * viewport.y / usable_height
    var fit_width := (x_max - x_min + 1.2) * viewport.y / usable_width
    target_size = maxf(6.8, maxf(fit_height, fit_width))
    var screen_center := (top + viewport.y - bottom) * 0.5
    center += global_basis.y * ((screen_center - viewport.y * 0.5) * target_size / viewport.y)
    target_position = center + global_basis.z * 65.0
    var weight := 1.0 if snap else 1.0 - exp(-delta * 7.0)
    global_position = global_position.lerp(target_position, weight)
    size = lerpf(size, target_size, weight)
    settled = global_position.distance_to(target_position) < 0.01 and absf(size - target_size) < 0.01
