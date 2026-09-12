extends SceneTree

const OUTPUT := "res://.godot/character_card_check"
var _failures: Array[String] = []
var _confirmation_count := 0


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	if "--screenshots" in OS.get_cmdline_user_args():
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT))
	var game = load("res://scene/scene_bg.tscn").instantiate()
	root.add_child(game)
	await _frames(4)
	await _click(game.select_character_button.get_global_rect().get_center())
	var roster = game.character_overlay
	_check(roster.visible and not game.roll_button.visible, "Character modal did not open")
	_check(roster.cards.size() == 6, "Expected six character cards")
	_check(roster._confirm.disabled, "Confirmation must require a selection")
	roster.character_confirmed.connect(func(_id, _name): _confirmation_count += 1)
	await _frames(15)
	await _capture("desktop.png")
	for i in roster.cards.size():
		var card = roster.cards[i]
		await _click(card.get_global_rect().get_center())
		_check(roster.selected_index == i and not roster._confirm.disabled, "Mouse selection failed for " + str(card.name))
		_check(card.get_global_rect().end.x <= root.get_visible_rect().size.x, "Card crosses the viewport edge")
		_check(card._source_region.size.x > 900, "Missing illustration crop")
		for node in card._labels.get_children():
			var label := node as Label
			_check(label.get_rect().end.y <= 540, "Text overflows card: " + label.text)
			_check(label.get_rect().end.x <= 280, "Text crosses card edge: " + label.text)
		_check(card._labels.get_node("Slogan").get_line_count() <= 3, "Slogan overflow")
	await _frames(15)
	await _capture("selected.png")
	await _click(roster._confirm.get_global_rect().get_center())
	_check(game.selected_character_id == "Lakan" and not roster.visible, "Confirm did not commit and close")
	_check(game.roll_button.visible and _confirmation_count == 1, "Selection signal or game controls incorrect")
	await _click(game.select_character_button.get_global_rect().get_center())
	_check(roster.selected_index == 5, "Confirmed selection was not restored")
	await _click(roster.cards[0].get_global_rect().get_center())
	await _key(KEY_ESCAPE)
	_check(not roster.visible and game.selected_character_id == "Lakan", "Cancel changed the confirmed character")
	game._on_select_character_pressed()
	await _frames(4)
	_check(roster.selected_index == 5, "Cancelled selection leaked into the next opening")
	await _key(KEY_LEFT)
	_check(roster.cards[4].has_focus(), "Keyboard navigation failed")
	await _key(KEY_ENTER)
	_check(roster.selected_index == 4, "Keyboard selection failed")
	await _click(roster._close.get_global_rect().get_center())
	_check(not roster.visible, "Close button failed")
	# Exercise the same controls at native narrow dimensions, independent of game viewport stretch.
	root.content_scale_size = Vector2i(390, 844)
	root.size = Vector2i(390, 844)
	await _frames(4)
	game._on_select_character_pressed()
	await _frames(5)
	_check(roster.size.is_equal_approx(Vector2(390, 844)), "Narrow modal does not fill viewport")
	roster.cards[0].grab_focus()
	await _frames(15)
	await _capture("narrow.png")
	for i in roster.cards.size():
		roster.cards[i].grab_focus()
		await _frames(4)
		var card = roster.cards[i]
		var position: Vector2 = card.get_global_rect().get_center()
		_check(roster._scroll.get_global_rect().has_point(position), "Narrow card is unreachable")
		_check(card.get_global_rect().end.x <= 390, "Narrow card clips horizontally")
		await _click(position)
		_check(roster.selected_index == i, "Scrolled card click failed")
	await _frames(15)
	await _capture("narrow_scrolled.png")
	await _click(roster._confirm.get_global_rect().get_center())
	_check(not roster.visible and _confirmation_count == 2, "Narrow confirmation failed")
	game.queue_free()
	await _frames(2)
	print("CHARACTER_CARD_CHECK failures=%d confirmations=%d" % [_failures.size(), _confirmation_count])
	quit(0 if _failures.is_empty() else 1)


func _click(position: Vector2) -> void:
	var motion := InputEventMouseMotion.new()
	motion.position = position
	root.push_input(motion, true)
	for pressed in [true, false]:
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


func _capture(filename: String) -> void:
	await RenderingServer.frame_post_draw
	var rendered := root.get_texture().get_image()
	_check(not rendered.is_empty(), "Empty render")
	var colors := {}
	for y in range(0, rendered.get_height(), 8):
		for x in range(0, rendered.get_width(), 8):
			colors[rendered.get_pixel(x, y).to_rgba32()] = true
	_check(colors.size() > 150, "Missing portraits or blank UI")
	if "--screenshots" in OS.get_cmdline_user_args():
		rendered.save_png(OUTPUT.path_join(filename))


func _check(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)
		push_error(message)
