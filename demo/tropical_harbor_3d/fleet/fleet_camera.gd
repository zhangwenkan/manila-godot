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

# Explicit cinematic camera only: gameplay rules decide when to begin/end it.
# A token prevents an interrupted older event from ending a replacement event.
var _pirate_event_serial := 0
var _pirate_event_token := 0
var _pirate_subject: Node3D
var _pirate_island_center := Vector3.ZERO
var _pirate_restore: Dictionary = {}
const PIRATE_EVENT_OFFSET := Vector3(23, 26, 21)


func _ready() -> void:
    projection = Camera3D.PROJECTION_ORTHOGONAL
    keep_aspect = Camera3D.KEEP_HEIGHT
    near = 0.2
    far = 250.0
    position = OVERVIEW_OFFSET
    look_at(Vector3.ZERO)
    make_current()


func update_view(ships: Array, delta: float, snap: bool = false) -> void:
    if _pirate_event_token != 0:
        if not _pirate_owner_unchanged():
            # A new user focus/area/inspection request takes ownership immediately.
            end_pirate_event(_pirate_event_token)
        elif is_instance_valid(_pirate_subject) and _pirate_subject.is_inside_tree():
            _update_pirate_event(delta, snap)
            return
        else:
            # Removed targets interrupt safely and restore the prior camera owner.
            end_pirate_event(_pirate_event_token)
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


func begin_pirate_event(subject: Node3D, island_center: Vector3 = Vector3(-17.5, 0, -14)) -> int:
    if not local_harbor or not reference_art or not is_instance_valid(subject) or not subject.is_inside_tree():
        return 0
    if _pirate_event_token != 0 and not _pirate_owner_unchanged():
        end_pirate_event(_pirate_event_token)
    if _pirate_event_token == 0:
        _pirate_restore = {
            "focus_ship": focus_ship, "auto_subject": auto_subject,
            "area_progress": area_progress, "shot_indices": shot_indices.duplicate(),
            "framed_indices": framed_indices.duplicate(), "inspecting": inspecting,
            "projection": projection, "fov": fov, "size": size,
        }
    _pirate_event_serial += 1
    _pirate_event_token = _pirate_event_serial
    _pirate_subject = subject
    _pirate_island_center = island_center
    settled = false
    return _pirate_event_token


func end_pirate_event(token: int = 0) -> bool:
    if _pirate_event_token == 0 or (token != 0 and token != _pirate_event_token):
        return false
    if _pirate_owner_unchanged():
        focus_ship = _pirate_restore.focus_ship
        auto_subject = _pirate_restore.auto_subject
        area_progress = _pirate_restore.area_progress
        shot_indices.assign(_pirate_restore.shot_indices)
        framed_indices.assign(_pirate_restore.framed_indices)
        inspecting = _pirate_restore.inspecting
        projection = _pirate_restore.projection
        fov = _pirate_restore.fov
        size = _pirate_restore.size
    _pirate_event_token = 0
    _pirate_subject = null
    _pirate_restore.clear()
    settled = false
    return true


func pirate_event_active() -> bool:
    return _pirate_event_token != 0


func _pirate_owner_unchanged() -> bool:
    return focus_ship == _pirate_restore.focus_ship and auto_subject == _pirate_restore.auto_subject \
        and is_equal_approx(area_progress, _pirate_restore.area_progress) \
        and shot_indices == _pirate_restore.shot_indices and inspecting == _pirate_restore.inspecting


func _update_pirate_event(delta: float, snap: bool) -> void:
    projection = Camera3D.PROJECTION_PERSPECTIVE
    fov = local_fov
    var subject := _pirate_subject.global_position
    subject.y = 0
    var target := _pirate_island_center.lerp(subject, .52) + Vector3(0, 2, 0)
    var desired := target + PIRATE_EVENT_OFFSET
    var weight := 1.0 if snap else 1.0 - exp(-delta * 4.0)
    global_position = global_position.lerp(desired, weight)
    local_look = target if snap else local_look.lerp(target, weight)
    look_at(local_look)
    target_position = desired
    settled = global_position.distance_to(desired) < .04 and local_look.distance_to(target) < .04


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
        if reference_art:
            center = _reference_origin(center, progress)
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
    end_pirate_event()
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
    var aim := Vector3(12, 2, -1).lerp(Vector3(7, 2, -1), smoothstep(3.5, 6.0, progress))
    var late_weight := smoothstep(11.5, 13.0, progress)
    var island_z := lerpf(-7.5, -3.4, smoothstep(13.0, 14.0, progress))
    return aim.lerp(Vector3(7, 2, island_z), late_weight)


func _reference_origin(subject: Vector3, progress: float) -> Vector3:
    if progress >= 14.0:
        return Vector3(-14.0, subject.y, subject.z)
    # Leave room for the subject on the widest seaward lane without changing
    # the viewing scale when the other boats are far ahead or behind.
    var origin_x := lerpf(ROUTE.center(progress).x, subject.x, .65)
    origin_x = lerpf(origin_x, -14.0, smoothstep(11.5, 13.0, progress))
    return Vector3(origin_x, subject.y, subject.z)


func _reference_offset(progress: float) -> Vector3:
    var offset := Vector3(-12, 22, 22).lerp(Vector3(-20, 21, 14), smoothstep(3.5, 6.0, progress))
    return offset.lerp(Vector3(-20, 25, 24), smoothstep(11.5, 13.0, progress))


func leave_inspection() -> void:
    end_pirate_event()
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
