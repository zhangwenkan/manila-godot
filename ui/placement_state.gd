extends RefCounted

signal changed

const COSTS := {
	"ginseng": [1, 2, 3], "nutmeg": [2, 3, 4],
	"silk": [3, 4, 5], "jade": [3, 4, 5, 5],
}
const CARGO_NAMES := {"ginseng": "人参", "nutmeg": "肉豆蔻", "silk": "丝绸", "jade": "玉石"}
const ALL_CARGOES := ["ginseng", "nutmeg", "silk", "jade"]

var ships: Array[String] = ["ginseng", "silk", "jade"]
var positions: Array[Dictionary] = []
var owners: Dictionary = {}
var arrived: Array[bool] = [false, false, false]


func _init() -> void:
	_rebuild_positions()


## 本航程装货（R04）：从四种货物中选三种、每船装一种、不重复。
## 重建船位并清空占用与到港（准备阶段调用，派遣前）。返回是否合法。
func set_voyage_cargo(cargo_ids: Array) -> bool:
	if cargo_ids.size() != 3:
		return false
	var seen := {}
	for id in cargo_ids:
		if not COSTS.has(id) or seen.has(id):
			return false
		seen[id] = true
	ships.assign(cargo_ids)
	owners.clear()
	arrived.assign([false, false, false])
	_rebuild_positions()
	changed.emit()
	return true


## 第 ship 艘船本航程所装货物 id / 中文名。
func cargo_of(ship: int) -> String:
	return ships[ship] if ship >= 0 and ship < ships.size() else ""


func cargo_name(ship: int) -> String:
	var id := cargo_of(ship)
	return CARGO_NAMES.get(id, "货")


func _rebuild_positions() -> void:
	positions.clear()
	for ship in ships.size():
		for seat in COSTS[ships[ship]].size():
			positions.append({"id": "ship_%d_%d" % [ship, seat], "group": "ship_%d" % ship,
				"title": "%s · 第 %d 座" % [CARGO_NAMES[ships[ship]], seat + 1],
				"cost": COSTS[ships[ship]][seat], "effect": "到港后按船员人数分红；须先选最便宜空座", "ship": ship})
	for group in ["harbor", "shipyard"]:
		for berth in 3:
			positions.append({"id": "%s_%d" % [group, berth], "group": group,
				"title": "%s %s" % ["港口" if group == "harbor" else "修船厂", ["A", "B", "C"][berth]],
				"cost": [4, 3, 2][berth], "effect": "对应泊位有船时收益 %d 比索" % [6, 8, 15][berth], "ship": -1})
	positions.append({"id": "pirate_0", "group": "pirate", "title": "海盗船长", "cost": 5, "effect": "优先选择登船；第三次航行后可参与劫掠", "ship": -1})
	positions.append({"id": "pirate_1", "group": "pirate", "title": "海盗次席", "cost": 5, "effect": "船长席有人后可选；按顺序登船或参与劫掠", "ship": -1})
	positions.append({"id": "pilot_0", "group": "pilot", "title": "小引航员", "cost": 2, "effect": "第三次航行前，移动一艘船 1 格", "ship": -1})
	positions.append({"id": "pilot_1", "group": "pilot", "title": "大引航员", "cost": 5, "effect": "移动一船最多 2 格，或两船各 1 格", "ship": -1})
	positions.append({"id": "insurance_0", "group": "insurance", "title": "保险公司", "cost": 0, "effect": "派驻立即领取 10；航程结束须承担修船赔付", "ship": -1})


func get_position(id: String) -> Dictionary:
	for item in positions:
		if item.id == id:
			return item
	return {}


func unavailable_reason(id: String) -> String:
	var item := get_position(id)
	if item.is_empty():
		return "无此岗位"
	if owners.get(id) != null:
		return "位置已占用"
	if item.ship >= 0:
		if arrived[item.ship]:
			return "船已到港，不能再派人"
		for other in positions:
			if other.group == item.group and owners.get(other.id) == null and other.cost < item.cost:
				return "请先选更便宜的空座"
	if id == "pirate_1" and owners.get("pirate_0") == null:
		return "请先选择海盗船长席"
	return ""


func ship_occupants(ship: int) -> Array:
	var result: Array = []
	for item in positions:
		if item.ship == ship:
			result.append(owners.get(item.id))
	return result


func set_ship_arrived(ship: int, value: bool) -> void:
	arrived[ship] = value
	changed.emit()


func set_preview_occupants(value: Dictionary) -> void:
	owners = value.duplicate()
	changed.emit()
