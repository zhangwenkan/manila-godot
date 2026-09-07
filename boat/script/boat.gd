extends CharacterBody2D

@export var move_duration := 4.0
@export var screen_width := 2340.0
@export var total_screens := 2
@export var water_bob_amount := 1.4
@export var water_bob_speed := 1.15
@export var water_roll_degrees := 0.28
@export var sailing_motion_multiplier := 1.2

var _move_tween: Tween
var _is_sailing := false
var _is_auto_moving := false
var _water_motion_time := 0.0
var _visual_base_position := Vector2.ZERO

@onready var visual_root: Node2D = $VisualRoot
@onready var sprite: Sprite2D = $VisualRoot/Sprite2D

func _ready() -> void:
	visible = true
	_visual_base_position = visual_root.position

func _process(delta: float) -> void:
	_water_motion_time += delta
	_update_water_motion()

func is_sailing() -> bool:
	return _is_sailing

func move_to_stake(stake_number: int) -> void:
	if _move_tween:
		_move_tween.kill()

	var stake_positions := {
		1: 220, 2: 820, 3: 1420, 4: 2020, 5: 2620,
		6: 3220, 7: 3820, 8: 4420, 9: 5020, 10: 5620
	}

	if not stake_positions.has(stake_number):
		return

	var target_x: float = stake_positions[stake_number]

	_is_sailing = true
	_is_auto_moving = true
	visible = true

	var distance: float = abs(target_x - global_position.x)
	var duration: float = distance / 300.0

	_move_tween = create_tween()
	_move_tween.tween_property(
		self,
		"global_position:x",
		target_x,
		duration
	)
	_move_tween.finished.connect(_on_move_finished)

func _on_move_finished() -> void:
	_is_sailing = false
	_is_auto_moving = false

func _update_water_motion() -> void:
	var motion_multiplier := sailing_motion_multiplier if _is_sailing else 1.0
	var bob := (
		sin(_water_motion_time * water_bob_speed) +
		sin(_water_motion_time * water_bob_speed * 0.53 + 1.7) * 0.35
	) * water_bob_amount * motion_multiplier
	var roll := sin(_water_motion_time * water_bob_speed * 0.72 + 0.4) * water_roll_degrees * motion_multiplier

	visual_root.position = _visual_base_position + Vector2(0.0, bob)
	visual_root.rotation_degrees = roll
