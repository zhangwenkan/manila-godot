extends SubViewportContainer
class_name DiceStage3D

signal dice_settled(index: int, value: int)
signal all_settled(values: Array)

const TRAY_SCRIPT = preload("res://dice3d/dice_tray_3d.gd")

@export var pixels_per_unit: float = 108.0

var _viewport: SubViewport
var _world: Node3D
var _camera: Camera3D
var _tray
var _walls: Array[StaticBody3D] = []
var _dice: Array[Dice3D] = []
var _settled_count: int = 0
var _rolling: bool = false


func _ready() -> void:
	stretch = true
	stretch_shrink = 2
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_build_stage()
	resized.connect(_sync_layout)
	_sync_layout()


func _physics_process(_delta: float) -> void:
	if not _rolling:
		return
	# A late collision can wake an earlier die, so complete the whole group together.
	for die: Dice3D in _dice:
		if not die.has_settled():
			return
	for die: Dice3D in _dice:
		die._finish_roll()


func get_dice_count() -> int:
	return _dice.size()


func set_value(index: int, value: int) -> void:
	if index < 0 or index >= _dice.size() or _rolling:
		return
	_dice[index].set_value(value)


func get_value(index: int) -> int:
	if index < 0 or index >= _dice.size():
		return 1
	return _dice[index].get_value()


func get_values() -> Array:
	var values: Array = []
	for die: Dice3D in _dice:
		values.append(die.get_value())
	return values


func throw_all() -> void:
	if _rolling:
		return
	_rolling = true
	_settled_count = 0
	for die: Dice3D in _dice:
		var travel := _tray_point() - die.global_position
		travel.y = 0.0
		var lift := randf_range(4.0, 5.5)
		# Aim the ballistic arc inside the rim, leaving room for the first bounce.
		var flight_time := lift * 2.0 / 9.8
		var horizontal := (travel / (flight_time + 0.35)).limit_length(5.5)
		var spin := Vector3(randf_range(-1.0, 1.0), randf_range(-1.0, 1.0), randf_range(-1.0, 1.0)).normalized()
		die.roll(horizontal + Vector3.UP * lift, spin * randf_range(0.9, 1.6))


func enable_debug_inspect() -> void:
	if _rolling:
		return
	for die: Dice3D in _dice:
		die.enable_debug_inspect()


func handle_debug_input(event: InputEvent) -> bool:
	if _rolling:
		return false
	var local_event: InputEventMouseButton
	if event is InputEventMouseButton:
		local_event = event.duplicate() as InputEventMouseButton
	elif event is InputEventScreenTouch:
		local_event = InputEventMouseButton.new()
		local_event.position = event.position
		local_event.button_index = MOUSE_BUTTON_LEFT
		local_event.pressed = event.pressed
	else:
		return false
	local_event.position = get_global_transform_with_canvas().affine_inverse() * local_event.position
	local_event.position *= Vector2(_viewport.size) / size
	var candidates := _dice.duplicate()
	candidates.sort_custom(func(a: Dice3D, b: Dice3D): return _camera.global_position.distance_squared_to(a.global_position) < _camera.global_position.distance_squared_to(b.global_position))
	for die: Dice3D in candidates:
		if die.handle_debug_input(local_event, _die_screen_rect(die)):
			return true
	return false


func _die_screen_rect(die: Dice3D) -> Rect2:
	var center := _camera.unproject_position(die.global_position)
	var bounds := Rect2(center, Vector2.ZERO)
	for x in [-1.0, 1.0]:
		for y in [-1.0, 1.0]:
			for z in [-1.0, 1.0]:
				var corner := die.global_transform * (Vector3(x, y, z) * die.mesh_size * 0.5)
				bounds = bounds.expand(_camera.unproject_position(corner))
	return bounds.grow(2.0)


func _tray_point() -> Vector3:
	var available: Vector2 = _tray.radii - Vector2.ONE * 0.9
	var angle := randf() * TAU
	var radius := sqrt(randf()) * 0.78
	return Vector3(cos(angle) * available.x * radius, 0.0, sin(angle) * available.y * radius)


func _build_stage() -> void:
	_viewport = SubViewport.new()
	_viewport.name = "Viewport"
	_viewport.size = Vector2i(size / float(stretch_shrink))
	_viewport.transparent_bg = true
	_viewport.handle_input_locally = false
	_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	_viewport.own_world_3d = true
	_viewport.physics_object_picking = false
	add_child(_viewport)
	_world = Node3D.new()
	_world.name = "World"
	_viewport.add_child(_world)

	_camera = Camera3D.new()
	_camera.name = "Camera"
	_camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	_camera.near = 0.05
	_camera.far = 100.0
	_camera.position = Vector3(0.0, 20.0, 34.64)
	_world.add_child(_camera)
	_camera.look_at(Vector3.ZERO, Vector3.UP)
	_camera.current = true

	var key := DirectionalLight3D.new()
	key.name = "KeyLight"
	key.light_energy = 1.35
	key.shadow_enabled = true
	key.directional_shadow_max_distance = 80.0
	key.rotation_degrees = Vector3(-48.0, 32.0, 0.0)
	_world.add_child(key)
	var env := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.0, 0.0, 0.0, 0.0)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color.WHITE
	environment.ambient_light_energy = 0.5
	env.environment = environment
	_world.add_child(env)

	_tray = TRAY_SCRIPT.new()
	_tray.name = "NauticalDiceTray"
	_world.add_child(_tray)
	for wall_name in ["WallLeft", "WallRight", "WallBack", "WallFront"]:
		_walls.append(_add_static_box(wall_name))

	for i in range(3):
		var die := Dice3D.new()
		die.name = "Dice%d" % i
		die.position = Vector3((i - 1) * 1.55, die.mesh_size * 0.5, 0.0)
		die.settle_with_group = true
		_world.add_child(die)
		die.settled.connect(_on_one_settled.bind(i))
		_dice.append(die)


func _sync_layout() -> void:
	if _camera == null or size.x <= 0.0 or size.y <= 0.0:
		return
	_camera.size = maxf(size.y / maxf(pixels_per_unit, 1.0), 6.8 * size.y / size.x)
	var width := _camera.size * size.x / size.y
	var height := _camera.size
	var target := _camera.basis.y * (height * 0.16)
	_camera.position = _camera.basis.z * 40.0 + target
	_tray.configure(Vector2(minf(width * 0.38, 6.4), height * 0.29))
	for i in _walls.size():
		var horizontal := i < 2
		var direction := -1.0 if i % 2 == 0 else 1.0
		var axis := _camera.basis.x if horizontal else _camera.basis.y
		var extent := width if horizontal else height
		_walls[i].basis = _camera.basis
		_walls[i].position = target + axis * direction * (extent * 0.5 - 0.12)
		var wall_size := Vector3(0.2, height + 4.0, 80.0) if horizontal else Vector3(width + 4.0, 0.2, 80.0)
		(_walls[i].get_node("Collision").shape as BoxShape3D).size = wall_size


func _add_static_box(node_name: String) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.name = node_name
	var collision := CollisionShape3D.new()
	collision.name = "Collision"
	collision.shape = BoxShape3D.new()
	body.add_child(collision)
	_world.add_child(body)
	return body


func _on_one_settled(index: int) -> void:
	if not _rolling or index < 0 or index >= _dice.size():
		return
	dice_settled.emit(index, _dice[index].get_value())
	_settled_count += 1
	if _settled_count >= _dice.size():
		_rolling = false
		all_settled.emit(get_values())
