extends SceneTree
## Run with a real renderer (not --headless):
## godot --path . --script res://tools/ocean_visual_check.gd -- --record

const OUTPUT := "res://.godot/ocean_visual_check"
const OCEAN = preload("res://scene/pixel_ocean.tscn")
const BACKGROUND = preload("res://scene/image/scene.png")

var _failures: Array[String] = []


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	if DisplayServer.get_name() == "headless":
		push_error("Ocean visual checks require a real renderer.")
		quit(1)
		return
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT))
	var viewport := SubViewport.new()
	viewport.size = Vector2i(6144, 1152)
	viewport.disable_3d = true
	viewport.transparent_bg = true
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	var backdrop := Sprite2D.new()
	backdrop.texture = BACKGROUND
	backdrop.centered = false
	viewport.add_child(backdrop)
	var ocean = OCEAN.instantiate()
	ocean.animation_enabled = false
	viewport.add_child(ocean)
	_check(ocean.mouse_filter == Control.MOUSE_FILTER_IGNORE, "Water intercepts game input")
	ocean.hide()
	var original := await _capture(viewport, "original.png")
	ocean.show()
	ocean.seek(0.0)
	var first := await _capture(viewport, "procedural_0.png")
	ocean.seek(2.5)
	var second := await _capture(viewport, "procedural_2_5.png")
	var layout := (load("res://scene/image/ocean_layout.png") as Texture2D).get_image()
	var changed_land := 0
	var changed_water := 0
	var animated_water := 0
	for y in range(0, 1152, 5):
		for x in range(0, 6144, 5):
			var before := original.get_pixel(x, y)
			var after := first.get_pixel(x, y)
			if layout.get_pixel(x, y).r < 0.1:
				if before != after:
					changed_land += 1
			else:
				if before != after:
					changed_water += 1
				if after != second.get_pixel(x, y):
					animated_water += 1
	_check(changed_land == 0, "Water changed %d land samples" % changed_land)
	_check(changed_water > 10000, "Procedural water is missing or transparent")
	_check(animated_water > 500, "Water did not animate")
	print("OCEAN_PIXELS changed_land=%d changed_water=%d animated_water=%d" % [changed_land, changed_water, animated_water])
	var paused := await _capture(viewport, "")
	_check(paused.get_data() == second.get_data(), "Disabled animation still changes the water")

	# Panning must reveal another part of the same ocean, never move its pattern.
	viewport.size = Vector2i(2048, 1152)
	viewport.canvas_transform = Transform2D(0.0, Vector2(-2048.0, 0.0))
	var panned := await _capture(viewport, "panned.png")
	_check(panned.get_data() == second.get_region(Rect2i(2048, 0, 2048, 1152)).get_data(), "Pattern swims when the camera pans")
	viewport.size = Vector2i(6144, 1152)
	viewport.canvas_transform = Transform2D.IDENTITY

	# The water also renders on its own, with no source image or coastline map.
	backdrop.hide()
	ocean.material.set_shader_parameter("use_layout", false)
	var independent := await _capture(viewport, "water_only.png")
	_check(independent.get_pixel(800, 960).a > 0.99, "Water requires the background image")
	ocean.material.set_shader_parameter("use_layout", true)
	backdrop.show()

	if "--record" in OS.get_cmdline_user_args():
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT.path_join("frames")))
		for frame in range(48):
			ocean.seek(float(frame) / 8.0)
			var rendered := await _capture(viewport, "")
			var preview := Image.create(2048, 864, false, Image.FORMAT_RGBA8)
			preview.blit_rect(rendered, Rect2i(0, 720, 2048, 432), Vector2i.ZERO)
			preview.blit_rect(rendered, Rect2i(4096, 720, 2048, 432), Vector2i(0, 432))
			preview.save_png(OUTPUT.path_join("frames/%03d.png" % frame))
	viewport.queue_free()
	await process_frame

	# Load the actual game as well, to exercise the intended scene and boat layers.
	root.content_scale_size = Vector2i(2048, 1152)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	var game = load("res://scene/scene_bg.tscn").instantiate()
	root.add_child(game)
	var game_ocean = game.get_node("PixelOcean")
	_check(game_ocean.z_index < game.get_node("BoatTop").z_index, "Water covers the boats")
	game_ocean.animation_enabled = false
	game_ocean.seek(2.5)
	await process_frame
	await RenderingServer.frame_post_draw
	var game_image := root.get_texture().get_image()
	_check(not game_image.is_empty(), "Game failed to render")
	game_image.save_png(OUTPUT.path_join("game.png"))
	game.queue_free()
	await process_frame
	print("OCEAN_VISUAL_CHECK failures=%d output=%s" % [_failures.size(), ProjectSettings.globalize_path(OUTPUT)])
	quit(0 if _failures.is_empty() else 1)


func _capture(viewport: SubViewport, filename: String) -> Image:
	await process_frame
	await RenderingServer.frame_post_draw
	var rendered := viewport.get_texture().get_image()
	_check(not rendered.is_empty(), "Empty ocean render")
	if not filename.is_empty():
		_check(rendered.save_png(OUTPUT.path_join(filename)) == OK, "Could not save " + filename)
	return rendered


func _check(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)
		push_error(message)
