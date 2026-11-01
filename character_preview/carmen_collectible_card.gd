extends Control
## Hanging card inside a fixed monitor. Pointer positions use the parent window's space.

const PORTRAIT = preload("res://card/image/carmen.png")
const DISPLAY_SHADER = preload("res://character_preview/carmen_display.gdshader")
const STUDIO_SHADER = preload("res://character_preview/carmen_studio.gdshader")
const Motion = preload("res://character_preview/lanyard_motion.gd")
const ART_HEIGHT := 3.6
const CARD_SIZE := Vector2(2.64, 3.88)
const RIBBON_WIDTH := 0.16
const RIBBON_SAMPLES := 48
const REST_YAW := 0.20943951
const MAX_RENDER_PIXELS := 4000000.0
const BODY_BOUNDS := Motion.BODY_BOUNDS

var viewport_3d: SubViewport
var camera: Camera3D
var screen: Node3D
var artwork: MeshInstance3D
var rim: MeshInstance3D
var name_label: Label3D
var title_label: Label3D
var number_label: Label3D
var motion := Motion.new()
var _view: TextureRect
var render_scale := 2.0
var can_begin_drag: Callable
var _geometry: Array[MeshInstance3D] = []
var _card: Node3D
var _ribbon: MeshInstance3D
var _strap_material: StandardMaterial3D
var _pointer := -2
var _grab_depth := 0.0
var _narrow := false
var _view_height := 5.35
var _monitor: Node3D
var _monitor_geometry: Array[MeshInstance3D] = []
var _monitor_foot: MeshInstance3D
var _monitor_spec := Vector2.ZERO
var _aperture := Rect2()
var _monitor_mode := false


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	focus_mode = Control.FOCUS_NONE
	_view = TextureRect.new()
	_view.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_view.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_view.stretch_mode = TextureRect.STRETCH_SCALE
	_view.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_view.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	add_child(_view)
	viewport_3d = SubViewport.new()
	viewport_3d.transparent_bg = true
	viewport_3d.own_world_3d = true
	viewport_3d.msaa_3d = Viewport.MSAA_4X
	viewport_3d.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(viewport_3d)
	_view.texture = viewport_3d.get_texture()
	var world := Node3D.new()
	viewport_3d.add_child(world)
	camera = Camera3D.new()
	# Orthographic framing intentionally retains the illustration's legibility.
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.keep_aspect = Camera3D.KEEP_HEIGHT
	camera.position = Vector3(0, 0, 12)
	camera.current = true
	world.add_child(camera)
	var environment := WorldEnvironment.new()
	environment.environment = Environment.new()
	environment.environment.background_mode = Environment.BG_COLOR
	environment.environment.background_color = Color.TRANSPARENT
	environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.environment.ambient_light_color = Color("e0e2e5")
	environment.environment.ambient_light_energy = 0.32
	var studio := ShaderMaterial.new()
	studio.shader = STUDIO_SHADER
	var reflection_sky := Sky.new()
	reflection_sky.sky_material = studio
	reflection_sky.radiance_size = Sky.RADIANCE_SIZE_256
	reflection_sky.process_mode = Sky.PROCESS_MODE_QUALITY
	environment.environment.sky = reflection_sky
	environment.environment.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	world.add_child(environment)
	for settings: Vector3 in [Vector3(-35, -38, 1.15), Vector3(18, 55, 0.35)]:
		var light := DirectionalLight3D.new()
		light.rotation_degrees = Vector3(settings.x, settings.y, 0)
		light.light_energy = settings.z
		world.add_child(light)
	screen = Node3D.new()
	screen.name = "HangingCardDisplay"
	world.add_child(screen)
	_card = Node3D.new()
	_card.name = "CarmenCharacterCard"
	screen.add_child(_card)
	var shell := _metal(Color("41454b"), 0.42)
	var silver := _metal(Color("d9dce1"), 0.28)
	var lip := _metal(Color("60656c"), 0.30)
	var gasket := _solid(Color("16181c"))
	gasket.roughness = 0.68
	# Broad, stepped bevels survive minification; no stack of hairline highlights.
	_box(_card, "ThinSleeve", Vector3(0, 0, -0.025), Vector3(CARD_SIZE.x, CARD_SIZE.y, 0.20), 0.11, shell)
	var shoulder := CARD_SIZE - Vector2.ONE * 0.10
	var opening := Vector2(ART_HEIGHT * PORTRAIT.get_size().aspect(), ART_HEIGHT)
	var seal := opening + Vector2(0.05, 0.07)
	var bevel_mid := CARD_SIZE - Vector2.ONE * 0.04
	_bevel(_card, "MachinedSilverShoulder", CARD_SIZE, bevel_mid, 0.11, 0.075, 0.11, silver, 0.09)
	_bevel(_card, "RoundedSilverCrown", bevel_mid, shoulder, 0.09, 0.11, 0.13, silver, 0.06)
	rim = _bevel(_card, "SleeveLip", shoulder, seal, 0.06, 0.13, 0.125, lip, 0.025)
	_bevel(_card, "RecessedSeal", seal, opening + Vector2.ONE * 0.004, 0.025, 0.125, 0.085, gasket, 0.003)
	var rear_edge := _bevel(_card, "RearSilverShoulder", CARD_SIZE, shoulder, 0.11, 0.125, 0.145, silver, 0.06)
	rear_edge.rotation.y = PI
	_box(_card, "RearPanel", Vector3(0, 0, -0.135), Vector3(shoulder.x, shoulder.y, 0.02), 0.06, shell)
	var glass := ShaderMaterial.new()
	glass.shader = DISPLAY_SHADER
	glass.set_shader_parameter("portrait", PORTRAIT)
	glass.set_shader_parameter("sheen", 0.65)
	artwork = MeshInstance3D.new()
	artwork.name = "CompleteOriginalIllustration"
	var image_plane := QuadMesh.new()
	image_plane.size = Vector2(ART_HEIGHT * PORTRAIT.get_size().aspect(), ART_HEIGHT)
	artwork.mesh = image_plane
	artwork.material_override = glass
	artwork.position.z = 0.089
	_card.add_child(artwork)
	_geometry.append(artwork)
	_box(_card, "AttachmentTab", Vector3(0, 1.93, 0), Vector3(0.34, 0.18, 0.10), 0.035, shell)
	var tab_edge := _bevel(_card, "TabSilverBevel", Vector2(0.34, 0.18), Vector2(0.29, 0.13), 0.035, 0.05, 0.075, silver, 0.025)
	tab_edge.position.y = 1.93
	_ring(_card, "Eyelet", Vector3(0, 1.96, 0.085), 0.05, 0.014, silver)
	_ring(_card, "SplitRing", Vector3(0, 2.045, 0.085), 0.087, 0.015, silver)
	_box(_card, "StrapClamp", Vector3(0, Motion.HANG, 0.07), Vector3(0.21, 0.09, 0.085), 0.018, lip)
	var clamp_edge := _bevel(_card, "ClampSilverBevel", Vector2(0.21, 0.09), Vector2(0.18, 0.06), 0.018, 0.113, 0.128, silver, 0.01)
	clamp_edge.position.y = Motion.HANG
	# Identity belongs on the reverse; never overwrite text baked into new art.
	name_label = _label3d(0.30, 64, Color("e0e2e6"))
	title_label = _label3d(0.17, 40, Color("a9adb5"))
	number_label = _label3d(0.18, 40, Color("a9adb5"))
	number_label.text = "01  /  MANILA"
	for label: Label3D in [name_label, title_label, number_label]:
		label.rotation.y = PI
		label.position.z = -0.149
	name_label.position.y = 0.12
	title_label.position.y = -0.25
	number_label.position.y = 1.36
	_strap_material = _solid(Color("34363b"))
	_strap_material.roughness = 0.92
	_strap_material.normal_enabled = true
	_strap_material.normal_texture = _weave_normal()
	_strap_material.normal_scale = 0.30
	_strap_material.cull_mode = BaseMaterial3D.CULL_DISABLED
	_ribbon = MeshInstance3D.new()
	_ribbon.name = "WovenLanyard"
	_ribbon.material_override = _strap_material
	screen.add_child(_ribbon)
	_geometry.append(_ribbon)
	visibility_changed.connect(_visibility_changed)
	get_window().focus_exited.connect(cancel_drag)
	motion.configure(Rect2(-2, -2.675, 4, 5.35), false)
	_apply_pose()
	set_process(false)


func set_identity(display_name: String, title: String, font: Font) -> void:
	name_label.text = display_name
	title_label.text = title
	for label: Label3D in [name_label, title_label, number_label]:
		label.font = font


func arrange(rect: Rect2, _unit: float, monitor_mode := false) -> void:
	position = rect.position.round()
	size = rect.size.round().max(Vector2.ONE)
	_narrow = get_window().size.x < 550
	_monitor_mode = monitor_mode
	_update_render_size()
	if _monitor_mode:
		_view_height = 5.40 if _narrow else 5.96
		var border_width := 0.28 if _narrow else 0.50
		var aperture_width := maxf(3.20 if _narrow else 3.80, _view_height * size.aspect() - border_width - 0.18)
		_build_monitor(Vector2(aperture_width, 4.60 if _narrow else 4.86))
		_view_height = maxf(_view_height, (aperture_width + border_width + 0.18) / size.aspect())
		camera.size = _view_height
		_monitor.show()
		motion.rest = 0.075
		motion.configure(_aperture.grow(-0.05), _narrow)
		motion.anchor.x -= _aperture.size.x * 0.10
	else:
		if is_instance_valid(_monitor):
			_monitor.hide()
		var required_width := 3.0 if _narrow else 3.65
		_view_height = maxf(5.20, required_width / size.aspect())
		camera.size = _view_height
		motion.rest = 0.21
		motion.configure(Rect2(Vector2(-_view_height * size.aspect(), -_view_height) * 0.5,
			Vector2(_view_height * size.aspect(), _view_height)).grow(-0.035), _narrow)
		motion.anchor.y = minf(motion.anchor.y, 2.52)
	cancel_drag()


func _build_monitor(opening: Vector2) -> void:
	if _monitor_spec.is_equal_approx(opening):
		return
	if is_instance_valid(_monitor):
		_monitor.free()
	_monitor_geometry.clear()
	_monitor_spec = opening
	_monitor = Node3D.new()
	_monitor.name = "FixedDesktopMonitor"
	_monitor.position.y = 0.13 if _narrow else 0.24
	screen.get_parent().add_child(_monitor)
	_aperture = Rect2(Vector2(-opening.x * 0.5, _monitor.position.y - opening.y * 0.5), opening)
	var outer := opening + Vector2(0.28, 0.28) if _narrow else opening + Vector2(0.50, 0.46)
	var housing := _solid(Color("555962"))
	housing.roughness = 0.60
	var edge := _metal(Color("9b9fa7"), 0.44)
	var inner := _solid(Color("1d2027"))
	inner.roughness = 0.54
	var backing := _solid(Color("242a36"))
	backing.roughness = 0.34
	backing.emission_enabled = true
	backing.emission = Color("202a3c")
	backing.emission_energy_multiplier = 0.22
	# Only the recessed backing is closed; every front surface leaves the display open.
	_box(_monitor, "RearHousing", Vector3(0.025, 0, -1.23), Vector3(outer.x, outer.y, 0.30), 0.13, inner)
	_box(_monitor, "RecessedDisplay", Vector3(0, 0, -0.98), Vector3(opening.x, opening.y, 0.04), 0.025, backing)
	_bevel(_monitor, "CaseShoulder", outer, outer - Vector2.ONE * 0.10, 0.13, -1.08, 0.48, housing, 0.10)
	_bevel(_monitor, "SilverCaseEdge", outer - Vector2.ONE * 0.10, outer - Vector2.ONE * 0.14, 0.10, 0.48, 0.52, edge, 0.08)
	_bevel(_monitor, "MatteFrontBezel", outer - Vector2.ONE * 0.14, opening + Vector2.ONE * 0.06, 0.08, 0.52, 0.52, housing, 0.04)
	_bevel(_monitor, "RecessedInnerBezel", opening + Vector2.ONE * 0.06, opening, 0.04, 0.52, 0.34, inner, 0.025)
	var bottom := -outer.y * 0.5
	var neck_height := 0.18 if _narrow else 0.32
	_box(_monitor, "MonitorNeck", Vector3(0, bottom - neck_height * 0.35, -0.40), Vector3(0.46, neck_height, 0.40), 0.045, housing)
	_monitor_foot = _box(_monitor, "MonitorFoot", Vector3(0, bottom - neck_height + 0.02, 0),
		Vector3(1.55 if _narrow else 2.35, 0.12 if _narrow else 0.14, 0.34 if _narrow else 0.55), 0.045, housing)
	_monitor_foot.rotation.x = -0.45
	var led := _solid(Color("b0c4dc"))
	led.emission_enabled = true
	led.emission = Color("819fca")
	led.emission_energy_multiplier = 0.65
	_box(_monitor, "PowerIndicator", Vector3(outer.x * 0.5 - 0.30, -opening.y * 0.5 - 0.07, 0.54), Vector3(0.055, 0.025, 0.025), 0.008, led)
	for i in 3:
		_box(_monitor, "ControlKey%d" % i, Vector3(outer.x * 0.5 - 0.48 - i * 0.11, -opening.y * 0.5 - 0.07, 0.54), Vector3(0.065, 0.025, 0.025), 0.005, inner)


func display_rect() -> Rect2:
	if not _monitor_mode:
		return image_rect()
	var top_left := _project_world(Vector3(_aperture.position.x, _aperture.end.y, 0.34))
	var bottom_right := _project_world(Vector3(_aperture.end.x, _aperture.position.y, 0.34))
	return Rect2(top_left, bottom_right - top_left)


func monitor_rect() -> Rect2:
	var result := display_rect()
	if _monitor_mode:
		for model in _monitor_geometry:
			result = result.merge(_project_bounds(model, model.mesh.get_aabb()))
	return result


func monitor_foot_rect() -> Rect2:
	return _project_bounds(_monitor_foot, _monitor_foot.mesh.get_aabb()) if _monitor_mode else Rect2()


func protect_foreground(screen_x: float) -> void:
	var local := _plane_point(Vector2(screen_x, global_position.y + size.y * 0.5), 0.0)
	motion.protect_right_edge(local.x)


func _update_render_size() -> void:
	var factor := minf(render_scale, sqrt(MAX_RENDER_PIXELS / maxf(1.0, size.x * size.y)))
	viewport_3d.size = Vector2i((size * factor).round().max(Vector2(2, 2)))


func cancel_drag() -> void:
	_pointer = -2
	motion.reset()
	if is_instance_valid(_card):
		_apply_pose()
	set_process(false)


func _visibility_changed() -> void:
	cancel_drag()
	viewport_3d.render_target_update_mode = SubViewport.UPDATE_ALWAYS if is_visible_in_tree() else SubViewport.UPDATE_DISABLED


func _exit_tree() -> void:
	_pointer = -2
	motion.reset()


func _input(event: InputEvent) -> void:
	if not is_visible_in_tree():
		return
	if event is InputEventScreenTouch:
		if event.pressed:
			if _pointer == -2:
				_begin_drag(event.position, event.index)
		elif _pointer == event.index:
			if event.canceled:
				cancel_drag()
			else:
				_end_drag()
			get_viewport().set_input_as_handled()
			return
		if _pointer == event.index:
			get_viewport().set_input_as_handled()
	elif event is InputEventScreenDrag and _pointer == event.index:
		_move_drag(event.position)
		get_viewport().set_input_as_handled()
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		# Godot emits device -1 mouse events for touch. Touch owns its own grab.
		if event.device == -1 or _pointer >= 0:
			return
		if event.pressed and _pointer == -2:
			_begin_drag(event.position, -1)
		elif not event.pressed and _pointer == -1:
			_end_drag()
			get_viewport().set_input_as_handled()
	elif event is InputEventMouseMotion and _pointer == -1 and event.device != -1:
		_move_drag(event.position)
		get_viewport().set_input_as_handled()


func _begin_drag(point: Vector2, pointer: int) -> void:
	if not get_global_rect().has_point(point):
		return
	if _monitor_mode and not display_rect().has_point(point):
		return
	var hit := card_hit(point)
	if not hit.is_finite():
		return
	if can_begin_drag.is_valid() and not can_begin_drag.call(point):
		return
	_pointer = pointer
	_grab_depth = _card.to_global(hit).z
	var target := _plane_point(point, _grab_depth)
	var planar_grip := Basis(Vector3.UP, REST_YAW + motion.yaw) * hit
	motion.begin(Vector2(planar_grip.x, planar_grip.y), Vector2(target.x, target.y))
	set_process(true)
	get_viewport().set_input_as_handled()


func card_hit(point: Vector2) -> Vector3:
	var pixel := (point - global_position) * Vector2(viewport_3d.size) / size
	var ray := camera.project_ray_origin(pixel)
	var direction := camera.project_ray_normal(pixel)
	var plane := Plane(_card.global_basis.z, _card.global_position + _card.global_basis.z * artwork.position.z)
	var hit = plane.intersects_ray(ray, direction)
	if hit == null:
		return Vector3.INF
	var local := _card.to_local(hit)
	if absf(local.x) > CARD_SIZE.x * 0.5 or absf(local.y) > CARD_SIZE.y * 0.5:
		return Vector3.INF
	return local


func _plane_point(point: Vector2, depth: float) -> Vector3:
	var pixel := (point - global_position) * Vector2(viewport_3d.size) / size
	var result = Plane(Vector3.FORWARD, -depth).intersects_ray(camera.project_ray_origin(pixel), camera.project_ray_normal(pixel))
	return result if result != null else Vector3.ZERO


func _move_drag(point: Vector2) -> void:
	var target := _plane_point(point, _grab_depth)
	motion.target = Vector2(target.x, target.y)


func _end_drag() -> void:
	_pointer = -2
	motion.release()


func _process(delta: float) -> void:
	if motion.advance(delta):
		_apply_pose()
	if motion.sleeping:
		set_process(false)


func _apply_pose() -> void:
	_card.position = Vector3(motion.center.x, motion.center.y, 0)
	_card.basis = Basis(Vector3.BACK, motion.angle) * Basis(Vector3.UP, REST_YAW + motion.yaw)
	_update_ribbon()


func _update_ribbon() -> void:
	var path := Curve3D.new()
	for i in motion.nodes.size():
		var point := motion.nodes[i]
		var tangent := Vector2.ZERO
		if i > 0 and i < Motion.LINKS:
			tangent = (motion.nodes[i + 1] - motion.nodes[i - 1]) / 6.0
		var position_3d := Vector3(point.x, point.y, 0.08)
		if i == Motion.LINKS:
			position_3d = _card.to_global(Vector3(0, Motion.HANG, 0.08))
		path.add_point(position_3d, Vector3(-tangent.x, -tangent.y, 0), Vector3(tangent.x, tangent.y, 0))
	path.bake_interval = 0.015
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	var vertices: Array[Vector3] = []
	var colors: Array[Color] = []
	var uvs: Array[Vector2] = []
	for i in RIBBON_SAMPLES + 1:
		var distance := path.get_baked_length() * i / RIBBON_SAMPLES
		var point := path.sample_baked(distance)
		var tangent := path.sample_baked(minf(distance + 0.012, path.get_baked_length())) - path.sample_baked(maxf(distance - 0.012, 0))
		var side := Vector3(tangent.y, -tangent.x, 0).normalized()
		for column in [0.0, 0.09, 0.91, 1.0]:
			vertices.append(point + side * (column - 0.5) * RIBBON_WIDTH)
			uvs.append(Vector2(column * 2.0, distance * 12.5))
			var shade := 0.62 if column == 0.0 or column == 1.0 else (1.15 if i % 3 == 0 else 0.94)
			colors.append(Color(shade, shade, shade))
	for i in RIBBON_SAMPLES:
		for column in 3:
			var a := i * 4 + column
			for index in [a, a + 4, a + 1, a + 1, a + 4, a + 5]:
				surface.set_color(colors[index])
				surface.set_uv(uvs[index])
				surface.add_vertex(vertices[index])
	surface.generate_normals()
	surface.generate_tangents()
	_ribbon.mesh = surface.commit()


func project_point(point: Vector3) -> Vector2:
	return _project_world(screen.to_global(point))


func _project_world(point: Vector3) -> Vector2:
	return global_position + camera.unproject_position(point) * size / Vector2(viewport_3d.size)


func art_point(uv: Vector2) -> Vector2:
	var dimensions: Vector2 = artwork.mesh.size
	return _project_world(artwork.to_global(Vector3((uv.x - 0.5) * dimensions.x, (0.5 - uv.y) * dimensions.y, 0)))


func image_rect() -> Rect2:
	return _project_bounds(artwork, artwork.mesh.get_aabb())


func _project_bounds(node: Node3D, box: AABB) -> Rect2:
	var result := Rect2()
	for corner in 8:
		var pixel := _project_world(node.to_global(box.get_endpoint(corner)))
		result = Rect2(pixel, Vector2.ZERO) if corner == 0 else result.expand(pixel)
	return result


func card_rect() -> Rect2:
	return _project_bounds(_card, BODY_BOUNDS)


func visual_rect() -> Rect2:
	var result := card_rect()
	for model in _geometry:
		if model.mesh != null:
			result = result.merge(_project_bounds(model, model.mesh.get_aabb()))
	return result


func text_rects() -> Array[Rect2]:
	return []


func plate_rect() -> Rect2:
	return Rect2()


func _label3d(pixel_height: float, font_size: int, color: Color) -> Label3D:
	var label := Label3D.new()
	label.pixel_size = pixel_height / font_size
	label.font_size = font_size
	label.modulate = color
	label.outline_size = 0
	label.no_depth_test = false
	label.double_sided = false
	label.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR
	_card.add_child(label)
	return label


func _solid(color: Color) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.vertex_color_use_as_albedo = true
	material.albedo_color = color
	return material


func _metal(color: Color, roughness: float) -> StandardMaterial3D:
	var material := _solid(color)
	material.metallic = 1.0
	material.roughness = roughness
	material.clearcoat_enabled = true
	material.clearcoat = 0.65
	material.clearcoat_roughness = 0.16
	return material


func _weave_normal() -> ImageTexture:
	var image := Image.create(64, 64, false, Image.FORMAT_RGB8)
	for y in 64:
		for x in 64:
			var warp := sin(float(x) / 64.0 * TAU * 4.0)
			var weft := sin(float(y) / 64.0 * TAU * 4.0)
			var normal := Vector3(warp * 0.32, weft * 0.20, 1.0).normalized()
			image.set_pixel(x, y, Color(normal.x * 0.5 + 0.5, normal.y * 0.5 + 0.5, normal.z * 0.5 + 0.5))
	image.generate_mipmaps()
	return ImageTexture.create_from_image(image)


func _outline(dimensions: Vector2, cut: float) -> PackedVector2Array:
	var half := dimensions * 0.5
	return PackedVector2Array([Vector2(-half.x + cut, half.y), Vector2(half.x - cut, half.y),
		Vector2(half.x, half.y - cut), Vector2(half.x, -half.y + cut), Vector2(half.x - cut, -half.y),
		Vector2(-half.x + cut, -half.y), Vector2(-half.x, -half.y + cut), Vector2(-half.x, half.y - cut)])


func _bevel(parent: Node3D, node_name: String, outer: Vector2, inner: Vector2, cut: float,
		outer_z: float, inner_z: float, material: Material, inner_cut: float = -1.0) -> MeshInstance3D:
	var a := _outline(outer, cut)
	var b := _outline(inner, maxf(0.003, cut * 0.40) if inner_cut < 0.0 else inner_cut)
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in 8:
		var j := (i + 1) % 8
		for point: Vector3 in [Vector3(a[i].x, a[i].y, outer_z), Vector3(a[j].x, a[j].y, outer_z),
				Vector3(b[i].x, b[i].y, inner_z), Vector3(b[i].x, b[i].y, inner_z),
				Vector3(a[j].x, a[j].y, outer_z), Vector3(b[j].x, b[j].y, inner_z)]:
			surface.set_color(Color.WHITE)
			surface.add_vertex(point)
	return _mesh(parent, node_name, Vector3.ZERO, surface, material)


func _box(parent: Node3D, node_name: String, center: Vector3, dimensions: Vector3, cut: float, material: Material) -> MeshInstance3D:
	var corners := _outline(Vector2(dimensions.x, dimensions.y), cut)
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in 8:
		var j := (i + 1) % 8
		var a := Vector3(corners[i].x, corners[i].y, dimensions.z * 0.5)
		var b := Vector3(corners[j].x, corners[j].y, dimensions.z * 0.5)
		var rear := Vector3(0, 0, -dimensions.z)
		for point: Vector3 in [Vector3(0, 0, dimensions.z * 0.5), a, b,
				Vector3(0, 0, -dimensions.z * 0.5), b + rear, a + rear,
				a, a + rear, b, b, a + rear, b + rear]:
			surface.set_color(Color.WHITE)
			surface.add_vertex(point)
	return _mesh(parent, node_name, center, surface, material)


func _mesh(parent: Node3D, node_name: String, center: Vector3, surface: SurfaceTool, material: Material) -> MeshInstance3D:
	surface.generate_normals()
	var model := MeshInstance3D.new()
	model.name = node_name
	model.mesh = surface.commit()
	model.material_override = material
	model.position = center
	parent.add_child(model)
	if parent == _monitor:
		_monitor_geometry.append(model)
	else:
		_geometry.append(model)
	return model


func _ring(parent: Node3D, node_name: String, center: Vector3, radius: float, thickness: float, material: Material) -> void:
	var model := MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = radius - thickness
	torus.outer_radius = radius + thickness
	torus.rings = 24
	torus.ring_segments = 8
	model.mesh = torus
	model.name = node_name
	model.material_override = material
	model.position = center
	model.rotation.x = PI * 0.5
	parent.add_child(model)
	_geometry.append(model)
