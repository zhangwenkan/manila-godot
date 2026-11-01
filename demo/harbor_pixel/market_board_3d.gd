extends Node3D
## A tabletop price instrument: real tracks, inset scales and sculpted cargo pieces.

const SURFACE = preload("res://demo/harbor_pixel/market_surface.gdshader")
const FONT = preload("res://card/fonts/fusion-pixel-12px-proportional-zh_hans.otf")
const GOODS = ["nutmeg", "silk", "ginseng", "jade"]
const NAMES = ["肉豆蔻", "丝绸", "人参", "翡翠"]
const VALUES = [0, 5, 10, 20, 30]
const ACCENTS = [Color("b85a3a"), Color("5080b8"), Color("d9b84e"), Color("4a8a5e")]
const FACE_NORMALS = [Vector3.UP, Vector3.BACK, Vector3.RIGHT, Vector3.LEFT, Vector3.FORWARD, Vector3.DOWN]
const WOOD = Color("a27a51")
const FELT = Color("376660")
const IVORY = Color("e1d3a5")

var _grain: ImageTexture
var _outline_material: StandardMaterial3D
var _materials: Dictionary = {}


static func marker_position(column: int, price_index: int) -> Vector3:
	return Vector3(-3.35 + price_index * 1.88, 0.045, -3.35 + column * 2.25)


func _ready() -> void:
	name = "MarketTabletop"
	_grain = _make_grain()
	_outline_material = StandardMaterial3D.new()
	_outline_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_outline_material.albedo_color = Color("203a35")
	_outline_material.cull_mode = BaseMaterial3D.CULL_FRONT
	_outline_material.grow = true
	_outline_material.grow_amount = 0.012
	_build_tray()
	_build_title()
	for column in GOODS.size():
		_build_track(column)
		var piece := Node3D.new()
		piece.name = "Marker_" + GOODS[column]
		piece.set_meta("cargo_id", GOODS[column])
		add_child(piece)
		piece.position = marker_position(column, 0)
		match GOODS[column]:
			"nutmeg": _nutmeg(piece)
			"silk": _silk(piece)
			"ginseng": _ginseng(piece)
			"jade": _jade(piece)


func _build_tray() -> void:
	_box(self, "WalnutFoot", Vector3(12.55, 0.42, 10.45), Vector3(0, -0.51, 0), Color("5c4a3e"), 0.16, true)
	_box(self, "CanvasBed", Vector3(11.82, 0.13, 9.73), Vector3(0, -0.15, 0), FELT, 0.06, true)
	var mesh := ArrayMesh.new()
	# The cross-section, rather than a texture bevel, supplies the rim's thickness.
	var profiles := [
		Vector4(12.55, 10.45, 0.65, -0.55), Vector4(12.75, 10.65, 0.75, -0.43),
		Vector4(12.75, 10.65, 0.75, 0.02), Vector4(12.64, 10.54, 0.70, 0.12),
		Vector4(12.51, 10.41, 0.65, 0.38), Vector4(12.39, 10.29, 0.59, 0.42),
		Vector4(11.92, 9.82, 0.39, 0.42), Vector4(11.81, 9.71, 0.33, 0.32),
		Vector4(11.76, 9.66, 0.31, -0.08),
	]
	var bands := [Color("303833"), Color("826149"), Color("5d493a"), Color("98734e"),
		Color("d0ae78"), Color("ba9363"), Color("e0bf85"), Color("66543f")]
	for ring in range(profiles.size() - 1):
		_rim_band(mesh, profiles[ring], profiles[ring + 1], bands[ring])
	_instance(self, "SculptedTrayRim", mesh)
	for x in [-6.10, 6.10]:
		for z in [-3.60, 3.60]:
			_ellipsoid(self, "RimPin", Vector3(0.065, 0.025, 0.065), Vector3(x, 0.424, z), IVORY, false)
	# Subtle stitched border, like the dice tray's printed compass surround.
	for x in range(47):
		for z in [-4.55, 4.55]:
			_box(self, "CanvasStitch", Vector3(0.09, 0.008, 0.018), Vector3(-5.65 + x * 0.245, -0.076, z), Color("819680"), 0.003, false, false)


func _build_title() -> void:
	for x in [-1.72, 1.72]:
		_box(self, "SignMount", Vector3(0.14, 0.55, 0.16), Vector3(x, 0.45, -4.85), Color("6b5642"), 0.035)
	_box(self, "MarketSign", Vector3(4.40, 0.78, 0.24), Vector3(0, 0.86, -4.80), WOOD, 0.13, true)
	_box(self, "SignInset", Vector3(3.99, 0.51, 0.035), Vector3(0, 0.87, -4.662), Color("294b44"), 0.015)
	_text(self, "MarketTitle", "股票市值", Vector3(0, 0.88, -4.631), 0.012, IVORY, 0.0)
	for x in [-1.80, 1.80]:
		_ellipsoid(self, "SignPin", Vector3(0.045, 0.045, 0.022), Vector3(x, 0.88, -4.63), IVORY, false)


func _build_track(column: int) -> void:
	var z := marker_position(column, 0).z
	var accent: Color = ACCENTS[column]
	var track := Node3D.new()
	track.name = "Track_" + GOODS[column]
	add_child(track)
	# Two wooden shoulders stand above a dark recessed channel.
	_box(track, "RecessedChannel", Vector3(9.52, 0.06, 1.14), Vector3(0.41, -0.04, z), Color("203d37"), 0.028)
	for dz in [-0.56, 0.57]:
		_box(track, "TrackShoulder", Vector3(9.63, 0.15, 0.12), Vector3(0.41, 0.005, z + dz), Color("897049"), 0.045, true, false)
		_box(track, "TrackInlay", Vector3(9.51, 0.017, 0.027), Vector3(0.41, 0.088, z + dz), Color("cfb67b"), 0.008, false, false)
	for index in VALUES.size():
		var x := marker_position(column, index).x
		_box(track, "CargoRest_" + str(VALUES[index]), Vector3(1.30, 0.055, 0.91), Vector3(x, 0.016, z), FELT.darkened(0.06), 0.025)
		# The scale is in front of the cargo, so even a tall piece cannot cover its value.
		var plaque := _box(track, "PricePlaque_" + str(VALUES[index]), Vector3(0.66, 0.36, 0.09), Vector3(x - 0.70, 0.045, z + 0.79), Color("284941"), 0.04)
		plaque.rotation.x = deg_to_rad(-48)
		var ink := _text(track, "Price_" + str(VALUES[index]), str(VALUES[index]), plaque.position + plaque.basis.z * 0.052, 0.008, IVORY, -48)
		ink.set_meta("price", VALUES[index])
		_box(track, "PriceNotch", Vector3(0.045, 0.012, 0.14), Vector3(x, 0.105, z + 0.60), accent.lightened(0.28), 0.006, false, false)
	var badge := _box(track, "CargoNameplate", Vector3(1.31, 0.46, 0.16), Vector3(-5.02, 0.10, z + 0.20), accent, 0.07)
	badge.rotation.x = deg_to_rad(-38)
	_text(track, "CargoName", NAMES[column], badge.position + badge.basis.z * 0.09, 0.008, Color("f3e6be"), -38)


func _nutmeg(piece: Node3D) -> void:
	var whole := _ellipsoid(piece, "NutmegShell", Vector3(0.29, 0.47, 0.29), Vector3(-0.21, 0.48, -0.05), Color("95502f"))
	whole.rotation.z = -0.22
	# Broad longitudinal seams follow the three-dimensional nut, not an icon plane.
	for angle in [-1.70, -0.95, -0.20, 0.55]:
		var points := PackedVector3Array()
		for step in 15:
			var phi := 0.18 + float(step) / 14.0 * (PI - 0.36)
			var p := Vector3(0.293 * sin(phi) * sin(angle), 0.473 * cos(phi), 0.293 * sin(phi) * cos(angle))
			points.append(whole.transform * p)
		_tube(piece, "ShellSeam", points, 0.012, Color("673c2b"), false)
	var cut := Node3D.new()
	cut.name = "NutmegCut"
	piece.add_child(cut)
	cut.position = Vector3(0.24, 0.34, 0.14)
	cut.rotation = Vector3(deg_to_rad(22), 0, deg_to_rad(-12))
	_ellipsoid(cut, "CutShell", Vector3(0.31, 0.34, 0.18), Vector3.ZERO, Color("70432b"))
	_ellipsoid(cut, "CutSeed", Vector3(0.265, 0.293, 0.035), Vector3(0, 0, 0.169), Color("d7a969"), false)
	for offset in [-0.12, 0.02, 0.14]:
		var points := PackedVector3Array()
		for i in 10:
			var y := -0.20 + i * 0.043
			points.append(Vector3(offset + 0.028 * sin(i * 1.8), y, 0.201))
		_tube(cut, "SeedMarbling", points, 0.012, Color("895333"), false)


func _silk(piece: Node3D) -> void:
	_box(piece, "FoldedCloth", Vector3(0.91, 0.16, 0.68), Vector3(0, 0.09, 0.11), Color("5080b8"), 0.07)
	_box(piece, "ClothFold", Vector3(0.85, 0.12, 0.40), Vector3(0, 0.20, 0.26), Color("86b4d2"), 0.05)
	var roll := _cylinder(piece, "SilkRoll", 0.285, 0.99, Vector3(0, 0.42, -0.08), Color("76a9cc"))
	roll.rotation.z = PI * 0.5
	for x in [-0.504, 0.504]:
		var spiral := PackedVector3Array()
		for i in 65:
			var angle := float(i) / 64.0 * TAU * 2.2
			var radius := 0.025 + float(i) / 64.0 * 0.215
			spiral.append(Vector3(x, 0.42 + sin(angle) * radius, -0.08 + cos(angle) * radius))
		_tube(piece, "RolledSelvedge", spiral, 0.018, Color("d1e2df"), false)
	var band := PackedVector3Array()
	for i in 25:
		var angle := float(i) / 24.0 * TAU
		band.append(Vector3(0.13, 0.42 + sin(angle) * 0.299, -0.08 + cos(angle) * 0.299))
	_tube(piece, "SilkBinding", band, 0.038, Color("dfbc75"), false)
	_box(piece, "BindingTail", Vector3(0.075, 0.025, 0.36), Vector3(0.13, 0.273, 0.32), Color("dfbc75"), 0.01, false, false)


func _ginseng(piece: Node3D) -> void:
	var root := Color("d8b165")
	var body := _ellipsoid(piece, "GinsengRoot", Vector3(0.18, 0.30, 0.16), Vector3(0, 0.53, 0), root)
	body.rotation.z = -0.16
	_tube(piece, "LeftRoot", PackedVector3Array([Vector3(-0.07, 0.35, 0), Vector3(-0.19, 0.23, 0.02), Vector3(-0.27, 0.07, 0.14), Vector3(-0.40, 0.035, 0.21)]), 0.068, root)
	_tube(piece, "RightRoot", PackedVector3Array([Vector3(0.07, 0.35, 0), Vector3(0.20, 0.23, 0.05), Vector3(0.18, 0.08, 0.18), Vector3(0.32, 0.035, 0.25)]), 0.063, root)
	for side in [-1.0, 1.0]:
		_tube(piece, "BranchRoot", PackedVector3Array([Vector3(side * 0.12, 0.59, 0), Vector3(side * 0.27, 0.46, 0), Vector3(side * 0.39, 0.50, 0.03)]), 0.043, root)
	_tube(piece, "Stem", PackedVector3Array([Vector3(0, 0.72, 0), Vector3(0.025, 0.90, -0.02)]), 0.031, Color("70944e"))
	for side in [-1.0, 1.0]:
		var leaf := _ellipsoid(piece, "Leaf", Vector3(0.19, 0.075, 0.10), Vector3(side * 0.13, 0.88, 0), Color("709c55"))
		leaf.rotation.z = side * 0.55
	for y in [0.43, 0.53, 0.63]:
		_tube(piece, "RootRing", PackedVector3Array([Vector3(-0.105, y + 0.025, 0.128), Vector3(0, y, 0.167), Vector3(0.11, y + 0.01, 0.126)]), 0.010, Color("a17e47"), false)


func _jade(piece: Node3D) -> void:
	var mesh := TorusMesh.new()
	mesh.inner_radius = 0.18
	mesh.outer_radius = 0.47
	mesh.rings = 48
	mesh.ring_segments = 20
	mesh.material = _material(Color("63a67c"))
	var ring := _instance(piece, "JadeBi", mesh)
	ring.position = Vector3(0, 0.47, 0)
	ring.rotation.x = deg_to_rad(77)
	var cord := PackedVector3Array([Vector3(-0.04, 0.83, -0.08), Vector3(-0.07, 1.00, -0.07), Vector3(0.06, 1.035, -0.06), Vector3(0.13, 0.91, -0.03), Vector3(0.07, 0.84, -0.06)])
	_tube(piece, "JadeCord", cord, 0.023, Color("d9ba74"))
	var vein := PackedVector3Array()
	for i in 20:
		var angle := 0.12 + float(i) / 19.0 * 1.75
		var local := Vector3(cos(angle) * 0.35, -0.133, sin(angle) * 0.35)
		vein.append(ring.transform * local)
	_tube(piece, "JadeCarving", vein, 0.014, Color("b4d4a3"), false)


func _material(color: Color, face := Vector3.ZERO, wood := false, outlined := true) -> ShaderMaterial:
	var key := str(color) + str(face) + str(wood) + str(outlined)
	if _materials.has(key):
		return _materials[key]
	var material := ShaderMaterial.new()
	material.shader = SURFACE
	material.set_shader_parameter("top_color", color.lightened(0.22))
	material.set_shader_parameter("base_color", color)
	material.set_shader_parameter("side_color", color.darkened(0.32))
	material.set_shader_parameter("face_axis", face)
	material.set_shader_parameter("use_grain", wood)
	material.set_shader_parameter("grain", _grain)
	material.set_shader_parameter("grain_scale", Vector2(4, 1))
	if outlined:
		material.next_pass = _outline_material
	_materials[key] = material
	return material


func _box(parent: Node3D, title: String, dimensions: Vector3, location: Vector3, color: Color, radius := 0.08, wood := false, outlined := true) -> MeshInstance3D:
	# The same rounded-box construction as the dice, generalized to non-cubic pieces.
	var mesh := ArrayMesh.new()
	var half := dimensions * 0.5
	radius = minf(radius, minf(half.x, minf(half.y, half.z)) * 0.98)
	var core := half - Vector3.ONE * radius
	const STEPS := 12
	for face: Vector3 in FACE_NORMALS:
		var u := Vector3.RIGHT if absf(face.y) > 0.5 else Vector3.UP.cross(face)
		var v := face.cross(u)
		var vertices := PackedVector3Array()
		var normals := PackedVector3Array()
		var uvs := PackedVector2Array()
		var indices := PackedInt32Array()
		for y in range(STEPS + 1):
			for x in range(STEPS + 1):
				var uv := Vector2(x, y) / float(STEPS)
				var cube := (face + u * (uv.x - 0.5) * 2.0 + v * (uv.y - 0.5) * 2.0) * half
				var nearest := cube.clamp(-core, core)
				var normal := (cube - nearest).normalized()
				vertices.append(nearest + normal * radius)
				normals.append(normal)
				uvs.append(uv)
				if x < STEPS and y < STEPS:
					var a := y * (STEPS + 1) + x
					var b := a + STEPS + 1
					indices.append_array(PackedInt32Array([a, b, a + 1, a + 1, b, b + 1]))
		_surface(mesh, vertices, normals, uvs, indices, _material(color, face, wood, outlined))
	var object := _instance(parent, title, mesh)
	object.position = location
	return object


func _ellipsoid(parent: Node3D, title: String, radii: Vector3, location: Vector3, color: Color, outlined := true) -> MeshInstance3D:
	var mesh := SphereMesh.new()
	mesh.radius = 1.0
	mesh.height = 2.0
	mesh.radial_segments = 40
	mesh.rings = 24
	mesh.material = _material(color, Vector3.ZERO, false, outlined)
	var object := _instance(parent, title, mesh)
	object.scale = radii
	object.position = location
	return object


func _cylinder(parent: Node3D, title: String, radius: float, height: float, location: Vector3, color: Color) -> MeshInstance3D:
	var mesh := CylinderMesh.new()
	mesh.top_radius = radius
	mesh.bottom_radius = radius
	mesh.height = height
	mesh.radial_segments = 48
	mesh.material = _material(color)
	var object := _instance(parent, title, mesh)
	object.position = location
	return object


func _tube(parent: Node3D, title: String, points: PackedVector3Array, radius: float, color: Color, outlined := true) -> void:
	var mesh := ArrayMesh.new()
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()
	var indices := PackedInt32Array()
	const SIDES := 10
	for i in points.size():
		var tangent := (points[mini(i + 1, points.size() - 1)] - points[maxi(i - 1, 0)]).normalized()
		var u := tangent.cross(Vector3.UP if absf(tangent.y) < 0.9 else Vector3.RIGHT).normalized()
		var v := tangent.cross(u)
		for side in range(SIDES + 1):
			var angle := TAU * float(side) / SIDES
			var normal := u * cos(angle) + v * sin(angle)
			vertices.append(points[i] + normal * radius)
			normals.append(normal)
			uvs.append(Vector2(float(side) / SIDES, float(i) / points.size()))
			if i < points.size() - 1 and side < SIDES:
				var a := i * (SIDES + 1) + side
				var b := a + SIDES + 1
				indices.append_array(PackedInt32Array([a, b, a + 1, a + 1, b, b + 1]))
	_surface(mesh, vertices, normals, uvs, indices, _material(color, Vector3.ZERO, false, outlined))
	_instance(parent, title, mesh)


func _text(parent: Node3D, title: String, text: String, location: Vector3, pixel_size: float, color: Color, angle: float) -> MeshInstance3D:
	var mesh := TextMesh.new()
	mesh.font = FONT
	mesh.font_size = 48
	mesh.pixel_size = pixel_size
	mesh.text = text
	mesh.depth = 0.008
	mesh.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	mesh.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	var ink := StandardMaterial3D.new()
	ink.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	ink.albedo_color = color
	mesh.material = ink
	var object := _instance(parent, title, mesh)
	object.position = location
	object.rotation.x = deg_to_rad(angle)
	object.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return object


func _rim_point(profile: Vector4, index: int) -> Vector3:
	var corner := int(index / 16.0)
	var angle := corner * PI * 0.5 + (index % 16) * PI / 32.0
	var center := Vector2(1 if corner == 0 or corner == 3 else -1, 1 if corner < 2 else -1) * (Vector2(profile.x, profile.y) * 0.5 - Vector2.ONE * profile.z)
	var point := center + Vector2(cos(angle), sin(angle)) * profile.z
	return Vector3(point.x, profile.w, point.y)


func _rim_band(mesh: ArrayMesh, a: Vector4, b: Vector4, color: Color) -> void:
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()
	var indices := PackedInt32Array()
	for i in range(65):
		var p := _rim_point(a, i % 64)
		var q := _rim_point(b, i % 64)
		var next := _rim_point(a, (i + 1) % 64)
		var tangent := (next - p).normalized()
		var normal := (q - p).cross(tangent).normalized()
		vertices.append_array(PackedVector3Array([p, q]))
		normals.append_array(PackedVector3Array([normal, normal]))
		uvs.append_array(PackedVector2Array([Vector2(float(i) / 8, 0), Vector2(float(i) / 8, 1)]))
		if i < 64:
			var n := i * 2
			indices.append_array(PackedInt32Array([n, n + 2, n + 1, n + 1, n + 2, n + 3]))
	_surface(mesh, vertices, normals, uvs, indices, _material(color, Vector3.ZERO, true, false))


func _make_grain() -> ImageTexture:
	var image := Image.create(128, 64, false, Image.FORMAT_RGB8)
	for y in 64:
		for x in 128:
			var shade := 0.96 + 0.025 * sin(y * 0.70 + sin(x * 0.06))
			if y % 13 == 0 and (x + y) % 27 < 19:
				shade -= 0.065
			image.set_pixel(x, y, Color(shade, shade, shade))
	return ImageTexture.create_from_image(image)


func _instance(parent: Node3D, title: String, mesh: Mesh) -> MeshInstance3D:
	var object := MeshInstance3D.new()
	object.name = title
	object.mesh = mesh
	parent.add_child(object)
	return object


func _surface(mesh: ArrayMesh, vertices: PackedVector3Array, normals: PackedVector3Array, uvs: PackedVector2Array, indices: PackedInt32Array, material: Material) -> void:
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_INDEX] = indices
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh.surface_set_material(mesh.get_surface_count() - 1, material)
