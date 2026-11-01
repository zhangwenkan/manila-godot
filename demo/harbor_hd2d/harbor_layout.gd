extends RefCounted


static func describe(view_size: Vector2) -> Dictionary:
	var factor := maxf(view_size.y / 900.0, 0.01)
	var width := maxf(1200.0, view_size.x / factor)
	var world_rect := Rect2(0, 40, width, 710)
	var hand_width := minf(620.0, width - 620.0)
	return {
		"factor": factor,
		"canvas_size": Vector2(width, 900),
		"world_rect": world_rect,
		"inspect_rect": Rect2(width - 302, 9, 190, 44),
		"overview_size": maxf(35.5, 63.5 * world_rect.size.y / width),
		"safe_board": Rect2(8, 76, width - 16, 572),
		"hand_rect": Rect2((width - hand_width) * 0.5, 650, hand_width, 250),
		"actor_rect": Rect2(16, 776, 280, 108),
		"action_rect": Rect2(width - 300, 758, 284, 126),
	}
