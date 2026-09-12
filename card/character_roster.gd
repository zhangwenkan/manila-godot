extends Control

signal character_confirmed(character_id: String, display_name: String)
signal closed

const Pixel := preload("res://card/pixel_card_theme.gd")
const Card := preload("res://card/character_card.gd")
const PixelButton := preload("res://card/pixel_card_button.gd")

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
	resized.connect(_layout)
	_layout()


func open() -> void:
	show()
	_select_card(confirmed_index)
	_layout()
	var target: Card = cards[maxi(confirmed_index, 0)]
	target.grab_focus()


func close() -> void:
	hide()
	closed.emit()


func _unhandled_input(event: InputEvent) -> void:
	if is_visible_in_tree() and event.is_action_pressed("ui_cancel"):
		close()
		get_viewport().set_input_as_handled()


func _select_card(index: int) -> void:
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
	if selected_index < 0:
		return
	confirmed_index = selected_index
	var chosen: Card = cards[confirmed_index]
	character_confirmed.emit(str(chosen.name), chosen.character_name)
	close()


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
	for i in cards.size():
		var card: Card = cards[i]
		card.position = (origin + Vector2(i % columns * (Card.CARD_SIZE.x + gap), floori(float(i) / columns) * (Card.CARD_SIZE.y + 24))).round()
		card.size = Card.CARD_SIZE
		card.focus_neighbor_left = card.get_path_to(cards[maxi(0, i - 1)])
		card.focus_neighbor_right = card.get_path_to(cards[mini(cards.size() - 1, i + 1)])
		card.focus_neighbor_top = card.get_path_to(cards[maxi(0, i - columns)])
		card.focus_neighbor_bottom = card.get_path_to(cards[i + columns]) if i + columns < cards.size() else card.get_path_to(_confirm)
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
