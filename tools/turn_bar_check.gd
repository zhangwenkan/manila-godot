extends "res://tools/personal_bar_check.gd"

const TurnBar := preload("res://ui/turn_bar.gd")
const TURN_OUTPUT := "res://.godot/turn_bar_check"

class PreviewController extends Node:
	const STAGES := [
		[TurnBar.Phase.DISPATCH, 1, 1, 0],
		[TurnBar.Phase.SAILING, 1, 1, 1],
		[TurnBar.Phase.DISPATCH, 1, 2, 1],
		[TurnBar.Phase.SAILING, 1, 2, 2],
		[TurnBar.Phase.PIRATES, 1, 2, 2],
		[TurnBar.Phase.DISPATCH, 1, 3, 2],
		[TurnBar.Phase.PILOTS, 1, 3, 2],
		[TurnBar.Phase.SAILING, 1, 3, 3],
		[TurnBar.Phase.SETTLEMENT, 1, 3, 3],
		[TurnBar.Phase.AUCTION, 2, 0, 0],
	]
	var game
	var stage_index := 0

	func _unhandled_key_input(event: InputEvent) -> void:
		if not event.is_pressed() or event.is_echo() or game.character_overlay.visible or game.dice_overlay.visible:
			return
		var bar = game.turn_bar
		if event.keycode >= KEY_1 and event.keycode < KEY_1 + bar.players.size():
			bar.set_current_player(event.keycode - KEY_1)
		elif event.keycode == KEY_H:
			bar.set_harbor_master((bar.harbor_master_index + 1) % bar.players.size())
		elif event.keycode == KEY_P:
			stage_index = (stage_index + 1) % STAGES.size()
			var stage: Array = STAGES[stage_index]
			bar.set_stage(stage[0], stage[1], stage[2], stage[3])
			if bar.phase == TurnBar.Phase.SAILING:
				bar.set_current_player(bar.harbor_master_index)
		elif event.keycode == KEY_R:
			stage_index = 0
			game.reset_voyage_flow()
			bar.set_current_player(0)
			bar.set_harbor_master(2)
			bar.set_stage(TurnBar.Phase.DISPATCH, 1, 1, 0)
			game.personal_bar.conceal_stocks()
		elif event.keycode == KEY_C:
			game.open_character_roster()
		elif event.keycode == KEY_D:
			game.inspect_dice()
		else:
			return
		get_viewport().set_input_as_handled()


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(TURN_OUTPUT))
	root.title = "Manila - UI-02 Preview"
	root.content_scale_size = Vector2i(2048, 1152)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.size = Vector2i(1280, 720)
	_game = load("res://scene/scene_bg.tscn").instantiate()
	root.add_child(_game)
	var controller := PreviewController.new()
	controller.game = _game
	root.add_child(controller)
	await _frames(5)
	if "--preview" in OS.get_cmdline_user_args():
		var instructions := Pixel.label(_game.get_node("CanvasLayer"), "预览  1–5 换人 / H 港务长 / P 阶段 / R 重置阶段 / C 选角 / D 骰子 · 点击持股翻面", Rect2(224, 20, 1600, 36), 24, Color("f0dfba"))
		instructions.add_theme_color_override("font_shadow_color", Color("1b292b"))
		instructions.add_theme_constant_override("shadow_offset_x", 2)
		instructions.add_theme_constant_override("shadow_offset_y", 2)
		instructions.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		if "--auto" in OS.get_cmdline_user_args():
			await _preview_tour()
			print("TURN_BAR_TOUR completed failures=%d" % _failures.size())
			_game.queue_free()
			controller.queue_free()
			await _frames(2)
			quit(0 if _failures.is_empty() else 1)
		return

	var turn = _game.turn_bar
	var hud = _game.personal_bar
	_check(turn.players.size() == 5, "Preview must contain five distinct players")
	_check(turn._stage_title.text == "派遣 1/3", "Opening phase is wrong")
	_check(hud._round_label.text == "第 1 航程", "Voyage label is missing")
	_check(hud.holdings.size() == 2 and hud._stock_cards.size() == 2, "Opening hand must have exactly two cards")
	_check_concealed()
	_check_compact_layout()
	_check_stock_layout()
	await _capture_turn("compact_hud.png")
	await _capture_turn("compact_detail.png", true)
	await _capture_turn("window_1280.png", false, Vector2i(1280, 720))

	var first_id: String = hud.character_id
	var first_hand: Array = hud.holdings.duplicate()
	hud.set_holdings(["silk", "nutmeg", "jade", "ginseng"])
	await _frames(3)
	_check_concealed()
	for i in 4:
		await _click_stock(i)
		_check(hud._stock_card_faces[i].texture.resource_path == "res://stock/%s.webp" % hud.holdings[i], "Stock artwork is mapped to the wrong cargo")
	_check_stock_layout()
	await _capture_turn("all_stock_faces.png", true)
	await _capture_turn("stock_faces_window_1280.png", false, Vector2i(1280, 720))
	hud.set_holdings(first_hand)
	await _frames(3)
	hud.set_resources(27, 2, 3)
	hud.set_stock_values({"silk": 10, "jade": 20})
	var market: Dictionary = hud.stock_values.duplicate()
	await _click_stock(0)
	_check(hud._stock_revealed[0] and not hud._stock_revealed[1], "Click must flip only the selected card")
	_check(hud._stock_card_faces[0].texture.resource_path == "res://stock/%s.webp" % first_hand[0], "Face must show the actual held cargo artwork")
	await _capture_turn("stock_face.png", true)
	await _click_stock(0)
	_check_concealed()
	await _key(KEY_2)
	_check(hud.character_id == turn.players[1].character_name_en and hud.character_id != first_id, "Actor change must replace the portrait")
	_check(hud.coins == 30 and hud.remaining_crew == 3, "Actor change must replace personal resources")
	_check(hud.holdings == _game._player_resources[hud.character_id].holdings, "Hand belongs to the wrong player")
	hud.set_resources(41, 1, 4)
	hud.set_holdings(["ginseng", "jade", "silk", "nutmeg", "silk"])
	await _frames(3)
	hud._stock_scroll.scroll_horizontal = 10000
	await _frames(3)
	var last: Button = hud._stock_cards[4]
	await _click(last.get_global_rect().get_center())
	_check(hud._stock_revealed[4], "Extra holdings must remain accessible by scrolling")
	await _capture_turn("extended_hand.png", true)
	await _key(KEY_1)
	_check(hud.character_id == first_id and hud.coins == 27 and hud.remaining_crew == 2 and hud.crew_capacity == 3, "Returning to a player lost saved resources")
	_check(hud.holdings == first_hand and hud._stock_scroll.scroll_horizontal == 0, "Returning to a player lost or scrolled their hand")
	_check_concealed()
	await _key(KEY_2)
	_check(hud.coins == 41 and hud.remaining_crew == 1 and hud.crew_capacity == 4 and hud.holdings.size() == 5, "Second player's data was overwritten")
	for i in 5:
		await _key(KEY_1 + i)
		_check(hud.character_id == turn.players[i].character_name_en, "Current actor does not own the bottom HUD")
		_check(hud.stock_values == market, "Changing players changed public prices")
		_check_concealed()
		_check_compact_layout()
		await _click_stock(0)
		await _key(KEY_H)
		_check(turn.current_player_index == i, "Changing harbor master changed the actor")
		_check(hud._stock_revealed[0], "Public role update unexpectedly changed the hand")

	for master in 5:
		turn.set_harbor_master(master)
		for actor in 5:
			turn.set_current_player(actor)
			_check_compact_layout()
			if master != actor:
				var distance := (master - actor + 5) % 5
				var relation := "下家" if distance == 1 else "后 %d 位" % distance
				_check(turn._master_hint.text.ends_with(relation), "Relative master position is wrong")
	await _key(KEY_R)
	turn.set_harbor_master(0)
	await _capture_turn("master_arc.png", true)
	for i in 9:
		await _key(KEY_P)
		var expected: Array = PreviewController.STAGES[i + 1]
		_check(turn.phase == expected[0] and turn.voyage_number == expected[1], "Phase preview did not advance")
		_check(turn.deployment_round == expected[2] and turn.sailing_number == expected[3], "Deployment and sailing counters were conflated")
		_check(hud.round_number == turn.voyage_number, "Voyage did not reach bottom HUD")
		_check_compact_layout()
		if turn.phase == TurnBar.Phase.SETTLEMENT:
			_check_concealed()
			await _click_stock(0)
			_check_concealed()
			_check(not hud.can_view_stocks, "Settlement retains an active player's hand control")
			await _capture_turn("settlement.png", true)
	await _capture_turn("next_voyage.png", true)
	turn.set_stage(TurnBar.Phase.DISPATCH, 120, 3, 2)
	_check_compact_layout()
	await _key(KEY_R)

	var five_players: Array = turn.players.duplicate()
	turn.set_players(turn.players.slice(0, 3))
	turn.set_stage(TurnBar.Phase.DISPATCH, 1, 4, 2)
	hud.set_resources(27, 4, 4)
	_check(turn._stage_title.text == "派遣 4/4", "Three-player deployment count is wrong")
	_check_compact_layout()
	turn.set_players(five_players)
	await _key(KEY_R)

	await _click_stock(0)
	hud.notification(Node.NOTIFICATION_APPLICATION_FOCUS_OUT)
	_check_concealed()
	await _click_stock(0)
	var before: Transform2D = turn.get_global_transform_with_canvas()
	_game._pan_camera(800)
	await _frames(18)
	_check(before.is_equal_approx(turn.get_global_transform_with_canvas()), "HUD moved with camera")
	_game._is_manual_camera = false
	await _key(KEY_D)
	_check(not turn.visible and not hud.visible, "HUD overlaps dice")
	_check_concealed()
	await _key(KEY_5)
	_check(turn.current_player_index == 0, "Preview shortcuts passed through dice modal")
	await _key(KEY_ESCAPE)
	_check(turn.visible and hud.visible, "HUD did not return from dice")
	await _click_stock(0)
	await _key(KEY_C)
	_check(not turn.visible and not hud.visible, "HUD overlaps roster")
	_check_concealed()
	await _click(_game.character_overlay.cards[1].get_global_rect().get_center())
	await _key(KEY_ESCAPE)
	_check(hud.character_id == first_id, "Cancelled selection changed the player")
	for i in 6:
		await _choose(i)
		_check(turn.players[0].character_name_en == hud.character_id, "Confirmed character did not reach the active seat")
		var seen := {}
		for card in turn.players:
			_check(not seen.has(card.character_name_en), "Preview duplicated a character")
			seen[card.character_name_en] = true
		_check_compact_layout()
	await _choose(2)
	hud.set_holdings([])
	_check(hud._stock_cards.is_empty(), "Empty hand leaves stale cards")
	hud.set_holdings(first_hand)
	for dimensions in [Vector2i(1280, 720), Vector2i(640, 480)]:
		root.content_scale_size = dimensions
		root.size = dimensions
		await _frames(5)
		_check_compact_layout()
		_check_stock_layout()
		var top_of_card: Vector2 = hud._stock_cards[0].get_global_rect().position + Vector2(20, 20) * hud.scale
		await _click(top_of_card)
		_check(hud._stock_revealed[0], "Raised stock card does not receive clicks")
		await _capture_turn("native_face_%d.png" % dimensions.x)
		hud.conceal_stocks()
		await _capture_turn("native_%d.png" % dimensions.x)
		hud.set_holdings(["ginseng", "jade", "silk", "nutmeg", "silk"])
		await _frames(3)
		_check(hud._stock_scroll.get_h_scroll_bar().visible, "Overflow hand is missing its scrollbar")
		hud._stock_scroll.scroll_horizontal = 10000
		await _frames(3)
		_check(hud._stock_scroll.scroll_horizontal > 0, "Overflow hand did not scroll")
		_check_stock_layout()
		_check(hud._stock_scroll.get_global_rect().grow(0.1).encloses(hud._stock_cards[4].get_global_rect()), "Last stock is not fully reachable at %s: scroll=%s card=%s" % [dimensions, hud._stock_scroll.get_global_rect(), hud._stock_cards[4].get_global_rect()])
		await _click_stock(4)
		_check(hud._stock_revealed[4], "Scrolled stock did not receive click: viewport=%s visible=%s allowed=%s disabled=%s focus=%s card=%s scroll=%s" % [dimensions, hud.is_visible_in_tree(), hud.can_view_stocks, hud._stock_cards[4].disabled, root.has_focus(), hud._stock_cards[4].get_global_rect(), hud._stock_scroll.get_global_rect()])
		await _capture_turn("native_hand_%d.png" % dimensions.x)
		hud.set_holdings(first_hand)
		await _frames(3)
		_check_concealed()
	print("TURN_BAR_CHECK failures=%d output=%s" % [_failures.size(), ProjectSettings.globalize_path(TURN_OUTPUT)])
	_game.queue_free()
	controller.queue_free()
	await _frames(2)
	quit(0 if _failures.is_empty() else 1)


func _check_concealed() -> void:
	var hud = _game.personal_bar
	_check(not hud._stock_revealed.has(true), "Private cards did not turn face down")
	for i in hud._stock_cards.size():
		_check(hud._stock_card_faces[i].texture.resource_path == "res://stock/back.webp", "Hidden card does not show the shared back")
		_check(not hud._stock_cards[i].tooltip_text.contains(hud.CARGO_NAMES[hud.CARGO_IDS.find(hud.holdings[i])]), "Hidden tooltip leaks cargo")


func _check_compact_layout() -> void:
	_check_layout()
	var turn = _game.turn_bar
	var hud = _game.personal_bar
	_check(root.get_visible_rect().encloses(turn.get_global_rect()), "Phase strip crosses viewport")
	_check(turn.position.y > root.get_visible_rect().size.y * 0.5, "Phase strip still occupies the top")
	_check(not turn.get_global_rect().intersects(hud.get_global_transform() * hud.get_content_rect()), "Phase and personal content overlap")
	_check(turn.mouse_filter == Control.MOUSE_FILTER_IGNORE, "Phase strip blocks board input")
	_check(hud._stock_scroll.get_rect().position.x >= hud._crew_hint.get_rect().end.x, "Hand overlaps crew")
	_check(hud._stock_scroll.get_rect().end.x <= hud.size.x - hud.CARGO_PANEL_WIDTH, "Hand overlaps public prices")
	_check(hud.is_harbor_master == (turn.current_player_index == turn.harbor_master_index), "Master arc belongs to the wrong player")
	_check(turn._master_hint.visible != hud.is_harbor_master, "Master identity is missing or duplicated")
	for letter in hud._master_letters:
		_check(letter.visible == hud.is_harbor_master, "Master letter visibility is wrong")
	var card = turn.players[turn.current_player_index]
	_check(hud._portrait == (card.avatar if card.avatar else card.portrait), "Actor portrait is wrong")
	var crop: Rect2 = card.avatar_region
	_check(hud._portrait_material.get_shader_parameter("source_region") == Vector4(crop.position.x, crop.position.y, crop.size.x, crop.size.y), "Actor crop was lost")
	for label: Label in [turn._stage_title, turn._master_hint]:
		if not label.visible:
			continue
		var width := Pixel.FONT.get_string_size(label.text, HORIZONTAL_ALIGNMENT_LEFT, -1, label.get_theme_font_size("font_size")).x
		_check(width <= label.size.x, "Phase text is clipped: " + label.text)
		_check(Rect2(Vector2.ZERO, turn.size).encloses(label.get_rect()), "Phase label is outside strip")


func _check_stock_layout() -> void:
	var hud = _game.personal_bar
	var scroll_rect: Rect2 = hud._stock_scroll.get_global_rect()
	var available_bottom := scroll_rect.end.y
	var scrollbar: HScrollBar = hud._stock_scroll.get_h_scroll_bar()
	if scrollbar.visible:
		available_bottom = scrollbar.get_global_rect().position.y
	for i in hud._stock_cards.size():
		var card: Button = hud._stock_cards[i]
		var face: TextureRect = hud._stock_card_faces[i]
		var rect := card.get_global_rect()
		_check(card.size.is_equal_approx(hud.STOCK_CARD_SIZE), "Stock card was stretched by its container")
		_check(rect.position.y >= scroll_rect.position.y - 0.1 and rect.end.y <= available_bottom + 0.1, "Stock card is vertically clipped")
		_check(Rect2(Vector2.ZERO, card.size).encloses(face.get_rect()), "Stock art crosses its button")
		_check(face.stretch_mode == TextureRect.STRETCH_KEEP_ASPECT_CENTERED, "Stock art must fit without cropping or distortion")
		_check(face.texture_filter == CanvasItem.TEXTURE_FILTER_LINEAR, "Stock artwork is not using independent smooth filtering")
		if hud.holdings.size() == 2:
			_check(scroll_rect.encloses(rect), "Opening pair is not fully visible")
	for control: Control in [hud._portrait_image, hud._crew_hint]:
		_check(not scroll_rect.intersects(control.get_global_rect()), "Stock cards overlap player identity")
	for hint in hud._stock_hints:
		_check(not scroll_rect.intersects(hint.get_global_rect()), "Stock cards overlap public prices")


func _click_stock(index: int) -> void:
	await _frames(2)
	await _click(_game.personal_bar._stock_cards[index].get_global_rect().get_center())


func _capture_turn(filename: String, bar_only := false, window_size := Vector2i.ZERO) -> void:
	if DisplayServer.get_name() == "headless":
		return
	await RenderingServer.frame_post_draw
	var rendered := root.get_texture().get_image()
	if bar_only:
		var rect: Rect2 = (_game.personal_bar.get_global_transform() * _game.personal_bar.get_content_rect()).merge(_game.turn_bar.get_global_rect())
		rendered = rendered.get_region(Rect2i(rect))
	elif window_size != Vector2i.ZERO:
		rendered.resize(window_size.x, window_size.y, Image.INTERPOLATE_BILINEAR)
	_check(rendered.save_png(TURN_OUTPUT.path_join(filename)) == OK, "Could not save " + filename)


func _preview_tour() -> void:
	for key in [KEY_R, KEY_3, KEY_H, KEY_1, KEY_P, KEY_P, KEY_5, KEY_H]:
		await create_timer(1.5).timeout
		await _key(key)
		_check_compact_layout()
		await _click_stock(0)
	_game.personal_bar.conceal_stocks()
	_check_concealed()
