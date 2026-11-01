extends RefCounted
## Compact, read-only voyage and phase sign in the reference's top TURN footprint.

const Pixel = preload("res://card/pixel_card_theme.gd")
const FONT = Pixel.FONT
const BOUNDS = Rect2(604, 0, 236, 56)
const FACE = Color("543334")
const EDGE = Color("a05e4e")
const LOWER_EDGE = Color("86574b")
const SHADOW = Color("2f1d21")
const INK = Color("180e10")
const LETTERS = Color("faf9f9")
const MUTED = Color("e2c9bb")
const TEXT_WIDTH = 214.0


static func status(game, busy: bool, roll_phase: String, setup_step: String = "cargo") -> Dictionary:
	var detail := "装货" if setup_step == "cargo" else "起点 · 合计 9"
	# The model advances on dice commit, before the visual voyage is finished.
	if busy:
		var sail: int = game.sail_count + (1 if roll_phase == "rolling" else 0)
		var motion := "等待落定" if roll_phase == "rolling" else "船队前进"
		if roll_phase == "result":
			motion = "骰子已落定"
		detail = "航行 %d/3 · %s" % [sail, motion]
	elif game.phase == "auction":
		detail = "竞拍 · %s" % game.players[game.current_player].name
	elif game.phase == "stock":
		detail = "买股 · %s" % game.players[game.harbormaster].name
	elif game.phase == "setup":
		detail += " · %s" % game.players[game.harbormaster].name
	elif game.phase == "dispatch":
		detail = "派遣 %d/4 · %s" % [game.dispatch_round, game.players[game.current_player].name]
	elif game.phase == "sailing":
		detail = "投骰 %d/3 · %s" % [game.sail_count + 1, game.players[game.harbormaster].name]
	elif game.phase == "settlement":
		detail = "航行 3/3 · 收益结算"
	elif game.phase == "finished":
		detail = "航程结束 · 最终排名"
	return {"title": "TURN %d / %d" % [game.voyage, game.max_voyages], "detail": detail}


static func font_size(value: String, preferred: int) -> int:
	var size := preferred
	while size > 12 and FONT.get_string_size(value, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x > TEXT_WIDTH:
		size -= 1
	return size


static func _center(canvas: CanvasItem, value: String, baseline: float, preferred: int, color: Color) -> void:
	var size := font_size(value, preferred)
	var width := FONT.get_string_size(value, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	var at := Vector2(BOUNDS.get_center().x - width * 0.5, baseline)
	canvas.draw_string(FONT, at + Vector2(1, 1), value, HORIZONTAL_ALIGNMENT_LEFT, TEXT_WIDTH, size, INK)
	canvas.draw_string(FONT, at, value, HORIZONTAL_ALIGNMENT_LEFT, TEXT_WIDTH, size, color)


static func draw_board(canvas: CanvasItem, data: Dictionary) -> void:
	# Top edge meets the canvas; only the lower corners step inward like the source.
	canvas.draw_rect(Rect2(604, 0, 236, 45), INK)
	Pixel.step_rect(canvas, Rect2(604, 35, 236, 21), 6, SHADOW)
	canvas.draw_rect(Rect2(607, 0, 230, 43), EDGE)
	Pixel.step_rect(canvas, Rect2(607, 34, 230, 17), 5, LOWER_EDGE)
	canvas.draw_rect(Rect2(613, 0, 218, 44), INK)
	canvas.draw_rect(Rect2(615, 0, 214, 44), FACE)
	canvas.draw_line(Vector2(609, 1), Vector2(609, 42), Color("b27761"), 2)
	canvas.draw_line(Vector2(834, 1), Vector2(834, 43), Color("713e35"), 2)
	canvas.draw_line(Vector2(614, 47), Vector2(829, 47), Color("a66d5b"), 2)
	_center(canvas, data.title, 24, 23, LETTERS)
	_center(canvas, data.detail, 42, 14, MUTED)
