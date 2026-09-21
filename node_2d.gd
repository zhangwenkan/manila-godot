extends Node2D

const CharacterCard := preload("res://card/character_card.gd")
const PlacementPanel := preload("res://ui/placement_panel.gd")

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
@onready var dice_stage = $CanvasLayer/DiceStage3D
@onready var dice_overlay: ColorRect = $CanvasLayer/DiceOverlay
@onready var dice_close_button: Button = $CanvasLayer/DiceCloseButton
var placement_panel: PlacementPanel

var _dice_rolling := false
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

	for i in dice_stage.get_dice_count():
		dice_stage.set_value(i, int(_dice_results[i]))
	dice_stage.dice_settled.connect(_on_dice_settled)
	dice_stage.all_settled.connect(_on_all_dice_settled)
	character_overlay.character_confirmed.connect(_on_character_confirmed)
	character_overlay.closed.connect(_on_character_roster_closed)
	turn_bar.changed.connect(_sync_active_player)
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
	for control: Control in [left_pan_button, right_pan_button, personal_bar, turn_bar]:
		control.hide()

func _on_close_dice_pressed() -> void:
	if _dice_rolling:
		return
	dice_stage.hide()
	dice_overlay.hide()
	dice_close_button.hide()
	_sync_placement()
	for control: Control in [left_pan_button, right_pan_button, personal_bar, turn_bar, select_character_button]:
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
	dice_stage.enable_debug_inspect()

func open_character_roster() -> void:
	if dice_stage.visible:
		return
	for control: Control in [left_pan_button, right_pan_button, personal_bar, turn_bar, select_character_button]:
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


func placement_reason(id: String) -> String:
	if turn_bar.players.is_empty() or turn_bar.phase != turn_bar.Phase.DISPATCH:
		return "派遣阶段才可确认"
	if character_overlay.visible or dice_overlay.visible:
		return "请先关闭其他界面"
	var reason := placement_panel.state.unavailable_reason(id)
	if not reason.is_empty():
		return reason
	if personal_bar.remaining_crew <= 0:
		return "没有可派遣的伙计"
	var item := placement_panel.state.get_position(id)
	if personal_bar.coins < item.cost:
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
	var result := "%s → %s\n金币 %d → %d · 伙计 %d → %d" % [actor.character_name, item.title, old_coins, personal_bar.coins, old_crew, personal_bar.remaining_crew]
	placement_panel.close()
	var next_index := -1
	for step in range(1, turn_bar.players.size() + 1):
		var index: int = (turn_bar.current_player_index + step) % turn_bar.players.size()
		var next_actor: CharacterCard = turn_bar.players[index]
		if _player_resources[next_actor.character_name_en].remaining > 0:
			next_index = index
			break
	if next_index >= 0:
		personal_bar.conceal_stocks()
		turn_bar.set_current_player(next_index)
	else:
		result += "\n派遣演示结束：所有伙计已派出"
		_sync_placement()
	placement_panel.state.changed.emit()
	placement_panel.show_result(result)
	_placement_committing = false


func _placement_phase_key() -> String:
	return "%d/%d/%d/%d" % [turn_bar.phase, turn_bar.voyage_number, turn_bar.deployment_round, turn_bar.sailing_number]


func _sync_placement() -> void:
	if turn_bar.players.is_empty():
		return
	var enabled: bool = turn_bar.phase == turn_bar.Phase.DISPATCH and not character_overlay.visible and not dice_overlay.visible
	placement_panel.visible = not character_overlay.visible and not dice_overlay.visible
	placement_panel.set_context(turn_bar.players[turn_bar.current_player_index], enabled, _placement_phase_key())


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
	for control: Control in [left_pan_button, right_pan_button, personal_bar, turn_bar, select_character_button]:
		control.show()
