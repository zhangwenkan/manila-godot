extends SceneTree

const STATE = preload("res://demo/tropical_harbor_3d/fleet/fleet_state.gd")
var checks := 0
var failures := 0


func check(condition: bool, message: String) -> void:
    checks += 1
    if not condition:
        failures += 1
        push_error("FLEET_STATE_FAIL: " + message)


func _initialize() -> void:
    var state := STATE.new()
    var ids: Array = STATE.CARGO.keys()
    for a in ids:
        for b in ids:
            for c in ids:
                var cargos := [a, b, c]
                var distinct: bool = a != b and b != c and a != c
                var error := state.start_voyage(cargos, [0, 4, 5])
                check(error.is_empty() == distinct, "four choose three uniqueness")
                if distinct:
                    for i in 3:
                        check(state.ships[i].cargo_id == cargos[i], "cargo order")
                        check(state.ships[i].slots.size() == STATE.CARGO[cargos[i]].costs.size(), "cargo capacity")
    for a in 6:
        for b in 6:
            for c in 6:
                var error := state.start_voyage(["jade", "silk", "ginseng"], [a, b, c])
                check(error.is_empty() == (a + b + c == 9), "start sum")
    state.start_voyage(["jade", "silk", "ginseng"], [0, 4, 5])
    var before := JSON.stringify(state.ships)
    check(not state.start_voyage(["jade", "silk", "ginseng"], [-1, 5, 5]).is_empty(), "negative start")
    check(not state.start_voyage(["jade", "silk", "ginseng"], [1.0, 3, 5]).is_empty(), "integer start")
    check(JSON.stringify(state.ships) == before, "invalid setup is atomic")
    check(not state.place(0, 1, 0).is_empty(), "cheapest first")
    check(state.place(0, 0, 0).is_empty(), "player zero may occupy")
    check(state.ships[0].slots[0].owner == 0, "zero is not vacancy")
    check(state.players[0].cash == 27 and state.players[0].available == 3, "single charge")
    var balance: int = state.players[0].cash
    check(not state.place(0, 0, 0).is_empty() and state.players[0].cash == balance, "double-click cannot double-charge")
    check(state.place(0, 1, 1).is_empty(), "second cheapest")
    check(state.placement_error(0, 2, 2).is_empty() and state.placement_error(0, 3, 2).is_empty(), "equal cost seats both legal")
    check(state.place(0, 3, 2).is_empty(), "choose later equal seat")
    check(state.place(0, 2, 0).is_empty(), "same player may occupy twice")
    check(not state.place(0, 4, 1).is_empty(), "out of range seat")
    state.start_voyage(["silk", "ginseng", "nutmeg"], [0, 4, 5])
    check(state.ships[0].slots.size() == 3 and state.ships[0].slots[0].owner == -1, "fourth seat and owners cleared")
    check(state.players[0].cash == 22 and state.players[0].available == 4, "new voyage preserves money and returns crew")
    check(not state.roll([0, 4, 5]).is_empty() and state.rolls == 0, "invalid dice atomic")
    check(state.roll([1, 6, 6]).is_empty(), "first independent dice")
    check(state.ships[0].progress == 1 and state.ships[1].progress == 10 and state.ships[2].progress == 11, "independent movement")
    state.roll([1, 3, 3])
    check(state.ships[1].progress == 13 and not state.ships[1].arrived, "13 not harbor")
    check(state.ships[2].arrived and state.ships[2].berth == 0, "first arrival gets berth zero regardless of lane")
    check(not state.placement_error(2, 0, state.current_player).is_empty(), "arrived rejects crew")
    state.roll([1, 6, 6])
    check(state.ships[2].progress == 14 and state.ships[2].berth == 0, "arrived ship unchanged")
    check(state.ships[1].progress == 14 and state.ships[1].berth == 1, "overshoot discarded, next berth")
    check(state.ships[0].progress == 3, "reachable extreme gap")
    check(not state.roll([1, 1, 1]).is_empty(), "no fourth roll")
    check(not state.place(0, 0, state.current_player).is_empty(), "no dispatch after third roll")
    state.start_voyage(["jade", "silk", "ginseng"], [3, 3, 3])
    state.players[0].cash = 0
    check(not state.place(0, 0, 0).is_empty(), "insufficient funds is explicit")
    state.players[0].cash = 30
    state.players[0].available = 0
    check(not state.place(0, 0, 0).is_empty(), "no crew")
    print("FLEET_STATE_%s checks=%d failures=%d" % ["PASS" if failures == 0 else "FAIL", checks, failures])
    quit(0 if failures == 0 else 2)
