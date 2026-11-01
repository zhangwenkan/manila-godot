extends Node3D

const SAMPLE := preload("res://demo/harbor_hd2d/art/insurance_pixel/insurance_pixel_sample.glb")
const World := preload("res://demo/harbor_hd2d/harbor_world.gd")
const ORIGINAL := "C:/Users/51440/Downloads/harbor dock 3d model.glb"

var viewport: SubViewport
var display: SubViewportContainer
var stage: Node3D
var model: Node3D
var camera: Camera3D
var label: Label
var target := Vector3(0.55, 3.2, -0.55)
var yaw := 12.0
var pitch := 29.0
var zoom := 18.5
var dragging := false
var pixel_scale := 2
var version := 2
var failures := 0
var models: Dictionary = {}
var original_document: GLTFDocument
var original_state: GLTFState
var version_buttons: Dictionary = {}
var pixels_button: Button
var reset_button: Button


func _ready() -> void:
	var canvas := Control.new()
	canvas.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	canvas.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(canvas)
	display = SubViewportContainer.new()
	display.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	display.stretch = true
	display.stretch_shrink = pixel_scale
	display.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	display.mouse_filter = Control.MOUSE_FILTER_IGNORE
	canvas.add_child(display)
	viewport = SubViewport.new()
	viewport.own_world_3d = true
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	viewport.msaa_3d = Viewport.MSAA_DISABLED
	display.add_child(viewport)
	# Use only the existing lighting method, NOT the full harbor construction.
	stage = Node3D.new()
	viewport.add_child(stage)
	var lighting := World.new()
	lighting._lighting()
	for child in lighting.get_children():
		lighting.remove_child(child)
		stage.add_child(child)
	lighting.free()
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.near = 0.1
	camera.far = 180.0
	stage.add_child(camera)
	camera.current = true
	var bar := HBoxContainer.new()
	bar.position = Vector2(12, 12)
	canvas.add_child(bar)
	for item in [["原始 GLB",0],["灰模样板",1],["像素样板",2]]:
		var button := Button.new()
		button.text = item[0]
		button.pressed.connect(_show.bind(item[1]))
		bar.add_child(button)
		version_buttons[item[1]] = button
	pixels_button = Button.new()
	pixels_button.text = "像素倍率 1× / 2×"
	pixels_button.pressed.connect(func():
		pixel_scale = 3 - pixel_scale
		display.stretch_shrink = pixel_scale
		_status()
	)
	bar.add_child(pixels_button)
	reset_button = Button.new()
	reset_button.text = "复位视角"
	reset_button.pressed.connect(func():
		yaw = 12.0
		pitch = 29.0
		zoom = 18.5
		dragging = false
		_update_camera()
	)
	bar.add_child(reset_button)
	label = Label.new()
	label.position = Vector2(14, 57)
	label.add_theme_color_override("font_color", Color("eedeb8"))
	canvas.add_child(label)
	_show(2)
	_update_camera()
	if "--capture" in OS.get_cmdline_user_args():
		get_tree().create_timer(55.0).timeout.connect(func():
			push_error("INS7_SAMPLE_PREVIEW_TIMEOUT")
			get_tree().quit(1)
		)
		_capture.call_deferred()


func _show(which: int) -> void:
	if not models.has(which):
		var next: Node3D
		if which == 0:
			# Keep the imported resources and instances alive while comparing views.
			original_document = GLTFDocument.new()
			original_state = GLTFState.new()
			var error := original_document.append_from_file(ORIGINAL, original_state)
			if error != OK:
				push_error("Cannot load local reference GLB: %s" % error)
				failures += 1
				return
			next = original_document.generate_scene(original_state)
			if next == null:
				push_error("Cannot instantiate local reference GLB")
				failures += 1
				return
			next.scale = Vector3.ONE * 13.1
			next.position.x = 0.55
		else:
			next = SAMPLE.instantiate()
			_adapt(next, which == 1)
		stage.add_child(next)
		models[which] = next
	if model != null:
		model.hide()
	model = models[which]
	model.show()
	version = which
	_status()


func _adapt(node: Node, clay: bool) -> void:
	if node is MeshInstance3D:
		var mesh_node := node as MeshInstance3D
		for surface in mesh_node.mesh.get_surface_count():
			var imported := mesh_node.mesh.surface_get_material(surface) as StandardMaterial3D
			if imported == null:
				failures += 1
				continue
			var material := imported.duplicate() as StandardMaterial3D
			material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
			material.metallic = 0.0
			material.roughness = 1.0
			material.metallic_specular = 0.0
			if clay:
				material.albedo_texture = null
				material.albedo_color = Color("9b9b96")
			mesh_node.set_surface_override_material(surface, material)
	for child in node.get_children():
		_adapt(child, clay)


func _status() -> void:
	if label != null:
		label.text = "%s · %d×\n滚轮缩放 / 按住右键旋转 · 部分材质样板，非完整重建、未经美术验收" % [["外部输入（统一尺寸，方位尚未视觉校准）", "结构灰模", "像素材质样板"][version], pixel_scale]


func _update_camera() -> void:
	var y := deg_to_rad(yaw)
	var p := deg_to_rad(pitch)
	camera.position = target + Vector3(sin(y) * cos(p), sin(p), cos(y) * cos(p)) * 35.0
	camera.look_at(target)
	camera.size = zoom


func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_RIGHT and not event.pressed:
		dragging = false


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_RIGHT:
			dragging = event.pressed
		if event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
			zoom = clampf(zoom * (0.85 if event.button_index == MOUSE_BUTTON_WHEEL_UP else 1.0 / 0.85), 5, 38)
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
	var out := "res://demo/harbor_hd2d/preview/v7-insurance-pixel/sample"
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--output="):
			out = argument.trim_prefix("--output=")
	if DirAccess.dir_exists_absolute(out):
		push_error("Refusing to overwrite preview directory")
		get_tree().quit(1)
		return
	if DirAccess.make_dir_recursive_absolute(out) != OK:
		push_error("Cannot create preview directory")
		get_tree().quit(1)
		return
	await get_tree().process_frame
	_check(display.size.x > 640 and display.size.y > 400, "Preview fills the window")
	await _exercise_controls()
	for item in [[0, "01_original_front"], [1, "02_sample_clay"], [2, "03_sample_pixel_2x"]]:
		await _click(version_buttons[item[0]])
		_check(version == item[0], "Model button changes the visible version")
		for key in models:
			_check(models[key].visible == (key == version), "Only one model is visible")
		await _save(out.path_join(item[1] + ".png"))
	await _click(pixels_button)
	_check(pixel_scale == 1 and display.stretch_shrink == 1, "1x button updates the viewport")
	await _save(out.path_join("04_sample_pixel_1x.png"))
	yaw = 35.0
	pitch = 32.0
	_update_camera()
	await _click(pixels_button)
	_check(pixel_scale == 2 and display.stretch_shrink == 2, "2x button updates the viewport")
	await _save(out.path_join("05_sample_side_2x.png"))
	await _click(version_buttons[0])
	_check(version == 0, "Original model can be shown again")
	await _save(out.path_join("06_original_side.png"))
	print("INS7_SAMPLE_PREVIEW_DONE: 6 images; injected GUI controls checked; failures=%d; visual verification separate" % failures)
	get_tree().quit(0 if failures == 0 else 1)


func _exercise_controls() -> void:
	var point := get_viewport().get_visible_rect().size * 0.65
	_motion(point, Vector2.ZERO, 0)
	_mouse_button(MOUSE_BUTTON_WHEEL_UP, true, point)
	_mouse_button(MOUSE_BUTTON_WHEEL_UP, false, point)
	_check(zoom < 18.5 and is_equal_approx(camera.size, zoom), "Wheel zooms in")
	_mouse_button(MOUSE_BUTTON_WHEEL_DOWN, true, point)
	_mouse_button(MOUSE_BUTTON_WHEEL_DOWN, false, point)
	_check(is_equal_approx(zoom, 18.5), "Wheel zooms out")
	_mouse_button(MOUSE_BUTTON_RIGHT, true, point)
	_motion(point + Vector2(80, 40), Vector2(80, 40), MOUSE_BUTTON_MASK_RIGHT)
	_check(dragging and not is_equal_approx(yaw, 12.0) and not is_equal_approx(pitch, 29.0), "Right drag rotates the camera")
	_mouse_button(MOUSE_BUTTON_RIGHT, false, reset_button.get_global_rect().get_center())
	_check(not dragging, "Release over GUI stops dragging")
	await _click(reset_button)
	_check(is_equal_approx(yaw, 12.0) and is_equal_approx(pitch, 29.0) and is_equal_approx(zoom, 18.5), "Reset restores the review camera")


func _click(button: Button) -> void:
	var point := button.get_global_rect().get_center()
	_motion(point, Vector2.ZERO, 0)
	_mouse_button(MOUSE_BUTTON_LEFT, true, point)
	_mouse_button(MOUSE_BUTTON_LEFT, false, point)
	await get_tree().process_frame


func _mouse_button(index: MouseButton, pressed: bool, point: Vector2) -> void:
	var event := InputEventMouseButton.new()
	event.button_index = index
	event.pressed = pressed
	event.position = point
	get_viewport().push_input(event, true)


func _motion(point: Vector2, relative: Vector2, mask: int) -> void:
	var event := InputEventMouseMotion.new()
	event.position = point
	event.relative = relative
	event.button_mask = mask
	get_viewport().push_input(event, true)


func _check(condition: bool, message: String) -> void:
	if not condition:
		failures += 1
		push_error("INS7_SAMPLE_CONTROL_FAIL: " + message)


func _save(path: String) -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	if image == null or image.save_png(path) != OK:
		failures += 1
		push_error("Could not save " + path)
