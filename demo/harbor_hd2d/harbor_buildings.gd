extends RefCounted

const INK := Color("30252c")
const TIMBER := Color("b49565")

var _box: Callable
var _quad: Callable
var _triangle: Callable


func _init(box: Callable, quad: Callable, triangle: Callable) -> void:
	_box = box
	_quad = quad
	_triangle = triangle


func build_warehouse(parent: Node3D, position: Vector3, footprint: Vector2, height: float, wall_tile: int, roof_tile: int) -> Node3D:
	var root := _group(parent, "Warehouse", position)
	var walls := _group(root, "Walls")
	var w := footprint.x
	var d := footprint.y
	var front := d * 0.5
	var thickness := 0.22
	var door_width := 2.25
	var door_height := 2.45
	var doors := [-w * 0.29, w * 0.04]
	_box.call(root, Vector3(0, 0.04, 0), Vector3(w + 0.24, 0.22, d + 0.24), INK, 5)
	_box.call(root, Vector3(0, 0.16, 0), Vector3(w - 0.20, 0.10, d - 0.18), Color.WHITE, 0)
	_box.call(walls, Vector3(0, height * 0.5, -front + thickness * 0.5), Vector3(w, height, thickness), Color.WHITE, wall_tile)
	for side in [-1, 1]:
		_box.call(walls, Vector3(side * (w * 0.5 - thickness * 0.5), height * 0.5, 0), Vector3(thickness, height, d), Color.WHITE, wall_tile)
	var start := -w * 0.5
	for x: float in doors:
		var left := x - door_width * 0.5
		_box.call(walls, Vector3((start + left) * 0.5, height * 0.5, front - thickness * 0.5), Vector3(left - start, height, thickness), Color.WHITE, wall_tile)
		_box.call(walls, Vector3(x, (height + door_height) * 0.5, front - thickness * 0.5), Vector3(door_width, height - door_height, thickness), Color.WHITE, wall_tile)
		start = x + door_width * 0.5
		_loading_door(root, x, front, door_width, door_height)
	_box.call(walls, Vector3((start + w * 0.5) * 0.5, height * 0.5, front - thickness * 0.5), Vector3(w * 0.5 - start, height, thickness), Color.WHITE, wall_tile)
	var framing := _group(root, "WallFraming")
	for x in [-w * 0.5 + 0.10, w * 0.5 - 0.10]:
		for z in [-front, front]:
			_box.call(framing, Vector3(x, height * 0.5, z), Vector3(0.20, height + 0.12, 0.25), TIMBER, 8)
		# Side-wall framing has real relief, rather than painted window rectangles.
		for z in [-d * 0.24, d * 0.24]:
			_box.call(framing, Vector3(x, height * 0.5, z), Vector3(0.25, height, 0.16), TIMBER, 8)
		for y in [0.40, height - 0.12]:
			_box.call(framing, Vector3(x, y, 0), Vector3(0.26, 0.18, d), TIMBER, 8)
		_side_vent(root, x, -d * 0.05, height * 0.68, signf(x))
	_box.call(framing, Vector3(0, height - 0.06, front + 0.04), Vector3(w, 0.24, 0.30), TIMBER, 8)
	var roof := _group(root, "Roof")
	var roof_frame := _group(root, "RoofFrame")
	var half_span := front + 0.42
	var half_length := w * 0.5 + 0.22
	var eave := height + 0.12
	var ridge := eave + 1.60
	for side in [-1, 1]:
		_solid_panel(roof, "Slope%d" % side, [Vector3(-half_length, eave, side * half_span), Vector3(half_length, eave, side * half_span), Vector3(half_length, ridge, 0), Vector3(-half_length, ridge, 0)], 0.20, roof_tile)
		_box.call(roof_frame, Vector3(0, eave - 0.04, side * half_span), Vector3(w + 0.44, 0.23, 0.18), TIMBER, 8)
	for x in [-w * 0.5, w * 0.5]:
		_solid_gable(roof_frame, x, front, height, ridge - 0.17, wall_tile)
		for side in [-1, 1]:
			_beam(roof_frame, Vector3(x, eave + 0.03, side * half_span), Vector3(x, ridge + 0.03, 0), 0.18, TIMBER, 0)
	_box.call(roof_frame, Vector3(0, ridge + 0.04, 0), Vector3(w + 0.44, 0.20, 0.26), TIMBER, 8)
	var canopy := _group(root, "LoadingCanopy")
	_solid_panel(canopy, "CanopySlab", [Vector3(-w * 0.5, height - 0.18, front), Vector3(w * 0.5, height - 0.18, front), Vector3(w * 0.5, height - 0.57, front + 0.82), Vector3(-w * 0.5, height - 0.57, front + 0.82)], 0.16, roof_tile)
	_box.call(canopy, Vector3(0, height - 0.57, front + 0.82), Vector3(w, 0.19, 0.17), TIMBER, 8)
	for x in [-w * 0.46, (doors[0] + doors[1]) * 0.5, w * 0.46]:
		_beam(canopy, Vector3(x, height - 1.12, front + 0.05), Vector3(x, height - 0.69, front + 0.70), 0.17, TIMBER, 0)
	return root


func _loading_door(parent: Node3D, x: float, front: float, width: float, height: float) -> void:
	var root := _group(parent, "LoadingDoor", Vector3(x, 0, front))
	for side in [-1, 1]:
		_box.call(root, Vector3(side * (width * 0.5 + 0.07), height * 0.5, 0.01), Vector3(0.18, height + 0.08, 0.38), TIMBER, 8)
		var leaf := _group(root, "OpenLeaf", Vector3(side * width * 0.5, 0.22, 0.08))
		leaf.rotation.y = -side * deg_to_rad(110)
		var leaf_w := width * 0.5 - 0.07
		var leaf_h := height - 0.25
		var center: float = -side * leaf_w * 0.5
		_box.call(leaf, Vector3(center, leaf_h * 0.5, 0), Vector3(leaf_w, leaf_h, 0.13), Color.WHITE, 8)
		for y in [0.18, leaf_h - 0.18]:
			_box.call(leaf, Vector3(center, y, 0.095), Vector3(leaf_w, 0.12, 0.08), TIMBER, 0)
		_beam(leaf, Vector3(center - leaf_w * 0.40, 0.20, 0.095), Vector3(center + leaf_w * 0.40, leaf_h - 0.20, 0.095), 0.10, TIMBER, 0)
		for y in [0.38, leaf_h - 0.38]:
			_box.call(leaf, Vector3(-side * 0.18, y, 0.13), Vector3(0.36, 0.09, 0.04), INK)
	_box.call(root, Vector3(0, height + 0.08, 0), Vector3(width + 0.34, 0.24, 0.40), TIMBER, 8)
	_box.call(root, Vector3(0, 0.18, 0.12), Vector3(width, 0.10, 0.48), Color("a69273"), 5)


func _side_vent(parent: Node3D, x: float, z: float, y: float, side: float) -> void:
	var root := _group(parent, "LouveredVent", Vector3(x + side * 0.04, y, z))
	_box.call(root, Vector3.ZERO, Vector3(0.12, 0.78, 0.92), INK, 8)
	for level in 5:
		var slat: MeshInstance3D = _box.call(root, Vector3(side * 0.10, -0.29 + level * 0.145, 0), Vector3(0.17, 0.065, 0.78), TIMBER, 0)
		slat.rotation.z = side * 0.35
	for dz in [-0.48, 0.48]:
		_box.call(root, Vector3(side * 0.10, 0, dz), Vector3(0.22, 0.88, 0.10), TIMBER, 8)


func build_shipyard(parent: Node3D, position: Vector3) -> Node3D:
	var root := _group(parent, "Shipyard", position)
	_box.call(root, Vector3(0, -0.22, 0), Vector3(13.0, 0.45, 9.0), Color.WHITE, 5)
	var frame := _group(root, "TimberFrame")
	for z in [-3.3, -1.1, 1.1, 3.3]:
		var truss := _group(frame, "Truss", Vector3(0, 0, z))
		for side in [-1, 1]:
			var x: float = side * 3.5
			_box.call(truss, Vector3(x, 0.16, 0), Vector3(0.62, 0.34, 0.60), Color("9c9279"), 5)
			_box.call(truss, Vector3(x, 2.00, 0), Vector3(0.36, 3.80, 0.38), TIMBER, 8)
			_box.call(truss, Vector3(x, 3.76, 0), Vector3(0.58, 0.26, 0.56), TIMBER, 0)
			_beam(truss, Vector3(x, 2.92, 0), Vector3(x - side * 0.76, 3.79, 0), 0.21, TIMBER, 0)
			_beam(truss, Vector3(side * 4.14, 3.77, 0), Vector3(0, 5.52, 0), 0.24, TIMBER, 0)
			_beam(truss, Vector3(side * 2.15, 3.83, 0), Vector3(side * 1.05, 5.06, 0), 0.15, TIMBER, 0)
		_box.call(truss, Vector3(0, 3.83, 0), Vector3(7.36, 0.27, 0.28), TIMBER, 8)
		_box.call(truss, Vector3(0, 4.66, 0), Vector3(0.18, 1.66, 0.22), TIMBER, 0)
	for side in [-1, 1]:
		_box.call(frame, Vector3(side * 3.5, 3.70, 0), Vector3(0.28, 0.32, 7.20), TIMBER, 8)
		for z in [-3.3, 3.3]:
			_beam(frame, Vector3(side * 3.5, 2.8, z), Vector3(side * 3.5, 3.60, z - signf(z) * 0.84), 0.20, TIMBER, 0)
	for x in [-3.5, -1.75, 0.0, 1.75, 3.5]:
		var y := 5.68 - absf(x) * 1.8 / 4.2
		_box.call(frame, Vector3(x, y, 0), Vector3(0.19, 0.19, 8.10), TIMBER, 0)
	var roof := _group(root, "Roof")
	for side in [-1, 1]:
		_solid_panel(roof, "Slope%d" % side, [Vector3(side * 4.2, 4.1, -4.1), Vector3(side * 4.2, 4.1, 4.1), Vector3(0, 5.9, 4.1), Vector3(0, 5.9, -4.1)], 0.20, 1)
		_box.call(roof, Vector3(side * 4.2, 4.04, 0), Vector3(0.17, 0.24, 8.24), TIMBER, 8)
		for z in [-4.1, 4.1]:
			_beam(roof, Vector3(side * 4.2, 4.12, z), Vector3(0, 5.92, z), 0.19, TIMBER, 8)
	_box.call(roof, Vector3(0, 5.94, 0), Vector3(0.25, 0.19, 8.28), TIMBER, 8)
	_build_repair_hull(root)
	return root


func _build_repair_hull(parent: Node3D) -> void:
	var cradle := _group(parent, "Cradle")
	for z in [-2.0, 0.0, 2.0]:
		_box.call(cradle, Vector3(0, 0.17, z), Vector3(4.3, 0.32, 0.44), TIMBER, 8)
		_box.call(cradle, Vector3(0, 0.43, z), Vector3(0.65, 0.25, 0.52), TIMBER, 0)
		for side in [-1, 1]:
			_beam(cradle, Vector3(side * 1.95, 0.25, z), Vector3(side * 1.13, 0.96, z), 0.24, TIMBER, 8)
	var hull := _group(parent, "RepairHull")
	var skin := _group(hull, "Shell")
	var ribs := _group(hull, "Ribs")
	var stations := [-3.15, -2.40, -1.40, -0.30, 0.80, 1.80, 2.70]
	var widths := [0.06, 0.88, 1.36, 1.58, 1.57, 1.44, 1.17]
	var outer_sections: Array = []
	var inner_sections: Array = []
	for i in stations.size():
		var w: float = widths[i]
		var z: float = stations[i]
		var sheer := 0.20 * pow(absf(z) / 3.15, 2)
		var outer := [Vector3(-w, 1.78 + sheer, z), Vector3(-w * 0.86, 1.06, z), Vector3(-w * 0.43, 0.67, z), Vector3(0, 0.56, z), Vector3(w * 0.43, 0.67, z), Vector3(w * 0.86, 1.06, z), Vector3(w, 1.78 + sheer, z)]
		var inner: Array = []
		for j in outer.size():
			var point: Vector3 = outer[j]
			point.x *= maxf(0.0, (w - 0.11) / w)
			if j > 0 and j < outer.size() - 1:
				point.y += 0.12
			inner.append(point)
		outer_sections.append(outer)
		inner_sections.append(inner)
		if i > 0 and i < stations.size() - 1:
			var rib := _group(ribs, "Rib%d" % i)
			for j in inner.size() - 1:
				_beam(rib, inner[j] + Vector3.UP * 0.035, inner[j + 1] + Vector3.UP * 0.035, 0.13, TIMBER, 0)
	for i in stations.size() - 1:
		var a: Array = outer_sections[i]
		var b: Array = outer_sections[i + 1]
		var ia: Array = inner_sections[i]
		var ib: Array = inner_sections[i + 1]
		for j in a.size() - 1:
			_quad.call(skin, [a[j], b[j], b[j + 1], a[j + 1]], Color.WHITE, 14)
			_quad.call(skin, [ia[j + 1], ib[j + 1], ib[j], ia[j]], Color("c2a073"), 0)
		for j in [0, a.size() - 1]:
			_quad.call(skin, [a[j], ia[j], ib[j], b[j]], TIMBER, 0)
			_beam(hull, a[j] + Vector3.UP * 0.035, b[j] + Vector3.UP * 0.035, 0.12, TIMBER, 8)
	for end in [0, stations.size() - 1]:
		# Close the bow/transom across their U-shaped cross-section, never across the open deck.
		var section: Array = outer_sections[end]
		var inside: Array = inner_sections[end]
		var center := Vector3(0, 1.30, section[0].z)
		var inward := Vector3(0, 0, 0.10 if end == 0 else -0.10)
		for j in section.size():
			var next := (j + 1) % section.size()
			_triangle.call(skin, [center, section[j], section[next]], Color.WHITE, 14)
			_triangle.call(skin, [center + inward, inside[next] + inward, inside[j] + inward], Color.WHITE, 0)
			_quad.call(skin, [section[j], inside[j] + inward, inside[next] + inward, section[next]], TIMBER, 0)
	_box.call(hull, Vector3(0, 0.67, -0.22), Vector3(0.16, 0.19, 5.80), TIMBER, 8)


func _solid_panel(parent: Node3D, name: String, outline: Array, thickness: float, tile: int) -> Node3D:
	var root := _group(parent, name)
	var top := outline.duplicate()
	var normal: Vector3 = (top[1] - top[0]).cross(top[2] - top[0]).normalized()
	if normal.y < 0:
		top.reverse()
		normal = -normal
	var bottom: Array = []
	for point: Vector3 in top:
		bottom.append(point - normal * thickness)
	_quad.call(root, top, Color.WHITE, tile)
	var underside := bottom.duplicate()
	underside.reverse()
	_quad.call(root, underside, Color("887252"), 8)
	for i in top.size():
		var next := (i + 1) % top.size()
		_quad.call(root, [top[i], bottom[i], bottom[next], top[next]], TIMBER, 0)
	return root


func _solid_gable(parent: Node3D, x: float, half_span: float, base: float, peak: float, tile: int) -> void:
	var points := [Vector3(x, base, -half_span), Vector3(x, base, half_span), Vector3(x, peak, 0)]
	var other: Array = []
	for point: Vector3 in points:
		other.append(point - Vector3(signf(x) * 0.18, 0, 0))
	_triangle.call(parent, points, Color.WHITE, tile)
	_triangle.call(parent, [other[2], other[1], other[0]], Color.WHITE, tile)
	for i in 3:
		var next := (i + 1) % 3
		_quad.call(parent, [points[i], other[i], other[next], points[next]], Color.WHITE, tile)


func _beam(parent: Node3D, a: Vector3, b: Vector3, width: float, color: Color, tile := -1) -> void:
	var direction := b - a
	var beam: MeshInstance3D = _box.call(parent, (a + b) * 0.5, Vector3(width, width, direction.length()), color, tile)
	# Endpoints are parent-local; global look_at_from_position would move nested members out of place.
	if direction.length_squared() > 0.000001:
		var up := Vector3.FORWARD if absf(direction.normalized().y) > 0.99 else Vector3.UP
		beam.basis = Basis.looking_at(direction, up)


func _group(parent: Node3D, name: String, position := Vector3.ZERO) -> Node3D:
	var root := Node3D.new()
	root.name = name
	root.position = position
	parent.add_child(root)
	return root
