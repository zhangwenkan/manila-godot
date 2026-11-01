extends Button

const Pixel := preload("res://card/pixel_card_theme.gd")
const DialogSkin := preload("res://ui/harbor_dialog_skin.gd")

var caption := ""
var glyph := "arrow"
var primary := false


func _ready() -> void:
	custom_minimum_size = Vector2(64, 64)
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR if glyph == "close" else CanvasItem.TEXTURE_FILTER_NEAREST
	Pixel.clear_button_styles(self)
	for event in [mouse_entered, mouse_exited, focus_entered, focus_exited, button_down, button_up]:
		event.connect(queue_redraw)
	resized.connect(queue_redraw)


func _draw() -> void:
	if glyph == "close":
		DialogSkin.close_icon(self, Rect2(Vector2.ZERO, size), is_hovered(), is_pressed(), disabled, has_focus())
		return
	var active := not disabled and (is_hovered() or has_focus())
	var ink := DialogSkin.PAPER if not disabled else DialogSkin.MUTED
	var down := 3.0 if is_pressed() else 0.0
	DialogSkin.action(self, Rect2(0, down, size.x, size.y - 4), primary, not disabled, active)
	if caption.is_empty():
		Pixel.icon(self, glyph, (size - Vector2(27, 27)) * 0.5 + Vector2(0, down - 2), 3, ink)
	else:
		var text_width := Pixel.FONT.get_string_size(caption, HORIZONTAL_ALIGNMENT_LEFT, -1, 24).x
		var start := (size.x - text_width - 48.0) * 0.5
		Pixel.icon(self, glyph, Vector2(start, (size.y - 27) * 0.5 + down - 2), 3, ink)
		var baseline := (size.y - Pixel.FONT.get_height(24)) * 0.5 + Pixel.FONT.get_ascent(24) + down - 2
		draw_string(Pixel.FONT, Vector2(start + 48, baseline), caption, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, ink)
