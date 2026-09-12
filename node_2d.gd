extends Node2D

@export var layout_mode := true
@export var layout_view_size := Vector2(2340.0, 1080.0)
@export var world_size := Vector2(6144.0, 1152.0)

@onready var boats: Array[CharacterBody2D] = [$BoatTop, $BoatMiddle, $BoatBottom]
@onready var camera: Camera2D = $Camera2D
@onready var roll_button: Button = $CanvasLayer/RollButton
@onready var debug_dice_button: Button = $CanvasLayer/DebugDiceButton
@onready var left_pan_button: Button = $CanvasLayer/LeftPanButton
@onready var right_pan_button: Button = $CanvasLayer/RightPanButton
@onready var select_character_button: Button = $CanvasLayer/SelectCharacterButton
@onready var character_overlay = $CanvasLayer/CharacterOverlay
@onready var dice_stage = $CanvasLayer/DiceStage3D
@onready var dice_overlay: ColorRect = $CanvasLayer/DiceOverlay
@onready var dice_close_button: Button = $CanvasLayer/DiceCloseButton

var _dice_rolling := false
var _current_stakes := [0, 0, 0]
var _dice_results := [1, 1, 1]
var selected_character_id := ""
var _camera_target_x := 0.0
var _camera_target_y := 0.0
var _camera_velocity := 0.0
var _is_manual_camera := false
var _button_press_time := {}

func _ready() -> void:
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

func _on_roll_button_pressed() -> void:
	if _dice_rolling:
		return
	_dice_rolling = true
	_show_dice_mode()
	roll_button.disabled = true
	dice_close_button.disabled = true
	dice_stage.throw_all()

func _on_debug_dice_button_pressed() -> void:
	if _dice_rolling:
		return
	_show_dice_mode()
	dice_stage.enable_debug_inspect()

func _show_dice_mode() -> void:
	dice_stage.show()
	dice_overlay.show()
	dice_close_button.show()
	for control: Control in [left_pan_button, right_pan_button, select_character_button, debug_dice_button]:
		control.hide()

func _on_close_dice_pressed() -> void:
	if _dice_rolling:
		return
	dice_stage.hide()
	dice_overlay.hide()
	dice_close_button.hide()
	for control: Control in [left_pan_button, right_pan_button, select_character_button, debug_dice_button]:
		control.show()

func _on_dice_overlay_gui_input(event: InputEvent) -> void:
	if dice_stage.handle_debug_input(event):
		dice_overlay.accept_event()

func _on_dice_settled(index: int, value: int) -> void:
	if index >= 0 and index < _dice_results.size():
		_dice_results[index] = value

func _on_all_dice_settled(values: Array) -> void:
	_dice_rolling = false
	roll_button.disabled = false
	dice_close_button.disabled = false
	for i in values.size():
		if i < _dice_results.size():
			_dice_results[i] = int(values[i])
	dice_stage.enable_debug_inspect()

func _on_select_character_pressed() -> void:
	for control: Control in [left_pan_button, right_pan_button, select_character_button, debug_dice_button, roll_button]:
		control.hide()
	character_overlay.open()

func _on_character_confirmed(character_id: String, display_name: String) -> void:
	selected_character_id = character_id
	select_character_button.text = "角色: " + display_name

func _on_character_roster_closed() -> void:
	for control: Control in [left_pan_button, right_pan_button, select_character_button, debug_dice_button, roll_button]:
		control.show()
	select_character_button.grab_focus()
