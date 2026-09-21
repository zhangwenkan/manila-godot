extends SceneTree
## Check the actual scene: godot --path . --script res://tools/personal_bar_check.gd
## Append -- --preview (optionally --four-crew) to leave the Lakan sample open.

const OUTPUT := "res://.godot/personal_bar_check"
const Pixel := preload("res://card/pixel_card_theme.gd")
var _failures: Array[String] = []
var _game


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT))
	root.content_scale_size = Vector2i(2048, 1152)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.size = Vector2i(2048, 1152)
	_game = load("res://scene/scene_bg.tscn").instantiate()
	root.add_child(_game)
	await _frames(5)
	var bar = _game.personal_bar
	var roster = _game.character_overlay
	if "--preview" in OS.get_cmdline_user_args():
		if "--four-crew" in OS.get_cmdline_user_args():
			bar.set_resources(30, 4, 4)
		return

	_check(bar.character_id == "Lakan Bautista", "The game should start with the Lakan preview")
	_check(bar._portrait.resource_path == "res://card/image/lanka_avatar.png", "Dedicated Lakan avatar is missing")
	_check(bar.round_number == 1 and bar._coins_value.text == "30", "Opening round or cash is wrong")
	_check_play_ui()
	_check_layout()
	await _capture("lakan_desktop.png")
	await _capture("lakan_detail.png", true)

	_game.open_character_roster()
	await _frames(3)
	_check(not bar.visible, "Personal bar overlaps the character roster")
	await _click(roster.cards[0].get_global_rect().get_center())
	await _key(KEY_ESCAPE)
	_check(bar.visible and bar.character_id == "Lakan Bautista", "Cancelling changed the initial character")

	for index in roster.cards.size():
		await _choose(index)
		var card = roster.cards[index]
		var expected_portrait: Texture2D = card.avatar if card.avatar else card.portrait
		_check(bar.character_id == card.character_name_en, "Confirmed identity did not reach the HUD")
		_check(bar._display_name == card.character_name, "Identity tooltip lost the full name")
		_check(bar._portrait == expected_portrait, "Wrong portrait texture")
		_check(Rect2(Vector2.ZERO, expected_portrait.get_size()).encloses(bar._portrait_source), "Avatar crop falls outside its texture")
		_check(bar._coins_value.text == "30" and bar.remaining_crew == 3, "Choosing a character changed resources")
		_check_layout()
		await _capture("character_%d.png" % index, true)

	var committed_id: String = bar.character_id
	_game.open_character_roster()
	await _frames(3)
	await _click(roster.cards[0].get_global_rect().get_center())
	_check(bar.character_id == committed_id, "Browsing changed the committed identity")
	await _key(KEY_ESCAPE)
	_check(bar.character_id == committed_id and bar.visible, "Cancel did not preserve the committed character")
	await _choose(2)

	bar.set_resources(30, 4, 4)
	_check(bar.remaining_crew == 4 and bar.crew_capacity == 4, "Four-crew preview is not supported")
	await _capture("lakan_four_crew.png", true)
	bar.set_resources(27, 2, 4)
	bar.round_number = 3
	bar.set_stock_values({"silk": 10, "nutmeg": 5, "jade": 20, "ginseng": 15})
	_check(bar._coins_value.text == "27" and bar._round_label.text == "第 3 航程", "Resource updates did not reach the HUD")
	for i in 4:
		_check(bar._stock_labels[i].text == str([10, 5, 20, 15][i]), "Cargo values are missing or out of order")
	_check_layout()
	await _capture("lakan_partial_crew.png", true)
	bar.set_resources(0, 0, 3)
	await _capture("lakan_empty_crew.png", true)
	bar.set_resources(999999, 3, 3)
	bar.round_number = 120
	bar.set_stock_values({"silk": 120, "nutmeg": 100, "jade": 200, "ginseng": 60})
	_check_layout()
	await _capture("large_values.png", true)
	bar.set_resources(30, 3, 3)
	bar.round_number = 1
	bar.set_stock_values({"silk": 0, "nutmeg": 0, "jade": 0, "ginseng": 0})

	var before: Transform2D = bar.get_global_transform_with_canvas()
	var old_camera_x: float = _game.camera.position.x
	_game._pan_camera(800.0)
	await _frames(18)
	_check(_game.camera.position.x > old_camera_x, "Panning did not move the camera")
	_check(bar.get_global_transform_with_canvas().is_equal_approx(before), "HUD moves with the sea camera")
	await _capture("panned.png")
	_game._is_manual_camera = false
	_game.camera.position.x = _game.layout_view_size.x * 0.5

	_game.inspect_dice()
	_check(not bar.visible and _game.dice_overlay.visible, "Personal bar overlaps dice mode")
	await _key(KEY_ESCAPE)
	_check(bar.visible and not _game.dice_overlay.visible, "Personal bar did not return after dice mode")
	_check_play_ui()

	# Exercise the project's viewport stretch in a smaller desktop window.
	root.size = Vector2i(1280, 720)
	await _frames(8)
	_check_layout()
	await _capture("window_1280.png", false, root.size)

	# Also exercise native smaller viewports and the four-heart arc.
	for dimensions in [Vector2i(1280, 720), Vector2i(640, 480)]:
		root.content_scale_size = dimensions
		root.size = dimensions
		await _frames(5)
		bar.set_resources(30, 4, 4)
		_check_layout()
		await _capture("native_%d.png" % dimensions.x)

	print("PERSONAL_BAR_CHECK failures=%d output=%s" % [_failures.size(), ProjectSettings.globalize_path(OUTPUT)])
	_game.queue_free()
	await _frames(2)
	quit(0 if _failures.is_empty() else 1)


func _check_play_ui() -> void:
	for old_name in ["RollButton", "DebugDiceButton"]:
		_check(_game.get_node_or_null("CanvasLayer/" + old_name) == null, "Test control still exists: " + old_name)
	_check(_game.personal_bar.get_node_or_null("ViewStocks") == null, "The old stock popup entry still exists")


func _check_layout() -> void:
	var bar = _game.personal_bar
	_check(root.get_visible_rect().encloses(bar.get_global_transform() * bar.get_content_rect()), "HUD content crosses viewport bounds")
	var viewport_width: float = root.get_visible_rect().size.x
	var margin := 24.0 if viewport_width >= 1200.0 else 16.0
	_check(is_equal_approx(bar.position.x, margin), "Cash and portrait lost their left margin")
	_check(is_equal_approx(bar.get_global_rect().end.x, viewport_width - margin), "Cargo panel is not right-aligned")
	_check(bar.size.x - bar.CARGO_PANEL_WIDTH >= bar._crew_hint.get_rect().end.x, "Cargo panel overlaps the crew area")
	_check(bar.mouse_filter == Control.MOUSE_FILTER_IGNORE, "HUD blocks open water input")
	_check(bar.get_node("CashCoin").texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST, "Cash coin uses smoothing")
	_check(not bar.COIN_TEXTURE.get_image().has_mipmaps(), "Coin texture still contains mipmaps")
	for i in bar._stock_hints.size():
		var hint: Control = bar._stock_hints[i]
		var coin: TextureRect = bar._stock_coins[i]
		var value: Label = bar._stock_labels[i]
		var expected_x: float = bar.size.x - bar.CARGO_PANEL_WIDTH + 12.0 + i * bar.CARGO_CELL_WIDTH
		_check(is_equal_approx(hint.position.x, expected_x), "Cargo hover area is out of sync with artwork")
		_check(hint.get_rect().encloses(value.get_rect()) and hint.get_rect().encloses(coin.get_rect()), "Cargo value or coin falls outside its hover area")
		_check(absf((value.position.x + coin.get_rect().end.x) * 0.5 - hint.get_rect().get_center().x) <= 0.5, "Cargo value and coin are not centered")
		_check(coin.texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST, "Stock coin uses smoothing")
	var labels: Array[Label] = [bar._coins_value, bar._round_label]
	labels.append_array(bar._stock_labels)
	for value_label in labels:
		var width := Pixel.FONT.get_string_size(value_label.text, HORIZONTAL_ALIGNMENT_LEFT, -1, value_label.get_theme_font_size("font_size")).x
		_check(width <= value_label.size.x, "HUD value is clipped: " + value_label.text)
		_check(Rect2(Vector2.ZERO, bar.size).encloses(value_label.get_rect()), "HUD label falls outside its layout")


func _choose(index: int) -> void:
	_game.open_character_roster()
	await _frames(3)
	var roster = _game.character_overlay
	await _click(roster.cards[index].get_global_rect().get_center())
	_check(roster.selected_index == index, "Character click missed: target=%d selected=%d card=%s scroll=%s" % [index, roster.selected_index, roster.cards[index].get_global_rect(), roster._scroll.get_global_rect()])
	await _click(roster._confirm.get_global_rect().get_center())
	var deadline := Time.get_ticks_msec() + 3000
	while roster.visible and Time.get_ticks_msec() < deadline:
		await process_frame
	_check(not roster.visible, "Character confirmation did not finish: target=%d selected=%d confirmed=%d gathering=%s elapsed=%s focus=%s" % [index, roster.selected_index, roster.confirmed_index, roster._gathering, roster._gather_elapsed, root.has_focus()])
	await _frames(3)


func _click(position: Vector2) -> void:
	var motion := InputEventMouseMotion.new()
	motion.position = position
	for pressed in [true, false]:
		# Native pointer events can change hover between the synthetic press and release.
		root.push_input(motion, true)
		var event := InputEventMouseButton.new()
		event.position = position
		event.button_index = MOUSE_BUTTON_LEFT
		event.pressed = pressed
		root.push_input(event, true)
		await process_frame


func _key(code: Key) -> void:
	for pressed in [true, false]:
		var event := InputEventKey.new()
		event.keycode = code
		event.pressed = pressed
		root.push_input(event, true)
		await process_frame


func _frames(count: int) -> void:
	for frame in count:
		await process_frame


func _capture(filename: String, bar_only := false, window_size := Vector2i.ZERO) -> void:
	if DisplayServer.get_name() == "headless":
		return
	await RenderingServer.frame_post_draw
	var rendered := root.get_texture().get_image()
	_check(not rendered.is_empty(), "Empty viewport image")
	if bar_only:
		rendered = rendered.get_region(Rect2i(_game.personal_bar.get_global_transform() * _game.personal_bar.get_content_rect()))
	elif window_size != Vector2i.ZERO:
		rendered.resize(window_size.x, window_size.y, Image.INTERPOLATE_BILINEAR)
	_check(rendered.save_png(OUTPUT.path_join(filename)) == OK, "Could not save " + filename)


func _check(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)
		push_error(message)
