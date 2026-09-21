extends Button

const Pixel := preload("res://card/pixel_card_theme.gd")
const CARD_SIZE := Vector2(304, 568)
const ART_RECT := Rect2(20, 60, 264, 264)

@export var character_name := "角色"
@export var character_name_en := "Character"
@export_multiline var slogan := ""
@export var accent_color := Color("c99da7")
@export var portrait: Texture2D
## Optional dedicated in-game portrait; the card illustration stays independent.
@export var avatar: Texture2D
## Normalized illustration bounds, excluding the original frame and lettering.
@export var portrait_region := Rect2(0.09, 0.215, 0.82, 0.485)
## Normalized crop in avatar when supplied, otherwise in portrait.
@export var avatar_region := Rect2(0.3, 0.1, 0.4, 0.4)
@export var roster_number := 1
@export var country_code := "PH"
@export var trait_title := "航海者"

var selected := false
var _lift := 0.0
var _hovered := false
var _animation_locked := false
var _motion: Tween
var _labels: Control
var _source_region := Rect2()
var _body_ink := Pixel.INK
var _detail_color := Pixel.MUTED


func _ready() -> void:
	custom_minimum_size = CARD_SIZE
	size = CARD_SIZE
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	Pixel.clear_button_styles(self)
	var light_surface := accent_color.srgb_to_linear().get_luminance() > 0.22
	_body_ink = Color("222326") if light_surface else Color("f5f5f0")
	_detail_color = accent_color.darkened(0.5) if light_surface else accent_color.lightened(0.5)
	_labels = Control.new()
	_labels.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_labels)
	Pixel.label(_labels, trait_title, Rect2(62, 21, 174, 26), 20, Pixel.PAPER)
	var name_label := Pixel.label(_labels, character_name, Rect2(24, 341, 256, 44), 36, _body_ink)
	name_label.name = "CharacterName"
	var english_label := Pixel.label(_labels, character_name_en.to_upper(), Rect2(24, 388, 256, 26), 24, _body_ink.lerp(accent_color, 0.15))
	english_label.name = "CharacterNameEn"
	for label: Label in [name_label, english_label]:
		var font_size := label.get_theme_font_size("font_size")
		while Pixel.FONT.get_string_size(label.text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x > 256 and font_size > 16:
			font_size -= 2
		label.add_theme_font_size_override("font_size", font_size)
		label.size.x = 256
	var quote := Pixel.label(_labels, slogan, Rect2(24, 440, 256, 96), 20, _body_ink)
	quote.name = "Slogan"
	quote.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	quote.add_theme_constant_override("line_spacing", 0)
	if portrait:
		var texture_size := portrait.get_size()
		# Use the full texture, ignore portrait_region for now to debug
		_source_region = Rect2(Vector2.ZERO, texture_size)
		# Contain the image inside the square window without cropping - scale to fit
		var source_aspect := texture_size.x / texture_size.y
		var window_size := ART_RECT.size
		var draw_rect := ART_RECT
		if source_aspect > 1.0:
			# Wider than tall - fit width
			draw_rect.size.y = window_size.x / source_aspect
			draw_rect.position.y = ART_RECT.position.y + (window_size.y - draw_rect.size.y) * 0.5
		else:
			# Taller than wide - fit height
			draw_rect.size.x = window_size.y * source_aspect
			draw_rect.position.x = ART_RECT.position.x + (window_size.x - draw_rect.size.x) * 0.5
		# Store the fitted draw rect for use in _draw()
		set_meta("_fitted_art_rect", draw_rect)
	mouse_entered.connect(_set_hovered.bind(true))
	mouse_exited.connect(_set_hovered.bind(false))
	focus_entered.connect(_update_state)
	focus_exited.connect(_update_state)
	visibility_changed.connect(_reset_motion)
	queue_redraw()


func set_selected(value: bool) -> void:
	selected = value
	_update_state()


func set_animation_locked(value: bool) -> void:
	_animation_locked = value
	if _motion and _motion.is_valid():
		_motion.kill()
	_hovered = false
	disabled = value
	mouse_filter = Control.MOUSE_FILTER_IGNORE if value else Control.MOUSE_FILTER_STOP
	focus_mode = Control.FOCUS_NONE if value else Control.FOCUS_ALL
	# Keep the current lift while moving between parents; restore a stable rest pose afterwards.
	if not value:
		_set_lift(8.0 if selected else 0.0)
	queue_redraw()


func _set_hovered(value: bool) -> void:
	if _animation_locked:
		return
	_hovered = value
	_update_state()


func _update_state() -> void:
	if not is_node_ready() or _animation_locked:
		return
	if _motion and _motion.is_valid():
		_motion.kill()
	var target := 8.0 if selected or _hovered or has_focus() else 0.0
	_motion = create_tween().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_motion.tween_method(_set_lift, _lift, target, 0.14)
	queue_redraw()


func _set_lift(value: float) -> void:
	_lift = value
	_labels.position.y = -roundf(value)
	queue_redraw()


func _reset_motion() -> void:
	if is_visible_in_tree() or _animation_locked:
		return
	if _motion and _motion.is_valid():
		_motion.kill()
	_hovered = false
	if _labels:
		_set_lift(8.0 if selected else 0.0)


func _draw() -> void:
	var edge := accent_color.lightened(0.15)
	if selected:
		edge = Pixel.GOLD
	elif _hovered or has_focus():
		edge = accent_color.lightened(0.3)
	Pixel.step_rect(self, Rect2(8, 21, 292, 540), 8, Color(0.025, 0.045, 0.045, 0.7))
	draw_set_transform(Vector2(0, -roundf(_lift)))
	Pixel.step_rect(self, Rect2(0, 8, 304, 548), 12, Pixel.INK)
	Pixel.step_rect(self, Rect2(4, 12, 296, 540), 8, edge)
	Pixel.step_rect(self, Rect2(8, 16, 288, 532), 8, accent_color)
	draw_rect(Rect2(12, 20, 280, 320), accent_color.darkened(0.66))
	draw_rect(Rect2(16, 16, 272, 4), edge.lightened(0.35))
	draw_rect(Rect2(12, 24, 4, 512), Color(1, 1, 1, 0.22))
	draw_rect(Rect2(288, 24, 4, 512), Color(0, 0, 0, 0.18))
	draw_rect(Rect2(16, 56, 272, 272), edge.darkened(0.35))
	if portrait:
		var fitted_rect: Rect2 = get_meta("_fitted_art_rect", ART_RECT)
		draw_texture_rect_region(portrait, fitted_rect, _source_region)
	else:
		draw_rect(ART_RECT, accent_color.darkened(0.4))
	draw_rect(Rect2(20, 324, 264, 4), edge)
	_draw_flag(Vector2(248, 24), country_code, edge)
	draw_rect(Rect2(20, 52, 264, 2), Color(edge, 0.55))
	for corner: Vector2 in [Vector2(16, 56), Vector2(280, 56), Vector2(16, 320), Vector2(280, 320)]:
		draw_rect(Rect2(corner, Vector2(8, 8)), Pixel.GOLD)
		draw_rect(Rect2(corner + Vector2(2, 2), Vector2(3, 3)), Pixel.GOLD.lightened(0.3))
	draw_rect(Rect2(24, 428, 104, 2), _detail_color)
	draw_rect(Rect2(176, 428, 104, 2), _detail_color)
	Pixel.icon(self, "diamond", Vector2(144, 422), 2, _detail_color)
	for x in range(28, 280, 12):
		draw_rect(Rect2(x, 543, 4, 1), Color(_detail_color, 0.4))
	if selected:
		for x in [0, 292]:
			draw_rect(Rect2(x, 0, 12, 4), Pixel.GOLD)
			draw_rect(Rect2(x, 560, 12, 4), Pixel.GOLD)


func _draw_flag(origin: Vector2, code: String, edge: Color) -> void:
	var frame := Rect2(origin, Vector2(36, 22))
	var inner := Rect2(origin + Vector2(2, 2), Vector2(32, 18))
	draw_rect(frame, Color(edge, 0.7))
	draw_rect(inner, Color("e6ebe0"))
	match code:
		"ES":
			draw_rect(Rect2(inner.position, Vector2(32, 5)), Color("c94343"))
			draw_rect(Rect2(inner.position + Vector2(0, 5), Vector2(32, 8)), Color("f2c54f"))
			draw_rect(Rect2(inner.position + Vector2(0, 13), Vector2(32, 5)), Color("c94343"))
			draw_rect(Rect2(inner.position + Vector2(8, 7), Vector2(2, 5)), Color("a94b3e"))
		"US":
			for stripe in 7:
				draw_rect(Rect2(inner.position + Vector2(0, stripe * 18.0 / 7.0), Vector2(32, 18.0 / 7.0 + 0.5)), Color("d94b4b") if stripe % 2 == 0 else Color("f1e8d5"))
			draw_rect(Rect2(inner.position, Vector2(14, 10)), Color("315a91"))
			draw_rect(Rect2(inner.position + Vector2(5, 3), Vector2(3, 3)), Color("f2c54f"))
		"CN":
			draw_rect(inner, Color("d84040"))
			draw_colored_polygon(PackedVector2Array([inner.position + Vector2(5, 3), inner.position + Vector2(6, 5), inner.position + Vector2(8, 5), inner.position + Vector2(6.5, 6.2), inner.position + Vector2(7, 8), inner.position + Vector2(5, 6.8), inner.position + Vector2(3, 8), inner.position + Vector2(3.5, 6.2), inner.position + Vector2(2, 5), inner.position + Vector2(4, 5)]), Color("f2c54f"))
		"JP":
			draw_rect(inner, Color("f4eee0"))
			draw_rect(Rect2(inner.position + Vector2(12, 5), Vector2(8, 8)), Color("cf4a4a"))
			draw_rect(Rect2(inner.position + Vector2(10, 7), Vector2(12, 4)), Color("cf4a4a"))
		"TZ":
			draw_rect(inner, Color("2f7a70"))
			draw_colored_polygon(PackedVector2Array([inner.position, inner.position + Vector2(32, 0), inner.position + Vector2(0, 18)]), Color("2f63a0"))
			draw_colored_polygon(PackedVector2Array([inner.position + Vector2(32, 18), inner.position + Vector2(0, 18), inner.position + Vector2(32, 0)]), Color("e3bb48"))
			draw_colored_polygon(PackedVector2Array([inner.position + Vector2(0, 18), inner.position + Vector2(32, 0), inner.position + Vector2(32, 3), inner.position + Vector2(0, 18)]), Color("1d292c"))
		"PH":
			draw_rect(Rect2(inner.position, Vector2(32, 9)), Color("3974a8"))
			draw_rect(Rect2(inner.position + Vector2(0, 9), Vector2(32, 9)), Color("c94747"))
			draw_colored_polygon(PackedVector2Array([inner.position, inner.position + Vector2(13, 9), inner.position + Vector2(0, 18)]), Color("f4eee0"))
			draw_rect(Rect2(inner.position + Vector2(4, 7), Vector2(3, 4)), Color("f2c54f"))
