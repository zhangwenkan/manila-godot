extends RefCounted
## Selection furniture, deliberately independent of the dice tray.


static func bench(width: float) -> ArrayMesh:
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	var woods: Array[Color] = [Color("b58653"), Color("c39660"), Color("a87749")]
	for plank in 3:
		var z := (plank - 1) * 0.27
		var mesh := _slab(Vector2(width * 0.5, 0.125), 0.0, 0.14, 0.08,
			woods[plank], woods[plank].darkened(0.24), woods[plank].lightened(0.12))
		surface.append_from(mesh, 0, Transform3D(Basis.IDENTITY, Vector3(0, 0, z)))
		# Fine inlaid grain runs along the planks, not across the whole screen.
		for line in 2:
			var grain := _slab(Vector2(width * (0.36 if line == 0 else 0.27), 0.006), 0.003, 0.003, 0.0,
				woods[plank].darkened(0.13), woods[plank], woods[plank])
			surface.append_from(grain, 0, Transform3D(Basis.IDENTITY, Vector3(width * (0.04 if line == 0 else -0.08), 0, z - 0.05 + line * 0.09)))
	var leg_x := width * 0.5 - 0.38
	for side: float in [-1.0, 1.0]:
		for z in [-0.24, 0.24]:
			var leg := _slab(Vector2(0.095, 0.10), -0.13, 0.79, 0.025,
				Color("997247"), Color("634c35"), Color("ad8050"))
			surface.append_from(leg, 0, Transform3D(Basis.IDENTITY, Vector3(side * leg_x, 0, z)))
		var brace := _slab(Vector2(0.14, 0.38), -0.67, 0.12, 0.035,
			Color("936a42"), Color("604932"), Color("ad8050"))
		surface.append_from(brace, 0, Transform3D(Basis.IDENTITY, Vector3(side * leg_x, 0, 0)))
	var rail := _slab(Vector2(leg_x, 0.07), -0.45, 0.13, 0.025,
		Color("936a42"), Color("715336"), Color("ad8050"))
	surface.append_from(rail, 0, Transform3D.IDENTITY)
	var result := surface.commit()
	var material := ShaderMaterial.new()
	material.shader = preload("res://character_preview/pawn.gdshader")
	material.set_shader_parameter("matte", true)
	result.surface_set_material(0, material)
	result.set_meta("seat_height", 0.0)
	result.set_meta("seat_count", 3)
	return result


static func seat_marker() -> ArrayMesh:
	return _slab(Vector2(0.29, 0.018), -0.045, 0.075, 0.01,
		Color("f0d79a"), Color("dbc085"), Color("f7e4b3"))


static func board(half_size: Vector2) -> ArrayMesh:
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	var inset := minf(0.12, minf(half_size.x, half_size.y) * 0.08)
	var rings: Array[PackedVector3Array] = [
		_capsule_outline(half_size - Vector2.ONE * inset, 0.0),
		_capsule_outline(half_size, -0.12),
		_capsule_outline(half_size, -0.46),
		_capsule_outline(half_size - Vector2.ONE * inset * 0.8, -0.55),
		_capsule_outline(half_size - Vector2.ONE * inset * 0.8, -0.62)]
	var colors: Array[Color] = [Color("c2bdb1"), Color("71747a"), Color("41454d"), Color("292d34")]
	for i in rings[0].size():
		var j := (i + 1) % rings[0].size()
		_triangle(surface, Vector3.ZERO, rings[0][i], rings[0][j], Color("aaa99e"))
		for layer in rings.size() - 1:
			_triangle(surface, rings[layer][i], rings[layer + 1][i], rings[layer][j], colors[layer])
			_triangle(surface, rings[layer][j], rings[layer + 1][i], rings[layer + 1][j], colors[layer])
		_triangle(surface, Vector3(0, -0.62, 0), rings[-1][j], rings[-1][i], Color("292d34"))
	var mesh := surface.commit()
	var material := StandardMaterial3D.new()
	material.vertex_color_use_as_albedo = true
	material.roughness = 0.62
	material.metallic_specular = 0.32
	mesh.surface_set_material(0, material)
	return mesh


static func _capsule_outline(half_size: Vector2, y: float) -> PackedVector3Array:
	# Compensate the fixed display camera's ground foreshortening.
	var projected := Vector2(half_size.x, half_size.y * 0.6)
	var along_x := projected.x >= projected.y
	var radius := minf(projected.x, projected.y)
	var span := absf(projected.x - projected.y)
	var points := PackedVector3Array()
	for end in 2:
		for segment in 9:
			var angle := -PI * 0.5 + PI * (float(segment) / 8.0 + end)
			var point := Vector2(cos(angle) * radius + (span if end == 0 else -span), sin(angle) * radius)
			if not along_x:
				point = Vector2(-point.y, point.x)
			points.append(Vector3(point.x, y, point.y / 0.6))
	return points


static func supported_point(point: Vector3, half_size: Vector2, clearance: float) -> Vector3:
	var half := Vector2(half_size.x, half_size.y * 0.6)
	var p := Vector2(point.x, point.z * 0.6)
	var along_x := half.x >= half.y
	var span := absf(half.x - half.y)
	var nearest := Vector2(clampf(p.x, -span, span), 0) if along_x else Vector2(0, clampf(p.y, -span, span))
	# Inscribed polygon radius also protects the straight facets between arc vertices.
	var radius := maxf(0.01, minf(half.x, half.y) * cos(PI / 16.0) - clearance)
	p = nearest + (p - nearest).limit_length(radius)
	return Vector3(p.x, point.y, p.y / 0.6)


static func choice_base(radius: float) -> ArrayMesh:
	return _slab(Vector2(radius, radius * 0.70), 0.08, 0.08, radius * 0.32,
		Color("464950"), Color("30333a"), Color("8d9299"))


static func display_base(radius: float) -> ArrayMesh:
	return _slab(Vector2(radius, radius * 0.76), 0.0, 0.17, radius * 0.38,
		Color("56585e"), Color("282b31"), Color("babdc4"))


static func marker(radius: float) -> ArrayMesh:
	return _slab(Vector2(radius, radius * 0.70), 0.0, 0.025, radius * 0.32,
		Color("e2dfd8"), Color("797d85"), Color("c8cbd1"))


static func _outline(half_size: Vector2, cut: float, y: float) -> PackedVector3Array:
	var x := half_size.x
	var z := half_size.y
	var c := minf(cut, minf(x, z) * 0.6)
	return PackedVector3Array([Vector3(-x + c, y, -z), Vector3(x - c, y, -z),
		Vector3(x, y, -z + c), Vector3(x, y, z - c), Vector3(x - c, y, z),
		Vector3(-x + c, y, z), Vector3(-x, y, z - c), Vector3(-x, y, -z + c)])


static func _slab(half_size: Vector2, top: float, depth: float, cut: float,
		face_color: Color, side_color: Color, bevel_color: Color) -> ArrayMesh:
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	var inset := minf(0.045, half_size.y * 0.10)
	var top_edge := _outline(half_size - Vector2.ONE * inset, cut, top)
	var shoulder := _outline(half_size, cut, top - inset)
	var bottom := _outline(half_size, cut, top - depth)
	for i in top_edge.size():
		var j := (i + 1) % top_edge.size()
		_triangle(surface, Vector3(0, top, 0), top_edge[i], top_edge[j], face_color)
		_triangle(surface, top_edge[i], shoulder[i], top_edge[j], bevel_color)
		_triangle(surface, top_edge[j], shoulder[i], shoulder[j], bevel_color)
		_triangle(surface, shoulder[i], bottom[i], shoulder[j], side_color)
		_triangle(surface, shoulder[j], bottom[i], bottom[j], side_color)
		_triangle(surface, Vector3(0, top - depth, 0), bottom[j], bottom[i], side_color)
	var mesh := surface.commit()
	var material := StandardMaterial3D.new()
	material.vertex_color_use_as_albedo = true
	material.roughness = 0.78
	material.metallic_specular = 0.25
	mesh.surface_set_material(0, material)
	return mesh


static func _triangle(surface: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, color: Color) -> void:
	var normal := -(b - a).cross(c - a).normalized()
	for point in [a, b, c]:
		surface.set_normal(normal)
		surface.set_color(color.srgb_to_linear())
		surface.add_vertex(point)
