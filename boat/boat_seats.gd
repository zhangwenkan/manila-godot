extends Node2D

const Pixel := preload("res://card/pixel_card_theme.gd")
const CharacterCard := preload("res://card/character_card.gd")
const State := preload("res://ui/placement_state.gd")
const LAKAN := preload("res://worker/worker_lakan.png")
const LAKAN_REGION := Rect2(639, 114, 757, 1818)

var state: State
var ship_index := 0


func bind_state(value: State, index: int) -> void:
	if state != null:
		state.changed.disconnect(queue_redraw)
	state = value
	ship_index = index
	state.changed.connect(queue_redraw)
	z_index = 1
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	queue_redraw()


func _draw() -> void:
	if state == null:
		return
	var occupants := state.ship_occupants(ship_index)
	var spacing := 80.0 if occupants.size() == 4 else 90.0
	for i in occupants.size():
		var card: CharacterCard = occupants[i]
		if card == null:
			continue
		var center := 132.0 + (i - (occupants.size() - 1) * 0.5) * spacing
		if card.character_name_en == "Lakan Bautista":
			draw_texture_rect_region(LAKAN, Rect2(center - 33, -22, 66, 158.5), LAKAN_REGION)
		else:
			Pixel.icon(self, "crew", Vector2(center - 28, 6), 8, Pixel.INK)
			Pixel.icon(self, "crew", Vector2(center - 21, 10), 6, card.accent_color)
		Pixel.step_rect(self, Rect2(center - 17, -42, 34, 30), 4, Pixel.INK)
		draw_string(Pixel.FONT, Vector2(center - 8, -18), str(card.roster_number), HORIZONTAL_ALIGNMENT_LEFT, -1, 24, card.accent_color)
