extends SceneTree

const DEMO := preload("res://demo/harbor_hd2d/harbor_demo.tscn")
var demo: Control
var failures: Array[String] = []
var checks := 0
var preview := false
var output_dir := "user://harbor_demo_preview"
var _finished := false
var _logic_complete := false
var _input_complete := false
var _tour_complete := false


func _initialize() -> void:
	preview = "--preview" in OS.get_cmdline_user_args()
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):
			output_dir = arg.trim_prefix("--output=")
	_run.call_deferred()


func _run() -> void:
	create_timer(60.0).timeout.connect(func():
		if not _finished:
			failures.append("60 second watchdog expired")
			_finish())
	if preview and DisplayServer.get_name() == "headless":
		failures.append("GUI preview requires a real rendering display")
		_finish()
		return
	root.content_scale_size = Vector2i(2048, 1152)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.size = Vector2i(1440, 810)
	demo = DEMO.instantiate()
	root.add_child(demo)
	await process_frame
	await process_frame
	_check(demo.world != null and demo.hud != null, "world and HUD initialize")
	if demo.world == null or demo.hud == null:
		_finish()
		return
	_logic_checks()
	_check(_logic_complete, "logic checks complete without interruption")
	await _input_checks()
	_check(_input_complete, "input checks complete without interruption")
	if preview:
		await _tour()
		_check(_tour_complete, "render tour completes without interruption")
	_finish()


func _logic_checks() -> void:
	_check(demo.state.positions.size() == 21, "21 stable positions")
	_check(demo.world.anchors.size() == 21, "every position has a world anchor")
	_check_building_integration()
	_check_insurance_integration()
	demo.select_slot("ship_0_0")
	_check(demo.actors[0].cash == 30 and demo.actors[0].crew == 5, "selection is free")
	_check(demo.confirm_selection(), "first seat accepted")
	_check(demo.actors[0].cash == 29 and demo.actors[0].crew == 4, "charge once")
	_check(not demo.confirm_selection(), "duplicate confirmation rejected")
	_check(not demo.placement_reason("ship_0_2").is_empty(), "cheaper seat required")
	_check(not demo.placement_reason("pirate_1").is_empty(), "pirate captain first")
	demo.switch_actor(1)
	_check(demo.actors[1].cash == 30 and demo.actors[1].crew == 5, "independent actor resources")
	_check(demo.hud.person.text == "卡门" and "丝绸" in demo.hud.holdings.text, "whole HUD switches actor")
	demo.select_slot("insurance_0")
	_check(demo.confirm_selection(), "insurance accepted")
	_check(demo.actors[1].cash == 40 and demo.actors[1].crew == 4, "insurance pays ten")
	demo.actors[1].cash = 0
	_check(demo.placement_reason("ship_1_0") == "现金不足", "insufficient cash")
	demo.actors[1].crew = 0
	_check(demo.placement_reason("ship_1_0") == "没有可派遣的伙计", "no crew")
	demo.reset_demo()
	_check(demo.state.owners.is_empty() and demo.world.markers.is_empty(), "reset clears placement")
	_check(demo.actors[0].cash == 30 and demo.actor_index == 0, "reset restores actors")
	demo.steps = [12, 13, 14]
	demo.state.set_ship_arrived(2, true)
	demo.world.set_positions(demo.steps)
	_check(not demo.roll_sailing([0, 1, 1]), "invalid dice rejected")
	_check(demo.roll_sailing([1, 1, 6]), "sailing starts")
	_check(not demo.roll_sailing([1, 1, 1]), "duplicate sailing rejected")
	_check(demo.steps == [13, 14, 14], "arrived boats do not advance")
	_check(not demo.state.arrived[0] and demo.state.arrived[1], "arrival is strictly beyond thirteen")
	_check(not demo.confirm_selection(), "dispatch locked during playback")
	demo.skip_sailing()
	demo.skip_sailing()
	_check(demo.applied_sailings == 1 and demo.steps == [13, 14, 14], "skip never reapplies results")
	_check(not demo.busy and demo.world.camera_blend == 0.0, "skip restores overview")
	_check(demo.placement_reason("ship_1_0") == "船已到港，不能再派人", "arrived ship rejects dispatch")
	demo.auto_closeup = false
	_check(demo.roll_sailing([1, 1, 1]), "overview-only sailing starts")
	demo.skip_sailing()
	_check(demo.applied_sailings == 2 and demo.world.camera_blend == 0.0, "overview mode finishes once")
	_check(not demo.roll_sailing([1, 1, 1]), "all arrived disables more sailing")
	demo.reset_demo(true)
	_check(demo.steps == [0, 7, 13], "scattered composition preset")
	demo.world._update_camera()
	demo.hud._process(0)
	_check_projection()
	demo.world.set_positions([14, 14, 14])
	for i in 3:
		var stopped: Vector3 = demo.world.route_point(i, 14)
		_check(stopped.z < demo.world.route_point(i, 13).z, "arrival still advances toward dock: %d" % i)
		var bow_z := INF
		for mesh: MeshInstance3D in demo.world.boats[i].find_children("*", "MeshInstance3D", true, false):
			var bounds: AABB = mesh.global_transform * mesh.get_aabb()
			bow_z = minf(bow_z, bounds.position.z)
		_check(bow_z > -13.9, "arrived boat remains outside transverse dock: %d" % i)
	demo.reset_demo()
	demo.auto_closeup = true
	_logic_complete = true


func _check_building_integration() -> void:
	var expected := {
		"harbor_0": Vector3(-6, 0.72, -15.1), "harbor_1": Vector3(0, 0.72, -15.1), "harbor_2": Vector3(6, 0.72, -15.1),
		"shipyard_0": Vector3(14.9, 0.8, 2.8), "shipyard_1": Vector3(16.8, 0.8, 6.6), "shipyard_2": Vector3(24.3, 0.8, 6.6),
		"pirate_0": Vector3(-16.1, 0.69, 1.8), "pirate_1": Vector3(-13.1, 0.69, 1.8),
		"pilot_0": Vector3(-20, 0.70, 9.8), "pilot_1": Vector3(-15.8, 0.70, 9.8),
		"insurance_0": Vector3(15.1, 0.72, -8.3),
	}
	for ship in 3:
		for seat in (4 if ship == 2 else 3):
			var id := "ship_%d_%d" % [ship, seat]
			expected[id] = Vector3(-0.90 + (seat % 2) * 1.80, 0.84, -0.65 + (seat / 2) * 2.0)
			_check(demo.world.anchors[id].position.is_equal_approx(expected[id]), "building changes preserve deck anchor: " + id)
		for step in range(15):
			var point := Vector3(-6.0 + ship * 6.0, 0, -10.5 if step > 13 else 11.5 - step * 1.68)
			_check(demo.world.route_point(ship, step).is_equal_approx(point), "building changes preserve route")
	for id: String in expected:
		_check(demo.world.anchors.has(id), "building changes preserve slot ID: " + id)
		if not id.begins_with("ship_"):
			_check(demo.world.slot_position(id).is_equal_approx(expected[id]), "building changes preserve shore anchor: " + id)


func _check_insurance_integration() -> void:
	var models: Array[Node] = demo.world.find_children("InsuranceBlender", "Node3D", true, false)
	_check(models.size() == 1, "one imported insurance asset in initialized world")
	if models.size() != 1:
		return
	var model: Node3D = models[0]
	_check(model.get_parent() == demo.world, "insurance stays outside atlas batching root")
	_check(model.scene_file_path == "res://demo/harbor_hd2d/art/insurance_rebuild_r2/insurance_rebuild_r2_1.glb", "world loads R2.1 exported GLB")
	var materials: Dictionary = {}
	for instance: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		_check(instance.material_override == null, "imported material surfaces survive initialization")
		for surface in instance.mesh.get_surface_count():
			var material := instance.get_active_material(surface)
			_check(material != null, "imported surface has material")
			if material != null:
				materials[material.resource_name] = true
				_check(material is StandardMaterial3D and material.texture_filter == BaseMaterial3D.TEXTURE_FILTER_NEAREST, "R2.1 surfaces keep nearest sampling")
	_check(materials.size() == 20, "twenty R2.1 insurance materials survive global batching")
	_check(demo.world.boats.size() == 3, "decorative tug is not a gameplay boat")
	_check(demo.world.find_children("*", "Camera3D", true, false).size() == 1, "asset adds no camera")
	_check(demo.world.find_children("*", "Light3D", true, false).size() == 1, "asset adds no light")


func _check_insurance_framing() -> void:
	var model: Node3D = demo.world.get_node("InsuranceBlender")
	var display_rect: Rect2 = demo.hud._layout_data.world_rect
	var fits := true
	for instance: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		for point in instance.mesh.get_faces():
			fits = fits and display_rect.has_point(demo.hud.project(instance.global_transform * point))
	_check(fits, "complete insurance geometry fits unchanged overview camera")


func _check_projection() -> void:
	var board: Rect2 = demo.hud._layout_data.safe_board
	for id: String in demo.world.anchors:
		_check(board.has_point(demo.hud.project(demo.world.slot_position(id))), "anchor in usable board: " + id)
	var ids: Array = demo.hud.buttons.keys()
	for i in ids.size():
		for j in range(i + 1, ids.size()):
			var a: Button = demo.hud.buttons[ids[i]]
			var b: Button = demo.hud.buttons[ids[j]]
			_check(not a.get_rect().intersects(b.get_rect()), "non-overlap: %s / %s" % [ids[i], ids[j]])


func _input_checks() -> void:
	demo.reset_demo(true)
	await process_frame
	await process_frame
	for id: String in demo.hud.buttons:
		await _click(demo.hud.buttons[id])
		if demo.selected_id != id:
			var button: Button = demo.hud.buttons[id]
			print("HARBOR_INPUT_DIAGNOSTIC: expected=%s actual=%s rect=%s mouse=%s hovered=%s disabled=%s" % [id, demo.selected_id, button.get_global_rect(), root.get_mouse_position(), button.is_hovered(), button.disabled])
		_check(demo.selected_id == id, "mouse hit reaches world slot: " + id)
	_check(demo.actors[0].cash == 30 and demo.actors[0].crew == 5, "mouse selections never charge")
	await _click(demo.hud.buttons["ship_0_0"])
	await _click(demo.hud.confirm)
	_check(demo.actors[0].cash == 29 and demo.actors[0].crew == 4, "mouse confirmation charges once")
	await _click(demo.hud.actor_buttons[1])
	_check(demo.actor_index == 1 and demo.hud.person.text == "卡门", "mouse switches whole actor HUD")
	await _click(demo.hud.buttons["insurance_0"])
	await _click(demo.hud.confirm)
	_check(demo.actors[1].cash == 40 and demo.actors[1].crew == 4, "mouse insurance confirmation")
	var point: Vector3 = demo.world.slot_position("insurance_0")
	var projected: Vector2 = demo.hud.project(point)
	_check(not demo.hud.tools_panel.visible, "debug tools initially folded")
	await _click(demo.hud.tools_toggle)
	_check(demo.hud.tools_panel.visible, "debug tools expand by input")
	await _click(demo.hud.pixel_toggle)
	await process_frame
	await process_frame
	_check(demo.display.stretch_shrink == 1, "pixel button enables native resolution")
	_check(projected.distance_to(demo.hud.project(point)) < 1.0, "pixel toggle preserves anchor projection")
	_check_projection()
	await _click(demo.hud.buttons["harbor_0"])
	_check(demo.selected_id == "harbor_0", "native resolution mouse hit")
	await _click(demo.hud.pixel_toggle)
	await process_frame
	await process_frame
	_check(demo.display.stretch_shrink == 2, "pixel button restores pixel rendering")
	await _click(demo.hud.tools_toggle)
	await _click(demo.hud.roll)
	_check(demo.busy and demo.applied_sailings == 1, "mouse starts sailing once")
	await _click(demo.hud.skip)
	_check(not demo.busy and demo.applied_sailings == 1, "mouse skip restores overview without reapplying")
	demo.reset_demo()
	demo.auto_closeup = true
	await _click(demo.hud.buttons["ship_0_0"])
	demo.hud.confirm.grab_focus()
	await _key(KEY_SPACE)
	_check(demo.busy and demo.applied_sailings == 1, "Space starts sailing despite confirm focus")
	_check(demo.actors[0].cash == 30 and demo.actors[0].crew == 5, "Space never activates focused confirmation")
	await _key(KEY_SPACE)
	_check(demo.applied_sailings == 1, "repeated Space during playback never reapplies")
	await _key(KEY_ESCAPE)
	_check(not demo.busy and demo.world.camera_blend == 0.0, "Escape skips sailing")
	demo.reset_demo()
	await _click(demo.hud.buttons["ship_0_0"])
	await _key(KEY_ESCAPE)
	_check(demo.selected_id.is_empty(), "Escape cancels a focused slot selection")
	await _hand_checks()
	await _inspection_checks()
	await _aspect_checks()
	_input_complete = true


func _hand_checks() -> void:
	demo.reset_demo()
	var hand: Control = demo.hud.hand
	_check(hand.cards.size() == 3 and hand.cargo_ids == demo.actors[0].holdings, "fan uses only actual structured holdings")
	_check(not hand.revealed.any(func(value: bool): return value), "stock cards start covered")
	var selected_before: String = demo.selected_id
	# Left edge is exposed even where rotated cards overlap; click via actual transform.
	await _click_at(hand.cards[0].get_global_transform_with_canvas() * Vector2(24, 70))
	_check(hand.revealed[0] and not hand.revealed[1] and not hand.revealed[2], "rotated exposed card receives click")
	_check(hand.get_child(hand.get_child_count() - 1) == hand.cards[0], "raised card has matching visual and input order")
	_check(demo.selected_id == selected_before and demo.actors[0].cash == 30, "flipping never dispatches or charges")
	hand._process(1.0)
	_check(hand.cards[0].position.y < hand._origins[0].y - 30.0, "hover or focus lifts card")
	for focus_notification in [Control.NOTIFICATION_APPLICATION_FOCUS_OUT, Control.NOTIFICATION_WM_WINDOW_FOCUS_OUT]:
		if not hand.revealed[0]:
			hand._toggle_card(0)
		hand.cards[0].grab_focus()
		# Traverse children as the window does, not just a direct notification call.
		hand.propagate_notification(focus_notification)
		_check(not hand.revealed.any(func(value: bool): return value), "focus loss covers all cards immediately")
		_check(hand._raised == -1 and not hand.cards[0].has_focus(), "focus loss clears raised and focused card immediately")
		for face: TextureRect in hand._faces:
			_check(face.texture == hand.BACK, "focus loss replaces face texture before deferred work")
		await process_frame
		await process_frame
		for i in hand.cards.size():
			_check(hand.get_child(i) == hand.cards[i], "focus loss restores sibling order after traversal")
	hand.cards[1].grab_focus()
	await _key(KEY_ENTER)
	_check(hand.revealed[1], "keyboard activation flips focused stock")
	await _click(demo.hud.actor_buttons[1])
	_check(hand.cargo_ids == ["silk", "silk", "ginseng"] and not hand.revealed.any(func(value: bool): return value), "switch swaps and covers entire hand")
	hand._toggle_card(0)
	demo.reset_demo()
	_check(not hand.revealed.any(func(value: bool): return value), "reset covers hand")
	hand._toggle_card(0)
	demo.roll_sailing([1, 1, 1])
	_check(hand.collapsed and not hand.visible and not hand.revealed.any(func(value: bool): return value), "sailing hides and covers hand")
	demo.skip_sailing()
	_check(not hand.collapsed and hand.visible, "return restores covered hand")
	demo.reset_demo()


func _inspection_snapshot() -> Dictionary:
	return {
		"actors": demo.actors.duplicate(true), "actor": demo.actor_index,
		"selected": demo.selected_id, "steps": demo.steps.duplicate(),
		"round": demo.round_number, "sailings": demo.applied_sailings,
		"owners": demo.state.owners.duplicate(true), "arrived": demo.state.arrived.duplicate(),
		"auto_closeup": demo.auto_closeup, "notice": demo.notice,
	}


func _inspection_point() -> Vector2:
	return demo.display.get_global_transform_with_canvas() * (demo.display.size * 0.5)


func _mouse_button(index: MouseButton, pressed: bool, point: Vector2, factor := 1.0) -> void:
	var event := InputEventMouseButton.new()
	event.button_index = index
	event.pressed = pressed
	event.position = point
	event.factor = factor
	root.push_input(event, true)
	# The OS supplies wheel releases too; leaving one pressed poisons later GUI clicks.
	if pressed and index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
		var released := event.duplicate() as InputEventMouseButton
		released.pressed = false
		root.push_input(released, true)


func _inspection_motion(point: Vector2, relative: Vector2, held := true) -> void:
	var event := InputEventMouseMotion.new()
	event.position = point
	event.relative = relative
	event.button_mask = MOUSE_BUTTON_MASK_RIGHT if held else 0
	root.push_input(event, true)


func _check_inspection_frame() -> void:
	var bounds: AABB = demo.world.inspection_bounds
	var rect := Rect2(Vector2.ZERO, Vector2(demo.viewport.size))
	for corner in range(8):
		var point: Vector3 = demo.world.to_global(bounds.get_endpoint(corner))
		_check(not demo.world.camera.is_position_behind(point) and rect.has_point(demo.world.camera.unproject_position(point)), "whole crane fits initial inspection framing")
	var button: Button = demo.hud.inspect_button
	_check(Rect2(Vector2.ZERO, demo.hud.canvas.size).encloses(button.get_rect()), "inspection toggle stays in canvas")
	_check(not button.get_rect().intersects(demo.hud.phase_label.get_rect()), "inspection toggle avoids centered phase label")
	_check(not button.get_rect().intersects(demo.hud.tools_toggle.get_rect()), "inspection toggle avoids settings")


func _inspection_checks() -> void:
	demo.reset_demo()
	demo.select_slot("insurance_0")
	demo.hud.hand._toggle_card(0)
	var before := _inspection_snapshot()
	var overview: Transform3D = demo.world.camera.transform
	var overview_size: float = demo.world.camera.size
	var mouse_mode := Input.mouse_mode
	await _click(demo.hud.inspect_button)
	_check(demo.world.inspecting and not demo.busy, "inspection button enters without starting sailing")
	_check(not demo.hud.hand.visible and not demo.hud.hand.revealed.any(func(value): return value), "inspection covers and hides stocks")
	_check(not demo.hud.tools_panel.visible and not demo.hud.tools_toggle.visible, "inspection folds and hides settings")
	for control: Control in demo.hud.buttons.values() + demo.hud.district_labels.values() + demo.hud.ship_labels + demo.hud.actor_buttons + [demo.hud.avatar, demo.hud.person, demo.hud.resources, demo.hud.confirm, demo.hud.roll, demo.hud.detail]:
		_check(not control.visible, "inspection hides gameplay overlay")
	_check_inspection_frame()
	var point := _inspection_point()
	var yaw: float = demo.world.inspection_yaw
	_inspection_motion(point, Vector2(50, 40))
	_check(is_equal_approx(demo.world.inspection_yaw, yaw), "motion without right press does not orbit")
	_mouse_button(MOUSE_BUTTON_RIGHT, true, Vector2.ZERO)
	_inspection_motion(point, Vector2(50, 40))
	_check(is_equal_approx(demo.world.inspection_yaw, yaw), "outside right press cannot start orbit")
	_mouse_button(MOUSE_BUTTON_RIGHT, false, Vector2.ZERO)
	_mouse_button(MOUSE_BUTTON_RIGHT, true, point)
	var drag: Vector2 = demo.display.size * Vector2(0.10, 0.04)
	_inspection_motion(point, drag)
	_check(is_equal_approx(demo.world.inspection_yaw, yaw - 18.0), "root right drag rotates exactly once")
	_check(not demo.world.camera.transform.is_equal_approx(overview), "inspection uses a different camera transform")
	_mouse_button(MOUSE_BUTTON_RIGHT, false, Vector2.ZERO)
	yaw = demo.world.inspection_yaw
	_inspection_motion(point, Vector2(80, 0))
	_check(is_equal_approx(demo.world.inspection_yaw, yaw) and not demo._inspection_dragging, "release outside clears drag")
	_mouse_button(MOUSE_BUTTON_RIGHT, true, point)
	demo.notification(Control.NOTIFICATION_APPLICATION_FOCUS_OUT)
	_inspection_motion(point, Vector2(80, 0))
	_check(is_equal_approx(demo.world.inspection_yaw, yaw) and not demo._inspection_dragging, "focus loss clears drag")
	for shrink in [1, 2]:
		demo.display.stretch_shrink = shrink
		await process_frame
		await process_frame
		var zoom: float = demo.world.inspection_zoom
		var size_before: float = demo.world.camera.size
		_mouse_button(MOUSE_BUTTON_WHEEL_UP, true, point)
		_mouse_button(MOUSE_BUTTON_WHEEL_UP, false, point)
		_check(is_equal_approx(demo.world.inspection_zoom, zoom * 0.85), "wheel press zooms exactly once at either pixel resolution")
		_check(is_equal_approx(demo.world.camera.size, size_before * 0.85), "orthographic size implements zoom")
		_mouse_button(MOUSE_BUTTON_WHEEL_DOWN, true, point)
		_check(is_equal_approx(demo.world.inspection_zoom, zoom), "wheel down reverses zoom")
		var button: Button = demo.hud.inspect_button
		_mouse_button(MOUSE_BUTTON_WHEEL_UP, true, button.get_global_transform_with_canvas() * Vector2(20, 40))
		_mouse_button(MOUSE_BUTTON_WHEEL_UP, true, Vector2.ZERO)
		_check(is_equal_approx(demo.world.inspection_zoom, zoom), "wheel over header controls or outside view is ignored")
	for i in range(24):
		_mouse_button(MOUSE_BUTTON_WHEEL_UP, true, point)
	_check(is_equal_approx(demo.world.inspection_zoom, demo.world.INSPECTION_MIN_ZOOM), "close zoom is bounded")
	for i in range(36):
		_mouse_button(MOUSE_BUTTON_WHEEL_DOWN, true, point)
	_check(is_equal_approx(demo.world.inspection_zoom, demo.world.INSPECTION_MAX_ZOOM), "far zoom is bounded")
	_mouse_button(MOUSE_BUTTON_RIGHT, true, point)
	_inspection_motion(point, Vector2(0, 100000))
	_check(is_equal_approx(demo.world.inspection_pitch, demo.world.INSPECTION_MAX_PITCH), "orbit has upper pitch limit")
	_inspection_motion(point, Vector2(0, -100000))
	_check(is_equal_approx(demo.world.inspection_pitch, demo.world.INSPECTION_MIN_PITCH), "orbit has lower pitch limit")
	_mouse_button(MOUSE_BUTTON_RIGHT, false, point)
	await _key(KEY_SPACE)
	demo.hud.inspect_button.grab_focus()
	await _key(KEY_ENTER)
	_check(demo.world.inspecting, "Enter on focused inspection control cannot trigger gameplay")
	demo.select_slot("ship_0_0")
	demo.switch_actor(1)
	_check(not demo.confirm_selection() and not demo.roll_sailing([1, 1, 1]), "inspection guards direct placement and sailing calls")
	_check(_inspection_snapshot() == before, "inspection preserves full gameplay snapshot and selection")
	await _key(KEY_ESCAPE)
	_check(not demo.world.inspecting and not demo._inspection_dragging, "Escape exits inspection even with focused button")
	_check(_inspection_snapshot() == before, "inspection return does not advance or clear selection")
	_check(demo.world.camera.transform.is_equal_approx(overview) and is_equal_approx(demo.world.camera.size, overview_size), "return restores original overview")
	_check(Input.mouse_mode == mouse_mode, "inspection never captures the mouse")
	_check(demo.hud.hand.visible and not demo.hud.hand.revealed.any(func(value): return value), "return restores covered hand")
	_mouse_button(MOUSE_BUTTON_WHEEL_UP, true, point)
	_check(is_equal_approx(demo.world.camera.size, overview_size), "normal gameplay ignores inspection wheel")
	await _click(demo.hud.inspect_button)
	_mouse_button(MOUSE_BUTTON_RIGHT, true, point)
	await _click(demo.hud.inspect_button)
	_check(not demo.world.inspecting and not demo._inspection_dragging, "return button exits and clears drag")
	_check(demo.begin_inspection(), "inspection can reopen")
	_mouse_button(MOUSE_BUTTON_RIGHT, true, point)
	demo.reset_demo()
	_check(not demo.world.inspecting and not demo._inspection_dragging and demo.round_number == 1, "reset exits inspection before normal reset")
	# The physical button is eventually released even when reset cancelled the drag first.
	_mouse_button(MOUSE_BUTTON_RIGHT, false, point)
	_check(demo.roll_sailing([1, 1, 1]), "sailing still works after inspection")
	_check(not demo.begin_inspection() and demo.hud.inspect_button.disabled, "sailing prevents inspection entry")
	demo.skip_sailing()
	_check(demo.round_number == 2, "only actual sailing increments round")
	demo.reset_demo()


func _aspect_checks() -> void:
	for content_size in [Vector2i(1600, 1200), Vector2i(2048, 1152)]:
		root.content_scale_size = content_size
		root.size = Vector2i(1080, 810) if content_size.x == 1600 else Vector2i(1440, 810)
		await process_frame
		await process_frame
		demo.reset_demo(true)
		demo.world._update_camera()
		demo.hud._process(0)
		_check(absf(demo.size.x / demo.size.y - float(content_size.x) / content_size.y) < 0.01, "actual content aspect changes")
		_check_projection()
		_check_fan_clearance()
		_check_board_framing()
		_check_insurance_framing()
		for shrink in [1, 2]:
			demo.display.stretch_shrink = shrink
			await process_frame
			await process_frame
			await _click(demo.hud.inspect_button)
			if not demo.world.inspecting:
				print("INSPECTION_INPUT_DIAGNOSTIC: busy=%s sailing=%s disabled=%s hovered=%s top=%s focus=%s selected=%s" % [demo.busy, demo.world.sailing, demo.hud.inspect_button.disabled, demo.hud.inspect_button.is_hovered(), root.gui_get_hovered_control(), root.gui_get_focus_owner(), demo.selected_id])
			_check(demo.world.inspecting, "inspection entry works at each aspect and pixel scale")
			_check_inspection_frame()
			await _click(demo.hud.inspect_button)
			_check(not demo.world.inspecting, "inspection return works at each aspect and pixel scale")
		for id: String in demo.hud.buttons:
			var button: Button = demo.hud.buttons[id]
			_check(button.get_rect().end.y < demo.hud._layout_data.hand_rect.position.y, "placement stays above raised fan: " + id)
		for i in 3:
			await _click(demo.hud.buttons["ship_%d_0" % i])
			_check(demo.selected_id == "ship_%d_0" % i, "aspect-preserved boat input")
	_check(demo.begin_inspection(), "inspection starts before live resize")
	var target: Vector3 = demo.world.inspection_target
	for content_size in [Vector2i(1600, 1200), Vector2i(2048, 1152)]:
		root.content_scale_size = content_size
		root.size = Vector2i(1080, 810) if content_size.x == 1600 else Vector2i(1440, 810)
		await process_frame
		await process_frame
		_check_inspection_frame()
		_check(demo.world.inspection_target.is_equal_approx(target) and is_equal_approx(demo.world.inspection_zoom, 1.0), "live resize preserves target and user zoom")
	demo.end_inspection()
	demo.hud._process(0)
	_check_board_framing()
	_check_projection()
	demo.reset_demo()


func _check_fan_clearance() -> void:
	var hand: Control = demo.hud.hand
	hand.cover_all()
	var screen := Rect2(Vector2.ZERO, demo.hud.canvas.size)
	for raised in range(-1, hand.cards.size()):
		hand._raised = raised
		hand.layout_cards()
		for card: Button in hand.cards:
			var bounds := _control_bounds(card)
			_check(bounds.position.y >= 640.0, "stock fan stays below board")
			_check(screen.intersection(bounds).size.y > 195.0, "stock card has a substantial visible face")
			for button: Button in demo.hud.buttons.values():
				_check(not bounds.intersects(button.get_rect()), "raised fan avoids placement: " + str(button.name))
			for button: Button in demo.hud.actor_buttons + [demo.hud.confirm, demo.hud.roll]:
				_check(not bounds.intersects(button.get_rect()), "fan avoids actor and action buttons")
	hand.cover_all()


func _check_board_framing() -> void:
	var bounds := Rect2()
	var started := false
	for x in [-29.65, 29.65]:
		for z in [-22.65, 16.45]:
			for y in [-1.975, -1.625]:
				var point: Vector2 = demo.hud.project(Vector3(x, y, z))
				if not started:
					bounds = Rect2(point, Vector2.ZERO)
					started = true
				else:
					bounds = bounds.expand(point)
	var display_rect: Rect2 = demo.hud._layout_data.world_rect
	_check(display_rect.encloses(bounds), "finite board base fits the world viewport")
	_check(bounds.size.x / display_rect.size.x > 0.74, "board fills at least three quarters of the width")
	print("HARBOR_FRAMING: canvas=%s board=%s camera=%.2f" % [demo.hud.canvas.size, bounds, demo.world.camera.size])


func _control_bounds(control: Control) -> Rect2:
	var transform := control.get_transform()
	var bounds := Rect2(transform * Vector2.ZERO, Vector2.ZERO)
	for point in [Vector2(control.size.x, 0), control.size, Vector2(0, control.size.y)]:
		bounds = bounds.expand(transform * point)
	return Rect2(bounds.position + demo.hud.hand.position, bounds.size)


func _key(keycode: Key) -> void:
	for pressed in [true, false]:
		var event := InputEventKey.new()
		event.keycode = keycode
		event.physical_keycode = keycode
		event.pressed = pressed
		root.push_input(event, true)
		await process_frame


func _click(button: Button) -> void:
	await _click_at(button.get_global_transform_with_canvas() * (button.size * 0.5))


func _click_at(point: Vector2) -> void:
	var motion := InputEventMouseMotion.new()
	motion.position = point
	root.push_input(motion, true)
	# Keep a synthetic click together so live OS motion cannot replace its hover between frames.
	for pressed in [true, false]:
		var event := InputEventMouseButton.new()
		event.button_index = MOUSE_BUTTON_LEFT
		event.pressed = pressed
		event.position = point
		root.push_input(event, true)
	await process_frame


func _tour() -> void:
	if DirAccess.dir_exists_absolute(output_dir):
		_check(false, "preview directory already exists; choose a new output path")
		return
	if DirAccess.make_dir_recursive_absolute(output_dir) != OK:
		_check(false, "cannot create preview directory")
		return
	demo.reset_demo()
	await _click(demo.hud.inspect_button)
	_check(demo.world.inspecting, "render tour enters crane inspection")
	await create_timer(0.4).timeout
	await _capture("11_crane_inspection")
	var point := _inspection_point()
	_mouse_button(MOUSE_BUTTON_WHEEL_UP, true, point)
	_mouse_button(MOUSE_BUTTON_WHEEL_UP, true, point)
	_mouse_button(MOUSE_BUTTON_RIGHT, true, point)
	_inspection_motion(point, demo.display.size * Vector2(-0.18, 0.05))
	_mouse_button(MOUSE_BUTTON_RIGHT, false, point)
	await create_timer(0.4).timeout
	await _capture("12_crane_orbit_zoom")
	await _key(KEY_ESCAPE)
	_check(not demo.world.inspecting, "render tour exits crane inspection")
	await create_timer(0.3).timeout
	await _capture("13_crane_return")
	await create_timer(1.5).timeout
	await _capture("01_overview")
	for i in demo.hud.hand.cards.size():
		demo.hud.hand._toggle_card(i)
	demo.hud.hand.cards[1].grab_focus()
	await create_timer(0.4).timeout
	await _capture("09_hand_fan")
	demo.hud.cover_hand()
	demo.select_slot("ship_0_0")
	await create_timer(0.6).timeout
	await _capture("02_select")
	demo.confirm_selection()
	demo.switch_actor(1)
	demo.select_slot("insurance_0")
	demo.confirm_selection()
	await create_timer(0.7).timeout
	_check(demo.roll_sailing([3, 4, 2]), "preview sailing starts")
	await create_timer(0.5).timeout
	await _capture("03_dice")
	await create_timer(2.4).timeout
	_check(demo.world.camera_blend > 0.95, "close camera reached")
	await _capture("04_closeup")
	while demo.busy:
		await create_timer(0.1).timeout
	_check(demo.steps == [4, 8, 9] and demo.applied_sailings == 1, "normal playback finishes once")
	await create_timer(0.7).timeout
	await _capture("05_return")
	demo.reset_demo(true)
	await create_timer(0.5).timeout
	await _capture("06_scattered")
	demo.roll_sailing([1, 3, 1])
	await create_timer(0.3).timeout
	demo.skip_sailing()
	await process_frame
	_check(demo.state.arrived[2], "GUI arrival preset")
	await _capture("07_arrival")
	demo.reset_demo()
	demo.auto_closeup = false
	demo.roll_sailing([2, 3, 1])
	await create_timer(2.0).timeout
	_check(is_zero_approx(demo.world.camera_blend), "disabled closeup stays global")
	while demo.busy:
		await create_timer(0.1).timeout
	_check(demo.applied_sailings == 1, "overview playback finishes once")
	root.size = Vector2i(1280, 720)
	await create_timer(0.4).timeout
	_check_projection()
	await _capture("08_resized")
	root.content_scale_size = Vector2i(1600, 1200)
	root.size = Vector2i(1080, 810)
	demo.reset_demo()
	await create_timer(0.6).timeout
	_check_projection()
	await _capture("10_reference_aspect")
	print("HARBOR_PREVIEW_SAVED: ", ProjectSettings.globalize_path(output_dir))
	_tour_complete = true


func _capture(filename: String) -> void:
	await process_frame
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	_check(image != null and not image.is_empty(), "render " + filename)
	if image != null and not image.is_empty():
		_check(image.save_png(output_dir.path_join(filename + ".png")) == OK, "save " + filename)


func _check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)
		push_error("HARBOR_CHECK: " + message)


func _finish() -> void:
	if _finished:
		return
	_finished = true
	print("HARBOR_DEMO_%s: %d checks / %d failures" % ["PASS" if failures.is_empty() else "FAIL", checks, failures.size()])
	for failure in failures:
		print("  FAIL: ", failure)
	quit(0 if failures.is_empty() else 1)
