extends RefCounted

const Pixel = preload("res://card/pixel_card_theme.gd")
const WOOD_DARK = Color("443b30")
const WOOD = Color("8c704d")
const BRASS = Color("bc9a68")
const PAPER = Color("e1cda6")
const PAPER_LIGHT = Color("f0dfba")
const INK = Color("544332")
const MUTED = Color("7f6d52")
const SHADOW = Color(0.12, 0.09, 0.06, 0.45)


static func plaque(canvas: CanvasItem, rect: Rect2) -> void:
	Pixel.step_rect(canvas, Rect2(rect.position + Vector2(0, 4), rect.size), 6, SHADOW)
	Pixel.step_rect(canvas, rect, 6, WOOD_DARK)
	Pixel.step_rect(canvas, rect.grow(-2), 4, WOOD)
	Pixel.step_rect(canvas, rect.grow(-5), 2, PAPER)
	canvas.draw_rect(Rect2(rect.position + Vector2(9, 5), Vector2(rect.size.x - 18, 2)), PAPER_LIGHT)
	canvas.draw_rect(Rect2(rect.position + Vector2(9, rect.size.y - 8), Vector2(rect.size.x - 18, 3)), BRASS)
	for x in [rect.position.x + 7, rect.end.x - 10]:
		for y in [rect.position.y + 7, rect.end.y - 10]:
			canvas.draw_rect(Rect2(x, y, 3, 3), BRASS)


static func button(canvas: CanvasItem, rect: Rect2, active: bool, primary: bool, hover: bool) -> void:
	var fill = Color("c2a16a") if primary else Color("d4c09a")
	if not active:
		fill = Color("b9ad96")
	elif hover:
		fill = fill.lightened(0.12)
	Pixel.step_rect(canvas, Rect2(rect.position + Vector2(0, 3), rect.size), 4, SHADOW)
	Pixel.step_rect(canvas, rect, 4, WOOD_DARK if primary and active else WOOD)
	Pixel.step_rect(canvas, rect.grow(-2), 2, fill)
	canvas.draw_rect(Rect2(rect.position + Vector2(5, 3), Vector2(rect.size.x - 10, 2)), PAPER_LIGHT if active else PAPER)
