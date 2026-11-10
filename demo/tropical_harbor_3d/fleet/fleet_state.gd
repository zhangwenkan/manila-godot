extends RefCounted

const CARGO := {
    "ginseng": {"label": "人参", "glyph": "参", "color": Color("d5b852"), "costs": [1, 2, 3]},
    "nutmeg": {"label": "肉豆蔻", "glyph": "蔻", "color": Color("ba815b"), "costs": [2, 3, 4]},
    "silk": {"label": "丝绸", "glyph": "绸", "color": Color("6eaaca"), "costs": [3, 4, 5]},
    "jade": {"label": "玉石", "glyph": "玉", "color": Color("76b89a"), "costs": [3, 4, 5, 5]}
}
const PLAYER_COLORS := [Color("d67558"), Color("5b91c0"), Color("d4b758")]
const LAYOUT = preload("res://demo/tropical_harbor_3d/environment/harbor_layout.gd")
const LANES := LAYOUT.LANES
const START_Z := LAYOUT.START_Z
const STEP := LAYOUT.STEP

var ships: Array[Dictionary] = []
var players: Array[Dictionary] = []
var current_player := 0
var rolls := 0
var voyage := 0
var next_berth := 0


func _init() -> void:
    for i in 3:
        players.append({"player_id": i, "character_id": "", "cash": 30, "available": 4})


func start_voyage(cargos: Array, starts: Array) -> String:
    if cargos.size() != 3 or starts.size() != 3:
        return "需要三种货物和三个起点"
    var used: Array = []
    var total := 0
    for i in 3:
        if not CARGO.has(cargos[i]) or cargos[i] in used:
            return "货物必须三种且不重复"
        if not starts[i] is int or starts[i] < 0 or starts[i] > 5:
            return "起点必须为 0–5 的整数"
        used.append(cargos[i])
        total += starts[i]
    if total != 9:
        return "起点之和必须为 9"
    ships.clear()
    rolls = 0
    next_berth = 0
    current_player = 0
    voyage += 1
    for player in players:
        player.available = 4
    for i in 3:
        var slots: Array[Dictionary] = []
        for index in CARGO[cargos[i]].costs.size():
            slots.append({"slot_id": index, "cost": CARGO[cargos[i]].costs[index], "owner": -1})
        ships.append({"ship_id": i, "cargo_id": cargos[i], "progress": starts[i],
            "arrived": false, "berth": -1, "slots": slots, "last_die": 0})
    return ""


func placement_error(ship_id: int, slot_id: int, player_id: int) -> String:
    if ship_id < 0 or ship_id >= ships.size() or player_id < 0 or player_id >= players.size():
        return "无效目标"
    var ship: Dictionary = ships[ship_id]
    if slot_id < 0 or slot_id >= ship.slots.size():
        return "岗位不存在"
    if ship.arrived:
        return "已到港，不再接收船员"
    if rolls >= 3:
        return "三次航行结束"
    var slot: Dictionary = ship.slots[slot_id]
    if slot.owner != -1:
        return "岗位已有人"
    for other in ship.slots:
        if other.owner == -1 and other.cost < slot.cost:
            return "先选更便宜的空位"
    if player_id != current_player:
        return "尚未轮到该玩家"
    if players[player_id].available <= 0:
        return "没有可用船员"
    if players[player_id].cash < slot.cost:
        return "资金不足（本阶段未接入贷款）"
    return ""


func place(ship_id: int, slot_id: int, player_id: int) -> String:
    var error := placement_error(ship_id, slot_id, player_id)
    if not error.is_empty():
        return error
    var slot: Dictionary = ships[ship_id].slots[slot_id]
    slot.owner = player_id
    players[player_id].cash -= slot.cost
    players[player_id].available -= 1
    current_player = (current_player + 1) % players.size()
    return ""


func roll(dice: Array) -> String:
    if ships.size() != 3 or dice.size() != 3 or rolls >= 3:
        return "当前不可航行"
    for die in dice:
        if not die is int or die < 1 or die > 6:
            return "骰子必须为 1–6"
    rolls += 1
    for i in 3:
        var ship: Dictionary = ships[i]
        if ship.arrived:
            continue
        ship.last_die = dice[i]
        ship.progress = mini(ship.progress + dice[i], 14)
        if ship.progress > 13:
            ship.arrived = true
            ship.berth = next_berth
            next_berth += 1
    return ""


func world_position(ship: Dictionary) -> Vector3:
    if ship.arrived:
        return Vector3(LAYOUT.BERTH_X[ship.berth], 0.0, LAYOUT.BERTH_Z)
    return Vector3(LANES[ship.ship_id], 0.0, START_Z - ship.progress * STEP)
