extends SceneTree

const World := preload("res://demo/harbor_hd2d/harbor_world.gd")
const Buildings := preload("res://demo/harbor_hd2d/harbor_buildings.gd")
const Pixel := preload("res://card/pixel_card_theme.gd")

var helper: Node3D
var stage: Node3D
var models: Array[Node3D] = []
var checks := 0
var failures: Array[String] = []
var preview := false
var output_dir := "user://harbor_buildings_v4"
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
			failures.append("60 second building preview watchdog expired")
			_finish())
	if preview and DisplayServer.get_name() == "headless":
		failures.append("Building preview needs a real display")
		_finish()
		return
	root.content_scale_size = Vector2i(1600, 1000)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.size = Vector2i(1200, 750)
	stage = Node3D.new()
	root.add_child(stage)
	# Keep the helper out of the tree: reuse meshes/materials without running its port _ready.
	helper = World.new()
	var builder := Buildings.new(helper._box, helper._quad, helper._triangle)
	models.append(builder.build_warehouse(stage, Vector3(-4.2, 0.26, -19.1), Vector2(10.3, 4.8), 3.3, 3, 2))
	models.append(builder.build_warehouse(stage, Vector3(5.8, 0.26, -19.1), Vector2(8.4, 4.8), 3.2, 4, 1))
	models.append(builder.build_shipyard(stage, Vector3(20, 0.5, 2)))
	await process_frame
	_structure_checks()
	_check(_structure_complete, "structure checks reached their end")
	if preview and failures.is_empty():
		await _preview()
		_check(_preview_complete, "building preview reached its end")
	_finish()


func _structure_checks() -> void:
	for i in 2:
		var building := models[i]
		var w := 10.3 if i == 0 else 8.4
		var faces := _faces(building, building)
		var building_bounds := _bounds(faces)
		_check(building_bounds.position.x > -w * 0.5 - 0.40 and building_bounds.end.x < w * 0.5 + 0.40 and building_bounds.position.z > -3.0 and building_bounds.end.z < 3.8, "warehouse members stay inside the allocated footprint")
		for x in [-w * 0.29, w * 0.04]:
			_check(_door_clear(faces, x), "warehouse %d has an open loading doorway" % i)
			var hits := _hits(faces, Vector3(x, 1.35, 3.6), Vector3(x, 1.35, -3.0))
			_check(not hits.is_empty() and hits[0].z < -2.0, "doorway reaches the distant interior wall")
		_check(not _hits(faces, Vector3(w * 0.38, 1.2, 3.6), Vector3(w * 0.38, 1.2, 1.5)).is_empty(), "front wall exists beside the doors")
		for slope: Node3D in building.get_node("Roof").get_children():
			_check(_closed_panel(slope), "warehouse slope has welded closed edges")
		_check(_closed_panel(building.get_node("LoadingCanopy/CanopySlab")), "loading canopy is an actual solid panel")
		var blocker: MeshInstance3D = helper._box(building, Vector3(-w * 0.29, 1.3, 2.25), Vector3(2.25, 2.4, 0.22), Color.WHITE)
		_check(not _door_clear(_faces(building, building), -w * 0.29), "door test rejects a wall behind the opening")
		blocker.free()
	var left := _bounds(_faces(models[0].get_node("Roof"), stage))
	var right := _bounds(_faces(models[1].get_node("Roof"), stage))
	_check(right.position.x - left.end.x > 0.10, "adjacent warehouse roof meshes remain separated")
	var yard := models[2]
	var yard_faces := _faces(yard, yard)
	var frame_bounds := _bounds(_faces(yard.get_node("TimberFrame"), yard))
	_check(frame_bounds.position.x > -4.5 and frame_bounds.end.x < 4.5 and frame_bounds.position.z > -4.3 and frame_bounds.end.z < 4.3, "all frame members remain in the building local bounds")
	print("BUILDING_FRAME_BOUNDS: ", frame_bounds)
	for z in [-3.3, -1.1, 1.1, 3.3]:
		for side in [-1, 1]:
			_check(not _hits(yard_faces, Vector3(side * 3.5, 2.0, z - 0.4), Vector3(side * 3.5, 2.0, z + 0.4)).is_empty(), "truss column exists")
			_check(not _hits(yard_faces, Vector3(side * 2.0, 4.3, z - 0.4), Vector3(side * 2.0, 5.0, z + 0.4)).is_empty(), "truss rafter exists")
		_check(not _hits(yard_faces, Vector3(1.0, 3.83, z - 0.4), Vector3(1.0, 3.83, z + 0.4)).is_empty(), "truss tie beam exists")
	_check(_end_clear(yard_faces, 1.0) and _end_clear(yard_faces, -1.0), "both gable ends are open around the timber")
	var blocker_root := Node3D.new()
	yard.add_child(blocker_root)
	helper._triangle(blocker_root, [Vector3(-3.5, 3.95, 3.5), Vector3(3.5, 3.95, 3.5), Vector3(0, 5.8, 3.5)], Color.WHITE, 0)
	_check(not _end_clear(_faces(yard, yard), 1.0), "open-gable test rejects a solid infill")
	blocker_root.free()
	for slope: Node3D in yard.get_node("Roof").get_children():
		if str(slope.name).begins_with("Slope"):
			_check(_closed_panel(slope), "shipyard roof has real thickness and closed edges")
	var repair: Node3D = yard.get_node("RepairHull")
	var hull_faces := _faces(repair, yard)
	_check(_hull_open(hull_faces), "repair hull has a low interior, not a deck cap")
	var cap: MeshInstance3D = helper._box(repair, Vector3(0, 1.8, 0), Vector3(2.7, 0.08, 4.0), Color.WHITE)
	_check(not _hull_open(_faces(repair, yard)), "hull test rejects a cap across the gunwales")
	cap.free()
	for rib: Node3D in repair.get_node("Ribs").get_children():
		var bounds := _bounds(_faces(rib, yard))
		_check(bounds.size.y > 1.0 and bounds.size.x > 1.30 and bounds.position.y < 0.8, "rib bends from the keel up both sides")
	var shell := _faces(repair.get_node("Shell"), yard)
	_check(_hits(shell, Vector3(0.5, 1.32, 0.3), Vector3(2.0, 1.32, 0.3)).size() >= 2, "repair shell has separate inner and outer sides")
	for p in [Vector3(-5.1, 0.3, 0.8), Vector3(-3.2, 0.3, 4.6), Vector3(4.3, 0.3, 4.6)]:
		for dx in [-0.35, 0.0, 0.35]:
			for dz in [-0.35, 0.0, 0.35]:
				var a: Vector3 = p + Vector3(dx, 0, dz)
				_check(_hits(yard_faces, a, a + Vector3.UP * 1.5).is_empty(), "repair-yard worker standing space remains clear")
	_structure_complete = true


func _door_clear(faces: PackedVector3Array, x: float) -> bool:
	for dx in [-0.40, 0.0, 0.40]:
		for y in [0.55, 1.3, 2.1]:
			if not _hits(faces, Vector3(x + dx, y, 3.6), Vector3(x + dx, y, 0.8)).is_empty():
				return false
	return true


func _end_clear(faces: PackedVector3Array, side: float) -> bool:
	var clear := 0
	var total := 0
	for x in [-2.6, -2.2, -1.8, -1.4, -1.0, -0.6, 0.6, 1.0, 1.4, 1.8, 2.2, 2.6]:
		for y in [4.15, 4.4, 4.65]:
			if y > 5.5 - absf(x) * 0.43:
				continue
			total += 1
			if _hits(faces, Vector3(x, y, side * 4.4), Vector3(x, y, side * 2.95)).is_empty():
				clear += 1
	return float(clear) / maxf(total, 1) >= 0.65


func _hull_open(faces: PackedVector3Array) -> bool:
	for z in [-1.9, -0.8, 0.3, 1.3]:
		var hits := _hits(faces, Vector3(0.35, 2.6, z), Vector3(0.35, 0.2, z))
		if hits.is_empty() or hits[0].y >= 1.15:
			return false
	return true


func _closed_panel(panel: Node3D) -> bool:
	var faces := _faces(panel, panel)
	var edges: Dictionary = {}
	for i in range(0, faces.size(), 3):
		for edge in 3:
			var a := _vertex_key(faces[i + edge])
			var b := _vertex_key(faces[i + (edge + 1) % 3])
			var key := a + ":" + b if a < b else b + ":" + a
			edges[key] = edges.get(key, 0) + 1
	if edges.is_empty() or not edges.values().all(func(value): return value == 2):
		return false
	var top := faces[0]
	var normal := (faces[1] - top).cross(faces[2] - top).normalized()
	var max_depth := 0.0
	for p in faces:
		max_depth = maxf(max_depth, absf((p - top).dot(normal)))
	return max_depth >= 0.14 and max_depth <= 0.24


func _vertex_key(p: Vector3) -> String:
	return "%d,%d,%d" % [roundi(p.x * 10000), roundi(p.y * 10000), roundi(p.z * 10000)]


func _faces(node: Node3D, reference: Node3D) -> PackedVector3Array:
	var result := PackedVector3Array()
	var instances: Array[Node] = node.find_children("*", "MeshInstance3D", true, false)
	if node is MeshInstance3D:
		instances.append(node)
	for instance: MeshInstance3D in instances:
		var transform := reference.global_transform.affine_inverse() * instance.global_transform
		for point in instance.mesh.get_faces():
			result.append(transform * point)
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


func _bounds(faces: PackedVector3Array) -> AABB:
	var result := AABB(faces[0], Vector3.ZERO)
	for p in faces:
		result = result.expand(p)
	return result


func _preview() -> void:
	if DirAccess.dir_exists_absolute(output_dir):
		failures.append("Preview directory already exists; choose a new --output path")
		return
	_check(DirAccess.make_dir_recursive_absolute(output_dir) == OK, "preview directory created")
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color("252630")
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("d4d7d5")
	environment.ambient_light_energy = 0.65
	var world_environment := WorldEnvironment.new()
	world_environment.environment = environment
	stage.add_child(world_environment)
	var sunlight := DirectionalLight3D.new()
	sunlight.rotation_degrees = Vector3(-48, -30, 0)
	sunlight.light_color = Color("fff0d9")
	sunlight.light_energy = 0.85
	sunlight.shadow_enabled = true
	stage.add_child(sunlight)
	var camera := Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	stage.add_child(camera)
	camera.current = true
	var caption := Pixel.label(root, "", Rect2(24, 18, 1500, 38), 24, Color("f0dfbb"))
	var original: Dictionary = {}
	var clay := StandardMaterial3D.new()
	clay.albedo_color = Color("aaa59d")
	clay.roughness = 1.0
	clay.specular_mode = BaseMaterial3D.SPECULAR_DISABLED
	clay.cull_mode = BaseMaterial3D.CULL_DISABLED
	for instance: MeshInstance3D in stage.find_children("*", "MeshInstance3D", true, false):
		original[instance] = instance.material_override
	for model_index in [0, 2]:
		for i in models.size():
			models[i].visible = i < 2 if model_index == 0 else i == 2
		var center := Vector3(0.4, 2.0, -19.1) if model_index == 0 else Vector3(20, 2.5, 2)
		camera.size = 16.5 if model_index == 0 else 14.5
		for material_name in ["clay", "material"]:
			for instance: MeshInstance3D in original:
				instance.material_override = clay if material_name == "clay" else original[instance]
			for view_index in 3:
				var offsets := [Vector3(0, 2.0, 24), Vector3(13, 7, 20), Vector3(10, 20, 21)]
				camera.position = center + offsets[view_index]
				camera.look_at(center)
				_fit_preview(camera)
				await process_frame
				var viewport_rect := Rect2(Vector2(0, 62), Vector2(root.get_visible_rect().size.x, root.get_visible_rect().size.y - 62))
				for model: Node3D in models:
					if not model.visible:
						continue
					var bounds := _bounds(_faces(model, stage))
					var fits := true
					for corner in 8:
						var projected := camera.unproject_position(bounds.get_endpoint(corner))
						fits = fits and viewport_rect.has_point(projected)
					_check(fits, "complete building fits dedicated preview frame")
				var name := "%s_%s_%d" % ["warehouses" if model_index == 0 else "shipyard", material_name, view_index + 1]
				caption.text = "%s · %s · %s" % ["仓库建模" if model_index == 0 else "开放修船棚建模", "无纹理灰模" if material_name == "clay" else "材质模型", ["正面", "斜侧", "高位"][view_index]]
				await create_timer(0.22).timeout
				await RenderingServer.frame_post_draw
				var image := root.get_texture().get_image()
				_check(image != null and not image.is_empty(), "render " + name)
				if image != null and not image.is_empty():
					_check(image.save_png(output_dir.path_join(name + ".png")) == OK, "save " + name)
	for instance: MeshInstance3D in original:
		instance.material_override = original[instance]
	print("HARBOR_BUILDINGS_PREVIEW: ", ProjectSettings.globalize_path(output_dir))
	_preview_complete = true


func _fit_preview(camera: Camera3D) -> void:
	var inverse := camera.global_transform.affine_inverse()
	var projected := Rect2()
	var started := false
	for model: Node3D in models:
		if not model.visible:
			continue
		var bounds := _bounds(_faces(model, stage))
		for corner in 8:
			var local := inverse * bounds.get_endpoint(corner)
			var point := Vector2(local.x, local.y)
			if not started:
				projected = Rect2(point, Vector2.ZERO)
				started = true
			else:
				projected = projected.expand(point)
	var center := projected.get_center()
	camera.position += camera.basis.x * center.x + camera.basis.y * center.y
	var view_size := root.get_visible_rect().size
	camera.size = maxf(projected.size.y / 0.78, projected.size.x / (view_size.x / view_size.y * 0.90))


func _check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)
		push_error("HARBOR_BUILDING_CHECK: " + message)


func _finish() -> void:
	if _finished:
		return
	_finished = true
	if is_instance_valid(helper):
		helper.free()
	print("HARBOR_BUILDINGS_%s: %d checks / %d failures" % ["PASS" if failures.is_empty() else "FAIL", checks, failures.size()])
	for message in failures:
		print("  FAIL: ", message)
	quit(0 if failures.is_empty() else 1)
