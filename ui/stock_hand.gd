extends Control

const Pixel := preload("res://card/pixel_card_theme.gd")
const CARD_SIZE := Vector2(216, 306)
const BACK := preload("res://stock/back.webp")
const FACES := {
	"ginseng": preload("res://stock/ginseng.webp"),
	"silk": preload("res://stock/silk.webp"),
	"jade": preload("res://stock/jade.webp"),
	"nutmeg": preload("res://stock/nutmeg.webp"),
}

@export var display_only := false

var cards: Array[Button] = []
var revealed: Array[bool] = []
var cargo_ids: Array[String] = []
var collapsed := false
var _faces: Array[TextureRect] = []
var _origins: Array[Vector2] = []
var _angles: Array[float] = []
var _hovered := -1
var _focused := -1
var _raised := -1
var _covering := false


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	clip_contents = false
	resized.connect(layout_cards)
	visibility_changed.connect(func():
		if not is_visible_in_tree():
			cover_all())
	layout_cards()


func set_holdings(ids: Array) -> void:
	var next_ids: Array[String] = []
	for id in ids:
		next_ids.append(str(id))
	if next_ids == cargo_ids and cards.size() == next_ids.size():
		return
	cover_all()
	for card in cards:
		remove_child(card)
		card.queue_free()
	cards.clear()
	_faces.clear()
	revealed.clear()
	_origins.clear()
	_angles.clear()
	cargo_ids.assign(next_ids)
	for i in cargo_ids.size():
		var card := Button.new()
		card.name = "StockCard%d" % i
		card.size = CARD_SIZE
		card.pivot_offset = CARD_SIZE * 0.5
		card.focus_mode = Control.FOCUS_NONE if display_only else Control.FOCUS_ALL
		card.mouse_filter = Control.MOUSE_FILTER_IGNORE if display_only else Control.MOUSE_FILTER_STOP
		card.mouse_default_cursor_shape = Control.CURSOR_ARROW if display_only else Control.CURSOR_POINTING_HAND
		card.disabled = collapsed
		Pixel.clear_button_styles(card)
		add_child(card)
		cards.append(card)
		revealed.append(false)
		_origins.append(Vector2.ZERO)
		_angles.append(0.0)
		var face := TextureRect.new()
		face.name = "Face"
		face.position = Vector2(4, 4)
		face.size = CARD_SIZE - Vector2(8, 8)
		face.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		face.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		face.mouse_filter = Control.MOUSE_FILTER_IGNORE
		face.texture = BACK
		card.add_child(face)
		_faces.append(face)
		card.draw.connect(_draw_card.bind(i))
		card.pressed.connect(_toggle_card.bind(i))
		card.mouse_entered.connect(_hover_card.bind(i, true))
		card.mouse_exited.connect(_hover_card.bind(i, false))
		card.focus_entered.connect(_focus_card.bind(i, true))
		card.focus_exited.connect(_focus_card.bind(i, false))
		_refresh_card(i)
	layout_cards()


func cover_all(defer_order := false) -> void:
	if _covering:
		return
	_covering = true
	_hovered = -1
	_focused = -1
	_raised = -1
	for i in cards.size():
		revealed[i] = false
		cards[i].release_focus()
		_refresh_card(i)
	if defer_order:
		# Focus notifications traverse children; cover now, reorder after traversal.
		_restore_order.call_deferred()
	else:
		_restore_order()
	_covering = false
	layout_cards()


func set_collapsed(value: bool) -> void:
	if collapsed == value:
		return
	collapsed = value
	if collapsed:
		cover_all()
	for card in cards:
		card.disabled = collapsed
	visible = not collapsed


func layout_cards() -> void:
	var count := cards.size()
	var spacing := minf(148.0, maxf(24.0, (size.x - CARD_SIZE.x - 70.0) / maxf(float(count - 1), 1.0)))
	for i in count:
		var offset := float(i) - float(count - 1) * 0.5
		var fan := offset / maxf(float(count - 1) * 0.5, 1.0)
		_angles[i] = deg_to_rad(fan * 18.0)
		var center := Vector2(size.x * 0.5 + offset * spacing, size.y - 62.0 + fan * fan * 20.0)
		if display_only:
			var inset := CARD_SIZE.y * 0.5 + 40.0
			var spread := minf(130.0, maxf(0.0, (size.x - 2.0 * inset) / maxf(float(count - 1), 1.0)))
			center = Vector2(size.x * 0.5 + offset * spread, size.y * 0.5 - 8.0 + fan * fan * 10.0)
		_origins[i] = center - CARD_SIZE * 0.5
		cards[i].position = _target_position(i)
		cards[i].rotation = 0.0 if i == _raised else _angles[i]


func _target_position(index: int) -> Vector2:
	if index == _raised:
		return Vector2(_origins[index].x, size.y - 106.0 - CARD_SIZE.y * 0.5)
	return _origins[index]


func _process(delta: float) -> void:
	if display_only or collapsed or not is_visible_in_tree():
		return
	var blend := 1.0 - exp(-18.0 * delta)
	for i in cards.size():
		cards[i].position = cards[i].position.lerp(_target_position(i), blend)
		cards[i].rotation = lerp_angle(cards[i].rotation, 0.0 if i == _raised else _angles[i], blend)


func _hover_card(index: int, entered: bool) -> void:
	if display_only or _covering or collapsed:
		return
	if entered:
		_hovered = index
	elif _hovered == index:
		_hovered = -1
	_update_raised()


func _focus_card(index: int, entered: bool) -> void:
	if display_only or _covering or collapsed:
		return
	if entered:
		_focused = index
	elif _focused == index:
		_focused = -1
	_update_raised()


func _update_raised() -> void:
	var next := _hovered if _hovered >= 0 else _focused
	if next == _raised:
		return
	_raised = next
	_restore_order()
	for card in cards:
		card.queue_redraw()


func _restore_order() -> void:
	# Sibling order, not just z_index, owns both drawing and native Control picking.
	for card in cards:
		move_child(card, get_child_count() - 1)
	if _raised >= 0 and _raised < cards.size():
		move_child(cards[_raised], get_child_count() - 1)


func _toggle_card(index: int) -> void:
	if display_only or collapsed or not is_visible_in_tree() or index < 0 or index >= cards.size():
		return
	if not FACES.has(cargo_ids[index]):
		return
	revealed[index] = not revealed[index]
	_refresh_card(index)


func _refresh_card(index: int) -> void:
	var is_face: bool = (display_only or revealed[index]) and FACES.has(cargo_ids[index])
	_faces[index].texture = FACES[cargo_ids[index]] if is_face else BACK
	cards[index].tooltip_text = "" if display_only else ("点击盖回股票" if is_face else "个人持股 · 点击翻面\n同屏请避看")
	cards[index].queue_redraw()


func _draw_card(index: int) -> void:
	var card := cards[index]
	var rect := Rect2(Vector2.ZERO, CARD_SIZE)
	Pixel.step_rect(card, Rect2(Vector2(4, 7), CARD_SIZE), 7, Color(0.03, 0.02, 0.06, 0.6))
	Pixel.step_rect(card, rect, 7, Color("17151f"))
	Pixel.step_rect(card, rect.grow(-2), 5, Color("f4e5bb") if index == _raised else Color("edc66c"))
	Pixel.step_rect(card, rect.grow(-4), 3, Color("b98d4b"))


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT or what == NOTIFICATION_WM_WINDOW_FOCUS_OUT:
		cover_all(true)
