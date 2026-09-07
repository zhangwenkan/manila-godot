extends SceneTree

const STAGE = preload("res://dice3d/dice_stage_3d.tscn")
var _failures := 0


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	for dimensions in [Vector2i(2048, 1152), Vector2i(390, 844)]:
		root.content_scale_size = dimensions
		var stage := STAGE.instantiate() as DiceStage3D
		root.add_child(stage)
		stage.set_value(0, 6)
		stage.set_value(1, 4)
		stage.set_value(2, 5)
		await process_frame
		for attempt in 24:
			seed(429 + attempt)
			var starts: Array[Transform3D] = []
			for die: Dice3D in stage._dice:
				starts.append(die.global_transform)
			stage.throw_all()
			for i in starts.size():
				check(stage._dice[i].global_transform.is_equal_approx(starts[i]), "Throw moved a die without physics")
			for frame in 1200:
				await physics_frame
				if not stage._rolling:
					break
			check(not stage._rolling, "Throw timed out at %s attempt %d" % [dimensions, attempt])
			var poses: Array[Transform3D] = []
			for die: Dice3D in stage._dice:
				var normal := die.global_basis * die.FACE_NORMALS[die._detect_top_face() - 1]
				var tilt := rad_to_deg(normal.angle_to(Vector3.UP))
				var context := "%s attempt=%d die=%s tilt=%.3f position=%s" % [dimensions, attempt, die.name, tilt, die.position]
				if tilt >= 0.8:
					print("RADII=%s angular=%s linear=%s" % [stage._tray.radii, die.angular_velocity, die.linear_velocity])
					var state := PhysicsServer3D.body_get_direct_state(die.get_rid())
					for contact in state.get_contact_count():
						var collider = state.get_contact_collider_object(contact)
						var shape_index := state.get_contact_collider_shape(contact)
						var owner = collider.shape_owner_get_owner(collider.shape_find_owner(shape_index))
						print("SHAPE=%d transform=%s normal=%s" % [shape_index, owner.global_transform, state.get_contact_local_normal(contact)])
					for collider in die.get_colliding_bodies():
						print("CONTACT body=%s transform=%s" % [collider.name, collider.global_transform])
				check(tilt < 0.8, "Tilted: " + context)
				check(absf(die.position.y - die.mesh_size * 0.5) < 0.03, "Not on floor: " + context)
				check(stage._tray.contains_point(die.global_position, 0.1), "Outside tray: " + context)
				check(die.get_value() == die._detect_top_face(), "Wrong value: " + context)
				poses.append(die.global_transform)
			for frame in 90:
				await physics_frame
			for i in poses.size():
				check(stage._dice[i].position.distance_to(poses[i].origin) < 0.003, "Position changed after settling")
				check(stage._dice[i].quaternion.angle_to(poses[i].basis.get_rotation_quaternion()) < 0.005, "Pose changed after settling")
			if _failures > 0:
				break
		print("PHYSICS_CHECK viewport=%s failures=%d" % [dimensions, _failures])
		stage.queue_free()
		await process_frame
	print("DICE_PHYSICS_CHECK failures=%d" % _failures)
	quit(0 if _failures == 0 else 1)


func check(condition: bool, message: String) -> void:
	if not condition:
		_failures += 1
		push_error(message)
