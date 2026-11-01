extends Node3D

const Pixel := preload("res://card/pixel_card_theme.gd")
const WATER := preload("res://demo/harbor_hd2d/harbor_water.gdshader")
const ATLAS_SHADER := preload("res://demo/harbor_hd2d/art/harbor_atlas.gdshader")
const ATLAS := preload("res://demo/harbor_hd2d/art/harbor_atlas.png")
const Buildings := preload("res://demo/harbor_hd2d/harbor_buildings.gd")
const INSURANCE := preload("res://demo/harbor_hd2d/art/insurance_rebuild_r2/insurance_rebuild_r2_1.glb")
const CARGO_COLORS := [Color("d5ac4d"), Color("568ebb"), Color("67a764")]
const LANE_X := [-6.0, 0.0, 6.0]
const OVERVIEW_TARGET := Vector3(0, 0, -2.0)
const OVERVIEW_OFFSET := Vector3(1.0, 43, 31)
const INK := Color("30252c")
const WOOD := Color("94704e")
const INSPECTION_MIN_ZOOM := 0.25
const INSPECTION_MAX_ZOOM := 2.0
const INSPECTION_MIN_PITCH := 10.0
const INSPECTION_MAX_PITCH := 80.0

var inspecting := false
var inspection_bounds := AABB()
var inspection_target := Vector3.ZERO
var inspection_yaw := 35.0
var inspection_pitch := 32.0
var inspection_zoom := 1.0
var _inspection_radius := 1.0
var camera: Camera3D
var boats: Array[Node3D] = []
var boat_visuals: Array[Node3D] = []
var anchors: Dictionary = {}
var district_anchors: Dictionary = {}
var markers: Dictionary = {}
var overview_size := 36.8
var camera_blend := 0.0
var focus_ship := 1
var sailing := false
var elapsed := 0.0
var _materials: Dictionary = {}
var _rng := RandomNumberGenerator.new()
var _static_root: Node3D
var _buildings: RefCounted


func _ready() -> void:
	_rng.seed = 41972
	_lighting()
	_static_root = Node3D.new()
	_static_root.name = "IllustratedHarborBoard"
	add_child(_static_root)
	_buildings = Buildings.new(_box, _quad, _triangle)
	_build_port()
	for i in 3:
		_build_boat(i)
	_batch_static_geometry()
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.near = 0.15
	camera.far = 180.0
	add_child(camera)
	camera.current = true
	_update_camera()


func route_point(ship: int, step: int) -> Vector3:
	return Vector3(LANE_X[ship], 0, -10.5 if step > 13 else 11.5 - step * 1.68)


func set_positions(steps: Array) -> void:
	for i in 3:
		boats[i].position = route_point(i, int(steps[i]))


func slot_position(id: String) -> Vector3:
	var anchor: Node3D = anchors[id]
	return anchor.global_position


func place_crew(id: String, color: Color) -> void:
	if markers.has(id):
		return
	var anchor: Node3D = anchors[id]
	var pawn := Node3D.new()
	anchor.add_child(pawn)
	_cylinder(pawn, Vector3(0, 0.04, 0), 0.36, 0.09, INK)
	_cylinder(pawn, Vector3(0, 0.33, 0), 0.25, 0.49, color.darkened(0.12))
	_box(pawn, Vector3(0, 0.40, 0), Vector3(0.68, 0.20, 0.30), color)
	_cylinder(pawn, Vector3(0, 0.74, 0), 0.25, 0.30, color)
	markers[id] = pawn


func clear_owners() -> void:
	for pawn: Node3D in markers.values():
		pawn.get_parent().remove_child(pawn)
		pawn.queue_free()
	markers.clear()


func _process(delta: float) -> void:
	elapsed += delta
	for i in boat_visuals.size():
		boat_visuals[i].position.y = sin(elapsed * 1.4 + i * 2.0) * 0.025
		boat_visuals[i].rotation.z = sin(elapsed * 0.93 + i) * 0.005
	_update_camera()


func begin_inspection() -> bool:
	if inspecting or sailing or camera == null:
		return false
	var insurance := get_node_or_null("InsuranceBlender")
	if insurance == null:
		return false
	var crane := insurance.find_child("INS_CraneGeometry", true, false) as MeshInstance3D
	if crane == null or crane.mesh == null:
		return false
	var bounds := crane.mesh.get_aabb()
	if bounds.size.length_squared() <= 0.01:
		return false
	var transform := global_transform.affine_inverse() * crane.global_transform
	inspection_bounds = AABB(transform * bounds.get_endpoint(0), Vector3.ZERO)
	for corner in range(1, 8):
		inspection_bounds = inspection_bounds.expand(transform * bounds.get_endpoint(corner))
	inspection_target = inspection_bounds.get_center()
	_inspection_radius = inspection_bounds.size.length() * 0.5
	inspection_yaw = 35.0
	inspection_pitch = 32.0
	inspection_zoom = 1.0
	inspecting = true
	_update_camera()
	return true


func end_inspection() -> void:
	inspecting = false
	_update_camera()


func orbit_inspection(delta: Vector2) -> void:
	if not inspecting:
		return
	inspection_yaw = wrapf(inspection_yaw - delta.x * 180.0, -180.0, 180.0)
	inspection_pitch = clampf(inspection_pitch + delta.y * 120.0, INSPECTION_MIN_PITCH, INSPECTION_MAX_PITCH)
	_update_camera()


func zoom_inspection(steps: float) -> void:
	if not inspecting:
		return
	inspection_zoom = clampf(inspection_zoom * pow(0.85, clampf(steps, -20.0, 20.0)), INSPECTION_MIN_ZOOM, INSPECTION_MAX_ZOOM)
	_update_camera()


func _update_camera() -> void:
	if camera == null:
		return
	if inspecting:
		var yaw := deg_to_rad(inspection_yaw)
		var pitch := deg_to_rad(inspection_pitch)
		var direction := Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch))
		camera.position = inspection_target + direction * (_inspection_radius * 3.0 + 2.0)
		camera.look_at(to_global(inspection_target))
		var view_size := get_viewport().get_visible_rect().size
		var aspect := view_size.x / maxf(view_size.y, 1.0)
		# Sphere fitting stays stable while orbiting; only the viewport aspect changes the baseline.
		var fit := _inspection_radius * 2.16
		camera.size = fit * maxf(1.0, aspect) * inspection_zoom if camera.keep_aspect == Camera3D.KEEP_WIDTH else fit / minf(aspect, 1.0) * inspection_zoom
		return
	var target := boats[focus_ship].position + Vector3(0, 0.8, -1.3)
	var close_position := target + Vector3(11.8, 8.2, 13.2)
	camera.position = (OVERVIEW_TARGET + OVERVIEW_OFFSET).lerp(close_position, camera_blend)
	camera.look_at(OVERVIEW_TARGET.lerp(target, camera_blend))
	camera.size = lerpf(overview_size, 17.0, camera_blend)


func _lighting() -> void:
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color("252630")
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("d4d7d5")
	environment.ambient_light_energy = 0.72
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	var world_environment := WorldEnvironment.new()
	world_environment.environment = environment
	add_child(world_environment)
	var sunlight := DirectionalLight3D.new()
	sunlight.rotation_degrees = Vector3(-58, -28, 0)
	sunlight.light_color = Color("ffe4bc")
	sunlight.light_energy = 0.85
	sunlight.shadow_enabled = true
	sunlight.directional_shadow_max_distance = 110
	sunlight.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	sunlight.shadow_bias = 0.025
	add_child(sunlight)


func _coast(z: float, side: int) -> float:
	return side * (10.9 + sin(z * 0.30 + side * 0.6) * 1.05 + sin(z * 0.67) * 0.35)


func _land_outline(side: int, inset := 0.0) -> PackedVector2Array:
	var points := PackedVector2Array()
	points.append(Vector2(side * 28.8, -21.8))
	points.append(Vector2(side * 28.8, 15.6))
	for j in range(38, -1, -1):
		var z := -21.8 + j * 37.4 / 38.0
		points.append(Vector2(_coast(z, side) + side * inset, z))
	return points


func _build_port() -> void:
	# The sea and islands share a bounded board, with visible layered earth at its edge.
	_box(_static_root, Vector3(0, -1.8, -3.1), Vector3(59.3, 0.35, 39.1), INK)
	_box(_static_root, Vector3(0, -1.15, -3.1), Vector3(58.6, 1.0, 38.5), Color("775338"), 8)
	_box(_static_root, Vector3(0, -0.58, -3.1), Vector3(58.2, 0.20, 38.2), Color("bc8950"))
	_box(_static_root, Vector3(0, -0.30, 15.55), Vector3(22.4, 0.65, 0.20), Color("3e718d"))
	var ocean := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(57.6, 37.4)
	ocean.mesh = plane
	var water_material := ShaderMaterial.new()
	water_material.shader = WATER
	ocean.material_override = water_material
	ocean.position = Vector3(0, -0.12, -3.1)
	_static_root.add_child(ocean)
	for side in [-1, 1]:
		_prism(_static_root, _land_outline(side), -0.6, 0.04, Color("e1ac62"), 1.0, 7)
		_prism(_static_root, _land_outline(side, 0.85), 0.04, 0.30, Color.WHITE, 1.0, 6)
		for j in 38:
			var za := -21.8 + j * 37.4 / 38.0
			var zb := -21.8 + (j + 1) * 37.4 / 38.0
			var a := Vector3(_coast(za, side) - side * 0.16, -0.06, za)
			var b := Vector3(_coast(zb, side) - side * 0.16, -0.06, zb)
			_beam(_static_root, a, b, 0.12, Color("c5f1df"))
	_box(_static_root, Vector3(0, 0.04, -18.8), Vector3(32, 0.38, 6.0), Color.WHITE, 5)
	_dock(Vector3(0, 0.49, -15.3), Vector2(22, 2.8))
	for x in [-9.0, -3.0, 3.0, 9.0]:
		_dock(Vector3(x, 0.46, -12.4), Vector2(0.9, 5.8))
	for i in 3:
		_add_slot("harbor_%d" % i, _static_root, Vector3(LANE_X[i], 0.72, -15.1))
	for step in 14:
		var z := route_point(0, step).z
		for side in [-1, 1]:
			_water_number(str(step), Vector3(side * 9.4, -0.015, z))
		for j in 32:
			var x0 := -8.6 + j * 17.2 / 32.0
			var x1 := -8.6 + (j + 1) * 17.2 / 32.0
			_beam(_static_root, Vector3(x0, -0.075, z + sin(x0 * 1.12) * 0.12), Vector3(x1, -0.075, z + sin(x1 * 1.12) * 0.12), 0.075, Color("b5e3e0"))
	_warehouse(Vector3(-4.2, 0.26, -19.1), Vector2(10.3, 4.8), 3.3, 3, 2)
	_warehouse(Vector3(5.8, 0.26, -19.1), Vector2(8.4, 4.8), 3.2, 4, 1)
	_house(Vector3(-21.0, 0.3, -8.4), Vector2(4.5, 3.4), 2.0, 4, 1)
	_house(Vector3(-25.0, 0.3, -4.6), Vector2(3.8, 3.2), 1.9, 4, 10)
	_house(Vector3(-20.5, 0.3, -1.2), Vector2(5.3, 4.2), 2.5, 8, 10)
	_sign(_static_root, Vector3(-20.5, 3.20, 1.02), "PIRATES", 4.1)
	_dock(Vector3(-14.6, 0.5, 1.8), Vector2(6.4, 3.0))
	for i in 2:
		_add_slot("pirate_%d" % i, _static_root, Vector3(-16.1 + i * 3.0, 0.69, 1.8))
	_navigator()
	_insurance()
	_shipyard()
	_market()
	for p in [Vector3(-25, 0.3, -15), Vector3(-16, 0.3, -11), Vector3(-26, 0.3, 4), Vector3(-26, 0.3, 12), Vector3(26, 0.3, -16), Vector3(27, 0.3, -4), Vector3(27, 0.3, 8), Vector3(23, 0.3, -20)]:
		_palm(p)
	for i in 45:
		var side: int = -1 if i % 2 == 0 else 1
		var p := Vector3(side * _rng.randf_range(25.4, 28.0), 0.3, _rng.randf_range(-19, 14))
		_bush(p, _rng.randf_range(0.55, 1.15))
	for p in [Vector3(-10, 0.9, -18), Vector3(9.9, 0.8, -18), Vector3(15, 0.8, -9.5), Vector3(-23.8, 0.8, 1.9), Vector3(25.0, 0.8, 5.6)]:
		for j in 3:
			_crate(_static_root, p + Vector3(j * 0.76, 0, 0), 0.68)
		_crate(_static_root, p + Vector3(0.40, 0.68, 0), 0.64)
	for side in [-1, 1]:
		for z in range(-18, 15, 3):
			_box(_static_root, Vector3(side * 28.2, 0.86, z), Vector3(0.16, 1.25, 0.18), Color.WHITE, 0)
		for y in [0.70, 1.25]:
			_box(_static_root, Vector3(side * 28.2, y, -2), Vector3(0.12, 0.13, 34), Color.WHITE, 0)
	district_anchors = {
		"到港泊位": Vector3(0, 0.8, -16.8),
		"海盗湾": Vector3(-14.6, 0.8, -0.6),
		"引航员": Vector3(-17.8, 0.8, 7.0),
		"保险公司": Vector3(15.1, 0.9, -11.3),
		"修船厂": Vector3(17.2, 0.9, 1.9),
	}


func _navigator() -> void:
	_dock(Vector3(-18.3, 0.5, 9.6), Vector2(13.2, 3.1))
	for i in 6:
		_box(_static_root, Vector3(-23.6 + i * 2.1, 0.59, 9.6), Vector3(0.06, 0.025, 2.8), Color("d9bd79"))
	_sign(_static_root, Vector3(-18.7, 1.45, 8.0), "NAVIGATOR", 6.0)
	for i in 2:
		_add_slot("pilot_%d" % i, _static_root, Vector3(-20.0 + i * 4.2, 0.70, 9.8))


func _insurance() -> void:
	var model: Node3D = INSURANCE.instantiate()
	model.name = "InsuranceBlender"
	model.position = Vector3(18.9, 0, -11.4)
	# Keep the building at full scale; fit only the dock and tug to this shoreline.
	var dock := model.find_child("INS_DockGeometry", true, false) as Node3D
	dock.scale = Vector3(1.12, 1, 1.16)
	dock.position = Vector3(-0.665, 0, 0.6)
	var tug := model.find_child("INS_TugGeometry", true, false) as Node3D
	tug.scale = Vector3.ONE * 0.52
	tug.rotation_degrees.y = -176.0
	var rope_end := Vector3(-6.65, 1.17, 3.69)
	var mooring := dock.transform * rope_end
	mooring.y = 0.5
	tug.position = mooring - tug.basis * rope_end
	_insurance_materials(model)
	# Keep imported surface materials outside the procedural atlas batch.
	add_child(model)
	_add_slot("insurance_0", _static_root, Vector3(15.1, 0.72, -8.3))


func _insurance_materials(node: Node) -> void:
	if node is MeshInstance3D:
		var instance := node as MeshInstance3D
		for surface in instance.mesh.get_surface_count():
			var imported := instance.mesh.surface_get_material(surface) as StandardMaterial3D
			if imported == null:
				continue
			var material := imported.duplicate() as StandardMaterial3D
			material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
			material.roughness = 1.0
			material.metallic = 0.0
			material.metallic_specular = 0.0
			instance.set_surface_override_material(surface, material)
	for child in node.get_children():
		_insurance_materials(child)


func _shipyard() -> void:
	_buildings.build_shipyard(_static_root, Vector3(20.0, 0.5, 2.0))
	for i in 3:
		_add_slot("shipyard_%d" % i, _static_root, [Vector3(14.9, 0.8, 2.8), Vector3(16.8, 0.8, 6.6), Vector3(24.3, 0.8, 6.6)][i])


func _market() -> void:
	var root := Node3D.new()
	root.position = Vector3(19.1, 0.4, 11.6)
	_static_root.add_child(root)
	_box(root, Vector3(0, 0.12, 0), Vector3(8.8, 0.35, 5.8), INK)
	_box(root, Vector3(0, 0.31, 0), Vector3(8.5, 0.17, 5.5), Color.WHITE, 0)
	var colors := [Color("c9544f"), Color("568bbb"), Color("d9b752"), Color("62a367")]
	for col in 4:
		for row in 5:
			_box(root, Vector3(-3.0 + col * 2.0, 0.43, -2.0 + row), Vector3(1.84, 0.06, 0.84), colors[col].darkened(row % 2 * 0.10))
		_cylinder(root, Vector3(-3.0 + col * 2.0, 0.61, -2.0 + [1, 3, 2, 0][col]), 0.57, 0.26, colors[col].lightened(0.15))
	for x in [-4.25, 4.25]:
		_box(root, Vector3(x, 0.54, 0), Vector3(0.20, 0.25, 5.9), Color.WHITE, 0)
	_sign(root, Vector3(0, 1.3, -2.95), "SHARES / 示例", 7.2)
	for i in 4:
		var names := ["丝绸 20", "肉蔻 10", "玉石 30", "人参 20"]
		_flat_text(root, names[i], Vector3(-3.0 + i * 2, 0.50, 2.30), 0.009, Color("fff0c7"))


func _build_boat(index: int) -> void:
	var boat := Node3D.new()
	boat.name = "CargoBoat%d" % index
	add_child(boat)
	boats.append(boat)
	var visual := Node3D.new()
	boat.add_child(visual)
	boat_visuals.append(visual)
	# Open cargo barges: broad deck, low sides, no sail hiding the placement seats.
	var outline := PackedVector2Array([Vector2(-1.55, 2.30), Vector2(-1.72, 0.8), Vector2(-1.62, -1.5), Vector2(-1.18, -2.35), Vector2(0, -2.80), Vector2(1.18, -2.35), Vector2(1.62, -1.5), Vector2(1.72, 0.8), Vector2(1.55, 2.30)])
	_prism(visual, outline, -0.18, 0.55, INK, 0.81)
	_prism(visual, outline, 0.10, 0.64, Color.WHITE, 0.94, 14)
	_prism(visual, outline, 0.63, 0.72, CARGO_COLORS[index], 1.0)
	_box(visual, Vector3(0, 0.76, 0.10), Vector3(2.98, 0.10, 4.10), Color.WHITE, 0)
	for j in outline.size():
		var a := Vector3(outline[j].x, 0.89, outline[j].y)
		var b := Vector3(outline[(j + 1) % outline.size()].x, 0.89, outline[(j + 1) % outline.size()].y)
		_beam(visual, a, b, 0.14, INK)
		_beam(visual, a + Vector3.UP * 0.04, b + Vector3.UP * 0.04, 0.08, Color("d5b575"))
	_box(visual, Vector3(0, 1.04, 2.05), Vector3(2.9, 0.40, 0.45), CARGO_COLORS[index].darkened(0.2))
	_box(visual, Vector3(0, 0.58, 2.57), Vector3(0.19, 0.75, 0.50), Color.WHITE, 8)
	for i in 2:
		_crate(visual, Vector3(-0.56 + i * 1.12, 1.02, -1.85), 0.66, CARGO_COLORS[index])
	var count := 4 if index == 2 else 3
	for seat in count:
		_add_slot("ship_%d_%d" % [index, seat], visual, Vector3(-0.90 + (seat % 2) * 1.80, 0.84, -0.65 + (seat / 2) * 2.0))
	var panel := _box(visual, Vector3(0, 0.85, 1.77), Vector3(1.35, 0.06, 0.31), CARGO_COLORS[index])
	panel.name = "CargoBadge"
	for side in [-1, 1]:
		for j in 4:
			_box(visual, Vector3(side * (1.82 + j * 0.10), -0.055, 0.6 + j * 0.45), Vector3(0.12, 0.024, 0.40), Color("bcdfd4"))


func _add_slot(id: String, parent: Node3D, p: Vector3) -> void:
	var anchor := Node3D.new()
	anchor.name = id
	anchor.position = p
	parent.add_child(anchor)
	anchors[id] = anchor
	var radius := 0.52 if id.begins_with("ship_") else 0.78
	for part in 8:
		var a := part * TAU / 8.0
		var b := a + TAU / 8.0 * 0.68
		for j in 3:
			var aa := lerpf(a, b, j / 3.0)
			var bb := lerpf(a, b, (j + 1) / 3.0)
			_beam(anchor, Vector3(cos(aa) * radius, 0.012, sin(aa) * radius), Vector3(cos(bb) * radius, 0.012, sin(bb) * radius), 0.10, Color("ffdf69"))


func _warehouse(p: Vector3, footprint: Vector2, height: float, wall: int, roof: int) -> void:
	var root: Node3D = _buildings.build_warehouse(_static_root, p, footprint, height, wall, roof)
	_crate(root, Vector3(footprint.x * 0.31, 0.61, 0.30), 0.78)
	_crate(root, Vector3(footprint.x * 0.31, 1.37, 0.30), 0.70)
	_sign(root, Vector3(footprint.x * 0.35, 2.05, footprint.y * 0.5 + 0.11), "港務", 1.5)


func _house(p: Vector3, footprint: Vector2, height: float, wall: int, roof: int, windows := true, long_ridge := false) -> Node3D:
	var root := Node3D.new()
	root.position = p
	_static_root.add_child(root)
	var w := footprint.x
	var d := footprint.y
	_box(root, Vector3(0, 0.07, 0), Vector3(w + 0.35, 0.20, d + 0.35), INK)
	_box(root, Vector3(0, height * 0.5, 0), Vector3(w, height, d), Color.WHITE, wall)
	for x in [-w * 0.49, w * 0.49]:
		for z in [-d * 0.50, d * 0.50]:
			_box(root, Vector3(x, height * 0.5, z), Vector3(0.13, height, 0.14), Color("584434"))
	_box(root, Vector3(0, 0.28, d * 0.505), Vector3(w, 0.10, 0.08), Color("b39361"))
	if windows:
		for x in [-w * 0.28, w * 0.28]:
			_box(root, Vector3(x, height * 0.61, d * 0.51), Vector3(w * 0.23, height * 0.38, 0.09), INK)
			_box(root, Vector3(x, height * 0.61, d * 0.53), Vector3(w * 0.19, height * 0.29, 0.09), Color("b18b52"), 0)
			_box(root, Vector3(x, height * 0.61, d * 0.55), Vector3(0.07, height * 0.29, 0.10), INK)
		_box(root, Vector3(0, height * 0.33, d * 0.52), Vector3(0.9, height * 0.66, 0.09), INK)
		_box(root, Vector3(0, height * 0.33, d * 0.55), Vector3(0.73, height * 0.62, 0.09), Color.WHITE, 8)
	if long_ridge:
		var roof_root := Node3D.new()
		root.add_child(roof_root)
		roof_root.rotation.y = PI * 0.5
		_roof(roof_root, d + 1.15, w + 1.10, height, 1.65, roof)
	else:
		_roof(root, w + 0.70, d + 0.85, height, minf(w * 0.28, 2.1), roof)
	return root


func _roof(root: Node3D, w: float, d: float, height: float, rise: float, tile: int) -> void:
	for side in [-1, 1]:
		var points := [Vector3(side * w * 0.5, height, -d * 0.5), Vector3(side * w * 0.5, height, d * 0.5), Vector3(0, height + rise, d * 0.5), Vector3(0, height + rise, -d * 0.5)]
		if side == 1:
			points.reverse()
		_quad(root, points, Color.WHITE, tile)
		for z in [-d * 0.5, d * 0.5]:
			_beam(root, Vector3(side * w * 0.5, height, z), Vector3(0, height + rise, z), 0.16, INK)
			_beam(root, Vector3(side * w * 0.5, height + 0.03, z), Vector3(0, height + rise + 0.04, z), 0.075, Color("c29b6c"))
		_beam(root, Vector3(side * w * 0.5, height, -d * 0.5), Vector3(side * w * 0.5, height, d * 0.5), 0.16, INK)
		for j in range(1, int(d / 0.7)):
			var z := -d * 0.5 + j * 0.7
			_beam(root, Vector3(side * w * 0.5, height + 0.035, z), Vector3(0, height + rise + 0.035, z), 0.04, Color("554537"))
	_beam(root, Vector3(0, height + rise + 0.04, -d * 0.52), Vector3(0, height + rise + 0.04, d * 0.52), 0.18, Color("725239"))
	for z in [-d * 0.46, d * 0.46]:
		_triangle(root, [Vector3(-w * 0.43, height, z), Vector3(w * 0.43, height, z), Vector3(0, height + rise - 0.10, z)], Color.WHITE, 4)


func _dock(p: Vector3, dimensions: Vector2) -> void:
	_box(_static_root, p - Vector3.UP * 0.12, Vector3(dimensions.x, 0.26, dimensions.y), INK)
	_box(_static_root, p + Vector3.UP * 0.055, Vector3(dimensions.x - 0.1, 0.12, dimensions.y - 0.1), Color.WHITE, 0)
	for x in [-dimensions.x * 0.43, dimensions.x * 0.43]:
		for z in [-dimensions.y * 0.43, dimensions.y * 0.43]:
			_cylinder(_static_root, p + Vector3(x, -0.10, z), 0.16, 1.50, Color("725439"))
			_cylinder(_static_root, p + Vector3(x, 0.65, z), 0.19, 0.08, Color("cda873"))


func _palm(p: Vector3) -> void:
	var height := _rng.randf_range(3.6, 5.0)
	for n in 10:
		var f := n / 10.0
		var segment := _cylinder(_static_root, p + Vector3(f * f * 0.58, height * f, 0), 0.19 - f * 0.075, height / 10.0 + 0.04, [Color("8b7041"), Color("b39557")][n % 2])
		segment.rotation.z = -0.12
	var top := p + Vector3(0.58, height, 0)
	for n in 8:
		var angle := n * TAU / 8.0 + 0.2
		var dir := Vector3(cos(angle), 0, sin(angle))
		var cross_dir := Vector3(-dir.z, 0, dir.x)
		for part in 4:
			var a := top + dir * part * 0.56 + Vector3.UP * sin(part * 0.95) * 0.50
			var b := top + dir * (part + 1) * 0.56 + Vector3.UP * (sin((part + 1) * 0.95) * 0.50 - part * 0.07)
			var width := 0.33 * (1.0 - part / 5.0)
			_quad(_static_root, [a - cross_dir * width, a + cross_dir * width, b + cross_dir * width * 0.45, b - cross_dir * width * 0.45], Color.WHITE, 12)
			_beam(_static_root, a, b, 0.035, Color("b7b44f"))


func _bush(p: Vector3, radius: float) -> void:
	for j in 3:
		var sphere := SphereMesh.new()
		sphere.radius = radius * (0.75 if j > 0 else 1.0)
		sphere.height = radius * 1.35
		sphere.radial_segments = 7
		sphere.rings = 3
		var mesh := MeshInstance3D.new()
		mesh.mesh = sphere
		mesh.position = p + Vector3((j - 1) * radius * 0.55, radius * 0.50, j % 2 * 0.28)
		mesh.material_override = _material([Color("688b42"), Color("88a64c"), Color("a5bc5c")][j])
		_static_root.add_child(mesh)


func _crate(parent: Node3D, p: Vector3, edge: float, tint := Color.WHITE) -> void:
	_box(parent, p, Vector3.ONE * edge, tint, 9)
	for side in [-1, 1]:
		_box(parent, p + Vector3(side * edge * 0.39, 0, edge * 0.505), Vector3(edge * 0.08, edge, 0.035), Color("634933"))


func _barrel(parent: Node3D, p: Vector3) -> void:
	_cylinder(parent, p, 0.36, 0.82, Color("8c7050"))
	for y in [-0.26, 0.26]:
		_cylinder(parent, p + Vector3.UP * y, 0.37, 0.065, INK)


func _sign(parent: Node3D, p: Vector3, text: String, width: float) -> void:
	_box(parent, p, Vector3(width, 0.85, 0.18), INK)
	_box(parent, p + Vector3(0, 0, 0.11), Vector3(width - 0.15, 0.71, 0.07), Color("c19b69"))
	_box(parent, p + Vector3(0, 0, 0.15), Vector3(width - 0.28, 0.57, 0.04), Color("4e352d"))
	var label := Label3D.new()
	label.text = text
	label.font = Pixel.FONT
	label.font_size = 48
	label.pixel_size = minf(0.011, (width - 0.5) / maxf(text.length() * 29.0, 1.0))
	label.modulate = Color("f1d69c")
	label.outline_size = 0
	label.position = p + Vector3(0, 0, 0.19)
	parent.add_child(label)


func _flat_text(parent: Node3D, text: String, p: Vector3, pixel_size: float, color: Color) -> void:
	var label := Label3D.new()
	label.text = text
	label.font = Pixel.FONT
	label.font_size = 32
	label.pixel_size = pixel_size
	label.modulate = color
	label.outline_size = 0
	label.rotation_degrees.x = -90
	label.position = p
	parent.add_child(label)


func _water_number(value: String, p: Vector3) -> void:
	_flat_text(_static_root, value, p, 0.020, Color("d2ebdf"))


func _material(color: Color, tile := -1) -> Material:
	var key := "%s:%d" % [color.to_html(), tile]
	if not _materials.has(key):
		if tile >= 0:
			var material := ShaderMaterial.new()
			material.shader = ATLAS_SHADER
			material.set_shader_parameter("atlas_texture", ATLAS)
			material.set_shader_parameter("tile_index", tile)
			material.set_shader_parameter("tint", color)
			_materials[key] = material
		else:
			var material := StandardMaterial3D.new()
			material.albedo_color = color
			material.roughness = 1.0
			material.specular_mode = BaseMaterial3D.SPECULAR_DISABLED
			material.cull_mode = BaseMaterial3D.CULL_DISABLED
			_materials[key] = material
	return _materials[key]


func _box(parent: Node3D, p: Vector3, dimensions: Vector3, color: Color, tile := -1) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	if tile < 0:
		var mesh := BoxMesh.new()
		mesh.size = dimensions
		instance.mesh = mesh
	else:
		var s := dimensions * 0.5
		var surface := SurfaceTool.new()
		surface.begin(Mesh.PRIMITIVE_TRIANGLES)
		for face in [
			[Vector3(-s.x,s.y,-s.z),Vector3(-s.x,s.y,s.z),Vector3(s.x,s.y,s.z),Vector3(s.x,s.y,-s.z)],
			[Vector3(-s.x,-s.y,s.z),Vector3(-s.x,-s.y,-s.z),Vector3(s.x,-s.y,-s.z),Vector3(s.x,-s.y,s.z)],
			[Vector3(-s.x,-s.y,s.z),Vector3(s.x,-s.y,s.z),Vector3(s.x,s.y,s.z),Vector3(-s.x,s.y,s.z)],
			[Vector3(s.x,-s.y,-s.z),Vector3(-s.x,-s.y,-s.z),Vector3(-s.x,s.y,-s.z),Vector3(s.x,s.y,-s.z)],
			[Vector3(s.x,-s.y,s.z),Vector3(s.x,-s.y,-s.z),Vector3(s.x,s.y,-s.z),Vector3(s.x,s.y,s.z)],
			[Vector3(-s.x,-s.y,-s.z),Vector3(-s.x,-s.y,s.z),Vector3(-s.x,s.y,s.z),Vector3(-s.x,s.y,-s.z)]]:
			_surface_quad(surface, face)
		surface.generate_normals()
		instance.mesh = surface.commit()
	instance.material_override = _material(color, tile)
	instance.position = p
	parent.add_child(instance)
	return instance


func _cylinder(parent: Node3D, p: Vector3, radius: float, height: float, color: Color) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	var mesh := CylinderMesh.new()
	mesh.top_radius = radius
	mesh.bottom_radius = radius * 1.04
	mesh.height = height
	mesh.radial_segments = 10
	instance.mesh = mesh
	instance.material_override = _material(color)
	instance.position = p
	parent.add_child(instance)
	return instance


func _beam(parent: Node3D, a: Vector3, b: Vector3, width: float, color: Color, tile := -1) -> void:
	var beam := _box(parent, (a + b) * 0.5, Vector3(width, width, a.distance_to(b)), color, tile)
	if a.distance_to(b) > 0.001:
		beam.look_at_from_position((a + b) * 0.5, b, Vector3.FORWARD if absf((b - a).normalized().y) > 0.99 else Vector3.UP)


func _surface_quad(surface: SurfaceTool, points: Array) -> void:
	var u: float = points[0].distance_to(points[1]) / 2.0
	var v: float = points[1].distance_to(points[2]) / 2.0
	var uv := [Vector2.ZERO, Vector2(u, 0), Vector2(u, v), Vector2(0, v)]
	for index in [0, 1, 2, 0, 2, 3]:
		surface.set_uv(uv[index])
		surface.add_vertex(points[index])


func _quad(parent: Node3D, points: Array, color: Color, tile := -1) -> void:
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	_surface_quad(surface, points)
	surface.generate_normals()
	var instance := MeshInstance3D.new()
	instance.mesh = surface.commit()
	instance.material_override = _material(color, tile)
	parent.add_child(instance)


func _triangle(parent: Node3D, points: Array, color: Color, tile: int) -> void:
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	for p: Vector3 in points:
		surface.set_uv(Vector2(p.x, p.y) / 2.0)
		surface.add_vertex(p)
	surface.generate_normals()
	var instance := MeshInstance3D.new()
	instance.mesh = surface.commit()
	instance.material_override = _material(color, tile)
	parent.add_child(instance)


func _prism(parent: Node3D, outline: PackedVector2Array, bottom: float, top: float, color: Color, base_scale: float, tile := -1) -> void:
	for i in outline.size():
		var a := outline[i]
		var b := outline[(i + 1) % outline.size()]
		_quad(parent, [Vector3(a.x * base_scale, bottom, a.y * base_scale), Vector3(b.x * base_scale, bottom, b.y * base_scale), Vector3(b.x, top, b.y), Vector3(a.x, top, a.y)], color, tile)
	var indices := Geometry2D.triangulate_polygon(outline)
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in indices:
		surface.set_uv(outline[i] / 2.0)
		surface.add_vertex(Vector3(outline[i].x, top, outline[i].y))
	surface.generate_normals()
	var cap := MeshInstance3D.new()
	cap.mesh = surface.commit()
	cap.material_override = _material(color, tile)
	parent.add_child(cap)


func _batch_static_geometry() -> void:
	# Bake actual vertices/UVs by material identity; color-only box batching loses atlas mapping.
	var surfaces: Dictionary = {}
	var materials: Dictionary = {}
	for node in _static_root.find_children("*", "MeshInstance3D", true, false):
		var instance := node as MeshInstance3D
		if instance.material_override is ShaderMaterial and instance.material_override.shader == WATER:
			continue
		var material: Material = instance.material_override
		if material == null:
			continue
		var key := material.get_instance_id()
		if not surfaces.has(key):
			var surface := SurfaceTool.new()
			surface.begin(Mesh.PRIMITIVE_TRIANGLES)
			surfaces[key] = surface
			materials[key] = material
		var surface: SurfaceTool = surfaces[key]
		for index in instance.mesh.get_surface_count():
			surface.append_from(instance.mesh, index, instance.global_transform)
		instance.get_parent().remove_child(instance)
		instance.queue_free()
	for key in surfaces:
		var instance := MeshInstance3D.new()
		instance.mesh = surfaces[key].commit()
		instance.material_override = materials[key]
		instance.name = "BakedMaterial%d" % key
		add_child(instance)
