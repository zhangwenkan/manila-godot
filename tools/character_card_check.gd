extends SceneTree

const OUTPUT := "res://.godot/character_card_check"
var _failures: Array[String] = []
var _confirmation_count := 0
var _closed_count := 0


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
	roster.closed.connect(func(): _closed_count += 1)
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
	var chosen_id: String = roster.cards[5].character_name_en
	var start_center: Vector2 = roster.cards[5].get_global_rect().get_center()
	await _click(roster._confirm.get_global_rect().get_center())
	_check(game.selected_character_id == chosen_id and roster.visible and roster._gathering, "Confirm did not commit and start gathering")
	_check(not game.roll_button.visible and roster._confirm.disabled, "Game controls became active during gathering")
	_check(_confirmation_count == 1 and _closed_count == 0, "Confirmation was not emitted exactly once before closing")
	roster._confirm_selection()
	roster._select_card(0)
	roster.open()
	_check(roster.selected_index == 5 and _confirmation_count == 1, "Repeated input changed a gathering selection")
	await _sample_gather(roster, 0.22, "gather_travel.png")
	_check(roster.cards[5].get_global_rect().get_center().distance_to(start_center) > 100, "Selected card did not move towards the center")
	_check_gather_layers(roster)
	await _sample_gather(roster, 0.53, "gather_stack.png")
	_check_stack_fits(roster)
	roster._gather_tween.play()
	await _wait_for_close(roster)
	_check(game.roll_button.visible and _confirmation_count == 1, "Selection signal or game controls incorrect")
	_check(_closed_count == 1, "Gathering did not close exactly once")
	_check_restored(roster)
	await _click(game.select_character_button.get_global_rect().get_center())
	_check(roster.selected_index == 5, "Confirmed selection was not restored")
	await _click(roster.cards[0].get_global_rect().get_center())
	await _key(KEY_ESCAPE)
	_check(not roster.visible and game.selected_character_id == chosen_id, "Cancel changed the confirmed character")
	game._on_select_character_pressed()
	await _frames(4)
	_check(roster.selected_index == 5, "Cancelled selection leaked into the next opening")
	await _key(KEY_LEFT)
	_check(roster.cards[4].has_focus(), "Keyboard navigation failed")
	await _key(KEY_ENTER)
	_check(roster.selected_index == 4, "Keyboard selection failed")
	await _click(roster._close.get_global_rect().get_center())
	_check(not roster.visible, "Close button failed")
	# A confirmed selection survives skipping the feedback. Its old tween must not close a new opening.
	game._on_select_character_pressed()
	await _frames(4)
	await _click(roster.cards[2].get_global_rect().get_center())
	await _click(roster._confirm.get_global_rect().get_center())
	await _key(KEY_ESCAPE)
	_check(not roster.visible and _confirmation_count == 2, "Escape did not skip gathering cleanly")
	_check(game.selected_character_id == roster.cards[2].character_name_en, "Skipping feedback reverted the committed character")
	_check_restored(roster)
	game._on_select_character_pressed()
	await create_timer(0.8).timeout
	_check(roster.visible and roster.selected_index == 2 and not roster._gathering, "An interrupted tween affected the next opening")
	var before_close := _closed_count
	roster.close()
	roster.close()
	roster._confirm_selection()
	_check(_closed_count == before_close + 1 and _confirmation_count == 2, "Hidden roster emitted duplicate signals")
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
	_check(roster._gathering and not roster._scroll.follow_focus, "Scrolled list interferes with gathering")
	await _sample_gather(roster, 0.22, "narrow_gather_travel.png")
	_check_gather_layers(roster)
	await _sample_gather(roster, 0.53, "narrow_gather_stack.png")
	_check_stack_fits(roster)
	roster._gather_tween.play()
	await _wait_for_close(roster)
	_check(_confirmation_count == 3, "Narrow confirmation failed")
	_check_restored(roster)
	# Resizing while cards are detached must preserve the effect and restore the new grid afterwards.
	game._on_select_character_pressed()
	await _frames(4)
	await _click(roster._confirm.get_global_rect().get_center())
	roster._gather_tween.pause()
	root.content_scale_size = Vector2i(1024, 768)
	root.size = Vector2i(1024, 768)
	await _frames(4)
	_check(roster._gathering, "Resize interrupted confirmation")
	await _sample_gather(roster, 0.53, "resized_gather_stack.png")
	_check_gather_layers(roster)
	_check_stack_fits(roster)
	roster._gather_tween.play()
	await _wait_for_close(roster)
	_check(_confirmation_count == 4, "Resized animation emitted duplicate confirmation")
	_check_restored(roster)
	game._on_select_character_pressed()
	await _frames(4)
	_check(roster._scroll.get_global_rect().has_point(roster.cards[5].get_global_rect().get_center()), "Restored selection was not scrolled into view: card=%s list=%s scroll=%d" % [roster.cards[5].get_global_rect(), roster._scroll.get_global_rect(), roster._scroll.scroll_vertical])
	await _key(KEY_LEFT)
	_check(roster.cards[4].has_focus(), "Focus neighbors were not restored after gathering")
	# Scene teardown also needs to stop a live animation without leaving detached cards or callbacks.
	roster._confirm_selection()
	game.queue_free()
	await create_timer(0.8).timeout
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
	if DisplayServer.get_name() == "headless":
		return
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


func _sample_gather(roster, elapsed: float, filename: String) -> void:
	var tween: Tween = roster._gather_tween
	tween.pause()
	tween.custom_step(maxf(0.0, elapsed - roster._gather_elapsed))
	await _capture(filename)


func _wait_for_close(roster) -> void:
	var deadline := Time.get_ticks_msec() + 2000
	while roster.visible and Time.get_ticks_msec() < deadline:
		await process_frame
	_check(not roster.visible, "Gathering did not finish within two seconds")
	if roster.visible:
		roster.close()


func _check_gather_layers(roster) -> void:
	var chosen = roster.cards[roster.confirmed_index]
	for card in roster.cards:
		_check(card.get_parent() == roster._gather_layer, "A gathering card remained in the scrolling layout")
		_check(card.disabled and card.focus_mode == Control.FOCUS_NONE, "A gathering card still accepts input")
		_check(card.modulate.a == 1.0 and card.self_modulate.a == 1.0, "Gathering made a card transparent")
		_check(card == chosen or card.z_index < chosen.z_index, "Selected card is covered by another card")


func _check_stack_fits(roster) -> void:
	var bounds: Rect2 = roster._gather_layer.get_global_rect()
	for card in roster.cards:
		_check(bounds.encloses(card.get_global_rect()), "Finished stack clips outside its animation area")
		_check(card.get_global_rect().get_center().distance_to(bounds.get_center()) < 24, "A card did not join the stack")


func _check_restored(roster) -> void:
	_check(not roster._gathering and roster._gather_layer.get_child_count() == 0, "Animation left detached cards behind")
	_check(roster._scroll.visible and roster._scroll.follow_focus, "Scrolling was not restored")
	for card in roster.cards:
		_check(card.get_parent() == roster._sheet and card.scale == Vector2.ONE and card.z_index == 0, "Card did not return to its grid pose")
		_check(not card.disabled and not card._animation_locked and card.focus_mode == Control.FOCUS_ALL, "Card input was not restored")


func _check(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)
		push_error(message)
