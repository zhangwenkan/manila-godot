extends SceneTree
## Bounded integration test of the real demo Control, input routing and rules.
## Import first, then run: godot --headless --path . --script res://tools/harbor_pixel_demo_check.gd
## Optional rendered run: godot --path . --rendering-method gl_compatibility --script res://tools/harbor_pixel_demo_check.gd -- --preview
## --preview writes screenshots under .godot/harbor_pixel_demo_check and still exits.
## Require completed failures=0 sails=9 settlements=[1, 2, 3] exit=0 AND
## HARBOR_PIXEL_DEMO_CHECK_PASS scope=full. Exit 0 alone is never proof.
## --shipyard-only has a distinct scope marker and is not a full-suite pass.

const DEMO_SCENE := "res://demo/harbor_pixel/harbor_demo.tscn"
const OUTPUT := "res://.godot/harbor_pixel_demo_check"
const BASE := Vector2(1448, 1086)
const SEED := 20261013
const WATCHDOG_SECONDS := 150.0
# Independently measured baked lower-right blue die button; never the old helm.
const SAIL_RECT := Rect2(1324, 955, 110, 113)
# Measured background-worker landmarks, independent of production marker geometry.
const WORKER_INPUTS := [Vector2(1032, 559), Vector2(1226, 653), Vector2(1348, 558)]
const WORKER_FEET := [Vector2(1028, 597), Vector2(1226, 691), Vector2(1340, 592)]
const WORKER_HEADS := [Vector2(1032, 525), Vector2(1231, 613), Vector2(1356, 520)]
const WORKER_BODIES := [Rect2(1007, 525, 58, 74), Rect2(1199, 613, 54, 80), Rect2(1326, 520, 52, 76)]

var _demo
var _failures: Array[String] = []
var _assertions := 0
var _stage := "initialization"
var _started_ms := 0
var _done := false
var _preview := false
var _settlements: Array[int] = []
var _committed_rolls := 0
var _completed_suite := false
var _pointer_position := Vector2(-100, -100)


func _initialize() -> void:
	_started_ms = Time.get_ticks_msec()
	_preview = "--preview" in OS.get_cmdline_user_args()
	Engine.max_fps = 60
	call_deferred("_run")


func _process(_delta: float) -> bool:
	# Monotonic time also protects waits on process_frame/frame_post_draw.
	if not _done and Time.get_ticks_msec() - _started_ms >= int(WATCHDOG_SECONDS * 1000):
		_check(false, "150s watchdog expired during %s" % _stage)
		_finish(124)
	return false


func _run() -> void:
	# Never await a rendering signal with the dummy headless renderer.
	if _preview and DisplayServer.get_name() == "headless":
		_check(false, "--preview requires a real renderer; omit --headless")
		_finish()
		return
	root.title = "Harbor pixel integration check (bounded 150s)"
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	root.content_scale_size = Vector2i.ZERO
	root.size = Vector2i(1200, 900)
	root.gui_disable_input = false
	var packed = load(DEMO_SCENE)
	if not _check(packed is PackedScene, "Demo scene loads"):
		_finish()
		return
	_demo = packed.instantiate()
	root.add_child(_demo)
	_demo.dice_overlay.failed.connect(func(message, request):
		print("HARBOR_PIXEL_DICE_ABORT request=%d message=%s" % [request, message])
	)
	_demo.auto_ai = false
	_demo.game.reset(SEED)
	await _frames(5)
	if not _check(not _demo._hits.is_empty(), "Engine draw notifications populate actual hit regions"):
		_finish()
		return
	if "--shipyard-only" in OS.get_cmdline_user_args():
		await _test_shipyard_character()
		_finish()
		return
	await _test_scene_actions()
	if not await _test_setup_and_stock():
		_finish()
		return
	if not await _test_placement_and_ai():
		_finish()
		return
	if not await _test_pass_and_sail():
		_finish()
		return
	if not await _test_three_voyages():
		_finish()
		return
	if not await _test_restart_and_resize():
		_finish()
		return
	await _test_ai_authority()
	await _test_turn_art()
	await _test_character_art()
	await _test_placement_markers()
	await _test_shipyard_character()
	await _test_ground_light_art()
	await _test_stock_art()
	await _test_live_fan()
	if not await _test_reference_and_landmarks():
		_finish()
		return
	await _test_dice_recovery()
	_completed_suite = true
	_finish()


func _test_scene_actions() -> void:
	_stage = "scene actions without permanent hint panels"
	var game = _demo.game
	var reference: Image = _demo.BOARD.get_image().duplicate()
	reference.convert(Image.FORMAT_RGBA8)
	var patch: Image = _demo.FAN_PATCH.get_image().duplicate()
	patch.convert(Image.FORMAT_RGBA8)
	reference.blend_rect(patch, Rect2i(Vector2i.ZERO, patch.get_size()), Vector2i.ZERO)
	for dimensions in [Vector2i(1200, 900), Vector2i(1280, 720), Vector2i(720, 1000)]:
		root.size = dimensions
		game.reset(SEED)
		_demo._sync_setup()
		_demo.modal = ""
		_demo.selected = ""
		await _frames(5)
		_check(_demo.toast_time == 0 and _demo.modal.is_empty(), "No automatic rule prompt at startup")
		_check(not _demo.inspector_rect().has_area() and not _has_hit("inspect"), "No selection means no action card")
		_check(not _has_hit("setup") and not _has_hit("stocks"), "Removed setup/stocks shortcuts never return at startup")
		if not _win_auction(0):
			return
		if not await _click_id("stock_skip"):
			return
		_check(game.phase == "setup" and _demo._setup_step == "cargo", "Stock choice advances directly to cargo preparation")
		if not await _keyboard_activate("to_starts"):
			return
		_check(_demo._setup_step == "starts", "Phase-owned setup remains keyboard accessible")
		await _click_id("begin")
		_check(_demo.toast_time == 0, "Beginning dispatch does not repeat rules in a toast")
		_check(not _has_hit("pick:ginseng") and not _has_hit("start:0:1") and not _has_hit("begin"), "Preparation actions leave the scene after dispatch starts")
		await _check_rendered_reference(reference, [Rect2(24, 827, 380, 247), Rect2(1078, 951, 329, 121)])
		var before := _snapshot()
		for item in game.slots.positions:
			await _click_id("slot:" + item.id)
			var card: Rect2 = _demo.inspector_rect()
			_check(card.has_area() and card.size.x <= 248 and card.size.y <= 154, "Selected position has a compact temporary card")
			_check(Rect2(Vector2.ZERO, BASE).encloses(card), "Temporary card remains inside board")
			for other in game.slots.positions:
				_check(not card.intersects(_demo.placement_hit_rect(other.id)), "Temporary card does not cover a scene position: " + other.id)
			_check(_snapshot() == before, "Opening position card never spends cash or crew")
			await _click_id("cancel")
			_check(not _demo.inspector_rect().has_area() and _snapshot() == before, "Cancel removes the card without placing")
		await _click_id("slot:ship_0_0")
		_key(KEY_ESCAPE)
		await _frames()
		_check(not _has_hit("inspect") and _snapshot() == before, "Escape removes selection without placing")
		await _click_id("slot:ship_0_0")
		await _click_id("confirm")
		_check(game.slots.owners.get("ship_0_0") == 0 and not _demo.inspector_rect().has_area(), "Confirmed placement closes temporary card")
	game.reset(SEED)
	_demo._sync_setup()
	_demo.modal = ""
	_demo.selected = ""
	root.size = Vector2i(1200, 900)
	await _frames(5)
	print("HARBOR_PIXEL_DEMO_CHECK stage=scene_actions complete")


func _test_setup_and_stock() -> bool:
	_stage = "auction, permission gates, stock and atomic preparation drafts"
	var game = _demo.game
	_check(game.phase == "auction" and game.voyage == 1, "Initial model starts voyage one with an auction")
	_check(game.players.size() == 3 and game.slots.owners.is_empty(), "Three players start with no placements")
	_check(_visual_matches(), "Initial visual ship positions match model")
	_check_fresh_resources()
	_check_stock_view()
	await _capture("01_auction")
	var untouched := _snapshot()
	var draft_cargo: Array = _demo.setup_cargo.duplicate()
	var draft_starts: Array = _demo.setup_starts.duplicate()
	for id in ["setup", "stocks", "buy:jade", "stock_skip", "pick:nutmeg", "load:0", "to_starts", "start:0:1", "begin", "sail", "confirm", "pass_confirm"]:
		_demo._activate(id)
	_check(_snapshot() == untouched and _demo.setup_cargo == draft_cargo and _demo.setup_starts == draft_starts, "Out-of-phase UI IDs cannot mutate the auction or drafts")
	_check(not game.bid(game.auction_bid, 0) and not game.bid(game.players[0].cash + 1, 0) and not game.bid(1, 1), "Auction rejects non-increasing, unaffordable and wrong-actor bids")
	_check(not game.pass_bid(1) and not game.skip_stock(0) and not game.buy_stock("jade", 0) and not game.begin_voyage([], [], 0) and not game.roll([1, 2, 3], 0), "Wrong actor/phase cannot bypass the auction")
	_check(_snapshot() == untouched, "Rejected auction actions preserve all model state including RNG")
	await _click_id("bid_more")
	await _click_id("bid_less")
	_check(_demo._bid_amount == game.auction_bid + 1 and _snapshot() == untouched, "Bid adjustments are view-only and obey the minimum")
	var bid_point := _hit_center("bid")
	_click_board(bid_point)
	_check(_demo._hits.is_empty(), "Bid invalidates old hit regions synchronously")
	var bid_state := _snapshot()
	_click_board(bid_point)
	_demo._activate("bid_pass")
	_check(_snapshot() == bid_state and game.auction_leader == 0 and game.current_player != 0, "Duplicate bid and stale pass cannot act for the next bidder")
	if not _win_auction(0):
		return false
	await _frames()
	_check(game.harbormaster == 0 and game.phase == "stock" and game.players[0].cash == 29, "Winning auction pays the bid exactly once and enters stock")
	_check(not _has_hit("bid") and not _has_hit("setup") and not _has_hit("stocks"), "Auction controls disappear instead of reviving legacy entries")
	var stock_id: String = game.CARGO_IDS[0]
	var before_buy := _snapshot()
	_check(not game.skip_stock(1) and not game.buy_stock(stock_id, 1) and not game.begin_voyage([], [], 0), "Only elected master may buy/skip; preparation cannot skip stock")
	_check(_snapshot() == before_buy, "Rejected stock actions are atomic")
	var cost: int = maxi(5, game.prices[stock_id])
	var buy_point := _hit_center("buy:" + stock_id)
	_click_board(buy_point)
	_check(_demo._hits.is_empty(), "Stock transition clears its hit regions before the next draw")
	_click_board(buy_point)
	_demo._activate("buy:jade")
	await _frames()
	_check(game.phase == "setup" and _demo._setup_step == "cargo", "Successful purchase automatically enters cargo preparation")
	_check(game.players[0].cash == before_buy.players[0].cash - cost and game.players[0].holdings[stock_id] == before_buy.players[0].holdings[stock_id] + 1 and game.stock[stock_id] == before_buy.stock[stock_id] - 1, "Purchase charges and transfers exactly one share despite duplicate input")
	_check_stock_view()
	var bought := _snapshot()
	_check(not game.buy_stock("jade", 0) and not game.skip_stock(0), "Leaving stock prevents a second purchase or skip")
	_check(_snapshot() == bought and _visual_matches(), "Stock rejection leaves model and displayed ships unchanged")
	var original_cargo: Array = _demo.setup_cargo.duplicate()
	await _click_id("pick:" + str(original_cargo[1]))
	await _click_id("load:0")
	_check(_demo.setup_cargo[0] == original_cargo[1] and _demo.setup_cargo[1] == original_cargo[0], "Loading an existing cargo swaps its previous ship atomically")
	var omitted := ""
	for id in game.CARGO_IDS:
		if not _demo.setup_cargo.has(id):
			omitted = id
	await _click_id("pick:" + omitted)
	await _click_id("load:2")
	_check(_demo.setup_cargo[2] == omitted and _demo.setup_cargo.size() == 3, "Fourth cargo replaces one ship without duplicate selection")
	_check(_snapshot() == bought and _visual_matches(), "Cargo draft never changes official cargo, slots or ship positions")
	var cargo_draft: Array = _demo.setup_cargo.duplicate()
	_demo._activate("begin")
	_check(game.phase == "setup" and _snapshot() == bought, "Begin from cargo step cannot bypass start confirmation")
	await _click_id("to_starts")
	_check(not _has_hit("load:0") and not _has_hit("pick:ginseng"), "Start step removes cargo hit regions")
	await _click_id("start:0:1")
	_check(not _has_hit("begin"), "Invalid start total removes begin from keyboard and mouse targets")
	_demo._activate("begin")
	await _frames()
	_check(game.phase == "setup" and not _demo._setup_error.is_empty() and _snapshot() == bought, "Invalid start sum reports feedback without partial model commit")
	await _click_id("back_cargo")
	_check(_demo.setup_cargo == cargo_draft and _demo.setup_starts[0] == game.positions[0] + 1, "Back preserves both drafts without touching official state")
	await _click_id("to_starts")
	await _click_id("start:1:-1")
	var expected_cargo: Array = _demo.setup_cargo.duplicate()
	var expected_starts: Array = _demo.setup_starts.duplicate()
	for invalid in [[-1, 5, 5], [6, 1, 2], [1, 2, 3], [2.0, 3, 4], [true, 3, 5]]:
		_check(not game.begin_voyage(expected_cargo, invalid, 0) and _snapshot() == bought, "Invalid starts are rejected before any model change")
	_check(not game.begin_voyage(expected_cargo, expected_starts, 1) and _snapshot() == bought, "Non-master cannot commit another player's preparation")
	for invalid_cargo in [["jade", "jade", "silk"], ["jade", "silk"], ["jade", "silk", "unknown"]]:
		_check(not game.begin_voyage(invalid_cargo, expected_starts, 0) and _snapshot() == bought, "Invalid cargo cannot partially rebuild slots or commit starts")
	var draft_step: String = _demo._setup_step
	var stale_start_point := _hit_center("start:0:1")
	await _click_id("help")
	_demo._activate("begin")
	_click_board(stale_start_point)
	_key(KEY_SPACE)
	_check(_snapshot() == bought and _demo.setup_cargo == expected_cargo and _demo.setup_starts == expected_starts and _demo._setup_step == draft_step, "Help blocks stale setup actions while preserving both drafts")
	await _click_id("close")
	_key(KEY_TAB)
	_check(_demo._focus_index == 0, "Tab focuses first phase action")
	_key(KEY_TAB, false, true)
	_check(_demo._focus_index == _demo._hits.size() - 1, "Shift-Tab wraps backward through phase actions")
	if not await _keyboard_activate("begin"):
		return false
	_check(game.phase == "dispatch" and game.current_player == game.harbormaster and game.dispatch_round == 1, "Keyboard begin starts dispatch with the elected master")
	_check(_demo.modal.is_empty() and game.cargo == expected_cargo and game.positions == expected_starts, "Begin commits both preparation drafts together")
	_check(game.slots.ships == expected_cargo and _visual_matches(), "Committed cargo slots and visual positions agree")
	var started := _snapshot()
	_demo._activate("begin")
	_demo._activate("start:0:1")
	_check(_snapshot() == started and not _has_hit("begin"), "Stale setup actions cannot recommit or edit a live voyage")
	print("HARBOR_PIXEL_DEMO_CHECK stage=setup complete")
	return true


func _test_placement_and_ai() -> bool:
	_stage = "selection, modal isolation, confirmation and automatic AI"
	var game = _demo.game
	var initial := _snapshot()
	if not await _click_id("slot:ship_0_0"):
		return false
	_check(_demo.selected == "ship_0_0" and _snapshot() == initial, "Mouse selection is free and does not spend crew or cash")
	await _click_id("cancel")
	_check(_demo.selected.is_empty() and _snapshot() == initial, "Cancel clears selection without spending")
	await _click_id("slot:ship_0_0")
	_key(KEY_ESCAPE)
	await _frames()
	_check(_demo.selected.is_empty() and _snapshot() == initial, "Escape cancels selection without spending")
	await _click_id("slot:ship_0_0")
	var confirm_point := _hit_center("confirm")
	await _click_id("help")
	_check(_demo.modal == "help", "Help opens while a free selection exists")
	_check_modal_hits(["close"])
	_click_board(confirm_point)
	_click_board(_demo.slot_point("pirate_0"))
	_key(KEY_SPACE)
	await _frames()
	_check(_snapshot() == initial and _demo.selected.is_empty() and _demo.modal == "help", "Help clears selection and blocks background confirmation, slot clicks and Space")
	await _capture("02_help")
	_key(KEY_ESCAPE)
	await _frames()
	await _click_id("slot:ship_0_0")
	confirm_point = _hit_center("confirm")
	var before_cash: int = game.players[0].cash
	var before_crew: int = game.players[0].crew
	var placement_cost: int = game.slots.get_position("ship_0_0").cost
	# Two real press/release pairs before the next draw also exercise stale hits.
	_click_board(confirm_point)
	_click_board(confirm_point)
	_key(KEY_SPACE)
	await _frames()
	_check(game.players[0].cash == before_cash - placement_cost and game.players[0].crew == before_crew - 1, "Duplicate mouse confirmation spends once only")
	_check(game.slots.owners.get("ship_0_0", -1) == 0 and game.slots.owners.size() == 1 and game.current_player == 1, "One confirmed placement belongs to human and advances exactly one turn")
	_check(_demo.selected.is_empty(), "Successful confirmation clears selection")
	var ai_turn := _snapshot()
	_click_board(_demo.slot_point("ship_1_0"))
	_demo._activate("slot:ship_1_0")
	await _frames()
	_check(_demo.selected.is_empty() and not game.placement_reason("ship_1_0", 0).is_empty() and not _has_hit("confirm"), "AI turn rejects human selection and confirmation")
	_key(KEY_SPACE)
	await _frames()
	_check(_snapshot() == ai_turn, "Keyboard cannot place a human pawn during AI turn")
	await _capture("03_dispatch")
	await _click_id("help")
	_demo.auto_ai = true
	await create_timer(1.05, true, false, true).timeout
	_check(_snapshot() == ai_turn, "Open modal pauses automatic AI beyond its normal turn delay")
	_key(KEY_ESCAPE)
	var deadline := Time.get_ticks_msec() + 4000
	while game.phase == "dispatch" and game.current_player != 0 and Time.get_ticks_msec() < deadline:
		await process_frame
	_demo.auto_ai = false
	if not _check(game.phase == "dispatch" and game.current_player == 0 and game.dispatch_round == 2, "Real process ticks automatically execute both AI turns and return control"):
		return false
	_check(game.players[1].crew == 3 and game.players[2].crew == 3 and game.players[0].crew == 3, "Automatic AI takes one action per actor, without spending human crew")
	await _frames()
	print("HARBOR_PIXEL_DEMO_CHECK stage=placement_ai complete")
	return true


func _test_pass_and_sail() -> bool:
	_stage = "pass confirmation and one-shot sailing input"
	var game = _demo.game
	var before_pass := _snapshot()
	await _click_id("pass")
	_check(_demo.modal == "pass" and _snapshot() == before_pass, "Pass requests confirmation without committing")
	_check_modal_hits(["close", "pass_confirm"])
	_click_board(_demo.slot_point("pirate_0"))
	_key(KEY_SPACE)
	await _frames()
	_check(_snapshot() == before_pass and _demo.modal == "pass", "Pass confirmation isolates background mouse and Space")
	_key(KEY_ESCAPE)
	await _frames()
	_check(_snapshot() == before_pass and _demo.modal.is_empty(), "Escape cancels pass")
	await _click_id("pass")
	await _click_id("close")
	_check(_snapshot() == before_pass and _demo.modal.is_empty(), "Mouse Cancel cancels pass")
	await _click_id("pass")
	var confirm_point := _hit_center("pass_confirm")
	_click_board(confirm_point)
	_click_board(confirm_point)
	await _frames()
	_check(_demo.modal.is_empty() and game.players[0].crew == 3 and game.slots.owners.get("ship_0_0", -1) == 0, "Confirmed pass retains remaining crew and previously placed pawn")
	_check(game.current_player == 1 and not game.placement_reason("ship_0_1", 0).is_empty(), "Duplicate pass confirmation advances human only once")
	if not _advance_ai_to_sailing():
		return false
	await _frames()
	var before_roll := _snapshot()
	_check(not _demo.start_roll([0, 2, 3]), "Invalid forced dice are rejected by view's public roll method")
	_check(not _demo.busy and _snapshot() == before_roll and _visual_matches(), "Rejected roll leaves model and view unchanged")
	var old_positions: Array = game.positions.duplicate()
	var sail_point := SAIL_RECT.get_center()
	if not _check(_has_hit("sail"), "Sailing phase exposes real sail button"):
		return false
	_check(_hit_center("sail") == sail_point, "Sailing target centers on the independently measured lower-right blue die button")
	for hit in _demo._hits:
		if hit.id == "sail":
			_check(hit.rect == SAIL_RECT, "Sailing target uses the measured baked blue button footprint")
	var saved_window := root.size
	var board_image: Image = _demo.BOARD.get_image()
	for dimensions in [Vector2i(1200, 900), Vector2i(1280, 720), Vector2i(720, 1000)]:
		root.size = dimensions
		_move_board(Vector2(420, 800))
		await _frames(5)
		_check(_hit_center("sail") == sail_point, "Blue-button target survives all three independent letterbox transforms")
		await _check_rendered_reference(board_image, [SAIL_RECT.grow(-4)])
		_click_board(sail_point)
		_check(_demo.busy and _demo._roll_phase == "rolling" and _snapshot() == before_roll, "Independent blue-button click requests physical dice without committing at each size")
		_demo._on_dice_failed("bounded blue-button input fixture cancellation", _demo._roll_request)
		_demo.toast_time = 0
		_check(not _demo.busy and _snapshot() == before_roll, "Blue-button input fixture retires without consuming a sail")
	root.size = saved_window
	await _frames(5)
	_click_board(sail_point)
	_click_board(sail_point)
	_check(_demo.busy and _demo._roll_phase == "rolling" and _snapshot() == before_roll, "Mouse opens original tray without committing before settlement")
	_check(_demo.dice_overlay.close_button.disabled, "Physical throw disables close")
	_key(KEY_SPACE)
	_key(KEY_ESCAPE)
	_demo.finish_animation()
	await _frames()
	_check(_snapshot() == before_roll and _demo.busy, "Space/Escape/finish cannot cancel or commit a rolling die")
	_check(_demo._hits.is_empty(), "Fullscreen tray isolates all board hit targets")
	await _capture("04_sailing")
	if _preview:
		var deadline := Time.get_ticks_msec() + 27000
		var next_diagnostic := Time.get_ticks_msec()
		while _demo._roll_phase == "rolling" and Time.get_ticks_msec() < deadline:
			if Time.get_ticks_msec() >= next_diagnostic:
				next_diagnostic = Time.get_ticks_msec() + 5000
				for die in _demo.dice_overlay.stage._dice:
					print("HARBOR_PIXEL_DICE_STATE pos=%s linear=%s angular=%s sleeping=%s settled=%s" % [die.position, die.linear_velocity, die.angular_velocity, die.sleeping, die.has_settled()])
			await process_frame
		if not _check(_demo._roll_phase == "result", "Original physical dice settle within bounded timeout"):
			return false
	else:
		# Headless exercises the genuine mouse request, then explicitly aborts
		# before using the deterministic static-result fixture, never fake physics.
		_demo._on_dice_failed("test cancellation", _demo._roll_request)
		_check(_snapshot() == before_roll and not _demo.busy, "Precommit abort preserves all model state")
		_check(_demo.start_roll([2, 3, 4]), "Explicit forced fixture displays committed faces")
	# Freeze only the controller's result-hold timer while saving a screenshot;
	# GPU readback can exceed the 0.8s hold. Dice physics has already settled.
	_demo.set_process(false)
	_committed_rolls += 1
	_check(game.sail_count == 1, "Settlement commits exactly one sailing")
	for ship in 3:
		_check(game.positions[ship] == mini(14, old_positions[ship] + game.dice[ship]), "First sail model displacement equals its die on ship %d" % ship)
		_check(_demo.dice_overlay.stage.get_value(ship) == game.dice[ship], "Tray result equals model result")
		_check(_demo.dice_overlay.stage._dice[ship]._detect_top_face() == game.dice[ship], "Actual upward face equals committed result")
		_check(_demo.dice_overlay.stage._dice[ship].cargo_id == game.cargo[ship], "Tray cargo colors follow ship order")
	var committed := _snapshot()
	_demo._on_dice_results([6, 6, 6], _demo._roll_request)
	_check(_snapshot() == committed, "Duplicate settlement cannot reapply roll")
	_check(not _demo.start_roll([6, 6, 6]), "Busy presentation rejects another roll")
	_key(KEY_SPACE, true)
	_check(_demo._roll_phase == "result", "Echoed Space cannot dismiss result hold")
	await _capture("04_dice_result")
	_key(KEY_ESCAPE)
	await _frames()
	_check(_demo._roll_phase == "moving" and _demo.dice_overlay.state == "closed", "Result close hides tray before moving ships")
	_check(_demo.dice_overlay.stage.process_mode == Node.PROCESS_MODE_DISABLED and _demo.dice_overlay.stage._viewport.render_target_update_mode == SubViewport.UPDATE_DISABLED, "Hidden settled tray disables simulation and rendering")
	for die in _demo.dice_overlay.stage._dice:
		_check(die.freeze, "Hidden rigid body is frozen without changing its face")
	if not await _click_id("skip_animation"):
		_demo.set_process(true)
		return false
	_demo.set_process(true)
	_key(KEY_ESCAPE)
	_demo.finish_animation()
	_demo.finish_animation()
	await _frames()
	_check(not _demo.busy and _visual_matches() and _snapshot() == committed, "Mouse skip and repeated finish/Escape only synchronize visuals, never recommit")
	print("HARBOR_PIXEL_DEMO_CHECK stage=pass_sail complete")
	return true


func _test_three_voyages() -> bool:
	_stage = "bounded three-voyage public-API flow"
	var game = _demo.game
	# Never assign phase, counters, cash, ownership or settlement flags. Every
	# transition below goes through the same public API used by the view.
	for step in 96:
		if game.phase == "finished":
			break
		_stage = "three-voyage step %d phase=%s voyage=%d sails=%d" % [step, game.phase, game.voyage, game.sail_count]
		if _preview:
			print("HARBOR_PIXEL_FLOW %s elapsed_ms=%d" % [_stage, Time.get_ticks_msec() - _started_ms])
		match game.phase:
			"auction":
				_check(game.slots.owners.is_empty(), "Next voyage clears old placements before its auction")
				for player in game.players:
					_check(player.crew == 4, "Next voyage returns all crew before bidding")
				if not _win_auction(game.voyage - 1):
					return false
			"stock":
				if not _check(game.skip_stock(game.harbormaster), "Elected master resolves the next stock stage"):
					return false
			"setup":
				_check(_demo.setup_cargo == game.cargo and _demo.setup_starts == game.positions and _visual_matches(), "Entering setup resynchronizes both preparation drafts")
				if not _check(game.begin_voyage(_demo.setup_cargo, _demo.setup_starts, game.harbormaster), "Public begin_voyage starts next voyage for its elected master"):
					return false
			"dispatch":
				var progressed: bool = game.pass_turn(0) if game.current_player == 0 else game.ai_step()
				if not _check(progressed, "Public dispatch action advances step %d" % step):
					return false
			"sailing":
				var previous_count: int = game.sail_count
				var physical := false
				if _committed_rolls == 1:
					_key(KEY_SPACE, true)
					_check(not _demo.busy and game.sail_count == previous_count, "Held-key echo cannot initiate sailing")
					var pending := _snapshot()
					var cached_stage = _demo.dice_overlay.stage
					_key(KEY_SPACE)
					_check(_demo.busy and _snapshot() == pending, "Keyboard starts an uncommitted physical throw")
					_check(_demo.dice_overlay.stage == cached_stage, "Second physical throw reuses settled stage")
					for die in cached_stage._dice:
						_check(not die.freeze and die.is_rolling(), "Reopened tray unfreezes each die for a new throw")
					if _preview:
						physical = true
						var deadline := Time.get_ticks_msec() + 27000
						while _demo._roll_phase == "rolling" and Time.get_ticks_msec() < deadline:
							await process_frame
						if not _check(_demo._roll_phase == "result", "Reused original physical tray settles again"):
							return false
						for i in 3:
							_check(cached_stage._dice[i]._detect_top_face() == game.dice[i] and cached_stage.get_value(i) == game.dice[i], "Reused tray upward faces match second committed result")
					else:
						_demo._on_dice_failed("test cancellation", _demo._roll_request)
				if game.harbormaster != 0:
					var denied := _snapshot()
					_check(not _has_hit("sail") and not _demo.start_roll([6, 6, 6], 0) and not game.roll([6, 6, 6], 0), "AI master cannot be impersonated by human sail controls or public APIs")
					_key(KEY_SPACE)
					_demo._activate("sail")
					_check(not _demo.busy and _snapshot() == denied, "Human Space and stale sail ID cannot roll for an AI master")
				if not physical and not _check(_demo.start_roll([6, 6, 6], game.harbormaster), "Elected master's public start_roll accepts deterministic dice"):
					return false
				_committed_rolls += 1
				_check(_demo.busy and game.sail_count == previous_count + 1, "Each sailing transition increments once")
				var committed := _snapshot()
				_check(not _demo.start_roll([6, 6, 6]), "Duplicate sailing request is rejected while busy")
				if _committed_rolls == 2:
					_click_root(_demo.dice_overlay.close_button.get_global_rect().get_center())
					_check(_demo._roll_phase == "moving" and _demo.dice_overlay.state == "closed", "Mouse close button begins movement without recommitting")
				elif _committed_rolls == 3:
					# Exercise natural animation completion, not only test-driven skip.
					var deadline := Time.get_ticks_msec() + 3000
					while _demo.busy and Time.get_ticks_msec() < deadline:
						await process_frame
					if not _check(not _demo.busy, "Animation finishes automatically within three seconds"):
						return false
				else:
					_key(KEY_ESCAPE)
				_demo.finish_animation()
				_check(not _demo.busy and _visual_matches() and _snapshot() == committed, "Skipping/finishing animation preserves its single committed model result")
			"settlement":
				_check(game.sail_count == 3 and not _demo.busy and not game.settlement_lines.is_empty(), "Third sail exposes settlement before ranking/next voyage")
				_check(not _settlements.has(game.voyage), "Each voyage is settled once")
				_settlements.append(game.voyage)
				var settled := _snapshot()
				_check(not game.roll([6, 6, 6]) and not game.ai_step() and not game.pass_turn(0), "Settled voyage rejects further dice and dispatch")
				_check(_snapshot() == settled, "Settlement rejection cannot repeat payouts or market changes")
				await _capture("05_settlement_%d" % game.voyage)
				if not await _click_id("ledger"):
					return false
				_check(_demo.modal == "ledger", "Settlement opens complete ledger")
				_check_modal_hits(["close", "ledger_prev", "ledger_next"])
				var newest_page: int = _demo._ledger_page
				if not _check(newest_page > 0 and _has_hit("ledger_prev") and not _has_hit("ledger_next"), "Multi-page ledger opens at newest page with forward navigation disabled"):
					return false
				if not await _click_id("ledger_prev"):
					return false
				_check(_demo._ledger_page == newest_page - 1 and _has_hit("ledger_next"), "Mouse previous-page navigation exposes earlier records")
				if not await _click_id("ledger_next"):
					return false
				_check(_demo._ledger_page == newest_page and not _has_hit("ledger_next"), "Mouse next-page navigation returns to newest records without overflow")
				_key(KEY_SPACE)
				_check(_snapshot() == settled, "Ledger navigation and Space do not change settled model")
				_key(KEY_ESCAPE)
				await _frames()
				if not await _click_id("next"):
					return false
			_:
				_check(false, "Unexpected phase %s" % game.phase)
				return false
		await _frames()
	if not _check(game.phase == "finished", "Bounded public-API flow reaches final ranking"):
		return false
	_check(_settlements == [1, 2, 3] and _committed_rolls == 9 and game.voyage == 3, "Exactly three voyages and nine committed sails preceded ranking")
	_check(_has_hit("restart") and not _has_hit("sail") and not _has_hit("next"), "Finished result exposes restart rather than live sailing controls")
	var order: Array = game.ranking()
	_check(order.size() == 3 and order.has(0) and order.has(1) and order.has(2), "Ranking contains every player exactly once")
	for i in range(1, order.size()):
		_check(game.wealth(order[i - 1]) >= game.wealth(order[i]), "Ranking orders wealth descending")
	for actor in 3:
		var expected: int = game.players[actor].cash
		for id in game.CARGO_IDS:
			expected += game.players[actor].holdings[id] * game.prices[id]
		_check(game.wealth(actor) == expected, "Final wealth includes cash plus market-valued shares")
	await _capture("06_ranking")
	print("HARBOR_PIXEL_DEMO_CHECK stage=three_voyages complete sails=%d settlements=%s ranking=%s" % [_committed_rolls, _settlements, order])
	return true


func _test_restart_and_resize() -> bool:
	_stage = "restart confirmation and resized letterbox input"
	var game = _demo.game
	var finished := _snapshot()
	await _click_id("restart")
	_check(_demo.modal == "restart" and _snapshot() == finished, "Restart opens confirmation without resetting")
	_check_modal_hits(["close", "restart_confirm"])
	_key(KEY_SPACE)
	_click_board(_demo.slot_point("pirate_0"))
	_check(_snapshot() == finished and _demo.modal == "restart", "Restart modal isolates Space and background clicks")
	await _click_id("close")
	_check(_snapshot() == finished and _demo.modal.is_empty(), "Cancelling restart preserves completed game")
	await _click_id("restart")
	if not await _keyboard_activate("restart_confirm"):
		return false
	_check(game.phase == "auction" and game.voyage == 1 and game.sail_count == 0 and game.dispatch_round == 0, "Confirmed restart resets voyage and phase counters")
	_check(game.slots.owners.is_empty() and game.settlement_lines.is_empty() and _demo.modal.is_empty(), "Restart clears placements, settlement and modal")
	_check(_visual_matches() and game.auction_bid == 0 and game.auction_leader == -1, "Restart resets auction and rendered ships without committing a draft")
	_check_fresh_resources()
	# Re-seed only through the public reset API for reproducible preview hands.
	game.reset(SEED)
	await _frames()
	for dimensions in [Vector2i(1280, 720), Vector2i(720, 1000)]:
		root.size = dimensions
		await _frames(5)
		var zoom := minf(_demo.size.x / BASE.x, _demo.size.y / BASE.y)
		var origin: Vector2 = (_demo.size - BASE * zoom) * 0.5
		_check(_demo.size.is_equal_approx(Vector2(dimensions)), "Root resize reaches full-rect demo Control at %s" % dimensions)
		_check(is_equal_approx(_demo._zoom, zoom) and _demo._origin.is_equal_approx(origin), "View's letterbox transform matches independent aspect-fit calculation")
		_check(origin.x > 0 if dimensions.x > dimensions.y else origin.y > 0, "Resize produces expected horizontal/vertical letterboxing")
		var before := _snapshot()
		if not await _click_id("help"):
			return false
		_check(_demo.modal == "help", "Resized, transformed mouse hits the correct help button")
		var bar_point := Vector2(origin.x * 0.5, _demo.size.y * 0.5) if origin.x > 0 else Vector2(_demo.size.x * 0.5, origin.y * 0.5)
		_click_root(bar_point)
		_key(KEY_SPACE)
		await _frames()
		_check(_demo.modal == "help" and _snapshot() == before, "Letterbox margin click does not activate board or dismiss modal")
		await _click_id("close")
		await _click_id("bid_more")
		_check(_demo._bid_amount == game.auction_bid + 2 and _snapshot() == before, "Resized auction adjustment maps correctly without model mutation")
		await _click_id("bid_less")
		await _frames()
		await _capture("07_resized_%dx%d" % [dimensions.x, dimensions.y])
	print("HARBOR_PIXEL_DEMO_CHECK stage=restart_resize complete")
	return true


func _test_reference_and_landmarks() -> bool:
	_stage = "original pixels, lighthouse buildings and compact boat geometry"
	var reference := Image.new()
	var board := Image.new()
	_check(reference.load_png_from_buffer(FileAccess.get_file_as_bytes("res://demo/harbor_pixel/art/reference.png")) == OK, "Original reference PNG decodes")
	_check(board.load_png_from_buffer(FileAccess.get_file_as_bytes("res://demo/harbor_pixel/art/harbor_board.png")) == OK, "Generated board PNG decodes")
	_check(reference.get_size() == Vector2i(BASE) and board.get_size() == reference.get_size(), "Board preserves original reference dimensions")
	reference.convert(Image.FORMAT_RGB8)
	board.convert(Image.FORMAT_RGB8)
	_check(reference.get_data() == board.get_data(), "Board pixels exactly match reference; no repainted water or resampling")
	_check(FileAccess.get_sha256("res://demo/harbor_pixel/art/reference.png") == "0622f8944075b0882a19556a8b8c8a81a5d731c64662875e202abc9f200c3817", "Preserved original file fingerprint is unchanged")
	var workers_source := Image.new()
	var workers_board := Image.new()
	var source_path := "res://demo/harbor_pixel/art/harbor_workers_reference.png"
	var board_path := "res://demo/harbor_pixel/art/harbor_workers_board.png"
	_check(workers_source.load_png_from_buffer(FileAccess.get_file_as_bytes(source_path)) == OK, "Updated background-worker source decodes")
	_check(workers_board.load_png_from_buffer(FileAccess.get_file_as_bytes(board_path)) == OK, "Nearest-resampled background-worker board decodes")
	_check(workers_source.get_size() == Vector2i(1456, 1088) and workers_board.get_size() == Vector2i(BASE), "Updated source and active board retain their independent expected dimensions")
	_check(FileAccess.get_sha256(source_path) == "6ffb9719ef5a946c815606846579f9a8640d0400acd6a477f0b7617d91ecd17b", "Updated worker source fingerprint is unchanged")
	_check(FileAccess.get_sha256(board_path) == "de0d553813f777153295bd2e32ab22c7a09d13e7ec42ed6ecadb8a58af172914", "Active board matches the approved NEAREST derivative")
	_check(_demo.BOARD.resource_path == board_path and _demo.BOARD.get_size() == BASE, "Demo actively renders the updated worker board, not either retained original")
	reference = workers_board
	var game = _demo.game
	_demo.auto_ai = false
	game.reset(SEED)
	_check(_begin_fixture(["ginseng", "silk", "jade"], [0, 4, 5]), "Landmark fixture starts through public model API")
	root.size = Vector2i(1200, 900)
	await _frames(5)
	# Independent reference-image regions, not rectangles obtained from the view.
	# The former lower-sea rectangle included the baked fan tips at y899+.
	# Only that hand silhouette may change; open water above it remains untouched.
	var protected = [Rect2(438, 455, 122, 260), Rect2(860, 568, 140, 202), Rect2(565, 315, 30, 444), Rect2(863, 315, 26, 444), Rect2(530, 790, 360, 108)]
	var saved: Array = _demo.visual_positions.duplicate()
	for quarter in range(57):
		var progress := quarter / 4.0
		_demo.visual_positions = [progress, progress, progress]
		for ship in 3:
			var bounds: Rect2 = _demo.ship_bounds(ship)
			_check(bounds.size.x <= 64 and bounds.size.y <= 89, "Ship overlay stays compact at %.2f" % progress)
			for region in protected:
				_check(not bounds.intersects(region), "Ship %d avoids protected reference region at %.2f" % [ship, progress])
			for other in range(ship + 1, 3):
				_check(not bounds.intersects(_demo.ship_bounds(other)), "Different ship lanes do not overlap")
			var seat_hits: Array[Rect2] = []
			for item in game.slots.positions:
				if item.ship != ship:
					continue
				var hit: Rect2 = _demo.slot_rect(item.id).grow(2)
				_check(bounds.encloses(hit.grow(2)), "Seat hit and keyboard outline stay inside compact boat bounds")
				for previous in seat_hits:
					_check(not hit.intersects(previous), "Adjacent compact seats have disjoint hit regions")
				seat_hits.append(hit)
		if quarter in [0, 28, 56]:
			_demo.selected = ""
			_click_board(Vector2(420, 800))
			await _frames()
			await _capture("08_route_%02d" % int(progress))
			# Tight stepped tower bands, independently listed rather than whole input boxes.
			await _check_rendered_reference(reference, protected, [
				Rect2(514, 470, 14, 6), Rect2(506, 476, 30, 10), Rect2(499, 486, 44, 11), Rect2(507, 497, 30, 103), Rect2(501, 600, 44, 17),
				Rect2(915, 580, 14, 6), Rect2(908, 586, 29, 9), Rect2(902, 595, 41, 11), Rect2(910, 606, 25, 68), Rect2(904, 674, 38, 16)])
	_demo.visual_positions = saved
	await _frames()
	# Roof, lantern and base points from the local reference pixel masks. These
	# deliberately do not use PILOTS, slot_point() or _hits to choose a target.
	var towers = [
		{"id": "pilot_1", "cost": 5, "points": [Vector2(518, 489), Vector2(519, 513), Vector2(522, 592)]},
		{"id": "pilot_0", "cost": 2, "points": [Vector2(916, 598), Vector2(918, 617), Vector2(916, 670)]},
	]
	for dimensions in [Vector2i(1200, 900), Vector2i(1280, 720), Vector2i(720, 1000)]:
		root.size = dimensions
		await _frames(5)
		for tower in towers:
			game.reset(SEED)
			_check(_begin_fixture(["ginseng", "silk", "jade"], [0, 4, 5]), "Reset lighthouse input fixture through public API")
			await _frames()
			var initial := _snapshot()
			for point in tower.points:
				_click_board(point)
				await _frames()
				_check(_demo.selected == tower.id and _snapshot() == initial, "Independent roof/body/base click selects correct lighthouse for free at %s" % dimensions)
			await _keyboard_activate("slot:" + tower.id)
			_check(_demo.selected == tower.id and _snapshot() == initial, "Tab/Enter selects lighthouse without spending")
			if dimensions == Vector2i(1200, 900):
				await _capture("09_%s_selected" % tower.id)
			await _click_id("help")
			_click_board(tower.points[1])
			_key(KEY_SPACE)
			await _frames()
			_check(_demo.modal == "help" and _snapshot() == initial, "Modal isolates lighthouse and confirmation")
			_key(KEY_ESCAPE)
			await _frames()
			_click_board(tower.points[1])
			await _frames()
			var confirm := _hit_center("confirm")
			_click_board(confirm)
			_click_board(confirm)
			_key(KEY_SPACE)
			await _frames()
			_check(game.players[0].cash == initial.players[0].cash - tower.cost and game.players[0].crew == 3, "Lighthouse confirmation charges its 2/5 fee exactly once")
			_check(game.slots.owners.get(tower.id, -1) == 0 and game.current_player == 1, "Lighthouse pawn belongs to human; turn advances once")
			var placed := _snapshot()
			var other: Dictionary = towers[1] if tower.id == "pilot_1" else towers[0]
			_click_board(other.points[1])
			await _frames()
			_key(KEY_SPACE)
			_check(not _has_hit("confirm") and _snapshot() == placed, "Human cannot deploy to second lighthouse during AI turn")
			_key(KEY_ESCAPE)
			_click_board(Vector2(420, 800))
			await _frames()
			if dimensions == Vector2i(1200, 900):
				await _capture("10_%s_occupied" % tower.id)
			# A visible, independently positioned compact boat seat still works
			# under both letterbox transforms; its selection remains non-mutating.
			_click_board(Vector2(622, 737))
			await _frames()
			_check(_demo.selected.is_empty() and _snapshot() == placed, "Independent compact-seat click cannot select during the next actor's turn")
			_check(game.pass_turn(game.current_player) and game.pass_turn(game.current_player), "Public pass actions return the landmark fixture to the human")
			await _frames()
			var human_turn := _snapshot()
			_click_board(Vector2(622, 737))
			await _frames()
			_check(_demo.selected == "ship_0_0" and _snapshot() == human_turn, "Independent compact-seat click survives resized transform on the human turn")
	game.reset(SEED)
	_check(_begin_fixture(["ginseng", "silk", "jade"], [0, 4, 5]), "Start busy-state fixture")
	for _step in 18:
		if game.phase != "dispatch":
			break
		_check(game.pass_turn(game.current_player), "Pass all players through public API")
	_check(_demo.start_roll([1, 1, 1]), "Start animation for lighthouse input isolation")
	await _frames()
	var rolling := _snapshot()
	_click_board(Vector2(518, 513))
	await _frames()
	_check(not _has_hit("slot:pilot_1") and _snapshot() == rolling, "Sailing animation removes lighthouse hit targets")
	_key(KEY_ESCAPE)
	_check(_demo._roll_phase == "moving" and _demo.dice_overlay.state == "closed", "Escape leaves dice result for ship movement")
	_key(KEY_ESCAPE)
	_check(not _demo.busy and _visual_matches(), "Second Escape completes landmark movement without reroll")
	print("HARBOR_PIXEL_DEMO_CHECK stage=reference_landmarks complete")
	return true


func _test_dice_recovery() -> void:
	_stage = "dice timeout, stale callbacks, resize and action-card content"
	var game = _demo.game
	_demo.auto_ai = false
	game.reset(SEED)
	_check(_begin_fixture(["ginseng", "silk", "jade"], [0, 4, 5]), "Recovery fixture starts")
	for item in game.slots.positions:
		_check(_demo.FONT.get_string_size(item.title, HORIZONTAL_ALIGNMENT_LEFT, -1, 20).x <= 224, "Position title fits compact confirmation card")
	for _step in 18:
		if game.phase != "dispatch":
			break
		game.pass_turn(game.current_player)
	await _frames()
	var initial := _snapshot()
	for invalid in [[0, 2, 3], [1, 7, 3], [1, 2], [1.0, 2, 3], [true, 2, 3]]:
		_check(not _demo.start_roll(invalid) and _snapshot() == initial and not _demo.busy, "Invalid forced input rejected before opening tray")
	_check(_demo.start_roll(), "Begin timeout fixture with original physics")
	var retired: int = _demo._roll_request
	_demo.dice_overlay._started_ms = Time.get_ticks_msec() - _demo.dice_overlay.TIMEOUT_MS - 1
	await _frames()
	_check(not _demo.busy and _snapshot() == initial and _demo.dice_overlay.stage == null, "Timeout destroys physics world and preserves uncommitted game")
	_check(_demo.start_roll(), "Retry creates fresh original tray")
	_demo._on_dice_results([6, 6, 6], retired)
	_check(_demo._roll_phase == "rolling" and _snapshot() == initial, "Old request cannot settle a new throw")
	_demo.dice_overlay._on_settled([1, 2, 7], _demo._roll_request)
	_check(not _demo.busy and _snapshot() == initial, "Invalid natural result aborts without a fallback roll")
	_check(_demo.start_roll(), "Begin live-resize fixture")
	root.size += Vector2i(24, 16)
	await _frames(5)
	_check(not _demo.busy and _snapshot() == initial, "Resize during physical throw aborts safely before commitment")
	_check(_demo.start_roll(), "Begin reset fixture")
	retired = _demo._roll_request
	game.reset(SEED)
	var reset := _snapshot()
	_demo._on_dice_results([6, 6, 6], retired)
	_check(not _demo.busy and _snapshot() == reset and _demo.dice_overlay.state == "closed", "Model reset invalidates old dice world and callbacks")
	root.size = Vector2i(1200, 900)
	await _frames(5)
	await _capture("11_action_idle")
	_check(_begin_fixture(["ginseng", "silk", "jade"], [0, 4, 5]), "Final action-card fixture starts")
	await _frames()
	_click_board(Vector2(518, 513))
	await _frames()
	await _capture("12_action_selected")
	for hit in _demo._hits:
		if hit.id in ["confirm", "cancel", "pass"]:
			_check(not hit.rect.intersects(Rect2(530, 790, 360, 135)), "Action button does not invade lower sea")
	print("HARBOR_PIXEL_DEMO_CHECK stage=dice_recovery complete")


func _check_rendered_reference(reference: Image, regions: Array, overlays: Array = []) -> void:
	if not _preview:
		return
	await RenderingServer.frame_post_draw
	var actual: Image = root.get_texture().get_image()
	var zoom := minf(_demo.size.x / BASE.x, _demo.size.y / BASE.y)
	var origin: Vector2 = (_demo.size - BASE * zoom) * 0.5
	# Render the independent original through the same GPU, avoiding color-space
	# and nearest-sampling differences from comparing raw PNG to framebuffer.
	var baseline := TextureRect.new()
	baseline.texture = ImageTexture.create_from_image(reference)
	baseline.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	baseline.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	baseline.mouse_filter = Control.MOUSE_FILTER_IGNORE
	baseline.position = origin
	baseline.size = BASE * zoom
	root.add_child(baseline)
	await _frames()
	await RenderingServer.frame_post_draw
	var expected: Image = root.get_texture().get_image()
	baseline.queue_free()
	await _frames()
	for region in regions:
		var start: Vector2 = origin + region.position * zoom
		var end: Vector2 = origin + region.end * zoom
		var changed := 0
		var sampled := 0
		for y in range(ceili(start.y) + 2, floori(end.y) - 2):
			for x in range(ceili(start.x) + 2, floori(end.x) - 2):
				var covered := false
				for overlay in overlays:
					if overlay.has_point((Vector2(x, y) + Vector2(0.5, 0.5) - origin) / zoom):
						covered = true
				if covered:
					continue
				sampled += 1
				if actual.get_pixel(x, y) != expected.get_pixel(x, y):
					changed += 1
		_check(sampled > 0, "Protected region has actual framebuffer samples at this window size")
		_check(changed == 0, "Rendered original-art region %s has %d overpainted pixels" % [region, changed])
		print("HARBOR_PIXEL_PROTECTED_REGION rect=%s sampled=%d changed_pixels=%d" % [region, sampled, changed])


func _win_auction(winner: int) -> bool:
	# Exercise the real election without assigning phase, master, cash or actor.
	var game = _demo.game
	for _step in 12:
		if game.phase != "auction":
			break
		var actor: int = game.current_player
		var progressed: bool = game.bid(game.auction_bid + 1, actor) if actor == winner else game.pass_bid(actor)
		if not _check(progressed, "Public auction fixture advances actor %d" % actor):
			return false
	return _check(game.phase == "stock" and game.harbormaster == winner and game.current_player == winner, "Bounded auction elects requested fixture master")


func _begin_fixture(cargo_ids: Array, starts: Array, actor: int = 0) -> bool:
	var game = _demo.game
	if game.phase == "auction" and not _win_auction(actor):
		return false
	if game.phase == "stock" and not _check(game.skip_stock(actor), "Public fixture skips optional stock purchase"):
		return false
	return game.begin_voyage(cargo_ids, starts, actor)


func _advance_ai_to_sailing() -> bool:
	for _step in 12:
		if _demo.game.phase != "dispatch":
			break
		if not _check(_demo.game.current_player != 0, "Confirmed human pass skips remaining human turns"):
			return false
		if not _check(_demo.game.ai_step(), "Public AI action progresses remaining dispatch"):
			return false
	return _check(_demo.game.phase == "sailing", "Bounded AI progression reaches sailing")


func _check_stock_view() -> void:
	var game = _demo.game
	var expected: Array[String] = []
	for id in game.CARGO_IDS:
		for _copy in int(game.players[0].holdings[id]):
			expected.append(id)
		var disc: Dictionary = _demo.stock_marker(id)
		var column: int = {"nutmeg": 0, "silk": 1, "ginseng": 2, "jade": 3}[id]
		var row: int = [0, 5, 10, 20, 30].find(game.prices[id])
		_check(disc.price == game.prices[id] and disc.column == column and disc.row == row, "Market exposes public prices in four independent five-step lanes")
		_check(disc.position.is_equal_approx(Vector3(-3.35 + row * 1.88, 0.045, -3.35 + column * 2.25)), "Market marker matches its horizontal tabletop track and price position")
		var purchase: Dictionary = _demo.purchase_row(id)
		_check(purchase.cost == maxi(5, game.prices[id]) and purchase.supply == game.stock[id], "Separate purchase data distinguishes cost and bank supply from value")
		var available: bool = game.phase == "stock" and game.harbormaster == 0 and not game._bought_stock and game.stock[id] > 0 and game.players[0].cash >= maxi(5, game.prices[id]) and not _demo.busy and _demo.modal.is_empty()
		_check(purchase.available == available, "Purchase availability follows elected master, stock phase, one-buy limit, supply and cash")
		_check(_demo.FONT.get_string_size(purchase.action, HORIZONTAL_ALIGNMENT_LEFT, -1, 21).x <= 182, "Purchase action fits its independent phase button")
		if game.phase != "stock" or game.harbormaster != 0 or not _demo.modal.is_empty():
			_check(not _has_hit("buy:" + id), "No purchase target exists outside the human master's stock step")
	if _demo.modal.is_empty() and game.phase not in ["auction", "stock", "setup"]:
		for hit in _demo._hits:
			# The timber worker's hit bounds cross the sign's bounding rectangle;
			# only that placement target is allowed, never stock/share actions.
			_check(not hit.rect.intersects(Rect2(1008, 646, 232, 244)) or hit.id == "slot:shipyard_1", "Only the background timber-worker target may overlap the former board footprint")
	var hand = _demo.stock_hand
	_check(hand.cargo_ids == expected and hand.cards.size() == expected.size(), "Fan contains one actual card per held share, including duplicates")
	for i in expected.size():
		_check(hand._faces[i].texture == hand.FACES[expected[i]], "Held cargo is visible face-up without a text substitute")
		_check(hand.cards[i].mouse_filter == Control.MOUSE_FILTER_IGNORE and hand.cards[i].focus_mode == Control.FOCUS_NONE, "Display-only fan does not steal board mouse or keyboard input")


func _check_turn_status() -> void:
	var game = _demo.game
	var data: Dictionary = _demo.turn_status()
	_check(data.title == "TURN %d / %d" % [game.voyage, game.max_voyages], "Top TURN follows real voyage and configured limit")
	var expected := ""
	if _demo.busy:
		var sail: int = game.sail_count + (1 if _demo._roll_phase == "rolling" else 0)
		var motion: String = {"rolling": "等待落定", "result": "骰子已落定", "moving": "船队前进"}[_demo._roll_phase]
		expected = "航行 %d/3 · %s" % [sail, motion]
	elif game.phase == "auction":
		expected = "竞拍 · %s" % game.players[game.current_player].name
	elif game.phase == "stock":
		expected = "买股 · %s" % game.players[game.harbormaster].name
	elif game.phase == "setup":
		expected = ("装货" if _demo._setup_step == "cargo" else "起点 · 合计 9") + " · " + game.players[game.harbormaster].name
	elif game.phase == "dispatch":
		expected = "派遣 %d/4 · %s" % [game.dispatch_round, game.players[game.current_player].name]
	elif game.phase == "sailing":
		expected = "投骰 %d/3 · %s" % [game.sail_count + 1, game.players[game.harbormaster].name]
	elif game.phase == "settlement":
		expected = "航行 3/3 · 收益结算"
	elif game.phase == "finished":
		expected = "航程结束 · 最终排名"
	_check(data.detail == expected, "Top TURN follows phase, actor and visual sailing lifecycle without precommit advancement")
	for field in ["title", "detail"]:
		var font_size: int = _demo.TurnBoard.font_size(data[field], 23 if field == "title" else 14)
		_check(_demo.FONT.get_string_size(data[field], HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x <= 214, "TURN text fits the original compact plaque")
	for hit in _demo._hits:
		_check(not hit.rect.intersects(Rect2(604, 0, 236, 56)), "TURN plaque is display-only and cannot cover an input target")


func _test_ai_authority() -> void:
	_stage = "AI master permissions and normal animated scheduling"
	var game = _demo.game
	game.reset(SEED)
	await _frames()
	await _click_id("bid_pass")
	_check(game.auction_passed[0] and game.current_player != 0, "Human pass button retires only the human bidder")
	if not _win_auction(1):
		return
	await _frames()
	var before := _snapshot()
	var cargo_draft: Array = _demo.setup_cargo.duplicate()
	var start_draft: Array = _demo.setup_starts.duplicate()
	for id in ["stock_skip", "buy:jade", "pick:nutmeg", "load:0", "to_starts", "start:0:1", "begin", "sail"]:
		_demo._activate(id)
	_check(not game.buy_stock("jade", 0) and not game.skip_stock(0) and not game.begin_voyage([], [], 0), "Human APIs cannot control the AI master's stock or setup")
	_check(_snapshot() == before and _demo.setup_cargo == cargo_draft and _demo.setup_starts == start_draft, "AI-owned stage rejects human mutations including drafts")
	_demo.auto_ai = true
	var deadline := Time.get_ticks_msec() + 2500
	while game.phase == "stock" and Time.get_ticks_msec() < deadline:
		await process_frame
	_demo.auto_ai = false
	if not _check(game.phase == "setup", "Normal process scheduling resolves the AI master's stock choice"):
		return
	before = _snapshot()
	cargo_draft = _demo.setup_cargo.duplicate()
	start_draft = _demo.setup_starts.duplicate()
	for id in ["pick:nutmeg", "load:0", "to_starts", "start:0:1", "begin", "back_cargo"]:
		_demo._activate(id)
	_check(_snapshot() == before and _demo.setup_cargo == cargo_draft and _demo.setup_starts == start_draft and not game.begin_voyage([], [], 0), "Human cannot mutate or commit the AI master's preparation draft")
	_demo.auto_ai = true
	deadline = Time.get_ticks_msec() + 2500
	while game.phase == "setup" and Time.get_ticks_msec() < deadline:
		await process_frame
	_demo.auto_ai = false
	if not _check(game.phase == "dispatch" and game.harbormaster == 1 and game.current_player == 1, "Normal process scheduling resolves AI setup then starts at elected master"):
		return
	for _step in 6:
		if game.phase != "dispatch":
			break
		_check(game.pass_turn(game.current_player), "Public fixture passes each actor without changing election")
	await _frames()
	if not _check(game.phase == "sailing" and game.current_player == 1, "Sailing belongs to the AI master after dispatch"):
		return
	before = _snapshot()
	_check(not _has_hit("sail") and not _demo.start_roll([1, 2, 3], 0) and not game.roll([1, 2, 3], 0), "Human has no sail target or roll authority for AI master")
	_key(KEY_SPACE)
	_demo._activate("sail")
	_check(_snapshot() == before and not _demo.busy, "Human keyboard and stale sail cannot advance AI voyage")
	_demo.auto_ai = true
	deadline = Time.get_ticks_msec() + 2000
	while not _demo.busy and Time.get_ticks_msec() < deadline:
		await process_frame
	_demo.auto_ai = false
	if not _check(_demo.busy and _demo._roll_phase == "rolling" and _demo.dice_overlay.state == "rolling", "Normal AI schedule opens the same physical dice animation as human sailing"):
		return
	_check(_snapshot() == before, "AI scheduling never precommits a pending physical throw")
	_demo._on_dice_failed("bounded AI scheduling fixture cancellation", _demo._roll_request)
	_check(_snapshot() == before and not _demo.busy, "Cancelling the pending AI fixture preserves model state")
	_check(_demo.start_roll([1, 2, 3], 1), "AI master can use explicit deterministic presentation fixture")
	_check(_demo._roll_phase == "result" and game.sail_count == before.sails + 1, "AI result presentation commits one roll through the shared path")
	_demo.finish_animation()
	_demo.finish_animation()
	_check(not _demo.busy and _visual_matches(), "AI presentation finishes into synchronized ship positions")
	# Separate auction-scheduler fixture: do not use ai_step() directly here.
	game.reset(SEED)
	await _frames()
	await _click_id("bid_pass")
	_demo.auto_ai = true
	deadline = Time.get_ticks_msec() + 18000
	while game.phase == "auction" and Time.get_ticks_msec() < deadline:
		await process_frame
	_demo.auto_ai = false
	_check(game.phase == "stock" and game.harbormaster > 0, "Normal AI scheduling completes bidding after human withdrawal within 18 seconds")
	game.reset(SEED)
	await _frames()
	print("HARBOR_PIXEL_DEMO_CHECK stage=ai_authority complete")


func _test_turn_art() -> void:
	_stage = "reference TURN sign and removal of old progress panel"
	var fixture := {"voyage": 2, "max_voyages": 7, "phase": "dispatch", "dispatch_round": 4,
		"sail_count": 2, "current_player": 1, "players": [{"name": "你"}, {"name": "林船长"}, {"name": "陈掌柜"}]}
	var status: Dictionary = _demo.TurnBoard.status(fixture, false, "idle")
	_check(status == {"title": "TURN 2 / 7", "detail": "派遣 4/4 · 林船长"}, "TURN uses voyage, not individual actor or dispatch round, and no hardcoded total")
	for round_index in range(1, 5):
		fixture.dispatch_round = round_index
		for actor in 3:
			fixture.current_player = actor
			status = _demo.TurnBoard.status(fixture, false, "idle")
			_check(status.detail == "派遣 %d/4 · %s" % [round_index, fixture.players[actor].name], "All four dispatch rounds and three actor names fit the sign")
	fixture.phase = "settlement"
	fixture.sail_count = 3
	_check(_demo.TurnBoard.status(fixture, true, "result").detail == "航行 3/3 · 骰子已落定", "Committed final sail does not expose settlement before dice presentation finishes")
	_check(_demo.TurnBoard.status(fixture, true, "moving").detail == "航行 3/3 · 船队前进", "Committed final sail remains moving until animation finishes")
	_check(_demo.TurnBoard.status(fixture, false, "idle").detail == "航行 3/3 · 收益结算", "Settlement appears after visuals finish")
	fixture.phase = "sailing"
	fixture.sail_count = 0
	_check(_demo.TurnBoard.status(fixture, true, "rolling").detail == "航行 1/3 · 等待落定" and fixture.sail_count == 0, "Pending dice presentation does not mutate committed progress")
	var reference := Image.new()
	_check(reference.load_png_from_buffer(FileAccess.get_file_as_bytes("res://demo/harbor_pixel/art/harbor_workers_board.png")) == OK, "TURN active-board baseline decodes")
	var game = _demo.game
	for dimensions in [Vector2i(1200, 900), Vector2i(1280, 720), Vector2i(720, 1000)]:
		game.reset(SEED)
		_check(_begin_fixture(["ginseng", "silk", "jade"], [0, 4, 5]), "Visual counters fixture reaches dispatch through public preparation")
		for _actor in 3:
			_check(game.pass_turn(game.current_player), "Visual counters fixture enters idle sailing without placement effects")
		_demo.toast_time = 0
		root.size = dimensions
		await _frames(5)
		var initial := _snapshot()
		_click_board(Vector2(722, 28))
		_click_board(Vector2(530, 86))
		await _frames()
		_check(_snapshot() == initial and _demo.modal.is_empty(), "New TURN sign and former status area are read-only at every aspect ratio")
		# These independently specified regions used to be covered by the old teal HUD.
		await _check_rendered_reference(reference, [Rect2(501, 23, 95, 89), Rect2(848, 23, 106, 89), Rect2(501, 62, 453, 50)])
		await _capture("19_turn_%dx%d" % [dimensions.x, dimensions.y])
		var before: Image
		if _preview:
			await RenderingServer.frame_post_draw
			before = root.get_texture().get_image()
		game.voyage = 2
		game.changed.emit()
		await _frames()
		_check(_demo.turn_status().title == "TURN 2 / 3", "TURN number updates, replacing the baked TURN 1")
		if _preview:
			await RenderingServer.frame_post_draw
			var after: Image = root.get_texture().get_image()
			var zoom := minf(_demo.size.x / BASE.x, _demo.size.y / BASE.y)
			var origin: Vector2 = (_demo.size - BASE * zoom) * 0.5
			var inside := 0
			var outside := 0
			for y in after.get_height():
				for x in after.get_width():
					if before.get_pixel(x, y) != after.get_pixel(x, y):
						if Rect2(604, 0, 236, 56).has_point((Vector2(x, y) - origin) / zoom):
							inside += 1
						else:
							outside += 1
			_check(inside > 0 and outside == 0, "Changing voyage redraws TURN only, not any legacy counter")
			print("HARBOR_PIXEL_TURN_VALUES size=%s inside=%d outside=%d" % [dimensions, inside, outside])
		game.voyage = 3
		game.changed.emit()
		await _frames()
		_check(_demo.turn_status().title == "TURN 3 / 3", "TURN progresses through the final voyage")
	game.reset(SEED)
	await _frames()
	_check(_demo.turn_status().title == "TURN 1 / 3", "Restart resets top TURN to one")
	print("HARBOR_PIXEL_DEMO_CHECK stage=turn_art complete")


func _check_character_status() -> void:
	var data: Dictionary = _demo.character_status()
	_check(data.cash == str(_demo.game.players[0].cash) and data.crew == str(_demo.game.players[0].crew), "Portrait resources remain bound to human cash and available crew throughout gameplay")
	var character: Dictionary = _demo.CharacterStatus.CHARACTERS[_demo.character_id]
	_check(data.name == character.name and data.portrait == character.portrait and _demo.game.players[0].name == character.name, "Chosen character name and avatar remain bound to human player zero")
	_check(data.harbormaster == (_demo.game.harbormaster == 0), "Portrait master insignia reflects the auction result, not the current actor")
	for hit in _demo._hits:
		_check(not hit.rect.intersects(Rect2(11, 10, 261, 104)), "Character status is read-only and does not cover any input target")


func _test_character_art() -> void:
	_stage = "reference character status and removal of old resource panel"
	var fixture := {"current_player": 0, "harbormaster": 1, "players": [{"cash": 30, "crew": 4}, {"cash": 19, "crew": 2}, {"cash": 8, "crew": 1}]}
	for actor in 3:
		fixture.current_player = actor
		for id in _demo.CharacterStatus.CHARACTERS:
			var info: Dictionary = _demo.CharacterStatus.status(fixture, id)
			var character: Dictionary = _demo.CharacterStatus.CHARACTERS[id]
			_check(info.cash == "30" and info.crew == "4" and info.name == character.name and info.portrait == character.portrait and not info.harbormaster, "Changing actor never changes the selected human character or resources")
	for amount in [0, 5, 30, 999, 1020, 99999]:
		var value := str(amount)
		var font_size: int = _demo.CharacterStatus.font_size(value, 91)
		_check(_demo.FONT.get_string_size(value, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x <= 91, "Cash digits fit the original long plaque without abbreviating the value")
	for crew in range(5):
		var value := str(crew)
		var font_size: int = _demo.CharacterStatus.font_size(value, 29)
		_check(_demo.FONT.get_string_size(value, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x <= 29, "Available crew including zero fits the short plaque")
	var reference := Image.new()
	_check(reference.load_png_from_buffer(FileAccess.get_file_as_bytes("res://demo/harbor_pixel/art/harbor_workers_board.png")) == OK, "Character active-board baseline decodes")
	var game = _demo.game
	for dimensions in [Vector2i(1200, 900), Vector2i(1280, 720), Vector2i(720, 1000)]:
		game.reset(SEED)
		_check(_begin_fixture(["ginseng", "silk", "jade"], [0, 4, 5]), "Visual counters fixture reaches dispatch through public preparation")
		for _actor in 3:
			_check(game.pass_turn(game.current_player), "Visual counters fixture enters idle sailing without placement effects")
		_demo.toast_time = 0
		root.size = dimensions
		await _frames(5)
		var initial := _snapshot()
		for point in [Vector2(63, 62), Vector2(185, 40), Vector2(185, 85), Vector2(330, 90)]:
			_click_board(point)
		await _frames()
		_check(_snapshot() == initial and _demo.modal.is_empty(), "Portrait, both plaques and former HUD space have no click side effects")
		# Independent exposed regions of the old (24,22)-(389,134) teal panel.
		await _check_rendered_reference(reference, [Rect2(280, 23, 108, 110), Rect2(24, 118, 251, 16), Rect2(218, 71, 54, 40)])
		await _capture("20_character_%dx%d" % [dimensions.x, dimensions.y])
		var before: Image
		if _preview:
			await RenderingServer.frame_post_draw
			before = root.get_texture().get_image()
		game.players[0].cash = 7
		game.players[0].crew = 0
		game.changed.emit()
		await _frames()
		_check(_demo.character_status().cash == "7" and _demo.character_status().crew == "0", "Both live counters replace the original baked numbers, including zero crew")
		if _preview:
			await RenderingServer.frame_post_draw
			var after: Image = root.get_texture().get_image()
			var zoom := minf(_demo.size.x / BASE.x, _demo.size.y / BASE.y)
			var origin: Vector2 = (_demo.size - BASE * zoom) * 0.5
			var cash_changed := 0
			var crew_changed := 0
			var outside := 0
			for y in after.get_height():
				for x in after.get_width():
					if before.get_pixel(x, y) == after.get_pixel(x, y):
						continue
					var point := (Vector2(x, y) - origin) / zoom
					if Rect2(166, 24, 98, 34).has_point(point):
						cash_changed += 1
					elif Rect2(166, 69, 36, 34).has_point(point):
						crew_changed += 1
					else:
						outside += 1
			_check(cash_changed > 0 and crew_changed > 0 and outside == 0, "Changing human cash and crew redraws only both new numeric fields, never the legacy resource bar")
			print("HARBOR_PIXEL_CHARACTER_VALUES size=%s cash=%d crew=%d outside=%d" % [dimensions, cash_changed, crew_changed, outside])
		game.players[0].cash = 1020
		game.players[0].crew = 4
		game.changed.emit()
		await _frames()
		_check(_demo.character_status().cash == "1020", "Multi-digit cash remains live data, not a baked artwork value")
	game.reset(SEED)
	await _frames()
	_check(_demo.character_status().cash == "30" and _demo.character_status().crew == "4", "Restart restores both compact counters")
	print("HARBOR_PIXEL_DEMO_CHECK stage=character_art complete")


func _test_placement_markers() -> void:
	_stage = "scene highlights, contextual pawn previews and placement input"
	var game = _demo.game
	_demo.auto_ai = false
	var shore_ids := ["harbor_0", "harbor_1", "harbor_2", "shipyard_0", "shipyard_1", "shipyard_2", "pirate_0", "pirate_1", "pilot_0", "pilot_1", "insurance_0"]
	var costs := {"ginseng": [1, 2, 3], "nutmeg": [2, 3, 4], "silk": [3, 4, 5], "jade": [3, 4, 5, 5]}
	# Fixed world sites, independent of slot_point() and marker geometry.
	var shore_ground := {"harbor_0": Vector2(564, 231), "harbor_1": Vector2(622, 231), "harbor_2": Vector2(680, 231),
		"shipyard_0": Vector2(1028, 597), "shipyard_1": Vector2(1226, 691), "shipyard_2": Vector2(1340, 592),
		"pirate_0": Vector2(162, 583), "pirate_1": Vector2(220, 583), "insurance_0": Vector2(1170, 437),
		"pilot_1": Vector2(522, 617), "pilot_0": Vector2(923, 690)}
	for omitted in game.CARGO_IDS:
		var cargo: Array = []
		for id in game.CARGO_IDS:
			if id != omitted:
				cargo.append(id)
		game.reset(SEED)
		_demo.selected = ""
		_demo._mouse = Vector2(-100, -100)
		_demo._focus_index = -1
		_check(_begin_fixture(cargo, [0, 4, 5]), "Every three-of-four cargo combination starts")
		_demo.toast_time = 0
		await _frames()
		var expected_total := 21 if cargo.has("jade") else 20
		_check(game.slots.positions.size() == expected_total, "All boat seats and eleven shore positions exist for this cargo combination")
		var legal := 0
		var seen: Dictionary = {}
		for hit in _demo._hits:
			if hit.id.begins_with("slot:"):
				seen[hit.id.trim_prefix("slot:")] = int(seen.get(hit.id.trim_prefix("slot:"), 0)) + 1
		_check(seen.size() == expected_total, "Every catalog position has a real hit region")
		for item in game.slots.positions:
			_check(seen.get(item.id, 0) == 1, "Each position is registered exactly once")
			var data: Dictionary = _demo.placement_marker(item.id)
			_check(data.label == "$%d" % item.cost, "Marker explicitly prefixes the placement fee with a dollar sign")
			_check(not data.occupied and data.available == game.placement_reason(item.id, 0).is_empty(), "Only legal empty positions receive subtle default light")
			_check(not data.preview and data.show_price == (item.id.begins_with("shipyard_") and data.available), "Idle shipyard fees are visible; other sites keep contextual prices")
			legal += 1 if data.available else 0
			if item.ship >= 0:
				var seat: int = int(item.id.get_slice("_", 2))
				_check(item.cost == costs[cargo[item.ship]][seat], "Cargo price labels match the seat catalog")
				_check(_demo.ship_bounds(item.ship).encloses(data.pawn) and _demo.ship_bounds(item.ship).encloses(data.price), "Pawn preview and price stay within compact boat bounds")
				for point in data.shape:
					_check(_demo.ship_bounds(item.ship).has_point(point), "Deck highlight moves inside its own compact ship")
			_check(data.input_rect == _demo.slot_rect(item.id), "Visual geometry never replaces the existing input rectangle")
			_check(not data.pawn.intersects(data.price), "Contextual price does not cover the preview pawn")
			_check(data.ring_rect.has_area() == item.id.begins_with("shipyard_"), "Only shipyard sites receive ground-ring geometry")
		_check(legal == 13, "Fresh human dispatch has thirteen legal choices; other seats remain inspectable")
		for id in shore_ids:
			_check(seen.has(id), "All eleven original shore positions are presented, including both pilots")
			_check(_demo.placement_marker(id).feet == shore_ground[id], "Pawn feet are anchored to their fixed building entrance or shore site")
		_check(_demo.placement_marker("insurance_0").label == "$0", "Insurance fee is zero, distinct from its ten-peso payment")
		var initial := _snapshot()
		for item in game.slots.positions:
			_click_board(_demo.slot_point(item.id))
			await _frames(1)
			_check(_demo.selected == item.id and _snapshot() == initial, "Legal and illegal position markers can be inspected without spending")
	game.reset(SEED)
	_begin_fixture(["ginseng", "silk", "jade"], [0, 4, 5])
	game.slots.owners["ship_2_0"] = 1
	game.slots.owners["ship_2_1"] = 2
	_check(_demo.placement_marker("ship_2_2").available and _demo.placement_marker("ship_2_3").available, "Both equal-price jade seats invite placement after cheaper seats fill")
	_check(not _demo.placement_marker("pirate_1").available, "Second pirate is unavailable before captain placement")
	game.slots.owners["pirate_0"] = 1
	_check(_demo.placement_marker("pirate_1").available, "Second pirate becomes available after captain placement")
	_demo.selected = "ship_2_0"
	_check(_demo.placement_marker("ship_2_0").occupied and not _demo.placement_marker("ship_2_0").preview, "Occupied positions show only their owner's solid pawn")
	_demo.selected = "harbor_0"
	game.players[0].cash = 0
	_check(not _demo.placement_marker("harbor_0").preview and _demo.placement_marker("harbor_0").show_price, "Unaffordable site can be inspected but never offers a ghost pawn")
	game.players[0].cash = 30
	game.players[0].crew = 0
	_check(not _demo.placement_marker("harbor_0").preview, "No available crew means no preview")
	game.players[0].crew = 4
	game.slots.arrived[0] = true
	_check(not _demo.placement_marker("ship_0_0").available, "Arrived ships do not invite boarding")
	game.slots.arrived[0] = false
	game.current_player = 1
	_check(not _demo.placement_marker("harbor_0").preview, "Human cannot preview placement during AI turns")
	game.current_player = 0
	_demo.busy = true
	_check(not _demo.placement_marker("harbor_0").active and not _demo.placement_marker("harbor_0").show_price, "Busy sailing suppresses selected-site effects")
	_demo.busy = false
	_demo.modal = "help"
	_check(not _demo.placement_marker("harbor_0").active and not _demo.placement_marker("harbor_0").show_price, "Modal suppresses selected-site effects")
	_demo.modal = ""
	for dimensions in [Vector2i(1200, 900), Vector2i(1280, 720), Vector2i(720, 1000)]:
		game.reset(SEED)
		_begin_fixture(["ginseng", "silk", "jade"], [0, 4, 5])
		_demo.toast_time = 0
		_demo.selected = ""
		_demo._focus_index = -1
		root.size = dimensions
		await _frames(5)
		_move_board(Vector2(420, 800))
		await _frames()
		_demo.set_process(false)
		_demo._time = 0.0
		_demo.queue_redraw()
		await _frames()
		await _capture("23_scene_idle_%dx%d" % [dimensions.x, dimensions.y])
		var before: Image
		if _preview:
			await RenderingServer.frame_post_draw
			before = root.get_texture().get_image()
		var hit_before: Array = _demo._hits.duplicate(true)
		var initial := _snapshot()
		_demo._time = 1.25
		_demo.queue_redraw()
		await _frames()
		if _preview:
			await RenderingServer.frame_post_draw
			_check_ring_pixels(before, root.get_texture().get_image())
		_demo._time = 0.0
		_demo.queue_redraw()
		await _frames()
		# Motion only: the user has not clicked or spent anything.
		for target in [{"id": "pilot_1", "point": Vector2(518, 513)}, {"id": "harbor_0", "point": Vector2(564, 218)}, {"id": "ship_0_0", "point": Vector2(622, 737)}]:
			_move_board(target.point)
			_demo.queue_redraw()
			await _frames()
			var data: Dictionary = _demo.placement_marker(target.id)
			_check(data.preview and data.show_price and _demo.selected.is_empty(), "Hover alone shows one contextual pawn and fee without selecting")
			_check(_snapshot() == initial and _demo._hits == hit_before, "Hover never spends or changes targets")
			var previews := 0
			for item in game.slots.positions:
				previews += 1 if _demo.placement_marker(item.id).preview else 0
			_check(previews == 1, "Only one hovered slot shows a ghost")
			await _capture("23_scene_hover_%s_%dx%d" % [target.id, dimensions.x, dimensions.y])
			if _preview:
				await RenderingServer.frame_post_draw
				_check_preview_pixels(before, root.get_texture().get_image(), data)
			_move_board(Vector2(420, 800))
			_demo.queue_redraw()
			await _frames()
			_check(not _demo.placement_marker(target.id).preview, "Moving away removes the unselected ghost")
			if _preview:
				await RenderingServer.frame_post_draw
				_check(before.get_data() == root.get_texture().get_image().get_data(), "Leaving hover exactly restores the idle scene (mouse=%s focus=%s selected=%s)" % [_demo._mouse, _demo._focus_slot, _demo.selected])
		# Real click persists after the pointer moves; Escape cancels it.
		_click_board(Vector2(518, 513))
		_move_board(Vector2(564, 218))
		_demo.queue_redraw()
		await _frames()
		_check(_demo.placement_marker("pilot_1").preview and not _demo.placement_marker("harbor_0").preview, "Selected site retains its preview without creating a second hovered ghost")
		_check(_snapshot() == initial, "Selection does not spend")
		_key(KEY_ESCAPE)
		_move_board(Vector2(420, 800))
		_demo.queue_redraw()
		await _frames()
		_check(not _demo.placement_marker("pilot_1").preview, "Cancel clears selected preview")
		# Keep the mouse on a different site to verify keyboard precedence.
		_move_board(Vector2(564, 218))
		for _step in _demo._hits.size() + 1:
			_key(KEY_TAB)
			if _demo._hits[_demo._focus_index].id == "slot:pilot_0":
				break
		var focus_before: int = _demo._focus_index
		var mouse_before: Vector2 = _demo._mouse
		# Godot can refresh hover after a layout change without real movement.
		var refresh := InputEventMouseMotion.new()
		refresh.position = Vector2(680, 656)
		refresh.global_position = refresh.position
		root.push_input(refresh, true)
		_check(_demo._focus_index == focus_before and _demo._mouse == mouse_before, "Stationary hover refresh preserves keyboard focus and last actual motion")
		_move_board(Vector2(565, 218))
		_check(_demo._focus_index == -1 and _demo._focus_slot.is_empty(), "Actual pointer movement returns control from keyboard to mouse")
		for _step in _demo._hits.size() + 1:
			_key(KEY_TAB)
			if _demo._hits[_demo._focus_index].id == "slot:pilot_0":
				break
		_demo.queue_redraw()
		await _frames()
		_check(_demo.placement_marker("pilot_0").preview and not _demo.placement_marker("harbor_0").preview, "Keyboard focus replaces stale mouse hover (mouse=%s focus=%s index=%d selected=%s)" % [_demo._mouse, _demo._focus_slot, _demo._focus_index, _demo.selected])
		_key(KEY_ENTER)
		_demo.queue_redraw()
		await _frames()
		_check(_demo.selected == "pilot_0" and _snapshot() == initial, "Enter selects focused building without spending")
		await _capture("23_scene_selected_%dx%d" % [dimensions.x, dimensions.y])
		await _click_id("confirm")
		_check(game.players[0].cash == initial.players[0].cash - 2 and game.players[0].crew == 3, "Confirmation charges the two-peso pilot once")
		var occupied: Dictionary = _demo.placement_marker("pilot_0")
		_check(occupied.occupied and not occupied.preview and not occupied.show_price and occupied.color == game.players[0].color, "Confirmed ghost becomes the human player's solid pawn")
		var committed := _snapshot()
		_key(KEY_SPACE)
		await _frames()
		_check(_snapshot() == committed, "Repeated confirmation cannot duplicate placement")
		await _capture("23_scene_occupied_%dx%d" % [dimensions.x, dimensions.y])
		_demo.set_process(true)
	game.reset(SEED)
	await _frames()
	print("HARBOR_PIXEL_DEMO_CHECK stage=placement_markers complete")


func _test_shipyard_character() -> void:
	_stage = "background shipyard workers, foot rings and dispatch"
	var game = _demo.game
	var reference := Image.new()
	_check(reference.load_png_from_buffer(FileAccess.get_file_as_bytes("res://demo/harbor_pixel/art/harbor_workers_board.png")) == OK, "Shipyard background-worker baseline decodes")
	_check(_demo.BOARD.resource_path == "res://demo/harbor_pixel/art/harbor_workers_board.png", "Shipyard workers come from the active background board")
	game.reset(SEED)
	_begin_fixture(["ginseng", "silk", "jade"], [0, 4, 5])
	for item in game.slots.positions:
		var data: Dictionary = _demo.placement_marker(item.id)
		_check(data.shipyard == item.id.begins_with("shipyard_"), "Only the three repair jobs identify as background-worker sites")
		_check(not data.has("texture"), "Placement data does not introduce an Izezia or other pawn texture")
		_check(data.ring_visible == item.id.begins_with("shipyard_"), "Only legal shipyard sites receive rotating swirls")
	_check(_demo.slot_point("insurance_0") == Vector2(1170, 424), "Insurance belongs to the upper red-crane building")
	_check(not _demo.placement_marker("insurance_0").shipyard, "Insurance remains distinct from the worker sites around the wooden repair shed")
	var upper_bodies: Array[Rect2] = []
	for index in 3:
		var id := "shipyard_%d" % index
		var data: Dictionary = _demo.placement_marker(id)
		var input := Rect2(WORKER_INPUTS[index] - Vector2(22, 19), Vector2(44, 38))
		var ring := Rect2(WORKER_FEET[index] + Vector2(-28, -17), Vector2(56, 40))
		var price := Rect2(WORKER_HEADS[index] + Vector2(-15, -30), Vector2(30, 22))
		var expected_hit: Rect2 = input.grow(5).merge(WORKER_BODIES[index]).merge(ring.grow(1)).merge(price.grow(1))
		_check(_demo.slot_point(id) == WORKER_INPUTS[index] and data.input_rect == input, "Worker input remains a fixed 44-by-38 target at its independent center")
		_check(data.feet == WORKER_FEET[index] and data.pawn == WORKER_BODIES[index], "Hammer, timber and workbench jobs use their existing background workers' feet and body bounds")
		_check(data.price == price and data.ring_rect == ring, "Fee sits above the existing worker's head and the swirl surrounds its feet")
		_check(_demo.placement_hit_rect(id) == expected_hit, "Worker hit merges input padding, body, ring padding and overhead fee padding exactly")
		_check(not data.pawn.intersects(Rect2(1068, 472, 244, 48)) and not data.pawn.intersects(data.price), "Background worker clears the relocated repair title, its four/six-pixel shadow and the fee")
		# The timber worker crosses the SHARES bounding box, not its opaque grid;
		# protect the actual upper-body pixels below instead of excluding that box.
		_check(Rect2(Vector2.ZERO, BASE).encloses(data.pawn), "Every existing worker body stays on the board")
		_check(_demo.placement_hit_rect(id).has_point(data.pawn.get_center()), "The visible background worker center is a real placement target")
		_check(data.ring_visible and data.show_price and data.label == "$%d" % (4 - index), "Legal idle shipyard sites show their four/three/two-peso overhead fees without hover")
		_check(_demo.placement_hit_rect(id).encloses(data.price), "Permanent fee labels are also clickable placement targets")
		_check(_demo.placement_hit_rect(id).encloses(data.ring_rect), "The entire visible ground ring is clickable")
		_check(not data.ring_rect.intersects(data.price) and Rect2(Vector2.ZERO, BASE).encloses(data.ring_rect), "Ground ring clears price and board edges")
		upper_bodies.append(Rect2(WORKER_BODIES[index].position, Vector2(WORKER_BODIES[index].size.x, WORKER_FEET[index].y - 18 - WORKER_BODIES[index].position.y)))
		for other in 3:
			if index != other:
				_check(not data.pawn.intersects(_demo.placement_marker("shipyard_%d" % other).pawn), "Neighboring background workers do not overlap")
				var neighbor: Dictionary = _demo.placement_marker("shipyard_%d" % other)
				_check(not data.ring_rect.intersects(neighbor.ring_rect) and not data.price.intersects(neighbor.price) and not data.price.intersects(neighbor.pawn) and not data.price.intersects(neighbor.ring_rect), "Swirls and overhead prices stay clear of neighboring artwork")
				_check(not _demo.placement_hit_rect(id).intersects(_demo.placement_hit_rect("shipyard_%d" % other)), "Ground rings have separate non-overlapping click targets")
	game.players[0].cash = 0
	_check(not _demo.placement_marker("shipyard_0").ring_visible, "Unaffordable jobs do not invite placement")
	game.players[0].cash = 30
	game.players[0].crew = 0
	_check(not _demo.placement_marker("shipyard_0").ring_visible, "No crew means no placement invitation")
	game.players[0].crew = 4
	game.current_player = 1
	_check(not _demo.placement_marker("shipyard_0").ring_visible, "AI turns do not display human placement invitations")
	game.current_player = 0
	var marker = _demo.PlacementMarker
	_check(is_zero_approx(marker.swirl_phase(0.0)) and is_equal_approx(marker.swirl_phase(0.9), PI * 0.5), "The swirl advances a quarter-turn in 0.9 seconds")
	_check(is_equal_approx(marker.swirl_phase(0.37), marker.swirl_phase(3.97)), "Rotation repeats every 3.6 seconds without moving the hit target")
	var head := Vector2(cos(-0.12) * 0.69 * 25.0, sin(-0.12) * 0.69 * 17.0)
	var turned := Vector2(-head.y / 17.0 * 25.0, head.x / 25.0 * 17.0)
	_check(marker.swirl_pixel(head, 0.0, false).a > 0.65 and marker.swirl_pixel(head, PI * 0.5, false).a < 0.10, "Bright head leaves its former position, not just changing whole-ring brightness")
	_check(marker.swirl_pixel(turned, PI * 0.5, false).a > 0.65, "Bright head arrives at its rotated position")
	var tail := Vector2(cos(-1.6) * 0.94 * 25.0, sin(-1.6) * 0.94 * 17.0)
	_check(marker.swirl_pixel(tail, 0.0, false).a < marker.swirl_pixel(head, 0.0, false).a * 0.4, "Curved trails fade from bright heads to dim tails")
	_check(marker.swirl_pixel(Vector2.ZERO, 0.0, true).a == 0, "Even highlighted swirls leave the ground center empty")
	var thick_head := Vector2(cos(-0.12) * 0.57 * 25.0, sin(-0.12) * 0.57 * 17.0)
	_check(marker.swirl_pixel(thick_head, 0.0, false).a > 0.6, "Wider bright cores remain visible away from the original thin centerline")
	_demo.selected = ""
	for dimensions in [Vector2i(1200, 900), Vector2i(1280, 720), Vector2i(720, 1000)]:
		game.reset(SEED)
		_begin_fixture(["ginseng", "silk", "jade"], [0, 4, 5])
		_demo.selected = ""
		_demo._focus_index = -1
		_demo.toast_time = 0
		_demo.set_process(false)
		_demo._time = 0.0
		root.size = dimensions
		_move_board(Vector2(420, 800))
		_demo.queue_redraw()
		await _frames(5)
		var before: Image
		if _preview:
			await RenderingServer.frame_post_draw
			before = root.get_texture().get_image()
		var initial := _snapshot()
		await _capture("30_workers_idle_%dx%d" % [dimensions.x, dimensions.y])
		await _check_rendered_reference(reference, upper_bodies)
		if _preview:
			_demo._time = 0.9
			_demo.queue_redraw()
			await _frames()
			await _capture("30_workers_quarter_%dx%d" % [dimensions.x, dimensions.y])
			await RenderingServer.frame_post_draw
			_check_ring_pixels(before, root.get_texture().get_image())
			_demo._time = 3.6
			_demo.queue_redraw()
			await _frames()
			await RenderingServer.frame_post_draw
			_check(before.get_data() == root.get_texture().get_image().get_data(), "A complete rotation restores every scene pixel")
			_demo._time = 0.0
			game.players[0].cash = 0
			_demo.queue_redraw()
			await _frames()
			await _capture("30_workers_unavailable_%dx%d" % [dimensions.x, dimensions.y])
			await RenderingServer.frame_post_draw
			var unavailable := root.get_texture().get_image()
			for index in 3:
				var zoom := minf(_demo.size.x / BASE.x, _demo.size.y / BASE.y)
				var origin: Vector2 = (_demo.size - BASE * zoom) * 0.5
				var ring_rect := Rect2(WORKER_FEET[index] + Vector2(-28, -17), Vector2(56, 40))
				var area := Rect2i(Vector2i((origin + ring_rect.position * zoom).ceil()), Vector2i((ring_rect.size * zoom).floor()))
				_check(before.get_region(area).get_data() != unavailable.get_region(area).get_data(), "Idle swirls have visible pixels; unavailable jobs have no swirl")
				var fee_rect := Rect2(WORKER_HEADS[index] + Vector2(-15, -30), Vector2(30, 22))
				var fee_start: Vector2 = (origin + fee_rect.position * zoom).ceil()
				var fee_end: Vector2 = (origin + fee_rect.end * zoom).floor()
				var fee_pixels := 0
				for y in range(int(fee_start.y), int(fee_end.y)):
					for x in range(int(fee_start.x), int(fee_end.x)):
						var visible := before.get_pixel(x, y)
						if visible != unavailable.get_pixel(x, y) and visible.r > 0.9 and visible.g > 0.8 and visible.b > 0.6:
							fee_pixels += 1
				_check(fee_pixels > 15, "Each permanent fee has actual bright glyph pixels at this window size")
				print("HARBOR_PIXEL_FEE size=%s slot=%d bright_pixels=%d" % [dimensions, index, fee_pixels])
			game.players[0].cash = initial.players[0].cash
			_demo.queue_redraw()
			await _frames()
		if _preview and dimensions == Vector2i(1200, 900) and "--swirl-preview" in OS.get_cmdline_user_args():
			# Capture the actual app at 20 animation samples per second for a local loop.
			for frame in 72:
				_demo._time = float(frame) / 20.0
				_demo.queue_redraw()
				await _frames(2)
				await _capture("30_workers_loop_%02d" % frame)
			_demo._time = 0.0
			_demo.queue_redraw()
			await _frames()
		var initial_hits: Array = _demo._hits.duplicate(true)
		for index in 3:
			for point in [WORKER_HEADS[index] + Vector2(0, -19), WORKER_INPUTS[index], WORKER_BODIES[index].get_center(), WORKER_FEET[index] + Vector2(0, 12)]:
				_click_board(point)
				await _frames()
				_check(_demo.selected == "shipyard_%d" % index and _snapshot() == initial, "Independent fee, input, worker-body and ring clicks select exactly their own site without spending")
				_key(KEY_ESCAPE)
		_move_board(Vector2(420, 800))
		_demo.queue_redraw()
		await _frames()
		var hovered_bodies: Array[Image] = []
		for index in 3:
			var id := "shipyard_%d" % index
			_move_board(WORKER_FEET[index] + Vector2(0, 12))
			_demo.queue_redraw()
			await _frames()
			var data: Dictionary = _demo.placement_marker(id)
			_check(data.shipyard and data.preview and data.show_price and not data.occupied, "Real shipyard hover highlights the existing worker's ring and overhead fee")
			_check(_snapshot() == initial and _demo._hits == initial_hits, "Worker hover neither spends nor enlarges input targets")
			if _preview:
				await RenderingServer.frame_post_draw
				var hovered := root.get_texture().get_image()
				_check_worker_pixels(before, hovered, data)
				var zoom := minf(_demo.size.x / BASE.x, _demo.size.y / BASE.y)
				var origin: Vector2 = (_demo.size - BASE * zoom) * 0.5
				var body_start: Vector2 = (origin + data.pawn.position * zoom).ceil()
				var body_end: Vector2 = (origin + Vector2(data.pawn.end.x, data.feet.y - 18) * zoom).floor()
				var body := Rect2i(Vector2i(body_start), Vector2i(body_end - body_start))
				hovered_bodies.append(hovered.get_region(body))
				_check(before.get_region(body).get_data() == hovered_bodies[index].get_data(), "Idle and hovered worker upper bodies are identical; no pawn is overlaid")
		await _capture("30_workers_hover_%dx%d" % [dimensions.x, dimensions.y])
		_click_board(Vector2(1032, 559))
		_move_board(Vector2(420, 800))
		_demo.queue_redraw()
		await _frames()
		_check(_demo.selected == "shipyard_0" and _demo.placement_marker("shipyard_0").preview and _snapshot() == initial, "Selected worker's ring stays highlighted after leaving, without charging")
		await _capture("30_workers_selected_%dx%d" % [dimensions.x, dimensions.y])
		if _preview:
			await RenderingServer.frame_post_draw
			var selected_image := root.get_texture().get_image()
			_check_worker_pixels(before, selected_image, _demo.placement_marker("shipyard_0"))
			_demo._time = 0.9
			_demo.queue_redraw()
			await _frames()
			await RenderingServer.frame_post_draw
			var zoom := minf(_demo.size.x / BASE.x, _demo.size.y / BASE.y)
			var origin: Vector2 = (_demo.size - BASE * zoom) * 0.5
			var area := Rect2i(Vector2i((origin + Vector2(1000, 580) * zoom).ceil()), Vector2i((Vector2(56, 40) * zoom).floor()))
			_check(selected_image.get_region(area).get_data() != root.get_texture().get_image().get_region(area).get_data(), "Active swirl keeps rotating instead of freezing on selection")
			_demo._time = 0.0
			_demo.queue_redraw()
			await _frames()
		for gate in ["busy", "modal", "dice"]:
			_demo.busy = gate == "busy"
			_demo.modal = "help" if gate == "modal" else ""
			_demo.dice_overlay.state = "rolling" if gate == "dice" else "closed"
			var gated: Dictionary = _demo.placement_marker("shipyard_0")
			_check(not gated.preview and not gated.active and not gated.show_price and not gated.ring_visible, "Busy, modal and dice gates hide the placement invitation and overhead fee")
		_demo.busy = false
		_demo.modal = ""
		_demo.dice_overlay.state = "closed"
		_key(KEY_ESCAPE)
		_demo.queue_redraw()
		await _frames()
		_check(_demo.selected.is_empty() and _snapshot() == initial, "Cancel clears the worker selection without consuming cash or crew")
		if _preview:
			await RenderingServer.frame_post_draw
			_check(before.get_data() == root.get_texture().get_image().get_data(), "Cancelled worker selection exactly restores the idle background and rings")
		await _keyboard_activate("slot:shipyard_0")
		_check(_demo.selected == "shipyard_0", "Keyboard can select the background hammer-worker site")
		await _click_id("confirm")
		_check(game.slots.owners.get("shipyard_0") == 0 and game.players[0].cash == initial.players[0].cash - 4 and game.players[0].crew == 3, "Shipyard confirmation assigns the worker site and charges four pesos once")
		var occupied: Dictionary = _demo.placement_marker("shipyard_0")
		_check(occupied.occupied and not occupied.preview and not occupied.show_price and not occupied.ring_visible, "Confirmation leaves the background worker, adds an owner strip and removes the invitation ring")
		var committed := _snapshot()
		_key(KEY_SPACE)
		await _frames()
		_check(_snapshot() == committed, "Repeated confirmation cannot duplicate the worker placement")
		await _capture("30_workers_occupied_%dx%d" % [dimensions.x, dimensions.y])
		if _preview:
			await RenderingServer.frame_post_draw
			var occupied_image := root.get_texture().get_image()
			_check_worker_pixels(before, occupied_image, occupied)
			var zoom := minf(_demo.size.x / BASE.x, _demo.size.y / BASE.y)
			var origin: Vector2 = (_demo.size - BASE * zoom) * 0.5
			var body_start: Vector2 = (origin + occupied.pawn.position * zoom).ceil()
			var body_end: Vector2 = (origin + Vector2(occupied.pawn.end.x, occupied.feet.y - 18) * zoom).floor()
			var body := Rect2i(Vector2i(body_start), Vector2i(body_end - body_start))
			_check(hovered_bodies[0].get_data() == occupied_image.get_region(body).get_data(), "Idle, hovered and confirmed upper bodies remain identical background pixels")
		# Visual fixture: three different background workers, distinguished by foot tags.
		for index in 3:
			game.slots.owners["shipyard_%d" % index] = index
			_check(_demo.placement_marker("shipyard_%d" % index).color == game.players[index].color, "Existing background workers retain individual owner colors")
		_demo.queue_redraw()
		await _frames()
		await _capture("30_workers_three_owners_%dx%d" % [dimensions.x, dimensions.y])
		if _preview:
			await RenderingServer.frame_post_draw
			var owners_image := root.get_texture().get_image()
			var zoom := minf(_demo.size.x / BASE.x, _demo.size.y / BASE.y)
			var origin: Vector2 = (_demo.size - BASE * zoom) * 0.5
			for index in 3:
				var owner_data: Dictionary = _demo.placement_marker("shipyard_%d" % index)
				_check_worker_pixels(before, owners_image, owner_data)
				var body_start: Vector2 = (origin + owner_data.pawn.position * zoom).ceil()
				var body_end: Vector2 = (origin + Vector2(owner_data.pawn.end.x, owner_data.feet.y - 18) * zoom).floor()
				var body := Rect2i(Vector2i(body_start), Vector2i(body_end - body_start))
				_check(hovered_bodies[index].get_data() == owners_image.get_region(body).get_data(), "Each occupied worker's upper body matches its idle and hovered appearance")
				# Sample the interior of the actual 10-by-2 owner strip, not metadata.
				var strip_center: Vector2 = origin + (WORKER_FEET[index] + Vector2(0, 6)) * zoom
				var strip_pixel := owners_image.get_pixel(floori(strip_center.x), floori(strip_center.y))
				_check(strip_pixel.is_equal_approx(game.players[index].color), "Each occupied worker renders its owner's color at the independent foot-strip center")
		await _check_rendered_reference(reference, upper_bodies)
		_demo.set_process(true)
	game.reset(SEED)
	await _frames()
	print("HARBOR_PIXEL_DEMO_CHECK stage=shipyard_character complete")


func _test_ground_light_art() -> void:
	_stage = "foreshortened timber-worker light across a complete rotation"
	var game = _demo.game
	for dimensions in [Vector2i(1200, 900), Vector2i(1280, 720), Vector2i(720, 1000)]:
		game.reset(SEED)
		_begin_fixture(["ginseng", "silk", "jade"], [0, 4, 5])
		_demo.set_process(false)
		_demo.selected = ""
		_demo._focus_index = -1
		_demo.toast_time = 0
		root.size = dimensions
		_move_board(Vector2(420, 800))
		game.players[0].crew = 0
		_demo.queue_redraw()
		await _frames(3)
		var baseline: Image
		if _preview:
			await RenderingServer.frame_post_draw
			baseline = root.get_texture().get_image()
		game.players[0].crew = 4
		_demo.queue_redraw()
		await _frames(2)
		var initial := _snapshot()
		var initial_hits: Array = _demo._hits.duplicate(true)
		var zoom := minf(_demo.size.x / BASE.x, _demo.size.y / BASE.y)
		var origin: Vector2 = (_demo.size - BASE * zoom) * 0.5
		# Independent scene regions: shallow foot light, then untouched ground below it.
		var light_start := Vector2i((origin + Vector2(1198, 685) * zoom).ceil())
		var light_end := Vector2i((origin + Vector2(1254, 701) * zoom).floor())
		var ground_start := Vector2i((origin + Vector2(1216, 702) * zoom).ceil())
		var ground_end := Vector2i((origin + Vector2(1234, 715) * zoom).floor())
		var light_area := Rect2i(light_start, light_end - light_start)
		var ground_area := Rect2i(ground_start, ground_end - ground_start)
		for mode in ["idle", "hover", "keyboard"]:
			_move_board(WORKER_INPUTS[1] if mode == "hover" else Vector2(420, 800))
			if mode == "keyboard":
				for _step in _demo._hits.size() + 1:
					_key(KEY_TAB)
					if _demo._hits[_demo._focus_index].id == "slot:shipyard_1":
						break
			for step in 9:
				_demo._time = float(step) * 0.45
				_demo.queue_redraw()
				await _frames(2)
				var data: Dictionary = _demo.placement_marker("shipyard_1")
				_check(data.ring_visible and data.active == (mode != "idle"), "Ground light remains visible with the expected input mode")
				_check(_snapshot() == initial and _demo._hits == initial_hits, "Foreshortening and rotation never change rules or worker input targets")
				if _preview:
					await RenderingServer.frame_post_draw
					var image := root.get_texture().get_image()
					_check(image.get_region(light_area).get_data() != baseline.get_region(light_area).get_data(), "Ground light remains visibly animated at every sampled phase")
					_check(image.get_region(ground_area).get_data() == baseline.get_region(ground_area).get_data(), "Ground below the timber worker stays untouched across idle, hover and keyboard rotation")
		_demo.set_process(true)
	game.reset(SEED)
	await _frames()
	print("HARBOR_PIXEL_DEMO_CHECK stage=ground_light complete")


func _check_ring_pixels(before: Image, after: Image) -> void:
	var zoom := minf(_demo.size.x / BASE.x, _demo.size.y / BASE.y)
	var origin: Vector2 = (_demo.size - BASE * zoom) * 0.5
	var changes := [0, 0, 0]
	var outside := 0
	var filled_center := 0
	for y in after.get_height():
		for x in after.get_width():
			if before.get_pixel(x, y) == after.get_pixel(x, y):
				continue
			var point := (Vector2(x, y) + Vector2(0.5, 0.5) - origin) / zoom
			var on_ring := false
			for index in 3:
				# Independent bounds around the three existing background workers' feet.
				var center: Vector2 = WORKER_FEET[index] + Vector2(0, 3)
				if Rect2(center - Vector2(28, 20), Vector2(56, 40)).has_point(point):
					on_ring = true
					changes[index] += 1
					var local := point - center
					if Vector2(local.x / 10.0, local.y / 3.5).length() < 1.0:
						filled_center += 1
			if not on_ring:
				outside += 1
	_check(outside == 0 and filled_center == 0, "Rotation changes only the three local swirls, never scene/UI or empty centers")
	_check(changes[0] > 10 and changes[1] > 10 and changes[2] > 10, "All three idle placement swirls visibly rotate")
	print("HARBOR_PIXEL_RING size=%s changes=%s outside=%d filled_center=%d" % [root.size, changes, outside, filled_center])


func _check_worker_pixels(before: Image, after: Image, data: Dictionary) -> void:
	var zoom := minf(_demo.size.x / BASE.x, _demo.size.y / BASE.y)
	var origin: Vector2 = (_demo.size - BASE * zoom) * 0.5
	var start: Vector2 = origin + data.pawn.position * zoom
	var end: Vector2 = origin + Vector2(data.pawn.end.x, data.feet.y - 18) * zoom
	var colors: Dictionary = {}
	var sampled := 0
	var changed := 0
	for y in range(ceili(start.y), floori(end.y)):
		for x in range(ceili(start.x), floori(end.x)):
			# Only sample the existing upper body, above rings and owner strips.
			sampled += 1
			colors[after.get_pixel(x, y).to_rgba32()] = true
			if before.get_pixel(x, y) != after.get_pixel(x, y):
				changed += 1
	_check(sampled > 100 and colors.size() > 20, "Real framebuffer retains the detailed multicolor background worker above its feet")
	_check(changed == 0, "Hover or ownership never overlays a new pawn or changes the existing worker's upper body")
	print("HARBOR_PIXEL_WORKER size=%s occupied=%s sampled=%d colors=%d changed=%d" % [root.size, data.occupied, sampled, colors.size(), changed])


func _check_preview_pixels(before: Image, after: Image, data: Dictionary) -> void:
	var zoom := minf(_demo.size.x / BASE.x, _demo.size.y / BASE.y)
	var origin: Vector2 = (_demo.size - BASE * zoom) * 0.5
	var shape: PackedVector2Array = data.shape
	var outside := 0
	var pawn := 0
	var price := 0
	var highlight := 0
	for y in after.get_height():
		for x in after.get_width():
			if before.get_pixel(x, y) == after.get_pixel(x, y):
				continue
			var point := (Vector2(x, y) + Vector2(0.5, 0.5) - origin) / zoom
			var on_shape := Geometry2D.is_point_in_polygon(point, shape)
			for i in shape.size():
				# One-pixel non-antialiased edge is centered on its scene contour.
				if point.distance_to(Geometry2D.get_closest_point_to_segment(point, shape[i], shape[(i + 1) % shape.size()])) <= 1.0:
					on_shape = true
			var on_pawn: bool = data.pawn.has_point(point)
			var on_price: bool = data.price.has_point(point)
			pawn += 1 if on_pawn else 0
			price += 1 if on_price else 0
			highlight += 1 if on_shape else 0
			if not on_shape and not on_pawn and not on_price:
				outside += 1
	_check(outside == 0, "Hover changes only the precise scene contour, pawn and contextual price")
	_check(pawn > 0 and price > 0 and highlight > 0, "Actual framebuffer contains the preview pawn, price and local highlight")
	print("HARBOR_PIXEL_SCENE_PREVIEW size=%s pawn=%d price=%d highlight=%d outside=%d" % [root.size, pawn, price, highlight, outside])


func _check_stock_markers() -> void:
	var overlay = _demo.market_overlay
	var columns := {"nutmeg": 0, "silk": 1, "ginseng": 2, "jade": 3}
	var previous := {}
	for value in [0, 5, 10, 20, 30]:
		var prices := {"ginseng": value, "nutmeg": value, "silk": value, "jade": value}
		overlay.open(prices)
		var stage = overlay.stage
		_check(stage is SubViewportContainer and stage._viewport.own_world_3d, "Market uses its own real 3D viewport")
		_check(stage.prices == prices and stage.markers.size() == 4, "All four public prices reach the model")
		var seen: Array[Node3D] = []
		for id in columns:
			var row: int = [0, 5, 10, 20, 30].find(value)
			var info: Dictionary = stage.marker_state(id)
			var marker: Node3D = stage.markers[id]
			var target := Vector3(-3.35 + row * 1.88, 0.045, -3.35 + columns[id] * 2.25)
			_check(info.price == value and info.row == row and info.column == columns[id], "Five legal prices map to independent procedural lanes")
			_check(marker.position.is_equal_approx(target), "Actual procedural marker occupies its price socket")
			_check(marker == stage.board.find_child("Marker_" + id, true, false) and marker.get_child_count() >= 3, "Moving price marker is a multi-part sculpted cargo, not a flat overlay")
			_check(not seen.has(marker), "Four cargo markers are distinct scene nodes")
			seen.append(marker)
			if previous.has(id):
				_check(marker.position.x > previous[id], "Higher price advances right along the cargo track")
			previous[id] = marker.position.x
	overlay.close()


func _test_stock_art() -> void:
	_stage = "3D public prices, removed background board and phase-owned stock selection"
	_check_stock_markers()
	var game = _demo.game
	var reference: Image = _demo.BOARD.get_image().duplicate()
	reference.convert(Image.FORMAT_RGBA8)
	var patch: Image = _demo.FAN_PATCH.get_image().duplicate()
	patch.convert(Image.FORMAT_RGBA8)
	reference.blend_rect(patch, Rect2i(Vector2i.ZERO, patch.get_size()), Vector2i.ZERO)
	# Protect the entire former board footprint as well as every old scenery strip.
	var regions = [Rect2(1008, 646, 232, 244), Rect2(1038, 648, 156, 37), Rect2(1012, 692, 20, 185), Rect2(1216, 702, 18, 173), Rect2(1040, 866, 184, 17), Rect2(978, 700, 26, 176), Rect2(1244, 701, 26, 176), Rect2(1034, 894, 200, 25)]
	for dimensions in [Vector2i(1200, 900), Vector2i(1280, 720), Vector2i(720, 1000)]:
		game.reset(SEED)
		_check(_begin_fixture(["ginseng", "silk", "jade"], [0, 4, 5]), "Share-art fixture reaches dispatch through election and stock skip")
		root.size = dimensions
		await _frames(5)
		_check_stock_view()
		for _actor in 3:
			_check(game.pass_turn(game.current_player), "Remove only temporary placement invitations using public passes")
		_click_board(Vector2(420, 800))
		await _frames()
		await _check_rendered_reference(reference, regions)
		var before := _snapshot()
		await _click_id("help")
		var overlay = _demo.market_overlay
		_click_root(overlay.launcher.get_global_rect().get_center())
		await _frames()
		_check(overlay.is_open and overlay.layer > _demo.dice_overlay.layer and _demo.modal == "help", "Native stock icon opens above help without replacing its context")
		_check(overlay.screen.get_global_rect() == Rect2(Vector2.ZERO, Vector2(root.size)) and overlay.screen.mouse_filter == Control.MOUSE_FILTER_STOP, "Price shade covers the whole actual window")
		for id in ["close", "buy:jade", "stock_skip", "confirm", "next", "restart_confirm"]:
			_demo._activate(id)
		_check(_snapshot() == before and _demo.modal == "help", "Read-only market blocks stale underlying actions")
		await _capture("13_shares_%dx%d" % [dimensions.x, dimensions.y])
		_key(KEY_ESCAPE)
		await _frames()
		_check(not overlay.is_open and _demo.modal == "help", "Escape closes prices only")
		await _click_id("close")
		game.reset(SEED)
		if not _win_auction(0):
			return
		await _frames()
		before = _snapshot()
		_check_stock_view()
		await _capture("17_stock_purchase_%dx%d" % [dimensions.x, dimensions.y])
		var point := _hit_center("buy:ginseng")
		_click_board(point)
		_click_board(point)
		await _frames()
		_check(game.phase == "setup" and game.players[0].holdings.ginseng == before.players[0].holdings.ginseng + 1 and game.players[0].cash == before.players[0].cash - 5, "Phase-owned stock purchase executes once despite same-frame duplicate clicks")
		_check(game.prices == before.prices, "Buying does not alter public stock values")
		_check_stock_view()
		game.reset(SEED)
		if not _win_auction(0):
			return
		await _frames()
		before = _snapshot()
		await _keyboard_activate("buy:jade")
		_check(game.phase == "setup" and game.players[0].holdings.jade == before.players[0].holdings.jade + 1 and game.players[0].cash == before.players[0].cash - 5, "Keyboard buys from the stock stage at each aspect ratio")
		_check_stock_view()
		await _click_id("to_starts")
		await _click_id("begin")
		_check(game.phase == "dispatch" and _demo.stock_hand.visible, "Completed preparation reveals synchronized real holdings")
		for _actor in 3:
			_check(game.pass_turn(game.current_player), "Price-only pixel fixture removes animated placement invitations through public passes")
		await _frames()
		await _check_live_price_pixels()
	# Explicit value fixtures distinguish public value, cost, stock and holdings.
	game.reset(SEED)
	if not _win_auction(0):
		return
	for i in 4:
		game.prices[game.CARGO_IDS[i]] = [0, 5, 20, 30][i]
	game.stock.ginseng = 0
	game.players[0].cash = 19
	game.changed.emit()
	await _frames()
	_check_stock_view()
	await _capture("14_shares_values")
	_check(_demo.purchase_row("ginseng").action == "已售罄", "Empty bank stock is visibly disabled in the stock stage")
	_check(not _has_hit("buy:ginseng") and not _has_hit("buy:silk") and not _has_hit("buy:jade") and _has_hit("buy:nutmeg"), "Only affordable in-stock purchase remains focusable")
	var blocked := _snapshot()
	for id in ["buy:ginseng", "buy:silk", "buy:jade"]:
		_demo._activate(id)
	await _frames()
	_check(_snapshot() == blocked, "Disabled stock actions do not mutate cash or inventory")
	await _capture("18_stock_unavailable")
	await _click_id("buy:nutmeg")
	_check(game.phase == "setup" and game.players[0].cash == 14 and game.stock.nutmeg == blocked.stock.nutmeg - 1, "Remaining affordable stock enters preparation")
	await _click_id("to_starts")
	await _click_id("begin")
	_check(not _has_hit("stocks") and not _has_hit("stock_skip"), "Purchase actions disappear once voyage begins")
	blocked = _snapshot()
	_demo._activate("stocks")
	_demo._activate("buy:jade")
	await _frames()
	_check(_demo.modal.is_empty() and _snapshot() == blocked, "Removed purchase entry and out-of-phase buy cannot transact")
	game.reset(SEED)
	await _frames()
	_check_stock_view()
	print("HARBOR_PIXEL_DEMO_CHECK stage=stock_art complete")


func _check_live_price_pixels() -> void:
	var game = _demo.game
	_demo.toast_time = 0
	for id in game.CARGO_IDS:
		game.prices[id] = 0
	game.changed.emit()
	await _frames()
	var overlay = _demo.market_overlay
	overlay.open(game.prices)
	for marker in overlay.stage.markers.values():
		_check(is_equal_approx(marker.position.x, -3.35), "All zero-price pieces occupy the leftmost track position")
	for i in 4:
		game.prices[game.CARGO_IDS[i]] = [5, 10, 20, 30][i]
	var expected := _snapshot()
	game.changed.emit()
	await _frames()
	_check(overlay.stage.prices == game.prices, "Open model receives live public price changes")
	for i in 4:
		var id: String = game.CARGO_IDS[i]
		var marker: Node3D = overlay.stage.markers[id]
		_check(is_equal_approx(marker.position.x, -3.35 + (i + 1) * 1.88), "Actual 3D cargo advances to its new live price position")
	_check(_snapshot() == expected, "Synchronizing prices does not change cash, holdings, bank supply or phase")
	overlay.close()
	await _frames()
	_check_stock_view()
	var reference: Image = _demo.BOARD.get_image().duplicate()
	reference.convert(Image.FORMAT_RGBA8)
	var patch: Image = _demo.FAN_PATCH.get_image().duplicate()
	patch.convert(Image.FORMAT_RGBA8)
	reference.blend_rect(patch, Rect2i(Vector2i.ZERO, patch.get_size()), Vector2i.ZERO)
	await _check_rendered_reference(reference, [Rect2(1008, 646, 232, 244), Rect2(1216, 702, 18, 173)])
	print("HARBOR_PIXEL_SHARES_VALUES size=%s updated=4 background_preserved=true" % root.size)


func _test_live_fan() -> void:
	_stage = "live face-up fan counts, layout and modal layering"
	var game = _demo.game
	var hand = _demo.stock_hand
	var patch := Image.new()
	_check(patch.load_png_from_buffer(FileAccess.get_file_as_bytes("res://demo/harbor_pixel/art/fan_patch.png")) == OK, "Static-fan cleanup layer decodes")
	var forbidden := 0
	for y in patch.get_height():
		for x in patch.get_width():
			if patch.get_pixel(x, y).a > 0 and (y < 899 or x < 396 or x > 1080):
				forbidden += 1
	_check(forbidden == 0, "Cleanup alpha is confined to original bottom-hand neighborhood")
	var fixtures = [[], ["jade"], ["ginseng", "silk"], ["ginseng", "nutmeg", "silk", "jade", "jade"]]
	for dimensions in [Vector2i(1200, 900), Vector2i(1280, 720), Vector2i(720, 1000)]:
		root.size = dimensions
		for ids in fixtures:
			game.reset(SEED)
			_check(_begin_fixture(["ginseng", "silk", "jade"], [0, 4, 5]), "Hand fixture uses a live dispatch stage after public election")
			for id in game.CARGO_IDS:
				game.players[0].holdings[id] = ids.count(id)
			game.changed.emit()
			await _frames(5)
			_check_stock_view()
			_check(hand.visible, "Fan is visible during gameplay")
			var zoom := minf(_demo.size.x / BASE.x, _demo.size.y / BASE.y)
			var origin: Vector2 = (_demo.size - BASE * zoom) * 0.5
			for card in hand.cards:
				for corner in [Vector2(-1, -1), Vector2(221, -1), Vector2(-1, 314), Vector2(221, 314)]:
					var point: Vector2 = (card.get_global_transform() * corner - origin) / zoom
					_check(Rect2(408, 926, 664, 160).has_point(point), "Rotated card and shadow stay between action panels and below sea")
			if ids.size() > 1:
				_check(hand.cards.front().rotation < 0 and hand.cards.back().rotation > 0, "Actual cards fan out rather than forming a parallel row")
			var before := _snapshot()
			_click_board(Vector2(740, 1000))
			await _frames()
			_check(_snapshot() == before and hand._raised == -1, "Display-only cards do not spend, flip or hover outside hand bounds")
			hand.cover_all()
			_check_stock_view()
			await _capture("15_fan_%d_%dx%d" % [ids.size(), dimensions.x, dimensions.y])
		await _click_id("help")
		_check(not hand.visible, "Parent-drawn modal hides native hand children")
		await _capture("16_fan_modal")
		_key(KEY_ESCAPE)
		await _frames()
		_check(hand.visible, "Closing modal restores the same face-up cards")
		_check_stock_view()
	game.reset(SEED)
	await _frames()
	_check_stock_view()
	# Default reuse keeps the older HD-2D demo's private flip behavior unchanged.
	var legacy = _demo.StockHand.new()
	root.add_child(legacy)
	legacy.set_holdings(["jade"])
	_check(not legacy.display_only and legacy._faces[0].texture == legacy.BACK, "Legacy fan still starts covered")
	legacy._toggle_card(0)
	_check(legacy._faces[0].texture == legacy.FACES.jade, "Legacy fan still flips on activation")
	legacy.cover_all()
	_check(legacy._faces[0].texture == legacy.BACK, "Legacy fan still covers cards")
	legacy.queue_free()
	await _frames()
	print("HARBOR_PIXEL_DEMO_CHECK stage=live_fan complete")


func _check_fresh_resources() -> void:
	var game = _demo.game
	for player in game.players:
		var count := 0
		for amount in player.holdings.values():
			count += int(amount)
		_check(player.cash == 30 and player.crew == 4 and count == 2, "Fresh player has 30 cash, four crew and two shares")
	for id in game.CARGO_IDS:
		var count: int = game.stock[id]
		for player in game.players:
			count += player.holdings[id]
		_check(count == 5 and game.prices[id] == 0, "Fresh market conserves five shares per cargo at zero price")


func _snapshot() -> Dictionary:
	var game = _demo.game
	return {"players": game.players.duplicate(true), "positions": game.positions.duplicate(),
		"cargo": game.cargo.duplicate(), "phase": game.phase, "actor": game.current_player,
		"voyage": game.voyage, "round": game.dispatch_round, "sails": game.sail_count,
		"dice": game.dice.duplicate(), "prices": game.prices.duplicate(), "stock": game.stock.duplicate(),
		"owners": game.slots.owners.duplicate(), "arrived": game.slots.arrived.duplicate(),
		"logs": game.log_lines.duplicate(), "settlement": game.settlement_lines.duplicate(),
		"passed": game._passed.duplicate(), "bought": game._bought_stock, "settled": game._settled,
		"harbormaster": game.harbormaster, "previous_harbormaster": game.previous_harbormaster,
		"dispatch_visited": game._dispatch_visited, "auction_bid": game.auction_bid,
		"auction_leader": game.auction_leader, "auction_passed": game.auction_passed.duplicate(),
		"slot_cargo": game.slots.ships.duplicate(),
		"pilots": game._pilots_done, "rng_state": game._rng.state}


func _visual_matches() -> bool:
	for ship in 3:
		if not is_equal_approx(float(_demo.visual_positions[ship]), float(_demo.game.positions[ship])):
			return false
	return true


func _has_hit(id: String) -> bool:
	for hit in _demo._hits:
		if hit.id == id:
			return true
	return false


func _hit_center(id: String) -> Vector2:
	# Match production's reverse hit priority (e.g. the lower Cancel button).
	for index in range(_demo._hits.size() - 1, -1, -1):
		if _demo._hits[index].id == id:
			return _demo._hits[index].rect.get_center()
	return Vector2(-10000, -10000)


func _check_modal_hits(allowed: Array) -> void:
	for hit in _demo._hits:
		var accepted := false
		for prefix in allowed:
			if hit.id == prefix or (str(prefix).ends_with(":") and str(hit.id).begins_with(prefix)):
				accepted = true
		_check(accepted, "Modal exposes only its own hit regions: %s" % hit.id)


func _click_id(id: String) -> bool:
	await _frames()
	if not _check(_has_hit(id), "Visible input target exists: %s" % id):
		return false
	_click_board(_hit_center(id))
	await _frames()
	return true


func _move_board(point: Vector2) -> void:
	var zoom := minf(_demo.size.x / BASE.x, _demo.size.y / BASE.y)
	var origin: Vector2 = (_demo.size - BASE * zoom) * 0.5
	_move_root(_demo.position + origin + point * zoom)


func _move_root(point: Vector2) -> void:
	var event := InputEventMouseMotion.new()
	event.position = point
	event.global_position = point
	event.relative = point - _pointer_position
	_pointer_position = point
	root.push_input(event, true)


func _click_board(point: Vector2) -> void:
	# Independent transform, not the production _origin/_zoom under test.
	var zoom := minf(_demo.size.x / BASE.x, _demo.size.y / BASE.y)
	var origin: Vector2 = (_demo.size - BASE * zoom) * 0.5
	_click_root(_demo.position + origin + point * zoom)


func _click_root(point: Vector2) -> void:
	_move_root(point)
	for pressed in [true, false]:
		var event := InputEventMouseButton.new()
		event.position = point
		event.global_position = point
		event.button_index = MOUSE_BUTTON_LEFT
		event.button_mask = MOUSE_BUTTON_MASK_LEFT if pressed else 0
		event.pressed = pressed
		root.push_input(event, true)


func _key(code: int, is_echo := false, shift := false) -> void:
	for pressed in [true, false]:
		var event := InputEventKey.new()
		event.keycode = code
		event.physical_keycode = code
		event.pressed = pressed
		event.echo = is_echo and pressed
		event.shift_pressed = shift
		root.push_input(event, true)


func _keyboard_activate(id: String) -> bool:
	if not _check(_has_hit(id), "Keyboard target exists: %s" % id):
		return false
	for _step in _demo._hits.size() + 1:
		var index: int = _demo._focus_index
		if index >= 0 and index < _demo._hits.size() and _demo._hits[index].id == id:
			_key(KEY_ENTER)
			await _frames()
			return true
		_key(KEY_TAB)
	_check(false, "Tab reaches target within one bounded focus cycle: %s" % id)
	return false


func _frames(count := 3) -> void:
	# Let the engine send legitimate CanvasItem draw notifications. Do not call
	# _draw manually and do not fabricate hit regions, even in headless mode.
	for _frame in count:
		await process_frame
	if is_instance_valid(_demo) and not _demo.game.players.is_empty():
		_check_turn_status()
		_check_character_status()


func _capture(label: String) -> void:
	if not _preview:
		return
	print("HARBOR_PIXEL_CAPTURE_BEGIN %s elapsed_ms=%d" % [label, Time.get_ticks_msec() - _started_ms])
	await RenderingServer.frame_post_draw
	var image: Image = root.get_texture().get_image()
	if not _check(image != null and not image.is_empty(), "Rendered viewport screenshot is available: %s" % label):
		return
	var directory := ProjectSettings.globalize_path(OUTPUT)
	if not _check(DirAccess.make_dir_recursive_absolute(directory) == OK, "Screenshot output directory is writable"):
		return
	var path := directory.path_join(label + ".png")
	_check(image.save_png(path) == OK, "Screenshot saves: %s" % label)
	print("HARBOR_PIXEL_DEMO_CAPTURE %s" % path)


func _check(condition: bool, message: String) -> bool:
	_assertions += 1
	if not condition:
		_failures.append("%s: %s" % [_stage, message])
		push_error("HARBOR_PIXEL_DEMO_FAIL %s: %s" % [_stage, message])
	return condition


func _finish(forced_code := -1) -> void:
	if _done:
		return
	_done = true
	var scope := "shipyard-only" if "--shipyard-only" in OS.get_cmdline_user_args() else "full"
	if forced_code < 0 and scope == "full":
		_check(_completed_suite and _committed_rolls == 9 and _settlements == [1, 2, 3], "Full suite reached its explicit terminal checkpoint with all voyages")
	var code := forced_code if forced_code >= 0 else (0 if _failures.is_empty() else 1)
	print("HARBOR_PIXEL_DEMO_CHECK completed assertions=%d failures=%d sails=%d settlements=%s elapsed_ms=%d preview=%s exit=%d" % [_assertions, _failures.size(), _committed_rolls, _settlements, Time.get_ticks_msec() - _started_ms, _preview, code])
	print("HARBOR_PIXEL_DEMO_CHECK_%s scope=%s" % ["PASS" if code == 0 else "FAIL", scope])
	if is_instance_valid(_demo):
		_demo.queue_free()
	quit(code)
