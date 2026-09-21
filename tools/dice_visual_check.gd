extends SceneTree

const OUTPUT_DIR := "res://.godot/dice_visual_check"
const STAGE_SCENE = preload("res://dice3d/dice_stage_3d.tscn")
const DIE_SCRIPT = preload("res://dice3d/dice3d.gd")

var _failures: Array[String] = []
var _completed_rolls: int = 0
var _settled_indices: Array[int] = []


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	if "--native-viewport" in OS.get_cmdline_user_args():
		root.content_scale_size = root.size
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT_DIR))
	var stage := STAGE_SCENE.instantiate() as DiceStage3D
	root.add_child(stage)
	print("VIEWPORT_CHECK window=%s stage=%s" % [root.size, stage.size])
	_check(stage.position.is_equal_approx(Vector2.ZERO) and stage.size.is_equal_approx(root.get_visible_rect().size), "Stage does not fill the viewport")
	for value in range(1, 7):
		stage.set_value(0, value)
		_check(stage._dice[0]._detect_top_face() == value, "Top face does not match result %d" % value)
	stage.set_value(0, 6)
	stage.set_value(1, 4)
	stage.set_value(2, 5)
	await _save_viewport(stage._viewport, "stage.png", 2)
	await _check_tray_shadows(stage)

	var detail := SubViewport.new()
	detail.size = Vector2i(160, 160)
	detail.transparent_bg = true
	detail.own_world_3d = true
	detail.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(detail)
	var die := DIE_SCRIPT.new() as Dice3D
	detail.add_child(die)
	die.set_value(6)
	var camera := Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 1.48
	detail.add_child(camera)
	camera.position = die.position + Vector3(0.0, 3.0, 5.196)
	camera.look_at(die.position)
	camera.current = true
	for value in range(1, 7):
		die.set_value(value)
		await _save_viewport(detail, "face_%d.png" % value, 3)
	var preview := Image.create(480, 480, false, Image.FORMAT_RGBA8)
	preview.fill(Color("#f1f5ef"))
	var closeup := Image.load_from_file(OUTPUT_DIR.path_join("face_6.png"))
	preview.blend_rect(closeup, Rect2i(0, 0, 480, 480), Vector2i.ZERO)
	preview.save_png(OUTPUT_DIR.path_join("reference_view.png"))
	detail.queue_free()

	if "--roll" in OS.get_cmdline_user_args():
		seed(429)
		var final_poses: Dictionary = {}
		for rolling_die: Dice3D in stage._dice:
			rolling_die.settled.connect(func(): final_poses[rolling_die.get_instance_id()] = rolling_die.global_transform)
		stage.all_settled.connect(func(_values: Array): _completed_rolls += 1)
		stage.dice_settled.connect(func(index: int, _value: int): _settled_indices.append(index))
		var launch_poses: Array[Transform3D] = []
		for launching_die: Dice3D in stage._dice:
			launch_poses.append(launching_die.global_transform)
		stage.throw_all()
		stage.throw_all()
		for i in stage._dice.size():
			_check(stage._dice[i].global_transform.is_equal_approx(launch_poses[i]), "Throw teleported a die before applying the impulse")
		var previous_rotation := stage._dice[0].quaternion
		var previous_face := stage._dice[0]._detect_top_face()
		var changed_faces: Dictionary = {}
		var rotated := false
		var stayed_in_frame := true
		for frame in range(1200):
			await physics_frame
			for active_die: Dice3D in stage._dice:
				var frame_rect := Rect2(Vector2.ZERO, Vector2(stage._viewport.size))
				# The padded click target can cross an edge while the rounded mesh remains visible.
				if not frame_rect.encloses(stage._die_screen_rect(active_die)):
					var visible_rect := Rect2(stage._camera.unproject_position(active_die.global_position), Vector2.ZERO)
					var body := active_die.get_node("PixelRoundedMesh/RoundedBody") as MeshInstance3D
					for surface in body.mesh.get_surface_count():
						var arrays := body.mesh.surface_get_arrays(surface)
						var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
						var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
						for vertex in vertices.size():
							var point := active_die.global_transform * (vertices[vertex] + normals[vertex] * active_die.mesh_size * 0.014)
							visible_rect = visible_rect.expand(stage._camera.unproject_position(point))
					stayed_in_frame = stayed_in_frame and frame_rect.encloses(visible_rect)
			var current_rotation := stage._dice[0].quaternion
			rotated = rotated or current_rotation.angle_to(previous_rotation) > 0.02
			previous_rotation = current_rotation
			var face := stage._dice[0]._detect_top_face()
			if face != previous_face:
				changed_faces[face] = true
				previous_face = face
			if frame in [12, 30, 60, 100]:
				await _save_viewport(stage._viewport, "roll_%03d.png" % frame, 2)
			if not stage._rolling:
				break
		_check(rotated and changed_faces.size() >= 3, "Roll did not turn through at least three faces")
		_check(stayed_in_frame, "A die left the camera frame while rolling")
		_check(not stage._rolling, "Roll failed to settle within 20 seconds")
		_check(_completed_rolls == 1 and _settled_indices.size() == 3, "Roll signals must be emitted exactly once")
		for rolled_die: Dice3D in stage._dice:
			_check(rolled_die._detect_top_face() == rolled_die.get_value(), "Settled top face disagrees with result")
			_check_resting_pose(stage, rolled_die)
			_check(not rolled_die.freeze, "Settlement froze the physics body")
		stage.enable_debug_inspect()
		for rolled_die: Dice3D in stage._dice:
			if final_poses.has(rolled_die.get_instance_id()):
				_check(rolled_die.global_transform.is_equal_approx(final_poses[rolled_die.get_instance_id()]), "Debug inspection moved a landed die")
		for frame in range(90):
			await physics_frame
		for rolled_die: Dice3D in stage._dice:
			if final_poses.has(rolled_die.get_instance_id()):
				var resting_pose: Transform3D = final_poses[rolled_die.get_instance_id()]
				_check(rolled_die.position.distance_to(resting_pose.origin) < 0.003, "Position changed after settlement")
				_check(rolled_die.quaternion.angle_to(resting_pose.basis.get_rotation_quaternion()) < 0.005, "Face rotated after settlement")
				_check(rolled_die._detect_top_face() == rolled_die.get_value(), "Reported face became stale after settlement")
		await _save_viewport(stage._viewport, "settled.png", 2)
		var click := InputEventMouseButton.new()
		click.pressed = true
		click.button_index = MOUSE_BUTTON_LEFT
		var die_center := stage._camera.unproject_position(stage._dice[0].global_position)
		click.position = stage.get_global_transform_with_canvas() * (die_center * stage.size / Vector2(stage._viewport.size))
		var clicked_value := stage.get_value(0) % 6 + 1
		_check(stage.handle_debug_input(click) and stage.get_value(0) == clicked_value, "Projected debug click did not cycle the landed die")
		var landed_poses: Array[Transform3D] = []
		for landed_die: Dice3D in stage._dice:
			landed_poses.append(landed_die.global_transform)
		stage.throw_all()
		for i in stage._dice.size():
			_check(stage._dice[i].global_transform.is_equal_approx(landed_poses[i]), "Second throw teleported a landed die")
		for frame in range(1200):
			await physics_frame
			if not stage._rolling:
				break
		_check(not stage._rolling and _completed_rolls == 2 and _settled_indices.size() == 6, "Second throw failed to settle and report once")
		for rolled_die: Dice3D in stage._dice:
			_check(rolled_die._detect_top_face() == rolled_die.get_value(), "Second throw reported the wrong top face")
			_check_resting_pose(stage, rolled_die)
		print("ROLL_CHECK faces_seen=%d completed=%d signals=%d" % [changed_faces.size(), _completed_rolls, _settled_indices.size()])
	stage.queue_free()
	await process_frame
	if "--game" in OS.get_cmdline_user_args():
		root.content_scale_size = Vector2i(2048, 1152)
		root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
		var game = load("res://scene/scene_bg.tscn").instantiate()
		root.add_child(game)
		_check(game.get_node_or_null("CanvasLayer/DiceOverlay") != null, "Dice overlay is missing")
		game.inspect_dice()
		_check(game.get_node("CanvasLayer/DiceOverlay").visible and game.dice_stage.visible, "Dice mode did not show the full-screen overlay")
		game.dice_stage.set_value(0, 6)
		game.dice_stage.set_value(1, 4)
		game.dice_stage.set_value(2, 5)
		await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(OUTPUT_DIR.path_join("game.png"))
		game.roll_dice()
		game.inspect_dice()
		_check(game._dice_rolling, "Debug button interrupted an active throw")
		game._on_close_dice_pressed()
		_check(game.dice_overlay.visible and game.dice_close_button.disabled, "Active throw can be dismissed")
		for frame in range(1200):
			await physics_frame
			if frame in [12, 30, 60, 100]:
				await RenderingServer.frame_post_draw
				root.get_texture().get_image().save_png(OUTPUT_DIR.path_join("game_roll_%03d.png" % frame))
			if not game._dice_rolling:
				break
		_check(not game._dice_rolling and game._dice_results == game.dice_stage.get_values(), "Game roll did not finish with matching results")
		for game_die: Dice3D in game.dice_stage._dice:
			_check_resting_pose(game.dice_stage, game_die)
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(OUTPUT_DIR.path_join("game_settled.png"))
		var game_poses: Array[Transform3D] = []
		for game_die: Dice3D in game.dice_stage._dice:
			game_poses.append(game_die.global_transform)
		game._on_close_dice_pressed()
		_check(not game.dice_overlay.visible and not game.dice_stage.visible and game.personal_bar.visible, "Dice mode did not close")
		game.inspect_dice()
		for i in game_poses.size():
			_check(game.dice_stage._dice[i].global_transform.is_equal_approx(game_poses[i]), "Reopening dice mode moved a die")
		game.queue_free()
		await process_frame
	print("DICE_VISUAL_CHECK failures=%d output=%s" % [_failures.size(), ProjectSettings.globalize_path(OUTPUT_DIR)])
	quit(0 if _failures.is_empty() else 1)


func _save_viewport(viewport: SubViewport, filename: String, upscale: int) -> void:
	await process_frame
	await RenderingServer.frame_post_draw
	var image := viewport.get_texture().get_image()
	_check(not image.is_empty(), "Empty render for " + filename)
	if not image.is_empty():
		if filename == "stage.png":
			var transparent_pixels := 0
			for y in range(image.get_height()):
				for x in range(image.get_width()):
					if image.get_pixel(x, y).a < 0.01:
						transparent_pixels += 1
			var transparent_ratio := float(transparent_pixels) / float(image.get_width() * image.get_height())
			_check(transparent_ratio > 0.45 and transparent_ratio < 0.90, "Tray is missing or its surroundings are opaque")
		if filename.begins_with("face_"):
			var green_pixels := 0
			var blue_pixels := 0
			var white_pixels := 0
			for y in range(image.get_height()):
				for x in range(image.get_width()):
					var color := image.get_pixel(x, y)
					if color.a < 0.9:
						continue
					if color.g > color.r and color.g > color.b:
						green_pixels += 1
					if color.b > color.g * 1.2 and color.b > color.r * 1.2:
						blue_pixels += 1
					if minf(color.r, minf(color.g, color.b)) > 0.90:
						white_pixels += 1
			_check(green_pixels > 1000 and blue_pixels > 50 and white_pixels == 0, "Missing green body/blue pips or white surface in " + filename)
		image.resize(image.get_width() * upscale, image.get_height() * upscale, Image.INTERPOLATE_NEAREST)
		_check(image.save_png(OUTPUT_DIR.path_join(filename)) == OK, "Cannot save " + filename)


func _check_resting_pose(stage: DiceStage3D, die: Dice3D) -> void:
	var top_normal := die.global_basis * die.FACE_NORMALS[die._detect_top_face() - 1]
	var tilt := rad_to_deg(top_normal.angle_to(Vector3.UP))
	_check(tilt < 0.8, "Die is resting at a %.3f degree tilt" % tilt)
	_check(stage._tray.contains_point(die.global_position, 0.1), "Die landed outside the tray")
	_check(absf(die.position.y - die.mesh_size * 0.5) < 0.03, "Die is not resting on the tray floor")


func _check_tray_shadows(stage: DiceStage3D) -> void:
	for frame in 8:
		await process_frame
		await RenderingServer.frame_post_draw
	var shadowed := stage._viewport.get_texture().get_image()
	shadowed.save_png(OUTPUT_DIR.path_join("tray_shadowed.png"))
	var light := stage._world.get_node("KeyLight") as DirectionalLight3D
	light.shadow_enabled = false
	for frame in 3:
		await process_frame
		await RenderingServer.frame_post_draw
	var unshadowed := stage._viewport.get_texture().get_image()
	unshadowed.save_png(OUTPUT_DIR.path_join("tray_unshadowed.png"))
	light.shadow_enabled = true
	var shadow_pixels := 0
	var changed_pixels := 0
	for y in shadowed.get_height():
		for x in shadowed.get_width():
			var a := shadowed.get_pixel(x, y)
			var b := unshadowed.get_pixel(x, y)
			if a != b:
				changed_pixels += 1
			if a.a > 0.9 and b.g - a.g > 0.025:
				shadow_pixels += 1
	print("SHADOW_PIXELS=%d" % shadow_pixels)
	print("CHANGED_PIXELS=%d" % changed_pixels)
	_check(shadow_pixels > 30, "Dice and rim cast no shadows on the tray")


func _check(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)
		push_error(message)
