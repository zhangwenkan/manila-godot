extends Control
## Independent comparison only; neither the selection scene nor its models are modified.

const FACTORY = preload("res://character_preview/pawn_factory.gd")
const IMPORTED: PackedScene = preload("res://character_preview/comparison/pirate_doll.glb")
const MODEL_HEIGHT := 3.0
const DEFAULT_PITCH := 0.6435011088

var views: Array[SubViewport] = []
var cameras: Array[Camera3D] = []
var figures: Array[Node3D] = []
var original_bounds: Array[AABB] = []
var cards: Array[PanelContainer] = []
var comparison_grid: GridContainer
var status: Label
var yaw := 0.0
var pitch := DEFAULT_PITCH
var zoom := 1.0
var imported_reversed := false
var _dragging := false
var _touch_index := -1
var _orbit_radius := 2.0


func _ready() -> void:
	get_window().title = "卡门模型对比 · 当前版本 / 导入 GLB"
	get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	get_window().content_scale_size = Vector2i.ZERO
	var background := ColorRect.new()
	background.color = Color("18181f")
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(background)
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 16)
	add_child(margin)
	var layout := VBoxContainer.new()
	layout.add_theme_constant_override("separation", 10)
	margin.add_child(layout)
	layout.add_child(_label("卡门 · 模型对比", 26, Color("f4e5cd")))
	var description := _label("当前版本完整保留 · 独立预览，不替换选角页或右侧棋子", 15, Color("bdb7b2"))
	description.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	layout.add_child(description)
	var toolbar := HFlowContainer.new()
	toolbar.add_theme_constant_override("h_separation", 8)
	layout.add_child(toolbar)
	_add_button(toolbar, "选角视角", func(): set_view(0.0, DEFAULT_PITCH))
	_add_button(toolbar, "平视", func(): set_view(0.0, 0.08))
	_add_button(toolbar, "侧面", func(): set_view(PI / 2.0, 0.18))
	_add_button(toolbar, "背面", func(): set_view(PI, 0.18))
	_add_button(toolbar, "GLB 转向 180°", func():
		imported_reversed = not imported_reversed
		figures[1].rotation.y = PI if imported_reversed else 0.0)
	_add_button(toolbar, "复位", reset_view)
	comparison_grid = GridContainer.new()
	comparison_grid.columns = 2
	comparison_grid.add_theme_constant_override("h_separation", 12)
	comparison_grid.add_theme_constant_override("v_separation", 12)
	comparison_grid.size_flags_vertical = Control.SIZE_EXPAND_FILL
	layout.add_child(comparison_grid)
	_add_model("A · 当前卡门", "程序化坐姿模型 / 保留现有材质", FACTORY.build(0, FACTORY.Presentation.CHOICE))
	_add_model("B · 导入 GLB", "pirate_doll.glb / 保留自带贴图与 PBR 材质", IMPORTED.instantiate())
	status = _label("", 14, Color("bdb7b2"))
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	layout.add_child(status)
	resized.connect(_layout)
	_layout()


func _label(text: String, font_size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	return label


func _add_button(parent: Control, text: String, action: Callable) -> void:
	var button := Button.new()
	button.text = text
	button.custom_minimum_size.y = 36
	button.pressed.connect(action)
	parent.add_child(button)


func _add_model(title: String, subtitle: String, source: Node3D) -> void:
	var card := PanelContainer.new()
	card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	card.size_flags_vertical = Control.SIZE_EXPAND_FILL
	var style := StyleBoxFlat.new()
	style.bg_color = Color("24242c")
	style.set_corner_radius_all(10)
	style.content_margin_left = 12
	style.content_margin_right = 12
	style.content_margin_top = 12
	style.content_margin_bottom = 8
	card.add_theme_stylebox_override("panel", style)
	comparison_grid.add_child(card)
	cards.append(card)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 5)
	card.add_child(column)
	column.add_child(_label(title, 21, Color("f4e5cd")))
	var caption := _label(subtitle, 13, Color("bdb7b2"))
	caption.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(caption)
	var container := SubViewportContainer.new()
	container.stretch = true
	container.size_flags_vertical = Control.SIZE_EXPAND_FILL
	container.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	container.custom_minimum_size = Vector2(32, 100)
	container.mouse_default_cursor_shape = Control.CURSOR_DRAG
	container.gui_input.connect(_view_input)
	column.add_child(container)
	var view := SubViewport.new()
	view.own_world_3d = true
	view.msaa_3d = Viewport.MSAA_4X
	view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	view.handle_input_locally = false
	container.add_child(view)
	views.append(view)
	var world := WorldEnvironment.new()
	world.environment = Environment.new()
	world.environment.background_mode = Environment.BG_COLOR
	world.environment.background_color = Color("24242c")
	world.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	world.environment.ambient_light_color = Color("fff3e2")
	world.environment.ambient_light_energy = 0.65
	world.environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	view.add_child(world)
	_add_light(view, Vector3(-38, -32, 0), Color("fff4e8"), 1.3)
	_add_light(view, Vector3(-20, 130, 0), Color("dce7ff"), 0.7)
	var normalized := Node3D.new()
	view.add_child(normalized)
	normalized.add_child(source)
	var bounds := _bounds(source, normalized)
	original_bounds.append(bounds)
	var scale_factor := MODEL_HEIGHT / maxf(bounds.size.y, 0.001)
	source.scale *= scale_factor
	source.position = (source.position - Vector3(bounds.get_center().x, bounds.position.y, bounds.get_center().z)) * scale_factor
	_orbit_radius = maxf(_orbit_radius, Vector2(bounds.size.x, bounds.size.z).length() * scale_factor * 0.5)
	figures.append(normalized)
	var camera := Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.current = true
	camera.near = 0.01
	camera.far = 100.0
	view.add_child(camera)
	cameras.append(camera)
	view.size_changed.connect(_update_cameras)


func _add_light(parent: Node, angles: Vector3, color: Color, energy: float) -> void:
	var light := DirectionalLight3D.new()
	light.rotation_degrees = angles
	light.light_color = color
	light.light_energy = energy
	parent.add_child(light)


func _bounds(node: Node3D, relative_to: Node3D) -> AABB:
	var found := false
	var result := AABB()
	var meshes: Array[Node] = node.find_children("*", "MeshInstance3D", true, false)
	if node is MeshInstance3D:
		meshes.push_front(node)
	for child in meshes:
		var mesh := child as MeshInstance3D
		if mesh.mesh == null:
			continue
		var transformed: AABB = (relative_to.global_transform.affine_inverse() * mesh.global_transform) * mesh.get_aabb()
		result = result.merge(transformed) if found else transformed
		found = true
	return result


func _layout() -> void:
	comparison_grid.columns = 1 if size.x < 760.0 else 2
	_update_cameras()


func set_view(new_yaw: float, new_pitch: float) -> void:
	yaw = new_yaw
	pitch = new_pitch
	_update_cameras()


func reset_view() -> void:
	zoom = 1.0
	imported_reversed = false
	figures[1].rotation.y = 0.0
	set_view(0.0, DEFAULT_PITCH)


func _update_cameras() -> void:
	var target := Vector3(0, MODEL_HEIGHT * 0.5, 0)
	var direction := Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch))
	var frame_height := maxf(MODEL_HEIGHT, MODEL_HEIGHT * cos(pitch) + 2.0 * _orbit_radius * absf(sin(pitch))) * 1.16
	var frame_width := 2.0 * _orbit_radius * 1.16
	var common_size := frame_height
	for view in views:
		var aspect := float(view.size.x) / maxf(view.size.y, 1)
		common_size = maxf(common_size, frame_width / maxf(aspect, 0.1))
	for camera in cameras:
		camera.position = target + direction * 12.0
		camera.look_at(target)
		camera.size = common_size / zoom
	if is_instance_valid(status):
		status.text = "拖动任一模型同步旋转 · 滚轮缩放 · 按整体高度对齐，材质各自保留 · 缩放 %d%%" % roundi(zoom * 100.0)


func _view_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			_dragging = event.pressed
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_UP:
			zoom = clampf(zoom * 1.1, 0.65, 2.5)
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			zoom = clampf(zoom / 1.1, 0.65, 2.5)
	elif event is InputEventMouseMotion and _dragging:
		if not event.button_mask & MOUSE_BUTTON_MASK_LEFT:
			_dragging = false
		else:
			yaw -= event.relative.x * 0.008
			pitch = clampf(pitch + event.relative.y * 0.006, -0.25, 1.15)
	elif event is InputEventScreenTouch:
		_touch_index = event.index if event.pressed else -1
	elif event is InputEventScreenDrag and event.index == _touch_index:
		yaw -= event.relative.x * 0.008
		pitch = clampf(pitch + event.relative.y * 0.006, -0.25, 1.15)
	_update_cameras()
