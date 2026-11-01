extends SubViewportContainer

const BOARD = preload("res://demo/harbor_pixel/market_board_3d.gd")
const GOODS = ["nutmeg", "silk", "ginseng", "jade"]
const VALUES = [0, 5, 10, 20, 30]

var _viewport: SubViewport
var _camera: Camera3D
var board: Node3D
var markers: Dictionary = {}
var prices: Dictionary = {}
var _corners: Array[Vector3] = []


func _ready() -> void:
	stretch = true
	# Fine pixel art at native viewport resolution, not enlarged 2x blocks.
	stretch_shrink = 1
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_viewport = SubViewport.new()
	_viewport.transparent_bg = true
	_viewport.own_world_3d = true
	_viewport.handle_input_locally = false
	_viewport.physics_object_picking = false
	_viewport.msaa_3d = Viewport.MSAA_4X
	_viewport.render_target_update_mode = SubViewport.UPDATE_DISABLED
	add_child(_viewport)
	var world = Node3D.new()
	_viewport.add_child(world)
	board = BOARD.new()
	world.add_child(board)
	for id in GOODS:
		markers[id] = board.find_child("Marker_" + id, true, false)
		assert(markers[id] is Node3D, "Missing procedural price marker: " + id)
	_refresh_bounds()
	var environment = WorldEnvironment.new()
	environment.environment = Environment.new()
	environment.environment.background_mode = Environment.BG_CLEAR_COLOR
	environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.environment.ambient_light_color = Color.WHITE
	environment.environment.ambient_light_energy = 0.5
	environment.environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	world.add_child(environment)
	var light = DirectionalLight3D.new()
	light.name = "MarketKeyLight"
	light.rotation_degrees = Vector3(-52, -32, 0)
	light.light_color = Color.WHITE
	light.light_energy = 1.35
	light.shadow_enabled = true
	light.directional_shadow_max_distance = 40.0
	world.add_child(light)
	_camera = Camera3D.new()
	_camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	_camera.keep_aspect = Camera3D.KEEP_HEIGHT
	_camera.near = 0.05
	_camera.far = 100.0
	world.add_child(_camera)
	_camera.current = true
	resized.connect(_fit_camera)
	_fit_camera()


func _refresh_bounds() -> void:
	_corners.clear()
	_collect_corners(board)
	# Include both ends of every moving sculpted piece, not only its initial pose.
	for column in GOODS.size():
		var marker: Node3D = markers[GOODS[column]]
		var saved := marker.position
		for price_index in [0, VALUES.size() - 1]:
			marker.position = BOARD.marker_position(column, price_index)
			_collect_corners(marker)
		marker.position = saved


func _collect_corners(node: Node) -> void:
	if node is MeshInstance3D:
		var bounds: AABB = node.get_aabb()
		for i in 8:
			_corners.append(node.global_transform * bounds.get_endpoint(i))
	for child in node.get_children():
		_collect_corners(child)


func _fit_camera() -> void:
	if not is_instance_valid(_camera) or size.x <= 0 or size.y <= 0:
		return
	# Match the dice tray's low tabletop view; the sidewalls must stay visible.
	_camera.position = Vector3(0, 20, 34.64)
	_camera.look_at(Vector3.ZERO)
	var projected := Rect2()
	var first := true
	for corner in _corners:
		var local := _camera.to_local(corner)
		var point := Vector2(local.x, local.y)
		if first:
			projected = Rect2(point, Vector2.ZERO)
			first = false
		else:
			projected = projected.expand(point)
	var center := projected.get_center()
	_camera.position += _camera.basis.x * center.x + _camera.basis.y * center.y
	_camera.size = maxf(projected.size.y, projected.size.x / (size.x / size.y)) * 1.12


static func marker_info(cargo_id: String, values: Dictionary) -> Dictionary:
	var column: int = GOODS.find(cargo_id)
	if column < 0:
		return {}
	var price: int = int(values.get(cargo_id, 0))
	var row: int = VALUES.find(price)
	if row < 0:
		return {}
	return {"price": price, "row": row, "column": column,
		"position": BOARD.marker_position(column, row)}


func marker_state(cargo_id: String) -> Dictionary:
	return marker_info(cargo_id, prices)


func sync_prices(values: Dictionary) -> void:
	prices = values.duplicate()
	for id in GOODS:
		var info := marker_state(id)
		if not info.is_empty():
			markers[id].position = info.position


func set_active(active: bool) -> void:
	_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS if active else SubViewport.UPDATE_DISABLED
	process_mode = Node.PROCESS_MODE_INHERIT if active else Node.PROCESS_MODE_DISABLED
	visible = active
