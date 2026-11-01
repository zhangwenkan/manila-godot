extends Control

const Game = preload("res://demo/harbor_pixel/harbor_game.gd")
const Pixel = preload("res://card/pixel_card_theme.gd")
const DialogSkin = preload("res://ui/harbor_dialog_skin.gd")
const MarketOverlay = preload("res://demo/harbor_pixel/market_overlay.gd")
const MarketStage = preload("res://demo/harbor_pixel/market_stage_3d.gd")
const TurnBoard = preload("res://demo/harbor_pixel/turn_board.gd")
const CharacterStatus = preload("res://demo/harbor_pixel/character_status.gd")
const PlacementMarker = preload("res://demo/harbor_pixel/placement_marker.gd")
const DiceOverlay = preload("res://demo/harbor_pixel/dice_overlay.gd")
const StockHand = preload("res://ui/stock_hand.gd")
const FAN_PATCH = preload("res://demo/harbor_pixel/art/fan_patch.png")
const HAND_RECT = Rect2(408, 926, 664, 160)
const HAND_SCALE = 0.42
const FONT = preload("res://card/fonts/fusion-pixel-12px-proportional-zh_hans.otf")
const BOARD = preload("res://demo/harbor_pixel/art/harbor_workers_board.png")
const GOODS = ["ginseng", "nutmeg", "silk", "jade"]
const ICONS = {
	"ginseng": preload("res://demo/harbor_pixel/art/ginseng.png"),
	"nutmeg": preload("res://demo/harbor_pixel/art/nutmeg.png"),
	"silk": preload("res://demo/harbor_pixel/art/silk.png"),
	"jade": preload("res://demo/harbor_pixel/art/jade.png"),
}
const COLORS = {"ginseng": Color("eebf68"), "nutmeg": Color("bfa0d3"), "silk": Color("f0a499"), "jade": Color("8ac9a2")}
const INK = Color("16383d")
const PAPER = Color("fff0c6")
const GOLD = Color("ffd875")
const MUTED = Color("a3c5bd")
const BASE = Vector2(1448, 1086)
# Visible outer edge of the blue dice icon already painted into BOARD.
const SAIL_RECT = Rect2(1324, 955, 110, 113)
const PILOTS = {
	# Reference-pixel silhouettes: the taller west tower and shorter east tower.
	"pilot_1": Rect2(488, 462, 67, 161),
	"pilot_0": Rect2(893, 572, 61, 123),
}
const SHIP_X = [636.0, 732.0, 826.0]
const SHIP_SEAT_SIZE = Vector2(22, 20)
const SHORE = {
	"harbor_0": Vector2(564, 218), "harbor_1": Vector2(622, 218), "harbor_2": Vector2(680, 218),
	# Existing workers in the updated background: hammer, timber, workbench.
	"shipyard_0": Vector2(1032, 559), "shipyard_1": Vector2(1226, 653), "shipyard_2": Vector2(1348, 558),
	"pirate_0": Vector2(162, 570), "pirate_1": Vector2(220, 570),
	# The red crane building is insurance, not the repair shed.
	"insurance_0": Vector2(1170, 424),
}

const SHIPYARD_WORKERS = {
	"shipyard_0": {"feet": Vector2(1028, 597), "head": Vector2(1032, 525), "body": Rect2(1007, 525, 58, 74)},
	# This worker's shallow ground shadow ends near y701; foreshorten light, not input.
	"shipyard_1": {"feet": Vector2(1226, 691), "head": Vector2(1231, 613), "body": Rect2(1199, 613, 54, 80), "ring_scale": Vector2(1, 0.4)},
	"shipyard_2": {"feet": Vector2(1340, 592), "head": Vector2(1356, 520), "body": Rect2(1326, 520, 52, 76)},
}

var game = Game.new()
var visual_positions: Array = [2.0, 3.0, 4.0]
var busy = false
var auto_ai = true
var selected = ""
var modal = ""
var toast = ""
var toast_time = 0.0
var setup_cargo: Array = ["ginseng", "silk", "jade"]
var setup_starts: Array = [2, 3, 4]
var _hits: Array[Dictionary] = []
var _origin = Vector2.ZERO
var _zoom = 1.0
var _ai_clock = 0.0
var _time = 0.0
var _roll_time = 0.0
var _roll_from: Array = []
var _roll_phase = "idle"
var _roll_request = 0
var _roll_context: Dictionary = {}
var dice_overlay: CanvasLayer
var market_overlay: CanvasLayer
var stock_hand: Control
var _mouse = Vector2(-100, -100)
var _focus_index = -1
var _focus_slot = ""
var _setup_error = ""
var _inspector_key: Array = []
var _inspector_cached := Rect2()
var _setup_step = "cargo"
var _chosen_cargo = "ginseng"
var _bid_amount = 1
var _seen_phase = ""
var character_id = "Carmen"
var _ledger_page = 0
var _ledger_lines: Array[String] = []
const LEDGER_PAGE_SIZE = 8


func _ready() -> void:
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	mouse_filter = Control.MOUSE_FILTER_STOP
	stock_hand = StockHand.new()
	stock_hand.name = "ActualStockFan"
	stock_hand.display_only = true
	add_child(stock_hand)
	dice_overlay = DiceOverlay.new()
	add_child(dice_overlay)
	dice_overlay.results_ready.connect(_on_dice_results)
	dice_overlay.skip_requested.connect(_on_dice_skip)
	dice_overlay.failed.connect(_on_dice_failed)
	market_overlay = MarketOverlay.new()
	add_child(market_overlay)
	market_overlay.open_requested.connect(func(): _activate("market"))
	market_overlay.closed.connect(func(): _ai_clock = 0.0)
	character_id = str(get_tree().get_meta("harbor_character", "Carmen"))
	if not CharacterStatus.CHARACTERS.has(character_id):
		character_id = "Carmen"
	game.changed.connect(_on_changed)
	game.reset()
	_sync_setup()
	resized.connect(queue_redraw)
	mouse_exited.connect(func():
		_mouse = Vector2(-100, -100)
		queue_redraw()
	)
	queue_redraw()


func _on_changed() -> void:
	game.players[0].name = CharacterStatus.CHARACTERS[character_id].name
	if busy and _roll_phase == "rolling":
		_on_dice_failed("航程状态已经改变，本次投掷已取消。", _roll_request)
	if not busy:
		visual_positions = game.positions.duplicate()
	_hits.clear()
	_focus_index = -1
	_focus_slot = ""
	_ai_clock = 0.0
	_bid_amount = game.auction_bid + 1
	if _seen_phase != game.phase:
		selected = ""
		if game.phase == "setup":
			_sync_setup()
			_setup_step = "cargo"
		_seen_phase = game.phase
	if game.phase != "dispatch" or game.current_player != 0:
		selected = ""
	if is_instance_valid(stock_hand):
		var ids: Array[String] = []
		for cargo_id in GOODS:
			for _copy in int(game.players[0].holdings.get(cargo_id, 0)):
				ids.append(cargo_id)
		stock_hand.set_holdings(ids)
	if is_instance_valid(market_overlay):
		market_overlay.sync_prices(game.prices)
	queue_redraw()


func _sync_setup() -> void:
	setup_cargo = game.cargo.duplicate()
	setup_starts = game.positions.duplicate()
	visual_positions = game.positions.duplicate()
	_setup_error = ""


func _process(delta: float) -> void:
	_time += delta
	toast_time = maxf(0.0, toast_time - delta)
	if busy:
		if _roll_phase == "rolling":
			if not _roll_context_matches():
				_on_dice_failed("航程状态已经改变，本次投掷已取消。", _roll_request)
		elif _roll_phase == "result":
			# The physical throw still settles while viewing prices. Only hold its
			# presentation, so closing prices cannot hide or resubmit the result.
			if not market_overlay.is_open:
				_roll_time += delta
			if _roll_time >= 0.8:
				dice_overlay.close(_roll_request)
				_roll_phase = "moving"
				_roll_time = 0.0
		elif _roll_phase == "moving":
			_roll_time += delta
			var progress = clampf(_roll_time / 1.15, 0.0, 1.0)
			var eased = progress * progress * (3.0 - 2.0 * progress)
			for i in 3:
				visual_positions[i] = lerpf(float(_roll_from[i]), float(game.positions[i]), eased)
			if progress >= 1.0:
				finish_animation()
	elif auto_ai and not market_overlay.is_open and modal.is_empty() and game.current_player > 0 and game.phase in ["auction", "stock", "setup", "dispatch", "sailing"]:
		_ai_clock += delta
		if _ai_clock >= 0.9:
			_ai_clock = 0.0
			if game.phase == "sailing":
				start_roll([], game.harbormaster)
			else:
				game.ai_step()
	else:
		_ai_clock = 0.0
	queue_redraw()


func _input(event: InputEvent) -> void:
	if market_overlay.is_open:
		if event is InputEventKey:
			if event.pressed and not event.echo and event.keycode in [KEY_ESCAPE, KEY_M, KEY_ENTER, KEY_SPACE]:
				market_overlay.close()
			get_viewport().set_input_as_handled()
		return
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_M:
			_activate("market")
			get_viewport().set_input_as_handled()
			return
	if dice_overlay.state != "closed":
		if event is InputEventKey:
			if event.pressed and not event.echo and dice_overlay.state == "result" and event.keycode in [KEY_ESCAPE, KEY_SPACE, KEY_ENTER]:
				_on_dice_skip(_roll_request)
			get_viewport().set_input_as_handled()
		return
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_ESCAPE:
			if busy:
				finish_animation()
			elif not modal.is_empty():
				modal = ""
			else:
				selected = ""
			get_viewport().set_input_as_handled()
		elif event.keycode == KEY_SPACE:
			if busy:
				finish_animation()
			elif modal.is_empty() and game.phase == "sailing":
				start_roll()
			elif modal.is_empty() and not selected.is_empty():
				_activate("confirm")
			get_viewport().set_input_as_handled()
		elif event.keycode == KEY_TAB:
			market_overlay.launcher.release_focus()
			if not _hits.is_empty():
				_focus_index = posmod(_focus_index + (-1 if event.shift_pressed else 1), _hits.size())
				if _hits[_focus_index].id == "inspect":
					_focus_index = posmod(_focus_index + (-1 if event.shift_pressed else 1), _hits.size())
				var focused: String = _hits[_focus_index].id
				_focus_slot = focused.trim_prefix("slot:") if focused.begins_with("slot:") else ""
				queue_redraw()
			get_viewport().set_input_as_handled()
		elif event.keycode == KEY_ENTER and _focus_index >= 0 and _focus_index < _hits.size():
			_activate(_hits[_focus_index].id)
			get_viewport().set_input_as_handled()


func _gui_input(event: InputEvent) -> void:
	if market_overlay.is_open or dice_overlay.state != "closed":
		accept_event()
		return
	if event is InputEventMouseMotion:
		# Layout/redraw hover refreshes can emit stationary motion events. They
		# must not steal keyboard focus or replace the last actual pointer move.
		if event.relative.is_zero_approx():
			return
		_mouse = (event.position - _origin) / _zoom
		_focus_index = -1
		_focus_slot = ""
		queue_redraw()
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		var point = (event.position - _origin) / _zoom
		_mouse = point
		_focus_index = -1
		_focus_slot = ""
		for i in range(_hits.size() - 1, -1, -1):
			if _hits[i].rect.has_point(point):
				_activate(_hits[i].id)
				accept_event()
				return
		if modal.is_empty():
			selected = ""


func _activate(id: String) -> void:
	if id == "market":
		market_overlay.open(game.prices)
		_ai_clock = 0.0
		return
	if market_overlay.is_open:
		return
	if busy or dice_overlay.state != "closed":
		if id == "skip_animation":
			finish_animation()
		return
	# Old hit IDs must not bypass the active overlay or the model's actor checks.
	if not modal.is_empty():
		if id == "close":
			modal = ""
		elif modal == "ledger" and id in ["ledger_prev", "ledger_next"]:
			var pages := maxi(1, ceili(float(_ledger_lines.size()) / LEDGER_PAGE_SIZE))
			_ledger_page = clampi(_ledger_page + (-1 if id == "ledger_prev" else 1), 0, pages - 1)
		elif modal == "pass" and id == "pass_confirm":
			if game.pass_turn(0):
				modal = ""
		elif modal == "restart" and id == "restart_confirm":
			modal = ""
			_seen_phase = ""
			game.reset()
		_hits.clear()
		_focus_index = -1
		queue_redraw()
		return
	if id in ["help", "ledger"]:
		modal = id
		selected = ""
		if id == "ledger":
			_ledger_lines = _wrapped_lines(game.log_lines, 646, 20)
			_ledger_page = maxi(0, ceili(float(_ledger_lines.size()) / LEDGER_PAGE_SIZE) - 1)
	elif id == "next" and game.phase == "settlement":
		game.next_voyage()
	elif id == "restart" and game.phase == "finished":
		modal = "restart"
	elif game.phase == "auction" and game.current_player == 0:
		if id == "bid_less":
			_bid_amount = maxi(game.auction_bid + 1, _bid_amount - 1)
		elif id == "bid_more":
			_bid_amount = mini(game.players[0].cash, _bid_amount + 1)
		elif id == "bid":
			if not game.bid(_bid_amount, 0):
				_notify("报价须高于当前价，且不能超过现金。")
		elif id == "bid_pass":
			game.pass_bid(0)
	elif game.phase == "stock" and game.harbormaster == 0:
		if id == "stock_skip":
			game.skip_stock(0)
		elif id.begins_with("buy:"):
			if not game.buy_stock(id.trim_prefix("buy:"), 0):
				_notify("无法买入，请检查现金与库存。")
	elif game.phase == "setup" and game.harbormaster == 0:
		_setup_error = ""
		if _setup_step == "cargo":
			if id.begins_with("pick:") and GOODS.has(id.trim_prefix("pick:")):
				_chosen_cargo = id.trim_prefix("pick:")
			elif id.begins_with("load:"):
				var value := id.trim_prefix("load:")
				if value.is_valid_int() and int(value) in range(3):
					var ship := int(value)
					var previous: int = setup_cargo.find(_chosen_cargo)
					if previous >= 0:
						setup_cargo[previous] = setup_cargo[ship]
					setup_cargo[ship] = _chosen_cargo
			elif id == "to_starts":
				_setup_step = "starts"
		elif id == "back_cargo":
			_setup_step = "cargo"
		elif id.begins_with("start:"):
			var parts := id.split(":")
			if parts.size() == 3 and parts[1].is_valid_int() and parts[2] in ["-1", "1"] and int(parts[1]) in range(3):
				var ship := int(parts[1])
				setup_starts[ship] = clampi(setup_starts[ship] + int(parts[2]), 0, 5)
		elif id == "begin":
			if not game.begin_voyage(setup_cargo, setup_starts, 0):
				_setup_error = "起点各为 0–5，合计必须为 9。"
	elif game.phase == "dispatch" and game.current_player == 0:
		if id.begins_with("slot:"):
			var slot_id := id.trim_prefix("slot:")
			if not game.slots.get_position(slot_id).is_empty():
				selected = slot_id
		elif id == "cancel":
			selected = ""
		elif id == "confirm" and not selected.is_empty():
			var reason: String = game.placement_reason(selected, 0)
			if reason.is_empty() and game.place(selected, 0):
				selected = ""
			else:
				_notify(reason if not reason.is_empty() else "岗位状态已经变化，请重新选择。")
		elif id == "pass":
			modal = "pass"
	elif id == "sail" and game.phase == "sailing" and game.harbormaster == 0:
		start_roll()
	_hits.clear()
	_focus_index = -1
	queue_redraw()


func _notify(value: String) -> void:
	toast = value
	toast_time = 4.0


func start_roll(forced: Array = [], actor: int = 0) -> bool:
	if busy or market_overlay.is_open or not modal.is_empty() or game.phase != "sailing" or actor != game.harbormaster:
		return false
	if not forced.is_empty() and not DiceOverlay.valid_values(forced):
		return false
	_roll_from = visual_positions.duplicate()
	_roll_context = {"voyage": game.voyage, "sails": game.sail_count, "cargo": game.cargo.duplicate(), "positions": game.positions.duplicate(), "actor": actor, "harbormaster": game.harbormaster}
	_roll_request += 1
	busy = true
	_roll_phase = "rolling"
	_roll_time = 0.0
	_focus_index = -1
	_hits.clear()
	var labels: Array = []
	for id in game.cargo:
		labels.append(Game.CARGO_NAMES[id])
	if not dice_overlay.open(game.cargo, labels, _roll_request, forced):
		_on_dice_failed("骰盘暂不可用，请重新投掷。", _roll_request)
		return false
	return true


func _roll_context_matches() -> bool:
	return game.phase == "sailing" and game.voyage == _roll_context.get("voyage") and game.sail_count == _roll_context.get("sails") and game.cargo == _roll_context.get("cargo") and game.positions == _roll_context.get("positions") and game.harbormaster == _roll_context.get("harbormaster") and game.harbormaster == _roll_context.get("actor")


func _on_dice_results(values: Array, request: int) -> void:
	if request != _roll_request or not busy or _roll_phase != "rolling":
		return
	if not DiceOverlay.valid_values(values) or not _roll_context_matches():
		_on_dice_failed("投掷状态已失效，本次未结算。", request)
		return
	# Only this callback commits a normal physical throw. Mark first, so a
	# duplicate settlement cannot re-enter while changed handlers are running.
	_roll_phase = "result"
	if not game.roll(values, int(_roll_context.actor)):
		_on_dice_failed("航行结果未能应用，请重新投掷。", request)
		return
	_roll_time = 0.0


func _on_dice_skip(request: int) -> void:
	if request != _roll_request or _roll_phase != "result":
		return
	dice_overlay.close(request)
	_roll_phase = "moving"
	_roll_time = 0.0
	queue_redraw()


func _on_dice_failed(message: String, request: int) -> void:
	if request != _roll_request or not busy:
		return
	dice_overlay.close(request)
	_roll_request += 1
	_roll_phase = "idle"
	busy = false
	visual_positions = game.positions.duplicate()
	_notify(message)


func finish_animation() -> void:
	if _roll_phase == "rolling":
		return
	dice_overlay.close(_roll_request)
	visual_positions = game.positions.duplicate()
	busy = false
	_roll_phase = "idle"
	_roll_time = 0.0
	queue_redraw()


func slot_point(id: String) -> Vector2:
	var item: Dictionary = game.slots.get_position(id)
	if item.is_empty():
		return Vector2.ZERO
	if PILOTS.has(id):
		return PILOTS[id].get_center()
	if int(item.ship) < 0:
		return SHORE.get(id, Vector2.ZERO)
	var seat = int(id.get_slice("_", 2))
	return ship_point(int(item.ship)) + Vector2(-14 + (seat % 2) * 28, -5 + floori(seat / 2.0) * 26)


func slot_rect(id: String) -> Rect2:
	if PILOTS.has(id):
		return PILOTS[id]
	var item: Dictionary = game.slots.get_position(id)
	var extent = SHIP_SEAT_SIZE if int(item.get("ship", -1)) >= 0 else Vector2(44, 38)
	return Rect2(slot_point(id) - extent * 0.5, extent)


func ship_point(ship: int) -> Vector2:
	# The reference's 0 and 11 labels are at y742 and y396; keep both number rails clear.
	var position_value: float = float(setup_starts[ship]) if game.phase == "setup" and game.harbormaster == 0 else float(visual_positions[ship])
	return Vector2(SHIP_X[ship], 742.0 - clampf(position_value, 0.0, 14.0) * 31.5)


func ship_bounds(ship: int) -> Rect2:
	# Encloses the hull, cargo, seats and their hover / keyboard outlines.
	return Rect2(ship_point(ship) + Vector2(-32, -49), Vector2(64, 89))


func _draw() -> void:
	if game.players.is_empty():
		return
	draw_rect(Rect2(Vector2.ZERO, size), Color("102c34"))
	_zoom = minf(size.x / BASE.x, size.y / BASE.y)
	_origin = (size - BASE * _zoom) * 0.5
	draw_set_transform(_origin, 0.0, Vector2.ONE * _zoom)
	draw_texture_rect(BOARD, Rect2(Vector2.ZERO, BASE), false)
	draw_texture_rect(FAN_PATCH, Rect2(Vector2.ZERO, BASE), false)
	# Resolve keyboard identity before rebuilding the per-frame input list.
	_focus_slot = ""
	if _focus_index >= 0 and _focus_index < _hits.size() and _hits[_focus_index].id.begins_with("slot:"):
		_focus_slot = _hits[_focus_index].id.trim_prefix("slot:")
	_hits.clear()
	_draw_shore()
	for ship in 3:
		_draw_ship(ship)
	_draw_hud()
	_draw_hand()
	_draw_controls()
	_draw_inspector()
	if modal.is_empty() and game.phase == "auction":
		_draw_auction()
	elif modal.is_empty() and game.phase == "stock" and game.harbormaster == 0:
		_hits.clear()
		draw_rect(Rect2(Vector2.ZERO, BASE), DialogSkin.SHADE)
		_draw_purchase()
	if not busy and game.phase in ["settlement", "finished"] and modal.is_empty():
		_draw_result()
	if not modal.is_empty():
		_draw_modal()
	if dice_overlay.state != "closed":
		_hits.clear()
	if _focus_index >= 0 and _focus_index < _hits.size() and not _hits[_focus_index].id.begins_with("slot:"):
		draw_rect(_hits[_focus_index].rect.grow(1), GOLD, false, 2)
	draw_set_transform(Vector2.ZERO)


func _panel(rect: Rect2, color: Color = INK) -> void:
	Pixel.step_rect(self, Rect2(rect.position + Vector2(4, 6), rect.size), 8, Color(0.02, 0.1, 0.12, 0.5))
	Pixel.step_rect(self, rect, 8, color)
	draw_line(rect.position + Vector2(8, 2), rect.position + Vector2(rect.size.x - 8, 2), Color("497075"), 2)


func _text(value: String, at: Vector2, font_size: int = 24, color: Color = PAPER) -> void:
	draw_string(FONT, at + Vector2(1, 2), value, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(0.02, 0.08, 0.09, 0.7))
	draw_string(FONT, at, value, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, color)


func _wrapped_lines(lines: Array, width: float, font_size: int) -> Array[String]:
	var result: Array[String] = []
	for source in lines:
		var line = ""
		for character in str(source):
			if not line.is_empty() and FONT.get_string_size(line + character, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x > width:
				result.append(line)
				line = ""
			line += character
		result.append(line)
	return result


func _center(value: String, rect: Rect2, font_size: int = 24, color: Color = PAPER) -> void:
	var width = FONT.get_string_size(value, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
	while width > rect.size.x - 12 and font_size > 12:
		font_size -= 1
		width = FONT.get_string_size(value, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
	_text(value, rect.position + Vector2((rect.size.x - width) * 0.5, (rect.size.y + font_size * 0.7) * 0.5), font_size, color)


func _hit(id: String, rect: Rect2) -> void:
	_hits.append({"id": id, "rect": rect})


func _button(id: String, value: String, rect: Rect2, active = true, accent = false) -> void:
	if not modal.is_empty() or game.phase in ["settlement", "finished"]:
		_dialog_button(id, value, rect, active, accent)
		return
	var color = Color("caa35b") if accent else Color("315960")
	if not active:
		color = Color("375156")
	elif rect.has_point(_mouse):
		color = color.lightened(0.2)
	_panel(rect, color)
	_center(value, rect, 22, INK if accent and active else (PAPER if active else MUTED))
	if active:
		_hit(id, rect)


func _draw_shore() -> void:
	for id in SHORE:
		_draw_slot(id)
	for id in PILOTS:
		_draw_pilot(id)


func placement_hit_rect(id: String) -> Rect2:
	var rect := slot_rect(id)
	if PILOTS.has(id):
		return rect
	var item: Dictionary = game.slots.get_position(id)
	if SHIPYARD_WORKERS.has(id):
		var worker: Dictionary = SHIPYARD_WORKERS[id]
		return rect.grow(5).merge(worker.body).merge(PlacementMarker.ring_bounds(worker.feet).grow(1)).merge(PlacementMarker.price_bounds(worker.head).grow(1))
	return rect.grow(2 if int(item.get("ship", -1)) >= 0 else 5)


func placement_marker(id: String) -> Dictionary:
	var item: Dictionary = game.slots.get_position(id)
	if item.is_empty():
		return {}
	var rect := slot_rect(id)
	var compact: bool = int(item.ship) >= 0
	var point := slot_point(id)
	var feet := point + Vector2(0, 13)
	var price := Rect2(point + Vector2(14, -19), Vector2(22, 16))
	if compact:
		feet = point + Vector2(0, 9)
		price = Rect2(rect.position + Vector2(4, -3), Vector2(15, 11))
	elif id == "pilot_1":
		feet = Vector2(522, 617)
		price = Rect2(535, 584, 22, 16)
	elif id == "pilot_0":
		feet = Vector2(923, 690)
		price = Rect2(936, 657, 22, 16)
	var pixel := 1 if compact else 3
	var pawn := Rect2(feet - Vector2(3 * pixel, 10 * pixel), Vector2(7 * pixel + 1, 10 * pixel + 1))
	var shipyard: bool = SHIPYARD_WORKERS.has(id)
	var shape_point := point
	if shipyard:
		var worker: Dictionary = SHIPYARD_WORKERS[id]
		feet = worker.feet
		pawn = worker.body
		price = PlacementMarker.price_bounds(worker.head)
		shape_point = feet - Vector2(0, 13)
	var occupant = game.slots.owners.get(id)
	var gate: bool = not busy and modal.is_empty() and dice_overlay.state == "closed" and game.phase == "dispatch" and game.current_player == 0
	var available: bool = gate and game.placement_reason(id, 0).is_empty()
	var active: bool = false
	if gate:
		if not selected.is_empty():
			active = selected == id
		elif _focus_index >= 0:
			active = _focus_slot == id
		else:
			active = placement_hit_rect(id).has_point(_mouse)
	var ring_rect := PlacementMarker.ring_bounds(feet) if shipyard else Rect2()
	return {"input_rect": rect, "shape": PlacementMarker.site_shape(id, shape_point, compact),
		"ring_rect": ring_rect, "ring_visible": shipyard and available and occupant == null,
		"ring_phase": PlacementMarker.swirl_phase(_time),
		"ring_scale": SHIPYARD_WORKERS[id].get("ring_scale", Vector2.ONE) if shipyard else Vector2.ONE,
		"feet": feet, "pawn": pawn, "price": price, "compact": compact, "shipyard": shipyard,
		"label": "$%d" % int(item.cost), "available": available, "active": active,
		"preview": active and available and occupant == null,
		"show_price": (active or (shipyard and available)) and occupant == null, "occupied": occupant != null,
		"color": game.players[int(occupant) if occupant != null else 0].color}


func _draw_pilot(id: String) -> void:
	_draw_slot(id)


func _draw_slot(id: String) -> void:
	var data := placement_marker(id)
	if data.is_empty():
		return
	PlacementMarker.draw_marker(self, data)
	if not busy and modal.is_empty() and game.phase == "dispatch" and game.current_player == 0:
		_hit("slot:" + id, placement_hit_rect(id))


func _draw_ship(ship: int) -> void:
	var p = ship_point(ship)
	var cargo_id: String = setup_cargo[ship] if game.phase == "setup" and game.harbormaster == 0 else game.cargo[ship]
	var color: Color = COLORS[cargo_id]
	# Compact token: one shared, stable origin for hull, cargo and seat hits.
	var hull = PackedVector2Array([p + Vector2(0, -48), p + Vector2(19, -30), p + Vector2(30, -15), p + Vector2(30, 31), p + Vector2(23, 39), p + Vector2(-23, 39), p + Vector2(-30, 31), p + Vector2(-30, -15), p + Vector2(-19, -30)])
	draw_colored_polygon(hull, Color("423d36"))
	Pixel.step_rect(self, Rect2(p + Vector2(-27, -17), Vector2(54, 53)), 4, Color("b08755"))
	draw_colored_polygon(PackedVector2Array([p + Vector2(0, -44), p + Vector2(20, -20), p + Vector2(-20, -20)]), color)
	draw_texture_rect(ICONS[cargo_id], Rect2(p + Vector2(-11, -42), Vector2(22, 22)), false)
	if game.phase == "setup":
		var capacity: int = game.slots.COSTS[cargo_id].size()
		for seat in capacity:
			draw_circle(p + Vector2(-14 + (seat % 2) * 28, -5 + floori(seat / 2.0) * 26), 4, INK)
	else:
		for item in game.slots.positions:
			if item.ship == ship:
				_draw_slot(item.id)


func _draw_hud() -> void:
	CharacterStatus.draw_board(self, character_status())
	TurnBoard.draw_board(self, turn_status())
	_scene_button("ledger", "eye", Rect2(1272, 24, 54, 54), "玩家与账本")
	_button("help", "?", Rect2(1340, 24, 54, 54))
	if toast_time > 0 and modal.is_empty() and game.phase not in ["settlement", "finished"]:
		_panel(Rect2(400, 124, 626, 40), Color(0.06, 0.2, 0.22, 0.93))
		_center(toast, Rect2(400, 124, 626, 40), 18)


func character_status() -> Dictionary:
	return CharacterStatus.status(game, character_id)


func turn_status() -> Dictionary:
	return TurnBoard.status(game, busy, _roll_phase, _setup_step)


func stock_marker(cargo_id: String) -> Dictionary:
	return MarketStage.marker_info(cargo_id, game.prices)


func purchase_row(cargo_id: String) -> Dictionary:
	var cost: int = maxi(5, game.prices[cargo_id])
	var supply: int = game.stock[cargo_id]
	var available: bool = game.phase == "stock" and game.harbormaster == 0 and supply > 0 and game.players[0].cash >= cost and not busy and modal.is_empty()
	var action := "买入 · %d 比索" % cost
	if game.phase != "stock" or game.harbormaster != 0:
		action = "仅当任局长可买"
	elif supply <= 0:
		action = "已售罄"
	elif game.players[0].cash < cost:
		action = "现金不足"
	return {"cost": cost, "supply": supply, "action": action, "available": available}


func _draw_hand() -> void:
	# Native child controls need the same aspect-fit transform as custom drawing.
	stock_hand.position = _origin + HAND_RECT.position * _zoom
	stock_hand.size = HAND_RECT.size / HAND_SCALE
	stock_hand.scale = Vector2.ONE * HAND_SCALE * _zoom
	# Children draw above the parent's custom modal; hide explicitly underneath it.
	stock_hand.visible = modal.is_empty() and game.phase in ["dispatch", "sailing"] and dice_overlay.state == "closed"


func _scene_button(id: String, icon: String, rect: Rect2, hint: String, accent := false) -> void:
	var color := Color("caa35b") if accent else Color("315960")
	if rect.has_point(_mouse):
		color = color.lightened(0.2)
	Pixel.step_rect(self, rect, 8, color)
	var rows: Array = Pixel.ICONS[icon]
	var extent := Vector2(rows[0].length(), rows.size()) * 3
	Pixel.icon(self, icon, rect.get_center() - extent * 0.5, 3, INK if accent else PAPER)
	_hits.append({"id": id, "rect": rect, "hint": hint})


func _get_tooltip(at_position: Vector2) -> String:
	var point: Vector2 = (at_position - _origin) / _zoom
	for i in range(_hits.size() - 1, -1, -1):
		if _hits[i].rect.has_point(point):
			return _hits[i].get("hint", "")
	return ""


func _draw_controls() -> void:
	if not modal.is_empty():
		return
	if busy:
		if _roll_phase == "moving":
			_hits.append({"id": "skip_animation", "rect": SAIL_RECT, "hint": "跳过航行 · 空格"})
	elif game.phase == "setup" and game.harbormaster == 0:
		_draw_setup()
	elif game.phase == "sailing" and game.harbormaster == 0:
		# Keep the original blue artwork; only hover/focus adds a thin outline.
		_hits.append({"id": "sail", "rect": SAIL_RECT, "hint": "掷骰航行 · 空格"})
		if SAIL_RECT.has_point(_mouse):
			draw_rect(SAIL_RECT.grow(2), GOLD, false, 2)
	elif game.phase == "dispatch" and game.current_player == 0:
		_scene_button("pass", "arrow", Rect2(1136, 24, 54, 54), "结束本航程派遣")


func _draw_setup() -> void:
	if _setup_step == "cargo":
		for i in GOODS.size():
			var id: String = GOODS[i]
			var rect := Rect2(582 + i * 76, 826, 66, 66)
			_panel(rect, Color("a78448") if _chosen_cargo == id else INK)
			draw_texture_rect(ICONS[id], Rect2(rect.position + Vector2(12, 6), Vector2(42, 42)), false)
			_center(Game.CARGO_NAMES[id], Rect2(rect.position + Vector2(0, 44), Vector2(66, 20)), 15)
			_hits.append({"id": "pick:" + id, "rect": rect, "hint": "选货后点击船只装载"})
		for ship in 3:
			var rect := ship_bounds(ship).grow(5)
			draw_rect(rect, GOLD if rect.has_point(_mouse) else MUTED, false, 2)
			_hits.append({"id": "load:%d" % ship, "rect": rect, "hint": "装载%s" % Game.CARGO_NAMES[_chosen_cargo]})
		_button("to_starts", "起点 →", Rect2(916, 830, 140, 56), true, true)
	else:
		for ship in 3:
			var p := ship_point(ship)
			_button("start:%d:-1" % ship, "−", Rect2(p + Vector2(-39, 48), Vector2(36, 36)), setup_starts[ship] > 0)
			_button("start:%d:1" % ship, "+", Rect2(p + Vector2(3, 48), Vector2(36, 36)), setup_starts[ship] < 5)
			_panel(Rect2(p + Vector2(-20, -79), Vector2(40, 26)))
			_center(str(setup_starts[ship]), Rect2(p + Vector2(-20, -79), Vector2(40, 26)), 20, GOLD)
		var total: int = setup_starts[0] + setup_starts[1] + setup_starts[2]
		_button("back_cargo", "← 装货", Rect2(532, 830, 140, 56))
		_panel(Rect2(684, 830, 144, 56))
		_center("%d / 9" % total, Rect2(684, 830, 144, 56), 25, GOLD)
		_button("begin", "确认 →", Rect2(840, 830, 140, 56), total == 9, true)
	if not _setup_error.is_empty():
		_center(_setup_error, Rect2(480, 902, 580, 36), 18, GOLD)


func _draw_auction() -> void:
	_hits.clear()
	draw_rect(Rect2(Vector2.ZERO, BASE), DialogSkin.SHADE)
	_dialog_shell(Rect2(374, 288, 700, 488), "竞拍港务局长", false)
	var leader: String = "尚未报价" if game.auction_leader < 0 else game.players[game.auction_leader].name
	_center("%d 比索 · %s" % [game.auction_bid, leader], Rect2(422, 360, 604, 50), 30, GOLD)
	for actor in 3:
		var state := "已退出" if game.auction_passed[actor] else ("最高价" if game.auction_leader == actor else "待报价")
		if game.current_player == actor:
			state = "正在报价"
		var rect := Rect2(423 + actor * 202, 434, 194, 68)
		_center(game.players[actor].name, Rect2(rect.position, Vector2(194, 34)), 21, PAPER)
		_center(state, Rect2(rect.position + Vector2(0, 34), Vector2(194, 30)), 17, GOLD if game.current_player == actor else MUTED)
	if game.current_player == 0:
		_center("可用现金 %d" % game.players[0].cash, Rect2(439, 518, 570, 34), 20, MUTED)
		_dialog_button("bid_less", "−", Rect2(535, 566, 60, 50), _bid_amount > game.auction_bid + 1)
		_center(str(_bid_amount), Rect2(606, 566, 232, 50), 30, GOLD)
		_dialog_button("bid_more", "+", Rect2(851, 566, 60, 50), _bid_amount < game.players[0].cash)
		_dialog_button("bid_pass", "退出竞拍", Rect2(433, 657, 222, 58))
		_dialog_button("bid", "报价", Rect2(791, 657, 222, 58), _bid_amount > game.auction_bid and _bid_amount <= game.players[0].cash, true)
	_dialog_button("help", "?", Rect2(987, 301, 50, 45))


func inspector_rect() -> Rect2:
	if selected.is_empty() or busy or not modal.is_empty() or game.phase != "dispatch":
		return Rect2()
	var item: Dictionary = game.slots.get_position(selected)
	if item.is_empty():
		return Rect2()
	var reason: String = game.placement_reason(selected, 0)
	var extent := Vector2(248, 116 if reason.is_empty() else 154)
	var cache_key: Array = [selected, extent, visual_positions.duplicate(), game.cargo.duplicate()]
	if cache_key == _inspector_key:
		return _inspector_cached
	var anchor := placement_hit_rect(selected)
	var obstacles: Array[Rect2] = []
	var xs: Array[float] = [24.0, BASE.x - extent.x - 24.0, anchor.get_center().x - extent.x * 0.5]
	var ys: Array[float] = [174.0, 912.0 - extent.y, anchor.get_center().y - extent.y * 0.5]
	for slot in game.slots.positions:
		var obstacle := placement_hit_rect(slot.id).grow(8)
		obstacles.append(obstacle)
		xs.append(obstacle.end.x)
		xs.append(obstacle.position.x - extent.x)
		ys.append(obstacle.end.y)
		ys.append(obstacle.position.y - extent.y)
	var best := Rect2()
	var best_score := INF
	# Align to obstacle edges so a crowded ship can use nearby clear shore space.
	for x in xs:
		for y in ys:
			var rect := Rect2(Vector2(clampf(x, 24, BASE.x - extent.x - 24), clampf(y, 174, 912 - extent.y)), extent)
			var score := rect.get_center().distance_squared_to(anchor.get_center())
			for obstacle in obstacles:
				score += rect.intersection(obstacle).get_area() * 1000000.0
			if score < best_score:
				best = rect
				best_score = score
	_inspector_key = cache_key
	_inspector_cached = best
	return best


func _draw_inspector() -> void:
	var rect := inspector_rect()
	if not rect.has_area():
		return
	var item: Dictionary = game.slots.get_position(selected)
	var reason: String = game.placement_reason(selected, 0)
	# The temporary card consumes clicks rather than dispatching through to the scene.
	_hit("inspect", rect)
	_panel(rect)
	_text(item.title, rect.position + Vector2(12, 26), 20)
	var payment := "+10" if selected == "insurance_0" else "−%d" % int(item.cost)
	_text("%s 比索 · 1 船员" % payment, rect.position + Vector2(12, 53), 18, GOLD)
	if not reason.is_empty():
		var lines := _wrapped_lines([reason], rect.size.x - 24, 16)
		for i in mini(lines.size(), 2):
			_text(lines[i], rect.position + Vector2(12, 77 + i * 19), 16, Color("efbd94"))
	if reason.is_empty():
		_scene_button("confirm", "check", Rect2(rect.end - Vector2(100, 50), Vector2(40, 40)), "确认派遣", true)
	_scene_button("cancel", "close", Rect2(rect.end - Vector2(50, 50), Vector2(40, 40)), "取消选择")


func _dialog_shell(rect: Rect2, title: String, dismissible := true) -> void:
	DialogSkin.frame(self, rect, 76)
	var width := minf(570, rect.size.x - 176)
	DialogSkin.header(self, Rect2(rect.get_center().x - width * 0.5, rect.position.y - 42, width, 94), title, 32)
	if dismissible:
		var close_rect := Rect2(rect.end.x - 58, rect.position.y - 25, 68, 68)
		DialogSkin.close_icon(self, close_rect, close_rect.has_point(_mouse))
		_hit("close", close_rect)


func _dialog_button(id: String, value: String, rect: Rect2, active := true, accent := false) -> void:
	DialogSkin.action(self, rect, accent, active, rect.has_point(_mouse))
	_center(value, rect, 22, DialogSkin.PAPER if active else DialogSkin.MUTED)
	if active:
		_hit(id, rect)


func _draw_result() -> void:
	_hits.clear()
	draw_rect(Rect2(Vector2.ZERO, BASE), DialogSkin.SHADE)
	_dialog_shell(Rect2(298, 225, 852, 631), "航程 %d · 收益结算" % game.voyage if game.phase == "settlement" else "航程结束 · 最终身家", false)
	if game.phase == "settlement":
		var lines = _wrapped_lines(game.settlement_lines, 742, 21)
		for i in mini(lines.size(), 12):
			_text(lines[i], Vector2(353, 305 + i * 31), 21)
		if lines.size() > 12:
			_text("更多收益明细请翻阅完整账本。", Vector2(353, 710), 18, MUTED)
		_button("ledger", "完整账本", Rect2(351, 757, 217, 58))
		_button("next", "查看排名 →" if game.voyage >= game.max_voyages else "继续 →", Rect2(785, 757, 306, 58), true, true)
	else:
		_center("现金 + 持股市值", Rect2(340, 315, 766, 43), 24, DialogSkin.MUTED)
		var ranking: Array = game.ranking()
		var place = 1
		for i in ranking.size():
			var actor: int = ranking[i]
			if i > 0 and game.wealth(actor) < game.wealth(ranking[i - 1]):
				place = i + 1
			var y = 410 + i * 89
			Pixel.icon(self, "crew", Vector2(372, y - 22), 4, game.players[actor].color)
			_text("%d.  %s" % [place, game.players[actor].name], Vector2(415, y), 30)
			_text("%d 比索" % game.wealth(actor), Vector2(859, y), 30, GOLD)
		_center("三航程试玩 · 暂无贷款、角色技能与完整事件选择。", Rect2(340, 675, 766, 43), 20, MUTED)
		_button("restart", "再玩一局", Rect2(560, 757, 324, 58), true, true)


func _draw_purchase() -> void:
	_dialog_shell(Rect2(325, 237, 798, 614), "局长 · 买入一股", false)
	draw_line(Vector2(389, 354), Vector2(1056, 354), DialogSkin.GOLD, 1)
	for i in GOODS.size():
		var cargo_id: String = GOODS[i]
		var row := purchase_row(cargo_id)
		var y := 377 + i * 77
		draw_rect(Rect2(386, y, 677, 68), Color("494035"))
		draw_texture_rect(ICONS[cargo_id], Rect2(400, y + 12, 42, 42), false)
		_text(Game.CARGO_NAMES[cargo_id], Vector2(460, y + 28), 24)
		_text("银行余量 %d 张" % row.supply, Vector2(460, y + 54), 17, DialogSkin.MUTED)
		_text("买入价 %d" % row.cost, Vector2(683, y + 40), 21)
		_dialog_button("buy:" + cargo_id, row.action, Rect2(844, y + 12, 202, 43), row.available, true)
	_dialog_button("help", "?", Rect2(390, 766, 54, 49))
	_dialog_button("stock_skip", "跳过 · 装货 →", Rect2(785, 766, 269, 49), true, true)


func _draw_modal() -> void:
	_hits.clear()
	draw_rect(Rect2(Vector2.ZERO, BASE), DialogSkin.SHADE)
	var titles := {"help": "港口指南", "ledger": "玩家与完整账本", "pass": "结束派遣", "restart": "重新开始"}
	_dialog_shell(Rect2(325, 237, 798, 614), titles.get(modal, "港务窗口"))
	if modal == "help":
		var lines = [
			"1  轮流竞价；首价至少 1、加价递增，退出不可重入。",
			"2  得标者付款，可买一股；再装三种货物、安排起点。",
			"3  起点各为 0–5、合计 9；局长先派遣，顺时针轮流。",
			"4  点岗位并确认派人；首航前两轮，其后每航前一轮。",
			"5  局长点右下蓝色骰子；三次航行后结算。",
			"到港船分红 18/24/30/36，按船员平分、向下取整。",
			"港口 / 修船厂收益 6/8/15；保险先领 10，承担修船赔付。",
			"试玩：竞价限现金；无贷款、贫困派遣和角色技能。",
			"首航你先竞价，全弃重拍；以后前任先，全弃留任。",
			"引航自动前推；海盗第三航劫掠；赔付不足由银行垫付。",
			"三航程或市价达 30 结束，以现金加持股市值排名。",
			"空格：掷骰 / 确认 / 跳过；Esc：取消；Tab / Enter：选择。",
			"金币、船员与手牌始终属于你，不随局长易主。",
		]
		for i in lines.size():
			_text(lines[i], Vector2(387, 349 + i * 34), 20, PAPER if i < 7 else MUTED)
	elif modal == "ledger":
		for i in 3:
			var player: Dictionary = game.players[i]
			Pixel.icon(self, "crew", Vector2(389, 325 + i * 42), 3, player.color)
			_text("%s   现金 %d   剩余船员 %d" % [player.name, player.cash, player.crew], Vector2(426, 348 + i * 42), 23)
		var start = _ledger_page * LEDGER_PAGE_SIZE
		for i in mini(LEDGER_PAGE_SIZE, _ledger_lines.size() - start):
			_text(_ledger_lines[start + i], Vector2(389, 494 + i * 31), 20, MUTED)
		var pages = maxi(1, ceili(float(_ledger_lines.size()) / LEDGER_PAGE_SIZE))
		_button("ledger_prev", "← 较早记录", Rect2(388, 766, 198, 48), _ledger_page > 0)
		_center("%d / %d" % [_ledger_page + 1, pages], Rect2(606, 766, 204, 48), 22)
		_button("ledger_next", "较新记录 →", Rect2(829, 766, 198, 48), _ledger_page + 1 < pages)
	elif modal in ["pass", "restart"]:
		var passing = modal == "pass"
		_center("结束本航程的派遣？" if passing else "重新开始这一局？", Rect2(388, 377, 674, 65), 31, GOLD)
		_center("余下派遣轮将自动跳过，已派出的船员保留。" if passing else "当前短局进度将重置。", Rect2(388, 473, 674, 60), 22)
		_button("close", "取消", Rect2(411, 646, 235, 63))
		_button("pass_confirm" if passing else "restart_confirm", "确认", Rect2(787, 646, 235, 63), true, true)
