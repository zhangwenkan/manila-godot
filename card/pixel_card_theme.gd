extends RefCounted

const FONT = preload("res://card/fonts/fusion-pixel-12px-proportional-zh_hans.otf")
const INK := Color("1b292b")
const PAPER := Color("e6ebe0")
const MUTED := Color("9cbbb6")
const GOLD := Color("efc578")
const TEAL := Color("498c84")

const ICONS := {
	"anchor": ["00111000", "01000100", "01111100", "00111000", "00111000", "00111000", "00111000", "01111110", "11000011", "11000011", "01111110"],
	"spear": ["00011000", "00111100", "01111110", "01111110", "00111100", "00011000", "00011000", "00011000", "00011000", "00011000", "00011000"],
	"gun": ["00000110", "00011111", "01111110", "11111100", "01111110", "00011111", "00000110"],
	"shuriken": ["10000001", "01100110", "00111100", "11111111", "11111111", "00111100", "01100110", "10000001"],
	"music": ["00000011", "00000011", "00000011", "00000011", "01100011", "11110011", "11110110", "01101100"],
	"scale": ["00010000", "00111000", "01010100", "10000010", "11111110", "00111000", "00010000"],
	"check": ["0000000011", "0000000110", "0000001100", "1100011000", "0110110000", "0011100000", "0001000000"],
	"close": ["110000011", "011000110", "001101100", "000111000", "000010000", "000111000", "001101100", "011000110", "110000011"],
	"arrow": ["000010000", "000011000", "000001100", "111111110", "111111111", "111111110", "000001100", "000011000", "000010000"],
	"diamond": ["0001000", "0011100", "0111110", "1111111", "0111110", "0011100", "0001000"],
	"helm": ["00011100000", "00100010000", "01000001000", "01111111000", "00101010000", "00101010000", "01111111000", "01000001000", "00100010000", "00011100000"],
	"sword": ["000000001", "000000011", "000000110", "000001100", "000011000", "000110000", "001100000", "011000000", "110000000", "010000000", "011111110"],
	"dice": ["0111110", "1100011", "1010101", "1010101", "1010101", "1100011", "0111110"],
	"eye": ["0001000", "0110110", "1100011", "1000001", "1100011", "0110110", "0001000"],
	"wind": ["110000000", "011111100", "000001110", "001111000", "111000000", "011111100", "000001110"],
	"trade": ["000110000", "001111000", "011011000", "110001100", "001100110", "000110111", "000011110", "000001100"],
}


static func step_rect(canvas: CanvasItem, rect: Rect2, corner: float, color: Color) -> void:
	canvas.draw_rect(Rect2(rect.position + Vector2(corner, 0), rect.size - Vector2(corner * 2, 0)), color)
	canvas.draw_rect(Rect2(rect.position + Vector2(corner * 0.5, corner * 0.5), rect.size - Vector2(corner, corner)), color)
	canvas.draw_rect(Rect2(rect.position + Vector2(0, corner), rect.size - Vector2(0, corner * 2)), color)


static func icon(canvas: CanvasItem, kind: String, origin: Vector2, pixel: int, color: Color) -> void:
	var rows: Array = ICONS.get(kind, ICONS["diamond"])
	for y in rows.size():
		for x in rows[y].length():
			if rows[y][x] == "1":
				canvas.draw_rect(Rect2(origin + Vector2(x, y) * pixel, Vector2.ONE * pixel), color)


static func label(parent: Node, value: String, rect: Rect2, font_size: int, color: Color) -> Label:
	var result := Label.new()
	result.text = value
	result.position = rect.position
	result.size = rect.size
	result.mouse_filter = Control.MOUSE_FILTER_IGNORE
	result.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	result.add_theme_font_override("font", FONT)
	result.add_theme_font_size_override("font_size", font_size)
	result.add_theme_color_override("font_color", color)
	result.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	parent.add_child(result)
	return result


static func clear_button_styles(button: Button) -> void:
	for state in ["normal", "hover", "pressed", "disabled", "focus", "hover_pressed"]:
		button.add_theme_stylebox_override(state, StyleBoxEmpty.new())
