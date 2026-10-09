extends Node2D

const CharacterCard := preload("res://card/character_card.gd")
const PlacementPanel := preload("res://ui/placement_panel.gd")
const SituationPanel := preload("res://ui/situation_panel.gd")

@export var layout_mode := true
@export var layout_view_size := Vector2(2340.0, 1080.0)
@export var world_size := Vector2(6144.0, 1152.0)
## Preview identity until the pre-game character selection is connected.
@export var initial_character_id := "Lakan Bautista"

@onready var boats: Array[CharacterBody2D] = [$BoatTop, $BoatMiddle, $BoatBottom]
@onready var camera: Camera2D = $Camera2D
@onready var left_pan_button: Button = $CanvasLayer/LeftPanButton
@onready var right_pan_button: Button = $CanvasLayer/RightPanButton
@onready var personal_bar = $CanvasLayer/PersonalBar
@onready var turn_bar = $CanvasLayer/TurnBar
@onready var character_overlay = $CanvasLayer/CharacterOverlay
@onready var select_character_button: Button = $CanvasLayer/SelectCharacterButton
@onready var situation_panel = $CanvasLayer/SituationPanel
@onready var dice_stage = $CanvasLayer/DiceStage3D
@onready var dice_overlay: ColorRect = $CanvasLayer/DiceOverlay
@onready var dice_close_button: Button = $CanvasLayer/DiceCloseButton
var placement_panel: PlacementPanel
var sail_button: Button

var _dice_rolling := false
var _sailing_active := false
var _ship_starts := [3, 3, 3]   # 三船起点，之和须为 9（临时固定，港务长配置后再接）
var _dice_cargo := ["ginseng", "silk", "jade"]  # 每枚骰子对应的货物（港务长选货后设置）
var _current_stakes := [0, 0, 0]
var _dice_results := [1, 1, 1]
var selected_character_id := ""
var _camera_target_x := 0.0
var _camera_target_y := 0.0
var _camera_velocity := 0.0
var _is_manual_camera := false
var _button_press_time := {}
var _player_resources: Dictionary = {}
var _displayed_character_id := ""
var _placement_committing := false
var _acted_this_round: Dictionary = {}
var _awaiting_sail := false
var _route_configured := false
var _voyage_locked := false
var _flow_hold := ""

func _ready() -> void:
	placement_panel = PlacementPanel.new()
	placement_panel.name = "PlacementPanel"
	placement_panel.validate_placement = placement_reason
	placement_panel.confirm_requested.connect(_confirm_placement)
	$CanvasLayer.add_child(placement_panel)
	$CanvasLayer.move_child(placement_panel, character_overlay.get_index())
	for i in boats.size():
		boats[i].get_node("VisualRoot/Seats").bind_state(placement_panel.state, i)
	_camera_target_x = layout_view_size.x * 0.5
	_camera_target_y = layout_view_size.y * 0.5
	_update_camera_position(1.0)

	left_pan_button.button_down.connect(_on_pan_button_down.bind(-1.0, "left"))
	left_pan_button.button_up.connect(_on_pan_button_up.bind(-1.0, "left"))
	right_pan_button.button_down.connect(_on_pan_button_down.bind(1.0, "right"))
	right_pan_button.button_up.connect(_on_pan_button_up.bind(1.0, "right"))

	sail_button = Button.new()
	sail_button.name = "SailButton"
	sail_button.text = "投骰航行"
	sail_button.tooltip_text = "本轮每人派遣一次后，由港务长投骰航行"
	sail_button.add_theme_font_override("font", load("res://card/pixel_card_theme.gd").FONT)
	sail_button.add_theme_font_size_override("font_size", 24)
	sail_button.add_theme_color_override("font_color", Color("e1cda6"))
	sail_button.add_theme_color_override("font_disabled_color", Color("8a7c66"))
	for key in ["normal", "hover", "pressed", "disabled", "focus"]:
		var style := StyleBoxFlat.new()
		style.bg_color = Color("365c59") if key in ["hover", "focus"] else Color("203b3b")
		style.border_color = Color("bc9a68") if key == "focus" else Color("5d8a85")
		style.set_border_width_all(2)
		sail_button.add_theme_stylebox_override(key, style)
	$CanvasLayer.add_child(sail_button)
	# The dispatch modal must cover the regular HUD, including this runtime button.
	$CanvasLayer.move_child(sail_button, placement_panel.get_index())
	sail_button.pressed.connect(_on_sail_button_pressed)

	for i in dice_stage.get_dice_count():
		dice_stage.set_value(i, int(_dice_results[i]))
	dice_stage.dice_settled.connect(_on_dice_settled)
	dice_stage.all_settled.connect(_on_all_dice_settled)
	_sync_dice_cargo()
	character_overlay.character_confirmed.connect(_on_character_confirmed)
	character_overlay.closed.connect(_on_character_roster_closed)
	turn_bar.changed.connect(_sync_active_player)
	placement_panel.state.changed.connect(_refresh_situation)
	for i in character_overlay.cards.size():
		var card = character_overlay.cards[i]
		_player_resources[card.character_name_en] = {
			"coins": 30, "remaining": 3, "capacity": 3,
			"holdings": [personal_bar.CARGO_IDS[i % 4], personal_bar.CARGO_IDS[(i + 1) % 4]],
		}
	for i in character_overlay.cards.size():
		var card = character_overlay.cards[i]
		if card.character_name_en == initial_character_id:
			character_overlay.confirmed_index = i
			_on_character_confirmed(card.character_name_en, card.character_name)
			break
	if turn_bar.players.is_empty():
		turn_bar.set_players(_preview_players(null))
	get_viewport().size_changed.connect(_layout_personal_controls)
	_layout_personal_controls()
	_refresh_situation()


func _layout_personal_controls() -> void:
	var viewport_size := get_viewport_rect().size
	var margin := 24.0 if viewport_size.x >= 1200.0 else 16.0
	var hud_scale := minf(1.0, maxf(1.0, viewport_size.x - margin * 2.0) / personal_bar.DESIGN_SIZE.x)
	personal_bar.set_anchors_preset(Control.PRESET_TOP_LEFT)
	personal_bar.size = Vector2((viewport_size.x - margin * 2.0) / hud_scale, personal_bar.DESIGN_SIZE.y)
	personal_bar.scale = Vector2.ONE * hud_scale
	personal_bar.position = Vector2(margin, viewport_size.y - 12.0 - personal_bar.size.y * hud_scale).floor()
	turn_bar.size = Vector2(personal_bar.size.x, 32)
	turn_bar.scale = personal_bar.scale
	var content_rect: Rect2 = personal_bar.get_content_rect()
	turn_bar.position = personal_bar.position + Vector2(0, (content_rect.position.y - turn_bar.size.y - 6) * hud_scale)
	placement_panel.available_bottom = turn_bar.position.y - 12
	placement_panel._layout()
	# 态势面板固定在左上角，与底栏同缩放；尺寸由 set_situation 按玩家数决定，这里不覆盖。
	situation_panel.scale = personal_bar.scale
	situation_panel.position = Vector2(margin, maxf(margin, placement_panel.available_top)).floor()
	situation_panel.visible = not character_overlay.visible and not dice_overlay.visible
	# 投骰航行按钮：贴在态势面板右侧、同 y、同缩放，受各遮罩隐藏。
	sail_button.scale = personal_bar.scale
	sail_button.position = Vector2(margin + situation_panel.size.x * personal_bar.scale.x + 12, situation_panel.position.y).floor()
	sail_button.visible = not character_overlay.visible and not dice_overlay.visible
	_update_sail_button()


func _refresh_situation() -> void:
	if not is_instance_valid(situation_panel):
		return
	var ship_names := []
	for i in 3:
		ship_names.append(placement_panel.state.cargo_name(i))
	situation_panel.set_situation(turn_bar.players, _displayed_character_id, _player_resources, placement_panel.state.owners, turn_bar.voyage_number, ship_names)


func _process(delta: float) -> void:
	_update_camera_position(delta)

func _on_pan_button_down(_direction: float, key: String) -> void:
	_button_press_time[key] = Time.get_ticks_msec()

func _on_pan_button_up(direction: float, key: String) -> void:
	var press_time: int = _button_press_time.get(key, Time.get_ticks_msec())
	_button_press_time.erase(key)
	var held_seconds := float(Time.get_ticks_msec() - press_time) / 1000.0
	var distance := layout_view_size.x if held_seconds >= 0.35 else layout_view_size.x * 0.25
	_pan_camera(direction * distance)

func _pan_camera(distance: float) -> void:
	var half_view := layout_view_size.x * 0.5
	_is_manual_camera = true
	_camera_target_x = clampf(camera.position.x + distance, half_view, world_size.x - half_view)

func _update_camera_position(delta: float) -> void:
	var half_view := layout_view_size * 0.5
	camera.zoom = Vector2.ONE
	_camera_target_y = clampf(half_view.y, half_view.y, world_size.y - half_view.y)
	if not _is_manual_camera:
		_camera_target_x = 0.0
		for current_boat: CharacterBody2D in boats:
			_camera_target_x = maxf(_camera_target_x, current_boat.global_position.x)
		_camera_target_x = clampf(_camera_target_x, half_view.x, world_size.x - half_view.x)

	var smoothing := 1.0 - exp(-delta * 3.0)
	camera.position.x = lerpf(camera.position.x, _camera_target_x, smoothing)
	camera.position.y = lerpf(camera.position.y, _camera_target_y, smoothing)

func _unhandled_input(event: InputEvent) -> void:
	if dice_overlay.visible and event.is_action_pressed("ui_cancel"):
		_on_close_dice_pressed()
		get_viewport().set_input_as_handled()
		return
	if dice_stage.visible and not character_overlay.visible:
		if dice_stage.handle_debug_input(event):
			get_viewport().set_input_as_handled()

func roll_dice() -> void:
	if _dice_rolling or character_overlay.visible:
		return
	_dice_rolling = true
	_show_dice_mode()
	dice_close_button.disabled = true
	dice_stage.throw_all()


## 航行阶段起投。起点只在本航程第一次航行时定位，之后沿当前船位继续。
func begin_sailing() -> void:
	if not _enter_sailing():
		return
	_sailing_active = true
	roll_dice()


## 不播骰子，直接按给定点数完成本次航行。轮次检查用它覆盖到港和事件边界。
func resolve_sailing_now(steps: Array) -> void:
	if not _enter_sailing():
		return
	for i in mini(steps.size(), _dice_results.size()):
		_dice_results[i] = int(steps[i])
	apply_sailing(_dice_results)
	_voyage_locked = false
	_sailing_active = false
	_continue_after_sailing()


## 港务长准备：设定本航程三船装货（选三种）、骰子↔货物对应与三船起点。
## 现由预览工具/固定数据调用；UI-09/10 接通后由准备流程驱动。
func set_voyage(cargo_ids: Array, dice_cargo: Array = [], starts: Array = []) -> bool:
	if not placement_panel.state.set_voyage_cargo(cargo_ids):
		return false
	placement_panel.rebuild_ship_slots()
	_dice_cargo = dice_cargo.duplicate() if dice_cargo.size() == 3 else cargo_ids.duplicate()
	if starts.size() == 3:
		_ship_starts = starts.duplicate()
	_route_configured = false
	_sync_dice_cargo()
	return true


func _sync_dice_cargo() -> void:
	# 三枚骰子按 _dice_cargo 顺序对应本航程所装货物；原版每种货物一种颜色。
	var labels: Array = []
	for id in _dice_cargo:
		labels.append(placement_panel.state.CARGO_NAMES.get(id, ""))
	dice_stage.configure_cargo(_dice_cargo, labels)


func _configure_ship_starts() -> void:
	for i in boats.size():
		boats[i].configure_route(int(_ship_starts[i]) if i < _ship_starts.size() else 0)
		boats[i].cargo_id = placement_panel.state.cargo_of(i)
		placement_panel.state.set_ship_arrived(i, false)


## 按骰子结果推进三船。steps 与 _dice_cargo 同序（每枚骰子对应一种货物），
## 推进时按货物 id 匹配到实际装该货的船，而非 index 死绑。返回可读报告文本。
## deterministic：不依赖动画完成。
func apply_sailing(steps: Array) -> String:
	var pips_by_cargo := {}
	for d in mini(steps.size(), _dice_cargo.size()):
		pips_by_cargo[_dice_cargo[d]] = int(steps[d])
	var lines: Array[String] = []
	for i in boats.size():
		var pips := int(pips_by_cargo.get(boats[i].cargo_id, 0))
		var result: Dictionary = boats[i].advance_by(pips)
		if result.arrived and not placement_panel.state.arrived[i]:
			placement_panel.state.set_ship_arrived(i, true)
		var label := _ship_label(i)
		if not result.moved:
			lines.append("%s：已到港" % label)
		elif result.crossed:
			lines.append("%s +%d：越过 13 → 到港" % [label, pips])
		else:
			lines.append("%s +%d：%d → %d 号位" % [label, pips, result.from, result.to])
	_refresh_situation()
	return "\n".join(lines)


func _ship_label(ship: int) -> String:
	return placement_panel.state.cargo_name(ship) + "船"

func inspect_dice() -> void:
	if _dice_rolling or character_overlay.visible:
		return
	_show_dice_mode()
	dice_stage.enable_debug_inspect()
func _show_dice_mode() -> void:
	dice_stage.show()
	dice_overlay.show()
	dice_close_button.show()
	_sync_placement()
	for control: Control in [left_pan_button, right_pan_button, personal_bar, turn_bar, select_character_button, situation_panel, sail_button]:
		control.hide()

func _on_close_dice_pressed() -> void:
	if _dice_rolling:
		return
	dice_stage.hide()
	dice_overlay.hide()
	dice_close_button.hide()
	_sync_placement()
	for control: Control in [left_pan_button, right_pan_button, personal_bar, turn_bar, select_character_button, situation_panel, sail_button]:
		control.show()

func _on_dice_overlay_gui_input(event: InputEvent) -> void:
	if dice_stage.handle_debug_input(event):
		dice_overlay.accept_event()

func _on_dice_settled(index: int, value: int) -> void:
	if index >= 0 and index < _dice_results.size():
		_dice_results[index] = value

func _on_all_dice_settled(values: Array) -> void:
	_dice_rolling = false
	dice_close_button.disabled = false
	for i in values.size():
		if i < _dice_results.size():
			_dice_results[i] = int(values[i])
	if _sailing_active:
		_resolve_sailing()
		return
	dice_stage.enable_debug_inspect()


## 骰子落定 → 看清点数 → 收盘推船。船停稳后才进入下一轮或未接通的事件。
func _resolve_sailing() -> void:
	_sailing_active = false
	await get_tree().create_timer(0.8).timeout
	if dice_overlay.visible and not _dice_rolling:
		_on_close_dice_pressed()
	apply_sailing(_dice_results)
	var waited := 0.0
	while waited < 12.0 and _boats_sailing():
		await get_tree().create_timer(0.05).timeout
		waited += 0.05
	_voyage_locked = false
	_continue_after_sailing()

func open_character_roster() -> void:
	if dice_stage.visible:
		return
	for control: Control in [left_pan_button, right_pan_button, personal_bar, turn_bar, select_character_button, situation_panel, sail_button]:
		control.hide()
	character_overlay.open()
	_sync_placement()

func _on_character_confirmed(character_id: String, _display_name: String) -> void:
	selected_character_id = character_id
	for card in character_overlay.cards:
		if card.character_name_en == character_id:
			turn_bar.current_player_index = 0
			turn_bar.set_players(_preview_players(card))
			break


func _sync_active_player() -> void:
	if turn_bar.players.is_empty():
		return
	var card: CharacterCard = turn_bar.players[turn_bar.current_player_index]
	if _displayed_character_id != card.character_name_en:
		if not _displayed_character_id.is_empty():
			_player_resources[_displayed_character_id] = {
				"coins": personal_bar.coins, "remaining": personal_bar.remaining_crew,
				"capacity": personal_bar.crew_capacity, "holdings": personal_bar.holdings.duplicate(),
			}
		var data: Dictionary = _player_resources[card.character_name_en]
		personal_bar.set_character(card)
		personal_bar.set_resources(data.coins, data.remaining, data.capacity)
		personal_bar.set_holdings(data.holdings)
		_displayed_character_id = card.character_name_en
	personal_bar.round_number = turn_bar.voyage_number
	personal_bar.set_turn_context(turn_bar.current_player_index == turn_bar.harbor_master_index, turn_bar.phase != turn_bar.Phase.SETTLEMENT)
	_sync_placement()
	_refresh_situation()


func placement_reason(id: String) -> String:
	var blocked := _placement_block_reason()
	if not blocked.is_empty():
		return blocked
	var reason := placement_panel.state.unavailable_reason(id)
	if not reason.is_empty():
		return reason
	if personal_bar.remaining_crew <= 0:
		return "没有可派遣的伙计"
	var item := placement_panel.state.get_position(id)
	if item.is_empty():
		return "无此岗位"
	if personal_bar.coins < int(item.cost):
		return "金币不足：需要 %d，现有 %d（借款尚未接入）" % [item.cost, personal_bar.coins]
	return ""


func _confirm_placement(id: String, requesting_actor: CharacterCard, phase_key: String) -> void:
	if _placement_committing or turn_bar.players.is_empty():
		return
	if not placement_panel.is_visible_in_tree() or not placement_panel.shade.is_visible_in_tree():
		return
	if id.is_empty() or placement_panel.selected_id != id or not placement_panel.interaction_enabled:
		return
	var actor: CharacterCard = turn_bar.players[turn_bar.current_player_index]
	if requesting_actor != actor or phase_key != _placement_phase_key():
		return
	var reason := placement_reason(id)
	if not reason.is_empty():
		placement_panel.show_error(reason)
		return
	_placement_committing = true
	var item := placement_panel.state.get_position(id)
	var old_coins: int = personal_bar.coins
	var old_crew: int = personal_bar.remaining_crew
	var income := 10 if item.group == "insurance" else 0
	personal_bar.set_resources(old_coins - item.cost + income, old_crew - 1, personal_bar.crew_capacity)
	_player_resources[actor.character_name_en] = {
		"coins": personal_bar.coins, "remaining": personal_bar.remaining_crew,
		"capacity": personal_bar.crew_capacity, "holdings": personal_bar.holdings.duplicate(),
	}
	placement_panel.state.owners[id] = actor
	_acted_this_round[actor.character_name_en] = true
	var result := "%s → %s\n金币 %d → %d · 伙计 %d → %d" % [actor.character_name, item.title, old_coins, personal_bar.coins, old_crew, personal_bar.remaining_crew]
	placement_panel.close()
	var next_index := _scan_actors(turn_bar.current_player_index, false)
	if next_index >= 0:
		_switch_to(next_index)
	else:
		result += _finish_dispatch_round()
	placement_panel.state.changed.emit()
	placement_panel.show_result(result)
	_refresh_situation()
	_update_sail_button()
	_placement_committing = false


func _placement_phase_key() -> String:
	return "%d/%d/%d/%d" % [turn_bar.phase, turn_bar.voyage_number, turn_bar.deployment_round, turn_bar.sailing_number]


func _sync_placement() -> void:
	if turn_bar.players.is_empty():
		return
	var blocked := _placement_block_reason()
	var exposed = not character_overlay.visible and not dice_overlay.visible
	placement_panel.visible = exposed
	placement_panel.set_context(turn_bar.players[turn_bar.current_player_index], blocked.is_empty() and exposed, _placement_phase_key(), blocked)
	_update_sail_button()


func _update_sail_button() -> void:
	if not is_instance_valid(sail_button):
		return
	var ready := _can_start_sailing()
	sail_button.disabled = not ready
	sail_button.tooltip_text = "由港务长投骰航行" if ready else "本轮每人派遣一次后才能投骰"


func _on_sail_button_pressed() -> void:
	if not _can_start_sailing():
		return
	# UI-09/10 未接通前，货物被改掉时用默认装货和起点兜底。
	if placement_panel.state.ships != ["ginseng", "silk", "jade"]:
		set_voyage(["ginseng", "silk", "jade"], [], [3, 3, 3])
	begin_sailing()


func reset_voyage_flow() -> void:
	_acted_this_round.clear()
	_awaiting_sail = false
	_route_configured = false
	_voyage_locked = false
	_sailing_active = false
	_flow_hold = ""


func _crew_remaining(card: CharacterCard) -> int:
	return int(_player_resources.get(card.character_name_en, {}).get("remaining", 0))


func _can_act(card: CharacterCard) -> bool:
	return card != null and not _acted_this_round.has(card.character_name_en) and _crew_remaining(card) > 0


func _scan_actors(origin: int, include_origin: bool) -> int:
	var count = turn_bar.players.size()
	for step in count:
		var index = (origin + step) % count
		if not include_origin and index == origin:
			continue
		if _can_act(turn_bar.players[index]):
			return index
	return -1


func _switch_to(index: int) -> void:
	if index < 0 or index >= turn_bar.players.size():
		return
	if index == turn_bar.current_player_index:
		_sync_placement()
		return
	personal_bar.conceal_stocks()
	turn_bar.set_current_player(index)


func _rounds_needed_before_sail() -> int:
	if turn_bar.players.size() == 3 and turn_bar.sailing_number == 0:
		return 2
	return 1


func _begin_dispatch_round(round_number: int) -> void:
	_acted_this_round.clear()
	_awaiting_sail = false
	_flow_hold = ""
	turn_bar.set_stage(turn_bar.Phase.DISPATCH, turn_bar.voyage_number, round_number, turn_bar.sailing_number)
	var first := _scan_actors(turn_bar.harbor_master_index, true)
	if first >= 0:
		_switch_to(first)
	else:
		_awaiting_sail = true
		_switch_to(turn_bar.harbor_master_index)


func _finish_dispatch_round() -> String:
	if turn_bar.deployment_round < _rounds_needed_before_sail():
		var next_round = turn_bar.deployment_round + 1
		_begin_dispatch_round(next_round)
		return "\n本轮结束，进入第 %d 轮派遣。" % next_round
	if turn_bar.sailing_number == 2 and _role_occupied("pilot_0", "pilot_1"):
		_hold_flow("pilots")
		return "\n本轮派遣结束。引航调整尚未接通，第三次航行先暂停。"
	_awaiting_sail = true
	_switch_to(turn_bar.harbor_master_index)
	return "\n本轮派遣结束，请投骰航行。"


func _role_occupied(first: String, second: String) -> bool:
	var owners: Dictionary = placement_panel.state.owners
	return owners.get(first) != null or owners.get(second) != null


func _ship_stopped_at_13() -> bool:
	for boat in boats:
		if not boat.arrived and boat.route_position == 13:
			return true
	return false


func _hold_flow(kind: String) -> void:
	_awaiting_sail = false
	_flow_hold = kind
	var phase = turn_bar.Phase.SETTLEMENT
	if kind == "pilots":
		phase = turn_bar.Phase.PILOTS
	elif kind == "boarding" or kind == "plunder":
		phase = turn_bar.Phase.PIRATES
	turn_bar.set_stage(phase, turn_bar.voyage_number, turn_bar.deployment_round, turn_bar.sailing_number)


func _placement_block_reason() -> String:
	match _flow_hold:
		"pilots":
			return "引航调整尚未接通"
		"boarding":
			return "海盗登船尚未接通"
		"plunder":
			return "海盗劫掠尚未接通"
		"settlement":
			return "航程结算尚未接通"
	if turn_bar.players.is_empty() or turn_bar.phase != turn_bar.Phase.DISPATCH:
		return "派遣阶段才可打开"
	if character_overlay.visible or dice_overlay.visible or _dice_rolling or _voyage_locked or _sailing_active:
		return "请先关闭其他界面"
	if _awaiting_sail:
		return "本轮已完成，等待投骰"
	var actor: CharacterCard = turn_bar.players[turn_bar.current_player_index]
	if _acted_this_round.has(actor.character_name_en):
		return "本轮已经派遣过"
	if _crew_remaining(actor) <= 0:
		return "没有可派遣的伙计"
	return ""


func _can_start_sailing() -> bool:
	if turn_bar.players.is_empty() or turn_bar.phase != turn_bar.Phase.DISPATCH:
		return false
	if not _awaiting_sail or not _flow_hold.is_empty():
		return false
	if _dice_rolling or _voyage_locked or _sailing_active:
		return false
	return not character_overlay.visible and not dice_overlay.visible


func _enter_sailing() -> bool:
	if not _can_start_sailing():
		return false
	if not _route_configured:
		_configure_ship_starts()
		_route_configured = true
	_awaiting_sail = false
	_voyage_locked = true
	turn_bar.set_stage(turn_bar.Phase.SAILING, turn_bar.voyage_number, turn_bar.deployment_round, turn_bar.sailing_number + 1)
	return true


func _boats_sailing() -> bool:
	for boat in boats:
		if boat.is_sailing():
			return true
	return false


func _continue_after_sailing() -> void:
	_voyage_locked = false
	_sailing_active = false
	if turn_bar.sailing_number >= 3:
		if _ship_stopped_at_13() and _role_occupied("pirate_0", "pirate_1"):
			_hold_flow("plunder")
			placement_panel.show_result("第三次航行结束。海盗劫掠尚未接通，不会结算发钱。")
		else:
			_hold_flow("settlement")
			placement_panel.show_result("第三次航行结束。航程结算尚未接通。")
		_refresh_situation()
		_update_sail_button()
		return
	if turn_bar.sailing_number == 2 and _ship_stopped_at_13() and _role_occupied("pirate_0", "pirate_1"):
		_hold_flow("boarding")
		placement_panel.show_result("第二次航行结束。有船停在 13，海盗登船尚未接通。")
		_refresh_situation()
		_update_sail_button()
		return
	var next_round = turn_bar.deployment_round + 1
	_begin_dispatch_round(next_round)
	placement_panel.show_result("航行结束，进入第 %d 轮派遣。" % next_round)
	_refresh_situation()
	_update_sail_button()


func _preview_players(local_card) -> Array[CharacterCard]:
	var result: Array[CharacterCard] = []
	if local_card != null:
		result.append(local_card)
	for card in character_overlay.cards:
		if card != local_card and result.size() < 5:
			result.append(card)
	return result


func _on_character_roster_closed() -> void:
	_sync_placement()
	for control: Control in [left_pan_button, right_pan_button, personal_bar, turn_bar, select_character_button, situation_panel, sail_button]:
		control.show()
	_refresh_situation()
