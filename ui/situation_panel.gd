@tool
extends Control

# 横向态势长条：一条低矮的横条，玩家从左到右排列，每段显示 主色点 + 名字 + 剩余小人。
# 点击展开：每位玩家的派遣去向竖列在其名字下方，列与列继续横向并排。
# 只显示公共信息（剩余小人、岗位分布），不含现金与股票（见 R01/R12）。

signal toggled(expanded: bool)

const Pixel := preload("res://card/pixel_card_theme.gd")
const CharacterCard := preload("res://card/character_card.gd")
const PersonalBar := preload("res://ui/personal_bar.gd")

const GROUP_KEYS := ["ship_0", "ship_1", "ship_2", "harbor", "shipyard", "pirate", "pilot", "insurance"]
const BAR_H := 26.0
const DETAIL_LINE_H := 16.0
const EDGE := 8.0            # 左右边距
const CELL_GAP := 12.0       # 段间距
const NAME_FONT := 15
const DETAIL_FONT := 13

var _players: Array[CharacterCard] = []
var _current_id := ""
var _resources: Dictionary = {}
var _owners: Dictionary = {}
var _voyage_number := 1
var _ship_names: Array = ["人参", "丝绸", "玉石"]   # 本航程三船货物名，随港务长选货更新
var _expanded := false
var _hover := false
var _cell_x: Array[float] = []       # 每段起始 x
var _cell_w: Array[float] = []       # 每段宽度
var _max_lines := 0                  # 展开时最多派遣项数（决定下拉高度）


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	mouse_entered.connect(func(): _hover = true; queue_redraw())
	mouse_exited.connect(func(): _hover = false; queue_redraw())
	_refresh()


func set_situation(players: Array, current_id: String, resources: Dictionary, owners: Dictionary, voyage_number: int = 1, ship_names: Array = []) -> void:
	_players = players.duplicate()
	_current_id = current_id
	_resources = resources.duplicate()
	_owners = owners.duplicate()
	_voyage_number = maxi(1, voyage_number)
	if ship_names.size() == 3:
		_ship_names = ship_names.duplicate()
	_refresh()


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_expanded = not _expanded
		_refresh()
		toggled.emit(_expanded)
		accept_event()


func _text_w(text: String, font_size: int) -> float:
	return Pixel.FONT.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x


func _refresh() -> void:
	if not is_node_ready():
		return
	# 每段宽度 = max(点+名字+剩余, 最宽的派遣项)。
	_cell_x.clear()
	_cell_w.clear()
	_max_lines = 0
	var x := EDGE
	for card in _players:
		var res: Dictionary = _resources.get(card.character_name_en, {})
		var remaining := int(res.get("remaining", 0))
		var head_w := 12.0 + _text_w(_short_name(card.character_name), NAME_FONT) + 6.0 + _text_w("剩%d" % remaining, NAME_FONT)
		var cell_w := head_w
		var lines := _placement_lines(card)
		_max_lines = maxi(_max_lines, lines.size())
		for line in lines:
			cell_w = maxf(cell_w, 10.0 + _text_w(line, DETAIL_FONT))
		_cell_x.append(x)
		_cell_w.append(cell_w)
		x += cell_w + CELL_GAP
	var total_w: float = maxf(80.0, x - CELL_GAP + EDGE)
	var h := BAR_H
	if _expanded and _max_lines > 0:
		h += _max_lines * DETAIL_LINE_H + 6.0
	size = Vector2(total_w, h)
	queue_redraw()


func _place_label(id: String) -> String:
	if id.begins_with("ship_"):
		var ship := int(id.split("_")[1])
		return (_ship_names[ship] + "船") if ship < _ship_names.size() else "货船"
	if id.begins_with("harbor_"):
		return "港口" + ["A", "B", "C"][int(id.split("_")[1])]
	if id.begins_with("shipyard_"):
		return "船厂" + ["A", "B", "C"][int(id.split("_")[1])]
	if id == "pirate_0":
		return "海盗长"
	if id == "pirate_1":
		return "海盗副"
	if id == "pilot_0":
		return "小引航"
	if id == "pilot_1":
		return "大引航"
	if id.begins_with("insurance"):
		return "保险"
	return ""


# 返回该玩家的派遣项列表（同岗位多个合并成 "玉石船×2"），按 GROUP_KEYS 顺序。
func _placement_lines(card: CharacterCard) -> Array[String]:
	var order: Array[String] = []
	var tally := {}
	for key in GROUP_KEYS:
		for id in _owners:
			if not id.begins_with(key):
				continue
			var owner = _owners[id]
			if owner is CharacterCard and owner.character_name_en == card.character_name_en:
				var label := _place_label(id)
				if label.is_empty():
					continue
				if tally.has(label):
					tally[label] += 1
				else:
					tally[label] = 1
					order.append(label)
	var lines: Array[String] = []
	for label in order:
		lines.append(label if tally[label] == 1 else "%s×%d" % [label, tally[label]])
	return lines


func _short_name(full: String) -> String:
	var text := full
	var dot := text.find("·")
	if dot > 0:
		text = text.substr(0, dot)
	if text.length() > 4:
		text = text.substr(0, 4)
	return text


func _remaining_color(accent: Color, remaining: int) -> Color:
	if remaining <= 0:
		return Color(0.36, 0.30, 0.22, 0.55)
	return accent.darkened(0.4) if accent.get_luminance() > 0.7 else accent.darkened(0.1)


func _draw() -> void:
	var rect := Rect2(Vector2.ZERO, size)
	Pixel.step_rect(self, Rect2(rect.position + Vector2(0, 3), rect.size - Vector2(0, 3)), 5, PersonalBar.SHADOW)
	Pixel.step_rect(self, rect, 5, PersonalBar.WOOD_DARK)
	Pixel.step_rect(self, rect.grow(-2), 3, PersonalBar.PAPER)
	if _hover:
		Pixel.step_rect(self, Rect2(3, 3, size.x - 6, BAR_H - 4), 3, Color(PersonalBar.PAPER_LIGHT, 0.4))
	for i in _players.size():
		_draw_cell(i, _players[i])
	_draw_arrow(Vector2(size.x - 11, 13))
	if _expanded and _max_lines > 0:
		draw_rect(Rect2(6, BAR_H, size.x - 12, 1), Color(0.42, 0.34, 0.24, 0.5))
		for i in _players.size():
			_draw_detail(i, _players[i])


func _draw_cell(index: int, card: CharacterCard) -> void:
	if index >= _cell_x.size():
		return
	var x0: float = _cell_x[index]
	var is_current := card.character_name_en == _current_id
	var accent := card.accent_color
	if is_current:
		draw_rect(Rect2(x0 - 4, 4, _cell_w[index] + 8, BAR_H - 8), Color(accent, 0.14))
	# 主色点
	var dot := Vector2(x0 + 4, 13)
	draw_circle(dot, 4.0, PersonalBar.WOOD_DARK)
	draw_circle(dot, 3.0, accent)
	if is_current:
		draw_arc(dot, 6.0, 0, TAU, 14, PersonalBar.RIM, 1.2)
	# 名字
	var name_x := x0 + 12.0
	draw_string(Pixel.FONT, Vector2(name_x, 18), _short_name(card.character_name), HORIZONTAL_ALIGNMENT_LEFT, -1, NAME_FONT, PersonalBar.TEXT)
	# 剩余
	var res: Dictionary = _resources.get(card.character_name_en, {})
	var remaining := int(res.get("remaining", 0))
	var rx := name_x + _text_w(_short_name(card.character_name), NAME_FONT) + 6.0
	draw_string(Pixel.FONT, Vector2(rx, 18), "剩%d" % remaining, HORIZONTAL_ALIGNMENT_LEFT, -1, NAME_FONT, _remaining_color(accent, remaining))
	# 段分隔
	if index < _players.size() - 1:
		var sep_x: float = x0 + _cell_w[index] + CELL_GAP * 0.5
		draw_rect(Rect2(sep_x, 6, 1, size.y - 12), Color(0.42, 0.34, 0.24, 0.25))


func _draw_arrow(center: Vector2) -> void:
	var col := Color(PersonalBar.TEXT, 0.55)
	if _expanded:
		draw_colored_polygon(PackedVector2Array([center + Vector2(-4, 2), center + Vector2(4, 2), center + Vector2(0, -3)]), col)
	else:
		draw_colored_polygon(PackedVector2Array([center + Vector2(-4, -3), center + Vector2(4, -3), center + Vector2(0, 3)]), col)


func _draw_detail(index: int, card: CharacterCard) -> void:
	if index >= _cell_x.size():
		return
	var x0: float = _cell_x[index]
	var lines := _placement_lines(card)
	if lines.is_empty():
		draw_string(Pixel.FONT, Vector2(x0 + 2, BAR_H + 18), "待派遣", HORIZONTAL_ALIGNMENT_LEFT, -1, DETAIL_FONT, Color(0.4, 0.33, 0.24, 0.5))
		return
	for i in lines.size():
		var ly := BAR_H + 6.0 + i * DETAIL_LINE_H + 12.0
		draw_string(Pixel.FONT, Vector2(x0 + 2, ly), lines[i], HORIZONTAL_ALIGNMENT_LEFT, _cell_w[index] + 6.0, DETAIL_FONT, Color(0.33, 0.27, 0.2, 0.92))
