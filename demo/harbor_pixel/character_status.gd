extends RefCounted
## Read-only human resources in the reference's portrait and two compact plaques.

const Pixel = preload("res://card/pixel_card_theme.gd")
const FONT = Pixel.FONT
const PORTRAIT = preload("res://demo/harbor_pixel/art/captain.png")
const CHARACTERS = {
	"Carmen": {"name": "卡门", "portrait": preload("res://card/image/carmen_avatar.png")},
	"Li Yunlong": {"name": "李云龙", "portrait": preload("res://card/image/liyunlong_avatar.png")},
	"Lakan Bautista": {"name": "拉坎·巴蒂斯塔", "portrait": preload("res://card/image/lanka_avatar.png")},
	"Izefia": {"name": "伊泽菲亚", "portrait": preload("res://card/image/izefia_avatar.png")},
	"Kage": {"name": "影", "portrait": preload("res://card/image/kage_avatar.png")},
	"Jack": {"name": "杰克", "portrait": preload("res://card/image/jack_avatar.png")},
}
const BOUNDS = Rect2(11, 10, 261, 104)
const PORTRAIT_FRAME = Rect2(11, 10, 104, 104)
const CASH_PLAQUE = Rect2(105, 17, 167, 48)
const CREW_PLAQUE = Rect2(105, 61, 104, 47)
const CASH_TEXT = Rect2(169, 27, 91, 28)
const CREW_TEXT = Rect2(169, 72, 29, 28)
const INK = Color("130e10")
const FACE = Color("4a3233")
const EDGE = Color("7f534e")
const LOWER_EDGE = Color("744b46")
const FRAME = Color("c4a593")
const FRAME_SHADE = Color("9b7b63")
const LETTERS = Color("faf9f9")
const GOLD = Color("e3b963")


static func status(game, character_id: String = "Carmen") -> Dictionary:
	# Current actor belongs to TURN; portrait and resources always belong to you.
	var character: Dictionary = CHARACTERS.get(character_id, CHARACTERS.Carmen)
	return {"cash": str(game.players[0].cash), "crew": str(game.players[0].crew),
		"portrait": character.portrait, "name": character.name, "harbormaster": game.harbormaster == 0}


static func font_size(value: String, width: float) -> int:
	var size := 27
	while size > 12 and FONT.get_string_size(value, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x > width:
		size -= 1
	return size


static func _value(canvas: CanvasItem, value: String, rect: Rect2) -> void:
	var size := font_size(value, rect.size.x)
	var at := Vector2(rect.position.x, rect.get_center().y + (FONT.get_ascent(size) - FONT.get_descent(size)) * 0.5)
	canvas.draw_string(FONT, at + Vector2(1, 1), value, HORIZONTAL_ALIGNMENT_LEFT, rect.size.x, size, INK)
	canvas.draw_string(FONT, at, value, HORIZONTAL_ALIGNMENT_LEFT, rect.size.x, size, LETTERS)


static func _plaque(canvas: CanvasItem, rect: Rect2) -> void:
	Pixel.step_rect(canvas, rect, 6, INK)
	Pixel.step_rect(canvas, rect.grow(-3), 4, LOWER_EDGE)
	canvas.draw_rect(Rect2(rect.position + Vector2(5, 3), Vector2(rect.size.x - 11, 3)), EDGE)
	Pixel.step_rect(canvas, rect.grow(-7), 2, FACE)


static func draw_board(canvas: CanvasItem, data: Dictionary) -> void:
	_plaque(canvas, CASH_PLAQUE)
	_plaque(canvas, CREW_PLAQUE)
	# An opaque inset removes the baked portrait even where the live avatar is alpha.
	Pixel.step_rect(canvas, PORTRAIT_FRAME, 8, INK)
	Pixel.step_rect(canvas, Rect2(14, 12, 98, 98), 7, FRAME_SHADE)
	Pixel.step_rect(canvas, Rect2(14, 12, 98, 92), 7, FRAME)
	Pixel.step_rect(canvas, Rect2(20, 18, 86, 86), 3, INK)
	canvas.draw_rect(Rect2(23, 21, 80, 80), Color("397690"))
	var portrait: Texture2D = data.get("portrait", PORTRAIT)
	var texture_size := Vector2(portrait.get_size())
	canvas.draw_texture_rect_region(portrait, Rect2(23, 21, 80, 80), Rect2(texture_size * Vector2(0.11, 0.12), texture_size * Vector2(0.78, 0.58)))
	if data.get("harbormaster", false):
		Pixel.icon(canvas, "helm", Vector2(77, 77), 3, GOLD)
	canvas.draw_line(Vector2(23, 15), Vector2(101, 15), Color("d4b7a4"), 2)
	canvas.draw_line(Vector2(24, 107), Vector2(101, 107), Color("ac896c"), 2)
	Pixel.icon(canvas, "coin", Vector2(134, 28), 3, Color("493522"))
	Pixel.icon(canvas, "coin", Vector2(132, 26), 3, GOLD)
	Pixel.icon(canvas, "crew", Vector2(137, 72), 3, Color("493522"))
	Pixel.icon(canvas, "crew", Vector2(135, 70), 3, GOLD)
	_value(canvas, data.cash, CASH_TEXT)
	_value(canvas, data.crew, CREW_TEXT)
