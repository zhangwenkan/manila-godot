extends RefCounted
## Native, bounded adaptation of React Bits Lanyard's four-link suspension.
## Reference: https://reactbits.dev/components/lanyard (source inspected 2026-10-20).
## Unlike its 1/960 s tension/inertia solver, this uses 1/120 s planar PBD,
## tension-only length constraints and a damped card pivot. No breeze, intro or flip:
## the full illustration must remain readable inside a small selection panel.

const LINKS := 4
const STEP := 1.0 / 120.0
const ITERATIONS := 18
const GRAVITY := 24.0
const DRAG := 2.8
const ANGULAR_SPRING := 24.0
const ANGULAR_DRAG := 5.5
const MAX_SPEED := 8.0
const HANG := 2.02
const BODY_BOUNDS := AABB(Vector3(-1.33, -1.96, -0.15), Vector3(2.66, 4.15, 0.38))

var nodes: Array[Vector2] = []
var previous: Array[Vector2] = []
var anchor := Vector2.ZERO
var rest := 0.21
var center := Vector2.ZERO
var angle := 0.0
var angular_velocity := 0.0
var yaw := 0.0
var dragging := false
var sleeping := true
var grab_local := Vector2.ZERO
var target := Vector2.ZERO
var safe := Rect2(-2, -2.65, 4, 5.3)
var max_angle := 0.22
# Optional screen-right artwork clearance for a stationary foreground figure.
var artwork_right_limit := INF
var _accumulator := 0.0
var _quiet := 0.0
var _last_center := Vector2.ZERO


func configure(bounds: Rect2, narrow: bool) -> void:
	artwork_right_limit = INF
	safe = bounds
	anchor = Vector2(bounds.get_center().x, bounds.end.y - 0.10)
	max_angle = 0.055 if narrow else 0.20
	reset()


func protect_right_edge(limit: float) -> void:
	artwork_right_limit = limit
	# Both the complete body and the original art must fit at either roll extreme.
	var saved_angle := angle
	while max_angle > 0.001:
		var fits := true
		for direction in [-1.0, 1.0]:
			angle = direction * max_angle
			var low := safe.position.x - _body_footprint().position.x
			var art_right := Vector2(1.2, 0.089).length() * cos(angle) + 1.8 * absf(sin(angle))
			fits = fits and low <= limit - art_right - 0.001
		if fits:
			break
		max_angle *= 0.9
	angle = saved_angle


func reset() -> void:
	nodes.clear()
	previous.clear()
	for i in LINKS + 1:
		var point := anchor + Vector2.DOWN * (-rest * i)
		nodes.append(point)
		previous.append(point)
	angle = 0.0
	angular_velocity = 0.0
	yaw = 0.0
	dragging = false
	sleeping = true
	_accumulator = 0.0
	_quiet = 0.0
	center = nodes[LINKS] - Vector2(0, HANG)
	_last_center = center


func begin(local: Vector2, point: Vector2) -> void:
	grab_local = local
	target = point
	dragging = true
	sleeping = false
	_quiet = 0.0


func release() -> void:
	dragging = false
	_quiet = 0.0


func advance(delta: float) -> bool:
	if sleeping:
		return false
	_accumulator += minf(delta, 0.05)
	while _accumulator >= STEP:
		_step()
		_accumulator -= STEP
	return true


func _step() -> void:
	var old_angle := angle
	var desired := 0.0
	if dragging:
		# Off-centre grips create rotation, without snapping on pointer-down.
		desired = clampf((target.x - center.x - grab_local.x) * -0.25, -max_angle, max_angle)
	angular_velocity += ((desired - angle) * ANGULAR_SPRING - angular_velocity * ANGULAR_DRAG) * STEP
	angle = clampf(angle + angular_velocity * STEP, -max_angle, max_angle)
	var attach := Vector2(0, HANG).rotated(angle)
	var grab := grab_local.rotated(angle)
	var old_nodes := nodes.duplicate()
	for i in range(1, LINKS + 1):
		var velocity := ((nodes[i] - previous[i]) / STEP).limit_length(MAX_SPEED) * exp(-DRAG * STEP)
		previous[i] = nodes[i]
		nodes[i] += velocity * STEP + Vector2(0, -GRAVITY) * STEP * STEP
	var desired_pin := target - grab + attach
	desired_pin = anchor + (desired_pin - anchor).limit_length(rest * LINKS * 0.99)
	# Include sidewall depth at every allowed yaw, retaining the asymmetric top hardware.
	var footprint := _body_footprint()
	var low := safe.position - footprint.position
	var high := safe.end - footprint.end
	if is_finite(artwork_right_limit):
		var art_right := Vector2(1.2, 0.089).length() * cos(angle) + 1.8 * absf(sin(angle))
		high.x = maxf(low.x, minf(high.x, artwork_right_limit - art_right))
	desired_pin = (desired_pin - attach).clamp(low, high) + attach
	# Extra vertical letterboxing is not rope travel above the fixed suspension.
	desired_pin.y = minf(desired_pin.y, anchor.y - 0.02)
	for iteration in ITERATIONS:
		nodes[0] = anchor
		if dragging:
			nodes[LINKS] = nodes[LINKS].lerp(desired_pin, 0.65)
		for i in LINKS:
			var difference := nodes[i + 1] - nodes[i]
			var length := difference.length()
			if length <= rest:
				continue
			var correction := difference * (1.0 - rest / length)
			if i == 0:
				nodes[i + 1] -= correction
			else:
				nodes[i] += correction * 0.5
				nodes[i + 1] -= correction * 0.5
		var body := nodes[LINKS] - attach
		nodes[LINKS] = body.clamp(low, high) + attach
		nodes[LINKS].y = minf(nodes[LINKS].y, anchor.y - 0.02)
		for i in range(1, LINKS):
			nodes[i] = nodes[i].clamp(safe.position + Vector2.ONE * 0.10, Vector2(safe.end.x - 0.10, anchor.y))
	center = nodes[LINKS] - attach
	var speed := (center - _last_center) / STEP
	_last_center = center
	# Restrained out-of-plane tilt reveals the sleeve edge without hiding the art.
	if not dragging:
		yaw = lerpf(yaw, clampf(-speed.x * 0.09, -0.18, 0.18), 1.0 - exp(-8.0 * STEP))
	var energy := speed.length_squared() + angular_velocity * angular_velocity + yaw * yaw
	for i in range(1, LINKS):
		energy += nodes[i].distance_squared_to(old_nodes[i]) / (STEP * STEP) * 0.05
	if not dragging and energy < 0.002 and absf(angle) < 0.003:
		_quiet += STEP
	else:
		_quiet = 0.0
	if _quiet > 0.8:
		reset()
	if not center.is_finite() or not is_finite(angle) or not is_finite(old_angle):
		reset()


func _body_footprint() -> Rect2:
	# A yaw-independent radius bounds X/Z; keep the unequal top/bottom extents in Y.
	var radius := Vector2(BODY_BOUNDS.end.x, maxf(absf(BODY_BOUNDS.position.z), absf(BODY_BOUNDS.end.z))).length()
	var projected := Rect2(Vector2(-radius, BODY_BOUNDS.position.y).rotated(angle), Vector2.ZERO)
	for corner: Vector2 in [Vector2(radius, BODY_BOUNDS.position.y), Vector2(radius, BODY_BOUNDS.end.y), Vector2(-radius, BODY_BOUNDS.end.y)]:
		projected = projected.expand(corner.rotated(angle))
	return projected


func max_link_error() -> float:
	var error := 0.0
	for i in LINKS:
		error = maxf(error, maxf(0.0, nodes[i].distance_to(nodes[i + 1]) - rest))
	return error
