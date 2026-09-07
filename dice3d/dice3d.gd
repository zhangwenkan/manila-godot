extends RigidBody3D
class_name Dice3D

signal settled
signal dice_stopped(final_value: int)

const FACE_SHADER = preload("res://dice3d/dice_face.gdshader")
const FACE_NORMALS: Array[Vector3] = [Vector3.UP, Vector3.BACK, Vector3.RIGHT, Vector3.LEFT, Vector3.FORWARD, Vector3.DOWN]

@export var base_color: Color = Color("#9bc49d")
@export var top_color: Color = Color("#bfdab6")
@export var side_color: Color = Color("#79a47c")
@export var separator_color: Color = Color("#cfe5c4")
@export var outline_color: Color = Color("#273d2c")
@export var dot_color: Color = Color("#4656c8")
@export var mesh_size: float = 0.95
@export var corner_radius: float = 0.35
@export var settle_linear_threshold: float = 0.04
@export var settle_angular_threshold: float = 0.06
@export var settle_hold_time: float = 0.55

var target_value: int = 1
var is_rolling_flag: bool = false
var settle_with_group: bool = false
var _debug_mode: bool = false
var _settle_timer: float = 0.0
var _mesh_root: Node3D
var _collision: CollisionShape3D
var _pending_impulse: Vector3 = Vector3.ZERO
var _pending_torque: Vector3 = Vector3.ZERO
var _has_pending_throw: bool = false


func _ready() -> void:
	continuous_cd = true
	contact_monitor = true
	max_contacts_reported = 8
	gravity_scale = 1.0
	can_sleep = true
	sleeping = true
	freeze = true
	_build_visual_and_collision()
	_apply_orientation_for_value(target_value)


func set_value(value: int) -> void:
	target_value = clampi(value, 1, 6)
	_has_pending_throw = false
	freeze = true
	sleeping = true
	linear_velocity = Vector3.ZERO
	angular_velocity = Vector3.ZERO
	is_rolling_flag = false
	_apply_orientation_for_value(target_value)


func get_value() -> int:
	return target_value


func is_rolling() -> bool:
	return is_rolling_flag


func throw() -> void:
	roll()


func roll(impulse: Vector3 = Vector3.ZERO, torque: Vector3 = Vector3.ZERO) -> void:
	if is_rolling_flag:
		return
	is_rolling_flag = true
	_debug_mode = false
	_settle_timer = 0.0
	freeze = false
	sleeping = false
	linear_velocity = Vector3.ZERO
	angular_velocity = Vector3.ZERO
	_pending_impulse = impulse if not impulse.is_zero_approx() else Vector3(randf_range(-4.5, 4.5), randf_range(4.0, 5.5), randf_range(-3.0, 3.0))
	_pending_torque = torque if not torque.is_zero_approx() else Vector3(randf_range(-1.4, 1.4), randf_range(-1.4, 1.4), randf_range(-1.4, 1.4))
	_has_pending_throw = true


func enable_debug_inspect() -> void:
	if is_rolling_flag:
		return
	_debug_mode = true


func disable_debug_inspect() -> void:
	_debug_mode = false


func handle_debug_input(event: InputEvent, screen_rect: Rect2) -> bool:
	if not _debug_mode:
		return false
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		if screen_rect.has_point(event.position):
			set_value((target_value % 6) + 1)
			return true
	return false


func _physics_process(delta: float) -> void:
	if _has_pending_throw and not freeze:
		apply_central_impulse(_pending_impulse)
		apply_torque_impulse(_pending_torque)
		_has_pending_throw = false
		return
	if not is_rolling_flag or _debug_mode:
		return
	var lin := linear_velocity.length()
	var ang := angular_velocity.length()
	var top_normal := global_basis * FACE_NORMALS[_detect_top_face() - 1]
	if (sleeping or get_contact_count() > 0) and lin < 0.35 and ang < 1.0 and top_normal.dot(Vector3.UP) < cos(deg_to_rad(0.5)):
		_settle_timer = 0.0
		return
	if sleeping or (get_contact_count() > 0 and lin < settle_linear_threshold and ang < settle_angular_threshold):
		_settle_timer += delta
		if not settle_with_group and has_settled():
			_finish_roll()
	else:
		_settle_timer = 0.0


func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
	if not is_rolling_flag or _has_pending_throw or state.get_contact_count() == 0:
		return
	if state.linear_velocity.length() > 0.35 or state.angular_velocity.length() > 1.0:
		return
	var top_normal := state.transform.basis * FACE_NORMALS[_detect_top_face() - 1]
	var tilted := top_normal.dot(Vector3.UP) < cos(deg_to_rad(0.5))
	var raised := state.transform.origin.y > mesh_size * 0.5 + 0.03
	if not tilted and not raised:
		return
	# A die caught on the rim must clear its contact before it can lie flat.
	# Apply forces during settlement, without assigning a result or a new pose.
	state.sleeping = false
	_settle_timer = 0.0
	var clearance := Vector3.ZERO
	for contact in state.get_contact_count():
		var normal := state.get_contact_local_normal(contact)
		if normal.y < 0.999:
			clearance += Vector3(normal.x, 0.0, normal.z)
	if raised and state.transform.origin.y > mesh_size * 0.5 + 0.15:
		clearance = Vector3(-state.transform.origin.x, 0.0, -state.transform.origin.z)
	if not clearance.is_zero_approx():
		state.apply_central_force(clearance.normalized() * 9.0)
	elif raised and not tilted:
		state.apply_central_force(Vector3(1.0, 0.0, 0.37).normalized() * 9.0)
	var horizontal_spin := Vector3(state.angular_velocity.x, 0.0, state.angular_velocity.z)
	state.apply_torque(top_normal.cross(Vector3.UP) * 10.0 - horizontal_spin * 1.5)


func has_settled() -> bool:
	var top_normal := global_basis * FACE_NORMALS[_detect_top_face() - 1]
	return is_rolling_flag and global_position.y < mesh_size * 0.5 + 0.03 and top_normal.dot(Vector3.UP) >= cos(deg_to_rad(0.5)) and (sleeping or _settle_timer >= settle_hold_time)


func _finish_roll() -> void:
	if not is_rolling_flag:
		return
	# Read the physical pose without changing it, velocities, or sleep state.
	target_value = _detect_top_face()
	is_rolling_flag = false
	dice_stopped.emit(target_value)
	settled.emit()


func _detect_top_face() -> int:
	var best_value := 1
	var best_dot := -999.0
	for i in FACE_NORMALS.size():
		var world_n := global_transform.basis * FACE_NORMALS[i]
		var d := world_n.dot(Vector3.UP)
		if d > best_dot:
			best_dot = d
			best_value = i + 1
	return best_value


func _apply_orientation_for_value(value: int) -> void:
	var face_normal := FACE_NORMALS[clampi(value, 1, 6) - 1]
	var face_basis := Basis(Vector3.RIGHT, PI) if face_normal == Vector3.DOWN else Basis(Quaternion(face_normal, Vector3.UP))
	global_transform.basis = face_basis.rotated(Vector3.UP, deg_to_rad(45.0))
	global_position.y = maxf(global_position.y, mesh_size * 0.5)


func _build_visual_and_collision() -> void:
	var physics_mat := PhysicsMaterial.new()
	physics_mat.bounce = 0.38
	physics_mat.friction = 0.68
	physics_material_override = physics_mat
	mass = 1.0
	linear_damp = 0.06
	angular_damp = 0.32

	_collision = CollisionShape3D.new()
	_mesh_root = Node3D.new()
	_mesh_root.name = "PixelRoundedMesh"
	add_child(_mesh_root)

	var mesh := ArrayMesh.new()
	var outline := StandardMaterial3D.new()
	outline.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	outline.albedo_color = outline_color
	outline.cull_mode = BaseMaterial3D.CULL_FRONT
	outline.grow = true
	outline.grow_amount = mesh_size * 0.014
	for i in FACE_NORMALS.size():
		_add_rounded_surface(mesh, FACE_NORMALS[i])
		var material := ShaderMaterial.new()
		material.shader = FACE_SHADER
		material.set_shader_parameter("face_mask", _make_face_texture(i + 1))
		material.set_shader_parameter("face_normal", FACE_NORMALS[i])
		material.set_shader_parameter("top_color", top_color)
		material.set_shader_parameter("base_color", base_color)
		material.set_shader_parameter("side_color", side_color)
		material.set_shader_parameter("separator_color", separator_color)
		material.set_shader_parameter("dot_color", dot_color)
		# Only backfaces of the expanded mesh draw: no dark shell over the seams.
		material.next_pass = outline
		mesh.surface_set_material(i, material)
	var body := MeshInstance3D.new()
	body.name = "RoundedBody"
	body.mesh = mesh
	_mesh_root.add_child(body)
	# Broad, flat contacts keep the decorative round corners from resting at a tilt.
	var box_shape := BoxShape3D.new()
	box_shape.size = Vector3.ONE * mesh_size
	_collision.shape = box_shape
	add_child(_collision)


func _add_rounded_surface(mesh: ArrayMesh, face_normal: Vector3) -> void:
	const SEGMENTS := 32
	var half_size := mesh_size * 0.5
	var radius := clampf(corner_radius, 0.01, half_size * 0.95)
	var inner := Vector3.ONE * (half_size - radius)
	var axis_u := Vector3.RIGHT if absf(face_normal.y) > 0.5 else Vector3.UP.cross(face_normal)
	var axis_v := face_normal.cross(axis_u)
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()
	var indices := PackedInt32Array()
	for y in range(SEGMENTS + 1):
		for x in range(SEGMENTS + 1):
			var uv := Vector2(x, y) / float(SEGMENTS)
			var cube_point := face_normal * half_size + (axis_u * (uv.x - 0.5) + axis_v * (uv.y - 0.5)) * mesh_size
			var core_point := cube_point.clamp(-inner, inner)
			var normal := (cube_point - core_point).normalized()
			vertices.append(core_point + normal * radius)
			normals.append(normal)
			uvs.append(uv)
			if x < SEGMENTS and y < SEGMENTS:
				var start := y * (SEGMENTS + 1) + x
				var below := start + SEGMENTS + 1
				indices.append_array(PackedInt32Array([start, below, start + 1, start + 1, below, below + 1]))
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_INDEX] = indices
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)


func _make_face_texture(face_value: int) -> ImageTexture:
	const TEXTURE_SIZE := 64
	var img := Image.create(TEXTURE_SIZE, TEXTURE_SIZE, false, Image.FORMAT_RGB8)
	# R is the round green panel; G is the pip mask. Both follow the curved mesh.
	for y in range(TEXTURE_SIZE):
		for x in range(TEXTURE_SIZE):
			var uv := Vector2(x + 0.5, y + 0.5) / float(TEXTURE_SIZE)
			var distance := uv.distance_to(Vector2(0.5, 0.5))
			var panel := 1.0 - smoothstep(0.477, 0.499, distance)
			img.set_pixel(x, y, Color(panel, 0.0, 0.0))
	for dot: Vector2 in get_dots_positions(face_value):
		var center := Vector2.ONE * (TEXTURE_SIZE * 0.5) + dot * (TEXTURE_SIZE * 0.31)
		for y in range(int(center.y) - 4, int(center.y) + 5):
			for x in range(int(center.x) - 4, int(center.x) + 5):
				if Vector2(x + 0.5, y + 0.5).distance_squared_to(center) <= 4.2 * 4.2:
					img.set_pixel(x, y, Color(1.0, 1.0, 0.0))
	return ImageTexture.create_from_image(img)


func get_dots_positions(value: int) -> Array[Vector2]:
	match value:
		1: return [Vector2(0, 0)]
		2: return [Vector2(-0.55, -0.55), Vector2(0.55, 0.55)]
		3: return [Vector2(-0.55, -0.55), Vector2(0, 0), Vector2(0.55, 0.55)]
		4: return [Vector2(-0.55, -0.55), Vector2(0.55, -0.55), Vector2(-0.55, 0.55), Vector2(0.55, 0.55)]
		5: return [Vector2(-0.55, -0.55), Vector2(0.55, -0.55), Vector2(0, 0), Vector2(-0.55, 0.55), Vector2(0.55, 0.55)]
		6: return [Vector2(-0.55, -0.55), Vector2(0.55, -0.55), Vector2(-0.55, 0), Vector2(0.55, 0), Vector2(-0.55, 0.55), Vector2(0.55, 0.55)]
	return []
