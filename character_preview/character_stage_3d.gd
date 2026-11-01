extends SubViewportContainer

signal hero_pose_changed

const PawnFactory = preload("res://character_preview/pawn_factory.gd")
const Plinth = preload("res://character_preview/selection_plinth.gd")
const VINYL_SHADER = preload("res://character_preview/carmen_vinyl.gdshader")
const CARMEN_GLB: PackedScene = preload("res://character_preview/comparison/pirate_doll.glb")

var viewport_3d: SubViewport
var camera: Camera3D
var pawns: Array[Node3D] = []
var hero: Node3D
var selected_index := 0
var hit_rects: Array[Rect2] = []
var _world: Node3D
var _benches: Array[MeshInstance3D] = []
var _hero_base: MeshInstance3D
var _selection_ring: MeshInstance3D
var _homes: Array[Vector3] = []
var _pawn_scale := 1.0
var _pawn_scales: Array[float] = []
var _hero_rect := Rect2()
var hero_contact := Vector2.INF
var _fit_cache: Dictionary = {}
var _hit_cache: Dictionary = {}
var _hero_scale := 1.0
var _hero_home := Vector3.ZERO
var _pixels_per_unit := 48.0
var _tween: Tween
var _table_rect := Rect2()
var _vinyl_materials: Array[ShaderMaterial] = []
var imported_carmen: Node3D
var imported_carmen_enabled := true
var _imported_extent := Rect2()


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	stretch = true
	stretch_shrink = 1
	texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	viewport_3d = SubViewport.new()
	viewport_3d.transparent_bg = true
	viewport_3d.own_world_3d = true
	viewport_3d.msaa_3d = Viewport.MSAA_4X
	viewport_3d.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(viewport_3d)
	_world = Node3D.new()
	viewport_3d.add_child(_world)
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.near = 0.1
	camera.far = 150.0
	camera.position = Vector3(0, 36, 48)
	_world.add_child(camera)
	camera.look_at(Vector3.ZERO)
	camera.current = true
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-48, -28, 0)
	light.light_energy = 1.0
	light.shadow_enabled = true
	light.directional_shadow_max_distance = 100.0
	_world.add_child(light)
	var env := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color.TRANSPARENT
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("dfe0e3")
	environment.ambient_light_energy = 0.55
	env.environment = environment
	_world.add_child(env)
	for row in 2:
		var bench := MeshInstance3D.new()
		bench.name = "WoodenBench%d" % row
		_world.add_child(bench)
		_benches.append(bench)
	_hero_base = MeshInstance3D.new()
	_hero_base.name = "SlateDisplayPlinth"
	_world.add_child(_hero_base)
	_selection_ring = MeshInstance3D.new()
	_selection_ring.name = "SelectedSeatInlay"
	_selection_ring.mesh = Plinth.seat_marker()
	_world.add_child(_selection_ring)
	for i in 6:
		var pawn: Node3D = PawnFactory.build(i, PawnFactory.Presentation.CHOICE)
		pawn.name = "Pawn%d" % i
		_world.add_child(pawn)
		pawns.append(pawn)
		_homes.append(Vector3.ZERO)
	_create_imported_carmen()
	_create_hero(0)
	set_process(false)


func _create_imported_carmen() -> void:
	imported_carmen = Node3D.new()
	imported_carmen.name = "CarmenGLBComparison"
	_world.add_child(imported_carmen)
	var source: Node3D = CARMEN_GLB.instantiate()
	imported_carmen.add_child(source)
	var first := true
	for model: MeshInstance3D in source.find_children("*", "MeshInstance3D", true, false):
		var transform_to_root := imported_carmen.global_transform.affine_inverse() * model.global_transform
		# Match the fixed selection camera using actual vertices, not the larger AABB corners.
		for surface in model.mesh.get_surface_count():
			var vertices: PackedVector3Array = model.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
			for vertex in vertices:
				var point := transform_to_root * vertex
				var projected := Vector2(point.x, -0.8 * point.y + 0.6 * point.z)
				_imported_extent = Rect2(projected, Vector2.ZERO) if first else _imported_extent.expand(projected)
				first = false
	set_imported_carmen(imported_carmen_enabled)


func set_imported_carmen(enabled: bool) -> void:
	imported_carmen_enabled = enabled
	imported_carmen.visible = enabled
	pawns[0].visible = not enabled


func _arrange_imported_carmen() -> void:
	# The original six figures still determine bench spacing and scale in both modes.
	var original := _fit_bounds(pawns[0], [0.0])
	var factor := minf(original.size.x / _imported_extent.size.x, original.size.y / _imported_extent.size.y)
	var scale_factor := factor * _pawn_scales[0]
	imported_carmen.scale = Vector3.ONE * scale_factor
	var original_center := original.get_center() * _pawn_scales[0]
	var imported_center := _imported_extent.get_center() * scale_factor
	var offset := original_center - imported_center
	imported_carmen.position = _homes[0] + Vector3(offset.x, -0.8 * offset.y, 0.6 * offset.y)


func arrange(table_rect: Rect2, cells: Array[Rect2], hero_rect: Rect2, ui_scale: float) -> void:
	if camera == null or size.y < 1.0:
		return
	if _tween and _tween.is_valid():
		_tween.kill()
	_pixels_per_unit = 48.0 * ui_scale
	camera.size = size.y / _pixels_per_unit
	_table_rect = table_rect
	hit_rects = cells.duplicate()
	# Use one scale for all six people; seat origins share the same plank plane.
	var extent := _fit_bounds(pawns[0], [0.0])
	for i in range(1, pawns.size()):
		extent = extent.merge(_fit_bounds(pawns[i], [0.0]))
	extent = extent.expand(Vector2(0, 0.92 * 0.8 + 0.38 * 0.6))
	var cell_size := cells[0].size
	var pawn_scale := minf((cell_size.y * 0.77 - 8.0 * ui_scale) / (extent.size.y * _pixels_per_unit),
		cell_size.x * 0.77 / (extent.size.x * _pixels_per_unit))
	_pawn_scales.clear()
	for row in 2:
		var first := cells[row * 3]
		var last := cells[row * 3 + 2]
		var seat_y := first.position.y + 8.0 * ui_scale - extent.position.y * pawn_scale * _pixels_per_unit
		var bench := _benches[row]
		bench.position = _ground(Vector2((first.position.x + last.end.x) * 0.5, seat_y))
		bench.scale = Vector3.ONE * pawn_scale
		bench.mesh = Plinth.bench((last.end.x - first.position.x - 8.0 * ui_scale) / (_pixels_per_unit * pawn_scale))
		for column in 3:
			var i := row * 3 + column
			_pawn_scales.append(pawn_scale)
			_homes[i] = _ground(Vector2(cells[i].get_center().x, seat_y))
			pawns[i].scale = Vector3.ONE * pawn_scale
	_arrange_imported_carmen()
	_pawn_scale = _pawn_scales[selected_index]
	_hero_rect = hero_rect
	_fit_hero()
	_apply_selection(false)


func choose(index: int, animate := true) -> void:
	if index < 0 or index >= pawns.size():
		return
	selected_index = index
	_create_hero(index)
	_fit_hero()
	_apply_selection(animate)


func _create_hero(index: int) -> void:
	if is_instance_valid(hero):
		_world.remove_child(hero)
		hero.queue_free()
	hero = PawnFactory.build(index, PawnFactory.Presentation.DISPLAY)
	hero.name = "FocusedPawn"
	_world.add_child(hero)
	var model: MeshInstance3D = hero.get_child(0)
	if _vinyl_materials.is_empty():
		for surface in 2:
			var vinyl := ShaderMaterial.new()
			vinyl.shader = VINYL_SHADER
			vinyl.next_pass = model.mesh.surface_get_material(surface).next_pass
			_vinyl_materials.append(vinyl)
	for surface in 2:
		model.set_surface_override_material(surface, _vinyl_materials[surface])


func _apply_selection(animate: bool) -> void:
	if _tween and _tween.is_valid():
		_tween.kill()
	if animate:
		_tween = create_tween().set_parallel(true)
		_tween.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	for i in pawns.size():
		# Do not rotate or lift the seated body off its shared bench.
		pawns[i].position = _homes[i]
		pawns[i].rotation = Vector3.ZERO
	_pawn_scale = _pawn_scales[selected_index] if not _pawn_scales.is_empty() else 1.0
	var marker_target := _homes[selected_index] + Vector3(0, 0, 0.414) * _pawn_scale
	if animate:
		_tween.tween_property(_selection_ring, "position", marker_target, 0.22)
	else:
		_selection_ring.position = marker_target
	_selection_ring.scale = Vector3.ONE * _pawn_scale
	# Each sculpt's measured sole is normalized by the factory.
	hero.position = _hero_home
	hero.scale = Vector3.ONE * _hero_scale
	hero.rotation.y = -0.28
	if animate:
		hero.rotation.y = -0.48
		_tween.tween_property(hero, "rotation:y", -0.28, 0.25)
		_tween.finished.connect(func(): hero_pose_changed.emit(); set_process(false))
	set_process(animate)
	hero_pose_changed.emit()


func _process(_delta: float) -> void:
	hero_pose_changed.emit()


func hero_head_point() -> Vector2:
	if not is_instance_valid(hero):
		return Vector2.ZERO
	var world_point := hero.to_global(Vector3(0.05, 3.25, 0.20))
	var point := camera.unproject_position(world_point)
	var model: MeshInstance3D = hero.get_child(0)
	for i in 8:
		var corner := camera.unproject_position(model.to_global(model.get_aabb().get_endpoint(i)))
		point.y = minf(point.y, corner.y)
	return global_position + point * size / Vector2(viewport_3d.size)


func _fit_bounds(figure: Node3D, yaws: Array) -> Rect2:
	var key := "%s:%s:%s" % [figure.get_meta("character_index"), figure.get_meta("presentation"), yaws]
	if _fit_cache.has(key):
		return _fit_cache[key]
	var bounds := Rect2()
	var first := true
	for yaw: float in yaws:
		for model: MeshInstance3D in figure.get_children():
			for surface in model.mesh.get_surface_count():
				var points: PackedVector3Array = model.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
				for vertex in points:
					var point := Basis(Vector3.UP, yaw) * (model.transform * vertex)
					var projected := Vector2(point.x, -0.8 * point.y + 0.6 * point.z)
					bounds = Rect2(projected, Vector2.ZERO) if first else bounds.expand(projected)
					first = false
	_fit_cache[key] = bounds
	return bounds


func _fit_hero() -> void:
	if _hero_rect.size.y <= 0:
		return
	var extent := _fit_bounds(hero, [-0.48, -0.28])
	_hero_scale = minf(_hero_rect.size.y * 0.90 / (extent.size.y * _pixels_per_unit),
		_hero_rect.size.x * 0.86 / (extent.size.x * _pixels_per_unit))
	_hero_home = _ground(Vector2(_hero_rect.get_center().x - extent.get_center().x * _hero_scale * _pixels_per_unit,
		_hero_rect.end.y - (extent.end.y + 0.48) * _hero_scale * _pixels_per_unit))
	if hero_contact.is_finite():
		_hero_home = _ground(hero_contact)
	_hero_base.position = _hero_home
	_hit_cache.erase(_hero_base.mesh)
	_hero_base.mesh = Plinth.display_base(_hero_scale * 0.86)


func foreground_bounds() -> Rect2:
	return _mesh_screen_bounds(hero.get_child(0)).merge(_mesh_screen_bounds(_hero_base))


func _mesh_screen_bounds(model: MeshInstance3D) -> Rect2:
	var bounds := Rect2()
	for i in 8:
		var point := global_position + camera.unproject_position(model.to_global(model.get_aabb().get_endpoint(i))) * size / Vector2(viewport_3d.size)
		bounds = Rect2(point, Vector2.ZERO) if i == 0 else bounds.expand(point)
	return bounds


func foreground_hit(point: Vector2) -> bool:
	if not is_visible_in_tree() or not is_instance_valid(hero):
		return false
	var pixel := (point - global_position) * Vector2(viewport_3d.size) / size
	var origin := camera.project_ray_origin(pixel)
	var direction := camera.project_ray_normal(pixel)
	for model: MeshInstance3D in [hero.get_child(0), _hero_base]:
		if not _mesh_screen_bounds(model).has_point(point):
			continue
		var local_origin := model.to_local(origin)
		var local_direction := model.global_basis.inverse() * direction
		if not _hit_cache.has(model.mesh):
			_hit_cache[model.mesh] = model.mesh.get_faces()
		var faces: PackedVector3Array = _hit_cache[model.mesh]
		for i in range(0, faces.size(), 3):
			if Geometry3D.ray_intersects_triangle(local_origin, local_direction, faces[i], faces[i + 1], faces[i + 2]) != null:
				return true
	return false


func _ground(screen_position: Vector2) -> Vector3:
	var uv := screen_position * Vector2(viewport_3d.size) / size
	var origin := camera.project_ray_origin(uv)
	var direction := camera.project_ray_normal(uv)
	return origin + direction * (-origin.y / direction.y)
