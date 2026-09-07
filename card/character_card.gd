extends TextureRect

@export var character_name := "角色"
@export var character_name_en := "Character"
@export var slogan := "The Queen of Manhattan"
@export var accent_color := Color8(167, 50, 52)
@export var portrait: Texture2D

func _ready() -> void:
	custom_minimum_size = Vector2(400, 534)
	texture = _create_card_texture()
	expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	stretch_mode = TextureRect.STRETCH_SCALE
	mouse_filter = Control.MOUSE_FILTER_STOP
	clip_contents = false
	_ensure_text_labels()

func _create_card_texture() -> ImageTexture:
	var image := Image.create(400, 534, false, Image.FORMAT_RGBA8)
	image.fill(Color.TRANSPARENT)

	_draw_rect(image, Rect2i(0, 0, 400, 534), Color8(39, 30, 25))
	_draw_rect(image, Rect2i(12, 12, 376, 510), Color8(229, 204, 153))
	_draw_rect(image, Rect2i(24, 24, 352, 486), Color8(73, 55, 43))
	_draw_rect(image, Rect2i(32, 32, 336, 470), Color8(238, 219, 172))

	_draw_rect(image, Rect2i(46, 46, 308, 68), accent_color.darkened(0.3))
	_draw_rect(image, Rect2i(50, 50, 300, 60), accent_color)
	_draw_rect(image, Rect2i(58, 58, 284, 44), Color8(252, 236, 196))
	_draw_rect(image, Rect2i(58, 58, 284, 2), accent_color.darkened(0.4))
	_draw_rect(image, Rect2i(58, 100, 284, 2), accent_color.darkened(0.4))
	_draw_name_plate(image)

	_draw_rect(image, Rect2i(46, 122, 308, 240), Color8(35, 28, 24))
	_draw_rect(image, Rect2i(50, 126, 300, 232), Color8(58, 44, 36))
	_draw_portrait(image, Rect2i(58, 134, 284, 216))

	_draw_rect(image, Rect2i(46, 372, 308, 4), accent_color.darkened(0.4))

	_draw_rect(image, Rect2i(46, 432, 308, 64), accent_color.darkened(0.3))
	_draw_rect(image, Rect2i(50, 436, 300, 56), Color8(244, 224, 178))
	_draw_rect(image, Rect2i(50, 436, 300, 2), accent_color.darkened(0.4))
	_draw_rect(image, Rect2i(50, 490, 300, 2), accent_color.darkened(0.4))
	_draw_decorations(image)
	_apply_rounded_corners(image, 24)

	return ImageTexture.create_from_image(image)

func _apply_rounded_corners(image: Image, radius: int) -> void:
	var w := image.get_width()
	var h := image.get_height()
	for y in range(radius):
		for x in range(radius):
			var dx := radius - x
			var dy := radius - y
			if dx * dx + dy * dy > radius * radius:
				image.set_pixel(x, y, Color.TRANSPARENT)
				image.set_pixel(w - 1 - x, y, Color.TRANSPARENT)
				image.set_pixel(x, h - 1 - y, Color.TRANSPARENT)
				image.set_pixel(w - 1 - x, h - 1 - y, Color.TRANSPARENT)

func _ensure_text_labels() -> void:
	for child in get_children():
		if child is Label and child.name.begins_with("Card"):
			child.queue_free()

	var name_label := Label.new()
	name_label.name = "CardNameLabel"
	name_label.text = character_name
	name_label.position = Vector2(58, 56)
	name_label.size = Vector2(284, 30)
	name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	name_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	name_label.add_theme_font_size_override("font_size", 28)
	name_label.add_theme_color_override("font_color", accent_color.darkened(0.5))
	name_label.add_theme_color_override("font_shadow_color", Color(1, 1, 1, 0.4))
	name_label.add_theme_constant_override("shadow_offset_x", 1)
	name_label.add_theme_constant_override("shadow_offset_y", 1)
	name_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(name_label)

	var name_en_label := Label.new()
	name_en_label.name = "CardNameEnLabel"
	name_en_label.text = character_name_en
	name_en_label.position = Vector2(58, 84)
	name_en_label.size = Vector2(284, 18)
	name_en_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	name_en_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	name_en_label.add_theme_font_size_override("font_size", 14)
	name_en_label.add_theme_color_override("font_color", accent_color.darkened(0.25))
	name_en_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(name_en_label)

	var slogan_label := Label.new()
	slogan_label.name = "CardSloganLabel"
	slogan_label.text = slogan
	slogan_label.position = Vector2(58, 438)
	slogan_label.size = Vector2(284, 52)
	slogan_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	slogan_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	slogan_label.add_theme_font_size_override("font_size", 17)
	slogan_label.add_theme_color_override("font_color", Color8(92, 55, 38))
	slogan_label.add_theme_color_override("font_shadow_color", Color(1, 1, 1, 0.25))
	slogan_label.add_theme_constant_override("shadow_offset_x", 1)
	slogan_label.add_theme_constant_override("shadow_offset_y", 1)
	slogan_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	slogan_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(slogan_label)

func _draw_rect(image: Image, rect: Rect2i, color: Color) -> void:
	for y in range(rect.position.y, rect.position.y + rect.size.y):
		for x in range(rect.position.x, rect.position.x + rect.size.x):
			if x >= 0 and x < image.get_width() and y >= 0 and y < image.get_height():
				image.set_pixel(x, y, color)

func _draw_portrait(image: Image, rect: Rect2i) -> void:
	if portrait:
		var portrait_image := portrait.get_image()
		portrait_image.resize(rect.size.x, rect.size.y, Image.INTERPOLATE_LANCZOS)
		image.blit_rect(portrait_image, Rect2i(Vector2i.ZERO, rect.size), rect.position)
		return

	for y in range(rect.position.y, rect.position.y + rect.size.y):
		for x in range(rect.position.x, rect.position.x + rect.size.x):
			var u := float(x - rect.position.x) / rect.size.x
			var v := float(y - rect.position.y) / rect.size.y
			var color := Color(0.25 + u * 0.2, 0.18 + v * 0.18, 0.13 + (1.0 - v) * 0.1)
			image.set_pixel(x, y, color)

	_draw_circle(image, Vector2i(200, 165), 48, Color8(230, 190, 150))
	_draw_rect(image, Rect2i(150, 220, 100, 112), accent_color.darkened(0.2))
	_draw_rect(image, Rect2i(128, 255, 144, 70), Color8(45, 36, 35))

func _draw_name_plate(_image: Image) -> void:
	pass

func _draw_slogan_area(_image: Image) -> void:
	pass

func _draw_decorations(_image: Image) -> void:
	pass

func _draw_circle(image: Image, center: Vector2i, radius: int, color: Color) -> void:
	for y in range(-radius, radius + 1):
		for x in range(-radius, radius + 1):
			if x * x + y * y <= radius * radius:
				var px := center.x + x
				var py := center.y + y
				if px >= 0 and px < image.get_width() and py >= 0 and py < image.get_height():
					image.set_pixel(px, py, color)
