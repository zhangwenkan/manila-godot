extends Control

const Pixel := preload("res://card/pixel_card_theme.gd")
const DialogSkin := preload("res://ui/harbor_dialog_skin.gd")
const Layout := preload("res://demo/harbor_hd2d/harbor_layout.gd")
const Hand := preload("res://demo/harbor_hd2d/harbor_hand.gd")
const PORTRAIT := preload("res://ui/pixel_portrait.gdshader")
const AVATARS := [preload("res://card/image/lanka_avatar.png"), preload("res://card/image/carmen_avatar.png")]
const CARGO_COLORS := [Color("e1be63"), Color("6dabe0"), Color("89c87a")]
const INK := Color("191820")
const PLUM := Color("302634")
const CREAM := Color("f0dfbb")
const GOLD := Color("ffe27b")

var demo: Control
var canvas: Control
var buttons: Dictionary = {}
var district_labels: Dictionary = {}
var ship_labels: Array[Label] = []
var actor_buttons: Array[Button] = []
var phase_label: Label
var detail: Label
var person: Label
var resources: Label
var holdings: Label
var avatar: TextureRect
var confirm: Button
var roll: Button
var skip: Button
var camera_toggle: Button
var pixel_toggle: Button
var reset_button: Button
var preset_button: Button
var tools_toggle: Button
var inspect_button: Button
var tools_panel: Control
var voyage_label: Label
var notice: Label
var dice_panel: Control
var dice_caption: Label
var dice_values: Array = []
var hand: Control
var _factor := 1.0
var _layout_data: Dictionary = {}
var _actor := -1


func setup(controller: Control) -> void:
	demo = controller
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	canvas = Control.new()
	canvas.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(canvas)
	canvas.draw.connect(_draw_frame)
	for item in demo.state.positions:
		var button := Button.new()
		button.size = Vector2(28, 28)
		button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		button.focus_mode = Control.FOCUS_ALL
		Pixel.clear_button_styles(button)
		canvas.add_child(button)
		buttons[item.id] = button
		button.pressed.connect(func(): demo.select_slot(item.id))
		button.draw.connect(_draw_slot.bind(button, item))
		button.mouse_entered.connect(button.queue_redraw)
		button.mouse_exited.connect(button.queue_redraw)
		button.focus_entered.connect(button.queue_redraw)
		button.focus_exited.connect(button.queue_redraw)
	for title: String in demo.world.district_anchors:
		var label := _label(title, Rect2(0, 0, 118, 25), 17, CREAM)
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.add_theme_stylebox_override("normal", _style(Color("49362d"), Color("b68c58"), 2))
		district_labels[title] = label
	for i in 3:
		var label := _label("", Rect2(0, 0, 124, 24), 16, CARGO_COLORS[i])
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.add_theme_stylebox_override("normal", _style(PLUM, CARGO_COLORS[i].darkened(0.4), 2))
		ship_labels.append(label)
	phase_label = _label("", Rect2(0, 8, 284, 40), 23, CREAM)
	phase_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	phase_label.add_theme_stylebox_override("normal", _style(PLUM, Color("9a8990"), 3))
	voyage_label = _label("独立视觉 DEMO", Rect2(20, 17, 210, 24), 16, Color("ad9b99"))
	for i in 2:
		actor_buttons.append(_button(["拉坎", "卡门"][i], Rect2(0, 0, 100, 30), func(): demo.switch_actor(i)))
	avatar = TextureRect.new()
	avatar.size = Vector2(100, 100)
	avatar.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	avatar.stretch_mode = TextureRect.STRETCH_SCALE
	avatar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var portrait := ShaderMaterial.new()
	portrait.shader = PORTRAIT
	portrait.set_shader_parameter("draw_size", avatar.size)
	portrait.set_shader_parameter("portrait_diameter", 80.0)
	portrait.set_shader_parameter("pixel_grid", 48.0)
	portrait.set_shader_parameter("source_region", Vector4(0.11, 0.12, 0.78, 0.58))
	portrait.set_shader_parameter("has_portrait", true)
	portrait.set_shader_parameter("outline_color", INK)
	portrait.set_shader_parameter("rim_color", GOLD)
	portrait.set_shader_parameter("wood_color", Color("99784d"))
	portrait.set_shader_parameter("shadow_color", Color(0.05, 0.04, 0.07, 0.8))
	avatar.material = portrait
	canvas.add_child(avatar)
	person = _label("", Rect2(0, 0, 166, 28), 22, CREAM)
	resources = _label("", Rect2(0, 0, 166, 56), 22, GOLD)
	holdings = _label("", Rect2(0, 0, 240, 22), 16, CREAM)
	holdings.hide()
	hand = Hand.new()
	canvas.add_child(hand)
	detail = _label("", Rect2(0, 0, 284, 90), 17, CREAM)
	detail.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	confirm = _button("选择岗位", Rect2(0, 0, 132, 68), func(): demo.confirm_selection(), Color("356a98"))
	roll = _button("掷骰航行", Rect2(0, 0, 138, 68), func(): demo.roll_sailing(), Color("a33f39"))
	skip = _button("跳过 · 回全局 [Esc]", Rect2(0, 0, 284, 54), func(): demo.skip_sailing(), Color("356a98"))
	skip.hide()
	notice = _label("", Rect2(0, 0, 600, 30), 16, Color("c7b6a6"))
	notice.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tools_toggle = _button("设置", Rect2(0, 0, 84, 44), func(): tools_panel.visible = not tools_panel.visible; canvas.queue_redraw())
	inspect_button = _button("观察吊机", Rect2(0, 0, 190, 44), func(): demo.toggle_inspection(), Color("6b4338"))
	tools_panel = Control.new()
	tools_panel.size = Vector2(280, 304)
	tools_panel.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	canvas.add_child(tools_panel)
	tools_panel.draw.connect(func():
		DialogSkin.frame(tools_panel, Rect2(0, 24, 280, 280), 50)
		DialogSkin.header(tools_panel, Rect2(28, 0, 210, 58), "港湾设置", 22))
	var tools_close := Button.new()
	tools_close.position = Vector2(238, 8)
	tools_close.size = Vector2(42, 42)
	tools_close.tooltip_text = "收起设置"
	tools_panel.add_child(tools_close)
	DialogSkin.decorate_close(tools_close)
	tools_close.pressed.connect(tools_panel.hide)
	tools_panel.hide()
	camera_toggle = _button("", Rect2(28, 78, 224, 40), func(): demo.auto_closeup = not demo.auto_closeup; refresh())
	pixel_toggle = _button("", Rect2(28, 130, 224, 40), func(): demo.toggle_pixel(); refresh())
	preset_button = _button("分散船位 0 / 7 / 13", Rect2(28, 182, 224, 40), func(): demo.reset_demo(true))
	reset_button = _button("重新开始", Rect2(28, 234, 224, 40), func(): demo.reset_demo())
	for button in [camera_toggle, pixel_toggle, preset_button, reset_button]:
		button.reparent(tools_panel, false)
	dice_panel = Control.new()
	dice_panel.size = Vector2(454, 109)
	dice_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	canvas.add_child(dice_panel)
	dice_panel.draw.connect(_draw_dice)
	dice_caption = Pixel.label(dice_panel, "", Rect2(12, 75, 430, 26), 17, CREAM)
	dice_caption.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	dice_panel.hide()
	resized.connect(_layout)
	_layout()
	refresh()


func _layout() -> void:
	_layout_data = Layout.describe(size)
	_factor = _layout_data.factor
	canvas.scale = Vector2.ONE * _factor
	canvas.position = Vector2.ZERO
	canvas.size = _layout_data.canvas_size
	var width: float = canvas.size.x
	var actor_rect: Rect2 = _layout_data.actor_rect
	var action_rect: Rect2 = _layout_data.action_rect
	phase_label.position.x = (width - phase_label.size.x) * 0.5
	tools_toggle.position = Vector2(width - 100, 9)
	inspect_button.position = _layout_data.inspect_rect.position
	inspect_button.size = _layout_data.inspect_rect.size
	tools_panel.position = Vector2(width - 296, 72)
	for i in 2:
		actor_buttons[i].position = actor_rect.position + Vector2(4 + i * 110, -38)
	avatar.position = actor_rect.position + Vector2(2, 3)
	person.position = actor_rect.position + Vector2(104, 12)
	resources.position = actor_rect.position + Vector2(104, 39)
	hand.position = _layout_data.hand_rect.position
	hand.size = _layout_data.hand_rect.size
	if hand.has_method("layout_cards"):
		hand.layout_cards()
	detail.position = action_rect.position + Vector2(0, -52)
	detail.size = Vector2(action_rect.size.x, 83)
	confirm.position = action_rect.position + Vector2(0, 44)
	roll.position = action_rect.position + Vector2(146, 44)
	skip.position = action_rect.position + Vector2(0, 56)
	notice.position = Vector2(width * 0.5 - 300, 870)
	notice.size.x = 600
	dice_panel.position = Vector2(width * 0.5 - 227, 76)
	canvas.queue_redraw()


func project(point: Vector3) -> Vector2:
	var uv: Vector2 = demo.world.camera.unproject_position(point) / Vector2(demo.viewport.size)
	return (demo.display.position + uv * demo.display.size - canvas.position) / _factor


func _process(_delta: float) -> void:
	if demo == null or demo.world.camera == null:
		return
	var overview: bool = not demo.busy and not demo.world.inspecting and demo.world.camera_blend < 0.02
	for id: String in buttons:
		var button: Button = buttons[id]
		var point: Vector3 = demo.world.slot_position(id)
		button.visible = overview and not demo.world.camera.is_position_behind(point)
		if button.visible:
			button.position = (project(point) - button.size * 0.5).round()
	for title: String in district_labels:
		var label: Label = district_labels[title]
		label.visible = overview
		if overview:
			label.position = (project(demo.world.district_anchors[title]) - Vector2(label.size.x * 0.5, 25)).round()
	for i in 3:
		var label := ship_labels[i]
		label.visible = not demo.world.inspecting
		if overview:
			label.position = (project(demo.world.boats[i].position + Vector3(0, 0, 3.1)) - Vector2(62, 0)).round()
		else:
			label.position = Vector2(22, 84 + i * 35)


func cover_hand() -> void:
	if hand != null:
		hand.cover_all()


func refresh() -> void:
	if demo == null:
		return
	var inspecting: bool = demo.world.inspecting
	var locked: bool = demo.busy or inspecting
	var actor: Dictionary = demo.actors[demo.actor_index]
	if _actor != demo.actor_index:
		cover_hand()
		_actor = demo.actor_index
	hand.set_holdings(actor.holdings)
	hand.set_collapsed(locked)
	for control: Control in [avatar, person, resources, voyage_label, tools_toggle]:
		control.visible = not inspecting
	inspect_button.disabled = demo.busy
	inspect_button.text = "返回全局 [Esc]" if inspecting else "观察吊机"
	inspect_button.tooltip_text = "滚轮缩放 · 按住右键拖动旋转" if inspecting else "近距离环绕查看红色吊机桁架"
	if inspecting:
		tools_panel.hide()
		dice_panel.hide()
	person.text = actor.name
	resources.text = "金币  %d\n伙计  %d" % [actor.cash, actor.crew]
	var names := {"ginseng": "人参", "silk": "丝绸", "jade": "玉石", "nutmeg": "肉蔻"}
	var summary: Array[String] = []
	for id: String in actor.holdings:
		summary.append(names.get(id, id))
	holdings.text = "个人持股 · " + " / ".join(summary)
	avatar.texture = AVATARS[demo.actor_index]
	phase_label.text = "吊机桁架 · 近景观察" if inspecting else "TURN %d  ·  %s" % [demo.round_number, "航行" if demo.busy else "派遣"]
	camera_toggle.text = "自动近景 · %s" % ["开" if demo.auto_closeup else "关"]
	pixel_toggle.text = "像素 · %d×" % demo.display.stretch_shrink
	for i in 2:
		actor_buttons[i].modulate = CREAM if demo.actor_index == i else Color("9c9097")
		actor_buttons[i].disabled = locked
		actor_buttons[i].visible = not inspecting
	for i in 3:
		ship_labels[i].text = "%s  %s" % [demo.state.cargo_name(i), "已到港" if demo.state.arrived[i] else "%02d / 13" % demo.steps[i]]
	for item in demo.state.positions:
		var button: Button = buttons[item.id]
		button.disabled = locked
		button.tooltip_text = "%s · %d 比索\n%s\n%s" % [item.title, item.cost, item.effect, demo.placement_reason(item.id)]
		button.queue_redraw()
	confirm.disabled = locked or demo.selected_id.is_empty() or not demo.placement_reason(demo.selected_id).is_empty()
	confirm.text = "选择岗位"
	detail.text = "点选圆形岗位\n确认才派驻伙计并扣费"
	if not demo.selected_id.is_empty():
		var item: Dictionary = demo.state.get_position(demo.selected_id)
		var reason: String = demo.placement_reason(demo.selected_id)
		detail.text = "%s · %s\n%s" % [item.title, "领取 10 比索" if item.group == "insurance" else "%d 比索 / 1 伙计" % item.cost, item.effect if reason.is_empty() else reason]
		confirm.text = "确认领 10" if item.group == "insurance" else "确认 %d 币" % item.cost
	roll.disabled = locked or demo.state.arrived.all(func(value: bool): return value)
	roll.text = "全船到港" if roll.disabled and not locked else "掷骰航行"
	confirm.visible = not locked
	roll.visible = not locked
	detail.visible = not locked
	preset_button.disabled = locked
	reset_button.disabled = locked
	camera_toggle.disabled = locked
	skip.visible = demo.busy
	notice.text = "滚轮缩放 · 按住右键拖动旋转 · Esc 返回" if inspecting else (demo.notice if demo.busy else "个人持股 · 点击翻面 / 同屏请避看")
	canvas.queue_redraw()


func show_dice(values: Array, caption: String) -> void:
	dice_values = values.duplicate()
	dice_caption.text = caption
	dice_panel.show()
	dice_panel.queue_redraw()


func _draw_frame() -> void:
	if _layout_data.is_empty():
		return
	if not demo.world.inspecting:
		var rect: Rect2 = _layout_data.actor_rect
		_bevel(canvas, Rect2(rect.position + Vector2(48, 4), rect.size - Vector2(48, 8)), PLUM)
		if not demo.busy:
			var action_rect: Rect2 = _layout_data.action_rect
			DialogSkin.frame(canvas, Rect2(action_rect.position + Vector2(-14, -78), Vector2(312, 214)), 44)
			DialogSkin.header(canvas, Rect2(action_rect.position + Vector2(24, -102), Vector2(236, 48)), "派遣行动", 22)
	canvas.draw_rect(Rect2(0, 894, canvas.size.x, 6), Color("47333e"))


func _draw_slot(button: Button, item: Dictionary) -> void:
	var selected: bool = demo.selected_id == item.id
	var owner = demo.state.owners.get(item.id)
	var available: bool = demo.placement_reason(item.id).is_empty()
	var edge := GOLD if selected or available or button.is_hovered() else Color("ad9273")
	if owner != null:
		edge = owner.color
	var center := button.size * 0.5
	button.draw_circle(center, 13, Color(0.12, 0.09, 0.09, 0.80))
	for i in 8:
		button.draw_arc(center, 13, i * TAU / 8.0, (i + 0.72) * TAU / 8.0, 4, Color(edge, 0.2), 7)
		button.draw_arc(center, 13, i * TAU / 8.0, (i + 0.72) * TAU / 8.0, 4, edge, 2)
	if selected or button.has_focus():
		button.draw_arc(center, 18, 0, TAU, 24, GOLD, 2)
	if owner != null:
		Pixel.icon(button, "crew", Vector2(7, 4), 2, edge)
	else:
		button.draw_string(Pixel.FONT, Vector2(0, 21), str(item.cost), HORIZONTAL_ALIGNMENT_CENTER, 28, 18, edge)


func _draw_dice() -> void:
	_bevel(dice_panel, Rect2(Vector2.ZERO, dice_panel.size), PLUM)
	var dots := [Vector2(0, 0), Vector2(-1, -1), Vector2(1, 1), Vector2(1, -1), Vector2(-1, 1), Vector2(-1, 0), Vector2(1, 0)]
	var patterns := {1: [0], 2: [1, 2], 3: [0, 1, 2], 4: [1, 2, 3, 4], 5: [0, 1, 2, 3, 4], 6: [1, 2, 3, 4, 5, 6]}
	for i in mini(3, dice_values.size()):
		var p := Vector2(65 + i * 146, 13)
		_bevel(dice_panel, Rect2(p, Vector2(48, 48)), CARGO_COLORS[i])
		for index in patterns.get(int(dice_values[i]), [0]):
			dice_panel.draw_rect(Rect2(p + Vector2(21, 21) + dots[index] * 12, Vector2(6, 6)), INK)


func _bevel(target: CanvasItem, rect: Rect2, color: Color) -> void:
	Pixel.step_rect(target, Rect2(rect.position + Vector2(0, 4), rect.size), 7, INK)
	Pixel.step_rect(target, rect, 7, INK)
	Pixel.step_rect(target, rect.grow(-2), 5, color.lightened(0.28))
	Pixel.step_rect(target, rect.grow(-5), 3, color.darkened(0.35))
	Pixel.step_rect(target, Rect2(rect.position + Vector2(6, 6), rect.size - Vector2(12, 15)), 2, color)


func _label(text: String, rect: Rect2, font_size: int, color: Color) -> Label:
	return Pixel.label(canvas, text, rect, font_size, color)


func _style(background: Color, border: Color, width := 2) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = background
	style.border_color = border
	style.set_border_width_all(width)
	return style


func _button(text: String, rect: Rect2, action: Callable, color := PLUM) -> Button:
	var button := Button.new()
	button.text = text
	button.position = rect.position
	button.size = rect.size
	button.add_theme_font_override("font", Pixel.FONT)
	button.add_theme_font_size_override("font_size", 18)
	button.add_theme_color_override("font_color", CREAM)
	button.add_theme_color_override("font_disabled_color", Color("aa9593"))
	Pixel.clear_button_styles(button)
	button.draw.connect(func():
		var fill := color.lightened(0.13) if button.is_hovered() or button.has_focus() else color
		if button.disabled:
			fill = fill.darkened(0.30)
		var warm := button in [camera_toggle, pixel_toggle, preset_button, reset_button, confirm, roll]
		if warm:
			DialogSkin.action(button, Rect2(Vector2.ZERO, button.size), button == confirm, not button.disabled, button.is_hovered() or button.has_focus())
		else:
			_bevel(button, Rect2(Vector2.ZERO, button.size), fill)
		button.draw_string(Pixel.FONT, Vector2(0, button.size.y * 0.5 + 7), button.text, HORIZONTAL_ALIGNMENT_CENTER, button.size.x, 18, CREAM if not button.disabled else Color("aa9593")))
	# Custom bevel draws after the default content; the final text above keeps it legible.
	button.pressed.connect(action)
	button.mouse_entered.connect(button.queue_redraw)
	button.mouse_exited.connect(button.queue_redraw)
	button.focus_entered.connect(button.queue_redraw)
	button.focus_exited.connect(button.queue_redraw)
	canvas.add_child(button)
	return button
