extends Camera3D

const ROUTE = preload("res://demo/tropical_harbor_3d/fleet/harbor_route.gd")

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
var local_harbor := false
var reference_art := false
# Kept for the archived layout comparison harness; player poses use ROUTE.
var local_offset := Vector3(18, 28, 36)
var local_fov := 48.0
var shot_indices: Array[int] = []
var framed_indices: Array[int] = []
var auto_subject := 1
var area_progress := -1.0
var local_look := Vector3.ZERO


func _ready() -> void:
    projection = Camera3D.PROJECTION_ORTHOGONAL
    keep_aspect = Camera3D.KEEP_HEIGHT
    near = 0.2
    far = 250.0
    position = OVERVIEW_OFFSET
    look_at(Vector3.ZERO)
    make_current()


func update_view(ships: Array, delta: float, snap: bool = false) -> void:
    if local_harbor:
        _update_local_harbor(ships, delta, snap)
        return
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


func _update_local_harbor(ships: Array, delta: float, snap: bool) -> void:
    projection = Camera3D.PROJECTION_PERSPECTIVE
    fov = local_fov
    var indices: Array[int] = shot_indices.duplicate()
    if indices.is_empty():
        var primary := focus_ship if focus_ship >= 0 else auto_subject
        primary = clampi(primary, 0, ships.size() - 1)
        indices.append(primary)
        if focus_ship < 0:
            for i in ships.size():
                # The shoreline composition can include all nearby lanes.
                # Distant boats never change the fixed viewing scale.
                if i != primary and absf(ships[i].route_progress - ships[primary].route_progress) <= 2.1:
                    var candidate: Array[int] = indices.duplicate()
                    candidate.append(i)
                    var points: Array = []
                    var headings: Array = []
                    for j in candidate:
                        points.append(ships[j].position)
                        headings.append(ships[j].rotation.y)
                    var screen := get_viewport().get_visible_rect().size
                    var fits := _fits_reference(points, headings, ships[primary].route_progress, screen.x / screen.y) if reference_art else ROUTE.fits_local_shot(points, headings, ships[primary].route_progress, screen.x / screen.y, local_fov, get_world_3d().direct_space_state)
                    if fits:
                        indices.append(i)
    framed_indices.assign(indices)
    var progress: float = ships[indices[0]].route_progress
    var center: Vector3 = _reference_origin(ships[indices[0]].position, progress) if reference_art else ROUTE.framing_origin(ships[indices[0]].position, progress)
    if area_progress >= 0:
        progress = area_progress
        center = ROUTE.center(progress) if progress < 14 else Vector3(-.85, 0, -16.6)
    # Favor the waterfront beyond the boat, not the landward side of a roof.
    var target := center + ROUTE.aim_offset(progress)
    var offset := ROUTE.offset(progress)
    if reference_art:
        target = center + _reference_aim(progress)
        offset = _reference_offset(progress)
    var desired := target + offset
    var weight := 1.0 if snap else 1.0 - exp(-delta * 5.0)
    global_position = global_position.lerp(desired, weight)
    local_look = target if snap else local_look.lerp(target, weight)
    look_at(local_look)
    target_position = desired
    settled = global_position.distance_to(desired) < .04 and local_look.distance_to(target) < .04


func inspect_ship(index: int) -> void:
    inspecting = true
    focus_ship = index
    projection = Camera3D.PROJECTION_PERSPECTIVE
    fov = 45.0


func _fits_reference(points: Array, headings: Array, progress: float, aspect: float) -> bool:
    var offset := _reference_offset(progress)
    var eye := _reference_origin(points[0], progress) + _reference_aim(progress) + offset
    var view_basis := Basis.looking_at(-offset.normalized())
    var vertical := tan(deg_to_rad(local_fov) * .5)
    for i in points.size():
        var turn := Basis(Vector3.UP, headings[i])
        for x in [-1.05, 1.05]:
            for y in [-.4, 2.2]:
                for z in [-2.55, 2.55]:
                    var relative: Vector3 = points[i] + turn * Vector3(x, y, z) - eye
                    var depth := -relative.dot(view_basis.z)
                    if depth <= 0 or absf(relative.dot(view_basis.x)) > depth * vertical * aspect * .90 or absf(relative.dot(view_basis.y)) > depth * vertical * .82:
                        return false
        var ray := PhysicsRayQueryParameters3D.create(eye, points[i] + Vector3(0, .5, 0), 4)
        if not get_world_3d().direct_space_state.intersect_ray(ray).is_empty():
            return false
    return true


func _reference_aim(progress: float) -> Vector3:
    # Opening fleet and working harbor share a composed local view. Once the
    # approach ends, bring the nearby street into view without showing the map.
    return Vector3(12, 2, -1).lerp(Vector3(7, 2, -1), smoothstep(3.5, 6.0, progress))


func _reference_origin(subject: Vector3, progress: float) -> Vector3:
    if progress >= 14.0:
        return subject
    # Leave room for the subject on the widest seaward lane without changing
    # the viewing scale when the other boats are far ahead or behind.
    return Vector3(lerpf(ROUTE.center(progress).x, subject.x, .65), subject.y, subject.z)


func _reference_offset(progress: float) -> Vector3:
    return Vector3(-12, 22, 22).lerp(Vector3(-20, 21, 14), smoothstep(3.5, 6.0, progress))


func leave_inspection() -> void:
    inspecting = false
    projection = Camera3D.PROJECTION_ORTHOGONAL


func orbit(relative: Vector2) -> void:
    if local_harbor:
        return
    orbit_yaw = wrapf(orbit_yaw - relative.x * 0.22, -180.0, 180.0)
    orbit_pitch = clampf(orbit_pitch + relative.y * 0.18, 12.0, 65.0)


func zoom_inspection(direction: float) -> void:
    if local_harbor:
        return
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
