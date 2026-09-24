extends "res://tools/personal_bar_check.gd"

const SEAT_OUTPUT := "res://.godot/boat_seat_check"
var _controller: Node

class PreviewController extends Node:
	var game
	var initial_resources: Dictionary
	var initial_players: Array
	var initial_master: int
	var initial_character: String
	var initial_confirmed: int

	func _ready() -> void:
		initial_resources = game._player_resources.duplicate(true)
		initial_players = game.turn_bar.players.duplicate()
		initial_master = game.turn_bar.harbor_master_index
		initial_character = game.selected_character_id
		initial_confirmed = game.character_overlay.confirmed_index

	func reset() -> void:
		var panel = game.placement_panel
		var was_open: bool = panel.shade.visible
		panel.close()
		panel.result_notice.hide()
		game._displayed_character_id = ""
		game._player_resources = initial_resources.duplicate(true)
		game.selected_character_id = initial_character
		game.character_overlay.confirmed_index = initial_confirmed
		game.turn_bar.players.assign(initial_players)
		game.turn_bar.current_player_index = 0
		game.turn_bar.harbor_master_index = initial_master
		panel.state.arrived.assign([false, false, false])
		panel.state.set_preview_occupants({})
		game.reset_voyage_flow()
		game.turn_bar.set_stage(game.turn_bar.Phase.DISPATCH, 1, 1, 0)
		game.personal_bar.conceal_stocks()
		if was_open:
			panel.open()

	func _unhandled_key_input(event: InputEvent) -> void:
		if not event.is_pressed() or event.is_echo() or game.character_overlay.visible or game.dice_overlay.visible:
			return
		var panel = game.placement_panel
		var players: Array = game.turn_bar.players
		match event.keycode:
			KEY_M:
				panel.state.set_preview_occupants({"ship_0_0": players[0], "ship_1_0": players[1], "ship_2_0": players[0], "ship_2_1": players[1], "pirate_0": players[2], "harbor_0": players[3]})
			KEY_F:
				var full := {}
				for i in panel.state.positions.size():
					full[panel.state.positions[i].id] = players[i % players.size()]
				panel.state.set_preview_occupants(full)
			KEY_N:
				game.turn_bar.set_current_player((game.turn_bar.current_player_index + 1) % players.size())
			KEY_R:
				reset()
			KEY_A:
				panel.state.set_ship_arrived(0, not panel.state.arrived[0])
			KEY_C:
				game.open_character_roster()
			KEY_D:
				game.inspect_dice()
			_:
				return
		get_viewport().set_input_as_handled()


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(SEAT_OUTPUT))
	root.title = "Manila - UI-04 Dispatch"
	root.content_scale_size = Vector2i(2048, 1152)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.size = Vector2i(1280, 720)
	_game = load("res://scene/scene_bg.tscn").instantiate()
	root.add_child(_game)
	_controller = PreviewController.new()
	_controller.game = _game
	root.add_child(_controller)
	await _frames(8)
	if "--preview" in OS.get_cmdline_user_args():
		if "--auto" not in OS.get_cmdline_user_args():
			root.title += " | R: reset A: arrived M/F: fixtures N: next C: roster D: dice"
		_game.placement_panel.open()
		if "--auto" not in OS.get_cmdline_user_args():
			return
		create_timer(60).timeout.connect(_timeout)
		await _tour()
		await _finish()
		return
	create_timer(90).timeout.connect(_timeout)
	var panel = _game.placement_panel
	var state = panel.state
	var turn = _game.turn_bar
	var hud = _game.personal_bar
	var original_resources := [hud.coins, hud.remaining_crew, hud.holdings.duplicate(), _game._player_resources.duplicate(true)]
	_check(state.positions.size() == 21 and panel.buttons.size() == 21, "All 21 positions must share one panel")
	_check(state.owners.is_empty() and not panel.shade.visible, "Opening scene must contain no workers or open modal")
	for i in 3:
		var display = _game.boats[i].get_node("VisualRoot/Seats")
		_check(display.visible and display.state == state and display.ship_index == i, "Boat must observe the shared state")
		_check(display.get_child_count() == 0, "Scene boat still has input controls")
		_check(_game.boats[i].get_node_or_null("VisualRoot/WorkerLakan") == null, "Scene still has a fixed worker")
		_check(display.z_index < _game.boats[i].get_node("VisualRoot/BoatTop").z_index, "Crew must be behind the front hull")
		await _click(display.get_global_transform_with_canvas() * Vector2(132, 50))
	_check(panel.selected_id.is_empty() and state.owners.is_empty(), "World boat click must not select or place")
	await _capture_seats("empty_scene")
	await _click_control(panel.launcher)
	_check(panel.shade.visible, "Launcher did not open the panel")
	_check_geometry()
	await _capture_seats("all_positions")
	var expected_costs := {"ship_0": [1, 2, 3], "ship_1": [3, 4, 5], "ship_2": [3, 4, 5, 5], "harbor": [4, 3, 2], "shipyard": [4, 3, 2], "pirate": [5, 5], "pilot": [2, 5], "insurance": [0]}
	for group in expected_costs:
		var costs: Array = []
		for item in state.positions:
			if item.group == group:
				costs.append(item.cost)
		_check(costs == expected_costs[group], "Incorrect costs for " + group)
	for id in ["ship_0_1", "ship_1_2", "ship_2_3", "pirate_1"]:
		await _click_slot(id)
		_check(panel.selected_id.is_empty(), "Ordered slot accepted early selection: " + id)
	for id in ["ship_0_0", "ship_1_0", "ship_2_0", "harbor_0", "harbor_1", "harbor_2", "shipyard_0", "shipyard_1", "shipyard_2", "pirate_0", "pilot_0", "pilot_1", "insurance_0"]:
		await _click_slot(id)
		_check(panel.selected_id == id, "Slot click failed: " + id)
		_check(panel.detail.text.contains(state.get_position(id).title), "Selection detail is missing")
		await _click_slot(id)
		_check(panel.selected_id.is_empty(), "Second click must cancel: " + id)
	_check(state.owners.is_empty(), "Preview selection placed a worker")
	_check([hud.coins, hud.remaining_crew, hud.holdings, _game._player_resources] == original_resources, "Selection changed resources or paid insurance")
	await _click_slot("insurance_0")
	await _capture_seats("insurance_selected")
	await _click_control(panel.cancel_button)
	_check(panel.selected_id.is_empty() and panel.shade.visible, "Cancel must only clear selection")
	await _click_slot("ship_0_0")
	await _key(KEY_ESCAPE)
	_check(panel.selected_id.is_empty() and panel.shade.visible, "First Escape must clear selection")
	await _key(KEY_ESCAPE)
	_check(not panel.shade.visible, "Second Escape must close")
	await _click_control(panel.launcher)
	await _click_slot("pilot_0")
	await _click_control(panel.close_button)
	_check(panel.selected_id.is_empty() and state.owners.is_empty(), "Closing must not commit a worker")
	await _click_control(panel.launcher)
	await _click(_game.left_pan_button.get_global_rect().get_center())
	_check(not _game._is_manual_camera, "Shade allowed camera button click-through")
	await _click(hud._stock_cards[0].get_global_rect().get_center())
	_check(not hud._stock_revealed.has(true), "Shade allowed private-card click-through")
	await _key(KEY_M)
	_check(state.ship_occupants(2) == [turn.players[0], turn.players[1], null, null], "Shared mixed-crew fixture is wrong")
	for id in ["ship_0_0", "ship_1_0", "ship_2_0", "ship_2_1", "pirate_0", "harbor_0"]:
		_check(panel.buttons[id].disabled, "Occupied position is clickable: " + id)
	for id in ["ship_2_2", "ship_2_3", "pirate_1"]:
		await _click_slot(id)
		_check(panel.selected_id == id, "Equal-price seat or second pirate is not selectable: " + id)
	await _capture_seats("mixed_panel")
	await _click_control(panel.close_button)
	await _capture_seats("mixed_scene")
	await _click_control(panel.launcher)
	await _click_slot("ship_2_3")
	turn.set_harbor_master(1)
	_check(panel.selected_id == "ship_2_3", "Public role update cleared valid selection")
	await _key(KEY_N)
	_check(panel.selected_id.is_empty() and panel.actor == turn.players[1], "Actor change retained stale selection")
	await _click_slot("ship_2_3")
	turn.set_stage(turn.Phase.DISPATCH, 1, 2, 1)
	_check(panel.selected_id.is_empty(), "Deployment change retained selection")
	await _click_slot("ship_2_3")
	turn.set_stage(turn.Phase.SAILING, 1, 2, 2)
	_check(panel.selected_id.is_empty() and not panel.shade.visible and panel.launcher.disabled, "Sailing must lock and close placement")
	panel.open()
	_check(not panel.shade.visible, "Non-dispatch phase opened placement")
	turn.set_stage(turn.Phase.DISPATCH, 1, 3, 2)
	for modal in ["dice", "roster"]:
		await _click_control(panel.launcher)
		await _click_slot("ship_2_3")
		if modal == "dice":
			_game.inspect_dice()
		else:
			_game.open_character_roster()
		await _frames(3)
		_check(not panel.visible and not panel.shade.visible and panel.selected_id.is_empty(), "Modal did not hide/clear placement: " + modal)
		panel.open()
		panel.select("insurance_0")
		await _click_slot("ship_2_3")
		_check(panel.selected_id.is_empty(), "Modal allowed placement input: " + modal)
		await _key(KEY_ESCAPE)
		_check(panel.visible and panel.interaction_enabled and not panel.shade.visible, "Placement did not recover from " + modal)
	await _click_control(panel.launcher)
	await _key(KEY_F)
	for item in state.positions:
		_check(panel.buttons[item.id].disabled, "Full board has an enabled slot")
	await _capture_seats("full_panel")
	await _key(KEY_R)
	var before: Transform2D = panel.sheet.get_global_transform_with_canvas()
	_game.boats[0].position.x += 600
	_game.boats[0].visual_root.rotation_degrees = 3
	_game._pan_camera(400)
	await _frames(18)
	_check(before.is_equal_approx(panel.sheet.get_global_transform_with_canvas()), "Panel moves with the world camera")
	await _click_slot("ship_0_0")
	_check(panel.selected_id == "ship_0_0", "Moving world broke panel click")
	_game.boats[0].position.x -= 600
	_game._is_manual_camera = false
	_game.camera.position = _game.layout_view_size * 0.5
	await _key(KEY_R)
	for dimensions in [Vector2i(1280, 720), Vector2i(1024, 768), Vector2i(640, 480)]:
		root.content_scale_size = dimensions
		root.size = dimensions
		await _frames(8)
		_check_geometry()
		for id in ["ship_0_0", "harbor_2", "pirate_0", "pilot_1", "insurance_0"]:
			await _click_slot(id)
			_check(panel.selected_id == id, "Small viewport missed %s at %s" % [id, dimensions])
		await _capture_seats("native_%d" % dimensions.x)
		panel.clear_selection()
	_check(state.owners.is_empty(), "Interaction checks committed preview data")
	_check([hud.coins, hud.remaining_crew, hud.holdings, _game._player_resources] == original_resources, "Checks unexpectedly mutated resources")
	root.content_scale_size = Vector2i(2048, 1152)
	root.size = Vector2i(1280, 720)
	await _frames(8)
	await _check_dispatch()
	await _finish()


func _snapshot() -> Array:
	var hud = _game.personal_bar
	return [_game.placement_panel.state.owners.duplicate(), _game._player_resources.duplicate(true),
		hud.coins, hud.remaining_crew, hud.holdings.duplicate(), _game.turn_bar.current_player_index,
		_game.turn_bar.phase, hud.stock_values.duplicate()]


func _prepare_dispatch() -> void:
	_controller.reset()
	_game.placement_panel.open()
	await _frames(2)


func _check_dispatch() -> void:
	var panel = _game.placement_panel
	var state = panel.state
	var turn = _game.turn_bar
	var hud = _game.personal_bar
	# Each target gets a fresh budget; only prerequisite seats use fixtures.
	for item in state.positions:
		await _prepare_dispatch()
		var actor = turn.players[0]
		var prerequisites := {}
		for other in state.positions:
			if item.ship >= 0 and other.group == item.group and other.cost < item.cost:
				prerequisites[other.id] = turn.players[2]
		if item.id == "pirate_1":
			prerequisites["pirate_0"] = turn.players[2]
		state.set_preview_occupants(prerequisites)
		var before := _snapshot()
		await _click_slot(item.id)
		_check(panel.detail.text.contains(actor.character_name), "Confirmation must identify actor")
		_check(not panel.confirm_button.disabled, "Legal target cannot confirm: " + item.id)
		_check_geometry()
		await _click_control(panel.cancel_button)
		_check(_snapshot() == before and panel.selected_id.is_empty(), "Cancel changed transaction: " + item.id)
		await _click_slot(item.id)
		await _click_control(panel.close_button)
		_check(_snapshot() == before, "Close changed transaction: " + item.id)
		await _click_control(panel.launcher)
		await _click_slot(item.id)
		var key: String = _game._placement_phase_key()
		await _click_control(panel.confirm_button)
		var expected_coins: int = 40 if item.id == "insurance_0" else 30 - item.cost
		var saved: Dictionary = _game._player_resources[actor.character_name_en]
		_check(saved.coins == expected_coins and saved.remaining == 2, "Wrong committed resources: " + item.id)
		_check(state.owners.get(item.id) == actor and state.owners.size() == prerequisites.size() + 1, "Wrong committed owner: " + item.id)
		_check(turn.current_player_index == 1 and hud.character_id == turn.players[1].character_name_en, "Confirmation did not switch full HUD")
		_check(hud.coins == 30 and hud.remaining_crew == 3 and not hud._stock_revealed.has(true), "Next HUD is stale or reveals cards")
		_check(not panel.shade.visible and panel.selected_id.is_empty() and panel.confirm_button.disabled, "Commit must close and clear")
		for ship in 3:
			var occupants: Array = state.ship_occupants(ship)
			_check(occupants.count(actor) == (1 if item.ship == ship else 0), "Wrong boat received crew: " + item.id)
		var committed := _snapshot()
		# A second real click, a repeated signal and an old request must all be inert.
		await _click_control(panel.confirm_button)
		panel.confirm_selection()
		_game._confirm_placement(item.id, actor, key)
		_check(_snapshot() == committed, "Duplicate commit changed state: " + item.id)
		turn.set_current_player(0)
		_check(hud.coins == expected_coins and hud.remaining_crew == 2, "Returning HUD lost committed resources")
		_check(hud.holdings == _controller.initial_resources[actor.character_name_en].holdings, "Dispatch changed holdings")
		_check(hud.stock_values == before[7], "Dispatch changed public prices")

	# Revalidate even when the UI has not yet observed a resource/state change.
	for failure in ["coins", "crew", "occupied", "arrived", "cheaper", "pirate"]:
		await _prepare_dispatch()
		var id := "ship_0_0"
		if failure == "cheaper":
			state.set_preview_occupants({"ship_0_0": turn.players[2]})
			id = "ship_0_1"
		elif failure == "pirate":
			state.set_preview_occupants({"pirate_0": turn.players[2]})
			id = "pirate_1"
		await _click_slot(id)
		match failure:
			"coins": hud.set_resources(0, 3)
			"crew": hud.set_resources(30, 0)
			"occupied": state.owners[id] = turn.players[1]
			"arrived": state.arrived[0] = true
			"cheaper": state.owners.erase("ship_0_0")
			"pirate": state.owners.erase("pirate_0")
		var before := _snapshot()
		await _click_control(panel.confirm_button)
		_check(_snapshot() == before, "Stale confirmation mutated data: " + failure)
		_check(panel.confirm_button.disabled and panel.detail.text.contains("未派遣"), "Failure reason missing: " + failure)
		if failure == "coins":
			await _capture_seats("dispatch_insufficient")
		await _click_control(panel.close_button)

	await _prepare_dispatch()
	hud.set_resources(0, 3)
	await _click_slot("pilot_1")
	_check(panel.confirm_button.disabled and panel.detail.text.contains("金币不足"), "Insufficient cash must disable confirmation")
	await _click_slot("insurance_0")
	_check(not panel.confirm_button.disabled, "Zero-cost insurance should accept zero cash")
	await _click_control(panel.confirm_button)
	_check(_game._player_resources[turn.players[0].character_name_en].coins == 10, "Insurance did not pay exactly ten")
	await _capture_seats("dispatch_insurance_result")
	await _prepare_dispatch()
	hud.set_resources(30, 0)
	await _click_slot("insurance_0")
	_check(panel.confirm_button.disabled and panel.detail.text.contains("没有"), "Insurance still needs a worker")
	var before := _snapshot()
	panel.confirm_selection()
	_check(_snapshot() == before, "No-crew insurance paid money")

	await _prepare_dispatch()
	await _click_slot("ship_0_0")
	state.set_ship_arrived(0, true)
	_check(panel.selected_id.is_empty() and panel.buttons.ship_0_0.disabled, "Arrival left a selectable ship")
	_check(panel.buttons.ship_0_0.tooltip_text.contains("到港"), "Arrival reason is missing")
	await _capture_seats("dispatch_arrived")

	for change in ["actor", "phase", "dice", "roster", "close", "cancel"]:
		await _prepare_dispatch()
		var actor = panel.actor
		var key: String = _game._placement_phase_key()
		await _click_slot("ship_0_0")
		match change:
			"actor": turn.set_current_player(1)
			"phase": turn.set_stage(turn.Phase.SAILING, 1, 1, 1)
			"dice": _game.inspect_dice()
			"roster": _game.open_character_roster()
			"close": panel.close()
			"cancel": panel.clear_selection()
		before = _snapshot()
		_game._confirm_placement("ship_0_0", actor, key)
		_check(_snapshot() == before, "Invalid context accepted confirmation: " + change)
		if change in ["dice", "roster"]:
			await _key(KEY_ESCAPE)

	# Two actual confirmations produce mixed crew, never a ghost on selection.
	await _prepare_dispatch()
	await _click_slot("ship_0_0")
	await _capture_seats("dispatch_confirmation")
	await _click_control(panel.confirm_button)
	await _capture_seats("dispatch_first_crew")
	await _click_control(panel.launcher)
	await _click_slot("ship_0_1")
	_check(state.ship_occupants(0) == [turn.players[0], null, null], "Unconfirmed choice shows ghost crew")
	await _click_control(panel.confirm_button)
	_check(state.ship_occupants(0) == [turn.players[0], turn.players[1], null], "Real mixed-crew placement failed")
	await _capture_seats("dispatch_mixed_scene")
	await _click_control(panel.launcher)
	await _capture_seats("dispatch_mixed_panel")

	# Skip players without workers. Someone who still has a worker cannot act twice this round.
	await _prepare_dispatch()
	_game._player_resources[turn.players[1].character_name_en].remaining = 0
	await _click_slot("harbor_0")
	await _click_control(panel.confirm_button)
	_check(turn.current_player_index == 2, "Depleted player was not skipped")
	await _prepare_dispatch()
	for card in turn.players:
		_game._player_resources[card.character_name_en].remaining = 0
	_game._player_resources[turn.players[0].character_name_en].remaining = 2
	hud.set_resources(30, 2)
	await _click_slot("harbor_0")
	await _click_control(panel.confirm_button)
	_check(_game._player_resources[turn.players[0].character_name_en].remaining == 1, "Only worker was not spent once")
	_check(_game._awaiting_sail and not _game.sail_button.disabled, "One legal placement did not end the round")
	_check(turn.phase == turn.Phase.DISPATCH, "Round completion invented a sailing phase")
	var placed: int = state.owners.size()
	await _click_control(panel.launcher)
	await _click_slot("harbor_1")
	await _click_control(panel.confirm_button)
	_check(not panel.shade.visible and state.owners.size() == placed, "Same player started a second placement")
	_check(_game._player_resources[turn.players[0].character_name_en].remaining == 1, "Second placement spent another worker")

	# Reset really restores resources and arrival flags, then small windows can commit.
	state.arrived[0] = true
	await _key(KEY_R)
	_check(state.owners.is_empty() and not state.arrived.has(true), "Reset retained board state")
	_check(_game._player_resources == _controller.initial_resources and hud.coins == 30 and hud.remaining_crew == 3, "Reset retained spent resources")
	for dimensions in [Vector2i(1280, 720), Vector2i(1024, 768), Vector2i(640, 480)]:
		root.content_scale_size = dimensions
		root.size = dimensions
		await _frames(8)
		await _prepare_dispatch()
		await _click_slot("insurance_0")
		_check_geometry()
		await _capture_seats("dispatch_native_%d" % dimensions.x)
		await _click_control(panel.confirm_button)
		_check(state.owners.get("insurance_0") == turn.players[0], "Small viewport confirmation missed")
	print("DISPATCH_CHECK all_positions=21 revalidation=passed reset=passed")


func _click_control(control: Control) -> void:
	await _frames(2)
	await _click(control.get_global_transform_with_canvas() * (control.size * 0.5))


func _click_slot(id: String) -> void:
	await _click_control(_game.placement_panel.buttons[id])


func _check_geometry() -> void:
	var panel = _game.placement_panel
	var sheet_rect: Rect2 = panel.sheet.get_global_rect()
	_check(root.get_visible_rect().encloses(sheet_rect), "Placement panel crosses viewport")
	_check(not sheet_rect.intersects(_game.turn_bar.get_global_rect()), "Panel overlaps phase strip")
	for id in panel.buttons:
		var button: Button = panel.buttons[id]
		_check(sheet_rect.encloses(button.get_global_rect()), "Position leaves panel: " + id)
		for other in panel.buttons:
			if other != id:
				_check(not button.get_global_rect().intersects(panel.buttons[other].get_global_rect()), "Position hit areas overlap")
	for control: Control in [panel.detail, panel.cancel_button, panel.confirm_button]:
		_check(sheet_rect.encloses(control.get_global_rect()), "Confirmation control leaves panel")
	_check(not panel.detail.get_global_rect().intersects(panel.cancel_button.get_global_rect()), "Detail overlaps cancel")
	_check(not panel.detail.get_global_rect().intersects(panel.confirm_button.get_global_rect()), "Detail overlaps confirm")
	_check(not panel.cancel_button.get_global_rect().intersects(panel.confirm_button.get_global_rect()), "Confirmation buttons overlap")
	for button: Button in [panel.cancel_button, panel.confirm_button]:
		_check(Pixel.FONT.get_string_size(button.text, HORIZONTAL_ALIGNMENT_LEFT, -1, 24).x + 8 <= button.size.x, "Confirmation caption is clipped")
	for child in panel.sheet.get_children():
		if child is Label and child.autowrap_mode == TextServer.AUTOWRAP_OFF:
			for line in child.text.split("\n"):
				var width := Pixel.FONT.get_string_size(line, HORIZONTAL_ALIGNMENT_LEFT, -1, child.get_theme_font_size("font_size")).x
				_check(width <= child.size.x, "Panel label clipped: " + line)


func _capture_seats(filename: String) -> void:
	if DisplayServer.get_name() == "headless":
		return
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	_check(image.save_png(SEAT_OUTPUT.path_join(filename + ".png")) == OK, "Could not save screenshot")
	if root.content_scale_size == Vector2i(2048, 1152):
		image.resize(1280, 720, Image.INTERPOLATE_BILINEAR)
		_check(image.save_png(SEAT_OUTPUT.path_join(filename + "_window.png")) == OK, "Could not save window screenshot")


func _tour() -> void:
	var panel = _game.placement_panel
	await create_timer(2).timeout
	await _click_slot("ship_0_0")
	await _click_control(panel.cancel_button)
	_check(panel.state.owners.is_empty(), "Tour cancellation placed crew")
	for id in ["ship_0_0", "ship_0_1", "harbor_1", "shipyard_2", "pirate_0"]:
		if not panel.shade.visible:
			await _click_control(panel.launcher)
		await _click_slot(id)
		_check(panel.selected_id == id and not panel.confirm_button.disabled, "Tour click missed " + id)
		await create_timer(0.8).timeout
		var actor = panel.actor
		await _click_control(panel.confirm_button)
		_check(panel.state.owners.get(id) == actor, "Tour confirmation failed " + id)
		await create_timer(1.3).timeout
	_check(_game._awaiting_sail and not _game.sail_button.disabled, "Tour did not wait for sailing")
	var tour_placed: int = panel.state.owners.size()
	await _click_control(panel.launcher)
	_check(not panel.shade.visible and panel.state.owners.size() == tour_placed, "Tour opened a second round")
	await _capture_seats("dispatch_tour_result")
	await _click_control(panel.launcher)
	await _capture_seats("dispatch_tour_board")
	await create_timer(2).timeout
	await _key(KEY_R)
	_check(panel.state.owners.is_empty() and _game.personal_bar.coins == 30, "Tour reset failed")
	await _key(KEY_A)
	_check(panel.buttons.ship_0_0.disabled, "Tour arrival did not lock ship")
	await create_timer(1).timeout
	await _key(KEY_R)
	await create_timer(1).timeout
	print("DISPATCH_TOUR completed")


func _timeout() -> void:
	push_error("PLACEMENT_CHECK timed out")
	quit(1)


func _finish() -> void:
	print("PLACEMENT_CHECK failures=%d output=%s" % [_failures.size(), ProjectSettings.globalize_path(SEAT_OUTPUT)])
	_game.queue_free()
	_controller.queue_free()
	await _frames(2)
	quit(0 if _failures.is_empty() else 1)
