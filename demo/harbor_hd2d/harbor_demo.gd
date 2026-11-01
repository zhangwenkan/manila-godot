extends Control

const State := preload("res://ui/placement_state.gd")
const World := preload("res://demo/harbor_hd2d/harbor_world.gd")
const Hud := preload("res://demo/harbor_hd2d/harbor_hud.gd")
const Layout := preload("res://demo/harbor_hd2d/harbor_layout.gd")

var state := State.new()
var world: Node3D
var hud: Control
var display: SubViewportContainer
var viewport: SubViewport
var actors: Array[Dictionary] = []
var actor_index := 0
var selected_id := ""
var steps: Array = [1, 4, 7]
var round_number := 1
var auto_closeup := true
var busy := false
var notice := "点击圆形岗位查看费用；两位角色可切换体验派遣。"
var applied_sailings := 0
var _playback: Tween
var _rng := RandomNumberGenerator.new()
var _inspection_dragging := false


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_rng.randomize()
	display = SubViewportContainer.new()
	display.name = "PixelHarbor"
	display.stretch = true
	display.stretch_shrink = 2
	display.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	display.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(display)
	viewport = SubViewport.new()
	viewport.name = "WorldViewport"
	viewport.own_world_3d = true
	viewport.handle_input_locally = false
	viewport.physics_object_picking = false
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	viewport.msaa_3d = Viewport.MSAA_DISABLED
	display.add_child(viewport)
	world = World.new()
	world.name = "HarborWorld"
	viewport.add_child(world)
	hud = Hud.new()
	hud.name = "ClearHud"
	add_child(hud)
	_new_actors()
	hud.setup(self)
	resized.connect(_layout)
	_layout()
	world.set_positions(steps)
	hud.refresh()


func _layout() -> void:
	var layout := Layout.describe(size)
	var rect: Rect2 = layout.world_rect
	display.position = rect.position * layout.factor
	display.size = rect.size * layout.factor
	if world != null:
		world.overview_size = layout.overview_size


func _new_actors() -> void:
	actors = [
		{"name": "拉坎", "cash": 30, "crew": 5, "holdings": ["ginseng", "ginseng", "jade"], "color": Color("e8bc62")},
		{"name": "卡门", "cash": 30, "crew": 5, "holdings": ["silk", "silk", "ginseng"], "color": Color("cc8397")},
	]


func reset_demo(scattered := false) -> void:
	if busy:
		return
	end_inspection()
	hud.cover_hand()
	state.set_voyage_cargo(["ginseng", "silk", "jade"])
	_new_actors()
	actor_index = 0
	selected_id = ""
	steps = [0, 7, 13] if scattered else [1, 4, 7]
	round_number = 1
	applied_sailings = 0
	world.camera_blend = 0.0
	world.clear_owners()
	world.set_positions(steps)
	notice = "分散构图：0 / 7 / 13；恰好 13 未到港，超过 13 才到港。" if scattered else "点击圆形岗位查看费用；两位角色可切换体验派遣。"
	hud.dice_panel.hide()
	hud.refresh()


func switch_actor(index: int) -> void:
	if busy or world.inspecting or index < 0 or index >= actors.size():
		return
	hud.cover_hand()
	actor_index = index
	selected_id = ""
	hud.refresh()


func placement_reason(id: String) -> String:
	if world.inspecting:
		return "观察吊机中，返回全局后派遣"
	if busy:
		return "航行演出中，返回全局后派遣"
	var reason := state.unavailable_reason(id)
	if not reason.is_empty():
		return reason
	if actors[actor_index].crew <= 0:
		return "没有可派遣的伙计"
	if actors[actor_index].cash < state.get_position(id).cost:
		return "现金不足"
	return ""


func select_slot(id: String) -> void:
	if busy or world.inspecting or state.get_position(id).is_empty():
		return
	selected_id = "" if selected_id == id else id
	hud.refresh()


func confirm_selection() -> bool:
	if selected_id.is_empty() or not placement_reason(selected_id).is_empty():
		return false
	var item := state.get_position(selected_id)
	var actor := actors[actor_index]
	actor.cash -= item.cost
	actor.crew -= 1
	if item.group == "insurance":
		actor.cash += 10
	state.owners[selected_id] = actor
	world.place_crew(selected_id, actor.color)
	notice = "%s → %s · %s；已派驻 1 名伙计。" % [actor.name, item.title, "领取 10 比索" if item.group == "insurance" else "支付 %d 比索" % item.cost]
	selected_id = ""
	state.changed.emit()
	hud.refresh()
	return true


func roll_sailing(forced_values: Array = []) -> bool:
	if busy or world.inspecting or state.arrived.all(func(value: bool): return value):
		return false
	var values: Array = forced_values.duplicate()
	if values.is_empty():
		for i in 3:
			values.append(_rng.randi_range(1, 6))
	if values.size() != 3:
		return false
	for value in values:
		if not (value is int) or value < 1 or value > 6:
			return false
	busy = true
	selected_id = ""
	var focus := -1
	# Commit the result exactly once; the tween below only presents this snapshot.
	for i in 3:
		if state.arrived[i]:
			continue
		steps[i] += values[i]
		state.set_ship_arrived(i, steps[i] > 13)
		if focus < 0 or (i == 1 and not state.arrived[i]):
			focus = i
	applied_sailings += 1
	world.focus_ship = maxi(focus, 0)
	world.sailing = true
	notice = "骰子已确定：人参 +%d / 丝绸 +%d / 玉石 +%d。" % values
	hud.show_dice(values, "人参 +%d     丝绸 +%d     玉石 +%d" % values)
	hud.refresh()
	_playback = create_tween()
	_playback.tween_interval(1.0)
	if auto_closeup:
		_playback.tween_property(world, "camera_blend", 1.0, 1.05).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN_OUT)
	_playback.tween_callback(func(): hud.dice_panel.hide())
	for i in 3:
		if i > 0:
			_playback.parallel()
		_playback.tween_property(world.boats[i], "position", world.route_point(i, steps[i]), 3.8).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_playback.tween_interval(0.5)
	if auto_closeup:
		_playback.tween_property(world, "camera_blend", 0.0, 1.05).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN_OUT)
	_playback.tween_callback(_finish_sailing)
	return true


func skip_sailing() -> void:
	if not busy:
		return
	if _playback != null:
		_playback.kill()
	_finish_sailing()


func _finish_sailing() -> void:
	if not busy:
		return
	world.set_positions(steps)
	world.camera_blend = 0.0
	world.sailing = false
	busy = false
	_playback = null
	round_number += 1
	notice = "已返回全局 · 三船位置已同步。可继续派遣，或重新开始体验。"
	hud.dice_panel.hide()
	hud.refresh()


func toggle_pixel() -> void:
	display.stretch_shrink = 1 if display.stretch_shrink == 2 else 2


func begin_inspection() -> bool:
	if busy or not world.begin_inspection():
		return false
	_inspection_dragging = false
	var focused := get_viewport().gui_get_focus_owner()
	if focused != null:
		focused.release_focus()
	hud.tools_panel.hide()
	hud.cover_hand()
	hud.refresh()
	hud._process(0)
	return true


func end_inspection() -> void:
	_inspection_dragging = false
	if not world.inspecting:
		return
	world.end_inspection()
	var focused := get_viewport().gui_get_focus_owner()
	if focused != null:
		focused.release_focus()
	hud.refresh()
	hud._process(0)


func toggle_inspection() -> void:
	if world.inspecting:
		end_inspection()
	else:
		begin_inspection()


func _inspection_contains(point: Vector2) -> bool:
	var local := display.get_global_transform_with_canvas().affine_inverse() * point
	if not Rect2(Vector2.ZERO, display.size).has_point(local):
		return false
	var button: Button = hud.inspect_button
	var on_button := button.get_global_transform_with_canvas().affine_inverse() * point
	return not Rect2(Vector2.ZERO, button.size).has_point(on_button)


func _inspection_input(event: InputEvent) -> void:
	if event is InputEventKey:
		if event.keycode == KEY_ESCAPE:
			get_viewport().set_input_as_handled()
			if event.pressed and not event.echo:
				end_inspection()
		elif event.keycode in [KEY_SPACE, KEY_ENTER, KEY_KP_ENTER]:
			get_viewport().set_input_as_handled()
		return
	if event is InputEventMouseButton:
		# Releases outside the rendered area must still finish a drag.
		if event.button_index == MOUSE_BUTTON_RIGHT and not event.pressed:
			var was_dragging := _inspection_dragging
			_inspection_dragging = false
			if was_dragging:
				get_viewport().set_input_as_handled()
			return
		if not _inspection_contains(event.position):
			return
		if event.button_index == MOUSE_BUTTON_RIGHT:
			_inspection_dragging = event.pressed
			get_viewport().set_input_as_handled()
		elif event.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
			if event.pressed:
				world.zoom_inspection((1.0 if event.button_index == MOUSE_BUTTON_WHEEL_UP else -1.0) * event.factor)
			get_viewport().set_input_as_handled()
	elif event is InputEventMouseMotion and _inspection_dragging:
		if not _inspection_contains(event.position) or not (event.button_mask & MOUSE_BUTTON_MASK_RIGHT):
			_inspection_dragging = false
			return
		var inverse := display.get_global_transform_with_canvas().affine_inverse()
		var delta: Vector2 = (inverse * event.relative - inverse * Vector2.ZERO) / display.size
		world.orbit_inspection(delta)
		get_viewport().set_input_as_handled()


func _notification(what: int) -> void:
	if what in [NOTIFICATION_APPLICATION_FOCUS_OUT, NOTIFICATION_WM_WINDOW_FOCUS_OUT]:
		_inspection_dragging = false


func _input(event: InputEvent) -> void:
	if world != null and world.inspecting:
		_inspection_input(event)
		return
	if event is InputEventKey and event.keycode == KEY_SPACE:
		# Reserve Space before GUI focus can turn it into a button confirmation.
		get_viewport().set_input_as_handled()
		if event.pressed and not event.echo:
			roll_sailing()


func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		if busy:
			skip_sailing()
		else:
			selected_id = ""
			hud.refresh()
		get_viewport().set_input_as_handled()
