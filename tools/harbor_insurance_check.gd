extends SceneTree

const World := preload("res://demo/harbor_hd2d/harbor_world.gd")
const Asset := preload("res://demo/harbor_hd2d/art/insurance_rebuild_r2/insurance_rebuild_r2_1.glb")

var world: Node3D
var model: Node3D
var checks := 0
var failures: Array[String] = []
var preview := false
var output_dir := "user://harbor_insurance_v5"
var _finished := false
var _structure_complete := false
var _preview_complete := false


func _initialize() -> void:
	preview = "--preview" in OS.get_cmdline_user_args()
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):
			output_dir = arg.trim_prefix("--output=")
	_run.call_deferred()


func _run() -> void:
	create_timer(60.0).timeout.connect(func():
		if not _finished:
			failures.append("60 second insurance watchdog expired")
			_finish())
	if preview and DisplayServer.get_name() == "headless":
		failures.append("Insurance preview requires a real display")
		_finish()
		return
	root.content_scale_size = Vector2i(1600, 1000)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.size = Vector2i(1200, 750)
	world = World.new()
	root.add_child(world)
	model = world.get_node("InsuranceBlender")
	await process_frame
	_structure_checks()
	_check(_structure_complete, "structure checks completed")
	if preview and failures.is_empty():
		await _preview()
		_check(_preview_complete, "preview completed")
	_finish()


func _structure_checks() -> void:
	var meshes := model.find_children("*", "MeshInstance3D", true, false)
	_check(meshes.size() == 6, "runtime keeps six consolidated model groups after atlas batching")
	var materials: Dictionary = {}
	var textures: Dictionary = {}
	var triangles := 0
	for instance: MeshInstance3D in meshes:
		_check(instance.material_override == null, "no atlas override on imported mesh")
		triangles += instance.mesh.get_faces().size() / 3
		for surface in instance.mesh.get_surface_count():
			var material := instance.get_active_material(surface) as StandardMaterial3D
			_check(material != null, "surface keeps a glTF PBR material")
			if material == null:
				continue
			materials[material.resource_name] = true
			_check(material != instance.mesh.surface_get_material(surface), "instance material does not mutate the shared asset")
			_check(material.texture_filter == BaseMaterial3D.TEXTURE_FILTER_NEAREST, "pixel surfaces use nearest sampling")
			_check(is_equal_approx(material.roughness, 1.0) and is_zero_approx(material.metallic) and is_zero_approx(material.metallic_specular), "pixel surface has no smooth metallic highlights")
			_check(not material.normal_enabled, "no generated normal map")
			if material.albedo_texture != null:
				var size := Vector2i(material.albedo_texture.get_width(), material.albedo_texture.get_height())
				textures[material.albedo_texture.get_rid()] = size
				_check(size in [Vector2i(512, 512), Vector2i(512, 128)], "pixel atlas or bitmap sign texture decoded")
	_check(materials.size() == 20 and textures.size() == 2, "all R2.1 materials and both pixel textures survive import")
	_check(Vector2i(512, 512) in textures.values() and Vector2i(512, 128) in textures.values(), "both expected texture sizes present")
	_check(triangles == 8146, "R2.1 topology survives import without automatic LOD")
	_check(model.scene_file_path == Asset.resource_path, "world loads the R2.1 GLB")
	for node in model.find_children("*", "", true, false):
		_check(node is Node3D and not node is Camera3D and not node is Light3D and not node is AnimationPlayer, "asset contains only model nodes")
	var faces := _faces(model, world)
	var bounds := _bounds(faces)
	_check(bounds.position.x > 8.3 and bounds.end.x < 26.5, "complete asset stays on the board outside the cargo lanes")
	_check(bounds.position.y > -0.55 and bounds.end.y > 8.5 and bounds.end.y < 8.7, "full-scale R2.1 crane height retained")
	_check(bounds.position.z > -15.3 and bounds.end.z < -5.4, "asset remains in insurance district away from the shipyard")
	_check(_standing_clear(faces), "entire insurance standing ring has headroom")
	var blocker := MeshInstance3D.new()
	blocker.mesh = BoxMesh.new()
	blocker.mesh.size = Vector3(1.6, 1.5, 1.6)
	model.add_child(blocker)
	blocker.global_position = Vector3(15.1, 1.4, -8.3)
	_check(not _standing_clear(_faces(model, world)), "standing test rejects a blocking wall")
	blocker.mesh.size = Vector3(0.012, 0.2, 0.012)
	blocker.global_position = Vector3(15.195, 1.30, -8.205)
	_check(not _standing_clear(_faces(model, world)), "standing test rejects a thin obstacle between ray probes")
	blocker.mesh.size = Vector3(4, 4, 4)
	blocker.global_position = Vector3(15.1, 1.5, -8.3)
	_check(not _standing_clear(_faces(model, world)), "standing test rejects a volume enclosing the whole ring")
	blocker.free()
	var supported := true
	for x in range(-4, 5):
		for z in range(-4, 5):
			var offset := Vector2(x, z) * 0.19
			if offset.length() <= 0.78:
				var point := Vector3(15.1 + offset.x, 0.72, -8.3 + offset.y)
				supported = supported and not _hits(faces, point, point - Vector3.UP * 0.20).is_empty()
	_check(supported, "standing ring has dock support immediately below it")
	var office: Node3D = model.find_child("INS_OfficeGeometry", true, false)
	var front_faces := _faces(office, model)
	var wall_hits := _hits(front_faces, Vector3(-3.50, 1.90, 2.0), Vector3(-3.50, 1.90, 0.8))
	var pane_hits := _hits(front_faces, Vector3(-2.55, 1.90, 2.0), Vector3(-2.55, 1.90, 0.8))
	var frame_hits := _hits(front_faces, Vector3(-3.10, 1.90, 2.0), Vector3(-3.10, 1.90, 0.8))
	_check(not wall_hits.is_empty() and not pane_hits.is_empty() and not frame_hits.is_empty(), "front wall, window frame and inset pane are actual surfaces")
	if not frame_hits.is_empty() and not pane_hits.is_empty():
		_check(pane_hits[0].z < frame_hits[0].z - 0.04, "R2.1 pane is recessed behind its raised frame")
	var roof: Node3D = model.find_child("INS_RoofGeometry", true, false)
	var roof_hits := _hits(_faces(roof, model), Vector3(-5.20, 6, 0), Vector3(-5.20, 2, 0))
	_check(roof_hits.size() >= 2, "roof slope has separate top and underside")
	if roof_hits.size() >= 2:
		_check(roof_hits[0].distance_to(roof_hits[1]) > 0.09, "roof has geometric thickness")
	var tug: Node3D = model.find_child("INS_TugGeometry", true, false)
	var tug_faces := _faces(tug, world)
	var tug_bounds := _bounds(tug_faces)
	var water_clear := true
	# The mooring rope terminates on a dock pile; every other tug surface must be afloat.
	for point in _faces(tug, world, "INR2_Rope"):
		water_clear = water_clear and point.x < world._coast(point.z, 1) - 0.10
	_check(water_clear, "whole decorative tug including fenders stays on water side")
	var dock := model.find_child("INS_DockGeometry", true, false) as Node3D
	var rope_end: Vector3 = tug.to_global(Vector3(-6.65, 1.17, 3.69))
	var pile_center: Vector3 = dock.to_global(Vector3(-6.65, 0.5, 3.69))
	_check(rope_end.distance_to(pile_center) < 0.001, "mooring line remains attached to the dock pile")
	_check(tug_bounds.position.y < -0.12 and tug_bounds.end.y > 1.4, "tug hull intersects the actual waterline")
	_check(tug_bounds.position.z > -9.4, "tug clears end of existing narrow public pier")
	_check(tug_bounds.end.z < -5.4, "tug clears neighboring shipyard approach")
	for ship in 3:
		var local_bounds := _bounds(_faces(world.boats[ship], world.boats[ship]))
		for step in range(15):
			var position: Vector3 = world.route_point(ship, step)
			var ship_bounds := AABB(local_bounds.position + position, local_bounds.size).grow(0.06)
			_check(not ship_bounds.intersects(tug_bounds), "decorative tug clears complete cargo-boat bounds including wake")
	_check(world.boats.size() == 3 and world.anchors.size() == 21, "decoration adds no gameplay boat or slot")
	print("INSURANCE_GEOMETRY: triangles=%d materials=%d textures=%d bounds=%s tug=%s" % [triangles, materials.size(), textures.size(), bounds, tug_bounds])
	_structure_complete = true


func _standing_clear(faces: PackedVector3Array) -> bool:
	var center := Vector2(15.1, -8.3)
	for i in range(0, faces.size(), 3):
		var polygon: Array[Vector3] = [faces[i], faces[i + 1], faces[i + 2]]
		polygon = _clip_height(polygon, 0.73, true)
		polygon = _clip_height(polygon, 2.43, false)
		if polygon.is_empty():
			continue
		var projected := PackedVector2Array()
		for point in polygon:
			projected.append(Vector2(point.x, point.z))
		if projected.size() >= 3 and Geometry2D.is_point_in_polygon(center, projected):
			return false
		for edge in projected.size():
			var a := projected[edge]
			var b := projected[(edge + 1) % projected.size()]
			var delta := b - a
			var t := clampf((center - a).dot(delta) / delta.length_squared(), 0.0, 1.0) if delta.length_squared() > 0.000000001 else 0.0
			if (a + delta * t).distance_squared_to(center) <= 0.78 * 0.78:
				return false
	# Surface intersections miss the case where a closed component encloses the ring.
	var inside := Vector3(15.1, 1.58, -8.3)
	return _hits(faces, inside, inside + Vector3(100, 0.173, 0.319)).size() % 2 == 0


func _clip_height(polygon: Array[Vector3], height: float, keep_above: bool) -> Array[Vector3]:
	var result: Array[Vector3] = []
	if polygon.is_empty():
		return result
	var previous := polygon[-1]
	var previous_inside := previous.y >= height if keep_above else previous.y <= height
	for current in polygon:
		var current_inside := current.y >= height if keep_above else current.y <= height
		if current_inside != previous_inside:
			result.append(previous.lerp(current, (height - previous.y) / (current.y - previous.y)))
		if current_inside:
			result.append(current)
		previous = current
		previous_inside = current_inside
	return result


func _faces(node: Node3D, reference: Node3D, excluded_material := "") -> PackedVector3Array:
	var result := PackedVector3Array()
	var meshes := node.find_children("*", "MeshInstance3D", true, false)
	if node is MeshInstance3D:
		meshes.append(node)
	for instance: MeshInstance3D in meshes:
		var transform := reference.global_transform.affine_inverse() * instance.global_transform
		if excluded_material.is_empty():
			for point in instance.mesh.get_faces():
				result.append(transform * point)
			continue
		for surface in instance.mesh.get_surface_count():
			var material := instance.get_active_material(surface)
			if material != null and material.resource_name == excluded_material:
				continue
			var arrays := instance.mesh.surface_get_arrays(surface)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			if indices.is_empty():
				for point in vertices:
					result.append(transform * point)
			else:
				for index in indices:
					result.append(transform * vertices[index])
	return result


func _bounds(faces: PackedVector3Array) -> AABB:
	var result := AABB(faces[0], Vector3.ZERO)
	for point in faces:
		result = result.expand(point)
	return result


func _hits(faces: PackedVector3Array, a: Vector3, b: Vector3) -> Array[Vector3]:
	var result: Array[Vector3] = []
	for i in range(0, faces.size(), 3):
		var hit = Geometry3D.segment_intersects_triangle(a, b, faces[i], faces[i + 1], faces[i + 2])
		if hit == null:
			hit = Geometry3D.segment_intersects_triangle(a, b, faces[i + 2], faces[i + 1], faces[i])
		if hit == null:
			continue
		var duplicate := false
		for existing in result:
			if existing.distance_squared_to(hit) < 0.000001:
				duplicate = true
				break
		if not duplicate:
			result.append(hit)
	result.sort_custom(func(x: Vector3, y: Vector3): return a.distance_squared_to(x) < a.distance_squared_to(y))
	return result


func _preview() -> void:
	if DirAccess.dir_exists_absolute(output_dir):
		failures.append("Preview directory exists; choose a new output path")
		return
	_check(DirAccess.make_dir_recursive_absolute(output_dir) == OK, "create preview directory")
	world.set_process(false)
	world._static_root.visible = false
	for boat: Node3D in world.boats:
		boat.visible = false
	var camera := Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	world.add_child(camera)
	camera.current = true
	var clay := StandardMaterial3D.new()
	clay.albedo_color = Color("aaa59d")
	clay.roughness = 1.0
	clay.specular_mode = BaseMaterial3D.SPECULAR_DISABLED
	var meshes := model.find_children("*", "MeshInstance3D", true, false)
	var bounds := _bounds(_faces(model, world))
	for style in ["clay", "material"]:
		for instance: MeshInstance3D in meshes:
			instance.material_override = clay if style == "clay" else null
		for view in range(3):
			var offsets := [Vector3(0, 5, 24), Vector3(15, 12, 22), Vector3(-13, 18, 20)]
			camera.position = bounds.get_center() + offsets[view]
			camera.look_at(bounds.get_center())
			var inverse := camera.global_transform.affine_inverse()
			var projected := Rect2()
			for corner in range(8):
				var local := inverse * bounds.get_endpoint(corner)
				var point := Vector2(local.x, local.y)
				projected = Rect2(point, Vector2.ZERO) if corner == 0 else projected.expand(point)
			camera.position += camera.basis.x * projected.get_center().x + camera.basis.y * projected.get_center().y
			camera.size = maxf(projected.size.y / 0.87, projected.size.x / 1.6 / 0.90)
			await process_frame
			var rect := root.get_visible_rect()
			for corner in range(8):
				_check(rect.has_point(camera.unproject_position(bounds.get_endpoint(corner))), "complete insurance model fits preview")
			await create_timer(0.25).timeout
			await RenderingServer.frame_post_draw
			var image := root.get_texture().get_image()
			_check(image != null and not image.is_empty(), "preview renders")
			if image != null and not image.is_empty():
				_check(image.save_png(output_dir.path_join("insurance_%s_%d.png" % [style, view + 1])) == OK, "save preview")
	for instance: MeshInstance3D in meshes:
		instance.material_override = null
	print("INSURANCE_PREVIEW_SAVED: ", ProjectSettings.globalize_path(output_dir))
	_preview_complete = true


func _check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)
		push_error("HARBOR_INSURANCE_CHECK: " + message)


func _finish() -> void:
	if _finished:
		return
	_finished = true
	print("HARBOR_INSURANCE_%s: %d checks / %d failures" % ["PASS" if failures.is_empty() else "FAIL", checks, failures.size()])
	for message in failures:
		print("  FAIL: ", message)
	quit(0 if failures.is_empty() else 1)
