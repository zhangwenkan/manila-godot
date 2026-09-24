extends SceneTree
## 有界检查：godot --path . --headless --script res://tools/situation_panel_check.gd
## 实例化真实场景，验证横向态势长条的存在、布局、数据同步与展开，然后立即退出。

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
	# 横条可点击（展开/收起需要接收输入）。
	_check(panel.mouse_filter == Control.MOUSE_FILTER_STOP, "横条应可点击展开")
	# 折叠时高度为一条 BAR_H。
	_check(is_equal_approx(panel.size.y, panel.BAR_H), "折叠高度应为 BAR_H：%s vs %s" % [panel.size.y, panel.BAR_H])

	# 模拟一次派遣，验证该玩家的派遣项列表随 owners 刷新。
	var actor = _game.turn_bar.players[_game.turn_bar.current_player_index]
	_game.placement_panel.state.owners["harbor_2"] = actor
	_game.placement_panel.state.changed.emit()
	await _frames(2)
	var lines: Array = panel._placement_lines(actor)
	_check(lines.size() == 1 and String(lines[0]).begins_with("港口"), "派遣后派遣项未反映 harbor 占位：%s" % [lines])

	# 展开：高度按最多派遣项数增长；再点收起还原。
	panel._gui_input(_left_click())
	await _frames(2)
	_check(panel._expanded, "点击未展开")
	var expected_h: float = panel.BAR_H + panel._max_lines * panel.DETAIL_LINE_H + 6.0
	_check(is_equal_approx(panel.size.y, expected_h), "展开高度与派遣项数不符：%s vs %s" % [panel.size.y, expected_h])
	panel._gui_input(_left_click())
	await _frames(2)
	_check(not panel._expanded and is_equal_approx(panel.size.y, panel.BAR_H), "再次点击未收起")

	# 船名随港务长选货更新：换 nutmeg/jade/ginseng 后，船位派遣项显示新货名。
	_game.set_voyage(["nutmeg", "jade", "ginseng"], [], [3, 3, 3])
	_game.placement_panel.state.owners.clear()
	_game.placement_panel.state.owners["ship_0_0"] = actor   # 船0 现为 nutmeg
	_game.placement_panel.state.changed.emit()
	await _frames(2)
	lines = panel._placement_lines(actor)
	_check(lines.size() == 1 and String(lines[0]).begins_with("肉豆蔻"), "选货后船名未更新：%s" % [lines])

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


func _left_click() -> InputEventMouseButton:
	var event := InputEventMouseButton.new()
	event.button_index = MOUSE_BUTTON_LEFT
	event.pressed = true
	event.position = Vector2(10, 10)
	return event


func _check(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)


func _frames(count: int) -> void:
	for i in count:
		await process_frame
