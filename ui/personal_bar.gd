@tool
extends Control

const Pixel := preload("res://card/pixel_card_theme.gd")
const CharacterCard := preload("res://card/character_card.gd")
const PORTRAIT_SHADER := preload("res://ui/pixel_portrait.gdshader")
const PORTRAIT_BACKGROUND := Color("b79a6f")
const DESIGN_SIZE := Vector2(1144, 128)
const CARGO_IDS := ["silk", "nutmeg", "jade", "ginseng"]
const STOCK_CARD_SIZE := Vector2(144, 204)
const STOCK_BACK_TEXTURE := preload("res://stock/back.webp")
const STOCK_FACE_TEXTURES := [
	preload("res://stock/silk.webp"),
	preload("res://stock/nutmeg.webp"),
	preload("res://stock/jade.webp"),
	preload("res://stock/ginseng.webp"),
]
const CARGO_NAMES := ["丝绸", "肉豆蔻", "玉石", "人参"]
const CARGO_BACKDROP := preload("res://ui/icons/hud/backdrop.png")
const COIN_TEXTURE := preload("res://ui/icons/hud/coin.png")
const CASH_COIN_TEXTURE := preload("res://ui/icons/hud/coin_total.png")
const STOCK_COIN_SIZE := Vector2(24, 24)
const CARGO_TEXTURES := [
	preload("res://ui/icons/hud/silk.png"),
	preload("res://ui/icons/hud/nutmeg.png"),
	preload("res://ui/icons/hud/jade.png"),
	preload("res://ui/icons/hud/ginseng.png"),
]
const CARGO_ICON_BOUNDS := [Vector2(60, 50), Vector2(50, 44), Vector2(48, 48), Vector2(46, 54)]
const CARGO_PANEL_WIDTH := 488.0
const CARGO_CELL_WIDTH := 116.0
# Leave a strip of the grass top visible in front of the cargo, above the soil face.
const CARGO_ICON_BASELINE := 56.0
const WOOD_DARK := Color("443b30")
const WOOD := Color("8c704d")
const RIM := Color("bc9a68")
const PAPER := Color("e1cda6")
const PAPER_LIGHT := Color("f0dfba")
const TEXT := Color("544332")
const SHADOW := Color(0.055, 0.105, 0.105, 0.4)
const HEART := [
	"01110001110",
	"12331013321",
	"13433333431",
	"13333333331",
	"01233333210",
	"00123332100",
	"00012321000",
	"00001210000",
	"00000100000",
]

@export var coins := 30:
	set(value):
		coins = maxi(0, value)
		_refresh_values()
@export_range(1, 999, 1, "or_greater") var round_number := 1:
	set(value):
		round_number = maxi(1, value)
		_refresh_values()
@export_range(3, 4, 1) var crew_capacity := 3:
	set(value):
		crew_capacity = clampi(value, 3, 4)
		remaining_crew = mini(remaining_crew, crew_capacity)
		_refresh_values()
@export_range(0, 4, 1) var remaining_crew := 3:
	set(value):
		remaining_crew = clampi(value, 0, crew_capacity)
		_refresh_values()

var character_id := ""
var stock_values := {"silk": 0, "nutmeg": 0, "jade": 0, "ginseng": 0}
var holdings: Array[String] = []
var is_harbor_master := false
var can_view_stocks := true
var _display_name := "尚未选择角色"
var _portrait: Texture2D
var _portrait_source := Rect2()
var _portrait_rect := Rect2(198, 30, 84, 84)
var _portrait_image: TextureRect
var _portrait_material: ShaderMaterial
var _crew_hint: Control
var _coins_value: Label
var _round_label: Label
var _stock_labels: Array[Label] = []
var _stock_hints: Array[Control] = []
var _stock_coins: Array[TextureRect] = []
var _stock_cards: Array[Button] = []
var _stock_card_faces: Array[TextureRect] = []
var _stock_revealed: Array[bool] = []
var _stock_scroll: ScrollContainer
var _stock_row: HBoxContainer
var _master_letters: Array[Label] = []


func _ready() -> void:
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	# Only the small information regions receive hover events; open water stays usable.
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_coins_value = Pixel.label(self, "—", Rect2(48, 42, 82, 40), 36, TEXT)
	_coins_value.name = "Coins"
	_create_coin("CashCoin", Rect2(12, 46, 32, 32), CASH_COIN_TEXTURE)
	_round_label = Pixel.label(self, "", Rect2(10, 86, 124, 30), 24, TEXT)
	_round_label.name = "Round"
	_round_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_portrait_material = ShaderMaterial.new()
	_portrait_material.shader = PORTRAIT_SHADER
	_portrait_material.set_shader_parameter("pixel_grid", 42.0)
	_portrait_material.set_shader_parameter("background_color", PORTRAIT_BACKGROUND)
	_portrait_material.set_shader_parameter("outline_color", WOOD_DARK)
	_portrait_material.set_shader_parameter("rim_color", RIM)
	_portrait_material.set_shader_parameter("wood_color", WOOD)
	_portrait_material.set_shader_parameter("shadow_color", SHADOW)
	_portrait_image = TextureRect.new()
	_portrait_image.name = "Portrait"
	# One surface owns the frame, opaque backing and portrait crop, including AA margins.
	var frame_rect := _portrait_rect.grow(11)
	_portrait_image.position = frame_rect.position
	_portrait_image.size = frame_rect.size
	_portrait_material.set_shader_parameter("draw_size", frame_rect.size)
	_portrait_material.set_shader_parameter("portrait_diameter", _portrait_rect.size.x)
	_portrait_image.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_portrait_image.material = _portrait_material
	_portrait_image.texture = ImageTexture.create_from_image(Image.create_empty(1, 1, false, Image.FORMAT_RGBA8))
	_portrait_image.show_behind_parent = true
	_portrait_image.mouse_filter = Control.MOUSE_FILTER_PASS
	add_child(_portrait_image)
	_crew_hint = Control.new()
	_crew_hint.name = "CrewHearts"
	_crew_hint.position = Vector2(268, 16)
	_crew_hint.size = Vector2(52, 112)
	_crew_hint.mouse_filter = Control.MOUSE_FILTER_PASS
	add_child(_crew_hint)
	for i in CARGO_IDS.size():
		var hint := Control.new()
		hint.name = CARGO_IDS[i].capitalize() + "Stock"
		hint.size = Vector2(CARGO_CELL_WIDTH, 120)
		hint.mouse_filter = Control.MOUSE_FILTER_PASS
		add_child(hint)
		_stock_hints.append(hint)
		var value_label := Pixel.label(self, "0", Rect2(), 24, TEXT)
		value_label.name = CARGO_IDS[i].capitalize() + "Value"
		_stock_labels.append(value_label)
		_stock_coins.append(_create_coin(CARGO_IDS[i].capitalize() + "Coin", Rect2(Vector2.ZERO, STOCK_COIN_SIZE), COIN_TEXTURE))

	for i in 3:
		var center := _portrait_rect.get_center() + Vector2.from_angle(deg_to_rad(220 - i * 40)) * 68
		var letter := Pixel.label(self, "港务长"[i], Rect2(center - Vector2(12, 12), Vector2(24, 24)), 22, WOOD_DARK)
		letter.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		_master_letters.append(letter)
	_stock_scroll = ScrollContainer.new()
	_stock_scroll.position = Vector2(336, -96)
	_stock_scroll.size = Vector2(304, 224)
	_stock_scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_stock_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO
	add_child(_stock_scroll)
	_stock_row = HBoxContainer.new()
	_stock_row.add_theme_constant_override("separation", 10)
	_stock_row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_stock_scroll.add_child(_stock_row)
	visibility_changed.connect(_on_visibility_changed)
	resized.connect(_refresh_values)
	_refresh_values()


func _create_coin(node_name: String, rect: Rect2, coin_texture: Texture2D) -> TextureRect:
	var icon := TextureRect.new()
	icon.name = node_name
	icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	icon.texture = coin_texture
	icon.position = rect.position
	icon.size = rect.size
	icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	icon.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(icon)
	return icon


static func preferred_height(_available_width: float) -> float:
	return DESIGN_SIZE.y


func get_content_rect() -> Rect2:
	return Rect2(Vector2.ZERO, size).merge(_stock_scroll.get_rect())


func set_character(card: CharacterCard) -> void:
	if character_id != card.character_name_en:
		conceal_stocks()
	character_id = card.character_name_en
	_display_name = card.character_name
	_portrait = card.avatar if card.avatar else card.portrait
	_portrait_material.set_shader_parameter("has_portrait", _portrait != null)
	_portrait_source = Rect2()
	if _portrait:
		_portrait_image.texture = _portrait
		var texture_size := _portrait.get_size()
		_portrait_source = Rect2(card.avatar_region.position * texture_size, card.avatar_region.size * texture_size)
		var crop := card.avatar_region
		_portrait_material.set_shader_parameter("source_region", Vector4(crop.position.x, crop.position.y, crop.size.x, crop.size.y))
	_refresh_values()


func set_resources(new_coins: int, new_remaining: int, capacity: int = 3) -> void:
	coins = new_coins
	crew_capacity = capacity
	remaining_crew = new_remaining


func set_stock_values(values: Dictionary) -> void:
	for cargo_id: String in CARGO_IDS:
		if values.has(cargo_id):
			stock_values[cargo_id] = maxi(0, int(values[cargo_id]))
	_refresh_values()


func set_holdings(cards: Array) -> void:
	holdings.assign(cards)
	for card in _stock_cards:
		_stock_row.remove_child(card)
		card.queue_free()
	_stock_cards.clear()
	_stock_card_faces.clear()
	_stock_revealed.clear()
	_stock_scroll.scroll_horizontal = 0
	for i in holdings.size():
		var card := Button.new()
		card.name = "StockCard%d" % (i + 1)
		card.custom_minimum_size = STOCK_CARD_SIZE
		card.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
		card.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		Pixel.clear_button_styles(card)
		_stock_row.add_child(card)
		_stock_cards.append(card)
		_stock_revealed.append(false)
		var face := TextureRect.new()
		face.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		face.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		face.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
		face.mouse_filter = Control.MOUSE_FILTER_IGNORE
		card.add_child(face)
		face.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		face.offset_left = 3
		face.offset_top = 3
		face.offset_right = -3
		face.offset_bottom = -3
		_stock_card_faces.append(face)
		card.pressed.connect(_toggle_stock.bind(i))
		card.draw.connect(_draw_stock_card.bind(card))
		card.mouse_entered.connect(card.queue_redraw)
		card.mouse_exited.connect(card.queue_redraw)
		card.focus_entered.connect(card.queue_redraw)
		card.focus_exited.connect(card.queue_redraw)
	_refresh_values()


func set_turn_context(master: bool, may_view_stocks: bool) -> void:
	is_harbor_master = master
	can_view_stocks = may_view_stocks
	if not can_view_stocks:
		conceal_stocks()
	_refresh_values()


func conceal_stocks() -> void:
	_stock_revealed.fill(false)
	for card in _stock_cards:
		card.release_focus()
	_refresh_values()


func _on_visibility_changed() -> void:
	if not is_visible_in_tree():
		conceal_stocks()


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		conceal_stocks()


func _refresh_values() -> void:
	if not is_instance_valid(_coins_value):
		return
	var chosen := not character_id.is_empty()
	_coins_value.text = str(coins) if chosen else "—"
	_fit_label(_coins_value, 36, 82)
	_round_label.text = "第 %d 航程" % round_number
	_fit_label(_round_label, 24, 124)
	_portrait_image.tooltip_text = _display_name
	_crew_hint.tooltip_text = "%s\n剩余小人：%d / %d\n每颗亮起的爱心代表一名可派遣小人" % [_display_name, remaining_crew, crew_capacity]
	for i in _stock_labels.size():
		var value_label := _stock_labels[i]
		var amount: int = stock_values[CARGO_IDS[i]]
		value_label.text = str(amount)
		_fit_label(value_label, 24, 82)
		var text_width := ceilf(Pixel.FONT.get_string_size(value_label.text, HORIZONTAL_ALIGNMENT_LEFT, -1, value_label.get_theme_font_size("font_size")).x)
		var cell_center := size.x - CARGO_PANEL_WIDTH + 12.0 + (i + 0.5) * CARGO_CELL_WIDTH
		var group_left := roundf(cell_center - (text_width + 8.0 + STOCK_COIN_SIZE.x) * 0.5)
		value_label.position = Vector2(group_left, 86)
		value_label.size = Vector2(text_width, 32)
		_stock_coins[i].position = Vector2(group_left + text_width + 8, 91)
		_stock_hints[i].position = Vector2(cell_center - CARGO_CELL_WIDTH * 0.5, 0)
		_stock_hints[i].tooltip_text = "%s · 公共行情\n%d 比索" % [CARGO_NAMES[i], amount]
	for letter in _master_letters:
		letter.visible = is_harbor_master and chosen
	_stock_scroll.size.x = maxf(304, size.x - CARGO_PANEL_WIDTH - 16 - _stock_scroll.position.x)
	for i in _stock_cards.size():
		var revealed: bool = _stock_revealed[i]
		_stock_card_faces[i].texture = STOCK_FACE_TEXTURES[CARGO_IDS.find(holdings[i])] if revealed else STOCK_BACK_TEXTURE
		_stock_cards[i].tooltip_text = "点击盖回股票" if revealed else "个人持股 · 点击翻面（同屏请避看）"
		_stock_cards[i].disabled = not chosen or not can_view_stocks
		_stock_cards[i].queue_redraw()
	queue_redraw()


func _toggle_stock(index: int) -> void:
	if not can_view_stocks or character_id.is_empty() or not is_visible_in_tree():
		return
	_stock_revealed[index] = not _stock_revealed[index]
	_refresh_values()


func _fit_label(value_label: Label, maximum: int, available: float) -> void:
	var font_size := maximum
	while Pixel.FONT.get_string_size(value_label.text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x > available and font_size > 12:
		font_size -= 2
	value_label.add_theme_font_size_override("font_size", font_size)


func _draw() -> void:
	if not is_instance_valid(_coins_value):
		return
	_draw_plaque(Rect2(0, 38, 144, 82))
	draw_rect(Rect2(12, 83, 120, 2), Color("c0a77f"))
	# The portrait floats between two small plaques instead of a full-width panel.
	var center := _portrait_rect.get_center()
	if not _portrait:
		Pixel.icon(self, "helm", center - Vector2(16, 15), 3, TEXT)
	var angles := [-40.0, 0.0, 40.0] if crew_capacity == 3 else [-46.0, -15.0, 15.0, 46.0]
	var heart_radius := 64.0 if crew_capacity == 3 else 60.0
	for i in crew_capacity:
		var heart_center := center + Vector2.from_angle(deg_to_rad(angles[i])) * heart_radius
		_draw_heart((heart_center - Vector2(11, 9)).snapped(Vector2(2, 2)), not character_id.is_empty() and i < remaining_crew)
	_draw_plaque(Rect2(size.x - CARGO_PANEL_WIDTH, 38, CARGO_PANEL_WIDTH, 82))
	for i in CARGO_IDS.size():
		var cell_center := size.x - CARGO_PANEL_WIDTH + 12.0 + (i + 0.5) * CARGO_CELL_WIDTH
		draw_texture_rect(CARGO_BACKDROP, Rect2(cell_center - 42, 24, 84, 62), false)
		var source_size: Vector2 = CARGO_TEXTURES[i].get_size()
		var bounds: Vector2 = CARGO_ICON_BOUNDS[i]
		var icon_size := (source_size * minf(bounds.x / source_size.x, bounds.y / source_size.y)).round()
		var icon_position := Vector2(roundf(cell_center - icon_size.x * 0.5), CARGO_ICON_BASELINE - icon_size.y)
		draw_texture_rect(CARGO_TEXTURES[i], Rect2(icon_position, icon_size), false)
	for letter in _master_letters:
		if letter.visible:
			Pixel.step_rect(self, letter.get_rect(), 4, RIM)


func _draw_stock_card(card: Button) -> void:
	if card.is_hovered() or card.has_focus():
		card.draw_rect(Rect2(Vector2.ONE, card.size - Vector2(2, 2)), PAPER_LIGHT, false, 2)


func _draw_plaque(rect: Rect2) -> void:
	Pixel.step_rect(self, Rect2(rect.position + Vector2(0, 4), rect.size), 6, SHADOW)
	Pixel.step_rect(self, rect, 6, WOOD_DARK)
	Pixel.step_rect(self, rect.grow(-2), 4, WOOD)
	Pixel.step_rect(self, rect.grow(-4), 2, PAPER)
	draw_rect(Rect2(rect.position + Vector2(8, 4), Vector2(rect.size.x - 16, 2)), PAPER_LIGHT)
	draw_rect(Rect2(rect.position + Vector2(8, rect.size.y - 7), Vector2(rect.size.x - 16, 3)), Color("cbb18a"))


func _draw_heart(origin: Vector2, available: bool) -> void:
	var palette := [Color.TRANSPARENT, Color("533930"), Color("a05043"), Color("d98468"), Color("f2c7a0")]
	if not available:
		palette = [Color.TRANSPARENT, Color("304b47"), Color("94a18a"), Color(0.08, 0.2, 0.19, 0.35), Color("94a18a")]
	for y in HEART.size():
		for x in HEART[y].length():
			var value := int(HEART[y][x])
			if value > 0:
				var cell := Rect2(origin + Vector2(x, y) * 2, Vector2(2, 2))
				draw_rect(Rect2(cell.position + Vector2(0, 2), cell.size), SHADOW)
				draw_rect(cell, palette[value])
