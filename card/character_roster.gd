extends Control

signal character_confirmed(character_id: String, display_name: String)
signal closed

const Pixel := preload("res://card/pixel_card_theme.gd")
const Card := preload("res://card/character_card.gd")
const PixelButton := preload("res://card/pixel_card_button.gd")

const GATHER_LEAD := 0.076
const GATHER_STAGGER := 0.032
const GATHER_TRAVEL := 0.228
const GATHER_SETTLE := 0.186
const STACK_OFFSET := Vector2(3, 4)

var cards: Array[Card] = []
var selected_index := -1
var confirmed_index := -1
var _scroll: ScrollContainer
var _sheet: Control
var _title: Label
var _subtitle: Label
var _status: Label
var _confirm: PixelButton
var _close: PixelButton
var _margin := 48.0
var _footer_y := 0.0
var _header_line_y := 154.0
var _gather_layer: Control
var _gather_tween: Tween
var _gathering := false
var _gather_origins: Array[Vector2] = []
var _gather_ranks: Array[int] = []
var _gather_elapsed := 0.0
var _gather_scroll_vertical := 0


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_scroll = ScrollContainer.new()
	_scroll.name = "RosterScroll"
	_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_SHOW_NEVER
	_scroll.follow_focus = true
	add_child(_scroll)
	_sheet = $Cards
	_sheet.reparent(_scroll)
	_sheet.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for child in _sheet.get_children():
		if child is Card:
			cards.append(child)
			child.pressed.connect(_select_card.bind(cards.size() - 1))
	_title = Pixel.label(self, "选择角色", Rect2(), 36, Pixel.PAPER)
	_subtitle = Pixel.label(self, "MANILA  /  CREW REGISTER", Rect2(), 18, Pixel.MUTED)
	_status = Pixel.label(self, "尚未选择", Rect2(), 24, Pixel.MUTED)
	_confirm = PixelButton.new()
	_confirm.name = "ConfirmCharacter"
	_confirm.caption = "确认登船"
	_confirm.primary = true
	_confirm.disabled = true
	_confirm.pressed.connect(_confirm_selection)
	add_child(_confirm)
	_close = PixelButton.new()
	_close.name = "CloseRoster"
	_close.glyph = "close"
	_close.tooltip_text = "返回航线"
	_close.pressed.connect(close)
	add_child(_close)
	_gather_layer = Control.new()
	_gather_layer.name = "GatherLayer"
	_gather_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	# Keep the same visible area as the list, without its scrolling or layout updates.
	_gather_layer.clip_contents = true
	_gather_layer.z_index = 1
	_gather_layer.hide()
	add_child(_gather_layer)
	resized.connect(_layout)
	visibility_changed.connect(_on_visibility_changed)
	_layout()


func open() -> void:
	if _gathering:
		return
	show()
	_select_card(confirmed_index)
	_layout()
	var target: Card = cards[maxi(confirmed_index, 0)]
	target.grab_focus()
	# A hidden/resized ScrollContainer needs one layout frame before its new scroll range is usable.
	await get_tree().process_frame
	if is_visible_in_tree() and not _gathering and target.has_focus():
		_scroll.ensure_control_visible(target)


func close() -> void:
	if not visible:
		return
	_reset_gather()
	hide()
	closed.emit()


func _on_visibility_changed() -> void:
	if is_inside_tree() and not is_visible_in_tree():
		_reset_gather()


func _unhandled_input(event: InputEvent) -> void:
	if is_visible_in_tree() and event.is_action_pressed("ui_cancel"):
		close()
		get_viewport().set_input_as_handled()


func _select_card(index: int) -> void:
	if _gathering:
		return
	selected_index = index
	for i in cards.size():
		cards[i].set_selected(i == index)
	_confirm.disabled = index < 0
	_confirm.queue_redraw()
	if index >= 0:
		_status.text = "已选择  /  " + cards[index].character_name
		_status.add_theme_color_override("font_color", Pixel.GOLD)
	else:
		_status.text = "尚未选择"
		_status.add_theme_color_override("font_color", Pixel.MUTED)
	queue_redraw()


func _confirm_selection() -> void:
	if selected_index < 0 or _gathering or not is_visible_in_tree():
		return
	confirmed_index = selected_index
	var chosen: Card = cards[confirmed_index]
	_start_gather()
	# Confirmation commits once; closing during the animation only skips its remaining feedback.
	character_confirmed.emit(chosen.character_name_en, chosen.character_name)


func _start_gather() -> void:
	_gathering = true
	_gather_elapsed = 0.0
	_gather_scroll_vertical = _scroll.scroll_vertical
	_scroll.follow_focus = false
	_confirm.disabled = true
	_confirm.caption = "正在登船"
	_confirm.queue_redraw()
	_status.text = "正在登船  /  " + cards[confirmed_index].character_name
	_gather_origins.resize(cards.size())
	_gather_ranks.resize(cards.size())
	_gather_layer.show()
	var order: Array[int] = [confirmed_index]
	for distance in range(1, cards.size()):
		for index in [confirmed_index - distance, confirmed_index + distance]:
			if index >= 0 and index < cards.size():
				order.append(index)
	for rank in order.size():
		var index := order[rank]
		var card: Card = cards[index]
		card.set_animation_locked(true)
		card.reparent(_gather_layer, true)
		card.pivot_offset = Card.CARD_SIZE * 0.5
		card.z_index = cards.size() - rank
		var origin := card.position
		# Unseen rows enter from just beyond the list edge instead of travelling several screens.
		origin.y = clampf(origin.y, -Card.CARD_SIZE.y - 16.0, _gather_layer.size.y + 16.0)
		_gather_origins[index] = (origin + card.pivot_offset) / _gather_layer.size
		_gather_ranks[index] = rank
	_scroll.hide()
	_update_gather(0.0)
	var duration := GATHER_LEAD + (cards.size() - 1) * GATHER_STAGGER + GATHER_TRAVEL + GATHER_SETTLE
	_gather_tween = create_tween().set_ignore_time_scale(true)
	_gather_tween.tween_method(_update_gather, 0.0, duration, duration)
	_gather_tween.finished.connect(close)


func _update_gather(elapsed: float) -> void:
	_gather_elapsed = elapsed
	var stack_extent := STACK_OFFSET * (cards.size() - 1)
	var stack_size := Card.CARD_SIZE + stack_extent
	var fit_scale := minf(1.0, minf((_gather_layer.size.x - 24.0) / stack_size.x, (_gather_layer.size.y - 24.0) / stack_size.y))
	fit_scale = maxf(0.1, fit_scale)
	var arc_height := minf(22.0, maxf(0.0, (_gather_layer.size.y - stack_size.y * fit_scale) * 0.5 - 12.0))
	var arrival := GATHER_LEAD + (cards.size() - 1) * GATHER_STAGGER + GATHER_TRAVEL
	var settle := clampf((elapsed - arrival) / GATHER_SETTLE, 0.0, 1.0)
	var rebound := sin(settle * TAU) * (1.0 - settle) * 5.0
	var lift := 6.0 * (1.0 - pow(1.0 - clampf(elapsed / 0.06, 0.0, 1.0), 3.0))
	for i in cards.size():
		var card: Card = cards[i]
		var rank := _gather_ranks[i]
		var progress := clampf((elapsed - GATHER_LEAD - rank * GATHER_STAGGER) / GATHER_TRAVEL, 0.0, 1.0)
		var eased := 1.0 - pow(1.0 - progress, 3.0)
		var origin := _gather_origins[i] * _gather_layer.size - Vector2(0, lift)
		var target := _gather_layer.size * 0.5 + (STACK_OFFSET * rank - stack_extent * 0.5) * fit_scale
		var center := origin.lerp(target, eased)
		center.y += rebound - sin(progress * PI) * arc_height
		card.scale = Vector2.ONE * lerpf(1.0, fit_scale, eased)
		card.position = (center - card.pivot_offset).round()


func _reset_gather() -> void:
	if _gather_tween and _gather_tween.is_valid():
		_gather_tween.kill()
	_gather_tween = null
	if not _gathering:
		return
	_gathering = false
	_gather_layer.hide()
	for i in cards.size():
		var card: Card = cards[i]
		card.reparent(_sheet, false)
		_sheet.move_child(card, i)
		card.scale = Vector2.ONE
		card.pivot_offset = Vector2.ZERO
		card.z_index = 0
		card.set_animation_locked(false)
	_gather_origins.clear()
	_gather_ranks.clear()
	_scroll.show()
	_scroll.follow_focus = true
	_scroll.scroll_vertical = _gather_scroll_vertical
	_confirm.caption = "确认登船"
	_confirm.disabled = selected_index < 0
	_confirm.queue_redraw()
	_layout()


func _layout() -> void:
	if not _scroll:
		return
	_margin = 48.0 if size.x >= 1000 else 16.0
	var narrow := size.x < 700
	var header_height := 180.0 if not narrow else 128.0
	var footer_height := 128.0 if not narrow else 108.0
	_header_line_y = 154.0 if not narrow else 116.0
	_footer_y = size.y - footer_height
	_title.position = Vector2(_margin + 66, 44 if not narrow else 20)
	_title.size = Vector2(size.x - _margin * 2 - 150, 60)
	_subtitle.position = Vector2(_margin, 112 if not narrow else 80)
	_subtitle.size = Vector2(size.x - _margin * 2, 32)
	_close.position = Vector2(size.x - _margin - 64, 42 if not narrow else 20)
	_close.size = Vector2(64, 64)
	_scroll.position = Vector2(_margin, header_height)
	_scroll.size = Vector2(size.x - _margin * 2, maxf(100, _footer_y - header_height - 12))
	_gather_layer.position = _scroll.position
	_gather_layer.size = _scroll.size
	var gap := 20.0
	var available := size.x - _margin * 2 - 16.0
	var columns := clampi(floori((available + gap) / (Card.CARD_SIZE.x + gap)), 1, cards.size())
	if columns in [4, 5]:
		columns = 3
	var rows := ceili(float(cards.size()) / columns)
	var total_width := columns * Card.CARD_SIZE.x + (columns - 1) * gap
	var total_height := rows * Card.CARD_SIZE.y + (rows - 1) * 24.0 + 24.0
	_sheet.custom_minimum_size = Vector2(available, total_height)
	_sheet.size = Vector2(available, maxf(total_height, _scroll.size.y))
	var origin := Vector2(maxf(0, (available - total_width) * 0.5), maxf(12, (_scroll.size.y - total_height) * 0.5 + 12))
	if not _gathering:
		for i in cards.size():
			var card: Card = cards[i]
			card.position = (origin + Vector2(i % columns * (Card.CARD_SIZE.x + gap), floori(float(i) / columns) * (Card.CARD_SIZE.y + 24))).round()
			card.size = Card.CARD_SIZE
			card.focus_neighbor_left = card.get_path_to(cards[maxi(0, i - 1)])
			card.focus_neighbor_right = card.get_path_to(cards[mini(cards.size() - 1, i + 1)])
			card.focus_neighbor_top = card.get_path_to(cards[maxi(0, i - columns)])
			card.focus_neighbor_bottom = card.get_path_to(cards[i + columns]) if i + columns < cards.size() else card.get_path_to(_confirm)
	else:
		_update_gather(_gather_elapsed)
	_confirm.position = Vector2(size.x - _margin - 252, _footer_y + (42 if narrow else 32))
	_confirm.size = Vector2(252, 64)
	_status.position = Vector2(_margin + 34, _footer_y + (4 if narrow else 46))
	_status.size = Vector2(size.x - _margin * 2 - (34 if narrow else 320), 36)
	queue_redraw()


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.045, 0.075, 0.075, 0.94))
	# Chart ticks frame the roster without placing another panel behind the cards.
	var line_color := Color("52736b")
	draw_rect(Rect2(_margin, _header_line_y, maxf(0, size.x - _margin * 2), 2), line_color)
	draw_rect(Rect2(_margin, _footer_y, maxf(0, size.x - _margin * 2), 2), line_color)
	for x in range(int(_margin), int(size.x - _margin), 24):
		draw_rect(Rect2(x, _header_line_y + 2, 2, 6 if (x - int(_margin)) % 96 else 10), Color(line_color, 0.6))
	Pixel.icon(self, "anchor", Vector2(_margin + 4, 50 if size.x >= 700 else 28), 4, Pixel.GOLD)
	Pixel.icon(self, "diamond", Vector2(_margin, _footer_y + (14 if size.x < 700 else 56)), 2, Pixel.GOLD if selected_index >= 0 else Pixel.MUTED)
