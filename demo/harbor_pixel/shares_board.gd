extends RefCounted
## Public prices move four reference-textured discs; the original sign stays visible.

const PATCH = preload("res://demo/harbor_pixel/art/shares_patch.png")
const DISCS = preload("res://demo/harbor_pixel/art/shares_discs.png")
const BOUNDS = Rect2(1008, 646, 232, 244)
const COLUMNS = {"nutmeg": 0, "silk": 1, "ginseng": 2, "jade": 3}
const COLORS = [Color("cd3035"), Color("2f7fdc"), Color("f7af19"), Color("2cba3e")]
# Place the five demo values on existing bands, bottom to top. Preserve the
# extra reference band between 10 and 20 without inventing another model value.
const VALUE_ROWS = {0: 5, 5: 4, 10: 3, 20: 1, 30: 0}
const COLUMN_WIDTH = 41.0
const ROW_LEFTS = [1037.0, 1039.0, 1041.0, 1043.0, 1045.0, 1048.0]
const ROW_Y = [715.0, 745.0, 773.0, 800.0, 828.0, 852.0]
const DISC_SIZE = Vector2(25, 24)
const TILE_SIZE = Vector2(43, 41)


static func marker(cargo_id: String, prices: Dictionary) -> Dictionary:
	var column: int = COLUMNS[cargo_id]
	var value: int = prices[cargo_id]
	var row: int = VALUE_ROWS[value]
	var center := Vector2(ROW_LEFTS[row] + (column + 0.5) * COLUMN_WIDTH, ROW_Y[row])
	return {"value": value, "color": COLORS[column], "center": center,
		"rect": Rect2(center - DISC_SIZE * 0.5, DISC_SIZE), "column": column}


static func draw_board(canvas: CanvasItem, prices: Dictionary) -> void:
	# Equal-width reference-textured columns; no new frame, labels or cargo icons.
	canvas.draw_texture_rect(PATCH, BOUNDS, false)
	for cargo_id in COLUMNS:
		var disc := marker(cargo_id, prices)
		canvas.draw_texture_rect_region(DISCS, disc.rect,
			Rect2(Vector2(disc.column * TILE_SIZE.x, 0), TILE_SIZE))
