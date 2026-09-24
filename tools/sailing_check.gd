extends SceneTree
## 有界检查：godot --path . --headless --script res://tools/sailing_check.gd
## 预览（看真投骰推船）：godot --path . --script res://tools/sailing_check.gd -- --preview
## 实例化真实场景，验证「骰子结果驱动船沿航线移动 + 越过 13 到港」，然后立即退出。

var _failures: Array[String] = []
var _game


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	root.content_scale_size = Vector2i(2048, 1152)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.size = Vector2i(1280, 720)
	_game = load("res://scene/scene_bg.tscn").instantiate()
	root.add_child(_game)
	await _frames(6)

	if "--preview" in OS.get_cmdline_user_args():
		await _preview()
		return

	var boats: Array = _game.boats
	var state = _game.placement_panel.state

	# 起点定位：起点 x = origin + pos*step，三船之和须为 9。
	_game._configure_ship_starts()
	await _frames(1)
	var starts: Array = _game._ship_starts
	_check(int(starts[0]) + int(starts[1]) + int(starts[2]) == 9, "三船起点之和不为 9：%s" % [starts])
	for i in boats.size():
		_check(boats[i].route_position == int(starts[i]), "船 %d 起点号位未定位" % i)
		_check(is_equal_approx(boats[i].global_position.x, boats[i].route_x(int(starts[i]))), "船 %d 起点 x 未对齐号位" % i)
		_check(not boats[i].arrived and not state.arrived[i], "船 %d 起航前不应到港" % i)

	# 恰好停在 13：留在航线，不到港（海盗特例的前置）。
	boats[0].configure_route(10)
	var r0: Dictionary = boats[0].advance_by(3)
	_check(r0.to == 13 and not r0.crossed and not boats[0].arrived, "恰好停 13 被误判为到港")

	# 越过 13：立即到港，位置贴 dock_x，且已到港的船再投骰不动。
	boats[0].configure_route(11)
	var r1: Dictionary = boats[0].advance_by(3)
	_check(r1.crossed and boats[0].arrived, "越过 13 未判定到港")
	var r2: Dictionary = boats[0].advance_by(6)
	_check(not r2.moved, "已到港的船仍继续航行")

	# apply_sailing：按点数推三船，同步 state.arrived，动画目标为 dock_x。
	_game._configure_ship_starts()
	await _frames(1)
	var report: String = _game.apply_sailing([2, 6, 6])
	_check(not report.is_empty(), "航行报告为空")
	# 起点 3：+2 → 5 号位（未到港）；+6 → 9？不，需按各自起点判定。
	_check(boats[0].route_position == int(starts[0]) + 2 and not boats[0].arrived, "船0 推进/到港判定错误")
	for i in [1, 2]:
		var crossed: bool = int(starts[i]) + 6 > boats[i].ROUTE_END
		_check(boats[i].arrived == crossed and state.arrived[i] == crossed, "船 %d 到港同步与越 13 判定不一致" % i)

	# 越过 13 后应向 dock_x 靠泊（动画进行中，x 朝 dock 方向增大）。
	await _frames(30)
	for i in boats.size():
		if boats[i].arrived:
			_check(boats[i].global_position.x > boats[i].route_x(boats[i].ROUTE_END) - 1.0, "船 %d 到港后未向泊位移动" % i)

	# —— 货物映射解耦：换一组非默认货物，骰子按货物匹配到船，而非 index 死绑 ——
	# 选 nutmeg/jade/ginseng（含默认没有的 nutmeg，jade 有 4 座）；骰子顺序故意与船序不同。
	var ok: bool = _game.set_voyage(["nutmeg", "jade", "ginseng"], ["ginseng", "jade", "nutmeg"], [5, 4, 0])
	_check(ok, "set_voyage 合法输入被拒")
	# 船位应按新货物重建：jade 船 4 座，其余 3 座。
	_check(state.ships == ["nutmeg", "jade", "ginseng"], "选货未写入 ships")
	var jade_ship := int(state.ships.find("jade"))
	_check(state.ship_occupants(jade_ship).size() == 4, "jade 船未重建为 4 座")
	# 非法输入（重复/不足/未知货物）应被拒且不改状态。
	_check(not _game.set_voyage(["jade", "jade", "silk"]), "重复货物未被拒")
	_check(not _game.set_voyage(["jade", "silk"]), "不足三种未被拒")
	_check(state.ships == ["nutmeg", "jade", "ginseng"], "非法选货污染了状态")

	# 起航并推进，验证「按货物匹配」而非「按 index 死绑」：
	# 骰子序 _dice_cargo=[ginseng,jade,nutmeg]，值=[2,6,1]；船序=[nutmeg,jade,ginseng]、起点[5,4,0]。
	# 若 index 死绑：船0 会 +2 → 7。按货物：船0=nutmeg 拿 nutmeg 的骰(1) → 5+1=6。
	#   船1=jade 拿 jade 的骰(6) → 4+6=10；船2=ginseng 拿 ginseng 的骰(2) → 0+2=2。
	# （合法起点≤5，单次投骰最多 +6，不可能一次越 13；到港靠多次航行累积。）
	_game._configure_ship_starts()
	await _frames(1)
	for i in boats.size():
		_check(boats[i].cargo_id == state.ships[i], "船 %d 的 cargo_id 未随选货设置" % i)
	_game.apply_sailing([2, 6, 1])
	_check(boats[0].route_position == 6, "nutmeg 船应按 nutmeg 骰(+1)到 6，实为 %d（疑似 index 死绑）" % boats[0].route_position)
	_check(boats[1].route_position == 10, "jade 船应按 jade 骰(+6)到 10，实为 %d" % boats[1].route_position)
	_check(boats[2].route_position == 2, "ginseng 船应按 ginseng 骰(+2)到 2，实为 %d" % boats[2].route_position)
	_check(not boats[0].arrived and not boats[1].arrived and not boats[2].arrived, "单次航行不应越 13 到港")

	print("SAILING_CHECK failures=%d" % _failures.size())
	for f in _failures:
		print("  - " + f)
	_game.queue_free()
	await _frames(2)
	quit(0 if _failures.is_empty() else 1)


## 预览：真起投一次，落定后自动推船，限时结束并报告，不停在窗口等人。
func _preview() -> void:
	root.title = "Manila - 航行骰子推进预览"
	create_timer(40).timeout.connect(func(): push_error("SAILING_PREVIEW timed out"); quit(1))
	await _complete_dispatch_round()
	_game.begin_sailing()
	# 等骰子落定 + 收起骰盘 + 推进动画。
	var waited := 0.0
	while _game._sailing_active and waited < 20.0:
		await create_timer(0.2).timeout
		waited += 0.2
	await create_timer(1.5).timeout   # 让推进动画走一段
	await _frames(1)
	var moved := false
	for b in _game.boats:
		if b.route_position > 0 or b.arrived:
			moved = true
	_check(moved, "预览：船没有因骰子结果移动")
	print("SAILING_PREVIEW dice=%s failures=%d" % [_game._dice_results, _failures.size()])
	for f in _failures:
		print("  - " + f)
	await create_timer(2.5).timeout   # 有界停留，便于观察，然后退出
	_game.queue_free()
	await _frames(2)
	quit(0 if _failures.is_empty() else 1)


func _check(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)


func _frames(count: int) -> void:
	for i in count:
		await process_frame

func _complete_dispatch_round() -> void:
	var guard := 0
	while not _game._awaiting_sail and guard < 6:
		guard += 1
		var chosen := ""
		for item in _game.placement_panel.state.positions:
			if _game.placement_reason(item.id).is_empty():
				chosen = item.id
				break
		if chosen.is_empty():
			break
		var panel = _game.placement_panel
		panel.open()
		panel.select(chosen)
		panel.confirm_selection()
		await _frames(1)
	_check(_game._awaiting_sail, "预览未能完成本轮派遣")

