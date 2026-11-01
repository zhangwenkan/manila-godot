extends Control

signal character_confirmed(character_id: String, display_name: String)
signal closed

const Stage = preload("res://character_preview/character_stage_3d.gd")
const CollectibleCard = preload("res://character_preview/carmen_collectible_card.gd")
const SpeechBubble = preload("res://character_preview/character_speech_bubble.gd")
const FONT = preload("res://card/fonts/fusion-pixel-12px-proportional-zh_hans.otf")
const HARBOR_SCENE := "res://demo/harbor_pixel/harbor_demo.tscn"
const ROSTER := [
	{"id": "Carmen", "name": "卡门", "title": "佛朗船长", "color": Color("c99da7"), "note": "海风与长帆，皆听号令。"},
	{"id": "Li Yunlong", "name": "李云龙", "title": "大明武将", "color": Color("92a6ba"), "note": "披甲远航，堂堂正正。"},
	{"id": "Lakan Bautista", "name": "拉坎·巴蒂斯塔", "title": "吕宋商人", "color": Color("c39a70"), "note": "熟悉港口，也熟悉生意。"},
	{"id": "Izefia", "name": "伊泽菲亚", "title": "昆仑乐使", "color": Color("a0d7bd"), "note": "弦声相伴，远渡重洋。"},
	{"id": "Kage", "name": "影", "title": "东瀛忍者", "color": Color("a9a4c0"), "note": "藏身夜色，静候潮起。"},
	{"id": "Jack", "name": "杰克", "title": "西部牛仔", "color": Color("e99a62"), "note": "压低帽檐，再赴一场冒险。"},
]
const PAPER := Color("e8dfbb")
const MUTED := Color("96b0a2")
const GOLD := Color("cfb77e")

var selected_index := 0
var confirmed_index := -1
var quit_on_close := true
var stage
var choice_buttons: Array[Button] = []
var confirm_button: Button
var close_button: Button
var model_comparison_button: Button
var columns := 3
var cell_rects: Array[Rect2] = []
var _title: Label
var _subtitle: Label
var _section: Label
var _counter: Label
var _hero_name: Label
var _hero_title: Label
var _hero_note: Label
var _status: Label
var _hint: Label
var _board_rect := Rect2()
var _hero_rect := Rect2()
var _details_rect := Rect2()
var _unit := 1.0
var _portrait := false
var _grain: ImageTexture
var _ink: Control
var _closing := false
var _card
var _pawn_rect := Rect2()
var _card_mode := false
var _showcase_rect := Rect2()
var _speech
var _speech_region := Rect2()
var _previous_window_min_size := Vector2i.ZERO


func _ready() -> void:
	# Keep native-window layout here; restore the game canvas when entering the harbor.
	_previous_window_min_size = get_window().min_size
	get_window().content_scale_size = Vector2i.ZERO
	get_window().min_size = Vector2i(390, 600)
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_grain = _make_backdrop()
	_card = CollectibleCard.new()
	_card.name = "CarmenCollectibleCard"
	add_child(_card)
	_card.set_identity(ROSTER[0].name, ROSTER[0].title, FONT)
	stage = Stage.new()
	add_child(stage)
	_speech = SpeechBubble.new()
	_speech.name = "CarmenSpeech"
	add_child(_speech)
	stage.hero_pose_changed.connect(_position_speech)
	_card.can_begin_drag = _can_begin_card_drag
	_ink = Control.new()
	_ink.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_ink.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ink.draw.connect(_draw_ink)
	add_child(_ink)
	_title = _label("选择你的角色", 34, PAPER)
	_subtitle = _label("MANILA  /  六位旅人 · 一场远航", 12, MUTED)
	_section = _label("港口候船室", 16, GOLD)
	_counter = _label("", 13, MUTED)
	_hero_name = _label("", 34, PAPER)
	_hero_title = _label("", 16, GOLD)
	_hero_note = _label("", 14, MUTED)
	_status = _label("确认角色后进入港口", 12, MUTED)
	_hint = _label("点击选择  /  方向键切换  /  Enter 确认", 12, MUTED)
	for i in ROSTER.size():
		var button := Button.new()
		button.name = "Choose%d" % i
		button.text = ROSTER[i].name
		button.alignment = HORIZONTAL_ALIGNMENT_CENTER
		button.add_theme_font_override("font", FONT)
		button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		button.pressed.connect(_select.bind(i, true))
		button.mouse_entered.connect(_redraw)
		button.mouse_exited.connect(_redraw)
		button.focus_entered.connect(_redraw)
		button.focus_exited.connect(_redraw)
		button.gui_input.connect(_choice_input.bind(i))
		button.add_theme_color_override("font_color", MUTED)
		button.add_theme_color_override("font_hover_color", PAPER)
		button.add_theme_color_override("font_focus_color", PAPER)
		button.add_theme_color_override("font_pressed_color", GOLD)
		for style_name in ["normal", "hover", "pressed", "focus"]:
			button.add_theme_stylebox_override(style_name, StyleBoxEmpty.new())
		add_child(button)
		choice_buttons.append(button)
	confirm_button = _button("确认角色  →", true)
	confirm_button.name = "ConfirmCharacter"
	confirm_button.pressed.connect(_confirm)
	close_button = _button("退出  ×", false)
	close_button.name = "ClosePreview"
	close_button.pressed.connect(close)
	model_comparison_button = _button("卡门：GLB ⇄", false)
	model_comparison_button.name = "ToggleCarmenModel"
	model_comparison_button.tooltip_text = "在原座位切换卡门原版与 GLB；右侧棋子保持不变"
	model_comparison_button.pressed.connect(_toggle_carmen_model)
	resized.connect(_layout)
	_layout()
	_select(0, false)


func _label(text: String, font_size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.add_theme_font_override("font", FONT)
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	add_child(label)
	return label


func _button(text: String, primary: bool) -> Button:
	var button := Button.new()
	button.text = text
	button.add_theme_font_override("font", FONT)
	button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	button.add_theme_color_override("font_color", Color("2d3830") if primary else PAPER)
	button.add_theme_color_override("font_hover_color", Color("172e29") if primary else Color.WHITE)
	button.add_theme_color_override("font_pressed_color", Color("172e29") if primary else GOLD)
	for state in ["normal", "hover", "pressed", "focus"]:
		var box := StyleBoxFlat.new()
		box.bg_color = Color("d9bf83") if primary else Color("264039")
		if state == "hover":
			box.bg_color = box.bg_color.lightened(0.12)
		if state == "pressed":
			box.bg_color = box.bg_color.darkened(0.12)
		box.set_border_width_all(2)
		box.border_color = Color("f3dfac") if primary else Color("536b58")
		box.shadow_color = Color("101f1d")
		box.shadow_size = 0 if state == "pressed" else 4
		box.shadow_offset = Vector2(0, 3)
		if state == "focus":
			box.bg_color = Color.TRANSPARENT
			box.border_color = Color("fff1be")
			box.set_border_width_all(3)
		button.add_theme_stylebox_override(state, box)
	add_child(button)
	return button


func _layout() -> void:
	if not is_instance_valid(stage) or size.x < 1:
		return
	_portrait = size.x / size.y < 1.15
	_unit = clampf(minf(size.x / (768.0 if _portrait else 1280.0), size.y / (1024.0 if _portrait else 720.0)), 0.75, 2.0)
	var u := _unit
	var margin := 36.0 * u
	_title.position = Vector2(margin, 24 * u)
	_title.size = Vector2(size.x - 180 * u, 46 * u)
	_title.add_theme_font_size_override("font_size", int(34 * u))
	_subtitle.position = Vector2(margin + 2 * u, 72 * u)
	_subtitle.size = Vector2(size.x - 150 * u, 22 * u)
	_subtitle.add_theme_font_size_override("font_size", int(12 * u))
	_subtitle.text = "MANILA / 六位旅人" if _portrait and size.x < 550 else "MANILA  /  六位旅人 · 一场远航"
	close_button.position = Vector2(size.x - margin - 96 * u, 36 * u)
	close_button.size = Vector2(96 * u, 38 * u)
	close_button.add_theme_font_size_override("font_size", int(14 * u))
	var content_top := 126 * u
	var footer_height := 76 * u
	cell_rects.clear()
	columns = 3
	if _portrait:
		var focus_height := minf(285 * u, size.y * 0.30)
		if selected_index == 0:
			# Reserve room for two readable bench rows even in a short window.
			focus_height = minf(size.x * 1.04, size.y * 0.42)
			focus_height = minf(focus_height, size.y - content_top - footer_height - 40 * u - 220.0)
		_hero_rect = Rect2(margin, content_top, size.x * 0.41, focus_height)
		_details_rect = Rect2(size.x * 0.49, content_top + 25 * u, size.x * 0.51 - margin, focus_height - 20 * u)
		_board_rect = Rect2(margin, content_top + focus_height + 40 * u, size.x - margin * 2, size.y - content_top - focus_height - 40 * u - footer_height)
	else:
		var board_width := (size.x - margin * 3) * 0.50
		_board_rect = Rect2(margin, content_top + 34 * u, board_width, size.y - content_top - 34 * u - footer_height)
		var right_x := _board_rect.end.x + margin
		var right_w := size.x - right_x - margin
		_hero_rect = Rect2(right_x, content_top + 4 * u, right_w, _board_rect.size.y * 0.58)
		_details_rect = Rect2(right_x, _hero_rect.end.y + 16 * u, right_w, _board_rect.end.y - _hero_rect.end.y - 16 * u)
	var rows := 2
	var padding := Vector2(8 * u, 8 * u)
	var inner := _board_rect.grow_individual(-padding.x, -padding.y, -padding.x, -padding.y)
	var cell_size := inner.size / Vector2(columns, rows)
	for i in 6:
		var rect := Rect2(inner.position + Vector2(i % columns, i / columns) * cell_size, cell_size)
		cell_rects.append(rect)
		var button := choice_buttons[i]
		button.position = rect.position.round()
		button.size = rect.end.round() - button.position
		var caption_size := int((17 if i != 2 else 14) * u)
		while caption_size > 9 and FONT.get_string_size(button.text, HORIZONTAL_ALIGNMENT_LEFT, -1, caption_size).x > rect.size.x - 6 * u:
			caption_size -= 1
		button.add_theme_font_size_override("font_size", caption_size)
		# Empty style margins place the caption below the projected figure.
		for style_name in ["normal", "hover", "pressed", "focus"]:
			var empty := StyleBoxEmpty.new()
			empty.content_margin_top = minf(rect.size.y * 0.80, rect.size.y - FONT.get_height(button.get_theme_font_size("font_size")) - 4 * u)
			empty.content_margin_bottom = 4 * u
			button.add_theme_stylebox_override(style_name, empty)
		button.size = rect.end.round() - button.position
	_section.position = Vector2(_board_rect.position.x + 8 * u, _board_rect.position.y - 30 * u)
	_section.size = Vector2(minf(180 * u, _board_rect.size.x * 0.48), 24 * u)
	_section.add_theme_font_size_override("font_size", int(16 * u))
	_counter.position = Vector2(_board_rect.end.x - 140 * u, _section.position.y)
	_counter.size = Vector2(130 * u, 24 * u)
	_counter.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_counter.add_theme_font_size_override("font_size", int(12 * u))
	var comparison_width := 130.0 * u
	var comparison_x := _section.position.x + 126.0 * u
	_section.visible = comparison_x + comparison_width + 8 * u <= _counter.position.x
	if not _section.visible:
		comparison_x = _section.position.x
	model_comparison_button.position = Vector2(comparison_x, _section.position.y - 3 * u)
	model_comparison_button.size = Vector2(comparison_width, 30 * u)
	model_comparison_button.add_theme_font_size_override("font_size", int(12 * u))
	var dx := _details_rect.position.x
	var dy := _details_rect.position.y
	var dw := _details_rect.size.x
	_hero_title.position = Vector2(dx, dy)
	_hero_title.size = Vector2(dw, 28 * u)
	_hero_title.add_theme_font_size_override("font_size", int(16 * u))
	_hero_name.position = Vector2(dx, dy + 31 * u)
	_hero_name.size = Vector2(dw, 48 * u)
	_hero_name.add_theme_font_size_override("font_size", int((26 if selected_index == 2 else 34) * u))
	_hero_note.position = Vector2(dx, dy + 84 * u)
	_hero_note.size = Vector2(dw, 24 * u)
	_hero_note.add_theme_font_size_override("font_size", int(13 * u))
	if _portrait and size.x < 550:
		_hero_name.add_theme_font_size_override("font_size", 20 if selected_index == 2 else 24)
		_hero_title.add_theme_font_size_override("font_size", 12)
		_hero_note.hide()
	else:
		_hero_note.show()
	confirm_button.position = Vector2(dx, maxf(dy + 124 * u, _details_rect.end.y - 50 * u))
	confirm_button.size = Vector2(dw, 46 * u)
	confirm_button.add_theme_font_size_override("font_size", int(18 * u))
	_hint.position = Vector2(margin, size.y - 49 * u)
	_hint.size = Vector2(size.x * 0.57, 26 * u)
	_hint.add_theme_font_size_override("font_size", int(12 * u))
	_status.position = Vector2(size.x * 0.54, size.y - 49 * u)
	_status.size = Vector2(size.x * 0.46 - margin, 26 * u)
	_status.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_status.add_theme_font_size_override("font_size", int(11 * u))
	if _portrait:
		_hint.text = "轻触棋子选择角色"
	else:
		_hint.text = "点击选择  /  方向键切换  /  Enter 确认"
	_update_showcase(true)
	_redraw()


func _update_showcase(resized_layout := false) -> void:
	var carmen := selected_index == 0
	_card.visible = carmen
	_speech.visible = carmen
	_hero_name.visible = not carmen
	_hero_title.visible = not carmen
	_hero_note.visible = not carmen and not (_portrait and size.x < 550)
	if not resized_layout and _card_mode == carmen:
		_position_speech()
		return
	_card_mode = carmen
	_pawn_rect = _hero_rect
	if carmen:
		var u := _unit
		var area: Rect2
		if _portrait:
			area = Rect2(30 * u, 119 * u, size.x - 60 * u, _board_rect.position.y - 137 * u)
		else:
			area = Rect2(_hero_rect.position, Vector2(_hero_rect.size.x, _board_rect.end.y - _hero_rect.position.y))
		_showcase_rect = area
		var narrow := size.x < 550
		var confirm_height := maxf(34 * u, 36.0)
		var button_width := 132.0 if narrow else 176.0 * u
		confirm_button.position = Vector2(area.position.x, area.end.y - confirm_height - (20 * u if _portrait else 0.0))
		confirm_button.size = Vector2(button_width, confirm_height)
		confirm_button.add_theme_font_size_override("font_size", 14 if narrow else int(16 * u))
		# Arrange the fixed monitor first, then freeze the toy beside the resting card.
		var monitor_area := area
		if _portrait:
			monitor_area.size.y -= confirm_height + 24 * u
		if narrow:
			monitor_area.size.x -= 40.0
		_card.arrange(monitor_area, u, true)
		var resting_art: Rect2 = _card.image_rect()
		var foot: Rect2 = _card.monitor_foot_rect()
		var compact := narrow and size.y < 700
		var pawn_height := (88.0 if compact else 115.0) if narrow else 180.0 * u
		var pawn_width := (58.0 if compact else 75.0) if narrow else 118.0 * u
		var target_height := (94.0 if compact else 123.0) if narrow else 190.0 * u
		# Freeze placement at rest; the toy overlaps the sleeve, not the portrait.
		var contact := Vector2(resting_art.end.x + pawn_height * 0.30,
			minf(area.end.y - 8 * u, foot.end.y) - target_height * 0.13)
		_pawn_rect = Rect2(contact - Vector2(pawn_width * 0.5, pawn_height), Vector2(pawn_width, pawn_height))
		stage.hero_contact = contact
		_speech_region = Rect2(area.end.x - (130.0 if narrow else 162.0 * u), area.position.y + 12 * u,
			130.0 if narrow else 162.0 * u, area.size.y * 0.70)
	else:
		stage.hero_contact = Vector2.INF
	stage.arrange(_board_rect, cell_rects, _pawn_rect, _unit)
	_position_speech()


func _position_speech() -> void:
	if not is_instance_valid(_speech) or not is_instance_valid(stage) or not _speech.visible or _speech_region.size.x <= 0:
		return
	_speech.arrange(_speech_region, stage.hero_head_point(), FONT, 12 if size.x < 550 else int(15 * _unit))


func _can_begin_card_drag(point: Vector2) -> bool:
	for button: Button in choice_buttons + [confirm_button, close_button, model_comparison_button]:
		if is_instance_valid(button) and button.is_visible_in_tree() and button.get_global_rect().has_point(point):
			return false
	if _speech.is_visible_in_tree() and _speech.contains_point(point):
		return false
	return not stage.foreground_hit(point)


func _toggle_carmen_model() -> void:
	stage.set_imported_carmen(not stage.imported_carmen_enabled)
	model_comparison_button.text = "卡门：GLB ⇄" if stage.imported_carmen_enabled else "卡门：原版 ⇄"


func _select(index: int, animate: bool) -> void:
	if _closing or index < 0 or index >= ROSTER.size():
		return
	var changed_showcase := (selected_index == 0) != (index == 0)
	selected_index = index
	if changed_showcase:
		_layout()
	var character: Dictionary = ROSTER[index]
	_hero_name.text = character.name
	_hero_name.add_theme_font_size_override("font_size", int((26 if index == 2 else 34) * _unit))
	if _portrait and size.x < 550:
		_hero_name.add_theme_font_size_override("font_size", 20 if index == 2 else 24)
	_hero_title.text = "%02d  /  %s" % [index + 1, character.title]
	_hero_title.add_theme_color_override("font_color", character.color)
	_hero_note.text = character.note
	_counter.text = "%02d 已选  /  06" % (index + 1)
	_status.text = "拖动卡牌 · 松手回摆" if index == 0 else "确认角色后进入港口"
	confirm_button.text = "确认角色  →"
	for i in 6:
		choice_buttons[i].add_theme_color_override("font_color", PAPER if i == index else MUTED)
	_update_showcase()
	stage.choose(index, animate)
	_redraw()


func _choice_input(event: InputEvent, index: int) -> void:
	if not event is InputEventKey or not event.pressed or event.echo:
		return
	var next := index
	match event.keycode:
		KEY_LEFT: next = maxi(0, index - 1)
		KEY_RIGHT: next = mini(5, index + 1)
		KEY_UP: next = maxi(0, index - columns)
		KEY_DOWN: next = mini(5, index + columns)
		KEY_ENTER, KEY_KP_ENTER:
			_select(index, false)
			_confirm()
			choice_buttons[index].accept_event()
			return
		_:
			return
	_select(next, true)
	choice_buttons[next].grab_focus()
	choice_buttons[index].accept_event()


func _unhandled_key_input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo:
		return
	if event.keycode == KEY_ESCAPE:
		close()
		get_viewport().set_input_as_handled()
	elif event.keycode in [KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN] and not get_viewport().gui_get_focus_owner():
		choice_buttons[selected_index].grab_focus()
		_choice_input(event, selected_index)
	elif event.keycode in [KEY_ENTER, KEY_KP_ENTER] and not get_viewport().gui_get_focus_owner():
		_confirm()
		get_viewport().set_input_as_handled()


func _confirm() -> void:
	if _closing:
		return
	_closing = true
	var previous_confirmed_index := confirmed_index
	confirmed_index = selected_index
	var character: Dictionary = ROSTER[selected_index]
	_status.text = "正在进入港口：%s" % character.name
	confirm_button.text = "正在登船…"
	confirm_button.disabled = true
	# Finish the current button/key event before the SceneTree detaches this scene.
	_enter_harbor.call_deferred(character, previous_confirmed_index)


func _enter_harbor(character: Dictionary, previous_confirmed_index: int) -> void:
	var tree := get_tree()
	var window := get_window()
	var had_character := tree.has_meta("harbor_character")
	var previous_character: Variant = tree.get_meta("harbor_character") if had_character else null
	tree.set_meta("harbor_character", str(character.id))
	var error := tree.change_scene_to_file(HARBOR_SCENE)
	if error == OK:
		# The selection layout uses native pixels, but the harbor uses the project canvas.
		window.content_scale_size = Vector2i(
			int(ProjectSettings.get_setting("display/window/size/viewport_width", 1448)),
			int(ProjectSettings.get_setting("display/window/size/viewport_height", 1086)))
		window.min_size = _previous_window_min_size
		character_confirmed.emit(str(character.id), str(character.name))
		return
	if had_character:
		tree.set_meta("harbor_character", previous_character)
	else:
		tree.remove_meta("harbor_character")
	confirmed_index = previous_confirmed_index
	_closing = false
	confirm_button.disabled = false
	confirm_button.text = "重试进入港口  →"
	_status.text = "港口暂时无法打开，请重试"
	push_error("Unable to enter harbor (%s): %s" % [HARBOR_SCENE, error_string(error)])


func open() -> void:
	_closing = false
	show()
	_select(selected_index, false)


func close() -> void:
	if _closing:
		return
	_closing = true
	hide()
	closed.emit()
	if quit_on_close:
		get_tree().quit()


func _make_backdrop() -> ImageTexture:
	var image := Image.create(128, 128, false, Image.FORMAT_RGB8)
	var rng := RandomNumberGenerator.new()
	rng.seed = 461
	for y in 128:
		for x in 128:
			var color := Color("1b302d").lightened(rng.randf() * 0.012)
			if (x + y) % 6 == 0:
				color = color.darkened(0.05)
			image.set_pixel(x, y, color)
	return ImageTexture.create_from_image(image)


func _redraw() -> void:
	queue_redraw()
	if is_instance_valid(_ink):
		_ink.queue_redraw()


func _draw() -> void:
	if _grain != null:
		draw_texture_rect(_grain, Rect2(Vector2.ZERO, size), true)


func _draw_ink() -> void:
	var u := _unit
	var line_color := Color("52624b")
	_ink.draw_rect(Rect2(Vector2(12, 12) * u, size - Vector2(24, 24) * u), line_color, false, maxf(1, u))
	_ink.draw_line(Vector2(36, 110) * u, Vector2(size.x - 36 * u, 110 * u), line_color, maxf(1, u))
	_ink.draw_line(Vector2(36 * u, size.y - 64 * u), Vector2(size.x - 36 * u, size.y - 64 * u), line_color, maxf(1, u))
	if not _portrait and selected_index != 0:
		var divider := _hero_rect.position.x - 18 * u
		_ink.draw_line(Vector2(divider, 143 * u), Vector2(divider, size.y - 96 * u), Color("344c40"), maxf(1, u))
	# Small engraved compass, independent of the table's texture aspect ratio.
	_compass(Vector2(size.x - 182 * u, 56 * u), 15 * u)
	for i in cell_rects.size():
		var rect := cell_rects[i]
		var p := Vector2(rect.get_center().x, rect.end.y - 7 * u)
		var active := i == selected_index
		var color: Color = ROSTER[i].color
		if active:
			_ink.draw_line(p - Vector2(22 * u, 0), p + Vector2(22 * u, 0), color, 2 * u)
			_ink.draw_circle(p, 3 * u, color)
		if choice_buttons[i].has_focus() or choice_buttons[i].is_hovered():
			var r := rect.grow(-6 * u)
			var length := 12 * u
			var c := GOLD if choice_buttons[i].has_focus() else Color("718b72")
			for corner in [r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y)]:
				var x_dir := 1.0 if corner.x == r.position.x else -1.0
				var y_dir := 1.0 if corner.y == r.position.y else -1.0
				_ink.draw_line(corner, corner + Vector2(x_dir * length, 0), c, 2 * u)
				_ink.draw_line(corner, corner + Vector2(0, y_dir * length), c, 2 * u)


func _compass(center: Vector2, radius: float) -> void:
	var color := Color("8c8963")
	_ink.draw_arc(center, radius * 0.72, 0, TAU, 24, color, maxf(1, _unit))
	for i in 4:
		var direction := Vector2.from_angle(i * PI / 2)
		var side := direction.orthogonal()
		_ink.draw_colored_polygon(PackedVector2Array([center + direction * radius, center + side * radius * 0.20, center, center - side * radius * 0.20]), Color("cbbb85") if i % 2 == 0 else color)
