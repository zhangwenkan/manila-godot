extends Control
## Screen-space speech, kept sharp and independent of the 3D render scale.

const LINE := "别惹老娘。\n我的船，我说了算。"
var label: Label
var _panel: StyleBoxFlat
var _anchor := Vector2.ZERO


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel = StyleBoxFlat.new()
	_panel.bg_color = Color("eeece5")
	_panel.border_color = Color("70747b")
	_panel.set_border_width_all(1)
	_panel.set_corner_radius_all(10)
	_panel.anti_aliasing = true
	_panel.shadow_color = Color(0.03, 0.04, 0.06, 0.24)
	_panel.shadow_size = 3
	_panel.shadow_offset = Vector2(0, 3)
	label = Label.new()
	label.text = LINE
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.autowrap_mode = TextServer.AUTOWRAP_OFF
	label.add_theme_color_override("font_color", Color("30333a"))
	add_child(label)


func arrange(region: Rect2, head: Vector2, font: Font, font_size: int) -> void:
	label.add_theme_font_override("font", font)
	label.add_theme_font_size_override("font_size", font_size)
	var text_width := font.get_string_size("我的船，我说了算。", HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
	var height := font.get_height(font_size) * 2.0 + 18.0
	size = Vector2(ceilf(text_width) + 20.0, ceilf(height))
	position = Vector2(clampf(head.x - size.x * 0.5, region.position.x, maxf(region.position.x, region.end.x - size.x)),
		maxf(region.position.y, head.y - size.y - 34.0)).round()
	label.position = Vector2(8, 6)
	label.size = size - Vector2(16, 12)
	_anchor = head - position
	queue_redraw()


func contains_point(point: Vector2) -> bool:
	var local := point - global_position
	if Rect2(Vector2.ZERO, size).has_point(local):
		return true
	var base_x := clampf(_anchor.x, 16, size.x - 16)
	var tip := Vector2(_anchor.x, clampf(_anchor.y - 8, size.y + 7, size.y + 24))
	return Geometry2D.is_point_in_polygon(local, PackedVector2Array([
		Vector2(base_x - 7, size.y - 1), tip, Vector2(base_x + 7, size.y - 1)]))


func _draw() -> void:
	if _panel == null:
		return
	draw_style_box(_panel, Rect2(Vector2.ZERO, size))
	var base_x := clampf(_anchor.x, 16, size.x - 16)
	var tip := Vector2(_anchor.x, clampf(_anchor.y - 8, size.y + 7, size.y + 24))
	var points := PackedVector2Array([Vector2(base_x - 7, size.y - 1), tip, Vector2(base_x + 7, size.y - 1)])
	draw_colored_polygon(points, _panel.bg_color)
	draw_line(points[0], points[1], _panel.border_color, 1, true)
	draw_line(points[1], points[2], _panel.border_color, 1, true)
