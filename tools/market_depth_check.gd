extends SceneTree
## Bounded render evidence: actual shadows, silhouettes and price-label visibility.

const STAGE = preload("res://demo/harbor_pixel/market_stage_3d.gd")
var _started := 0
var _failures := 0
var _stage


func _initialize() -> void:
	_started = Time.get_ticks_msec()
	Engine.max_fps = 60
	call_deferred("_run")


func _process(_delta: float) -> bool:
	if Time.get_ticks_msec() - _started > 45000:
		push_error("MARKET_DEPTH_CHECK timeout")
		quit(124)
	return false


func _run() -> void:
	if DisplayServer.get_name() == "headless":
		push_error("This check requires a real renderer")
		quit(2)
		return
	root.title = "New market tabletop — bounded visual check"
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	root.content_scale_size = Vector2i.ZERO
	root.size = Vector2i(1200, 900)
	_stage = STAGE.new()
	root.add_child(_stage)
	_stage.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_stage.set_active(true)
	_stage.sync_prices({"nutmeg": 5, "silk": 10, "ginseng": 20, "jade": 30})
	await _frames(12)
	var light: DirectionalLight3D = _stage._viewport.find_child("MarketKeyLight", true, false)
	var shaded := await _image()
	light.shadow_enabled = false
	await _frames(5)
	var unshaded := await _image()
	light.shadow_enabled = true
	var shadow_pixels := 0
	for y in shaded.get_height():
		for x in shaded.get_width():
			var a := shaded.get_pixel(x, y)
			var b := unshaded.get_pixel(x, y)
			if a.a > 0.99 and b.a > 0.99 and b.get_luminance() - a.get_luminance() > 0.025:
				shadow_pixels += 1
	_check(shadow_pixels > 500, "Visible cast-shadow pixels: %d" % shadow_pixels)
	var out := ProjectSettings.globalize_path("res://.godot/harbor_pixel_demo_check")
	shaded.save_png(out.path_join("market_tabletop_depth.png"))
	# Remove each real cargo piece independently and measure its actual silhouette.
	for cargo in _stage.GOODS:
		await _frames(3)
		var shown := await _image()
		var marker: Node3D = _stage.markers[cargo]
		marker.hide()
		await _frames(3)
		var hidden := await _image()
		marker.show()
		var changed := 0
		var left := shown.get_width()
		var right := 0
		var top := shown.get_height()
		var bottom := 0
		for y in shown.get_height():
			for x in shown.get_width():
				var a := shown.get_pixel(x, y)
				var b := hidden.get_pixel(x, y)
				if absf(a.r - b.r) + absf(a.g - b.g) + absf(a.b - b.b) > 0.1:
					changed += 1
					left = mini(left, x)
					right = maxi(right, x)
					top = mini(top, y)
					bottom = maxi(bottom, y)
		_check(changed > 500 and bottom - top > 40, "%s actual silhouette: pixels=%d width=%d height=%d" % [cargo, changed, right-left, bottom-top])
	# Count actual rendered ink, not merely the presence of a TextMesh node.
	for value in [0, 5, 10, 20, 30]:
		_stage.sync_prices({"nutmeg": value, "silk": value, "ginseng": value, "jade": value})
		await _frames(2)
		var shown := await _image()
		var labels: Array[MeshInstance3D] = []
		for cargo in _stage.GOODS:
			var track: Node3D = _stage.board.find_child("Track_" + cargo, true, false)
			var label: MeshInstance3D = track.find_child("Price_" + str(value), true, false)
			labels.append(label)
			label.hide()
		await _frames(2)
		var hidden := await _image()
		for label in labels:
			label.show()
			var center: Vector2 = _stage._camera.unproject_position(label.global_position)
			var ink := 0
			for y in range(maxi(0, int(center.y) - 25), mini(shown.get_height(), int(center.y) + 25)):
				for x in range(maxi(0, int(center.x) - 35), mini(shown.get_width(), int(center.x) + 35)):
					if shown.get_pixel(x,y).get_luminance() - hidden.get_pixel(x,y).get_luminance() > 0.1:
						ink += 1
			_check(ink > 35, "%s / %d visible price-ink pixels=%d" % [label.get_parent().name, value, ink])
	_stage.sync_prices({"nutmeg": 5, "silk": 10, "ginseng": 20, "jade": 30})
	await _frames(3)
	var final_image := await _image()
	final_image.save_png(out.path_join("market_tabletop_depth.png"))
	print("MARKET_DEPTH_CHECK_%s failures=%d elapsed_ms=%d" % ["PASS" if _failures == 0 else "FAIL", _failures, Time.get_ticks_msec() - _started])
	quit(0 if _failures == 0 else 1)


func _frames(count: int) -> void:
	for _i in count:
		await process_frame


func _image() -> Image:
	await RenderingServer.frame_post_draw
	return _stage._viewport.get_texture().get_image()


func _check(condition: bool, message: String) -> void:
	print(("OK " if condition else "FAIL ") + message)
	if not condition:
		_failures += 1
