extends CharacterBody2D

@export var water_bob_amount := 1.4
@export var water_bob_speed := 1.15
@export var water_roll_degrees := 0.28
@export var sailing_motion_multiplier := 1.2

## 航线坐标：临时等间距，后续做「0-13 号木桩」时再对齐盘面。
@export var route_origin_x := 300.0   # 0 号位的世界 x
@export var route_step_x := 400.0     # 每格间距（像素）
@export var dock_x := 5850.0          # 越过 13 到港后的停泊 x
@export var sail_speed := 300.0       # 航行动画速度（像素/秒）

const ROUTE_END := 13   # 越过 13 即到港；恰好停 13 仍在航线（海盗特例）

var route_position := 0
var arrived := false
var cargo_id := ""   # 本航程该船所装货物；骰子按货物匹配到船

var _move_tween: Tween
var _is_sailing := false
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

## 号位 → 世界 x。越界（>13）不用此函数，直接停泊 dock_x。
func route_x(position: int) -> float:
	return route_origin_x + position * route_step_x

## 设定起点（0-5），立即定位到该号位，不做动画。
func configure_route(start_position: int) -> void:
	if _move_tween:
		_move_tween.kill()
		_move_tween = null
	route_position = clampi(start_position, 0, ROUTE_END)
	arrived = false
	_is_sailing = false
	global_position.x = route_x(route_position)

## 沿航线前进 steps 格。越过 13 立即到港；恰好 13 仍留在航线。
## 返回 {from, to, arrived, moved, crossed}。已到港或 steps<=0 时 moved=false。
func advance_by(steps: int) -> Dictionary:
	var from_pos := route_position
	if arrived or steps <= 0:
		return {"from": from_pos, "to": from_pos, "arrived": arrived, "moved": false, "crossed": false}
	var target := from_pos + steps
	var crossed := target > ROUTE_END
	route_position = target
	if crossed:
		arrived = true
		_animate_to(dock_x)
	else:
		_animate_to(route_x(route_position))
	return {"from": from_pos, "to": route_position, "arrived": arrived, "moved": true, "crossed": crossed}

func _animate_to(target_x: float) -> void:
	if _move_tween:
		_move_tween.kill()
	_is_sailing = true
	visible = true
	var distance: float = absf(target_x - global_position.x)
	var duration: float = maxf(0.4, distance / maxf(sail_speed, 1.0))
	_move_tween = create_tween()
	_move_tween.tween_property(self, "global_position:x", target_x, duration)
	_move_tween.finished.connect(_on_move_finished)

func _on_move_finished() -> void:
	_is_sailing = false

func _update_water_motion() -> void:
	var motion_multiplier := sailing_motion_multiplier if _is_sailing else 1.0
	var bob := (
		sin(_water_motion_time * water_bob_speed) +
		sin(_water_motion_time * water_bob_speed * 0.53 + 1.7) * 0.35
	) * water_bob_amount * motion_multiplier
	var roll := sin(_water_motion_time * water_bob_speed * 0.72 + 0.4) * water_roll_degrees * motion_multiplier

	visual_root.position = _visual_base_position + Vector2(0.0, bob)
	visual_root.rotation_degrees = roll
