extends Control

signal confirm_requested(id: String, requesting_actor: CharacterCard, phase_key: String)

const Pixel := preload("res://card/pixel_card_theme.gd")
const State := preload("res://ui/placement_state.gd")
const CharacterCard := preload("res://card/character_card.gd")
const BOAT := preload("res://boat/boat.png")
const DESIGN := Vector2(1440, 790)
const GROUPS := ["ship_0", "ship_1", "ship_2", "harbor", "shipyard", "pirate", "pilot", "insurance"]
const RECTS := [Rect2(24, 104, 448, 230), Rect2(496, 104, 448, 230), Rect2(968, 104, 448, 230),
	Rect2(24, 354, 684, 156), Rect2(732, 354, 684, 156),
	Rect2(24, 530, 448, 162), Rect2(496, 530, 448, 162), Rect2(968, 530, 448, 162)]
const TITLES := ["01  人参船", "02  丝绸船", "03  玉石船", "港口", "修船厂", "海盗", "引航员", "保险公司"]
const ICONS := ["anchor", "anchor", "diamond", "anchor", "trade", "sword", "helm", "scale"]

var state := State.new()
var actor: CharacterCard
var interaction_enabled := false
var selected_id := ""
var buttons: Dictionary = {}
var launcher: Button
var sheet: Control
var shade: ColorRect
var close_button: Button
var cancel_button: Button
var confirm_button: Button
var validate_placement: Callable
var detail: Label
var result_notice: Label
var _notice_timer: Timer
var _phase_key := ""
var _disabled_reason := ""
var _ship_status_labels: Array[Label] = []
var available_bottom := 880.0
var available_top := 24.0


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	launcher = _button(self, "打开派遣面板", Rect2(0, 0, 208, 48))
	launcher.pressed.connect(open)
	result_notice = Pixel.label(self, "", Rect2(0, 84, 660, 112), 22, Pixel.PAPER)
	var notice_style := StyleBoxFlat.new()
	notice_style.bg_color = Color("142e30")
	notice_style.content_margin_left = 12
	notice_style.content_margin_top = 8
	result_notice.add_theme_stylebox_override("normal", notice_style)
	result_notice.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	result_notice.hide()
	_notice_timer = Timer.new()
	_notice_timer.one_shot = true
	_notice_timer.wait_time = 5.0
	_notice_timer.timeout.connect(result_notice.hide)
	add_child(_notice_timer)
	shade = ColorRect.new()
	shade.color = Color(0.02, 0.06, 0.07, 0.62)
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(shade)
	sheet = Control.new()
	sheet.size = DESIGN
	shade.add_child(sheet)
	sheet.draw.connect(_draw_sheet)
	Pixel.label(sheet, "派遣图板", Rect2(28, 20, 400, 42), 36, Pixel.PAPER)
	Pixel.label(sheet, "选择岗位 → 确认派遣 → 本轮下一位 · 每人每轮只派一次", Rect2(28, 65, 1160, 28), 22, Pixel.MUTED)
	close_button = _button(sheet, "收起", Rect2(1284, 24, 128, 48))
	close_button.pressed.connect(close)
	for group_index in GROUPS.size():
		var rect: Rect2 = RECTS[group_index]
		Pixel.label(sheet, TITLES[group_index], Rect2(rect.position + Vector2(60, 10), Vector2(320, 32)), 26, Pixel.PAPER)
		_add_slot_buttons(group_index)
		if group_index < 3:
			_ship_status_labels.append(Pixel.label(sheet, "", Rect2(rect.position + Vector2(18, 189), Vector2(412, 28)), 22, Pixel.MUTED))
		else:
			var notes := ["有船才有收益", "受损船入厂", "登船 / 劫掠", "小先大后", "先领 10\n后担赔付"]
			Pixel.label(sheet, notes[group_index - 3], Rect2(rect.position + Vector2(18, 70), Vector2(230 if group_index < 5 else 190, 60)), 22, Pixel.MUTED)
	detail = Pixel.label(sheet, "", Rect2(28, 700, 860, 78), 22, Pixel.PAPER)
	detail.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	cancel_button = _button(sheet, "取消选择", Rect2(908, 718, 152, 48))
	cancel_button.pressed.connect(clear_selection)
	confirm_button = _button(sheet, "确认派遣", Rect2(1076, 718, 324, 48))
	confirm_button.pressed.connect(confirm_selection)
	state.changed.connect(_on_state_changed)
	get_viewport().size_changed.connect(_layout)
	shade.hide()
	_layout()
	_refresh()


## 按 group 建该组的岗位按钮（船位座数随货物变化，故需可重建）。返回该组岗位项。
func _add_slot_buttons(group_index: int) -> Array[Dictionary]:
	var rect: Rect2 = RECTS[group_index]
	var items: Array[Dictionary] = []
	for item in state.positions:
		if item.group == GROUPS[group_index]:
			items.append(item)
	var spacing := 96.0 if group_index < 3 else 106.0
	var start := rect.position + Vector2(rect.size.x - items.size() * spacing - 12, 64 if group_index < 3 else 60)
	for i in items.size():
		var item := items[i]
		var button := Button.new()
		button.name = item.id
		button.position = start + Vector2(i * spacing, 0)
		button.size = Vector2(84, 82)
		button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		Pixel.clear_button_styles(button)
		sheet.add_child(button)
		buttons[item.id] = button
		button.pressed.connect(select.bind(item.id))
		button.draw.connect(_draw_slot.bind(button, item))
		button.mouse_entered.connect(button.queue_redraw)
		button.mouse_exited.connect(button.queue_redraw)
		button.focus_entered.connect(button.queue_redraw)
		button.focus_exited.connect(button.queue_redraw)
	return items


## 港务长换货后重建三船的座位按钮（座位数随货物变化）。分红/座位数文字标签属 UI-09，暂不更新。
func rebuild_ship_slots() -> void:
	_sync_ship_slots()
	_refresh()


## 让船位按钮与 state.positions 对齐；不匹配才重建。_refresh 起手调用以自愈，
## 因为 set_voyage_cargo 的 changed 信号可能早于外部重建触达。
func _sync_ship_slots() -> void:
	if not is_instance_valid(sheet):
		return
	var expected: Array[String] = []
	for item in state.positions:
		if item.group.begins_with("ship_"):
			expected.append(item.id)
	var have: Array[String] = []
	for id in buttons:
		if id.begins_with("ship_"):
			have.append(id)
	expected.sort()
	have.sort()
	if expected == have:
		return
	for id in have:
		var old: Button = buttons[id]
		sheet.remove_child(old)   # 立即脱离树，避免同名新按钮被自动改名
		old.queue_free()
		buttons.erase(id)
	for group_index in 3:
		_add_slot_buttons(group_index)


func _button(parent: Control, text: String, rect: Rect2) -> Button:
	var button := Button.new()
	button.text = text
	button.position = rect.position
	button.size = rect.size
	button.add_theme_font_override("font", Pixel.FONT)
	button.add_theme_font_size_override("font_size", 24)
	button.add_theme_color_override("font_color", Pixel.PAPER)
	button.add_theme_color_override("font_disabled_color", Pixel.MUTED)
	for key in ["normal", "hover", "pressed", "disabled", "focus"]:
		var style := StyleBoxFlat.new()
		style.bg_color = Color("365c59") if key in ["hover", "focus"] else Color("203b3b")
		style.border_color = Pixel.GOLD if key == "focus" else Pixel.TEAL
		style.set_border_width_all(2)
		button.add_theme_stylebox_override(key, style)
	parent.add_child(button)
	return button


func _layout() -> void:
	var viewport := get_viewport_rect().size
	var factor := minf(1.0, minf((viewport.x - 48) / DESIGN.x, (minf(available_bottom, viewport.y - 24) - available_top) / DESIGN.y))
	factor = maxf(0.2, factor)
	sheet.scale = Vector2.ONE * factor
	sheet.position = Vector2((viewport.x - DESIGN.x * factor) * 0.5, available_top).floor()
	launcher.position = Vector2(viewport.x - 240, 24)
	result_notice.size.x = minf(660, viewport.x - 48)
	result_notice.position = Vector2(viewport.x - result_notice.size.x - 24, 84)


func set_context(current_actor: CharacterCard, enabled: bool, phase_key: String, disabled_reason: String = "") -> void:
	var context_changed := actor != current_actor or phase_key != _phase_key or interaction_enabled != enabled
	if context_changed:
		clear_selection()
		result_notice.hide()
	actor = current_actor
	interaction_enabled = enabled
	_phase_key = phase_key
	_disabled_reason = disabled_reason
	if not enabled:
		close()
	_refresh()


func open() -> void:
	if not interaction_enabled or not visible:
		return
	result_notice.hide()
	_refresh()
	shade.show()
	launcher.hide()
	close_button.grab_focus()


func close() -> void:
	clear_selection()
	shade.hide()
	launcher.show()


func clear_selection() -> void:
	selected_id = ""
	for button: Button in buttons.values():
		button.release_focus()
	_refresh()


func select(id: String) -> void:
	if not interaction_enabled or actor == null or not shade.is_visible_in_tree() or not state.unavailable_reason(id).is_empty():
		return
	selected_id = "" if selected_id == id else id
	_refresh()


func confirm_selection() -> void:
	if selected_id.is_empty() or not interaction_enabled or not shade.is_visible_in_tree():
		return
	confirm_requested.emit(selected_id, actor, _phase_key)


func show_error(reason: String) -> void:
	_refresh()
	detail.text = "%s\n未派遣：%s" % [state.get_position(selected_id).title, reason]
	confirm_button.disabled = true
	confirm_button.tooltip_text = reason


func show_result(message: String) -> void:
	result_notice.text = message
	result_notice.show()
	_notice_timer.start()


func _unhandled_key_input(event: InputEvent) -> void:
	if shade.is_visible_in_tree() and event.is_action_pressed("ui_cancel"):
		if selected_id.is_empty():
			close()
		else:
			clear_selection()
		get_viewport().set_input_as_handled()


func _on_state_changed() -> void:
	clear_selection()


func _refresh() -> void:
	if not is_instance_valid(detail):
		return
	_sync_ship_slots()
	for ship in _ship_status_labels.size():
		var status := _ship_status_labels[ship]
		status.text = "已到港 · 不能再派人" if state.arrived[ship] else "到港分红 %d · %d 个船位" % [[18, 30, 36][ship], state.ship_occupants(ship).size()]
		status.add_theme_color_override("font_color", Pixel.GOLD if state.arrived[ship] else Pixel.MUTED)
	launcher.disabled = not interaction_enabled
	launcher.tooltip_text = "所有岗位在这里选择" if interaction_enabled else (_disabled_reason if not _disabled_reason.is_empty() else "派遣阶段才可打开")
	cancel_button.disabled = selected_id.is_empty()
	confirm_button.disabled = true
	confirm_button.text = "确认派遣"
	confirm_button.tooltip_text = "先选择一处岗位"
	detail.text = "选择岗位后确认才会扣费、派人。取消或收起不影响资源，也不等于放弃本航程。"
	if not selected_id.is_empty():
		var item := state.get_position(selected_id)
		var reason: String = validate_placement.call(selected_id)
		var payment := "免费派驻 · 立即领取 10 比索" if item.group == "insurance" else "支付 %d 比索" % item.cost
		detail.text = "%s → %s · %s\n消耗 1 名伙计 · %s" % [actor.character_name, item.title, payment, item.effect if reason.is_empty() else reason]
		confirm_button.disabled = not interaction_enabled or not reason.is_empty()
		confirm_button.text = "确认 · 领取 10" if item.group == "insurance" else "确认 · 支付 %d" % item.cost
		confirm_button.tooltip_text = "确认后轮到本轮下一位" if reason.is_empty() else reason
	for item in state.positions:
		var button: Button = buttons[item.id]
		var reason := state.unavailable_reason(item.id)
		button.disabled = not interaction_enabled or not reason.is_empty()
		button.focus_mode = Control.FOCUS_NONE if button.disabled else Control.FOCUS_ALL
		var owner: CharacterCard = state.owners.get(item.id)
		button.tooltip_text = "%s · %d 比索\n%s\n%s" % [item.title, item.cost, item.effect, ("已占：" + owner.character_name) if owner != null else reason]
		button.queue_redraw()


func _draw_sheet() -> void:
	Pixel.step_rect(sheet, Rect2(Vector2.ZERO, DESIGN), 12, Pixel.GOLD)
	Pixel.step_rect(sheet, Rect2(Vector2(3, 3), DESIGN - Vector2(6, 6)), 10, Color("142e30"))
	for i in RECTS.size():
		var rect: Rect2 = RECTS[i]
		Pixel.step_rect(sheet, rect, 8, Color("284749"))
		Pixel.icon(sheet, ICONS[i], rect.position + Vector2(18, 14), 3, Pixel.GOLD)
		if i < 3:
			sheet.draw_texture_rect(BOAT, Rect2(rect.position + Vector2(12, 84), Vector2(420, 104)), false, Color(1, 1, 1, 0.55))
		elif i in [3, 4, 7]:
			var origin := rect.position + Vector2(250 if i < 5 else 224, 69)
			sheet.draw_rect(Rect2(origin, Vector2(44, 62)), Pixel.TEAL)
			sheet.draw_colored_polygon(PackedVector2Array([origin + Vector2(-8, 0), origin + Vector2(22, -22), origin + Vector2(52, 0)]), Pixel.GOLD)
			sheet.draw_rect(Rect2(origin + Vector2(15, 34), Vector2(14, 28)), Pixel.INK)


func _draw_slot(button: Button, item: Dictionary) -> void:
	var owner: CharacterCard = state.owners.get(item.id)
	var selected: bool = selected_id == item.id
	var edge := Pixel.GOLD if selected else Pixel.PAPER if button.is_hovered() or button.has_focus() else Pixel.TEAL if not button.disabled else Color("617976")
	Pixel.step_rect(button, Rect2(Vector2.ZERO, button.size), 6, edge)
	Pixel.step_rect(button, Rect2(Vector2(2, 2), button.size - Vector2(4, 4)), 4, Color("162f32"))
	if owner != null:
		var texture := owner.avatar if owner.avatar != null else owner.portrait
		if texture != null:
			button.draw_texture_rect_region(texture, Rect2(22, 6, 40, 40), Rect2(owner.avatar_region.position * texture.get_size(), owner.avatar_region.size * texture.get_size()))
		button.draw_string(Pixel.FONT, Vector2(5, 26), str(owner.roster_number), HORIZONTAL_ALIGNMENT_LEFT, -1, 20, owner.accent_color)
	else:
		Pixel.icon(button, "check" if selected else "crew", Vector2(29, 8), 3, edge)
	var caption: String = "已占" if owner != null else "%d 币" % item.cost
	button.draw_string(Pixel.FONT, Vector2(12, 72), caption, HORIZONTAL_ALIGNMENT_CENTER, 60, 24, edge)
	if item.ship < 0:
		var short_title: String = {"harbor": ["A", "B", "C"][int(item.id.right(1))], "shipyard": ["A", "B", "C"][int(item.id.right(1))], "pirate": "船长" if item.id.ends_with("0") else "次席", "pilot": "小" if item.id.ends_with("0") else "大", "insurance": "保险"}.get(item.group, "")
		button.draw_string(Pixel.FONT, Vector2(4, -5), short_title, HORIZONTAL_ALIGNMENT_CENTER, 76, 20, Pixel.MUTED)
