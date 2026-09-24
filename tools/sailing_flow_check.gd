extends "res://tools/personal_bar_check.gd"

const SEAT_OUTPUT := "res://.godot/sailing_flow_check"
var _controller: Node


class FlowController extends Node:
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


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(SEAT_OUTPUT))
	root.title = "Manila - 派遣→投骰航行阶段流转"
	root.content_scale_size = Vector2i(2048, 1152)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.size = Vector2i(1280, 720)
	_game = load("res://scene/scene_bg.tscn").instantiate()
	root.add_child(_game)
	_controller = FlowController.new()
	_controller.game = _game
	root.add_child(_controller)
	await _frames(8)
	create_timer(80).timeout.connect(func(): push_error("SAILING_FLOW_CHECK timed out"); quit(1))

	await _check_five_player_rounds()
	await _check_arrival_persists()
	await _check_pirate_hold()
	await _check_pilot_hold()
	await _check_three_player_rounds()
	await _check_real_dice_round()

	print("SAILING_FLOW_CHECK failures=%d output=%s" % [_failures.size(), ProjectSettings.globalize_path(SEAT_OUTPUT)])
	for f in _failures:
		print("  - " + f)
	_game.queue_free()
	_controller.queue_free()
	await _frames(2)
	quit(0 if _failures.is_empty() else 1)


func _check_five_player_rounds() -> void:
	var turn = _game.turn_bar
	_check(turn.players.size() == 5 and turn.deployment_round == 1 and turn.sailing_number == 0, "Five-player round did not start clean")
	_check(_game.sail_button.disabled and not _game._awaiting_sail, "Sail was available before the round")
	for step in 4:
		_check(_place_next() != "", "Placement %d in round 1 failed" % (step + 1))
		_check(_game.sail_button.disabled, "Sail enabled before the round finished")
	_check(_place_next() != "", "Fifth placement failed")
	_check(_game._awaiting_sail and not _game.sail_button.disabled, "Completed round did not enable sailing")
	_check(turn.phase == turn.Phase.DISPATCH and turn.deployment_round == 1 and turn.sailing_number == 0, "Round completion changed phase counters")
	_check(turn.current_player_index == turn.harbor_master_index, "Harbor master does not roll after the round")
	_check(_game.placement_panel.result_notice.text.contains("请投骰航行"), "Round end did not ask for sailing")
	for card in turn.players:
		_check(_crew(card) == 2, "A player did not keep two workers after one placement")
	var first = turn.players[0]
	var crew_before := _crew(first)
	var purse_before := _purse()
	turn.set_current_player(0)
	_check(_place_next() == "", "Same player placed again before sailing")
	_check(_crew(first) == crew_before and _purse() == purse_before, "Rejected repeat placement changed resources")
	_game.resolve_sailing_now([1, 1, 1])
	_check(turn.phase == turn.Phase.DISPATCH and turn.deployment_round == 2 and turn.sailing_number == 1, "First sailing did not open round 2")
	_check(_routes() == [4, 4, 4], "First sailing did not advance from the fixed start: %s" % [_routes()])
	_check(turn.current_player_index == turn.harbor_master_index and not _game._awaiting_sail, "Round 2 did not start at the harbor master")
	var leader = turn.players[turn.current_player_index]
	var leader_before := _crew(leader)
	_check(_place_next() != "", "Harbor master could not place in round 2")
	_check(_crew(leader) == leader_before - 1, "Round 2 placement did not spend one worker")
	var resume: int = turn.current_player_index
	turn.set_current_player(turn.players.find(leader))
	_check(_place_next() == "", "Harbor master placed twice in round 2")
	_check(_crew(leader) == leader_before - 1, "Repeated round 2 placement spent another worker")
	turn.set_current_player(resume)
	for step in 4:
		_check(_place_next() != "", "Remaining round 2 placement %d failed" % (step + 1))
	_check(_game._awaiting_sail, "Round 2 did not end")
	_game.resolve_sailing_now([1, 1, 1])
	_check(_routes() == [5, 5, 5] and turn.deployment_round == 3 and turn.sailing_number == 2, "Second sailing reset or skipped a route")
	for step in 5:
		_check(_place_next() != "", "Round 3 placement %d failed" % (step + 1))
	var purse := _purse()
	_game.resolve_sailing_now([1, 1, 1])
	_check(_routes() == [6, 6, 6], "Third sailing did not continue from the current route")
	_check(turn.phase == turn.Phase.SETTLEMENT and turn.sailing_number == 3 and turn.deployment_round == 3, "Third sailing started another dispatch round")
	_check(_game._flow_hold == "settlement" and _game.sail_button.disabled, "Settlement boundary was not held")
	_check(_purse() == purse and _place_next() == "", "Settlement changed money or accepted another placement")


func _check_arrival_persists() -> void:
	_controller.reset()
	for step in 5:
		_check(_place_next() != "", "Arrival setup placement failed")
	_game.resolve_sailing_now([11, 1, 1])
	_check(_game.boats[0].arrived and _game.boats[0].route_position == 14, "Ship did not arrive by crossing 13")
	_check(_game.turn_bar.phase == _game.turn_bar.Phase.DISPATCH, "Arrival did not return to dispatch")
	_game.placement_panel.state.owners.erase("ship_0_0")
	_check(_game.placement_panel.state.arrived[0] and _game.placement_reason("ship_0_0").contains("到港"), "Arrived ship stayed open")
	for step in 5:
		_check(_place_next() != "", "Post-arrival placement failed")
	_check(_game._awaiting_sail, "Post-arrival round did not end")
	_game.resolve_sailing_now([1, 1, 1])
	_check(_game.boats[0].arrived and _game.boats[0].route_position == 14, "Later sailing reset an arrived ship")
	_check(_game.boats[1].route_position == 5 and _game.boats[2].route_position == 5, "Moving ships did not keep their route")


func _check_pirate_hold() -> void:
	_controller.reset()
	_check(_place_id("pirate_0"), "Pirate seat was rejected")
	for step in 4:
		_check(_place_next() != "", "Pirate-round placement failed")
	_game.resolve_sailing_now([1, 1, 1])
	_check(_game.turn_bar.phase == _game.turn_bar.Phase.DISPATCH and _game.turn_bar.sailing_number == 1, "A ship at 4 triggered pirate boarding")
	for step in 5:
		_check(_place_next() != "", "Second pirate-round placement failed")
	_game.resolve_sailing_now([9, 1, 1])
	_check(_game.boats[0].route_position == 13 and not _game.boats[0].arrived, "Pirate test ship did not stop on 13")
	_check(_game.turn_bar.phase == _game.turn_bar.Phase.PIRATES and _game._flow_hold == "boarding", "Pirate boarding was skipped")
	_check(_game.turn_bar.deployment_round == 2 and _game.turn_bar.sailing_number == 2, "Pirate hold advanced the dispatch round")
	_check(_game.sail_button.disabled and _place_next() == "", "Play continued during the unfinished pirate event")


func _check_pilot_hold() -> void:
	_controller.reset()
	_check(_place_id("pilot_0"), "Pilot seat was rejected")
	for step in 4:
		_check(_place_next() != "", "Pilot-round placement failed")
	_game.resolve_sailing_now([1, 1, 1])
	for step in 5:
		_check(_place_next() != "", "Middle pilot-round placement failed")
	_game.resolve_sailing_now([1, 1, 1])
	for step in 5:
		_check(_place_next() != "", "Final pilot-round placement failed")
	_check(_game.turn_bar.phase == _game.turn_bar.Phase.PILOTS and _game._flow_hold == "pilots", "Occupied pilot was skipped")
	_check(_game.turn_bar.sailing_number == 2 and _game.turn_bar.deployment_round == 3, "Pilot hold changed the voyage counters")
	_check(_game.sail_button.disabled and not _game._awaiting_sail, "Third sailing started before pilots")


func _check_three_player_rounds() -> void:
	_controller.reset()
	_game.turn_bar.set_players(_game.turn_bar.players.slice(0, 3))
	for card in _game.turn_bar.players:
		var data: Dictionary = _game._player_resources[card.character_name_en]
		data.remaining = 4
		data.capacity = 4
		data.coins = 30
		_game._player_resources[card.character_name_en] = data
	_game._displayed_character_id = ""
	_game.reset_voyage_flow()
	_game.turn_bar.harbor_master_index = 2
	_game.turn_bar.set_current_player(0)
	_game.turn_bar.set_stage(_game.turn_bar.Phase.DISPATCH, 1, 1, 0)
	for step in 3:
		_check(_place_next() != "", "Three-player first round failed")
	_check(_game.turn_bar.deployment_round == 2 and _game.turn_bar.sailing_number == 0 and not _game._awaiting_sail, "Three-player game sailed after one round")
	_check(_game.turn_bar.current_player_index == 2, "Second opening round did not start at the harbor master")
	for card in _game.turn_bar.players:
		_check(_crew(card) == 3, "Three-player crew was not four")
	for step in 3:
		_check(_place_next() != "", "Three-player second round failed")
	_check(_game._awaiting_sail and _game.turn_bar.deployment_round == 2, "Two opening rounds did not reach sailing")
	_game.resolve_sailing_now([1, 1, 1])
	_check(_game.turn_bar.deployment_round == 3 and _game.turn_bar.sailing_number == 1, "Three-player game did not open round 3")
	for step in 3:
		_check(_place_next() != "", "Three-player round 3 failed")
	_game.resolve_sailing_now([1, 1, 1])
	_check(_game.turn_bar.deployment_round == 4 and _game.turn_bar.sailing_number == 2, "Three-player game did not open the fourth round")
	for step in 3:
		_check(_place_next() != "", "Three-player round 4 failed")
	var purse := _purse()
	_game.resolve_sailing_now([1, 1, 1])
	_check(_game.turn_bar.phase == _game.turn_bar.Phase.SETTLEMENT and _game.turn_bar.sailing_number == 3 and _game.turn_bar.deployment_round == 4, "Three-player game did not stop after three sailings")
	_check(_purse() == purse and _place_next() == "", "Three-player settlement paid or continued dispatch")


func _check_real_dice_round() -> void:
	_controller.reset()
	for step in 5:
		_check(_place_next() != "", "Real-dice setup placement failed")
	_check(not _game.sail_button.disabled, "Real sailing button stayed disabled")
	_game.sail_button.pressed.emit()
	var waited := 0.0
	while not (_game.turn_bar.phase == _game.turn_bar.Phase.DISPATCH and _game.turn_bar.deployment_round == 2) and waited < 30.0:
		await create_timer(0.2).timeout
		waited += 0.2
	_check(_game.turn_bar.phase == _game.turn_bar.Phase.DISPATCH and _game.turn_bar.deployment_round == 2 and _game.turn_bar.sailing_number == 1, "Real dice sailing did not open the next round")
	for boat in _game.boats:
		_check(boat.route_position > 3 or boat.arrived, "Real dice did not move a ship")
	for card in _game.turn_bar.players:
		_check(_crew(card) == 2, "Real sailing consumed or restored workers")


func _place_next() -> String:
	for item in _game.placement_panel.state.positions:
		if _game.placement_reason(item.id).is_empty():
			return item.id if _place_id(item.id) else ""
	return ""


func _place_id(id: String) -> bool:
	var turn = _game.turn_bar
	var panel = _game.placement_panel
	if not _game.placement_reason(id).is_empty():
		return false
	var actor = turn.players[turn.current_player_index]
	var coins: int = int(_game._player_resources[actor.character_name_en].coins)
	var crew: int = int(_game._player_resources[actor.character_name_en].remaining)
	panel.open()
	panel.select(id)
	if panel.selected_id != id:
		return false
	panel.confirm_selection()
	if panel.state.owners.get(id) != actor:
		return false
	var saved: Dictionary = _game._player_resources[actor.character_name_en]
	var income := 10 if str(panel.state.get_position(id).group) == "insurance" else 0
	var cost := int(panel.state.get_position(id).cost)
	if int(saved.coins) != coins - cost + income or int(saved.remaining) != crew - 1:
		_failures.append("Placement resources mismatch for " + id)
		return false
	return true


func _crew(card) -> int:
	return int(_game._player_resources[card.character_name_en].remaining)


func _purse() -> int:
	var total := 0
	for card in _game.turn_bar.players:
		total += int(_game._player_resources[card.character_name_en].coins)
	return total


func _routes() -> Array:
	var values := []
	for boat in _game.boats:
		values.append(int(boat.route_position))
	return values
