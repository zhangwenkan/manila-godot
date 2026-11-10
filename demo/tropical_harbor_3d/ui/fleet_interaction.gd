extends CanvasLayer

const STATE = preload("res://demo/tropical_harbor_3d/fleet/fleet_state.gd")
var harbor: Node3D
var root: Control
var ship_buttons: Array[Button] = []
var slot_buttons: Array[Button] = []
var overview: Button
var roll_button: Button
var pause_button: Button
var restart: Button
var detail: PanelContainer
var title: Label
var status: Label
var confirm: Button
var identity: Label
var selected_slot := -1
var message_until := 0
var message := ""
var info := false
var inspect_button: Button
var observation_hint: Label


func build(owner_: Node3D) -> void:
    harbor = owner_
    root = Control.new()
    root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    root.mouse_filter = Control.MOUSE_FILTER_IGNORE
    add_child(root)
    var top := HBoxContainer.new()
    top.position = Vector2(24, 20)
    top.add_theme_constant_override("separation", 8)
    root.add_child(top)
    overview = _button("总览", harbor.overview)
    overview.tooltip_text = "返回三船总览 · V"
    top.add_child(overview)
    var piers := _button("栈桥", harbor.view_piers)
    piers.tooltip_text = "查看栈桥 · P"
    top.add_child(piers)
    var landing := _button("到港码头", harbor.view_landing)
    landing.tooltip_text = "查看三船到港码头 · H"
    top.add_child(landing)
    inspect_button = _button("近船观察", harbor.toggle_inspection)
    inspect_button.tooltip_text = "低角度观察当前船只 · C"
    top.add_child(inspect_button)
    for i in 3:
        var button := _button("", harbor.select_ship.bind(i))
        top.add_child(button)
        ship_buttons.append(button)
    var help := _button("?", _help)
    help.tooltip_text = "本阶段范围与操作"
    top.add_child(help)
    var actions := HBoxContainer.new()
    actions.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
    actions.offset_left = -310
    actions.offset_right = -24
    actions.offset_top = -62
    actions.offset_bottom = -20
    actions.add_theme_constant_override("separation", 8)
    root.add_child(actions)
    pause_button = _button("Ⅱ", harbor.toggle_pause)
    pause_button.tooltip_text = "暂停水面和船只 · 空格"
    actions.add_child(pause_button)
    roll_button = _button("掷骰", harbor.roll_dice)
    roll_button.tooltip_text = "三枚独立骰子 · 每航程最多三次"
    actions.add_child(roll_button)
    restart = _button("新航程", harbor.new_voyage)
    actions.add_child(restart)
    identity = Label.new()
    identity.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
    identity.position = Vector2(24, -55)
    identity.add_theme_color_override("font_color", Color("fff2d6"))
    identity.add_theme_color_override("font_shadow_color", Color("193d3e"))
    identity.add_theme_constant_override("shadow_offset_y", 2)
    identity.add_theme_font_size_override("font_size", 17)
    root.add_child(identity)
    observation_hint = Label.new()
    observation_hint.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
    observation_hint.position = Vector2(-260, -54)
    observation_hint.text = "右键拖动环绕 · 滚轮缩放 · 1 / 2 / 3 换船 · V 返回全港"
    observation_hint.add_theme_font_size_override("font_size", 16)
    observation_hint.add_theme_color_override("font_shadow_color", Color("193d3e"))
    observation_hint.add_theme_constant_override("shadow_offset_y", 2)
    observation_hint.mouse_filter = Control.MOUSE_FILTER_IGNORE
    root.add_child(observation_hint)
    detail = PanelContainer.new()
    detail.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
    detail.offset_left = -255
    detail.offset_right = 255
    detail.offset_top = -215
    detail.offset_bottom = -75
    var style := StyleBoxFlat.new()
    style.bg_color = Color("183e42", 0.96)
    style.set_corner_radius_all(10)
    style.content_margin_left = 16
    style.content_margin_right = 16
    style.content_margin_top = 10
    style.content_margin_bottom = 10
    detail.add_theme_stylebox_override("panel", style)
    root.add_child(detail)
    var column := VBoxContainer.new()
    column.add_theme_constant_override("separation", 6)
    detail.add_child(column)
    title = Label.new()
    title.add_theme_font_size_override("font_size", 20)
    column.add_child(title)
    var slots := HBoxContainer.new()
    slots.add_theme_constant_override("separation", 6)
    column.add_child(slots)
    for i in 4:
        var button := _button("", select_slot.bind(i))
        slots.add_child(button)
        slot_buttons.append(button)
    var bottom := HBoxContainer.new()
    column.add_child(bottom)
    status = Label.new()
    status.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    status.add_theme_font_size_override("font_size", 14)
    bottom.add_child(status)
    confirm = _button("派遣", _place)
    bottom.add_child(confirm)
    refresh()


func _button(text: String, callback: Callable) -> Button:
    var button := Button.new()
    button.text = text
    button.custom_minimum_size = Vector2(44, 38)
    button.add_theme_font_size_override("font_size", 17)
    var style := StyleBoxFlat.new()
    style.bg_color = Color("234b4c", 0.94)
    style.set_corner_radius_all(6)
    style.content_margin_left = 12
    style.content_margin_right = 12
    var hover := style.duplicate() as StyleBoxFlat
    hover.bg_color = Color("417470")
    button.add_theme_stylebox_override("normal", style)
    button.add_theme_stylebox_override("hover", hover)
    button.add_theme_stylebox_override("pressed", hover)
    button.pressed.connect(callback)
    return button


func select_slot(index: int) -> void:
    info = false
    selected_slot = index
    harbor.ships[harbor.selected].set_selected(true, index)
    refresh()


func _place() -> void:
    var error: String = harbor.state.place(harbor.selected, selected_slot, harbor.state.current_player)
    if not error.is_empty():
        message = error
        message_until = Time.get_ticks_msec() + 2500
    else:
        harbor.ships[harbor.selected].sync_crew(harbor.state.ships[harbor.selected])
        selected_slot = -1
    refresh()


func _help() -> void:
    info = not info
    refresh()


func refresh() -> void:
    if harbor.state.ships.size() != 3:
        return
    var state: RefCounted = harbor.state
    var moving: bool = harbor.is_moving()
    var observing: bool = harbor.camera.inspecting
    inspect_button.text = "返回全港" if observing else "近船观察"
    observation_hint.visible = observing
    for i in 3:
        var data: Dictionary = state.ships[i]
        var cargo: Dictionary = STATE.CARGO[data.cargo_id]
        ship_buttons[i].text = "%s  %s" % [cargo.glyph, "泊" if data.arrived else str(data.progress)]
        ship_buttons[i].modulate = cargo.color.lightened(0.35) if harbor.selected == i else Color.WHITE
        ship_buttons[i].tooltip_text = "%s · %s" % [cargo.label, "到港" if data.arrived else "进度 %d" % data.progress]
    var player: Dictionary = state.players[state.current_player]
    identity.text = "玩家 %d   ·   %d 币   ·   %d 船员" % [player.player_id + 1, player.cash, player.available]
    identity.modulate = STATE.PLAYER_COLORS[state.current_player].lightened(0.4)
    roll_button.text = "掷骰 %d/3" % state.rolls
    roll_button.disabled = moving or state.rolls >= 3 or harbor.paused
    restart.visible = state.rolls >= 3
    restart.disabled = moving
    pause_button.text = "▶" if harbor.paused else "Ⅱ"
    detail.visible = not observing and (harbor.selected >= 0 or info)
    if observing:
        return
    if info:
        title.text = "三船空间与派遣验证"
        status.text = "点船近看，点岗位后确认。V 总览，空格暂停。\n仅含船上派遣与三次骰子，未接入整局规则。"
        for button in slot_buttons:
            button.visible = false
        confirm.visible = false
        return
    if harbor.selected < 0:
        return
    var data: Dictionary = state.ships[harbor.selected]
    title.text = "%s  ·  %s" % [STATE.CARGO[data.cargo_id].label, "已到港" if data.arrived else "航线 %d" % (harbor.selected + 1)]
    for i in 4:
        var button := slot_buttons[i]
        button.visible = i < data.slots.size()
        if not button.visible:
            continue
        var slot: Dictionary = data.slots[i]
        button.text = "%d · %s" % [i + 1, "%d币" % slot.cost if slot.owner < 0 else "玩家%d" % (slot.owner + 1)]
        button.modulate = Color("f3d38d") if selected_slot == i else Color.WHITE
    confirm.visible = selected_slot >= 0 and selected_slot < data.slots.size()
    status.text = ""
    if confirm.visible:
        var error: String = state.placement_error(harbor.selected, selected_slot, state.current_player)
        status.text = error if not error.is_empty() else "派遣费用 %d 币" % data.slots[selected_slot].cost
        confirm.disabled = not error.is_empty() or moving
    if Time.get_ticks_msec() < message_until:
        status.text = message
