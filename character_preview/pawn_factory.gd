extends RefCounted
## Seated bench characters and standing display sculpts. +Z is the front direction.
## Geometry is cached by character and presentation; instances never share overrides.

enum Presentation { CHOICE, DISPLAY }

const PAWN_SHADER: Shader = preload("res://character_preview/pawn.gdshader")
const NAMES: Array[String] = ["Carmen", "LiYunlong", "LakanBautista", "Izefia", "Kage", "Jack"]
const BRASS: Color = Color("#d8ac59")
const IVORY: Color = Color("#f5dfb4")
const INK: Color = Color("#343039")
static var _meshes: Dictionary[int, ArrayMesh] = {}
static var _paint: Dictionary[int, ShaderMaterial] = {}
static var _detail_paint: Dictionary[int, ShaderMaterial] = {}


class Sculpt:
	extends RefCounted
	var vertices: Array[PackedVector3Array] = [PackedVector3Array(), PackedVector3Array()]
	var normals: Array[PackedVector3Array] = [PackedVector3Array(), PackedVector3Array()]
	var colors: Array[PackedColorArray] = [PackedColorArray(), PackedColorArray()]
	var indices: Array[PackedInt32Array] = [PackedInt32Array(), PackedInt32Array()]
	var component_count: int = 0

	func add_mesh(source: Mesh, pose: Transform3D, color: Color, layer: int) -> void:
		var arrays: Array = source.surface_get_arrays(0)
		var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var ns: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
		var ids: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		var base: int = vertices[layer].size()
		var normal_basis: Basis = pose.basis.inverse().transposed()
		var linear: Color = color.srgb_to_linear()
		for i: int in range(points.size()):
			vertices[layer].append(pose * points[i])
			normals[layer].append((normal_basis * ns[i]).normalized())
			colors[layer].append(linear)
		for id: int in ids:
			indices[layer].append(base + id)
		component_count += 1

	func finish() -> ArrayMesh:
		var result: ArrayMesh = ArrayMesh.new()
		for layer: int in range(2):
			var arrays: Array = []
			arrays.resize(Mesh.ARRAY_MAX)
			arrays[Mesh.ARRAY_VERTEX] = vertices[layer]
			arrays[Mesh.ARRAY_NORMAL] = normals[layer]
			arrays[Mesh.ARRAY_COLOR] = colors[layer]
			arrays[Mesh.ARRAY_INDEX] = indices[layer]
			result.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		result.set_meta("sculpted_components", component_count)
		return result


static func build(index: int, presentation: Presentation = Presentation.DISPLAY) -> Node3D:
	var id: int = clampi(index, 0, 5)
	var key := id * 2 + presentation
	if not _meshes.has(key):
		_make_character(id, presentation)
	var root: Node3D = Node3D.new()
	root.name = NAMES[id]
	root.set_meta("character_index", id)
	root.set_meta("presentation", presentation)
	root.set_meta("front_direction", Vector3.BACK)
	var model: MeshInstance3D = MeshInstance3D.new()
	model.name = "SeatedFigure" if presentation == Presentation.CHOICE else "DisplayFigure"
	model.mesh = _meshes[key]
	if presentation == Presentation.CHOICE:
		# The origin is the hip/seat contact, not the bottom of the shoes.
		root.set_meta("seat_contact", Vector3.ZERO)
		root.set_meta("pose", "seated")
	else:
		model.position.y = -model.mesh.get_aabb().position.y
	root.add_child(model)
	return root


static func _make_character(id: int, presentation: Presentation) -> void:
	var s: Sculpt = Sculpt.new()
	if presentation == Presentation.CHOICE:
		_choice_character(s, id)
	else:
		match id:
			0: _carmen(s)
			1: _li_yunlong(s)
			2: _lakan(s)
			3: _izefia(s)
			4: _kage(s)
			5: _jack(s)
	var key := id * 2 + presentation
	var mesh: ArrayMesh = s.finish()
	var outline: StandardMaterial3D = StandardMaterial3D.new()
	outline.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	outline.albedo_color = Color("#3d3036")
	outline.cull_mode = BaseMaterial3D.CULL_FRONT
	outline.grow = true
	outline.grow_amount = 0.008
	var paint: ShaderMaterial = ShaderMaterial.new()
	paint.shader = PAWN_SHADER
	paint.set_shader_parameter("matte", presentation == Presentation.CHOICE)
	if presentation == Presentation.DISPLAY:
		paint.next_pass = outline
	var detail: ShaderMaterial = ShaderMaterial.new()
	detail.shader = PAWN_SHADER
	detail.set_shader_parameter("matte", presentation == Presentation.CHOICE)
	mesh.surface_set_material(0, paint)
	mesh.surface_set_material(1, detail)
	_paint[key] = paint
	_detail_paint[key] = detail
	_meshes[key] = mesh


# Elliptical lathe profiles use (height, radius_x, radius_z). The small rim
# transitions form actual bevels; they are not stacked boxes/cylinders.
static func _loft(s: Sculpt, center: Vector3, profile: Array[Vector3], color: Color,
		layer: int = 0, sides: int = 10, rotation: Vector3 = Vector3.ZERO) -> void:
	var v: PackedVector3Array = PackedVector3Array()
	var n: PackedVector3Array = PackedVector3Array()
	var ix: PackedInt32Array = PackedInt32Array()
	for ring: int in range(profile.size()):
		var p: Vector3 = profile[ring]
		var before: Vector3 = profile[maxi(0, ring - 1)]
		var after: Vector3 = profile[mini(profile.size() - 1, ring + 1)]
		var dy: float = maxf(after.x - before.x, 0.0001)
		for j: int in range(sides):
			var a: float = TAU * float(j) / float(sides)
			var ca: float = cos(a)
			var sa: float = sin(a)
			v.append(Vector3(ca * p.y, p.x, sa * p.z))
			var slope: float = -((after.y - before.y) * ca * ca / maxf(p.y, 0.001)
				+ (after.z - before.z) * sa * sa / maxf(p.z, 0.001)) / dy
			n.append(Vector3(ca / maxf(p.y, 0.001), slope, sa / maxf(p.z, 0.001)).normalized())
			if ring < profile.size() - 1:
				var a0: int = ring * sides + j
				var a1: int = ring * sides + (j + 1) % sides
				ix.append_array(PackedInt32Array([a0, a1, a0 + sides, a1, a1 + sides, a0 + sides]))
	# Separate cap vertices preserve a clean normal at the top/bottom plane.
	for cap: int in range(2):
		var p: Vector3 = profile[0 if cap == 0 else profile.size() - 1]
		var normal: Vector3 = Vector3.DOWN if cap == 0 else Vector3.UP
		var start: int = v.size()
		v.append(Vector3(0.0, p.x, 0.0))
		n.append(normal)
		for j: int in range(sides):
			var a: float = TAU * float(j) / float(sides)
			v.append(Vector3(cos(a) * p.y, p.x, sin(a) * p.z))
			n.append(normal)
		for j: int in range(sides):
			var a0: int = start + 1 + j
			var a1: int = start + 1 + (j + 1) % sides
			if cap == 0:
				ix.append_array(PackedInt32Array([start, a1, a0]))
			else:
				ix.append_array(PackedInt32Array([start, a0, a1]))
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = v
	arrays[Mesh.ARRAY_NORMAL] = n
	arrays[Mesh.ARRAY_INDEX] = ix
	var mesh: ArrayMesh = ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	s.add_mesh(mesh, Transform3D(Basis.from_euler(rotation), center), color, layer)


static func _ellipsoid(s: Sculpt, center: Vector3, radii: Vector3, color: Color,
		layer: int = 0, rotation: Vector3 = Vector3.ZERO) -> void:
	var sphere: SphereMesh = SphereMesh.new()
	sphere.radius = 1.0
	sphere.height = 2.0
	sphere.radial_segments = 10
	sphere.rings = 4
	var basis: Basis = Basis.from_euler(rotation).scaled_local(radii)
	s.add_mesh(sphere, Transform3D(basis, center), color, layer)


static func _link(s: Sculpt, a: Vector3, b: Vector3, r0: float, r1: float,
		color: Color, layer: int = 0, depth: float = 1.0) -> void:
	var length: float = a.distance_to(b)
	var rotation: Vector3 = Basis(Quaternion(Vector3.UP, (b - a).normalized())).get_euler()
	_loft(s, a, [Vector3(0.0, r0 * 0.76, r0 * depth * 0.76),
		Vector3(length * 0.14, r0, r0 * depth),
		Vector3(length * 0.82, r1, r1 * depth),
		Vector3(length, r1 * 0.72, r1 * depth * 0.72)], color, layer, 8, rotation)


# A solid bevel-edged polygon in the XY plane, optionally bent in depth.
# Front and back use fan triangulation around the centroid; every supplied
# polygon is convex. Edge normals are smoothed across bevels, not face seams.
static func _badge(s: Sculpt, points: Array[Vector3], thickness: float, color: Color,
		layer: int = 1) -> void:
	var ordered: Array[Vector3] = points.duplicate()
	var signed_area: float = 0.0
	for j: int in range(ordered.size()):
		var a: Vector3 = ordered[j]
		var b: Vector3 = ordered[(j + 1) % ordered.size()]
		signed_area += a.x * b.y - b.x * a.y
	if signed_area > 0.0:
		ordered.reverse()
	points = ordered
	var center: Vector3 = Vector3.ZERO
	for p: Vector3 in points:
		center += p
	center /= float(points.size())
	var v: PackedVector3Array = PackedVector3Array()
	var n: PackedVector3Array = PackedVector3Array()
	var ix: PackedInt32Array = PackedInt32Array()
	# Polygon points are clockwise when viewed from +Z.
	for face: int in range(2):
		var z: float = thickness * (0.5 if face == 0 else -0.5)
		var normal: Vector3 = Vector3.BACK if face == 0 else Vector3.FORWARD
		var offset: int = v.size()
		v.append(center + Vector3(0.0, 0.0, z))
		n.append(normal)
		for p: Vector3 in points:
			v.append(p + Vector3(0.0, 0.0, z))
			n.append(normal)
		for j: int in range(points.size()):
			var a: int = offset + 1 + j
			var b: int = offset + 1 + (j + 1) % points.size()
			ix.append_array(PackedInt32Array([offset, a, b] if face == 0 else [offset, b, a]))
	for j: int in range(points.size()):
		var p: Vector3 = points[j]
		var q: Vector3 = points[(j + 1) % points.size()]
		var normal: Vector3 = Vector3(-(q - p).y, (q - p).x, 0.0).normalized()
		var offset: int = v.size()
		v.append_array(PackedVector3Array([p + Vector3(0, 0, thickness * 0.5),
			p - Vector3(0, 0, thickness * 0.5), q - Vector3(0, 0, thickness * 0.5),
			q + Vector3(0, 0, thickness * 0.5)]))
		for k: int in range(4):
			n.append(normal)
		ix.append_array(PackedInt32Array([offset, offset + 1, offset + 2, offset, offset + 2, offset + 3]))
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = v
	arrays[Mesh.ARRAY_NORMAL] = n
	arrays[Mesh.ARRAY_INDEX] = ix
	var mesh: ArrayMesh = ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	s.add_mesh(mesh, Transform3D.IDENTITY, color, layer)


static func _choice_character(s: Sculpt, id: int) -> void:
	if id == 0:
		_choice_carmen(s)
		return
	var coats: Array[Color] = [Color("ad5357"), Color("7593a6"), Color("d2a361"), Color("80c5ae"), Color("626477"), Color("be8954")]
	var skins: Array[Color] = [Color("dca06f"), Color("edbc98"), Color("c9916a"), Color("98684e"), Color("dfb392"), Color("e5b087")]
	var coat := coats[id]
	var skin := skins[id]
	var hair := Color("303039") if id != 5 else Color("694731")
	var trousers := coat.darkened(0.28) if id in [1, 4] else Color("4b5362")
	# Rounded hips rest at y=0; thighs run forward before the shins drop.
	_round(s, Vector3(0, 0.22, 0.03), Vector3(0.43, 0.22, 0.34), coat)
	_round(s, Vector3(0, 0.59, -0.015), Vector3(0.42, 0.51, 0.32), coat)
	for side: float in [-1.0, 1.0]:
		var knee := Vector3(side * 0.25, 0.12, 0.59)
		var ankle := Vector3(side * 0.28, -0.43, 0.66)
		_soft_link(s, Vector3(side * 0.22, 0.20, 0.02), knee, 0.205, trousers)
		_soft_link(s, knee, ankle, 0.155, trousers)
		_round(s, Vector3(side * 0.28, -0.53, 0.78), Vector3(0.21, 0.16, 0.32), Color("383941"))
		_round(s, Vector3(side * 0.28, -0.64, 0.79), Vector3(0.205, 0.045, 0.30), Color("c8bdac"), 1)
		var elbow := Vector3(side * 0.49, 0.53, 0.19)
		_soft_link(s, Vector3(side * 0.34, 0.87, 0), elbow, 0.18, coat)
		_soft_link(s, elbow, Vector3(side * 0.36, 0.32, 0.47), 0.145, coat)
		_round(s, Vector3(side * 0.34, 0.30, 0.51), Vector3(0.145, 0.105, 0.16), skin, 1)
	_round(s, Vector3(0, 1.08, 0.01), Vector3(0.19, 0.22, 0.18), skin)
	_round(s, Vector3(0, 1.73, -0.08), Vector3(0.62, 0.65, 0.46), hair)
	_round(s, Vector3(0, 1.66, 0.11), Vector3(0.57, 0.60, 0.49), skin)
	for side: float in [-1.0, 1.0]:
		_round(s, Vector3(side * 0.56, 1.63, 0.08), Vector3(0.115, 0.17, 0.13), skin)
		_round(s, Vector3(side * 0.19, 1.80, 0.559), Vector3(0.043, 0.064, 0.023), INK, 1)
		_round(s, Vector3(side * 0.19 - 0.010, 1.821, 0.581), Vector3(0.010, 0.015, 0.006), IVORY, 1)
		_soft_link(s, Vector3(side * 0.12, 1.946, 0.522), Vector3(side * 0.27, 1.930, 0.490), 0.022, hair, 1)
	_round(s, Vector3(0, 1.65, 0.592), Vector3(0.083, 0.082, 0.089), skin.lightened(0.05), 1)
	# The smile follows the cheek surface instead of disappearing into the sphere.
	for segment in 10:
		var ends: Array[Vector3] = []
		for step in [segment, segment + 1]:
			var x := lerpf(-0.19, 0.19, step / 10.0)
			var y := 1.405 + 0.085 * pow(x / 0.19, 2)
			var z := 0.11 + 0.49 * sqrt(1.0 - pow(x / 0.57, 2) - pow((y - 1.66) / 0.60, 2))
			ends.append(Vector3(x, y, z + 0.022))
		_soft_link(s, ends[0], ends[1], 0.020, Color("754437"), 1)
	match id:
		1:
			_round(s, Vector3(0, 2.12, -0.045), Vector3(0.64, 0.34, 0.49), coat.darkened(0.16))
			_loft(s, Vector3(0, 2.045, -0.03), [Vector3(0, 0.63, 0.49), Vector3(0.07, 0.63, 0.49)], BRASS, 1, 24)
			_soft_link(s, Vector3(0, 2.39, -0.04), Vector3(0.22, 2.63, -0.13), 0.10, Color("bb5551"))
			for y in [0.45, 0.62, 0.79]:
				for x in [-0.22, 0.0, 0.22]:
					_round(s, Vector3(x, y, 0.307), Vector3(0.10, 0.10, 0.035), coat.lightened(0.12), 1)
			_round(s, Vector3(0, 0.30, 0.35), Vector3(0.095, 0.06, 0.025), BRASS, 1)
		2:
			_loft(s, Vector3(0, 2.07, -0.03), [Vector3(0, 0.66, 0.49), Vector3(0.09, 0.66, 0.49), Vector3(0.12, 0.52, 0.42), Vector3(0.34, 0.47, 0.38)], Color("e6c58a"), 0, 24)
			_soft_link(s, Vector3(-0.27, 0.94, 0.27), Vector3(0.35, 0.29, 0.39), 0.047, Color("80583f"), 1)
			_round(s, Vector3(0.49, 0.18, 0.25), Vector3(0.22, 0.26, 0.16), Color("8e6144"), 1)
			_round(s, Vector3(0.49, 0.25, 0.40), Vector3(0.04, 0.055, 0.02), BRASS, 1)
		3:
			_round(s, Vector3(0, 2.32, -0.12), Vector3(0.29, 0.28, 0.28), hair)
			_soft_link(s, Vector3(-0.31, 2.26, -0.02), Vector3(0.35, 2.30, -0.02), 0.028, BRASS, 1)
			_round(s, Vector3(-0.21, 0.35, 0.64), Vector3(0.22, 0.28, 0.105), Color("b27e45"), 1, Vector3(0, 0, -0.6))
			_soft_link(s, Vector3(-0.12, 0.44, 0.64), Vector3(0.56, 0.77, 0.57), 0.064, Color("dec399"), 1)
			for offset in [-0.018, 0.018]:
				_soft_link(s, Vector3(-0.26, 0.30 + offset, 0.75), Vector3(0.53, 0.75 + offset, 0.64), 0.006, IVORY, 1)
		4:
			# Lowered scarf keeps the ninja silhouette while leaving the smile visible.
			_round(s, Vector3(0, 1.04, 0.19), Vector3(0.31, 0.13, 0.27), coat.darkened(0.25))
			_loft(s, Vector3(0, 2.005, 0.03), [Vector3(0, 0.60, 0.46), Vector3(0.095, 0.58, 0.45)], Color("aaa6c2"), 1, 24)
			_round(s, Vector3(0, 2.047, 0.488), Vector3(0.075, 0.042, 0.015), BRASS, 1)
			_soft_link(s, Vector3(-0.46, 0.28, -0.32), Vector3(0.52, 1.47, -0.30), 0.062, Color("828894"))
			_soft_link(s, Vector3(0.43, 1.36, -0.29), Vector3(0.62, 1.63, -0.29), 0.076, Color("383b48"))
		5:
			_loft(s, Vector3(0, 2.06, -0.06), [Vector3(0, 0.80, 0.56), Vector3(0.085, 0.80, 0.56), Vector3(0.12, 0.49, 0.39), Vector3(0.41, 0.44, 0.34), Vector3(0.45, 0.38, 0.30)], Color("91633f"), 0, 24)
			_loft(s, Vector3(0, 2.20, -0.06), [Vector3(0, 0.49, 0.39), Vector3(0.07, 0.48, 0.38)], Color("674431"), 1, 24)
			_badge(s, [Vector3(-0.23, 1.02, 0.22), Vector3(0.23, 1.02, 0.22), Vector3(0, 0.67, 0.34)], 0.04, Color("b84f49"))
			_round(s, Vector3(-0.23, 0.72, 0.29), Vector3(0.065, 0.065, 0.026), BRASS, 1)


static func _choice_carmen(s: Sculpt) -> void:
	var red := Color("b44d59")
	var lining := Color("803642")
	var cream := Color("f1d8b6")
	var skin := Color("efb16d")
	var hair := Color("30262e")
	var gold := Color("dbac55")
	var trousers := Color("353039")
	_round(s, Vector3(0, 0.22, 0.03), Vector3(0.43, 0.22, 0.34), red)
	_round(s, Vector3(0, 0.59, -0.015), Vector3(0.40, 0.51, 0.31), red)
	for side: float in [-1.0, 1.0]:
		var knee := Vector3(side * 0.23, 0.12, 0.59)
		_soft_link(s, Vector3(side * 0.22, 0.20, 0.02), knee, 0.205, trousers)
		_soft_link(s, knee, Vector3(side * 0.25, -0.43, 0.66), 0.155, trousers)
		_round(s, Vector3(side * 0.25, -0.32, 0.665), Vector3(0.17, 0.24, 0.18), Color("46332e"))
		_round(s, Vector3(side * 0.25, -0.53, 0.78), Vector3(0.21, 0.16, 0.32), Color("3d2e2c"))
		_round(s, Vector3(side * 0.25, -0.64, 0.79), Vector3(0.205, 0.045, 0.30), Color("584139"), 1)
		_round(s, Vector3(side * 0.25, -0.21, 0.68), Vector3(0.183, 0.11, 0.192), Color("77523b"), 1)
		_choice_stroke(s, [Vector3(side * 0.25 - 0.065, -0.37, 0.841), Vector3(side * 0.25 + 0.065, -0.37, 0.841), Vector3(side * 0.25 + 0.065, -0.46, 0.87), Vector3(side * 0.25 - 0.065, -0.46, 0.87), Vector3(side * 0.25 - 0.065, -0.37, 0.841)], 0.012, gold)
		_round(s, Vector3(side * 0.40, 0.10, 0.02), Vector3(0.17, 0.20, 0.32), lining)
		_choice_stroke(s, [Vector3(side * 0.32, 0.22, 0.32), Vector3(side * 0.43, 0.05, 0.34), Vector3(side * 0.54, 0.015, 0.24)], 0.014, gold)
	# Soft blouse folds, open collar, shoulder braid and a ruby pendant.
	_round(s, Vector3(0, 0.66, 0.245), Vector3(0.25, 0.36, 0.12), cream, 1)
	_round(s, Vector3(0, 1.08, 0.02), Vector3(0.16, 0.20, 0.17), skin)
	_badge(s, [Vector3(-0.16, 1.08, 0.25), Vector3(0.16, 1.08, 0.25), Vector3(0, 0.75, 0.38)], 0.015, skin)
	for side: float in [-1.0, 1.0]:
		_badge(s, [Vector3(side * 0.16, 1.075, 0.245), Vector3(side * 0.34, 0.94, 0.25), Vector3(side * 0.22, 0.94, 0.37)], 0.035, cream)
		_badge(s, [Vector3(side * 0.30, 0.93, 0.29), Vector3(side * 0.37, 0.87, 0.22), Vector3(side * 0.21, 0.43, 0.36)], 0.04, lining)
		_choice_stroke(s, [Vector3(side * 0.30, 0.93, 0.32), Vector3(side * 0.36, 0.86, 0.29), Vector3(side * 0.21, 0.44, 0.395)], 0.014, gold)
		for fold in 5:
			var t := fold / 4.0
			var center := Vector3(side * lerpf(0.17, 0.025, t), lerpf(0.94, 0.48, t), lerpf(0.34, 0.39, t))
			_badge(s, [center + Vector3(-0.059, 0.045, 0), center + Vector3(0.055, 0.025, 0), center + Vector3(0.020, -0.057, 0.025)], 0.02, cream.lightened(0.06 * (fold % 2)))
		_round(s, Vector3(side * 0.39, 0.94, 0.02), Vector3(0.17, 0.055, 0.17), gold, 1)
		for tassel in 4:
			var x := side * (0.28 + tassel * 0.06)
			_soft_link(s, Vector3(x, 0.94, 0.15), Vector3(x + side * 0.016, 0.84, 0.19), 0.026, gold, 1)
		for y in [0.51, 0.78]:
			_round(s, Vector3(side * (0.21 + (y - 0.51) * 0.25), y, 0.35), Vector3(0.035, 0.037, 0.024), gold, 1)
	_choice_stroke(s, [Vector3(-0.13, 1.07, 0.27), Vector3(-0.09, 0.96, 0.35), Vector3(0, 0.935, 0.385), Vector3(0.09, 0.96, 0.35), Vector3(0.13, 1.07, 0.27)], 0.017, gold)
	_round(s, Vector3(0, 0.875, 0.40), Vector3(0.053, 0.068, 0.025), gold, 1)
	_round(s, Vector3(0, 0.875, 0.426), Vector3(0.033, 0.046, 0.012), Color("a32c46"), 1)
	_round(s, Vector3(-0.01, 0.896, 0.44), Vector3(0.010, 0.013, 0.004), cream, 1)
	_soft_link(s, Vector3(-0.28, 0.35, 0.32), Vector3(0.27, 0.35, 0.32), 0.057, Color("674632"), 1)
	_choice_stroke(s, [Vector3(-0.075, 0.42, 0.385), Vector3(0.06, 0.42, 0.385), Vector3(0.06, 0.285, 0.40), Vector3(-0.075, 0.285, 0.40), Vector3(-0.075, 0.42, 0.385)], 0.020, gold)
	# Both hands rest on the knees; the sash falls between the boots.
	for side: float in [-1.0, 1.0]:
		_soft_link(s, Vector3(side * 0.33, 0.87, 0.015), Vector3(side * 0.39, 0.53, 0.26), 0.155, red)
		_soft_link(s, Vector3(side * 0.39, 0.53, 0.26), Vector3(side * 0.255, 0.31, 0.56), 0.145, red)
		_round(s, Vector3(side * 0.255, 0.32, 0.55), Vector3(0.15, 0.079, 0.13), gold, 1)
		_round(s, Vector3(side * 0.255, 0.287, 0.60), Vector3(0.151, 0.065, 0.112), cream, 1)
		_round(s, Vector3(side * 0.23, 0.255, 0.69), Vector3(0.133, 0.095, 0.104), skin, 1)
		_round(s, Vector3(side * 0.14, 0.258, 0.667), Vector3(0.059, 0.069, 0.066), skin, 1)
		_round(s, Vector3(side * 0.33, 0.405, 0.48), Vector3(0.031, 0.028, 0.020), gold, 1)
	for strand in 3:
		var x := 0.035 + strand * 0.034
		_choice_stroke(s, [Vector3(0.13, 0.33, 0.43), Vector3(x, 0.12, 0.81), Vector3(x - 0.01, -0.24 - strand * 0.035, 0.85), Vector3(x + 0.035, -0.40 - strand * 0.03, 0.82)], 0.032, red.lightened(strand * 0.03))
	# The little tricorn rests on the bench beside her, never on the head.
	var felt := Color("302b37")
	_round(s, Vector3(0.64, 0.26, 0.035), Vector3(0.135, 0.16, 0.115), felt)
	var brim: Array[Vector3] = [Vector3(0.44, 0.13, 0.22), Vector3(0.59, 0.48, 0.12), Vector3(0.79, 0.18, 0.20), Vector3(0.44, 0.13, 0.22)]
	_badge(s, brim.slice(0, 3), 0.035, felt, 0)
	_choice_stroke(s, brim, 0.015, gold)
	_round(s, Vector3(0.625, 0.28, 0.233), Vector3(0.041, 0.055, 0.012), gold, 1)
	for feather in 3:
		_round(s, Vector3(0.62 + feather * 0.035, 0.56 + feather * 0.025, 0.025), Vector3(0.053, 0.19, 0.028), red.lightened(0.10 + feather * 0.035), 1, Vector3(0, 0, 0.24 - feather * 0.20))
	# A camera-facing rounded head keeps the eyes painted onto the cheeks, not protruding.
	_choice_carmen_round(s, Vector3(0, 0.035, -0.10), Vector3(0.605, 0.585, 0.385), hair)
	_choice_carmen_round(s, Vector3.ZERO, Vector3(0.55, 0.53, 0.36), skin)
	for side: float in [-1.0, 1.0]:
		_choice_carmen_round(s, Vector3(side * 0.535, -0.08, 0.05), Vector3(0.095, 0.125, 0.08), skin)
		_choice_carmen_round(s, Vector3(side * 0.546, -0.085, 0.112), Vector3(0.050, 0.068, 0.011), Color("df955b"), 1)
	# Broad interleaved waves form a single hairstyle, with tapered curls at the waist.
	for side: float in [-1.0, 1.0]:
		for lock in 3:
			var d := lock * 0.07
			var z := -0.08 + lock * 0.085
			var waves: Array[Vector3] = [Vector3(side * (0.27 + d), 0.42 - d, z), Vector3(side * (0.53 + d), 0.23 - d, z), Vector3(side * (0.49 + d), -0.04 - d, z + 0.025), Vector3(side * (0.61 - d * 0.2), -0.31 - d, z + 0.05), Vector3(side * (0.48 + d), -0.56 - d, z + 0.06), Vector3(side * (0.57 + d * 0.35), -0.83 - d, z + 0.04), Vector3(side * (0.44 + d), -1.09 - d, z + 0.06), Vector3(side * (0.45 + d * 0.45), -1.28 - d * 0.6, z + 0.08), Vector3(side * (0.63 + d * 0.15), -1.20 - d * 0.4, z + 0.10)]
			_choice_carmen_wave(s, waves, 0.133 - lock * 0.012, 0.08, hair.lightened(lock * 0.012))
	_choice_carmen_wave(s, [Vector3(0.14, 0.48, 0.06), Vector3(-0.13, 0.51, 0.12), Vector3(-0.36, 0.38, 0.19), Vector3(-0.47, 0.18, 0.21), Vector3(-0.60, 0.10, 0.17)], 0.17, 0.095, hair.lightened(0.025))
	_choice_carmen_wave(s, [Vector3(0.13, 0.50, 0.11), Vector3(-0.06, 0.42, 0.31), Vector3(-0.20, 0.25, 0.345), Vector3(-0.38, 0.13, 0.31), Vector3(-0.53, 0.05, 0.21)], 0.133, 0.075, hair.lightened(0.04))
	_choice_carmen_wave(s, [Vector3(0.14, 0.49, 0.08), Vector3(0.10, 0.34, 0.31), Vector3(0.19, 0.26, 0.36)], 0.10, 0.06, hair.lightened(0.025))
	_choice_carmen_wave(s, [Vector3(0.19, 0.43, 0.09), Vector3(0.37, 0.37, 0.19), Vector3(0.48, 0.17, 0.24), Vector3(0.46, -0.04, 0.22), Vector3(0.60, -0.25, 0.16), Vector3(0.52, -0.48, 0.18), Vector3(0.58, -0.67, 0.16)], 0.113, 0.07, hair.lightened(0.022))
	for side: float in [-1.0, 1.0]:
		var ring: Array[Vector3] = []
		for segment in 33:
			var angle := TAU * segment / 32.0
			ring.append(_choice_carmen_head(Vector3(side * 0.535 + cos(angle) * 0.068, -0.285 + sin(angle) * 0.108, 0.22)))
		_choice_hair_lock(s, ring, 0.022, gold, 1)
		_choice_carmen_round(s, Vector3(side * 0.535, -0.18, 0.24), Vector3(0.026, 0.030, 0.018), gold, 1)
		# Large brown eyes with a small ivory crescent and one quiet catchlight.
		var eye := Vector2(side * 0.215, -0.015)
		_choice_carmen_oval(s, eye, Vector2(0.128, 0.123), Color("fff0d8"), 0.004)
		_choice_carmen_oval(s, eye + Vector2(0.006, 0.002), Vector2(0.096, 0.119), Color("4b2d23"), 0.007)
		_choice_carmen_oval(s, eye + Vector2(0.006, -0.054), Vector2(0.068, 0.049), Color("89542d"), 0.009)
		_choice_carmen_oval(s, eye + Vector2(0.006, 0.028), Vector2(0.074, 0.083), Color("241c22"), 0.011)
		_choice_carmen_oval(s, eye + Vector2(0.038, 0.057), Vector2(0.023, 0.025), Color("fff5e9"), 0.014)
		var lid: Array[Vector2] = []
		var brow: Array[Vector2] = []
		for point in 25:
			var t := point / 24.0
			lid.append(eye + Vector2(lerpf(-0.13, 0.13, t), 0.107 * sin(PI * t) + 0.014))
			brow.append(Vector2(eye.x + lerpf(-0.117, 0.117, t), 0.203 + 0.032 * sin(PI * t) - side * 0.015 * (t - 0.5)))
		_choice_carmen_ink(s, lid, 0.018, Color("241c22"), 0.016)
		_choice_carmen_ink(s, brow, 0.020, hair, 0.004)
		for lash in 2:
			var a := eye + Vector2(side * (0.092 + lash * 0.020), 0.075 - lash * 0.022)
			_choice_carmen_ink(s, [a, a + Vector2(side * 0.043, 0.035 - lash * 0.007)], 0.012, Color("241c22"), 0.016)
		for blush in range(4, 0, -1):
			_choice_carmen_oval(s, Vector2(side * 0.33, -0.177), Vector2(0.019, 0.013) * blush, skin.lerp(Color("e99470"), (5 - blush) * 0.12), 0.003 + (5 - blush) * 0.001)
	# No nostril dots or teeth: a tiny nose and a single relaxed smile.
	_choice_carmen_round(s, Vector3(0, -0.126, 0.357), Vector3(0.028, 0.020, 0.019), skin.lightened(0.015), 1)
	var smile: Array[Vector2] = []
	var lip: Array[Vector2] = []
	for point in 25:
		var t := point / 24.0
		var x := lerpf(-0.079, 0.09, t)
		var y := -0.227 - 0.029 * sin(PI * t) + 0.004 * t
		smile.append(Vector2(x, y))
		lip.append(Vector2(x * 0.87, y - 0.010 * sin(PI * t)))
	_choice_carmen_ink(s, lip, 0.014, Color("cf6b69"), 0.006)
	_choice_carmen_ink(s, smile, 0.010, Color("883d3e"), 0.009)


static func _choice_carmen_head(point: Vector3) -> Vector3:
	return Vector3(0, 1.62, 0.06) + _choice_carmen_basis() * point


static func _choice_carmen_basis() -> Basis:
	return Basis(Vector3.RIGHT, -atan2(0.6, 0.8)) * Basis(Vector3.FORWARD, 0.045)


static func _choice_carmen_round(s: Sculpt, center: Vector3, radii: Vector3, color: Color,
		layer: int = 0) -> void:
	var sphere := SphereMesh.new()
	sphere.radius = 1.0
	sphere.height = 2.0
	sphere.radial_segments = 48
	sphere.rings = 24
	s.add_mesh(sphere, Transform3D(_choice_carmen_basis().scaled_local(radii), _choice_carmen_head(center)), color, layer)


static func _choice_carmen_surface(point: Vector2, depth: float) -> Vector3:
	var z := 0.36 * sqrt(maxf(0.01, 1.0 - pow(point.x / 0.55, 2) - pow(point.y / 0.53, 2)))
	return Vector3(point.x, point.y, z + depth)


static func _choice_carmen_paint(s: Sculpt, points: Array[Vector2], indices: PackedInt32Array,
		color: Color, depth: float) -> void:
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	for point in points:
		var local := _choice_carmen_surface(point, depth)
		vertices.append(_choice_carmen_head(local))
		var normal := Vector3(local.x / pow(0.55, 2), local.y / pow(0.53, 2), (local.z - depth) / pow(0.36, 2)).normalized()
		normals.append(_choice_carmen_basis() * normal)
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	s.add_mesh(mesh, Transform3D.IDENTITY, color, 1)


static func _choice_carmen_oval(s: Sculpt, center: Vector2, radii: Vector2, color: Color, depth: float) -> void:
	# Concentric surface patches follow the cheek without floating eyeball geometry.
	var points: Array[Vector2] = [center]
	var indices := PackedInt32Array()
	var sides := 48
	for ring in range(1, 7):
		for side in sides:
			var angle := TAU * side / sides
			points.append(center + Vector2(cos(angle), sin(angle)) * radii * (ring / 6.0))
			var a := 1 + (ring - 1) * sides + side
			var b := 1 + (ring - 1) * sides + (side + 1) % sides
			if ring == 1:
				indices.append_array(PackedInt32Array([0, b, a]))
			else:
				indices.append_array(PackedInt32Array([a - sides, b, a, a - sides, b - sides, b]))
	_choice_carmen_paint(s, points, indices, color, depth)


static func _choice_carmen_ink(s: Sculpt, path: Array[Vector2], width: float, color: Color, depth: float) -> void:
	var points: Array[Vector2] = []
	var indices := PackedInt32Array()
	for i in path.size():
		var tangent := (path[mini(i + 1, path.size() - 1)] - path[maxi(0, i - 1)]).normalized()
		var across := Vector2(-tangent.y, tangent.x)
		var t := i / float(path.size() - 1)
		var radius := width * (0.38 + 0.62 * pow(sin(PI * t), 0.35))
		points.append(path[i] - across * radius)
		points.append(path[i] + across * radius)
		if i > 0:
			var a := (i - 1) * 2
			indices.append_array(PackedInt32Array([a, a + 1, a + 2, a + 1, a + 3, a + 2]))
	_choice_carmen_paint(s, points, indices, color, depth)


static func _choice_carmen_wave(s: Sculpt, controls: Array[Vector3], width: float, depth: float, color: Color) -> void:
	var path: Array[Vector3] = []
	for segment in controls.size() - 1:
		var a := controls[maxi(segment - 1, 0)]
		var b := controls[segment]
		var c := controls[segment + 1]
		var d := controls[mini(segment + 2, controls.size() - 1)]
		for sample in 10:
			var t := sample / 10.0
			path.append(0.5 * ((2.0 * b) + (-a + c) * t + (2.0 * a - 5.0 * b + 4.0 * c - d) * t * t + (-a + 3.0 * b - 3.0 * c + d) * t * t * t))
	path.append(controls[-1])
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var indices := PackedInt32Array()
	var sides := 16
	for i in path.size():
		var tangent := (path[mini(i + 1, path.size() - 1)] - path[maxi(i - 1, 0)]).normalized()
		var across := Vector3(tangent.y, -tangent.x, 0).normalized()
		var front := tangent.cross(across).normalized()
		var t := i / float(path.size() - 1)
		var taper := lerpf(1.0, 0.035, smoothstep(0.69, 1.0, t))
		var bend_width := width * taper
		var bend_depth := depth * taper
		if i > 0 and i < path.size() - 1:
			var incoming := path[i] - path[i - 1]
			var outgoing := path[i + 1] - path[i]
			var turn := incoming.angle_to(outgoing)
			# Limit both axes: the curl also bends in depth, not only across its silhouette.
			var bend_radius := 0.45 * minf(incoming.length(), outgoing.length()) / maxf(turn, 0.001)
			bend_width = minf(bend_width, bend_radius)
			bend_depth = minf(bend_depth, bend_radius)
		for side in sides:
			var angle := TAU * side / sides
			var ca := cos(angle)
			var sa := sin(angle)
			vertices.append(_choice_carmen_head(path[i] + across * bend_width * ca + front * bend_depth * sa))
			normals.append(_choice_carmen_basis() * (across * ca / bend_width + front * sa / bend_depth).normalized())
			if i < path.size() - 1:
				var a := i * sides + side
				var b := i * sides + (side + 1) % sides
				indices.append_array(PackedInt32Array([a, a + sides, b, b, a + sides, b + sides]))
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	s.add_mesh(mesh, Transform3D.IDENTITY, color, 0)


static func _choice_hair_lock(s: Sculpt, points: Array[Vector3], radius: float, color: Color,
		layer: int, tapered := false) -> void:
	# A continuous swept tube avoids stacked-sphere seams and excessive geometry.
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var indices := PackedInt32Array()
	var sides := 10
	for i in points.size():
		var tangent := (points[mini(i + 1, points.size() - 1)] - points[maxi(i - 1, 0)]).normalized()
		var axis := Vector3.BACK - tangent * Vector3.BACK.dot(tangent)
		if axis.length_squared() < 0.01:
			axis = Vector3.RIGHT - tangent * Vector3.RIGHT.dot(tangent)
		axis = axis.normalized()
		var second := tangent.cross(axis).normalized()
		var t := i / float(points.size() - 1)
		var width := radius * lerpf(1.0, 0.18, smoothstep(0.76, 1.0, t)) if tapered else radius
		for side in sides:
			var angle := TAU * side / sides
			var normal := axis * cos(angle) + second * sin(angle)
			vertices.append(points[i] + normal * width)
			normals.append(normal)
			if i < points.size() - 1:
				var a := i * sides + side
				var b := i * sides + (side + 1) % sides
				indices.append_array(PackedInt32Array([a, a + sides, b, b, a + sides, b + sides]))
	for end in 2:
		var ring := 0 if end == 0 else points.size() - 1
		var center := vertices.size()
		vertices.append(points[ring])
		normals.append((points[0] - points[1]).normalized() if end == 0 else (points[-1] - points[-2]).normalized())
		for side in sides:
			var a := ring * sides + side
			var b := ring * sides + (side + 1) % sides
			indices.append_array(PackedInt32Array([center, a, b] if end == 0 else [center, b, a]))
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	s.add_mesh(mesh, Transform3D.IDENTITY, color, layer)


static func _choice_stroke(s: Sculpt, points: Array[Vector3], width: float, color: Color, layer: int = 1) -> void:
	for i in range(points.size() - 1):
		_soft_link(s, points[i], points[i + 1], width, color, layer)
		if i > 0:
			_round(s, points[i], Vector3.ONE * width, color, layer)


static func _round(s: Sculpt, center: Vector3, radii: Vector3, color: Color,
		layer: int = 0, rotation: Vector3 = Vector3.ZERO) -> void:
	var sphere := SphereMesh.new()
	sphere.radius = 1.0
	sphere.height = 2.0
	sphere.radial_segments = 24
	sphere.rings = 12
	s.add_mesh(sphere, Transform3D(Basis.from_euler(rotation).scaled_local(radii), center), color, layer)


static func _soft_link(s: Sculpt, a: Vector3, b: Vector3, radius: float, color: Color, layer: int = 0) -> void:
	var rotation := Basis(Quaternion(Vector3.UP, (b - a).normalized())).get_euler()
	_round(s, (a + b) * 0.5, Vector3(radius, a.distance_to(b) * 0.5 + radius * 0.45, radius), color, layer, rotation)


static func _face(s: Sculpt, skin: Color, hair: Color, masked: bool = false,
		long_hair: bool = false) -> void:
	# Neck connects the head to the shoulder line instead of leaving it floating.
	_link(s, Vector3(0, 2.10, 0), Vector3(0, 2.43, 0), 0.16, 0.18, skin)
	# Back-of-head mass, real cheeks/chin, ears and a projecting carved nose.
	_ellipsoid(s, Vector3(0, 2.82, -0.115), Vector3(0.464, 0.515, 0.325), hair)
	_ellipsoid(s, Vector3(0, 2.76, 0.045), Vector3(0.435, 0.488, 0.359), skin)
	for side: float in [-1.0, 1.0]:
		_ellipsoid(s, Vector3(side * 0.443, 2.755, 0.035), Vector3(0.081, 0.132, 0.091), skin)
		_ellipsoid(s, Vector3(side * 0.159, 2.827, 0.375), Vector3(0.087, 0.049, 0.018), IVORY, 1)
		_ellipsoid(s, Vector3(side * 0.151, 2.827, 0.391), Vector3(0.036, 0.043, 0.013), INK, 1)
		_link(s, Vector3(side * 0.084, 2.933, 0.359), Vector3(side * 0.249, 2.921, 0.331),
			0.025, 0.021, hair, 1, 0.60)
	_ellipsoid(s, Vector3(0, 2.715, 0.398), Vector3(0.071, 0.107, 0.101), skin.lightened(0.07), 1)
	if not masked:
		_link(s, Vector3(-0.065, 2.561, 0.352), Vector3(0.065, 2.558, 0.352),
			0.012, 0.012, skin.darkened(0.32), 1, 0.5)
	if long_hair:
		for side: float in [-1.0, 1.0]:
			_link(s, Vector3(side * 0.34, 2.95, -0.11), Vector3(side * 0.37, 2.02, -0.16),
				0.18, 0.11, hair, 0, 0.8)


static func _torso(s: Sculpt, color: Color, waist: float = 0.32) -> void:
	_loft(s, Vector3.ZERO, [Vector3(1.18, waist * 0.95, 0.205), Vector3(1.38, waist, 0.235),
		Vector3(1.83, 0.43, 0.26), Vector3(2.08, 0.44, 0.23),
		Vector3(2.22, 0.27, 0.18)], color)


static func _boots(s: Sculpt, pants: Color, leather: Color, stance: float = 0.24) -> void:
	for side: float in [-1.0, 1.0]:
		_link(s, Vector3(side * stance, 0.62, 0.015), Vector3(side * 0.19, 1.37, -0.01),
			0.16, 0.21, pants)
		_loft(s, Vector3(side * stance, 0, 0.045), [Vector3(0.175, 0.18, 0.235),
			Vector3(0.22, 0.19, 0.25), Vector3(0.34, 0.17, 0.225),
			Vector3(0.43, 0.139, 0.15), Vector3(0.76, 0.155, 0.145)], leather)


static func _arm(s: Sculpt, shoulder: Vector3, elbow: Vector3, wrist: Vector3,
		sleeve: Color, cuff: Color, skin: Color) -> void:
	_link(s, shoulder, elbow, 0.19, 0.16, sleeve)
	_link(s, elbow, wrist, 0.145, 0.115, cuff)
	_ellipsoid(s, wrist, Vector3(0.116, 0.13, 0.10), skin)


static func _belt(s: Sculpt, color: Color, buckle: bool = true) -> void:
	_loft(s, Vector3.ZERO, [Vector3(1.36, 0.345, 0.252), Vector3(1.48, 0.354, 0.255)], color, 1)
	if buckle:
		_badge(s, [Vector3(-0.075, 1.486, 0.261), Vector3(0.075, 1.486, 0.261),
			Vector3(0.075, 1.37, 0.271), Vector3(-0.075, 1.37, 0.271)], 0.033, BRASS)


static func _carmen(s: Sculpt) -> void:
	var coat := Color("#a34849")
	var lining := Color("#672f38")
	var cream := Color("#e4c29b")
	var skin := Color("#cf925a")
	var hair := Color("#242c32")
	# The portrait stops at the thighs; the dark boots are a restrained completion.
	_boots(s, Color("#343b40"), Color("#342d2b"), 0.22)
	_loft(s, Vector3.ZERO, [Vector3(1.07, 0.31, 0.21), Vector3(1.26, 0.37, 0.25),
		Vector3(1.53, 0.32, 0.225)], Color("#343b40"))
	for side: float in [-1.0, 1.0]:
		_loft(s, Vector3(side * 0.32, 0, -0.14), [Vector3(0.30, 0.25, 0.15),
			Vector3(0.48, 0.29, 0.18), Vector3(1.15, 0.24, 0.21),
			Vector3(1.56, 0.19, 0.22)], lining)
		_badge(s, [Vector3(side * 0.33, 1.52, 0.15), Vector3(side * 0.56, 0.45, 0.02),
			Vector3(side * 0.35, 0.33, 0.05), Vector3(side * 0.23, 1.40, 0.18)], 0.04, coat, 0)
	_loft(s, Vector3.ZERO, [Vector3(1.40, 0.33, 0.22), Vector3(1.60, 0.32, 0.23),
		Vector3(1.94, 0.40, 0.265), Vector3(2.35, 0.46, 0.25),
		Vector3(2.52, 0.46, 0.215), Vector3(2.62, 0.28, 0.17)], coat)
	# A broad cream blouse and an open ruffled neckline, not a narrow pink bib.
	_loft(s, Vector3(0, 0, 0.075), [Vector3(1.52, 0.245, 0.205),
		Vector3(1.79, 0.305, 0.23), Vector3(2.18, 0.335, 0.245),
		Vector3(2.42, 0.245, 0.205), Vector3(2.52, 0.16, 0.17)], cream)
	_link(s, Vector3(0.015, 2.45, 0.01), Vector3(0.025, 2.91, 0.01), 0.15, 0.14, skin)
	_badge(s, [Vector3(-0.18, 2.55, 0.29), Vector3(0.19, 2.55, 0.29),
		Vector3(0.21, 2.40, 0.325), Vector3(0.0, 2.13, 0.337),
		Vector3(-0.22, 2.37, 0.325)], 0.026, skin)
	for side: float in [-1.0, 1.0]:
		var edge: Array[Vector3] = [Vector3(side * 0.21, 2.55, 0.32),
			Vector3(side * 0.24, 2.40, 0.34), Vector3(side * 0.16, 2.27, 0.36),
			Vector3(side * 0.065, 2.14, 0.365), Vector3(side * 0.045, 1.63, 0.32)]
		_carmen_stroke(s, edge, 0.035, Color("#b88f6e"))
		for i in range(4):
			var center := edge[mini(i, 3)]
			_badge(s, [center + Vector3(-0.052, 0.045, 0.025),
				center + Vector3(0.032, 0.060, 0.01), center + Vector3(0.065, -0.035, 0.03),
				center + Vector3(-0.027, -0.070, 0.05)], 0.025, cream.lightened(0.08))
		# Each lapel is convex; the folded notch is a separate piece.
		_badge(s, [Vector3(side * 0.22, 2.64, 0.19), Vector3(side * 0.38, 2.71, 0.12),
			Vector3(side * 0.47, 2.44, 0.28), Vector3(side * 0.31, 2.45, 0.31)], 0.065, lining, 0)
		_badge(s, [Vector3(side * 0.31, 2.43, 0.325), Vector3(side * 0.48, 2.35, 0.255),
			Vector3(side * 0.30, 1.52, 0.30), Vector3(side * 0.22, 1.60, 0.32)], 0.055, coat)
		_carmen_stroke(s, [Vector3(side * 0.23, 2.64, 0.23), Vector3(side * 0.37, 2.69, 0.17),
			Vector3(side * 0.46, 2.44, 0.32), Vector3(side * 0.31, 2.45, 0.35)], 0.014, BRASS)
		_carmen_stroke(s, [Vector3(side * 0.31, 2.42, 0.36), Vector3(side * 0.46, 2.34, 0.30),
			Vector3(side * 0.28, 1.56, 0.35)], 0.015, BRASS)
	for row in range(3):
		var y := 1.69 + row * 0.135
		_badge(s, [Vector3(-0.05, y + 0.06, 0.34), Vector3(0.045, y + 0.08, 0.34),
			Vector3(0.075, y - 0.045, 0.365), Vector3(-0.025, y - 0.06, 0.37)], 0.02, cream)
	# Image-left arm cradles the hat; image-right elbow opens into a hand-on-hip pose.
	_link(s, Vector3(-0.43, 2.46, 0.0), Vector3(-0.67, 2.00, 0.03), 0.20, 0.165, coat)
	_link(s, Vector3(-0.67, 2.00, 0.03), Vector3(-0.63, 1.46, 0.34), 0.16, 0.14, coat)
	_link(s, Vector3(0.43, 2.45, 0.0), Vector3(0.71, 1.96, 0.0), 0.20, 0.16, coat)
	_link(s, Vector3(0.71, 1.96, 0.0), Vector3(0.46, 1.69, 0.29), 0.16, 0.14, coat)
	for wrist: Vector3 in [Vector3(-0.63, 1.45, 0.36), Vector3(0.45, 1.69, 0.30)]:
		_ellipsoid(s, wrist, Vector3(0.155, 0.12, 0.125), BRASS, 1, Vector3(0, 0, -0.35))
		_ellipsoid(s, wrist + Vector3(-0.02, -0.035, 0.055), Vector3(0.145, 0.085, 0.12), cream, 1)
	_ellipsoid(s, Vector3(0.33, 1.63, 0.405), Vector3(0.15, 0.09, 0.067), skin, 1, Vector3(0, 0, 0.28))
	for finger in range(4):
		var offset := finger * 0.034
		_link(s, Vector3(0.30 + offset, 1.62 - offset * 0.25, 0.425),
			Vector3(0.21 + offset, 1.47 - offset * 0.10, 0.43), 0.024, 0.018, skin, 1, 0.7)
	_link(s, Vector3(0.36, 1.69, 0.41), Vector3(0.20, 1.70, 0.40), 0.03, 0.022, skin, 1)
	for side: float in [-1.0, 1.0]:
		_ellipsoid(s, Vector3(side * 0.45, 2.535, -0.005), Vector3(0.19, 0.065, 0.14), BRASS, 1)
		for tassel in range(5):
			var x := side * (0.31 + tassel * 0.062)
			_link(s, Vector3(x, 2.52, 0.115), Vector3(x + side * 0.018, 2.43, 0.13),
				0.019, 0.016, BRASS, 1)
	for button in range(4):
		_ellipsoid(s, Vector3(0.385 - button * 0.025, 2.29 - button * 0.17, 0.343),
			Vector3(0.036, 0.043, 0.02), BRASS, 1)
	# Red waist sash with long separate tails, plus a dark belt and open gold buckle.
	_loft(s, Vector3.ZERO, [Vector3(1.37, 0.365, 0.27), Vector3(1.51, 0.357, 0.29),
		Vector3(1.57, 0.335, 0.27)], coat, 1)
	_link(s, Vector3(-0.30, 1.51, 0.26), Vector3(0.21, 1.49, 0.33), 0.06, 0.055, Color("#48352c"), 1, 0.55)
	_badge(s, [Vector3(-0.16, 1.59, 0.345), Vector3(0.03, 1.57, 0.345),
		Vector3(0.005, 1.405, 0.365), Vector3(-0.185, 1.425, 0.365)], 0.035, BRASS)
	_badge(s, [Vector3(-0.127, 1.55, 0.369), Vector3(-0.005, 1.535, 0.369),
		Vector3(-0.022, 1.45, 0.38), Vector3(-0.143, 1.465, 0.38)], 0.012, Color("#47382e"))
	_ellipsoid(s, Vector3(0.15, 1.47, 0.335), Vector3(0.115, 0.09, 0.085), lining, 1)
	_badge(s, [Vector3(0.10, 1.46, 0.38), Vector3(0.22, 1.43, 0.39),
		Vector3(0.24, 0.38, 0.28), Vector3(0.05, 0.44, 0.30)], 0.06, coat, 0)
	_badge(s, [Vector3(0.18, 1.44, 0.32), Vector3(0.28, 1.39, 0.30),
		Vector3(0.42, 0.71, 0.21), Vector3(0.29, 0.62, 0.26)], 0.04, lining)
	_carmen_stroke(s, [Vector3(-0.29, 1.35, 0.23), Vector3(-0.21, 1.20, 0.26),
		Vector3(-0.06, 1.14, 0.26), Vector3(0.04, 1.23, 0.28)], 0.013, BRASS)
	_carmen_head(s, skin, hair)
	_carmen_hat(s, skin, coat)
	_carmen_stroke(s, [Vector3(-0.13, 2.66, 0.19), Vector3(-0.09, 2.43, 0.34),
		Vector3(0.03, 2.34, 0.37), Vector3(0.17, 2.58, 0.28)], 0.012, BRASS)
	_ellipsoid(s, Vector3(0.03, 2.34, 0.39), Vector3(0.062, 0.077, 0.026), BRASS, 1, Vector3(0, 0, -0.25))
	_ellipsoid(s, Vector3(0.03, 2.34, 0.416), Vector3(0.038, 0.052, 0.016), Color("#863943"), 1)


static func _carmen_stroke(s: Sculpt, points: Array[Vector3], width: float, color: Color,
		layer: int = 1) -> void:
	for i in range(points.size() - 1):
		_link(s, points[i], points[i + 1], width, width, color, layer)
		if i > 0:
			_ellipsoid(s, points[i], Vector3.ONE * width, color, layer)


static func _carmen_head(s: Sculpt, skin: Color, hair: Color) -> void:
	var starts: Array[int] = [s.vertices[0].size(), s.vertices[1].size()]
	# Bare head, tapered jaw and swept black waves; never the shared round face.
	_loft(s, Vector3(0.015, 0, 0.01), [Vector3(2.77, 0.13, 0.14),
		Vector3(2.86, 0.235, 0.21), Vector3(3.04, 0.31, 0.25),
		Vector3(3.24, 0.31, 0.25), Vector3(3.42, 0.245, 0.20),
		Vector3(3.48, 0.15, 0.14)], skin, 0, 12)
	_loft(s, Vector3(-0.015, 0, -0.24), [Vector3(1.91, 0.27, 0.115),
		Vector3(2.25, 0.46, 0.19), Vector3(2.77, 0.40, 0.23),
		Vector3(3.26, 0.38, 0.245), Vector3(3.49, 0.22, 0.17)], hair)
	_ellipsoid(s, Vector3(-0.025, 3.38, -0.09), Vector3(0.36, 0.215, 0.27), hair)
	for side: float in [-1.0, 1.0]:
		_ellipsoid(s, Vector3(side * 0.32, 3.07, 0.055), Vector3(0.055, 0.09, 0.055), skin)
		var curl: Array[Vector3] = [Vector3(side * 0.26, 3.42, -0.08),
			Vector3(side * 0.39, 3.19, -0.12), Vector3(side * 0.33, 2.96, -0.15),
			Vector3(side * 0.46, 2.72, -0.18), Vector3(side * 0.35, 2.48, -0.16),
			Vector3(side * 0.46, 2.23, -0.16), Vector3(side * 0.31, 2.00, -0.14)]
		_carmen_stroke(s, curl, 0.095, hair, 0)
		for strand in range(2):
			var line: Array[Vector3] = []
			for point in curl:
				line.append(point + Vector3(side * (strand * 0.068 - 0.02), -0.025 * strand, 0.072))
			_carmen_stroke(s, line, 0.016, Color("#40464a"))
		var earring: Array[Vector3] = []
		for segment in range(13):
			var angle := TAU * segment / 12.0
			earring.append(Vector3(side * 0.348 + cos(angle) * 0.072, 2.955 + sin(angle) * 0.11, 0.155))
		_carmen_stroke(s, earring, 0.013, BRASS)
	# Asymmetric swept locks leave the forehead and arched brows exposed.
	for strand in range(3):
		var shift := strand * 0.043
		_carmen_stroke(s, [Vector3(0.075, 3.43 + shift, 0.15 - shift),
			Vector3(-0.07, 3.50 + shift * 0.5, 0.15 - shift), Vector3(-0.25, 3.39, 0.18 - shift),
			Vector3(-0.34, 3.19, 0.11 - shift)], 0.065, hair, 0)
		_carmen_stroke(s, [Vector3(0.075, 3.465 + shift, 0.18 - shift),
			Vector3(-0.08, 3.53 + shift * 0.5, 0.17 - shift), Vector3(-0.28, 3.36, 0.205 - shift)],
			0.012, Color("#44494b"))
	_carmen_stroke(s, [Vector3(0.13, 3.43, 0.17), Vector3(0.27, 3.42, 0.16),
		Vector3(0.34, 3.26, 0.06), Vector3(0.29, 3.11, 0.015)], 0.07, hair, 0)
	for side: float in [-1.0, 1.0]:
		var x := side * 0.135 + 0.015
		_badge(s, [Vector3(x - 0.080, 3.185, 0.258), Vector3(x - 0.018, 3.218, 0.264),
			Vector3(x + 0.071, 3.197, 0.258), Vector3(x + 0.013, 3.163, 0.266)],
			0.012, Color("#ecdbb5"))
		_ellipsoid(s, Vector3(x + 0.012, 3.189, 0.278), Vector3(0.025, 0.030, 0.012), Color("#413726"), 1)
		_ellipsoid(s, Vector3(x + 0.013, 3.19, 0.289), Vector3(0.011, 0.021, 0.006), INK, 1)
		_carmen_stroke(s, [Vector3(x - 0.078, 3.193, 0.28), Vector3(x - 0.02, 3.222, 0.285),
			Vector3(x + 0.074, 3.201, 0.28)], 0.009, hair)
		_carmen_stroke(s, [Vector3(x - 0.07, 3.286, 0.243), Vector3(x - 0.01, 3.31, 0.25),
			Vector3(x + 0.072, 3.285, 0.242)], 0.023, hair)
	_ellipsoid(s, Vector3(0.023, 3.111, 0.268), Vector3(0.038, 0.075, 0.039), skin, 1)
	_ellipsoid(s, Vector3(0.024, 3.062, 0.302), Vector3(0.046, 0.028, 0.047), skin.lightened(0.05), 1)
	_badge(s, [Vector3(-0.06, 2.962, 0.245), Vector3(-0.009, 2.98, 0.26),
		Vector3(0.03, 2.972, 0.267), Vector3(0.085, 2.956, 0.245),
		Vector3(0.02, 2.931, 0.267)], 0.018, Color("#a25b4e"))
	_link(s, Vector3(-0.052, 2.958, 0.272), Vector3(0.073, 2.953, 0.275), 0.007, 0.007, Color("#754a40"), 1)
	# Compress only this head above the collar; the fixed camera sees the back of the crown too.
	for layer in range(2):
		for vertex in range(starts[layer], s.vertices[layer].size()):
			var point := s.vertices[layer][vertex]
			if point.y > 2.72:
				point.y = 2.72 + (point.y - 2.72) * 0.93
				s.vertices[layer][vertex] = point
				var normal := s.normals[layer][vertex]
				normal.y /= 0.93
				s.normals[layer][vertex] = normal.normalized()


static func _carmen_hat(s: Sculpt, skin: Color, red: Color) -> void:
	var felt := Color("#29333c")
	# The red-plumed hat is held against the image-left hip, not worn.
	_ellipsoid(s, Vector3(-0.60, 1.78, 0.39), Vector3(0.22, 0.28, 0.14), felt, 0, Vector3(0, 0, -0.30))
	_badge(s, [Vector3(-0.86, 1.84, 0.56), Vector3(-0.64, 1.70, 0.58),
		Vector3(-0.55, 1.42, 0.59), Vector3(-0.85, 1.47, 0.55)], 0.075, felt, 0)
	_badge(s, [Vector3(-0.64, 1.70, 0.59), Vector3(-0.35, 2.03, 0.50),
		Vector3(-0.29, 1.65, 0.54), Vector3(-0.55, 1.42, 0.59)], 0.075, felt, 0)
	_carmen_stroke(s, [Vector3(-0.85, 1.83, 0.606), Vector3(-0.64, 1.72, 0.63),
		Vector3(-0.35, 2.03, 0.55), Vector3(-0.29, 1.65, 0.58), Vector3(-0.55, 1.43, 0.64)], 0.014, BRASS)
	for feather in range(3):
		var shift := feather * 0.13
		_badge(s, [Vector3(-0.61, 1.99, 0.39), Vector3(-0.88 + shift, 2.28, 0.34),
			Vector3(-0.85 + shift, 2.45 + shift * 0.15, 0.32), Vector3(-0.69 + shift, 2.31, 0.34)],
			0.04, red.lightened(feather * 0.06), 0)
		_carmen_stroke(s, [Vector3(-0.61, 2.00, 0.42), Vector3(-0.79 + shift, 2.25, 0.38),
			Vector3(-0.85 + shift, 2.43 + shift * 0.15, 0.355)], 0.01, Color("#cf7770"))
	_badge(s, [Vector3(-0.59, 1.69, 0.66), Vector3(-0.54, 1.75, 0.64),
		Vector3(-0.47, 1.68, 0.63), Vector3(-0.54, 1.61, 0.66)], 0.017, BRASS)
	_ellipsoid(s, Vector3(-0.63, 1.40, 0.54), Vector3(0.115, 0.083, 0.09), skin, 1)
	for finger in range(4):
		var shift := finger * 0.035
		_link(s, Vector3(-0.68 + shift, 1.41, 0.61), Vector3(-0.66 + shift, 1.56 + shift * 0.6, 0.65),
			0.023, 0.017, skin, 1, 0.7)


static func _li_yunlong(s: Sculpt) -> void:
	var armor: Color = Color("#667f93")
	var dark: Color = Color("#3f5268")
	var red: Color = Color("#ba524a")
	var skin: Color = Color("#e3ac83")
	_boots(s, dark, Color("#3e414c"), 0.26)
	_torso(s, dark, 0.36)
	# Overlapping elliptical lamellar courses have real stepped silhouettes.
	for row: int in range(3):
		var y: float = 0.91 + float(row) * 0.205
		var w: float = 0.47 - float(row) * 0.038
		_loft(s, Vector3.ZERO, [Vector3(y, w, 0.285), Vector3(y + 0.07, w, 0.285),
			Vector3(y + 0.27, w - 0.05, 0.24)], armor if row % 2 == 0 else dark)
	_ellipsoid(s, Vector3(0, 1.91, 0.17), Vector3(0.37, 0.31, 0.18), armor)
	_arm(s, Vector3(-0.40, 2.10, 0), Vector3(-0.59, 1.75, 0.01),
		Vector3(-0.56, 1.45, 0.09), dark, armor, skin)
	_arm(s, Vector3(0.40, 2.10, 0), Vector3(0.63, 1.79, 0.06),
		Vector3(0.39, 1.65, 0.30), dark, armor, skin)
	for side: float in [-1.0, 1.0]:
		_ellipsoid(s, Vector3(side * 0.45, 2.135, 0), Vector3(0.285, 0.177, 0.275), armor)
	_belt(s, red)
	_face(s, skin, Color("#3f393a"))
	# Ming-style flared neck guard, a domed helmet and a swept red plume.
	_loft(s, Vector3(0, 2.78, -0.145), [Vector3(0, 0.50, 0.29),
		Vector3(0.20, 0.45, 0.27), Vector3(0.29, 0.39, 0.24)], dark)
	_loft(s, Vector3(0, 3.055, -0.035), [Vector3(0, 0.477, 0.358),
		Vector3(0.10, 0.479, 0.359), Vector3(0.27, 0.34, 0.28),
		Vector3(0.36, 0.12, 0.10)], armor)
	_link(s, Vector3(0, 3.365, 0), Vector3(0.13, 3.535, -0.055), 0.079, 0.056, red)
	_link(s, Vector3(0.11, 3.515, -0.055), Vector3(0.33, 3.465, -0.13), 0.063, 0.008, red)
	_badge(s, [Vector3(-0.065, 3.27, 0.32), Vector3(0.065, 3.27, 0.32),
		Vector3(0.08, 3.071, 0.367), Vector3(-0.08, 3.071, 0.367)], 0.02, BRASS)
	# A tiny separate moustache is paint relief rather than a black eye socket.
	for side: float in [-1.0, 1.0]:
		_link(s, Vector3(side * 0.025, 2.61, 0.375), Vector3(side * 0.13, 2.582, 0.337),
			0.023, 0.009, Color("#493c38"), 1)


static func _lakan(s: Sculpt) -> void:
	var gold: Color = Color("#c8944f")
	var brown: Color = Color("#815941")
	var skin: Color = Color("#bc815d")
	_boots(s, Color("#8c7652"), Color("#654739"), 0.23)
	_torso(s, gold, 0.36)
	# Short back mantle: broad shoulders taper to an irregular waist hem.
	_loft(s, Vector3(0, 0, -0.12), [Vector3(1.53, 0.415, 0.21),
		Vector3(1.65, 0.49, 0.24), Vector3(2.10, 0.50, 0.26),
		Vector3(2.20, 0.29, 0.20)], brown)
	_badge(s, [Vector3(-0.26, 2.17, 0.19), Vector3(0.29, 2.08, 0.23),
		Vector3(0.22, 1.45, 0.273), Vector3(-0.27, 1.59, 0.277)], 0.035, gold)
	_link(s, Vector3(-0.18, 2.18, 0.22), Vector3(0.22, 1.65, 0.304), 0.035, 0.025, IVORY, 1, 0.5)
	_belt(s, brown, false)
	_arm(s, Vector3(-0.4, 2.06, 0), Vector3(-0.55, 1.76, 0),
		Vector3(-0.48, 1.57, 0.31), brown, gold, skin)
	_arm(s, Vector3(0.4, 2.06, 0), Vector3(0.55, 1.78, 0.03),
		Vector3(0.33, 1.78, 0.36), brown, gold, skin)
	_face(s, skin, Color("#463831"))
	# Wrapped headcloth, asymmetric knot, no imperial/modern military hat.
	_loft(s, Vector3(0, 3.08, -0.035), [Vector3(0, 0.453, 0.345),
		Vector3(0.12, 0.47, 0.355), Vector3(0.27, 0.36, 0.285),
		Vector3(0.34, 0.13, 0.15)], Color("#ddbb79"))
	_link(s, Vector3(-0.38, 3.15, 0.22), Vector3(0.36, 3.28, 0.17), 0.055, 0.052, gold, 1, 0.60)
	_ellipsoid(s, Vector3(-0.39, 3.15, -0.10), Vector3(0.125, 0.13, 0.15), gold)
	# Diagonal strap and a sculpted satchel with flap.
	_link(s, Vector3(-0.29, 2.14, 0.29), Vector3(0.37, 1.23, 0.30), 0.050, 0.050, brown, 1, 0.48)
	_ellipsoid(s, Vector3(0.40, 1.14, 0.15), Vector3(0.24, 0.26, 0.17), brown)
	_badge(s, [Vector3(0.19, 1.30, 0.266), Vector3(0.59, 1.30, 0.266),
		Vector3(0.51, 1.12, 0.321), Vector3(0.26, 1.12, 0.321)], 0.035, gold)
	_ellipsoid(s, Vector3(-0.36, 1.25, 0.28), Vector3(0.15, 0.18, 0.125), Color("#b28243"))
	_link(s, Vector3(-0.40, 1.40, 0.29), Vector3(-0.30, 1.40, 0.29), 0.027, 0.027, BRASS, 1)
	_link(s, Vector3(-0.40, 1.64, 0.43), Vector3(0.23, 1.80, 0.45), 0.083, 0.084, IVORY, 1)


static func _izefia(s: Sculpt) -> void:
	var skin: Color = Color("#845743")
	var mint: Color = Color("#8acdb5")
	var deep: Color = Color("#468e86")
	var hair: Color = Color("#353031")
	_boots(s, deep, Color("#745142"), 0.20)
	# Tiered fabric builds a feminine silhouette without a flat cone body.
	_loft(s, Vector3.ZERO, [Vector3(0.50, 0.42, 0.29), Vector3(0.62, 0.44, 0.30),
		Vector3(1.15, 0.31, 0.235), Vector3(1.37, 0.29, 0.22)], deep)
	_loft(s, Vector3.ZERO, [Vector3(0.95, 0.43, 0.285), Vector3(1.04, 0.44, 0.29),
		Vector3(1.52, 0.29, 0.23)], mint)
	_torso(s, Color("#efe1b7"), 0.29)
	_arm(s, Vector3(-0.36, 2.08, 0), Vector3(-0.55, 1.71, 0.12),
		Vector3(-0.18, 1.67, 0.44), mint, skin, skin)
	_arm(s, Vector3(0.36, 2.08, 0), Vector3(0.59, 1.94, 0.12),
		Vector3(0.48, 2.20, 0.38), mint, skin, skin)
	# A draped shoulder ribbon slopes visibly across the chest.
	_badge(s, [Vector3(-0.44, 2.20, 0.10), Vector3(0.43, 2.18, 0.10),
		Vector3(0.36, 1.79, 0.25), Vector3(-0.39, 1.97, 0.26)], 0.055, mint, 0)
	_face(s, skin, hair)
	_ellipsoid(s, Vector3(0, 3.23, -0.15), Vector3(0.31, 0.27, 0.28), hair)
	_link(s, Vector3(-0.36, 3.04, 0.22), Vector3(0.32, 3.10, 0.25), 0.033, 0.033, BRASS, 1, 0.60)
	_ellipsoid(s, Vector3(-0.36, 3.13, 0.17), Vector3(0.097, 0.13, 0.062), mint, 1)
	for side: float in [-1.0, 1.0]:
		_ellipsoid(s, Vector3(side * 0.46, 2.60, 0.07), Vector3(0.039, 0.083, 0.030), BRASS, 1)
	# Small pear-bodied lute: soundboard, dark soundhole, neck, strings, bridge.
	_ellipsoid(s, Vector3(-0.09, 1.62, 0.42), Vector3(0.29, 0.355, 0.165), Color("#8f563b"), 0, Vector3(0, 0, -0.25))
	_ellipsoid(s, Vector3(-0.075, 1.63, 0.542), Vector3(0.247, 0.308, 0.045), Color("#deb577"), 1, Vector3(0, 0, -0.25))
	_link(s, Vector3(0.055, 1.81, 0.47), Vector3(0.48, 2.36, 0.40), 0.077, 0.065, Color("#70503b"), 0, 0.65)
	_ellipsoid(s, Vector3(0.005, 1.75, 0.591), Vector3(0.079, 0.085, 0.009), Color("#634735"), 1)
	_link(s, Vector3(-0.22, 1.44, 0.588), Vector3(-0.04, 1.36, 0.588), 0.023, 0.023, Color("#755137"), 1, 0.65)
	for string_id: int in range(3):
		var shift: float = (float(string_id) - 1.0) * 0.033
		_link(s, Vector3(-0.13 + shift, 1.42, 0.608), Vector3(0.49 + shift, 2.36, 0.474),
			0.006, 0.006, IVORY, 1)
	_link(s, Vector3(0.385, 2.30, 0.425), Vector3(0.575, 2.39, 0.425), 0.024, 0.024, BRASS, 1)


static func _kage(s: Sculpt) -> void:
	var cloth: Color = Color("#4e505c")
	var dark: Color = Color("#353944")
	var purple: Color = Color("#66526f")
	var skin: Color = Color("#d8a480")
	_boots(s, cloth, dark, 0.28)
	_torso(s, dark, 0.30)
	# One bent arm guards the chest while the other reaches toward the belt.
	_arm(s, Vector3(-0.37, 2.07, 0), Vector3(-0.61, 1.81, 0.01),
		Vector3(-0.41, 1.58, 0.27), cloth, purple, dark)
	_arm(s, Vector3(0.37, 2.07, 0), Vector3(0.60, 1.87, 0.03),
		Vector3(0.26, 2.04, 0.31), cloth, purple, dark)
	_belt(s, purple, false)
	_link(s, Vector3(-0.28, 2.17, 0.212), Vector3(0.29, 1.49, 0.276), 0.047, 0.047, Color("#a1928e"), 1, 0.45)
	_link(s, Vector3(0.28, 2.17, 0.220), Vector3(-0.29, 1.49, 0.279), 0.047, 0.047, Color("#a1928e"), 1, 0.45)
	_face(s, skin, dark, true)
	# Eye opening stays exposed between hood band and shaped lower mask.
	_loft(s, Vector3(0, 3.03, -0.045), [Vector3(0, 0.47, 0.348),
		Vector3(0.13, 0.472, 0.35), Vector3(0.31, 0.30, 0.25),
		Vector3(0.37, 0.07, 0.10)], dark)
	_ellipsoid(s, Vector3(0, 2.54, 0.252), Vector3(0.351, 0.225, 0.215), cloth)
	_link(s, Vector3(-0.29, 2.68, 0.351), Vector3(0, 2.719, 0.45), 0.016, 0.02, purple, 1)
	_link(s, Vector3(0, 2.719, 0.45), Vector3(0.29, 2.68, 0.351), 0.02, 0.016, purple, 1)
	_loft(s, Vector3(0, 2.24, 0), [Vector3(0, 0.25, 0.19), Vector3(0.15, 0.30, 0.22)], purple)
	_badge(s, [Vector3(-0.15, 2.38, -0.27), Vector3(-0.66, 2.55, -0.19),
		Vector3(-0.80, 2.40, -0.10), Vector3(-0.28, 2.19, -0.22)], 0.06, purple, 0)
	# Short back scabbard is diagonal and never covers the face.
	_link(s, Vector3(-0.30, 1.20, -0.30), Vector3(0.41, 2.28, -0.30), 0.077, 0.068, Color("#49404c"))
	_link(s, Vector3(0.40, 2.27, -0.30), Vector3(0.59, 2.54, -0.30), 0.057, 0.056, purple)
	_link(s, Vector3(0.33, 2.31, -0.30), Vector3(0.48, 2.21, -0.30), 0.027, 0.027, BRASS, 1)
	for side: float in [-1.0, 1.0]:
		_loft(s, Vector3(side * 0.28, 0.65, 0.045), [Vector3(0, 0.166, 0.153),
			Vector3(0.09, 0.164, 0.15)], purple, 1, 8)


static func _jack(s: Sculpt) -> void:
	var skin: Color = Color("#dca682")
	var leather: Color = Color("#a96b40")
	var shirt: Color = Color("#eee0c4")
	var hat: Color = Color("#c18b50")
	_boots(s, Color("#64707c"), Color("#76503b"), 0.26)
	_torso(s, shirt, 0.33)
	# Two separate vest fronts retain a bright shirt opening.
	for side: float in [-1.0, 1.0]:
		_loft(s, Vector3(side * 0.255, 0, 0.125), [Vector3(1.47, 0.17, 0.145),
			Vector3(1.65, 0.20, 0.165), Vector3(2.10, 0.16, 0.13),
			Vector3(2.17, 0.105, 0.09)], leather)
	_arm(s, Vector3(-0.40, 2.07, 0), Vector3(-0.58, 1.76, 0.05),
		Vector3(-0.37, 1.58, 0.28), shirt, shirt, skin)
	_arm(s, Vector3(0.40, 2.07, 0), Vector3(0.56, 1.74, 0.04),
		Vector3(0.56, 1.38, 0.14), shirt, shirt, skin)
	_belt(s, Color("#684a39"))
	_badge(s, [Vector3(-0.24, 2.20, 0.23), Vector3(0.25, 2.20, 0.23),
		Vector3(0.04, 1.94, 0.302)], 0.045, Color("#b75647"), 0)
	_face(s, skin, Color("#745039"))
	# Wide oval brim with lifted sides; pinched crown is unlike the tricorn.
	_loft(s, Vector3(0, 3.11, 0), [Vector3(0, 0.69, 0.415),
		Vector3(0.04, 0.745, 0.45), Vector3(0.105, 0.71, 0.43)], hat, 0, 12)
	_loft(s, Vector3(0, 3.17, -0.025), [Vector3(0, 0.40, 0.315),
		Vector3(0.10, 0.415, 0.315), Vector3(0.32, 0.34, 0.255),
		Vector3(0.38, 0.28, 0.21)], hat)
	_loft(s, Vector3(0, 3.20, -0.025), [Vector3(0, 0.416, 0.322),
		Vector3(0.077, 0.416, 0.322)], Color("#78503a"), 1)
	# Relief crease across the top suggests a pinched felt crown.
	_link(s, Vector3(-0.18, 3.55, 0.025), Vector3(0.18, 3.55, 0.025),
		0.018, 0.018, Color("#a47443"), 1, 0.60)
	_loft(s, Vector3(0.43, 0, 0.07), [Vector3(0.77, 0.09, 0.09),
		Vector3(0.86, 0.14, 0.12), Vector3(1.33, 0.14, 0.12)], Color("#815333"), 0, 8,
		Vector3(0, 0, -0.10))
	_link(s, Vector3(0.48, 1.24, 0.06), Vector3(0.53, 1.48, 0.06), 0.058, 0.06, Color("#5a4a42"), 1)
	# Sheriff-like brass badge, deliberately a simple painted geometric inlay.
	_badge(s, [Vector3(-0.245, 1.99, 0.29), Vector3(-0.175, 1.92, 0.301),
		Vector3(-0.245, 1.85, 0.31), Vector3(-0.315, 1.92, 0.301)], 0.022, BRASS)
