extends Node3D

const ASSET := preload("res://demo/harbor_hd2d/art/insurance_rebuild_r2/insurance_rebuild_r2_1.glb")

var camera: Camera3D
var display: SubViewportContainer
var viewport: SubViewport
var models: Array[Node3D] = []
var buttons: Dictionary = {}
var target := Vector3(0, 3.35, 1.05)
var yaw := 0.0
var pitch := 42.0
var zoom := 15.6
var dragging := false
var clay := false
var failures := 0


func _ready() -> void:
	get_window().content_scale_size = Vector2i(1200, 900)
	get_window().size = Vector2i(1200, 900)
	var canvas := Control.new()
	canvas.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	canvas.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(canvas)
	display = SubViewportContainer.new()
	display.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	display.stretch = true
	display.stretch_shrink = 2
	display.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	display.mouse_filter = Control.MOUSE_FILTER_IGNORE
	canvas.add_child(display)
	viewport = SubViewport.new()
	viewport.own_world_3d = true
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	viewport.msaa_3d = Viewport.MSAA_DISABLED
	display.add_child(viewport)
	var stage := Node3D.new()
	viewport.add_child(stage)
	var world_environment := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color.WHITE
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("d6d9df")
	environment.ambient_light_energy = 0.78
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	world_environment.environment = environment
	stage.add_child(world_environment)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55, -28, 0)
	sun.light_color = Color("fff0d6")
	sun.light_energy = 0.78
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 65.0
	sun.shadow_bias = 0.02
	stage.add_child(sun)
	for is_clay in [false, true]:
		var instance := ASSET.instantiate() as Node3D
		_adapt(instance, is_clay)
		stage.add_child(instance)
		instance.visible = not is_clay
		models.append(instance)
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.near = 0.1
	camera.far = 120.0
	stage.add_child(camera)
	camera.current = true
	_update_camera()
	var bar := HBoxContainer.new()
	bar.position = Vector2(12, 12)
	canvas.add_child(bar)
	for item in [["正面", 0.0], ["侧面", 65.0], ["背面", 180.0]]:
		var button := Button.new()
		button.text = item[0]
		button.pressed.connect(func():
			yaw = item[1]
			pitch = 42.0
			zoom = 15.6
			dragging = false
			_update_camera()
		)
		bar.add_child(button)
		buttons[item[0]] = button
	var material_button := Button.new()
	material_button.text = "灰模 / 像素材质"
	material_button.pressed.connect(func():
		clay = not clay
		models[0].visible = not clay
		models[1].visible = clay
	)
	bar.add_child(material_button)
	buttons["材质"] = material_button
	var pixel_button := Button.new()
	pixel_button.text = "1× / 2×"
	pixel_button.pressed.connect(func(): display.stretch_shrink = 3 - display.stretch_shrink)
	bar.add_child(pixel_button)
	buttons["倍率"] = pixel_button
	var label := Label.new()
	label.text = "完整重建 R2.1 · 滚轮缩放 / 右键旋转 · 独立原始构图，背面为补全设计"
	label.position = Vector2(14, 55)
	label.add_theme_color_override("font_color", Color("4b4445"))
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	canvas.add_child(label)
	if "--capture" in OS.get_cmdline_user_args():
		get_tree().create_timer(55.0).timeout.connect(func():
			push_error("R2_PREVIEW_TIMEOUT")
			get_tree().quit(1)
		)
		_capture.call_deferred()


func _adapt(node: Node, is_clay: bool) -> void:
	if node is MeshInstance3D:
		var mesh_node := node as MeshInstance3D
		for i in mesh_node.mesh.get_surface_count():
			var imported := mesh_node.mesh.surface_get_material(i) as StandardMaterial3D
			if imported == null:
				failures += 1
				continue
			var mat := imported.duplicate() as StandardMaterial3D
			mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
			mat.roughness = 1.0
			mat.metallic = 0.0
			mat.metallic_specular = 0.0
			if is_clay:
				mat.albedo_texture = null
				mat.albedo_color = Color("a5aaa8")
			mesh_node.set_surface_override_material(i, mat)
	for child in node.get_children():
		_adapt(child, is_clay)


func _update_camera() -> void:
	var y := deg_to_rad(yaw)
	var p := deg_to_rad(pitch)
	camera.position = target + Vector3(sin(y) * cos(p), sin(p), cos(y) * cos(p)) * 32.0
	camera.look_at(target)
	camera.size = zoom


func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_RIGHT and not event.pressed:
		dragging = false


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_RIGHT:
			dragging = event.pressed
		elif event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
			zoom = clampf(zoom * (0.85 if event.button_index == MOUSE_BUTTON_WHEEL_UP else 1.0 / 0.85), 5.0, 28.0)
			_update_camera()
	elif event is InputEventMouseMotion and dragging:
		if not event.button_mask & MOUSE_BUTTON_MASK_RIGHT:
			dragging = false
			return
		yaw -= event.relative.x * 0.25
		pitch = clampf(pitch + event.relative.y * 0.25, 10, 80)
		_update_camera()


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		dragging = false


func _capture() -> void:
	var out := "res://demo/harbor_hd2d/preview/insurance-r2/revised"
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--output="):
			out = argument.trim_prefix("--output=")
	if DirAccess.dir_exists_absolute(out) or DirAccess.make_dir_recursive_absolute(out) != OK:
		push_error("Refusing existing or invalid capture directory")
		get_tree().quit(1)
		return
	await get_tree().process_frame
	await _exercise_inputs()
	for item in [["正面", "01_front_2x", 0.0], ["侧面", "02_side_2x", 65.0], ["背面", "03_rear_2x", 180.0]]:
		await _click(buttons[item[0]])
		_check(is_equal_approx(yaw, item[2]), "view button " + item[0])
		await _save(out.path_join(item[1] + ".png"))
	await _click(buttons["材质"])
	_check(clay and models[1].visible and not models[0].visible, "clay model visible")
	await _save(out.path_join("04_rear_clay.png"))
	await _click(buttons["正面"])
	_check(is_zero_approx(yaw), "front clay view")
	await _save(out.path_join("05_front_clay.png"))
	await _click(buttons["材质"])
	await _click(buttons["倍率"])
	_check(not clay and models[0].visible and not models[1].visible, "pixel model visible")
	_check(display.stretch_shrink == 1, "native pixel size")
	await _save(out.path_join("06_front_1x.png"))
	print("R2_PREVIEW_DONE: 6 images; failures=%d; visual assessment separate" % failures)
	get_tree().quit(0 if failures == 0 else 1)


func _check(condition: bool, message: String) -> void:
	if not condition:
		failures += 1
		push_error("R2_PREVIEW_CHECK: " + message)


func _mouse_button(point: Vector2, button: MouseButton, pressed: bool) -> void:
	var event := InputEventMouseButton.new()
	event.position = point
	event.button_index = button
	event.pressed = pressed
	event.button_mask = MOUSE_BUTTON_MASK_RIGHT if button == MOUSE_BUTTON_RIGHT and pressed else 0
	get_viewport().push_input(event, true)


func _exercise_inputs() -> void:
	var point := Vector2(700, 650)
	_mouse_button(point, MOUSE_BUTTON_WHEEL_UP, true)
	_mouse_button(point, MOUSE_BUTTON_WHEEL_UP, false)
	await get_tree().process_frame
	_check(zoom < 15.6, "wheel zoom in")
	_mouse_button(point, MOUSE_BUTTON_WHEEL_DOWN, true)
	_mouse_button(point, MOUSE_BUTTON_WHEEL_DOWN, false)
	await get_tree().process_frame
	_check(is_equal_approx(zoom, 15.6), "wheel zoom out")
	_mouse_button(point, MOUSE_BUTTON_RIGHT, true)
	var motion := InputEventMouseMotion.new()
	motion.position = point + Vector2(80, 40)
	motion.relative = Vector2(80, 40)
	motion.button_mask = MOUSE_BUTTON_MASK_RIGHT
	get_viewport().push_input(motion, true)
	await get_tree().process_frame
	_check(not is_zero_approx(yaw) and not is_equal_approx(pitch, 42.0), "right drag orbit")
	_mouse_button(buttons["正面"].get_global_rect().get_center(), MOUSE_BUTTON_RIGHT, false)
	_check(not dragging, "release over toolbar")
	await _click(buttons["正面"])
	_check(is_zero_approx(yaw) and is_equal_approx(pitch, 42.0) and is_equal_approx(zoom, 15.6), "reset camera")
	_check(display.stretch_shrink == 2, "initial pixel size")


func _click(button: Button) -> void:
	var point := button.get_global_rect().get_center()
	for pressed in [true, false]:
		var event := InputEventMouseButton.new()
		event.position = point
		event.button_index = MOUSE_BUTTON_LEFT
		event.pressed = pressed
		get_viewport().push_input(event, true)
	await get_tree().process_frame


func _save(path: String) -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	if image == null or image.save_png(path) != OK:
		failures += 1
		push_error("Failed to save " + path)
