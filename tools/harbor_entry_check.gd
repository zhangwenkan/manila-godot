extends SceneTree
## Real character-selection entry, bounded to 60 seconds including scene changes.
## Import first, then: godot --headless --path . --script res://tools/harbor_entry_check.gd
## Optional screenshots: godot --path . --rendering-method gl_compatibility --script res://tools/harbor_entry_check.gd -- --preview
## Success requires HARBOR_ENTRY_CHECK completed failures=0 entries=6 exit=0,
## followed by HARBOR_ENTRY_CHECK_PASS; process exit 0 alone is not sufficient.

const ENTRY_SCENE := "res://character_preview/character_select_preview.tscn"
const HARBOR_SCENE := "res://demo/harbor_pixel/harbor_demo.tscn"
const OUTPUT := "res://.godot/harbor_entry_check"
const WATCHDOG_MS := 60000
const CHARACTERS := [
	{"id": "Carmen", "name": "卡门", "avatar": "res://card/image/carmen_avatar.png"},
	{"id": "Li Yunlong", "name": "李云龙", "avatar": "res://card/image/liyunlong_avatar.png"},
	{"id": "Lakan Bautista", "name": "拉坎·巴蒂斯塔", "avatar": "res://card/image/lanka_avatar.png"},
	{"id": "Izefia", "name": "伊泽菲亚", "avatar": "res://card/image/izefia_avatar.png"},
	{"id": "Kage", "name": "影", "avatar": "res://card/image/kage_avatar.png"},
	{"id": "Jack", "name": "杰克", "avatar": "res://card/image/jack_avatar.png"},
]

var _assertions := 0
var _failures: Array[String] = []
var _entries := 0
var _signals: Array[Dictionary] = []
var _started_ms := 0
var _stage := "initialization"
var _done := false
var _preview := false
var _had_meta := false
var _previous_meta: Variant


func _initialize() -> void:
	_started_ms = Time.get_ticks_msec()
	_preview = "--preview" in OS.get_cmdline_user_args()
	_had_meta = has_meta("harbor_character")
	_previous_meta = get_meta("harbor_character") if _had_meta else null
	Engine.max_fps = 60
	call_deferred("_run")


func _process(_delta: float) -> bool:
	if not _done and Time.get_ticks_msec() - _started_ms >= WATCHDOG_MS:
		_check(false, "60s watchdog expired during %s" % _stage)
		_finish(124)
	return false


func _run() -> void:
	if _preview and DisplayServer.get_name() == "headless":
		_check(false, "--preview requires a real renderer")
		_finish()
		return
	root.title = "Harbor character entry check (bounded 60s)"
	root.gui_disable_input = false
	var windows := [Vector2i(1200, 900), Vector2i(1280, 720), Vector2i(720, 1000)]
	for index in CHARACTERS.size():
		var character: Dictionary = CHARACTERS[index]
		_stage = "entry %d character=%s" % [index, character.id]
		root.size = windows[index % windows.size()]
		set_meta("harbor_character", "not-confirmed")
		if not _check(change_scene_to_file(ENTRY_SCENE) == OK, "Character entry scene loads"):
			_finish()
			return
		if not await _wait_scene(ENTRY_SCENE):
			_finish()
			return
		var selector = current_scene
		selector.quit_on_close = false
		selector.character_confirmed.connect(func(id: String, display_name: String):
			_signals.append({"id": id, "name": display_name})
		)
		var previous_signals := _signals.size()
		_check(selector.ROSTER[index].id == character.id and selector.ROSTER[index].name == character.name, "Entry roster matches independent character identity")
		_click(selector.choice_buttons[index].get_global_rect().get_center())
		await _frames(3)
		_check(selector.selected_index == index and selector.confirmed_index == -1, "Real choice button changes selection without confirming")
		_check(get_meta("harbor_character") == "not-confirmed" and current_scene == selector, "Selection alone does not change entry metadata or scene")
		if _preview:
			await _capture("selected_%d" % index)
		# Mouse confirmation and focused keyboard confirmation both use real input.
		if index % 2 == 0:
			var point: Vector2 = selector.confirm_button.get_global_rect().get_center()
			_click(point)
			_click(point)
		else:
			selector.confirm_button.grab_focus()
			_key(KEY_ENTER, true)
			_check(selector.confirmed_index == -1, "Echoed Enter does not confirm a character")
			_key(KEY_ENTER)
		if not await _wait_scene(HARBOR_SCENE):
			_finish()
			return
		var harbor = current_scene
		harbor.auto_ai = false
		_check(_signals.size() == previous_signals + 1 and _signals.back() == {"id": character.id, "name": character.name}, "Confirmation emits exactly once with the chosen identity")
		_check(not is_instance_valid(selector), "change_scene retires the selection scene instead of stacking harbor over it")
		_check(get_meta("harbor_character") == character.id and harbor.character_id == character.id, "Confirmed SceneTree metadata reaches harbor character_id")
		_check(harbor.game.phase == "auction" and harbor.game.voyage == 1, "Real entry starts a fresh auction, not a fixed-master setup")
		_check(harbor.game.players[0].name == character.name, "Selected display name belongs to human player zero")
		var data: Dictionary = harbor.character_status()
		_check(data.name == character.name and data.portrait.resource_path == character.avatar, "Harbor HUD uses selected character avatar and name mapping")
		_check(data.cash == str(harbor.game.players[0].cash) and data.crew == str(harbor.game.players[0].crew), "Entry portrait counters belong to human zero")
		_check(data.harbormaster == (harbor.game.harbormaster == 0), "Master badge derives from model authority, not selected character")
		var cash: int = harbor.game.players[0].cash
		_check(harbor.game.pass_bid(0), "Human may pass first auction after entering")
		await _frames(3)
		data = harbor.character_status()
		_check(harbor.game.current_player != 0 and data.name == character.name and data.portrait.resource_path == character.avatar and data.cash == str(cash), "AI active bidder never takes over the human identity or counters")
		harbor.game.reset(20261013)
		await _frames(3)
		_check(harbor.character_id == character.id and harbor.game.players[0].name == character.name and harbor.character_status().portrait.resource_path == character.avatar, "Reset keeps selected human identity and portrait")
		if _preview:
			await _capture("harbor_%d" % index)
		_entries += 1
		print("HARBOR_ENTRY_CHECK stage=entry complete index=%d character=%s window=%s" % [index, character.id, root.size])
	_check(_entries == 6 and _signals.size() == 6, "All six characters complete one real entry each across three window shapes")
	_finish()


func _wait_scene(path: String) -> bool:
	var deadline := Time.get_ticks_msec() + 10000
	while Time.get_ticks_msec() < deadline:
		await process_frame
		if is_instance_valid(current_scene) and current_scene.scene_file_path == path:
			await _frames(3)
			return _check(current_scene.is_node_ready(), "Requested scene reaches ready: " + path)
	return _check(false, "Scene transition timed out: " + path)


func _click(point: Vector2) -> void:
	var motion := InputEventMouseMotion.new()
	motion.position = point
	motion.global_position = point
	root.push_input(motion, true)
	for pressed in [true, false]:
		var event := InputEventMouseButton.new()
		event.position = point
		event.global_position = point
		event.button_index = MOUSE_BUTTON_LEFT
		event.button_mask = MOUSE_BUTTON_MASK_LEFT if pressed else 0
		event.pressed = pressed
		root.push_input(event, true)


func _key(code: int, is_echo := false) -> void:
	for pressed in [true, false]:
		var event := InputEventKey.new()
		event.keycode = code
		event.physical_keycode = code
		event.pressed = pressed
		event.echo = is_echo and pressed
		root.push_input(event, true)


func _frames(count: int) -> void:
	for _frame in count:
		await process_frame


func _capture(label: String) -> void:
	await RenderingServer.frame_post_draw
	var image: Image = root.get_texture().get_image()
	if not _check(image != null and not image.is_empty(), "Rendered entry screenshot exists"):
		return
	var output := ProjectSettings.globalize_path(OUTPUT)
	if not _check(DirAccess.make_dir_recursive_absolute(output) == OK, "Entry screenshot directory is writable"):
		return
	var path := output.path_join(label + ".png")
	_check(image.save_png(path) == OK, "Entry screenshot saves")
	print("HARBOR_ENTRY_CAPTURE %s" % path)


func _check(condition: bool, message: String) -> bool:
	_assertions += 1
	if not condition:
		_failures.append("%s: %s" % [_stage, message])
		push_error("HARBOR_ENTRY_FAIL %s: %s" % [_stage, message])
	return condition


func _finish(forced_code := -1) -> void:
	if _done:
		return
	_done = true
	var code := forced_code if forced_code >= 0 else (0 if _failures.is_empty() and _entries == 6 else 1)
	print("HARBOR_ENTRY_CHECK completed assertions=%d failures=%d entries=%d elapsed_ms=%d preview=%s exit=%d" % [_assertions, _failures.size(), _entries, Time.get_ticks_msec() - _started_ms, _preview, code])
	print("HARBOR_ENTRY_CHECK_PASS" if code == 0 else "HARBOR_ENTRY_CHECK_FAIL")
	if _had_meta:
		set_meta("harbor_character", _previous_meta)
	elif has_meta("harbor_character"):
		remove_meta("harbor_character")
	quit(code)
