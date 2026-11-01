extends "res://tools/harbor_pixel_demo_check.gd"
## Focused market isolation test; owns its distinct completion marker and 90s bound.

var _market_completed := false


func _process(_delta: float) -> bool:
	if not _done and Time.get_ticks_msec() - _started_ms > 90000:
		_check(false, "Market 90s watchdog expired")
		_finish(124)
	return false


func _run() -> void:
	root.title = "Market 3D isolation check (bounded 90s)"
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	root.content_scale_size = Vector2i.ZERO
	root.size = Vector2i(1200, 900)
	_demo = load(DEMO_SCENE).instantiate()
	root.add_child(_demo)
	_demo.auto_ai = false
	await _frames(5)
	var game = _demo.game
	var overlay = _demo.market_overlay
	_stage = "all phases, contexts and window shapes"
	for dimensions in [Vector2i(1200, 900), Vector2i(1280, 720), Vector2i(720, 1000)]:
		root.size = dimensions
		game.reset(SEED)
		await _frames(5)
		await _probe("auction")
		_win_auction(0)
		await _probe("stock")
		game.skip_stock(0)
		await _probe("cargo")
		_demo._activate("to_starts")
		_demo.setup_starts = [1, 3, 5]
		await _probe("starts")
		_demo._activate("begin")
		await _frames()
		_demo._activate("slot:shipyard_1")
		await _probe("selected_worker")
		for context in ["help", "ledger", "pass"]:
			_demo._activate(context)
			await _probe(context)
			_demo._activate("close")
		for _actor in 3:
			game.pass_turn(game.current_player)
		await _probe("sailing")
		_check_stock_markers()
		overlay.open({"nutmeg": 5, "silk": 10, "ginseng": 20, "jade": 30})
		await _frames(5)
		_check_camera_frame()
		await _capture("market_3d_%dx%d" % [dimensions.x, dimensions.y])
		if _preview:
			await RenderingServer.frame_post_draw
			var image: Image = overlay.stage._viewport.get_texture().get_image()
			var visible_pixels := 0
			for y in range(0, image.get_height(), 4):
				for x in range(0, image.get_width(), 4):
					if image.get_pixel(x, y).a > 0.5:
						visible_pixels += 1
			_check(visible_pixels > 400, "Real model produces substantial opaque rendered geometry")
			image.save_png(ProjectSettings.globalize_path(OUTPUT).path_join("market_model_%dx%d.png" % [dimensions.x, dimensions.y]))
		overlay.close()
		await _frames()
	# AI pauses only new moves; closing restarts its normal delay.
	_stage = "AI pause and resume"
	game.reset(SEED)
	_win_auction(1)
	await _probe("ai_stock")
	_demo.auto_ai = true
	_demo._activate("market")
	var before := _snapshot()
	await create_timer(1.2).timeout
	_check(_snapshot() == before, "AI does not buy, bid or prepare under the price viewer")
	overlay.close()
	await create_timer(1.1).timeout
	_check(_snapshot() != before, "AI resumes after prices close")
	_demo.auto_ai = false
	# Actual dice physics continue, submit once, and retain result display.
	_stage = "live physical roll with price viewer above dice"
	root.size = Vector2i(1200, 900)
	game.reset(SEED)
	_begin_fixture(["ginseng", "silk", "jade"], [2, 3, 4])
	for _actor in 3:
		game.pass_turn(game.current_player)
	await _frames(5)
	_check(_demo.start_roll(), "Start actual physical dice")
	var request: int = _demo._roll_request
	var dice_stage = _demo.dice_overlay.stage
	var prior_sails: int = game.sail_count
	_click_root(overlay.launcher.get_global_rect().get_center())
	await _frames()
	_check(overlay.is_open and _demo._roll_phase == "rolling", "Stock icon is clickable above rolling dice")
	_key(KEY_ESCAPE)
	await _frames()
	_check(not overlay.is_open and _demo._roll_request == request and _demo.dice_overlay.stage == dice_stage, "Escape from prices neither cancels nor rebuilds active dice")
	_key(KEY_M)
	while _demo._roll_phase == "rolling" and Time.get_ticks_msec() - _started_ms < 80000:
		await process_frame
	_check(_demo._roll_phase == "result" and game.sail_count == prior_sails + 1, "Hidden physical dice commit exactly once")
	await create_timer(1.0).timeout
	_check(_demo._roll_phase == "result" and overlay.is_open, "Result presentation waits while prices are open")
	var committed := _snapshot()
	_demo._on_dice_results(game.dice.duplicate(), request)
	_check(_snapshot() == committed, "Duplicate result cannot resubmit while market is open")
	_key(KEY_ESCAPE)
	await _frames()
	_check(_demo._roll_phase == "result" and _demo.dice_overlay.state == "result", "Closing price viewer reveals retained dice result")
	_demo._on_dice_skip(request)
	await _probe("moving", false)
	while _demo.busy:
		await process_frame
	_check(game.sail_count == prior_sails + 1, "Moving under market does not replay model roll")
	# Reach settlement and finished using public model actions and explicit replay dice.
	_stage = "settlement and finished accessibility"
	game.reset(SEED)
	game.max_voyages = 1
	_begin_fixture(["ginseng", "silk", "jade"], [2, 3, 4])
	for _step in 30:
		if game.phase == "dispatch":
			game.pass_turn(game.current_player)
		elif game.phase == "sailing":
			_check(_demo.start_roll([2, 3, 4], game.harbormaster), "Replay fixture starts through normal dice lifecycle")
			_demo.finish_animation()
		elif game.phase == "settlement":
			break
	_check(game.phase == "settlement", "Fixture reaches settlement")
	await _probe("settlement")
	game.next_voyage()
	_check(game.phase == "finished", "Fixture reaches finished")
	await _probe("finished")
	_demo._activate("restart")
	await _probe("restart")
	_demo._activate("close")
	var stage_id: int = overlay.stage.get_instance_id()
	var node_count: int = get_node_count()
	for _cycle in 25:
		overlay.open(game.prices)
		overlay.close()
	await _frames()
	_check(overlay.stage.get_instance_id() == stage_id and get_node_count() == node_count, "Repeated opening reuses model without leaking nodes")
	_market_completed = true
	_finish()


func _probe(label: String, stable := true) -> void:
	await _frames()
	var overlay = _demo.market_overlay
	var before := _snapshot()
	var context: Array = [_demo.modal, _demo.selected, _demo._setup_step, _demo._chosen_cargo, _demo.setup_cargo.duplicate(), _demo.setup_starts.duplicate(), _demo._bid_amount]
	_check(overlay.launcher.visible and not overlay.launcher.disabled, label + ": icon available independently of phase hits")
	_check(not _has_hit("market"), label + ": native icon cannot be erased by modal hit rebuilding")
	_click_root(overlay.launcher.get_global_rect().get_center())
	await _frames()
	_check(overlay.is_open, label + ": real icon click opens prices")
	_check(overlay.screen.get_global_rect() == Rect2(Vector2.ZERO, Vector2(root.size)), label + ": shade includes letterboxing")
	_check(overlay.stage._viewport.own_world_3d, label + ": isolated 3D world")
	for id in ["bid", "bid_pass", "stock_skip", "buy:jade", "load:0", "begin", "confirm", "pass_confirm", "sail", "next", "restart_confirm", "close"]:
		_demo._activate(id)
	_key(KEY_TAB)
	_key(KEY_UP)
	_click_root(Vector2(4, root.size.y - 4))
	_click_board(Vector2(640, 700))
	await _frames()
	if stable:
		_check(_snapshot() == before, label + ": no mouse, keyboard or stale-action mutation")
	_check([_demo.modal, _demo.selected, _demo._setup_step, _demo._chosen_cargo, _demo.setup_cargo, _demo.setup_starts, _demo._bid_amount] == context, label + ": context and preparation draft preserved")
	_click_root(overlay.close_button.get_global_rect().get_center())
	await _frames()
	_check(not overlay.is_open and not overlay.screen.visible and overlay.stage._viewport.render_target_update_mode == SubViewport.UPDATE_DISABLED, label + ": close stops only market rendering")
	if stable:
		_check(_snapshot() == before, label + ": close is read-only")


func _check_camera_frame() -> void:
	var stage = _demo.market_overlay.stage
	var bounds := Rect2(Vector2.ZERO, Vector2(stage._viewport.size)).grow(-2)
	for corner in stage._corners:
		_check(bounds.has_point(stage._camera.unproject_position(corner)), "Model corner fits pixel viewport at current aspect ratio")
	_check(stage.texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST and stage.stretch_shrink == 1, "Fine pixel rendering uses native resolution without 2x enlargement")
	_check(stage._viewport.size == Vector2i(stage.size), "Model render target uses the full available panel resolution")
	_check(_demo.market_overlay.screen.find_children("*", "Label", true, false).is_empty(), "No redundant external title or cargo-price labels")
	_check(_demo.market_overlay.screen.find_children("*", "GridContainer", true, false).is_empty(), "Removed footer reserves no empty layout band")
	_check(stage.board.find_child("PrintedBoard", true, false) == null, "No full-board picture or old flat-grid surface remains")
	_check(stage.board.find_children("*Capsule*", "MeshInstance3D", true, false).is_empty(), "No generic cargo capsules remain")
	_check(stage.board.scene_file_path.is_empty(), "Market geometry is generated in Godot, not imported from Blender")
	var title: MeshInstance3D = stage.board.find_child("MarketTitle", true, false)
	_check(is_instance_valid(title) and title.mesh is TextMesh and title.mesh.text == "股票市值", "Title is integrated into the standing wooden sign")
	var frame: MeshInstance3D = stage.board.find_child("SculptedTrayRim", true, false)
	_check(is_instance_valid(frame) and frame.get_aabb().size.y > 0.9, "Tray has an actual deep, profiled wooden rim")
	_check(absf(stage._camera.basis.z.y - 0.5) < 0.02, "Camera uses the dice tray's 30-degree tabletop angle")
	var identities := {"nutmeg": "NutmegShell", "silk": "SilkRoll", "ginseng": "GinsengRoot", "jade": "JadeBi"}
	for cargo in identities:
		var marker: Node3D = stage.markers[cargo]
		var body: MeshInstance3D = marker.find_child(identities[cargo], true, false)
		_check(is_instance_valid(body) and not body.mesh is PlaneMesh, "Cargo identity is a sculpted volume: " + cargo)
		if is_instance_valid(body):
			var material: ShaderMaterial = body.get_active_material(0)
			_check(material.shader.resource_path == "res://demo/harbor_pixel/market_surface.gdshader" and material.next_pass != null, "Cargo has independent top-side palette shading and expanded-backface contour")
		var track: Node3D = stage.board.find_child("Track_" + cargo, true, false)
		for value in [0, 5, 10, 20, 30]:
			var price: MeshInstance3D = track.find_child("Price_" + str(value), true, false)
			_check(is_instance_valid(price) and price.mesh is TextMesh and price.mesh.text == str(value), "All five price labels remain explicit and correct")
	_check(stage.board.find_child("Cube", true, false) == null, "Tabletop contains no leftover Blender mesh")


func _finish(forced_code := -1) -> void:
	if _done:
		return
	_done = true
	if forced_code < 0:
		_check(_market_completed, "Market suite reached all checkpoints")
	var code := forced_code if forced_code >= 0 else (0 if _failures.is_empty() else 1)
	print("HARBOR_MARKET_CHECK completed assertions=%d failures=%d preview=%s elapsed_ms=%d exit=%d" % [_assertions, _failures.size(), _preview, Time.get_ticks_msec() - _started_ms, code])
	print("HARBOR_MARKET_CHECK_%s" % ("PASS" if code == 0 else "FAIL"))
	if is_instance_valid(_demo):
		_demo.queue_free()
	quit(code)
