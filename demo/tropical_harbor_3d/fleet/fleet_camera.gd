extends Camera3D

const OVERVIEW_OFFSET := Vector3(-20, 46, 24)

var focus_ship := -1
var settled := false
var target_position := Vector3.ZERO
var target_size := 30.0


func _ready() -> void:
    projection = Camera3D.PROJECTION_ORTHOGONAL
    keep_aspect = Camera3D.KEEP_HEIGHT
    near = 0.2
    far = 250.0
    position = OVERVIEW_OFFSET
    look_at(Vector3.ZERO)
    make_current()


func update_view(ships: Array, delta: float, snap: bool = false) -> void:
    var offset := Vector3(12, 30, -33) if focus_ship >= 0 else OVERVIEW_OFFSET
    var desired := Basis.looking_at(-offset.normalized())
    var rotation_weight := 1.0 if snap else 1.0 - exp(-delta * 7.0)
    global_basis = global_basis.slerp(desired, rotation_weight).orthonormalized()
    var points: Array[Vector3] = []
    if focus_ship >= 0 and focus_ship < ships.size():
        points.append_array(ships[focus_ship].envelope_points())
    else:
        for ship in ships:
            points.append_array(ship.envelope_points())
        # Fit the current fleet and harbor, expanding smoothly as ships separate.
        # Empty portions of the full route should not shrink the opening view.
        for x in [2.2, 11.4]:
            for z in [5.8, 12.8]:
                points.append(Vector3(x, 1.6, z))
    frame_points(points, delta, snap, 170.0 if focus_ship >= 0 else 80.0)


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
