extends SceneTree
## 有界检查：godot --path . --headless --script res://tools/situation_panel_check.gd
## 实例化真实场景，验证态势面板的存在、布局、数据同步，然后立即退出。

var _failures: Array[String] = []
var _game


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	root.content_scale_size = Vector2i(2048, 1152)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.size = Vector2i(2048, 1152)
	_game = load("res://scene/scene_bg.tscn").instantiate()
	root.add_child(_game)
	await _frames(6)

	var panel = _game.situation_panel
	_check(panel != null, "态势面板未接入场景")
	_check(panel.visible, "开局时态势面板应可见")
	# 左上角对齐（与底栏同 margin=24）。
	_check(is_equal_approx(panel.position.x, 24.0) and is_equal_approx(panel.position.y, 24.0), "态势面板未贴左上角：%s" % panel.position)
	# 不遮挡其他 HUD。
	var right_edge: float = panel.get_global_rect().end.x
	_check(right_edge < _game.personal_bar.size.x, "态势面板过宽")
	# 数据同步：玩家数与 turn_bar 一致，且不为空。
	_check(panel._players.size() == _game.turn_bar.players.size() and not panel._players.is_empty(), "玩家列表未同步")
	_check(panel._current_id == _game.turn_bar.players[_game.turn_bar.current_player_index].character_name_en, "当前玩家高亮未同步")
	# 面板高度随玩家数增长。
	var expected_h: float = panel.HEADER_H + 10.0 + panel._players.size() * panel.ROW_H + (panel._players.size() - 1) * panel.ROW_GAP + 6.0
	_check(is_equal_approx(panel.size.y, expected_h), "面板高度与玩家数不符：%s vs %s" % [panel.size.y, expected_h])
	# 只显示公共信息：面板持有的资源里不解读现金/股票（仅读 remaining/capacity）。
	_check(panel.mouse_filter == Control.MOUSE_FILTER_IGNORE, "态势面板拦截了输入")

	# 模拟一次派遣，验证分布条随 owners 变化刷新。
	var actor = _game.turn_bar.players[_game.turn_bar.current_player_index]
	_game.placement_panel.state.owners["harbor_2"] = actor
	_game.placement_panel.state.changed.emit()
	await _frames(2)
	var counts: Dictionary = panel._counts_for(actor)
	_check(counts["harbor"] == 1, "派遣后分布条未反映 harbor 占位")

	# 覆盖开关面板时的可见性。
	_game.open_character_roster()
	await _frames(3)
	_check(not panel.visible, "角色列表打开时态势面板应隐藏")

	print("SITUATION_PANEL_CHECK failures=%d" % _failures.size())
	for f in _failures:
		print("  - " + f)
	_game.queue_free()
	await _frames(2)
	quit(0 if _failures.is_empty() else 1)


func _check(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)


func _frames(count: int) -> void:
	for i in count:
		await process_frame
