extends SceneTree

const OUTPUT := "res://.godot/dialog_skin_check"
const DialogSkin := preload("res://ui/harbor_dialog_skin.gd")
var failures: Array[String] = []
var shots := 0
var started := 0


func _initialize() -> void:
	started = Time.get_ticks_msec()
	_run.call_deferred()


func _process(_delta: float) -> bool:
	if Time.get_ticks_msec() - started > 85000:
		push_error("DIALOG_SKIN_CHECK timed out")
		quit(124)
	return false


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT))
	_check(DialogSkin.FRAME.get_width() > 0 and DialogSkin.SCROLL.get_width() > 0 and DialogSkin.CLOSE.get_width() > 0, "dialog skin textures load")
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.size = Vector2i(1200, 900)
	root.content_scale_size = Vector2i.ZERO
	var pixel = load("res://demo/harbor_pixel/harbor_demo.tscn").instantiate()
	root.add_child(pixel)
	pixel.auto_ai = false
	await _frames(8)
	_check(pixel.game.phase == "auction", "pixel auction opens automatically")
	await _capture("01_auction")
	await _pixel_click(pixel, "bid")
	_check(pixel.game.pass_bid(1) and pixel.game.pass_bid(2), "competitors concede")
	await _capture("02_stocks")
	await _pixel_click(pixel, "stock_skip")
	_check(pixel.game.phase == "setup" and pixel.modal.is_empty(), "stock skip enters scene loading")
	await _pixel_click(pixel, "help")
	await _capture("03_help")
	await _pixel_click(pixel, "close")
	_check(pixel.modal.is_empty() and pixel.game.phase == "setup", "red close restores preparation")
	await _pixel_click(pixel, "ledger")
	await _capture("04_ledger")
	await _pixel_click(pixel, "close")
	await _pixel_click(pixel, "to_starts")
	await _pixel_click(pixel, "begin")
	await _pixel_click(pixel, "slot:ship_0_0")
	await _capture("08_pixel_dispatch")
	pixel.queue_free()
	await _frames(4)
	print("DIALOG_SKIN_CHECK failures=%d screenshots=%d output=%s" % [failures.size(), shots, ProjectSettings.globalize_path(OUTPUT)])
	quit(0 if failures.is_empty() else 1)


func _check(value: bool, message: String) -> void:
	if not value:
		failures.append(message)
		push_error(message)


func _frames(count := 3) -> void:
	for i in count:
		await process_frame


func _point(point: Vector2) -> void:
	var motion := InputEventMouseMotion.new()
	motion.position = point
	root.push_input(motion, true)
	for down in [true, false]:
		var event := InputEventMouseButton.new()
		event.position = point
		event.button_index = MOUSE_BUTTON_LEFT
		event.pressed = down
		root.push_input(event, true)
		await process_frame
	await _frames()


func _pixel_click(demo: Control, id: String) -> void:
	await _frames()
	for hit in demo._hits:
		if hit.id == id:
			await _point(demo.position + demo._origin + hit.rect.get_center() * demo._zoom)
			return
	_check(false, "pixel target missing: " + id)


func _capture(filename: String) -> void:
	if DisplayServer.get_name() == "headless":
		return
	await _frames(3)
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	_check(not image.is_empty(), "render is not empty: " + filename)
	_check(image.save_png(OUTPUT.path_join(filename + ".png")) == OK, "save screenshot: " + filename)
	shots += 1
