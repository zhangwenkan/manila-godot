extends RefCounted

const Pixel := preload("res://card/pixel_card_theme.gd")
const FRAME := preload("res://ui/textures/dialog/wood_frame.png")
const SCROLL := preload("res://ui/textures/dialog/title_scroll.png")
const CLOSE := preload("res://ui/textures/dialog/close.png")
const INK := Color("35271e")
const PAPER := Color("f6e2bb")
const MUTED := Color("c7b69b")
const GOLD := Color("d7ac6a")
const PANEL := Color("302a24")
const SHADE := Color(0.055, 0.04, 0.03, 0.76)


# Source corners are kept intact; only straight rails and the dark inset stretch.
static func frame(target: CanvasItem, rect: Rect2, corner := 62.0) -> void:
	var edge := minf(corner, minf(rect.size.x, rect.size.y) * 0.25)
	var source := FRAME.get_size()
	var sx := [0.0, 156.0, source.x - 156.0, source.x]
	var sy := [0.0, 156.0, source.y - 156.0, source.y]
	var dx := [rect.position.x, rect.position.x + edge, rect.end.x - edge, rect.end.x]
	var dy := [rect.position.y, rect.position.y + edge, rect.end.y - edge, rect.end.y]
	for y in 3:
		for x in 3:
			target.draw_texture_rect_region(FRAME,
				Rect2(dx[x], dy[y], dx[x + 1] - dx[x], dy[y + 1] - dy[y]),
				Rect2(sx[x], sy[y], sx[x + 1] - sx[x], sy[y + 1] - sy[y]))


static func header(target: CanvasItem, rect: Rect2, title: String, font_size := 32) -> void:
	var source := SCROLL.get_size()
	var edge := minf(132.0 * rect.size.y / source.y, rect.size.x * 0.3)
	var sx := [0.0, 132.0, source.x - 132.0, source.x]
	var dx := [rect.position.x, rect.position.x + edge, rect.end.x - edge, rect.end.x]
	for x in 3:
		target.draw_texture_rect_region(SCROLL,
			Rect2(dx[x], rect.position.y, dx[x + 1] - dx[x], rect.size.y),
			Rect2(sx[x], 0, sx[x + 1] - sx[x], source.y))
	center_text(target, title, rect.grow_individual(-edge - 8, -6, -edge - 8, -6), font_size, INK)


static func center_text(target: CanvasItem, text: String, rect: Rect2, font_size := 24, color := PAPER) -> void:
	while font_size > 12 and Pixel.FONT.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x > rect.size.x:
		font_size -= 1
	var width := Pixel.FONT.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
	var baseline := (rect.size.y - Pixel.FONT.get_height(font_size)) * 0.5 + Pixel.FONT.get_ascent(font_size)
	target.draw_string(Pixel.FONT, rect.position + Vector2((rect.size.x - width) * 0.5, baseline), text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, color)


static func close_icon(target: CanvasItem, rect: Rect2, hovered := false, pressed := false, disabled := false, focused := false) -> void:
	var side := minf(rect.size.x, rect.size.y)
	var art := Rect2(rect.get_center() - Vector2.ONE * side * 0.5, Vector2.ONE * side)
	if pressed and not disabled:
		art = art.grow(-2)
		art.position.y += 2
	var tint := Color(0.58, 0.53, 0.49, 0.8) if disabled else Color(1.12, 1.08, 1.0) if hovered else Color.WHITE
	target.draw_texture_rect(CLOSE, art, false, tint)
	if focused and not disabled:
		target.draw_arc(rect.get_center(), side * 0.5 - 2, 0, TAU, 64, GOLD, 2, true)


static func decorate_close(button: Button) -> void:
	button.text = ""
	button.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	Pixel.clear_button_styles(button)
	button.draw.connect(func(): close_icon(button, Rect2(Vector2.ZERO, button.size), button.is_hovered(), button.is_pressed(), button.disabled, button.has_focus()))
	for event in [button.mouse_entered, button.mouse_exited, button.focus_entered, button.focus_exited, button.button_down, button.button_up, button.resized]:
		event.connect(button.queue_redraw)


static func button_style(primary := false, state := "normal") -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	var fill := Color("967043") if primary else Color("4c3d2e")
	if state == "hover" or state == "focus":
		fill = fill.lightened(0.16)
	elif state == "pressed":
		fill = fill.darkened(0.2)
	elif state == "disabled":
		fill = Color("39332c")
	style.bg_color = fill
	style.border_color = GOLD if state != "disabled" else Color("695c4b")
	style.set_border_width_all(2)
	style.set_corner_radius_all(5)
	style.shadow_color = Color(0.04, 0.025, 0.015, 0.4)
	style.shadow_size = 3
	style.shadow_offset = Vector2(0, 2)
	style.set_content_margin_all(6)
	return style


static func style_button(button: Button, primary := false) -> void:
	for state in ["normal", "hover", "pressed", "disabled", "focus"]:
		button.add_theme_stylebox_override(state, button_style(primary, state))
	button.add_theme_color_override("font_color", PAPER)
	button.add_theme_color_override("font_hover_color", Color("fff2d7"))
	button.add_theme_color_override("font_pressed_color", PAPER)
	button.add_theme_color_override("font_disabled_color", Color("a99a83"))
	button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND


static func action(target: CanvasItem, rect: Rect2, primary := false, enabled := true, hovered := false) -> void:
	var state := "disabled" if not enabled else "hover" if hovered else "normal"
	target.draw_style_box(button_style(primary, state), rect)
