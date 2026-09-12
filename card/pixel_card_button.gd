extends Button

const Pixel := preload("res://card/pixel_card_theme.gd")

var caption := ""
var glyph := "arrow"
var primary := false


func _ready() -> void:
	custom_minimum_size = Vector2(64, 64)
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	Pixel.clear_button_styles(self)
	for event in [mouse_entered, mouse_exited, focus_entered, focus_exited, button_down, button_up]:
		event.connect(queue_redraw)
	resized.connect(queue_redraw)


func _draw() -> void:
	var active := not disabled and (is_hovered() or has_focus())
	var fill := Pixel.TEAL if primary else Pixel.INK
	if active:
		fill = fill.lightened(0.13)
	if disabled:
		fill = Color("33413f")
	var edge := Pixel.GOLD if active else Color("6c8b83")
	var ink := Pixel.PAPER if not disabled else Color("83958c")
	var down := 3.0 if is_pressed() else 0.0
	Pixel.step_rect(self, Rect2(0, 4, size.x, size.y - 4), 8, Color("101b1b"))
	Pixel.step_rect(self, Rect2(0, down, size.x, size.y - 4), 8, edge)
	Pixel.step_rect(self, Rect2(3, 3 + down, size.x - 6, size.y - 10), 6, fill)
	if caption.is_empty():
		Pixel.icon(self, glyph, (size - Vector2(27, 27)) * 0.5 + Vector2(0, down - 2), 3, ink)
	else:
		var text_width := Pixel.FONT.get_string_size(caption, HORIZONTAL_ALIGNMENT_LEFT, -1, 24).x
		var start := (size.x - text_width - 48.0) * 0.5
		Pixel.icon(self, glyph, Vector2(start, (size.y - 27) * 0.5 + down - 2), 3, ink)
		var baseline := (size.y - Pixel.FONT.get_height(24)) * 0.5 + Pixel.FONT.get_ascent(24) + down - 2
		draw_string(Pixel.FONT, Vector2(start + 48, baseline), caption, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, ink)
