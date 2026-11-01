extends SceneTree

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	var path := "res://demo/harbor_hd2d/art/insurance/source/insurance_blockout.glb"
	assert(document.append_from_file(path, state) == OK)
	var model := document.generate_scene(state)
	root.add_child(model)
	var bounds := AABB()
	var started := false
	var materials: Dictionary = {}
	for instance: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		for p in instance.mesh.get_faces():
			var point := instance.global_transform * p
			bounds = bounds.expand(point) if started else AABB(point, Vector3.ZERO)
			started = true
		for surface in instance.mesh.get_surface_count():
			var material := instance.get_active_material(surface)
			assert(material != null)
			materials[material.resource_name] = true
	print("INS_BLOCKOUT_LOCAL_BOUNDS: ", bounds)
	print("INS_BLOCKOUT_MATERIALS: ", materials.keys())
	assert(bounds.position.x > -10.8 and bounds.end.x < 6.8)
	assert(bounds.position.y > -0.5 and bounds.end.y > 7.8 and bounds.end.y < 8.4)
	assert(bounds.position.z > -3.8 and bounds.end.z < 4.7)
	print("INS_BLOCKOUT_AXIS_PASS")
	quit()
