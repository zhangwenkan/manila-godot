extends SceneTree

const PREVIEW = preload("res://character_preview/character_select_preview.tscn")

class TouchProbe extends Node:
	var releases := 0

	func _input(event: InputEvent) -> void:
		if event is InputEventScreenTouch and event.index == 4 and not event.pressed:
			releases += 1

var _touch_probe: TouchProbe
const OUTPUT := "res://.godot/character_preview_check"
const LIKENESS := OUTPUT + "/carmen_likeness"
const CARD_OUTPUT := OUTPUT + "/carmen_card"
var _exhibit := false
var _lanyard := false
var _showcase := false
var _lanyard_layouts: Dictionary = {}
var _upright := ""
var _upright_layouts: Dictionary = {}
const UPRIGHT := OUTPUT + "/carmen_upright"
var _card_phase := ""
var _card_layouts: Dictionary = {}
var _card_baseline: Dictionary = {}
var _output := OUTPUT
var _phase := ""
var _likeness_frames: Dictionary = {}
var _failures: Array[String] = []
var _preview
var _confirmations: Array[String] = []
var _closed_count := 0
var _done := false
var _step := "starting"


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	create_timer(110.0 if "--showcase" in OS.get_cmdline_user_args() else (90.0 if "--lanyard" in OS.get_cmdline_user_args() else 55.0)).timeout.connect(_timeout)
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--likeness="):
			_phase = argument.trim_prefix("--likeness=")
		if argument.begins_with("--card="):
			_card_phase = argument.trim_prefix("--card=")
		if argument.begins_with("--upright="):
			_upright = argument.trim_prefix("--upright=")
		if argument == "--exhibit":
			_exhibit = true
		if argument == "--lanyard":
			_lanyard = true
		if argument == "--showcase":
			_showcase = true
			_lanyard = true
	if _lanyard:
		if _exhibit or not _upright.is_empty() or not _card_phase.is_empty() or not _phase.is_empty():
			push_error("Use --lanyard independently")
			quit(2)
			return
		_output = OUTPUT + ("/foreground/after" if _showcase else "/lanyard")
	if not _upright.is_empty():
		if _exhibit or not _card_phase.is_empty() or not _phase.is_empty() or _upright not in ["before", "after"]:
			push_error("Use --upright=before|after independently")
			quit(2)
			return
		_exhibit = true
	if _exhibit:
		if not _card_phase.is_empty() or not _phase.is_empty():
			push_error("Use --exhibit independently of historical capture modes")
			quit(2)
			return
		_output = OUTPUT + "/carmen_exhibit" if _upright.is_empty() else UPRIGHT.path_join(_upright)
		if _upright == "before" and FileAccess.file_exists(_output.path_join("layouts.json")):
			push_error("Accepted doll baseline already exists; refusing overwrite")
			quit(2)
			return
	if not _card_phase.is_empty():
		if not _phase.is_empty() or _card_phase not in ["before", "after"]:
			push_error("Use --card=before|after independently of --likeness")
			quit(2)
			return
		_output = CARD_OUTPUT.path_join(_card_phase)
		if _card_phase == "after":
			var baseline = JSON.parse_string(FileAccess.get_file_as_string(CARD_OUTPUT + "/before/layouts.json"))
			if not baseline is Dictionary:
				push_error("Missing card layout baseline")
				quit(2)
				return
			_card_baseline = baseline
	if not _phase.is_empty():
		if _phase not in ["before", "after"]:
			push_error("Expected --likeness=before or --likeness=after")
			quit(2)
			return
		_output = LIKENESS.path_join(_phase)
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(_output))
	root.size = Vector2i(1280, 720)
	_preview = PREVIEW.instantiate()
	_preview.quit_on_close = false
	if _lanyard:
		# Reverse tree-order input: the card runs first, then this observer.
		_touch_probe = TouchProbe.new()
		root.add_child(_touch_probe)
	root.add_child(_preview)
	_preview.character_confirmed.connect(func(id: String, _display: String): _confirmations.append(id))
	_preview.closed.connect(func(): _closed_count += 1)
	await _frames(5)
	_check(_preview.choice_buttons.size() == 6, "Six choices are present")
	_check(_preview.stage.pawns.size() == 6, "Six procedural pawns are present")
	var ids: Dictionary = {}
	for data: Dictionary in _preview.ROSTER:
		ids[data.id] = true
	_check(ids.size() == 6, "Character IDs are unique")
	if not _phase.is_empty():
		_geometry_snapshot()
		await _capture_carmen()
	if not _card_phase.is_empty():
		_geometry_snapshot()
		await _card_layout_check()
	if _exhibit:
		_geometry_snapshot()
		await _exhibit_check()
	if _lanyard:
		await _lanyard_check()
	await _capture("01_desktop.png")
	print("PREVIEW_RENDER: draw_calls=%d primitives=%d" % [RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME), RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME)])
	for index in 6:
		await _click(_preview.choice_buttons[index].get_global_rect().get_center())
		await create_timer(0.30).timeout
		_check(_preview.selected_index == index, "Click selects character %d" % index)
		_check(_preview._hero_name.text == _preview.ROSTER[index].name, "Displayed name matches %d" % index)
		_bench_layout_check()
		if _showcase:
			_check(_preview._speech.visible == (index == 0), "Speech follows selected character %d" % index)
			var choice: MeshInstance3D = _preview.stage.pawns[index].get_child(0)
			var display: MeshInstance3D = _preview.stage.hero.get_child(0)
			_check(choice.mesh != display.mesh, "Choice and display keep isolated resources %d" % index)
			_check(_preview.stage.pawns[index].get_meta("pose") == "seated", "Choice uses seated presentation %d" % index)
			_check(choice.mesh.get_aabb().position.y < -0.5 and is_zero_approx(choice.position.y), "Seated legs hang below hip contact %d" % index)
			for surface in 2:
				_check(choice.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX] != display.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX], "Seated and standing vertices differ %d/%d" % [index, surface])
			_check(choice.get_surface_override_material(0) == null, "Display override does not leak to choice %d" % index)
		await _capture("character_%d.png" % (index + 1))
		await _click(_preview.confirm_button.get_global_rect().get_center())
		_check(_confirmations.size() == index + 1, "Confirm emits once for %d" % index)
		if not _confirmations.is_empty():
			_check(_confirmations.back() == _preview.ROSTER[index].id, "Confirmed identity matches %d" % index)
	await _capture("02_confirmed.png")
	_preview.choice_buttons[0].grab_focus()
	await _key(KEY_RIGHT)
	_check(_preview.selected_index == 1, "Keyboard moves right")
	await _key(KEY_DOWN)
	_check(_preview.selected_index == 4, "Keyboard moves down a grid row")
	var previous_count := _confirmations.size()
	await _key(KEY_ENTER)
	_check(_confirmations.size() == previous_count + 1, "Keyboard confirmation emits only once")
	_preview.choice_buttons[5].grab_focus()
	await _key(KEY_ENTER)
	_check(_preview.selected_index == 5 and _confirmations.back() == _preview.ROSTER[5].id, "Enter confirms keyboard-focused choice")
	await _capture("03_keyboard.png")
	for index in [0, 5, 1, 4, 2, 3]:
		await _click(_preview.choice_buttons[index].get_global_rect().get_center())
	await create_timer(0.35).timeout
	for index in 6:
		var expected: Vector3 = _preview.stage._homes[index]
		_check(_preview.stage.pawns[index].position.distance_to(expected) < 0.001, "Rapid selection settles correctly %d" % index)
	for viewport_size in [Vector2i(2048, 1152), Vector2i(768, 1024), Vector2i(390, 844), Vector2i(390, 600)]:
		root.size = viewport_size
		await _frames(8)
		# Let the native Windows resize/mouse mapping settle before injecting input.
		await create_timer(0.15).timeout
		var bounds := Rect2(Vector2.ZERO, Vector2(root.size))
		_check(_preview.size.is_equal_approx(Vector2(root.size)), "Native preview size %s" % viewport_size)
		_check(bounds.encloses(_preview.confirm_button.get_global_rect()), "Confirm button in view %s" % viewport_size)
		_check(bounds.encloses(_preview.close_button.get_global_rect()), "Close button in view %s" % viewport_size)
		for button: Button in _preview.choice_buttons:
			_check(bounds.encloses(button.get_global_rect()), "Choice in view %s" % viewport_size)
		await _click(_preview.choice_buttons[2].get_global_rect().get_center())
		_check(_preview.selected_index == 2, "Resized click selects correct character %s" % viewport_size)
		await create_timer(0.30).timeout
		_bench_layout_check()
		await _capture("layout_%dx%d.png" % [viewport_size.x, viewport_size.y])
		if not _phase.is_empty():
			await _capture_carmen()
		if not _card_phase.is_empty():
			await _card_layout_check()
		if _exhibit:
			await _exhibit_check()
		if _lanyard:
			await _lanyard_check()
	if not _phase.is_empty() or not _card_phase.is_empty() or _exhibit or _lanyard:
		# Keep the touch assertion meaningful after the extra Carmen captures.
		await _click(_preview.choice_buttons[2].get_global_rect().get_center())
	var touch := InputEventScreenTouch.new()
	touch.index = 0
	touch.position = _preview.choice_buttons[0].get_global_rect().get_center()
	touch.pressed = true
	Input.parse_input_event(touch)
	await _frames(1)
	touch = touch.duplicate()
	touch.pressed = false
	Input.parse_input_event(touch)
	await _frames(2)
	# Button touch support depends on emulate_mouse_from_touch, enabled by default.
	_check(_preview.selected_index == 0, "Touch selects a character")
	if _lanyard:
		_mouse_button(_preview._card.art_point(Vector2(0.5, 0.5)), true)
		_check(_preview._card.motion.dragging, "Grab before closing preview")
	await _key(KEY_ESCAPE)
	_check(not _preview.visible and _closed_count == 1, "Escape closes once")
	if _lanyard:
		_check(not _preview._card.motion.dragging, "Closing preview cancels grab")
	_preview.open()
	await _frames(2)
	if _lanyard:
		_check(_preview._card.motion.sleeping and _preview._card.is_visible_in_tree(), "Reopen restores stable lanyard")
	if _card_phase == "after":
		_check(_preview._card.is_visible_in_tree(), "Card restored on reopen")
		_card_composition_check()
	if _exhibit:
		_exhibit_composition()
		_check(_preview._card.is_visible_in_tree(), "Exhibit restores on reopen")
	await _click(_preview.close_button.get_global_rect().get_center())
	_check(not _preview.visible and _closed_count == 2, "Close button closes once")
	_preview.queue_free()
	await _frames(2)
	if not _phase.is_empty():
		_save_json(_output.path_join("frames.json"), _likeness_frames)
	if not _card_phase.is_empty():
		_save_json(_output.path_join("layouts.json"), _card_layouts)
		_save_json(_output.path_join("result.json"), {"passed": _failures.is_empty(), "failures": _failures, "phase": _card_phase})
	if _exhibit:
		_save_json(_output.path_join("result.json"), {"passed": _failures.is_empty(), "failures": _failures, "phase": "exhibit" if _upright.is_empty() else _upright})
		if not _upright.is_empty():
			_save_json(_output.path_join("layouts.json"), _upright_layouts)
	if _lanyard:
		_save_json(_output.path_join("result.json"), {"passed": _failures.is_empty(), "failures": _failures, "layouts": _lanyard_layouts})
	_done = true
	if _failures.is_empty():
		print("CHARACTER_PREVIEW_PASS: six characters, mouse/touch/keyboard, confirmation, rapid selection, five layouts, close; screenshots in " + _output)
	else:
		for failure in _failures:
			push_error(failure)
		print("CHARACTER_PREVIEW_FAIL: %d checks failed" % _failures.size())
	quit(0 if _failures.is_empty() else 1)


func _bench_layout_check() -> void:
	var stage = _preview.stage
	var key := "%dx%d/%d" % [root.size.x, root.size.y, _preview.selected_index]
	_check(_preview.columns == 3 and stage._benches.size() == 2, "Fixed three-by-two bench layout " + key)
	for row in 2:
		var bench: MeshInstance3D = stage._benches[row]
		_check(bench.mesh.get_meta("seat_count") == 3, "Three seats per wooden bench " + key)
		var bench_bounds: Rect2 = stage._mesh_screen_bounds(bench)
		var row_rect: Rect2 = _preview.cell_rects[row * 3].merge(_preview.cell_rects[row * 3 + 2])
		_check(row_rect.grow(1).encloses(bench_bounds), "Bench stays within its row " + key)
		for column in 3:
			var i := row * 3 + column
			var pawn: Node3D = stage.pawns[i]
			var contact := bench.to_local(pawn.global_position)
			_check(absf(contact.y) < 0.001 and absf(contact.z) < 0.001, "Shared seat plane %s/%d" % [key, i])
			var bounds := _projected_bounds(pawn)
			var cell: Rect2 = _preview.cell_rects[i]
			_check(cell.grow(1).encloses(bounds), "Seated figure inside cell %s/%d" % [key, i])
			_check(maxf(bounds.end.y, bench_bounds.end.y) < cell.position.y + cell.size.y * 0.80, "Figure and bench clear of caption %s/%d" % [key, i])
			var button: Button = _preview.choice_buttons[i]
			var font: Font = button.get_theme_font("font")
			_check(font.get_string_size(button.text, HORIZONTAL_ALIGNMENT_LEFT, -1, button.get_theme_font_size("font_size")).x <= cell.size.x, "Full name fits seat %s/%d" % [key, i])


func _click(position: Vector2) -> void:
	_step = "click " + str(position)
	# Dispatch a complete click in one frame so native mouse motion between
	# press/release cannot redirect a scripted click to a different control.
	Input.flush_buffered_events()
	for pressed in [true, false]:
		var motion := InputEventMouseMotion.new()
		motion.position = position
		motion.global_position = position
		Input.parse_input_event(motion)
		var event := InputEventMouseButton.new()
		event.position = position
		event.global_position = position
		event.button_index = MOUSE_BUTTON_LEFT
		event.pressed = pressed
		Input.parse_input_event(event)
	Input.flush_buffered_events()
	await _frames(2)


func _key(keycode: Key) -> void:
	for pressed in [true, false]:
		var event := InputEventKey.new()
		event.keycode = keycode
		event.pressed = pressed
		Input.parse_input_event(event)
		await _frames(1)


func _frames(count: int) -> void:
	for i in count:
		await process_frame


func _render_frame() -> void:
	await process_frame
	# Windows can suppress drawing during native resize/occlusion; request an
	# actual frame synchronously rather than wait forever for an omitted signal.
	RenderingServer.force_draw(false)


func _capture(filename: String) -> void:
	_step = "capture " + filename
	await _render_frame()
	var image := root.get_texture().get_image()
	_check(image != null and not image.is_empty(), "Frame exists " + filename)
	if image != null and not image.is_empty():
		_check(image.save_png(_output.path_join(filename)) == OK, "Screenshot saved " + filename)


func _geometry_snapshot() -> void:
	var snapshot: Dictionary = {"meshes": [], "sources": {}}
	for index in 6:
		var model: MeshInstance3D = _preview.stage.pawns[index].get_child(0)
		var mesh := model.mesh
		var duplicate: Node3D = _preview.stage.PawnFactory.build(index)
		_check(duplicate.get_child(0).mesh == mesh, "Shared mesh cache %d" % index)
		duplicate.free()
		_check(mesh.get_surface_count() == 2, "Two merged surfaces %d" % index)
		var entry: Array = []
		for surface in mesh.get_surface_count():
			var arrays := mesh.surface_get_arrays(surface)
			var summary: Dictionary = {}
			for attribute in [Mesh.ARRAY_VERTEX, Mesh.ARRAY_NORMAL, Mesh.ARRAY_COLOR, Mesh.ARRAY_INDEX]:
				summary[str(attribute)] = var_to_bytes(arrays[attribute]).hex_encode().sha256_text()
			entry.append(summary)
			if index != 0:
				continue
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			_check(vertices.size() == normals.size(), "Carmen vertex/normal counts")
			var valid := true
			var winding_errors := 0
			for v in vertices.size():
				valid = valid and vertices[v].is_finite() and normals[v].is_finite()
				valid = valid and absf(normals[v].length() - 1.0) < 0.001
			for i in indices:
				valid = valid and i >= 0 and i < vertices.size()
			_check(valid, "Carmen finite vertices, unit normals, valid indices")
			if valid:
				for triangle in range(0, indices.size(), 3):
					var a := indices[triangle]
					var b := indices[triangle + 1]
					var c := indices[triangle + 2]
					var cross := (vertices[b] - vertices[a]).cross(vertices[c] - vertices[a])
					if cross.length_squared() > 0.000000000001:
						if cross.normalized().dot((normals[a] + normals[b] + normals[c]).normalized()) > 0.02:
							winding_errors += 1
			_check(winding_errors == 0, "Carmen clockwise winding: %d errors" % winding_errors)
		snapshot.meshes.append(entry)
	var carmen: Mesh = _preview.stage.pawns[0].get_child(0).mesh
	var bounds := carmen.get_aabb()
	_check(absf(bounds.position.y) < 0.001, "Carmen pedestal lands at y=0")
	_check(bounds.end.y <= 3.65 and bounds.size.x <= 1.80, "Carmen fits existing height/width envelope")
	_check(carmen.surface_get_material(0).next_pass != null, "Carmen body has outline")
	_check(carmen.surface_get_material(1).next_pass == null, "Carmen details omit outline")
	for filename in ["character_select_preview.tscn", "character_select_preview.gd", "character_stage_3d.gd", "pawn.gdshader"]:
		snapshot.sources[filename] = FileAccess.get_sha256("res://character_preview/" + filename)
	var source := FileAccess.get_file_as_string("res://character_preview/pawn_factory.gd")
	var untouched := source.substr(0, source.find("static func _carmen(")) + source.substr(source.find("static func _li_yunlong("))
	snapshot.sources["factory_except_carmen"] = untouched.sha256_text()
	if not _card_phase.is_empty() or _exhibit:
		snapshot.sources["factory"] = source.sha256_text()
		snapshot.sources["portrait"] = FileAccess.get_sha256("res://card/image/carmen.webp")
	_save_json(_output.path_join("geometry.json"), snapshot)
	if _card_phase == "after":
		var before = JSON.parse_string(FileAccess.get_file_as_string(CARD_OUTPUT + "/before/geometry.json"))
		_check(before is Dictionary, "Card geometry baseline exists")
		if before is Dictionary:
			_check(before.meshes == snapshot.meshes, "All six pawn meshes unchanged including Carmen")
			for key in ["factory", "portrait", "character_stage_3d.gd", "pawn.gdshader", "character_select_preview.tscn"]:
				_check(before.sources[key] == snapshot.sources[key], "Frozen source unchanged: " + key)
	if _phase == "after":
		var before = JSON.parse_string(FileAccess.get_file_as_string(LIKENESS + "/before/geometry.json"))
		_check(before is Dictionary, "Before geometry baseline exists")
		if before is Dictionary:
			_check(before.sources == snapshot.sources, "UI, stage, shader and all shared/other builders unchanged")
			for index in range(1, 6):
				_check(before.meshes[index] == snapshot.meshes[index], "Other pawn geometry unchanged %d" % index)
			_check(before.meshes[0] != snapshot.meshes[0], "Carmen geometry actually changed")
	if _exhibit:
		var accepted = JSON.parse_string(FileAccess.get_file_as_string(CARD_OUTPUT + "/before/geometry.json"))
		_check(accepted is Dictionary, "Accepted pawn baseline exists")
		if accepted is Dictionary:
			_check(accepted.meshes == snapshot.meshes, "Exhibit preserves all six accepted meshes")
			for key in ["factory", "portrait", "pawn.gdshader", "character_select_preview.tscn"]:
				_check(accepted.sources[key] == snapshot.sources[key], "Exhibit frozen source: " + key)
	print("CARMEN_GEOMETRY: bounds=%s; components=%d" % [bounds, carmen.get_meta("sculpted_components")])


func _projected_bounds(pawn: Node3D, minimum_y: float = -1.0) -> Rect2:
	var model: MeshInstance3D = pawn.get_child(0)
	var bounds := Rect2()
	var first := true
	var stage = _preview.stage
	for surface in model.mesh.get_surface_count():
		var arrays := model.mesh.surface_get_arrays(surface)
		for vertex: Vector3 in arrays[Mesh.ARRAY_VERTEX]:
			if vertex.y < minimum_y:
				continue
			var screen: Vector2 = stage.camera.unproject_position(model.global_transform * vertex)
			screen = stage.global_position + screen * stage.size / Vector2(stage.viewport_3d.size)
			if first:
				bounds = Rect2(screen, Vector2.ZERO)
				first = false
			else:
				bounds = bounds.expand(screen)
	return bounds


func _capture_carmen() -> void:
	await _click(_preview.choice_buttons[0].get_global_rect().get_center())
	await create_timer(0.30).timeout
	_check(_preview.selected_index == 0, "Carmen selected for comparison")
	var cell: Rect2 = _preview.cell_rects[0]
	var caption_free := Rect2(cell.position, Vector2(cell.size.x, cell.size.y * 0.80))
	var body := _projected_bounds(_preview.stage.pawns[0], 0.172)
	var hero_body := _projected_bounds(_preview.stage.hero, 0.172)
	_check(cell.encloses(_projected_bounds(_preview.stage.pawns[0])), "Carmen whole pawn stays in cell %s" % root.size)
	_check(caption_free.encloses(body), "Carmen body clears caption %s" % root.size)
	_check(_preview._hero_rect.encloses(hero_body), "Carmen hero body stays in its display %s: body=%s display=%s" % [root.size, hero_body, _preview._hero_rect])
	var home: Vector3 = _preview.stage._homes[0] + Vector3.UP * _preview.stage._pawn_scale * 0.16
	_check(_preview.stage.pawns[0].position.distance_to(home) < 0.001, "Carmen selected landing")
	_check(_preview.stage.hero.position.distance_to(_preview.stage._hero_home) < 0.001, "Carmen hero landing")
	await _render_frame()
	var image := root.get_texture().get_image()
	var key := "%dx%d" % [root.size.x, root.size.y]
	_check(image.save_png(_output.path_join("carmen_" + key + ".png")) == OK, "Carmen layout saved " + key)
	var crops: Dictionary = {"small": _projected_bounds(_preview.stage.pawns[0]), "hero": _projected_bounds(_preview.stage.hero), "head": _projected_bounds(_preview.stage.hero, 2.40)}
	var metadata: Dictionary = {}
	for label: String in crops:
		var rect: Rect2 = crops[label].grow(4).intersection(Rect2(Vector2.ZERO, Vector2(root.size)))
		var pixels := Rect2i(Vector2i(rect.position.floor()), Vector2i(rect.end.ceil() - rect.position.floor()))
		_check(image.get_region(pixels).save_png(_output.path_join("carmen_%s_%s.png" % [label, key])) == OK, "Carmen crop saved " + label)
		metadata[label] = [pixels.position.x, pixels.position.y, pixels.size.x, pixels.size.y]
	_likeness_frames[key] = metadata


func _card_layout_check() -> void:
	var key := "%dx%d" % [root.size.x, root.size.y]
	var entry: Dictionary = {"board": var_to_str(_preview._board_rect), "cells": var_to_str(_preview.cell_rects),
		"confirm": var_to_str(_preview.confirm_button.get_global_rect()), "other_heroes": []}
	if _card_phase == "after":
		_card_visibility_check()
	for index in range(1, 6):
		await _click(_preview.choice_buttons[index].get_global_rect().get_center())
		await create_timer(0.27).timeout
		_check(_preview.selected_index == index, "Card roundtrip selects %d" % index)
		var pose := var_to_str([_preview.stage.hero.transform, _preview.stage._hero_base.transform,
			_preview.stage._hero_base.mesh.get_aabb(), _preview.stage._table.transform])
		entry.other_heroes.append(pose)
		if _card_phase == "after":
			_card_visibility_check()
		await _click(_preview.choice_buttons[0].get_global_rect().get_center())
		# Sample the full selection tween, including its initial yaw.
		var elapsed := 0.0
		while elapsed < 0.28:
			await process_frame
			elapsed += root.get_process_delta_time()
			if _card_phase == "after":
				_card_composition_check()
	if _card_phase == "after":
		_check(_card_baseline.has(key), "Baseline size present " + key)
		if _card_baseline.has(key):
			_check(entry == _card_baseline[key], "Grid, confirm and other five presentations unchanged " + key)
		_card_visibility_check()
		_card_composition_check()
		print("CARD_LAYOUT %s pawn=%s body=%s base=%s card=%s name=%s title=%s confirm=%s" % [key, _preview._pawn_rect, _projected_bounds(_preview.stage.hero, 0.172), _instance_bounds(_preview.stage._hero_base), _preview._card.visual_rect(), _preview._card.name_label.get_global_rect(), _preview._card.title_label.get_global_rect(), _preview.confirm_button.get_global_rect()])
	_card_layouts[key] = entry
	await _capture("card_" + key + ".png")
	await _render_frame()
	var image := root.get_texture().get_image()
	if _card_phase == "after":
		# Verify the artwork really reached the framebuffer behind the 3D layer.
		var image_rect: Rect2 = _preview._card.image_rect()
		var reference: Image = _preview._card.art.texture.get_image()
		var mismatch := 0.0
		for uv: Vector2 in [Vector2(0.15, 0.2), Vector2(0.45, 0.25), Vector2(0.4, 0.5), Vector2(0.2, 0.75)]:
			var point := Vector2i(image_rect.position + image_rect.size * uv)
			var actual_uv := (Vector2(point) + Vector2.ONE * 0.5 - image_rect.position) / image_rect.size
			var expected := reference.get_pixelv(Vector2i(actual_uv * Vector2(reference.get_size())))
			var rendered := image.get_pixelv(point)
			mismatch += absf(expected.r - rendered.r) + absf(expected.g - rendered.g) + absf(expected.b - rendered.b)
		_check(mismatch / 12.0 < 0.16, "Original artwork visible in final framebuffer " + key)
	var region: Rect2 = _preview._hero_rect
	if _card_phase == "after":
		region = _preview._card.visual_rect().merge(_projected_bounds(_preview.stage.hero)).merge(_instance_bounds(_preview.stage._hero_base))
	region = region.grow(5).intersection(Rect2(Vector2.ZERO, Vector2(root.size)))
	var crop := Rect2i(Vector2i(region.position.floor()), Vector2i(region.end.ceil() - region.position.floor()))
	_check(image.get_region(crop).save_png(_output.path_join("composition_" + key + ".png")) == OK, "Full composition saved " + key)


func _card_visibility_check() -> void:
	var carmen: bool = _preview.selected_index == 0
	_check(_preview._card.visible == carmen, "Card only visible for Carmen")
	_check(_preview._hero_name.visible == not carmen and _preview._hero_title.visible == not carmen, "No duplicate identity labels")
	_check(_preview._hero_note.visible == (not carmen and not (_preview._portrait and _preview.size.x < 550)), "Flavor label restored correctly")
	_check(_preview._card.get_index() < _preview.stage.get_index(), "Card behind transparent stage")
	for control in [_preview._card, _preview._card.art, _preview._card.name_label, _preview._card.title_label]:
		_check(control.mouse_filter == Control.MOUSE_FILTER_IGNORE and control.focus_mode == Control.FOCUS_NONE, "Card decorations ignore input")
	_check(_preview._card.art.texture.resource_path == "res://card/image/carmen.webp", "Full original illustration source")
	_check(_preview._card.name_label.text == _preview.ROSTER[0].name and _preview._card.title_label.text == _preview.ROSTER[0].title, "Card identity matches roster")
	_check(_preview._card.art.stretch_mode == TextureRect.STRETCH_KEEP_ASPECT_CENTERED, "Full aspect fit without crop")


func _instance_bounds(model: MeshInstance3D) -> Rect2:
	var bounds := Rect2()
	var first := true
	var box := model.mesh.get_aabb()
	var stage = _preview.stage
	for corner in range(8):
		var screen: Vector2 = stage.camera.unproject_position(model.global_transform * box.get_endpoint(corner))
		screen = stage.global_position + screen * stage.size / Vector2(stage.viewport_3d.size)
		bounds = Rect2(screen, Vector2.ZERO) if first else bounds.expand(screen)
		first = false
	return bounds


func _card_composition_check() -> void:
	if _preview.selected_index != 0:
		return
	var u: float = _preview._unit
	var card = _preview._card
	var image_rect: Rect2 = card.image_rect()
	var dimensions: Vector2 = card.art.texture.get_size()
	_check(absf(image_rect.size.aspect() - dimensions.aspect()) < 0.001, "Card image preserves aspect ratio")
	var body := _projected_bounds(_preview.stage.hero, 0.172).grow(1.5 * u)
	var model := _projected_bounds(_preview.stage.hero).grow(1.5 * u)
	var base := _instance_bounds(_preview.stage._hero_base).grow(u)
	var window := Rect2(Vector2.ZERO, Vector2(root.size))
	var face := Rect2(image_rect.position + image_rect.size * Vector2(0.40, 0.12), image_rect.size * Vector2(0.21, 0.25))
	var torso := Rect2(image_rect.position + image_rect.size * Vector2(0.33, 0.37), image_rect.size * Vector2(0.37, 0.40))
	_check(window.encloses(card.visual_rect()) and window.encloses(model) and window.encloses(base), "Composite inside window")
	_check(_preview._pawn_rect.grow(2 * u).encloses(body), "Carmen in allocated pawn region")
	_check(not card.visual_rect().intersects(_preview._board_rect), "Card does not cover choice board")
	for shape in [model, base]:
		_check(not shape.intersects(face) and not shape.intersects(torso), "Pawn and base clear illustration face and costume")
		_check(not shape.intersects(card.name_label.get_global_rect()) and not shape.intersects(card.title_label.get_global_rect()), "Pawn and base clear nameplate text")
		_check(not shape.intersects(_preview.confirm_button.get_global_rect().grow(8 * u)), "Pawn and base clear confirm button")
		_check(not shape.intersects(_preview._board_rect), "Foreground stays off choice board")
	_check(not card.visual_rect().intersects(_preview.confirm_button.get_global_rect()), "Card frame clears confirmation")
	_check(not card.name_label.get_global_rect().intersects(card.title_label.get_global_rect()), "Nameplate text lines do not overlap")
	_check(card.get_global_rect().encloses(card.name_label.get_global_rect()) and card.get_global_rect().encloses(card.title_label.get_global_rect()), "Nameplate labels stay inside card")
	var cell: Rect2 = _preview.cell_rects[0]
	_check(Rect2(cell.position, Vector2(cell.size.x, cell.size.y * 0.80)).encloses(_projected_bounds(_preview.stage.pawns[0], 0.172)), "Carmen grid caption clear")


func _exhibit_check() -> void:
	var key := "%dx%d" % [root.size.x, root.size.y]
	var baseline = JSON.parse_string(FileAccess.get_file_as_string(CARD_OUTPUT + "/before/layouts.json"))
	_check(baseline is Dictionary and baseline.has(key), "Original layout baseline " + key)
	for index in range(1, 6):
		await _click(_preview.choice_buttons[index].get_global_rect().get_center())
		await create_timer(0.27).timeout
		_check(_preview.selected_index == index, "Exhibit roundtrip selects %d" % index)
		_check(not _preview._card.visible and _preview._hero_name.visible and _preview._hero_title.visible, "Other character restores original presentation")
		var model: MeshInstance3D = _preview.stage.hero.get_child(0)
		for surface in 2:
			_check(model.get_surface_override_material(surface) == null, "Other hero has no vinyl override %d" % index)
		if baseline is Dictionary and baseline.has(key):
			var saved: Dictionary = baseline[key]
			_check(var_to_str(_preview._board_rect) == saved.board and var_to_str(_preview.cell_rects) == saved.cells, "Other character grid unchanged " + key)
			_check(var_to_str(_preview.confirm_button.get_global_rect()) == saved.confirm, "Other confirmation restored " + key)
			var pose := var_to_str([_preview.stage.hero.transform, _preview.stage._hero_base.transform,
				_preview.stage._hero_base.mesh.get_aabb(), _preview.stage._table.transform])
			_check(pose == saved.other_heroes[index - 1], "Other hero pose unchanged %s / %d" % [key, index])
		await _click(_preview.choice_buttons[0].get_global_rect().get_center())
		var elapsed := 0.0
		while elapsed < 0.28:
			await process_frame
			elapsed += root.get_process_delta_time()
			_exhibit_composition()
	for pawn: Node3D in _preview.stage.pawns:
		var model: MeshInstance3D = pawn.get_child(0)
		for surface in 2:
			_check(model.get_surface_override_material(surface) == null and model.material_override == null, "Grid materials have no overrides")
			var material: ShaderMaterial = model.mesh.surface_get_material(surface)
			_check(material.shader.resource_path == "res://character_preview/pawn.gdshader", "Grid keeps original paint shader")
	if not _upright.is_empty():
		_upright_snapshot(key)
	var display = _preview._card
	_check(display.artwork.mesh is QuadMesh and display.rim.mesh is ArrayMesh, "Actual 3D image and extruded rim")
	_check(display.artwork.mesh.size == Vector2(4.5, 4.5), "Full square artwork without cropping")
	_check(display.artwork.material_override.get_shader_parameter("portrait").resource_path == "res://card/image/carmen.webp", "Original artwork texture on 3D screen")
	_check(display.name_label.text == _preview.ROSTER[0].name and display.title_label.text == _preview.ROSTER[0].title, "Screen identity matches roster")
	_check(display.mouse_filter == Control.MOUSE_FILTER_IGNORE and display._view.mouse_filter == Control.MOUSE_FILTER_IGNORE, "Display does not intercept input")
	_check(display.get_index() < _preview.stage.get_index(), "Pixel toy composited in front of screen")
	var hero_model: MeshInstance3D = _preview.stage.hero.get_child(0)
	_check(hero_model.get_surface_override_material(0).shader.resource_path == "res://character_preview/carmen_vinyl.gdshader", "Only Carmen hero has vinyl material")
	await _capture("exhibit_" + key + ".png")
	await _render_frame()
	var image := root.get_texture().get_image()
	var reference: Image = display.PORTRAIT.get_image()
	var error := 0.0
	for uv: Vector2 in [Vector2(0.18, 0.2), Vector2(0.48, 0.25), Vector2(0.4, 0.5), Vector2(0.2, 0.75)]:
		var rendered := image.get_pixelv(Vector2i(display.art_point(uv)))
		var expected := reference.get_pixelv(Vector2i(uv * Vector2(reference.get_size())))
		error += absf(rendered.r - expected.r) + absf(rendered.g - expected.g) + absf(rendered.b - expected.b)
	_check(error / 12.0 < 0.18, "Original art reaches framebuffer " + key)
	var region: Rect2 = display.visual_rect().merge(_projected_bounds(_preview.stage.hero)).merge(_instance_bounds(_preview.stage._hero_base))
	region = region.grow(4).intersection(Rect2(Vector2.ZERO, Vector2(root.size)))
	var crop := Rect2i(Vector2i(region.position.floor()), Vector2i(region.end.ceil() - region.position.floor()))
	_check(image.get_region(crop).save_png(_output.path_join("composition_" + key + ".png")) == OK, "Exhibit crop saved")
	display.artwork.hide()
	await _frames(2)
	await _render_frame()
	var hidden := root.get_texture().get_image()
	display.artwork.show()
	var visible_delta := 0.0
	for uv: Vector2 in [Vector2(0.3, 0.4), Vector2(0.4, 0.6)]:
		var point := Vector2i(display.art_point(uv))
		var a := image.get_pixelv(point)
		var b := hidden.get_pixelv(point)
		visible_delta += absf(a.r - b.r) + absf(a.g - b.g) + absf(a.b - b.b)
	_check(visible_delta > 0.12, "3D artwork contributes visible pixels " + key)
	await _frames(2)
	await _render_frame()
	var screen_image: Image = display.viewport_3d.get_texture().get_image()
	_check(screen_image.save_png(_output.path_join("screen_" + key + ".png")) == OK, "Isolated screen capture saved")
	display.rim.hide()
	await _frames(2)
	await _render_frame()
	var no_rim: Image = display.viewport_3d.get_texture().get_image()
	display.rim.show()
	var rim_delta := 0.0
	var rim_probes: Array = display.rim_points() if _upright == "after" else [Vector3(-2.52, 1.5, 0.12), Vector3(-2.52, 0.0, 0.12), Vector3(0.0, 2.86, 0.12)]
	for point: Vector3 in rim_probes:
		var pixel := Vector2i(display.camera.unproject_position(display.screen.to_global(point)))
		var a := screen_image.get_pixelv(pixel)
		var b := no_rim.get_pixelv(pixel)
		rim_delta += absf(a.r - b.r) + absf(a.g - b.g) + absf(a.b - b.b)
	_check(rim_delta > 0.12, "Iridescent rim contributes visible pixels " + key)
	await _frames(2)
	print("EXHIBIT_LAYOUT %s screen=%s art=%s pawn=%s base=%s confirm=%s framebuffer_error=%.3f" % [key, display.visual_rect(), display.image_rect(), _projected_bounds(_preview.stage.hero), _instance_bounds(_preview.stage._hero_base), _preview.confirm_button.get_global_rect(), error / 12.0])


func _exhibit_composition() -> void:
	if _preview.selected_index != 0:
		return
	var display = _preview._card
	var u: float = _preview._unit
	var model := _projected_bounds(_preview.stage.hero).grow(u)
	var base := _instance_bounds(_preview.stage._hero_base).grow(u)
	var art: Rect2 = display.image_rect()
	var window := Rect2(Vector2.ZERO, Vector2(root.size))
	_check(window.encloses(display.visual_rect()) and window.encloses(model) and window.encloses(base), "Exhibit contained in window")
	_check(art.get_area() > model.get_area() * 4.0, "Portrait dominates the small collectible")
	_check(model.size.y < art.size.y * 0.58, "Collectible is clearly smaller than the portrait")
	_check(model.get_center().x > art.get_center().x and model.get_center().y > art.get_center().y, "Toy occupies lower-right foreground")
	var face := _screen_region(Rect2(0.40, 0.12, 0.21, 0.25))
	var costume := _screen_region(Rect2(0.33, 0.37, 0.37, 0.40))
	for shape: Rect2 in [model, base]:
		_check(not shape.intersects(face) and not shape.intersects(costume), "Toy clears original face and main costume")
		_check(not shape.intersects(display.plate_rect()), "Toy clears identity lettering")
		_check(not shape.intersects(_preview.confirm_button.get_global_rect().grow(5 * u)), "Toy and base clear confirm")
		_check(not shape.intersects(_preview._board_rect), "Toy stays clear of choices")
	_check(not art.intersects(_preview.confirm_button.get_global_rect()), "Screen art clear of confirm")
	_check(not display.visual_rect().intersects(_preview._board_rect), "Display stays clear of choice board")
	_check(display.visible and not _preview._hero_name.visible and not _preview._hero_title.visible, "No duplicate identity")
	for index in 6:
		var cell: Rect2 = _preview.cell_rects[index]
		_check(Rect2(cell.position, Vector2(cell.size.x, cell.size.y * 0.80)).grow(2 * u).encloses(_projected_bounds(_preview.stage.pawns[index], 0.172)), "Exhibit grid caption clear %d" % index)


func _upright_snapshot(key: String) -> void:
	var pawn := _projected_bounds(_preview.stage.hero)
	var base := _instance_bounds(_preview.stage._hero_base)
	var entry := {
		"pawn_size": [pawn.size.x, pawn.size.y], "base_size": [base.size.x, base.size.y],
		"scale": var_to_str(_preview.stage.hero.scale), "yaw": _preview.stage.hero.rotation.y,
		"allocation": var_to_str(_preview._pawn_rect.size), "sources": {}}
	for filename in ["character_stage_3d.gd", "carmen_vinyl.gdshader", "pawn_factory.gd", "pawn.gdshader"]:
		entry.sources[filename] = FileAccess.get_sha256("res://character_preview/" + filename)
	_upright_layouts[key] = entry
	if _upright != "after":
		return
	var baseline = JSON.parse_string(FileAccess.get_file_as_string(UPRIGHT + "/before/layouts.json"))
	_check(baseline is Dictionary and baseline.has(key), "Accepted doll size baseline " + key)
	if baseline is Dictionary and baseline.has(key):
		var before: Dictionary = baseline[key]
		for field in ["pawn_size", "base_size"]:
			for axis in 2:
				_check(absf(entry[field][axis] - before[field][axis]) < 2.0, "Accepted doll dimensions " + key + field)
		_check(entry.scale == before.scale and is_equal_approx(entry.yaw, before.yaw), "Accepted doll scale and yaw " + key)
		_check(entry.sources == before.sources, "Frozen model, stage and paint sources " + key)
	_upright_composition()


func _upright_composition() -> void:
	var display = _preview._card
	var u: float = _preview._unit
	var housing: Rect2 = display.visual_rect()
	var toy := _projected_bounds(_preview.stage.hero)
	var base := _instance_bounds(_preview.stage._hero_base)
	var union := housing.merge(toy).merge(base)
	_check(display.screen.rotation.is_zero_approx() and display.camera.rotation.is_zero_approx(), "Upright card and camera")
	var tl: Vector2 = display.art_point(Vector2.ZERO)
	var tr: Vector2 = display.art_point(Vector2.RIGHT)
	var bl: Vector2 = display.art_point(Vector2.DOWN)
	_check(absf(tl.y - tr.y) < 0.5 and absf(tl.x - bl.x) < 0.5, "Card edges are horizontal and vertical")
	_check(absf(tl.distance_to(tr) - tl.distance_to(bl)) < 1.0, "Square artwork remains undistorted")
	_check(display.get_global_rect().grow(1).encloses(housing), "Holder fully inside native viewport")
	_check(not housing.intersects(_preview.confirm_button.get_global_rect().grow(5 * u)), "Entire holder clears confirmation")
	var texts: Array[Rect2] = display.text_rects()
	for i in texts.size():
		_check(housing.encloses(texts[i]), "Card text inside holder %d" % i)
		_check(not texts[i].grow(u).intersects(toy) and not texts[i].grow(u).intersects(base), "Toy clears all card typography %d" % i)
		for j in range(i + 1, texts.size()):
			_check(not texts[i].intersects(texts[j]), "Card typography does not overlap")
	if not _preview._portrait:
		var area: Rect2 = _preview._showcase_rect
		_check(area.grow(1).encloses(union), "Whole composition stays in right display area")
		_check(union.size.x / area.size.x >= 0.90 and union.size.y / area.size.y >= 0.88, "Composition fills right display area")
		print("UPRIGHT_FILL: %.3f x %.3f" % [union.size.x / area.size.x, union.size.y / area.size.y])


func _screen_region(uv: Rect2) -> Rect2:
	var display = _preview._card
	var result := Rect2(display.art_point(uv.position), Vector2.ZERO)
	for point: Vector2 in [Vector2(uv.end.x, uv.position.y), uv.end, Vector2(uv.position.x, uv.end.y)]:
		result = result.expand(display.art_point(point))
	return result


func _lanyard_check() -> void:
	var key := "%dx%d" % [root.size.x, root.size.y]
	_step = "lanyard " + key
	await _click(_preview.choice_buttons[0].get_global_rect().get_center())
	await create_timer(0.3).timeout
	var card = _preview._card
	card.cancel_drag()
	_check(card.PORTRAIT.resource_path == "res://card/image/carmen.png", "New portrait source " + key)
	_check(card.PORTRAIT.get_size() == Vector2(1024, 1536), "Imported portrait dimensions " + key)
	_check(is_equal_approx(card.artwork.mesh.size.aspect(), 2.0 / 3.0), "Complete 2:3 artwork " + key)
	_check(card._card.get_node_or_null("IntegralToe") == null, "No standing base " + key)
	_lanyard_bounds(key)
	var pawn := _projected_bounds(_preview.stage.hero)
	var base := _instance_bounds(_preview.stage._hero_base)
	var baseline = JSON.parse_string(FileAccess.get_file_as_string(UPRIGHT + "/before/layouts.json"))
	_check(baseline is Dictionary and baseline.has(key), "Accepted pawn baseline " + key)
	if not _showcase and baseline is Dictionary and baseline.has(key):
		var saved: Dictionary = baseline[key]
		_check(var_to_str(_preview.stage.hero.scale) == saved.scale, "Frozen pawn scale " + key)
		_check(is_equal_approx(_preview.stage.hero.rotation.y, saved.yaw), "Frozen pawn yaw " + key)
		for axis in 2:
			_check(absf(pawn.size[axis] - saved.pawn_size[axis]) < 2.0, "Frozen pawn dimensions " + key)
			_check(absf(base.size[axis] - saved.base_size[axis]) < 2.0, "Frozen pedestal dimensions " + key)
		for filename: String in saved.sources:
			_check(FileAccess.get_sha256("res://character_preview/" + filename) == saved.sources[filename], "Protected source " + filename)
	if _showcase:
		_showcase_layout_check(key)
		await _foreground_check(key)
	await _capture("lanyard_" + key + "_initial.png")
	await _lanyard_pixels(key)
	if root.size == Vector2i(2048, 1152):
		if _showcase:
			await _showcase_material_check()
		else:
			await _lanyard_material_check()
	var start: Vector2 = card.art_point(Vector2(0.5, 0.5))
	var center: Vector2 = card.motion.center
	_mouse_button(start, true)
	_check(card.motion.dragging, "Mouse grabs card " + key)
	_check(card.motion.center.distance_to(center) < 0.0001, "No centre snap on press " + key)
	for step in 12:
		_mouse_move(start + Vector2(-35, -18) * (step + 1) / 12.0)
		await create_timer(0.016).timeout
		_lanyard_bounds(key)
	var dragged: Vector2 = card.motion.center
	_check(dragged.distance_to(center) > 0.02, "Drag visibly moves card " + key)
	await _capture("lanyard_" + key + "_drag.png")
	await _lanyard_pixels(key + "_drag")
	_mouse_button(start + Vector2(-35, -18), false)
	_check(not card.motion.dragging, "Mouse release clears grab " + key)
	await create_timer(0.20).timeout
	_check(card.motion.center.distance_to(dragged) > 0.001, "Release keeps moving " + key)
	_lanyard_bounds(key)
	await _capture("lanyard_" + key + "_swing.png")
	var settle_elapsed := 0.0
	while not card.motion.sleeping and settle_elapsed < 8.0:
		await process_frame
		settle_elapsed += root.get_process_delta_time()
		_lanyard_bounds(key)
	_check(card.motion.sleeping, "Motion settles and sleeps " + key)
	_lanyard_bounds(key)
	await _capture("lanyard_" + key + "_settled.png")
	# Preserve the actual edge grab offset; continue outside the local viewport.
	var edge: Vector2 = card.art_point(Vector2(0.85, 0.65))
	_mouse_button(edge, true)
	_check(card.motion.dragging and card.motion.grab_local.x > 0.5, "Local edge grip " + key)
	_mouse_move(Vector2(-300, -300))
	await _frames(4)
	_lanyard_bounds(key)
	_mouse_button(Vector2(-300, -300), false)
	_check(not card.motion.dragging, "Release outside host " + key)
	card.cancel_drag()
	var touch_point: Vector2 = card.art_point(Vector2(0.5, 0.5))
	_touch_event(touch_point, 3, true)
	_check(card._pointer == 3, "Touch owns grab " + key)
	_touch_event(touch_point, 4, true)
	var seen := _touch_probe.releases
	_touch_event(touch_point, 4, false)
	_check(_touch_probe.releases == seen + 1, "Unowned touch release passes through " + key)
	_check(card._pointer == 3, "Second finger cannot steal or release " + key)
	var touch_motion := InputEventScreenDrag.new()
	touch_motion.index = 3
	touch_motion.position = touch_point + Vector2(-25, -15)
	Input.parse_input_event(touch_motion)
	await _frames(3)
	_lanyard_bounds(key)
	_touch_event(touch_point, 3, false, true)
	_check(card._pointer == -2 and not card.motion.dragging, "Touch cancellation resets " + key)
	_mouse_button(card.art_point(Vector2(0.5, 0.5)), true)
	root.focus_exited.emit()
	_check(not card.motion.dragging and card.motion.sleeping, "Focus loss cancels " + key)
	_mouse_button(card.art_point(Vector2(0.5, 0.5)), true)
	_preview._select(1, false)
	_check(not card.motion.dragging and not card.visible, "Selection cancels drag " + key)
	_preview._select(0, false)
	await _frames(2)
	_mouse_button(card.art_point(Vector2(0.5, 0.5)), true)
	var original_size := root.size
	root.size = original_size + Vector2i(2, 2)
	await _frames(4)
	_check(not card.motion.dragging, "Native resize cancels drag " + key)
	root.size = original_size
	await _frames(4)
	_mouse_button(card.art_point(Vector2(0.5, 0.5)), true)
	_preview._layout()
	_check(not card.motion.dragging, "Layout change cancels drag " + key)
	_mouse_button(card.art_point(Vector2(0.5, 0.5)), true)
	_preview.hide()
	_check(not card.motion.dragging, "Hidden parent cancels drag " + key)
	_preview.show()
	await _frames(2)
	_check(card.motion.sleeping and card.is_visible_in_tree(), "Shown parent restores stable card " + key)
	_lanyard_layouts[key] = {"host": var_to_str(card.get_global_rect()), "card": var_to_str(card.card_rect()),
		"visual": var_to_str(card.visual_rect()), "pawn": var_to_str(pawn), "link_error": card.motion.max_link_error(), "settle_seconds": settle_elapsed}
	if root.size == Vector2i(1280, 720):
		await _lanyard_back_check()
		if _showcase:
			await _showcase_sampling_check()
	print("LANYARD_LAYOUT " + key + " " + JSON.stringify(_lanyard_layouts[key]))


func _showcase_sampling_check() -> void:
	var card = _preview._card
	card.cancel_drag()
	var start: Vector2 = card.motion.center
	var frames: Array[Image] = []
	var timing := Time.get_ticks_usec()
	# Identical transforms, with a higher-sampling reference for edge-error analysis.
	for quality: String in ["native", "high", "reference"]:
		card.render_scale = 1.0 if quality == "native" else (2.0 if quality == "high" else 4.0)
		card.viewport_3d.msaa_3d = Viewport.MSAA_2X if quality == "native" else (Viewport.MSAA_4X if quality == "high" else Viewport.MSAA_8X)
		card._update_render_size()
		for step in 8:
			card.motion.center = start + Vector2(0.012 * step, 0.03 * sin(step * 0.3))
			card.motion.angle = -0.11 + step * 0.023
			card.motion.yaw = -0.08 + step * 0.018
			card._apply_pose()
			await _render_frame()
			var image: Image = card.viewport_3d.get_texture().get_image()
			image.resize(roundi(card.size.x), roundi(card.size.y), Image.INTERPOLATE_BILINEAR)
			frames.append(image)
			_check(image.save_png(_output.path_join("aa_%s_%02d.png" % [quality, step])) == OK, "AA sequence frame saved")
			var grip: Vector2 = card.art_point(Vector2(0.80, 0.38))
			var local: Vector3 = card.card_hit(grip)
			_check(local.is_finite() and absf(local.x - card.artwork.mesh.size.x * 0.30) < 0.002, "Supersampled tilted hit mapping")
		var viewport_rid: RID = card.viewport_3d.get_viewport_rid()
		RenderingServer.viewport_set_measure_render_time(viewport_rid, true)
		for step in 5:
			await _render_frame()
		var frame_times: Array[float] = []
		var gpu_times: Array[float] = []
		for step in 30:
			await process_frame
			var begin := Time.get_ticks_usec()
			RenderingServer.force_draw(false)
			frame_times.append((Time.get_ticks_usec() - begin) / 1000.0)
			gpu_times.append(RenderingServer.viewport_get_measured_render_time_gpu(viewport_rid))
		frame_times.sort()
		gpu_times.sort()
		print("SHOWCASE_FRAME_COST quality=", quality, " forced_draw_wall_ms median=", frame_times[15], " p95=", frame_times[28], " card_gpu_ms median=", gpu_times[15], " p95=", gpu_times[28])
	var coverage: Array[int] = []
	for image: Image in [frames[0], frames[8]]:
		var partial := 0
		for y in image.get_height():
			for x in image.get_width():
				var alpha := image.get_pixel(x, y).a
				if alpha > 0.04 and alpha < 0.96:
					partial += 1
		coverage.append(partial)
	_check(coverage[1] > coverage[0], "Supersampling creates finer silhouette coverage")
	print("SHOWCASE_AA partial_pixels=", coverage, " capture_seconds=", (Time.get_ticks_usec() - timing) / 1000000.0)
	card.render_scale = 2.0
	card.viewport_3d.msaa_3d = Viewport.MSAA_4X
	card._update_render_size()
	card.cancel_drag()
	await _frames(2)


func _foreground_check(key: String) -> void:
	var card = _preview._card
	var stage = _preview.stage
	_bench_layout_check()
	if root.size == Vector2i(1280, 720):
		var rid: RID = stage.viewport_3d.get_viewport_rid()
		RenderingServer.viewport_set_measure_render_time(rid, true)
		await _frames(5)
		var gpu: Array[float] = []
		for sample in 30:
			await _render_frame()
			gpu.append(RenderingServer.viewport_get_measured_render_time_gpu(rid))
		gpu.sort()
		RenderingServer.viewport_set_measure_render_time(rid, false)
		print("FOREGROUND_STAGE_GPU median_ms=", gpu[15], " p95_ms=", gpu[28])
	for index in 6:
		var pawn: Node3D = stage.pawns[index]
		var model: MeshInstance3D = pawn.get_child(0)
		var cell: Rect2 = _preview.cell_rects[index]
		var bounds := _projected_bounds(pawn)
		_check(cell.grow(1).encloses(_preview.choice_buttons[index].get_global_rect()), "Choice hit rect stays within cell %s/%d" % [key, index])
		for other in range(index):
			_check(not _preview.choice_buttons[index].get_global_rect().intersects(_preview.choice_buttons[other].get_global_rect()), "Choice buttons do not overlap %s/%d/%d" % [key, index, other])
		_check(cell.grow(1).encloses(bounds), "Detailed pawn inside cell %s/%d" % [key, index])
		_check(bounds.end.y < cell.position.y + cell.size.y * 0.80, "Detailed pawn clear of name %s/%d" % [key, index])
		var bench: MeshInstance3D = stage._benches[index / 3]
		var contact: Vector3 = bench.to_local(pawn.to_global(pawn.get_meta("seat_contact")))
		_check(absf(contact.y) < 0.001 and absf(contact.z) < 0.001, "Hips rest on shared bench %s/%d" % [key, index])
		_check(pawn.get_child_count() == 1 and is_zero_approx(model.position.y), "No individual stone pedestal %d" % index)
	var hero_model: MeshInstance3D = stage.hero.get_child(0)
	_check(is_zero_approx(hero_model.position.y + hero_model.mesh.get_aabb().position.y), "Hero sole contacts plinth " + key)
	# Actual alpha from only the foreground meshes, in native window coordinates.
	for bench: MeshInstance3D in stage._benches:
		bench.hide()
	stage._selection_ring.hide()
	for pawn: Node3D in stage.pawns:
		pawn.hide()
	stage._hero_base.hide()
	await _render_frame()
	var figure: Image = stage.viewport_3d.get_texture().get_image()
	stage._hero_base.show()
	await _render_frame()
	var foreground: Image = stage.viewport_3d.get_texture().get_image()
	_check(figure.save_png(_output.path_join("foreground_" + key + "_figure.png")) == OK, "Figure alpha frame saved " + key)
	_check(foreground.save_png(_output.path_join("foreground_" + key + "_stage.png")) == OK, "Foreground alpha frame saved " + key)
	for bench: MeshInstance3D in stage._benches:
		bench.show()
	stage._selection_ring.show()
	for pawn: Node3D in stage.pawns:
		pawn.show()
	await _render_frame()
	var combined: Image = root.get_texture().get_image()
	var back: Image = card.viewport_3d.get_texture().get_image()
	back.resize(roundi(card.size.x), roundi(card.size.y), Image.INTERPOLATE_BILINEAR)
	var region: Rect2 = stage.foreground_bounds().intersection(card.card_rect())
	var overlap := 0
	var figure_overlap := 0
	var composited := 0
	var blocked := Vector2.INF
	var transparent := Vector2.INF
	for y in range(maxi(0, ceili(region.position.y)), mini(root.size.y, floori(region.end.y))):
		for x in range(maxi(0, ceili(region.position.x)), mini(root.size.x, floori(region.end.x))):
			var point := Vector2(x, y)
			var pixel := Vector2i(point - card.global_position)
			if pixel.x < 0 or pixel.y < 0 or pixel.x >= back.get_width() or pixel.y >= back.get_height():
				continue
			if back.get_pixelv(pixel).a < 0.95:
				continue
			var front := foreground.get_pixel(x, y)
			if front.a > 0.98:
				overlap += 1
				if figure.get_pixel(x, y).a > 0.98:
					figure_overlap += 1
					# Pixel corners can lie just outside an antialiased silhouette.
					if not blocked.is_finite() and stage.foreground_hit(point + Vector2(0.5, 0.5)) and card.card_hit(point + Vector2(0.5, 0.5)).is_finite():
						blocked = point + Vector2(0.5, 0.5)
				var actual := combined.get_pixel(x, y)
				if Vector3(actual.r - front.r, actual.g - front.g, actual.b - front.b).length() < 0.08:
					composited += 1
			elif front.a < 0.01 and not transparent.is_finite() and card.card_hit(point).is_finite() and not _preview._speech.contains_point(point):
				transparent = point
	_check(figure_overlap > 5, "Actual figure silhouette overlaps sleeve " + key + " pixels=" + str(figure_overlap))
	_check(overlap > 10 and composited > overlap * 0.85, "Foreground pixels cover background card " + key)
	_check(stage.foreground_bounds().end.x > card.card_rect().end.x, "Foreground extends beyond card " + key)
	_check(blocked.is_finite(), "Opaque overlap has a hittable interior pixel " + key)
	if blocked.is_finite():
		_check(stage.foreground_hit(blocked) and card.card_hit(blocked).is_finite(), "Triangle hit agrees with overlap pixel " + key)
		_mouse_button(blocked, true)
		_check(not card.motion.dragging, "Mouse cannot grab through toy " + key)
		_mouse_button(blocked, false)
		_touch_event(blocked, 3, true)
		_check(card._pointer == -2, "Touch cannot grab through toy " + key)
		_touch_event(blocked, 3, false)
		var fixed: Transform3D = stage.hero.transform
		for touch in [false, true]:
			card.cancel_drag()
			Input.flush_buffered_events()
			var exposed: Vector2 = card.art_point(Vector2(0.5, 0.45))
			if touch:
				_touch_event(exposed, 3, true)
				var event := InputEventScreenDrag.new()
				event.index = 3
				event.position = blocked
				Input.parse_input_event(event)
			else:
				_mouse_button(exposed, true)
				_mouse_move(blocked)
			await create_timer(0.05).timeout
			_check(card.motion.dragging and card._pointer == (3 if touch else -1), "Owner retained across foreground " + key)
			_check(stage.hero.transform.is_equal_approx(fixed), "Toy stays planted during card drag " + key)
			if touch:
				_touch_event(blocked, 3, false)
			else:
				_mouse_button(blocked, false)
			_check(not card.motion.dragging, "Release across foreground " + key)
			card.cancel_drag()
	if transparent.is_finite():
		_mouse_button(transparent, true)
		_check(card.motion.dragging, "Transparent foreground space remains draggable " + key)
		_mouse_button(transparent, false)
		card.cancel_drag()
	else:
		_check(false, "Transparent overlap test point exists " + key)
	print("FOREGROUND_PIXELS ", key, " figure=", figure_overlap, " total=", overlap, " composite=", composited)


func _showcase_layout_check(key: String) -> void:
	var card = _preview._card
	var speech = _preview._speech
	_check(speech.visible and speech.label.text == "别惹老娘。\n我的船，我说了算。", "Exact Carmen speech and explicit two lines " + key)
	_check(speech.label.get_line_count() == 2, "Speech renders as two lines " + key)
	_check(speech.label.get_minimum_size().x <= speech.label.size.x + 1, "Speech fits without clipping " + key)
	var tail_tip: Vector2 = speech.global_position + Vector2(speech._anchor.x, clampf(speech._anchor.y - 8, speech.size.y + 7, speech.size.y + 24))
	var speech_bounds: Rect2 = speech.get_global_rect().expand(tail_tip)
	_check(Rect2(Vector2.ZERO, Vector2(root.size)).encloses(speech_bounds), "Speech and tail inside window " + key)
	_check(not speech_bounds.intersects(card.image_rect()), "Speech and tail clear complete artwork " + key)
	_check(not speech_bounds.intersects(_projected_bounds(_preview.stage.hero)), "Speech and tail clear figure " + key)
	_check(not speech_bounds.intersects(_preview.confirm_button.get_global_rect()), "Speech and tail clear confirm " + key)
	_check(speech.mouse_filter == Control.MOUSE_FILTER_IGNORE and speech.label.mouse_filter == Control.MOUSE_FILTER_IGNORE, "Speech does not intercept input " + key)
	_check(absf(card._card.rotation.y) > 0.15, "Resting card reveals sidewall " + key)
	_check(card.viewport_3d.size.x >= card.size.x * 1.5, "Card uses supersampled render target " + key)
	_check(card.viewport_3d.size.x * card.viewport_3d.size.y <= 4010000, "Card render target bounded " + key)
	# Shared benches deliberately take more room than the historical 2x3 layout.
	# Check current readability, not a growth ratio against the old wide card host.
	_check(card.image_rect().size.y >= (95.0 if root.size.y <= 600 else 180.0), "Card artwork stays readable " + key)
	print("SHOWCASE_SIZE ", key, " image=", card.image_rect(), " buffer=", card.viewport_3d.size, " speech=", speech.get_global_rect())
	var sources := FileAccess.get_file_as_string("res://character_preview/character_stage_3d.gd")
	_check(not sources.contains("dice3d/"), "Selection stage is independent of dice materials")
	var hashes = JSON.parse_string(FileAccess.get_file_as_string(OUTPUT + "/showcase/before/protected.json"))
	_check(hashes is Dictionary and not hashes.is_empty(), "Protected source manifest is valid")
	if not hashes is Dictionary:
		return
	for file: String in hashes:
		_check(FileAccess.get_sha256("res://" + file) == hashes[file], "Protected original unchanged: " + file)


func _showcase_material_check() -> void:
	var card = _preview._card
	var shell: MeshInstance3D = card._card.get_node("ThinSleeve")
	var crown: MeshInstance3D = card._card.get_node("RoundedSilverCrown")
	var seal: MeshInstance3D = card._card.get_node("RecessedSeal")
	_check(shell.mesh.get_aabb().size.z >= 0.20, "Thick modeled sleeve sidewall")
	_check(crown.mesh.get_aabb().end.z - card.artwork.position.z >= 0.035, "Artwork recessed below crown")
	_check(seal.mesh.get_aabb().size.z > 0.03, "Deep sloped inner seal")
	for part: MeshInstance3D in [shell, crown, card.rim, card._card.get_node("Eyelet")]:
		var material: StandardMaterial3D = part.material_override
		_check(material.metallic > 0.9 and material.albedo_color.g <= maxf(material.albedo_color.r, material.albedo_color.b), "Neutral metal " + str(part.name))
	for part: MeshInstance3D in card._geometry:
		_showcase_mesh_check(part.mesh, str(part.name))
	for part: MeshInstance3D in _preview.stage._benches + [_preview.stage._hero_base, _preview.stage._selection_ring]:
		_showcase_mesh_check(part.mesh, str(part.name))
	for index in 6:
		for presentation in [_preview.stage.PawnFactory.Presentation.CHOICE, _preview.stage.PawnFactory.Presentation.DISPLAY]:
			var pawn: Node3D = _preview.stage.PawnFactory.build(index, presentation)
			_showcase_mesh_check(pawn.get_child(0).mesh, "Pawn %d/%d" % [index, presentation])
			pawn.free()
	var tones: Array[float] = []
	for yaw: float in [-0.05, card.REST_YAW, 0.39]:
		card._card.rotation.y = yaw
		await _render_frame()
		var image: Image = card.viewport_3d.get_texture().get_image()
		var point := Vector3(-1.31, 0, 0.0925)
		var pixel := Vector2i(card.camera.unproject_position(card._card.to_global(point)))
		var color := image.get_pixelv(pixel)
		_check(color.a > 0.9, "Broad silver bevel has opaque pixels at " + str(yaw))
		_check(color.g - maxf(color.r, color.b) < 0.025, "Silver framebuffer remains neutral")
		tones.append((color.r + color.g + color.b) / 3.0)
		_check(image.get_pixel(0, 0).a < 0.01, "Studio reflection preserves transparency")
		_check(image.save_png(_output.path_join("showcase_material_%d.png" % roundi(rad_to_deg(yaw)))) == OK, "Current material angle saved")
		if is_equal_approx(yaw, card.REST_YAW):
			var front: Vector2 = card.project_point(card._card.to_global(Vector3(-1.32, 0, 0.075)))
			var back: Vector2 = card.project_point(card._card.to_global(Vector3(-1.32, 0, -0.125)))
			var side_pixel := Vector2i(card.camera.unproject_position(card._card.to_global(Vector3(-1.32, 0, -0.025))))
			_check(front.distance_to(back) > 2.0 and image.get_pixelv(side_pixel).a > 0.9, "Sidewall spans visible pixels at rest")
			print("SHOWCASE_SIDEWALL display_pixels=", front.distance_to(back))
	_check(absf(tones[0] - tones[2]) > 0.025, "Current silver bevel reflects changing angle")
	print("SHOWCASE_MATERIAL edge_tones=", tones)
	card.cancel_drag()
	await _frames(2)


func _showcase_mesh_check(mesh: Mesh, key: String) -> void:
	var invalid := 0
	var winding := 0
	for surface in mesh.get_surface_count():
		var arrays := mesh.surface_get_arrays(surface)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX] if arrays[Mesh.ARRAY_INDEX] != null else PackedInt32Array()
		for i in vertices.size():
			if not vertices[i].is_finite() or not normals[i].is_finite() or absf(normals[i].length() - 1.0) > 0.001:
				invalid += 1
		for i in range(0, vertices.size() if indices.is_empty() else indices.size(), 3):
			var a := i if indices.is_empty() else indices[i]
			var b := i + 1 if indices.is_empty() else indices[i + 1]
			var c := i + 2 if indices.is_empty() else indices[i + 2]
			var cross := (vertices[b] - vertices[a]).cross(vertices[c] - vertices[a])
			if cross.length_squared() > 0.000000000001 and cross.normalized().dot((normals[a] + normals[b] + normals[c]).normalized()) > 0.02:
				winding += 1
	_check(invalid == 0 and winding == 0, "Finite unit normals and clockwise winding " + key + " invalid=%d winding=%d" % [invalid, winding])


func _lanyard_material_check() -> void:
	var card = _preview._card
	var shell: MeshInstance3D = card._card.get_node("ThinSleeve")
	var shoulder: MeshInstance3D = card._card.get_node("MachinedSilverShoulder")
	var seal: MeshInstance3D = card._card.get_node("RecessedSeal")
	_check(shell.mesh.get_aabb().size.z >= 0.10, "Sleeve has modeled sidewall depth")
	_check(shoulder.mesh.get_aabb().end.z > card.artwork.position.z + 0.035, "Art is recessed below silver shoulder")
	_check(seal.mesh.get_aabb().size.z > 0.03, "Recess has a sloped inner wall")
	for part: MeshInstance3D in [shell, shoulder, card.rim, card._card.get_node("Eyelet"), card._card.get_node("SplitRing")]:
		var material: StandardMaterial3D = part.material_override
		var color := material.albedo_color
		_check(color.g <= maxf(color.r, color.b), "Neutral material without green tint: " + str(part.name))
		_check(material.metallic > 0.9, "Metal response: " + str(part.name))
	_check(card._strap_material.normal_enabled and card._strap_material.roughness > 0.85, "Matte woven charcoal strap")
	var samples: Array = []
	# Diagnostic poses only: production suspension angles and pointer logic stay untouched.
	for yaw in [-0.18, 0.0, 0.18]:
		card._card.rotation.y = yaw
		await _render_frame()
		var frame: Image = card.viewport_3d.get_texture().get_image()
		var tones: Array[float] = []
		for point: Vector3 in [Vector3(-1.26, 0, 0.075), Vector3(1.26, 0, 0.075), Vector3(0, 1.88, 0.075), Vector3(0, -1.88, 0.075)]:
			var pixel := Vector2i(card.camera.unproject_position(card._card.to_global(point)))
			var color := frame.get_pixelv(pixel)
			_check(color.a > 0.9, "Silver shoulder reaches framebuffer at yaw " + str(yaw))
			_check(color.g - maxf(color.r, color.b) < 0.025, "Rendered shoulder stays neutral at yaw " + str(yaw))
			tones.append((color.r + color.g + color.b) / 3.0)
		samples.append(tones)
		_check(frame.get_pixel(0, 0).a < 0.01, "Reflection sky preserves transparent background")
		_check(frame.save_png(_output.path_join("material_yaw_%d.png" % roundi(rad_to_deg(yaw)))) == OK, "Material angle frame saved")
		await _lanyard_pixels("material_yaw_%d" % roundi(rad_to_deg(yaw)))
	var angular_change := 0.0
	for edge in 4:
		angular_change = maxf(angular_change, absf(samples[0][edge] - samples[2][edge]))
	_check(angular_change > 0.025, "Metal highlights respond to actual card angle")
	print("LANYARD_MATERIAL tones=", samples, " angular_change=", angular_change)
	card.cancel_drag()
	await _frames(2)


func _lanyard_back_check() -> void:
	var card = _preview._card
	card.cancel_drag()
	card._card.rotation.y = PI
	await _capture("lanyard_reverse_material.png")
	var back: Image = card.viewport_3d.get_texture().get_image()
	var center := Vector2i(card.camera.unproject_position(card._card.global_position + Vector3(0.35, 0.5, 0)))
	_check(back.get_pixelv(center).a > 0.9, "Sleeve has an opaque reverse face")
	card.cancel_drag()
	# Removing a grabbed node must not leave a held pointer on a later instance.
	var spare = card.get_script().new()
	root.add_child(spare)
	spare.arrange(Rect2(5, 5, 200, 300), 1.0)
	await _frames(2)
	spare._begin_drag(spare.art_point(Vector2(0.5, 0.5)), -1)
	var state = spare.motion
	_check(state.dragging, "Spare card grabbed before removal")
	spare.queue_free()
	await _frames(2)
	_check(not state.dragging and state.sleeping, "Removal cancels pointer and motion")


func _lanyard_bounds(key: String) -> void:
	var card = _preview._card
	if not card.get_global_rect().grow(0.5).encloses(card.visual_rect()) or card.motion.max_link_error() >= 0.04:
		print("LANYARD_DIAGNOSTIC ", key, " host=", card.get_global_rect(), " visual=", card.visual_rect(), " center=", card.motion.center, " angle=", card.motion.angle, " nodes=", card.motion.nodes, " grab=", card.motion.dragging, " error=", card.motion.max_link_error())
	_check(card.motion.center.is_finite() and is_finite(card.motion.angle), "Finite lanyard state " + key)
	_check(card.get_global_rect().grow(0.5).encloses(card.visual_rect()), "Whole moving card and strap inside host " + key)
	_check(not card.visual_rect().intersects(_preview._board_rect), "Lanyard clear of choice grid " + key)
	_check(not card.visual_rect().intersects(_preview.confirm_button.get_global_rect()), "Lanyard clear of confirm " + key)
	# The resting portrait is unobstructed; a dragged card may pass behind the toy.
	if card.motion.sleeping:
		_check(not card.image_rect().intersects(_projected_bounds(_preview.stage.hero)), "Resting pawn leaves artwork unobstructed " + key)
	_check(card.motion.max_link_error() < 0.04, "Bounded link length error " + key)
	var attach: Vector3 = card._card.to_global(Vector3(0, card.Motion.HANG, 0))
	var end: Vector2 = card.motion.nodes[card.Motion.LINKS]
	_check(Vector2(attach.x, attach.y).distance_to(end) < 0.002, "Strap attached to card " + key)


func _lanyard_pixels(key: String) -> void:
	await _render_frame()
	var card = _preview._card
	var frame := root.get_texture().get_image()
	var reference: Image = card.PORTRAIT.get_image()
	if reference.is_compressed():
		reference.decompress()
	var error := 0.0
	for uv: Vector2 in [Vector2(0.18, 0.2), Vector2(0.48, 0.25), Vector2(0.4, 0.5), Vector2(0.2, 0.75)]:
		var actual := frame.get_pixelv(Vector2i(card.art_point(uv)))
		var expected := reference.get_pixelv(Vector2i(uv * Vector2(reference.get_size())))
		error += absf(actual.r - expected.r) + absf(actual.g - expected.g) + absf(actual.b - expected.b)
	_check(error / 12.0 < 0.20, "New artwork reaches framebuffer " + key)
	var isolated: Image = card.viewport_3d.get_texture().get_image()
	_check(isolated.save_png(_output.path_join("lanyard_" + key + "_isolated.png")) == OK, "Isolated card saved " + key)
	var first: Vector2 = card.motion.nodes[0].lerp(card.motion.nodes[1], 0.35)
	var rope_point: Vector2 = card.project_point(Vector3(first.x, first.y, 0.08))
	var rope_pixel := Vector2i((rope_point - card.global_position) * Vector2(card.viewport_3d.size) / card.size)
	_check(isolated.get_pixelv(rope_pixel).a > 0.5, "Strap has visible framebuffer pixels " + key)
	print("LANYARD_PIXELS " + key + " artwork_error=" + str(error / 12.0))


func _mouse_button(point: Vector2, pressed: bool) -> void:
	Input.flush_buffered_events()
	var event := InputEventMouseButton.new()
	event.position = point
	event.global_position = point
	event.button_index = MOUSE_BUTTON_LEFT
	event.pressed = pressed
	Input.parse_input_event(event)
	Input.flush_buffered_events()


func _mouse_move(point: Vector2) -> void:
	var event := InputEventMouseMotion.new()
	event.position = point
	event.global_position = point
	event.button_mask = MOUSE_BUTTON_MASK_LEFT
	Input.parse_input_event(event)
	Input.flush_buffered_events()


func _touch_event(point: Vector2, index: int, pressed: bool, canceled := false) -> void:
	var event := InputEventScreenTouch.new()
	event.position = point
	event.index = index
	event.pressed = pressed
	event.canceled = canceled
	Input.parse_input_event(event)
	Input.flush_buffered_events()


func _save_json(path: String, value: Dictionary) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	_check(file != null, "Can write " + path)
	if file != null:
		file.store_string(JSON.stringify(value, "\t"))
		file.close()


func _check(condition: bool, description: String) -> void:
	if not condition and not _failures.has(description):
		_failures.append(description)
		print("FAIL: " + description)


func _timeout() -> void:
	if not _done:
		push_error("CHARACTER_PREVIEW_TIMEOUT at " + _step + "; window=" + str(root.size))
		_save_json(_output.path_join("result.json"), {"passed": false, "failures": ["Timeout at " + _step], "phase": "timeout"})
		quit(2)
