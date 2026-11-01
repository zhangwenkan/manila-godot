extends RefCounted
## Shipyard rotating light trails and contextual scene previews; no placement rules.

const Pixel = preload("res://card/pixel_card_theme.gd")
const GLYPHS = {
	"$": ["011", "110", "011", "110", "010"],
	"0": ["111", "101", "101", "101", "111"],
	"1": ["010", "110", "010", "010", "111"],
	"2": ["111", "001", "111", "100", "111"],
	"3": ["111", "001", "111", "001", "111"],
	"4": ["101", "101", "111", "001", "001"],
	"5": ["111", "100", "111", "001", "111"],
}
const INK = Color("263c3c")
const MUTED = Color("a7a394")
const LIGHT = Color("fff0c6")
const WARM = Color("efc578")
const RING_GOLD = Color("d3a860")
const RING_LIGHT = Color("fff3ce")
const SWIRL_SECONDS = 3.6
const SWIRL_TRAIL = 1.78


static func ring_bounds(feet: Vector2) -> Rect2:
	return Rect2(feet + Vector2(-28, -17), Vector2(56, 40))


static func price_bounds(head: Vector2) -> Rect2:
	return Rect2(head + Vector2(-15, -30), Vector2(30, 22))


static func swirl_phase(time: float) -> float:
	return fposmod(time, SWIRL_SECONDS) / SWIRL_SECONDS * TAU


static func swirl_pixel(point: Vector2, phase: float, active: bool) -> Color:
	var local := Vector2(point.x / 25.0, point.y / 17.0)
	var radius := local.length()
	if radius < 0.50 or radius > 1.10:
		return Color.TRANSPARENT
	var angle := local.angle()
	var result := Color.TRANSPARENT
	for arm in 3:
		var behind := fposmod(phase + arm * TAU / 3.0 - angle, TAU)
		if behind > SWIRL_TRAIL:
			continue
		var tail := behind / SWIRL_TRAIL
		# Outer tails curl toward the brighter inner heads, leaving the center open.
		var spine := lerpf(0.67, 0.97, tail)
		var distance := absf(radius - spine)
		var width := lerpf(0.17, 0.065, tail)
		var glow := maxf(0.0, 1.0 - distance / (width + 0.10))
		var core := clampf((width - distance) / 0.055, 0.0, 1.0)
		var fade := pow(1.0 - tail, 0.58)
		var alpha := (core * 0.95 + glow * 0.25) * fade
		alpha *= [1.0, 0.92, 0.84][arm]
		alpha *= 0.92 if point.y < -2.0 else 1.0
		alpha = minf(1.0, alpha * (1.28 if active else 1.0))
		if alpha > result.a:
			result = RING_GOLD.lerp(RING_LIGHT, core)
			result.a = alpha
	return result


static func _draw_placement_ring(canvas: CanvasItem, data: Dictionary) -> void:
	if not data.ring_visible:
		return
	var center: Vector2 = data.feet + Vector2(0, 3)
	var ground_scale: Vector2 = data.get("ring_scale", Vector2.ONE)
	# Rasterize at scene-pixel centers; rotation never changes the input footprint.
	for y in range(-20, 20):
		for x in range(-28, 28):
			var color := swirl_pixel(Vector2(x + 0.5, y + 0.5) / ground_scale, data.ring_phase, data.active)
			if color.a > 0.005:
				canvas.draw_rect(Rect2(center + Vector2(x, y), Vector2.ONE), color)


static func site_shape(id: String, point: Vector2, compact: bool) -> PackedVector2Array:
	# Separate scene silhouettes, never the rectangular input targets.
	if id == "pilot_1":
		return PackedVector2Array([Vector2(514, 470), Vector2(528, 470), Vector2(528, 476), Vector2(536, 476),
			Vector2(536, 486), Vector2(543, 486), Vector2(543, 497), Vector2(537, 497),
			Vector2(537, 600), Vector2(545, 600), Vector2(545, 617), Vector2(501, 617),
			Vector2(501, 600), Vector2(507, 600), Vector2(507, 497), Vector2(499, 497),
			Vector2(499, 486), Vector2(506, 486), Vector2(506, 476), Vector2(514, 476)])
	if id == "pilot_0":
		return PackedVector2Array([Vector2(915, 580), Vector2(929, 580), Vector2(929, 586), Vector2(937, 586),
			Vector2(937, 595), Vector2(943, 595), Vector2(943, 606), Vector2(935, 606),
			Vector2(935, 674), Vector2(942, 674), Vector2(942, 690), Vector2(904, 690),
			Vector2(904, 674), Vector2(910, 674), Vector2(910, 606), Vector2(902, 606),
			Vector2(902, 595), Vector2(908, 595), Vector2(908, 586), Vector2(915, 586)])
	var offsets := [Vector2(-19, 5), Vector2(-13, 1), Vector2(17, 1), Vector2(21, 5), Vector2(15, 14), Vector2(-21, 14)]
	if compact:
		offsets = [Vector2(-9, -8), Vector2(7, -8), Vector2(9, -6), Vector2(9, 8), Vector2(-9, 8)]
	var shape := PackedVector2Array()
	for offset in offsets:
		shape.append(point + offset)
	return shape


static func _price(canvas: CanvasItem, value: String, origin: Vector2, pixel: int, color: Color, shadow: int = 1) -> void:
	for i in value.length():
		var rows: Array = GLYPHS[value[i]]
		for y in rows.size():
			for x in rows[y].length():
				if rows[y][x] == "1":
					var at := origin + Vector2(i * 4 + x, y) * pixel
					canvas.draw_rect(Rect2(at + Vector2.ONE * shadow, Vector2.ONE * pixel), INK)
					canvas.draw_rect(Rect2(at, Vector2.ONE * pixel), color)


static func draw_marker(canvas: CanvasItem, data: Dictionary) -> void:
	var shape: PackedVector2Array = data.shape
	var shipyard: bool = data.shipyard
	if shipyard:
		_draw_placement_ring(canvas, data)
	if not shipyard and (data.available or data.active):
		# Translucent light preserves the underlying roof, stone and plank texture.
		var strength := 0.12 if data.active else 0.045
		canvas.draw_colored_polygon(shape, Color(WARM, strength))
	if not shipyard and data.active:
		var edge := shape.duplicate()
		edge.append(shape[0])
		canvas.draw_polyline(edge, Color(WARM if data.available else MUTED, 0.65), 1.0, false)
	if data.occupied or data.preview:
		var alpha := 1.0 if data.occupied else 0.48
		if shipyard:
			# Workers are baked into the scene; never draw a second pawn over them.
			if data.occupied:
				canvas.draw_rect(Rect2(data.feet + Vector2(-6, 4), Vector2(12, 4)), INK)
				canvas.draw_rect(Rect2(data.feet + Vector2(-5, 5), Vector2(10, 2)), data.color)
		else:
			var pixel: int = 1 if data.compact else 3
			var origin: Vector2 = data.pawn.position
			Pixel.icon(canvas, "crew", origin + Vector2.ONE, pixel, Color(INK, alpha * 0.7))
			Pixel.icon(canvas, "crew", origin, pixel, Color(data.color, alpha))
	if data.show_price:
		_price(canvas, data.label, data.price.position, 4 if shipyard else (2 if data.compact else 3), LIGHT if data.available else MUTED, 2 if shipyard else 1)
