extends Node2D
class_name Dice2D

# ==============================================
# 3渲2 圆角骰子：
# - 主场景仍是 2D
# - 内部用 SubViewport 渲染 3D 骰子模型
# - 保留现有触发接口：throw / roll / set_value / settled
# ==============================================
@export var dice_size: int = 160
@export var viewport_size: int = 256
@export var base_color: Color = Color("#88d8b0")
@export var top_color: Color = Color("#dff7ea")
@export var side_color: Color = Color("#6fb99a")
@export var outline_color: Color = Color("#101018")
@export var dot_color: Color = Color("#4f66c8")
@export var edge_color: Color = Color("#f4fff8")
@export var roll_duration: float = 1.15
@export var settle_duration: float = 0.35

signal settled
signal dice_stopped(final_value: int)

var is_rolling_flag: bool = false
var target_value: int = 1
var current_frame: int = 0

var _sprite: Sprite2D
var _viewport: SubViewport
var _world_root: Node3D
var _dice_root: Node3D
var _camera: Camera3D
var _light: DirectionalLight3D
var _face_meshes: Dictionary = {}
var _roll_tween: Tween
var _debug_mode: bool = false


func _ready() -> void:
	_build_projection_chain()
	_build_dice_mesh()
	_update_materials_for_value(target_value)
	_apply_face_basis(target_value)
	_refresh_projection()


func set_value(value: int) -> void:
	target_value = clampi(value, 1, 6)
	current_frame = target_value - 1
	_update_materials_for_value(target_value)
	_apply_face_basis(target_value)
	_refresh_projection()


func get_value() -> int:
	return target_value


func is_rolling() -> bool:
	return is_rolling_flag


func throw(final_value: int = -1) -> void:
	roll(final_value)


func roll(target: int = 0) -> void:
	if is_rolling_flag:
		return

	is_rolling_flag = true
	_debug_mode = false
	target_value = target if target >= 1 and target <= 6 else randi_range(1, 6)
	current_frame = target_value - 1
	if _viewport:
		_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS

	if _roll_tween and _roll_tween.is_valid():
		_roll_tween.kill()

	var start_q: Quaternion = _dice_root.quaternion
	var mid_a: Quaternion = Quaternion.from_euler(Vector3(
		randf_range(-2.6, 2.6),
		randf_range(-2.6, 2.6),
		randf_range(-2.6, 2.6)
	))
	var mid_b: Quaternion = Quaternion.from_euler(Vector3(
		randf_range(-3.2, 3.2),
		randf_range(-3.2, 3.2),
		randf_range(-3.2, 3.2)
	))
	var end_q: Quaternion = _basis_for_value(target_value).get_rotation_quaternion()

	_roll_tween = create_tween()
	_roll_tween.set_parallel(false)
	_roll_tween.tween_method(_set_dice_quaternion, start_q, mid_a, roll_duration * 0.35)\
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_roll_tween.tween_method(_set_dice_quaternion, mid_a, mid_b, roll_duration * 0.35)\
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_roll_tween.tween_method(_set_dice_quaternion, mid_b, end_q, settle_duration)\
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	_roll_tween.tween_callback(_on_roll_finished)


func enable_debug_inspect() -> void:
	is_rolling_flag = false
	_debug_mode = true
	if _roll_tween and _roll_tween.is_valid():
		_roll_tween.kill()
	_apply_face_basis(target_value)
	_update_materials_for_value(target_value)
	_refresh_projection()


func disable_debug_inspect() -> void:
	_debug_mode = false


func handle_debug_input(event: InputEvent) -> bool:
	if not _debug_mode:
		return false
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		var local: Vector2 = to_local(event.global_position)
		var half: float = float(dice_size) * 0.5
		if Rect2(Vector2(-half, -half), Vector2(half * 2.0, half * 2.0)).has_point(local):
			set_value((target_value % 6) + 1)
			return true
	return false


func _on_roll_finished() -> void:
	is_rolling_flag = false
	_apply_face_basis(target_value)
	_update_materials_for_value(target_value)
	if _viewport:
		_viewport.render_target_update_mode = SubViewport.UPDATE_ONCE
	_refresh_projection()
	dice_stopped.emit(target_value)
	settled.emit()


func _set_dice_quaternion(q: Variant) -> void:
	if _dice_root == null:
		return
	var quat: Quaternion = q as Quaternion
	_dice_root.quaternion = quat.normalized()
	_refresh_projection()


func _refresh_projection() -> void:
	if _viewport == null:
		return
	_viewport.render_target_update_mode = SubViewport.UPDATE_ONCE


func _build_projection_chain() -> void:
	_sprite = get_node_or_null("Sprite") as Sprite2D
	if _sprite == null:
		_sprite = Sprite2D.new()
		_sprite.name = "Sprite"
		add_child(_sprite)
	_sprite.centered = true
	_sprite.scale = Vector2.ONE * (float(dice_size) / float(viewport_size))

	_viewport = SubViewport.new()
	_viewport.name = "DiceViewport"
	_viewport.size = Vector2i(viewport_size, viewport_size)
	_viewport.transparent_bg = true
	_viewport.render_target_update_mode = SubViewport.UPDATE_ONCE
	_viewport.own_world_3d = true
	add_child(_viewport)

	_world_root = Node3D.new()
	_world_root.name = "World3D"
	_viewport.add_child(_world_root)

	_camera = Camera3D.new()
	_camera.name = "Camera3D"
	_camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	_camera.size = 2.35
	_camera.near = 0.05
	_camera.far = 20.0
	_camera.position = Vector3(1.75, 1.75, 1.75)
	_world_root.add_child(_camera)
	_camera.look_at(Vector3.ZERO, Vector3.UP)
	_camera.current = true

	_light = DirectionalLight3D.new()
	_light.name = "KeyLight"
	_light.light_energy = 1.2
	_light.shadow_enabled = false
	_light.rotation_degrees = Vector3(-45.0, 35.0, 0.0)
	_world_root.add_child(_light)

	var fill := DirectionalLight3D.new()
	fill.name = "FillLight"
	fill.light_energy = 0.45
	fill.rotation_degrees = Vector3(-20.0, -120.0, 0.0)
	_world_root.add_child(fill)

	_dice_root = Node3D.new()
	_dice_root.name = "DiceRoot"
	_world_root.add_child(_dice_root)

	_sprite.texture = _viewport.get_texture()


func _build_dice_mesh() -> void:
	# 先做黑色外轮廓立方体，再叠六个略小的彩色面，模拟圆角像素骰子体块
	var body := MeshInstance3D.new()
	body.name = "Body"
	var box := BoxMesh.new()
	box.size = Vector3(1.16, 1.16, 1.16)
	body.mesh = box
	body.material_override = _make_material(outline_color, false)
	_dice_root.add_child(body)

	var soft := MeshInstance3D.new()
	soft.name = "SoftCore"
	var soft_box := BoxMesh.new()
	soft_box.size = Vector3(1.05, 1.05, 1.05)
	soft.mesh = soft_box
	soft.material_override = _make_material(base_color, true)
	_dice_root.add_child(soft)

	_face_meshes.clear()
	_face_meshes[1] = _make_face_plane(Vector3(0, 1, 0), Vector3(-90, 0, 0), top_color, 1)
	_face_meshes[6] = _make_face_plane(Vector3(0, -1, 0), Vector3(90, 0, 0), side_color, 6)
	_face_meshes[2] = _make_face_plane(Vector3(0, 0, 1), Vector3(0, 0, 0), base_color, 2)
	_face_meshes[5] = _make_face_plane(Vector3(0, 0, -1), Vector3(0, 180, 0), side_color, 5)
	_face_meshes[3] = _make_face_plane(Vector3(1, 0, 0), Vector3(0, -90, 0), base_color, 3)
	_face_meshes[4] = _make_face_plane(Vector3(-1, 0, 0), Vector3(0, 90, 0), side_color, 4)


func _make_face_plane(local_pos: Vector3, euler_deg: Vector3, color: Color, face_value: int) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.name = "Face%d" % face_value
	var plane := PlaneMesh.new()
	plane.size = Vector2(0.96, 0.96)
	mi.mesh = plane
	mi.position = local_pos * 0.54
	mi.rotation_degrees = euler_deg
	mi.material_override = _make_face_material(color, face_value)
	_dice_root.add_child(mi)
	return mi


func _make_material(color: Color, rough: bool) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.82 if rough else 0.55
	mat.metallic = 0.0
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	return mat


func _make_face_material(color: Color, face_value: int) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color.WHITE
	mat.roughness = 0.78
	mat.metallic = 0.0
	mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
	mat.albedo_texture = _make_face_texture(color, face_value)
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	return mat


func _make_face_texture(color: Color, face_value: int) -> ImageTexture:
	var size: int = 64
	var img := Image.create(size, size, false, Image.FORMAT_RGBA8)
	img.fill(Color.TRANSPARENT)

	# 圆角面底色
	var pad: int = 4
	var radius: int = 12
	for y in range(size):
		for x in range(size):
			if _in_rounded_rect(x, y, pad, pad, size - pad - 1, size - pad - 1, radius):
				img.set_pixel(x, y, color)

	# 白边
	for y in range(size):
		for x in range(size):
			var inside_inner := _in_rounded_rect(x, y, pad + 3, pad + 3, size - pad - 4, size - pad - 4, radius - 3)
			var inside_outer := _in_rounded_rect(x, y, pad, pad, size - pad - 1, size - pad - 1, radius)
			if inside_outer and not inside_inner:
				img.set_pixel(x, y, edge_color)

	# 点数
	for n: Vector2 in get_dots_positions(face_value):
		var cx: float = 32.0 + n.x * 16.0
		var cy: float = 32.0 + n.y * 16.0
		_draw_dot(img, cx, cy, 5)

	return ImageTexture.create_from_image(img)


func _in_rounded_rect(x: int, y: int, x0: int, y0: int, x1: int, y1: int, r: int) -> bool:
	if x < x0 or x > x1 or y < y0 or y > y1:
		return false
	if x < x0 + r and y < y0 + r:
		var dx0: int = x - (x0 + r)
		var dy0: int = y - (y0 + r)
		return dx0 * dx0 + dy0 * dy0 <= r * r
	if x > x1 - r and y < y0 + r:
		var dx1: int = x - (x1 - r)
		var dy1: int = y - (y0 + r)
		return dx1 * dx1 + dy1 * dy1 <= r * r
	if x < x0 + r and y > y1 - r:
		var dx2: int = x - (x0 + r)
		var dy2: int = y - (y1 - r)
		return dx2 * dx2 + dy2 * dy2 <= r * r
	if x > x1 - r and y > y1 - r:
		var dx3: int = x - (x1 - r)
		var dy3: int = y - (y1 - r)
		return dx3 * dx3 + dy3 * dy3 <= r * r
	return true


func _draw_dot(img: Image, cx: float, cy: float, r: int) -> void:
	for y in range(int(cy) - r, int(cy) + r + 1):
		for x in range(int(cx) - r, int(cx) + r + 1):
			var dx: float = float(x) + 0.5 - cx
			var dy: float = float(y) + 0.5 - cy
			if dx * dx + dy * dy <= float(r * r):
				if x >= 0 and y >= 0 and x < img.get_width() and y < img.get_height():
					img.set_pixel(x, y, dot_color)


func _update_materials_for_value(value: int) -> void:
	var face_values: Array[int] = [1, 2, 3, 4, 5, 6]
	for face_value: int in face_values:
		var mi: MeshInstance3D = _face_meshes.get(face_value) as MeshInstance3D
		if mi == null:
			continue
		var color: Color = base_color
		if face_value == value:
			color = top_color
		elif face_value == 7 - value:
			color = side_color.darkened(0.08)
		elif face_value == 4 or face_value == 5 or face_value == 6:
			color = side_color
		mi.material_override = _make_face_material(color, face_value)


func _basis_for_value(value: int) -> Basis:
	# 面布局：1=+Y, 6=-Y, 2=+Z, 5=-Z, 3=+X, 4=-X
	var eulers: Dictionary = {
		1: Vector3(0.0, 0.0, 0.0),
		2: Vector3(-PI * 0.5, 0.0, 0.0),
		3: Vector3(0.0, 0.0, -PI * 0.5),
		4: Vector3(0.0, 0.0, PI * 0.5),
		5: Vector3(PI * 0.5, 0.0, 0.0),
		6: Vector3(PI, 0.0, 0.0),
	}
	var e: Vector3 = eulers.get(value, Vector3.ZERO)
	var basis := Basis.from_euler(e)
	# 固定偏航，露出左右两个侧面
	return basis.rotated(Vector3.UP, deg_to_rad(35.0)).rotated(Vector3.RIGHT, deg_to_rad(-18.0))


func _apply_face_basis(value: int) -> void:
	if _dice_root == null:
		return
	_dice_root.basis = _basis_for_value(value)


func get_dots_positions(value: int) -> Array[Vector2]:
	match value:
		1:
			return [Vector2(0, 0)]
		2:
			return [Vector2(-0.55, -0.55), Vector2(0.55, 0.55)]
		3:
			return [Vector2(-0.55, -0.55), Vector2(0, 0), Vector2(0.55, 0.55)]
		4:
			return [Vector2(-0.55, -0.55), Vector2(0.55, -0.55), Vector2(-0.55, 0.55), Vector2(0.55, 0.55)]
		5:
			return [Vector2(-0.55, -0.55), Vector2(0.55, -0.55), Vector2(0, 0), Vector2(-0.55, 0.55), Vector2(0.55, 0.55)]
		6:
			return [Vector2(-0.55, -0.55), Vector2(0.55, -0.55), Vector2(-0.55, 0), Vector2(0.55, 0), Vector2(-0.55, 0.55), Vector2(0.55, 0.55)]
	return []
