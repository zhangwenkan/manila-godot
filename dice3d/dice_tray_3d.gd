extends Node3D

const TRAY_SHADER = preload("res://dice3d/dice_tray.gdshader")
const SEGMENTS := 32
const RIM_HEIGHT := 0.46

var radii := Vector2(6.0, 3.0)
var _body: StaticBody3D
var _surface: MeshInstance3D
var _floor_collision: CollisionShape3D
var _rim_collisions: Array[CollisionShape3D] = []
var _wood: ImageTexture
var _felt: ImageTexture


func _ready() -> void:
	_wood = _make_wood_texture()
	_felt = _make_felt_texture()
	_body = StaticBody3D.new()
	_body.name = "TrayCollision"
	add_child(_body)
	_floor_collision = CollisionShape3D.new()
	_body.add_child(_floor_collision)
	for i in SEGMENTS:
		var wall := CollisionShape3D.new()
		wall.shape = BoxShape3D.new()
		_body.add_child(wall)
		_rim_collisions.append(wall)
	_surface = MeshInstance3D.new()
	_surface.name = "WoodRimAndCanvas"
	add_child(_surface)


func configure(new_radii: Vector2) -> void:
	if new_radii.is_equal_approx(radii) and _surface.mesh != null:
		return
	radii = new_radii
	var floor_points := PackedVector3Array()
	for i in SEGMENTS:
		var a := _ellipse_point(i, 0.0, 0.0)
		var b := _ellipse_point(i + 1, 0.0, 0.0)
		floor_points.append(a)
		floor_points.append(a - Vector3.UP * 0.30)
		var wall := _rim_collisions[i]
		var edge := b - a
		wall.position = (a + b) * 0.5 + Vector3.UP * RIM_HEIGHT * 0.5
		wall.rotation.y = -atan2(edge.z, edge.x)
		(wall.shape as BoxShape3D).size = Vector3(edge.length() + 0.06, RIM_HEIGHT, 0.12)
	var floor_shape := ConvexPolygonShape3D.new()
	floor_shape.points = floor_points
	_floor_collision.shape = floor_shape
	_surface.mesh = _make_mesh()


func contains_point(point: Vector3, margin: float = 0.0) -> bool:
	var local := to_local(point)
	return Vector2(local.x / (radii.x - margin), local.z / (radii.y - margin)).length_squared() <= 1.0


func _ellipse_point(index: int, extra: float, height: float) -> Vector3:
	var angle := TAU * float(index) / SEGMENTS
	return Vector3(cos(angle) * (radii.x + extra), height, sin(angle) * (radii.y + extra))


func _make_mesh() -> ArrayMesh:
	var mesh := ArrayMesh.new()
	var vertices := PackedVector3Array([Vector3.ZERO])
	var uvs := PackedVector2Array([Vector2(0.5, 0.5)])
	var indices := PackedInt32Array()
	for i in SEGMENTS:
		var point := _ellipse_point(i, 0.0, 0.0)
		vertices.append(point)
		uvs.append(Vector2(point.x / radii.x, point.z / radii.y) * 0.5 + Vector2.ONE * 0.5)
		indices.append_array(PackedInt32Array([0, (i + 1) % SEGMENTS + 1, i + 1]))
	_add_surface(mesh, vertices, uvs, indices, _material(_felt, Color.WHITE))
	_add_ring(mesh, -0.045, 0.005, 0.02, 0.015, Color("#253d38"))
	_add_ring(mesh, 0.0, 0.01, 0.10, RIM_HEIGHT - 0.05, Color("#705444"))
	_add_ring(mesh, 0.10, RIM_HEIGHT - 0.05, 0.15, RIM_HEIGHT, Color("#d0ae78"))
	_add_ring(mesh, 0.15, RIM_HEIGHT, 0.35, RIM_HEIGHT, Color("#ba9363"))
	_add_ring(mesh, 0.35, RIM_HEIGHT, 0.40, RIM_HEIGHT - 0.06, Color("#795a42"))
	_add_ring(mesh, 0.40, RIM_HEIGHT - 0.06, 0.37, -0.19, Color("#765343"))
	_add_ring(mesh, 0.37, -0.19, 0.33, -0.25, Color("#302f32"))
	return mesh


func _add_ring(mesh: ArrayMesh, inner_extra: float, inner_y: float, outer_extra: float, outer_y: float, color: Color) -> void:
	var vertices := PackedVector3Array()
	var uvs := PackedVector2Array()
	var colors := PackedColorArray()
	var indices := PackedInt32Array()
	for i in range(SEGMENTS + 1):
		vertices.append(_ellipse_point(i, inner_extra, inner_y))
		vertices.append(_ellipse_point(i, outer_extra, outer_y))
		uvs.append(Vector2(float(i) / 4.0, 0.0))
		uvs.append(Vector2(float(i) / 4.0, 1.0))
		var shade := 0.84 + 0.16 * cos(TAU * float(i) / SEGMENTS + 0.8)
		colors.append(Color(shade, shade, shade))
		colors.append(Color(shade, shade, shade))
		if i < SEGMENTS:
			var start := i * 2
			indices.append_array(PackedInt32Array([start, start + 2, start + 1, start + 1, start + 2, start + 3]))
	_add_surface(mesh, vertices, uvs, indices, _material(_wood, color), colors)


func _add_surface(mesh: ArrayMesh, vertices: PackedVector3Array, uvs: PackedVector2Array, indices: PackedInt32Array, material: Material, colors := PackedColorArray()) -> void:
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	var normals := PackedVector3Array()
	normals.resize(vertices.size())
	normals.fill(Vector3.UP)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	# Godot uses clockwise front faces; keep the receiving side facing the light.
	for triangle in range(0, indices.size(), 3):
		var second := indices[triangle + 1]
		indices[triangle + 1] = indices[triangle + 2]
		indices[triangle + 2] = second
	arrays[Mesh.ARRAY_INDEX] = indices
	if not colors.is_empty():
		arrays[Mesh.ARRAY_COLOR] = colors
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh.surface_set_material(mesh.get_surface_count() - 1, material)


func _material(texture: ImageTexture, color: Color) -> ShaderMaterial:
	var material := ShaderMaterial.new()
	material.shader = TRAY_SHADER
	material.set_shader_parameter("surface_texture", texture)
	material.set_shader_parameter("tint", color)
	return material


func _make_wood_texture() -> ImageTexture:
	var image := Image.create(64, 32, false, Image.FORMAT_RGB8)
	var rng := RandomNumberGenerator.new()
	rng.seed = 613
	for y in 32:
		for x in 64:
			var shade := 0.91 + float(rng.randi_range(0, 3)) * 0.03
			if y % 7 == 0 and (x + y * 3) % 21 < 16:
				shade *= 0.85
			if x < 1:
				shade *= 0.65
			image.set_pixel(x, y, Color(shade, shade, shade))
	return ImageTexture.create_from_image(image)


func _make_felt_texture() -> ImageTexture:
	var image := Image.create(256, 256, false, Image.FORMAT_RGB8)
	var rng := RandomNumberGenerator.new()
	rng.seed = 906
	for y in 256:
		for x in 256:
			var color := Color("#376660")
			color = color.lightened(float(rng.randi_range(0, 2)) * 0.015)
			if (x + y) % 4 == 0:
				color = color.darkened(0.035)
			var offset := Vector2(x - 128, y - 128)
			var distance := offset.length()
			var angle := atan2(offset.y, offset.x)
			if absf(distance - 116.0) < 0.6 and int((angle + PI) * 72.0) % 5 < 3:
				color = Color("#8a9b7e")
			# A worn compass rose and stitch ring belong to the tray's canvas lining.
			var rose := offset / Vector2(27.0, 42.0)
			if absf(rose.x) + absf(rose.y) < 1.0:
				color = Color("#4c7770") if rose.x * rose.y > 0.0 else Color("#6b8d7c")
			if absf(distance - 35.0) < 0.6:
				color = Color("#638579")
			image.set_pixel(x, y, color)
	return ImageTexture.create_from_image(image)
