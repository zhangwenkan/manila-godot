extends SceneTree
## Run headlessly with --path <project> --script res://tools/harbor_pixel_rules_check.gd.
## Uses direct script loading, not class_name/import caches. All drivers are bounded.

const GAME = preload("res://demo/harbor_pixel/harbor_game.gd")
const WATCHDOG_SECONDS := 15.0
var _failures: Array[String] = []
var _checks := 0
var _deadline := 0


func _initialize() -> void:
	_deadline = Time.get_ticks_msec() + int(WATCHDOG_SECONDS * 1000)
	create_timer(WATCHDOG_SECONDS).timeout.connect(func():
		push_error("HARBOR_PIXEL_RULES_CHECK watchdog expired")
		quit(1))
	call_deferred("_run")


func _run() -> void:
	_test_reset_and_inventory()
	_test_auction_and_permissions()
	_test_master_round_order()
	_test_atomic_setup_and_stock()
	_test_placement_validation()
	_test_sequential_ai_and_rounds()
	_test_permanent_pass_and_dice()
	_test_per_pawn_and_shore_payouts()
	_test_insurance()
	_test_exact_thirteen_and_pirates()
	_test_pilots()
	_test_next_voyage_and_game_end()
	_test_bounded_full_games()
	print("HARBOR_PIXEL_RULES_CHECK checks=%d failures=%d" % [_checks, _failures.size()])
	for failure in _failures:
		print("  FAIL: " + failure)
	quit(0 if _failures.is_empty() else 1)


func _check(condition: bool, message: String) -> void:
	_checks += 1
	if not condition:
		_failures.append(message)


func _new(seed_value: int = 317, prepare: bool = true):
	var game = GAME.new()
	game.reset(seed_value)
	if prepare:
		_elect(game, 0)
		_check(game.skip_stock(0), "Fixture skips stock through public API")
	return game


func _elect(game, master: int) -> void:
	for step in 12:
		if game.phase != "auction":
			break
		var actor: int = game.current_player
		_check(game.bid(game.auction_bid + 1, actor) if actor == master else game.pass_bid(actor), "Fixture auction action")
	_check(game.phase == "stock" and game.harbormaster == master, "Fixture elects requested master")


func _snapshot(game) -> Dictionary:
	return {"players": game.players.duplicate(true), "cargo": game.cargo.duplicate(),
		"positions": game.positions.duplicate(), "prices": game.prices.duplicate(),
		"stock": game.stock.duplicate(), "owners": game.slots.owners.duplicate(),
		"slot_positions": game.slots.positions.duplicate(true), "ships": game.slots.ships.duplicate(),
		"arrived": game.slots.arrived.duplicate(), "phase": game.phase,
		"current": game.current_player, "voyage": game.voyage, "round": game.dispatch_round,
		"sails": game.sail_count, "dice": game.dice.duplicate(), "logs": game.log_lines.duplicate(),
		"settlement": game.settlement_lines.duplicate(), "passed": game._passed.duplicate(),
		"bought": game._bought_stock, "settled": game._settled,
		"pilots": game._pilots_done, "rng": game._rng.state,
		"master": game.harbormaster, "previous_master": game.previous_harbormaster,
		"bid": game.auction_bid, "leader": game.auction_leader, "auction_passed": game.auction_passed.duplicate(),
		"visited": game._dispatch_visited}


func _unchanged(game, before: Dictionary, message: String) -> void:
	_check(_snapshot(game) == before, message)


func _pass_dispatch(game) -> void:
	var actions := 0
	while game.phase == "dispatch" and actions < 12 and Time.get_ticks_msec() < _deadline:
		if not game.pass_turn():
			_check(false, "Could not pass current dispatch actor")
			return
		actions += 1
	_check(game.phase != "dispatch", "Dispatch driver exceeded bounded action/time budget")


func _first_legal(game) -> String:
	for item in game.slots.positions:
		if game.placement_reason(item.id).is_empty():
			return item.id
	return ""


func _opening(game, actions: Array) -> void:
	_check(game.begin_voyage(), "Scenario voyage could not begin")
	for id in actions:
		_check(game.pass_turn() if id == "pass" else game.place(id), "Scenario action rejected: %s" % id)


func _finish_with(game, first: Array, second: Array, third: Array) -> void:
	for values in [first, second, third]:
		_pass_dispatch(game)
		_check(game.roll(values), "Scenario sailing rejected: %s" % [values])
	_check(game.phase == "settlement" and game.sail_count == 3, "Scenario did not settle after exactly three sails")


func _cash(game) -> Array:
	return [game.players[0].cash, game.players[1].cash, game.players[2].cash]


func _test_reset_and_inventory() -> void:
	var game = _new(317, false)
	_check(game is RefCounted and not game is Node, "Rules must be a pure RefCounted")
	_check(game.has_signal("changed"), "Missing changed signal")
	_check(game.phase == "auction" and game.harbormaster == -1 and game.voyage == 1 and game.current_player == 0, "Initial phase/master/voyage wrong")
	_check(game.positions == [2, 3, 4] and game.cargo == ["ginseng", "silk", "jade"], "Initial cargo/start wrong")
	_check(game.dispatch_round == 0 and game.sail_count == 0 and game.max_voyages == 3, "Initial counters wrong")
	_check(game.players.size() == 3 and game.PAYOUTS == {"ginseng": 18, "nutmeg": 24, "silk": 30, "jade": 36}, "Payout/player contract wrong")
	for player in game.players:
		_check(player.cash == 30 and player.crew == 4 and player.color is Color, "Initial player resources/color wrong")
		_check(player.holdings.values().reduce(func(a, b): return a + b, 0) == 2, "Initial deal did not give two cards")
	for id in game.CARGO_IDS:
		var count: int = game.stock[id]
		for player in game.players:
			count += player.holdings[id]
		_check(count == 5 and game.prices[id] == 0 and game.stock[id] >= 0, "Stock conservation failed: " + id)
	_check(game.stock.values().reduce(func(a, b): return a + b, 0) == 14, "Undealt inventory must total 14")
	var original := _snapshot(game)
	game.reset(317)
	_unchanged(game, original, "Same seed failed to reset to identical state")
	var other = _new(317, false)
	_unchanged(other, original, "Same seed differed across model instances")
	for instance in [game, other]:
		_elect(instance, 0)
		instance.skip_stock(0)
		instance.begin_voyage()
		_pass_dispatch(instance)
		instance.roll()
	_check(game.dice == other.dice and game._rng.state == other._rng.state, "Seeded dice are not reproducible")
	game.reset(318)
	_check(game._rng.state != original.rng, "Different seed failed to change RNG")
	_check(game.log_lines.any(func(line): return line.contains("简化")) and game.log_lines.any(func(line): return line.contains("贷款")), "Demo deviations not documented in logs")


func _test_auction_and_permissions() -> void:
	var game = _new(17, false)
	var before := _snapshot(game)
	_check(not game.bid(0) and not game.bid(31) and not game.bid(1, 1) and not game.pass_bid(2), "Reject invalid opening bids/actors")
	for amount in [1.5, true, "2", null]:
		_check(not game.bid(amount, 0), "Bid amount must be an integer without coercion")
	_check(not game.begin_voyage() and not game.skip_stock() and not game.buy_stock("jade"), "Cannot bypass auction")
	_unchanged(game, before, "Invalid auction action is atomic")
	_check(game.bid(2, 0) and _cash(game) == [30, 30, 30], "Bid reserves no cash")
	before = _snapshot(game)
	_check(not game.bid(2, 1) and not game.bid(3, 0), "Must increase; leader cannot bid twice")
	_unchanged(game, before, "Rejected repeat bid is atomic")
	_check(game.pass_bid(1) and game.bid(3, 2), "Challenge after player passes")
	_check(game.current_player == 0, "Auction wraps to earlier leader")
	before = _snapshot(game)
	_check(not game.bid(4, 1), "Passed actor cannot rejoin")
	_unchanged(game, before, "Passed bid is atomic")
	_check(game.pass_bid(0), "Leader concedes to challenger")
	_check(game.phase == "stock" and game.harbormaster == 2 and _cash(game) == [30, 30, 27], "Only winner pays once")
	before = _snapshot(game)
	_check(not game.bid(4, 2) and not game.pass_bid(2) and not game.buy_stock("jade", 0) and not game.skip_stock(0), "Award cannot repeat or grant others stock access")
	_unchanged(game, before, "Rejected award/stock actions are atomic")
	_check(game.skip_stock(2), "Winner skips stock")
	before = _snapshot(game)
	_check(not game.begin_voyage([], [], 0) and not game.skip_stock(2), "Only winner submits once")
	_unchanged(game, before, "Wrong setup actor has no effects")
	_check(game.begin_voyage([], [], 2), "AI master can submit")
	_pass_dispatch(game)
	before = _snapshot(game)
	_check(not game.roll([6, 6, 6], 0), "Non-master cannot roll")
	_unchanged(game, before, "Unauthorized roll has no RNG effects")
	for step in 3:
		_check(game.roll([1, 1, 1], 2), "Master rolls each sail")
	_check(game.next_voyage() and game.current_player == 2, "Next auction starts with former master")
	var cash := _cash(game)
	for step in 3:
		_check(game.pass_bid(game.current_player), "Later voyage all-pass action")
	_check(game.phase == "stock" and game.harbormaster == 2 and _cash(game) == cash, "All-pass retains former master without payment")
	game = _new(17, false)
	for step in 3:
		_check(game.pass_bid(game.current_player), "First auction all-pass action")
	_check(game.phase == "auction" and game.current_player == 0 and game.auction_leader == -1 and game.auction_passed == [false, false, false] and _cash(game) == [30, 30, 30], "First all-pass restarts without charging or appointing")


func _test_master_round_order() -> void:
	for master in 3:
		var game = _new(13, false)
		_elect(game, master)
		_check(game.skip_stock(master) and game.begin_voyage([], [], master), "Master fixture starts dispatch")
		for round_number in range(1, 5):
			_check(game.phase == "dispatch" and game.dispatch_round == round_number, "Round is active")
			for offset in 3:
				var actor := (master + offset) % 3
				_check(game.current_player == actor, "All masters get full circular dispatch order")
				_check(game.place(_first_legal(game), actor), "Circular dispatch accepts one pawn")
			if round_number > 1:
				_check(game.phase == "sailing" and game.current_player == master, "Master gets sailing turn")
				_check(game.roll([1, 1, 1], master), "Master advances round")
		_check(game.phase == "settlement" and game.players.all(func(p): return p.crew == 0), "All twelve pawns used across all starting seats")


func _test_atomic_setup_and_stock() -> void:
	var game = _new()
	var changes := {"count": 0}
	game.changed.connect(func(): changes.count += 1)
	var before := _snapshot(game)
	var bad_cargoes := [["ginseng", "ginseng", "jade"], ["ginseng", "silk"],
		["ginseng", "silk", "fake"], ["ginseng", 1, "jade"], ["ginseng", "silk", "jade", "nutmeg"]]
	for ids in bad_cargoes:
		_check(not game.begin_voyage(ids, [2, 3, 4]), "Invalid cargo accepted: %s" % [ids])
		_unchanged(game, before, "Invalid cargo mutated setup")
	var bad_starts := [[0, 0, 0], [6, 1, 2], [-1, 5, 5], [3, 3], [3, 3, 3, 0],
		[3.0, 3, 3], [true, 3, 5], ["3", 3, 3], [null, 4, 5]]
	for starts in bad_starts:
		_check(not game.begin_voyage(["nutmeg", "silk", "jade"], starts), "Invalid start accepted: %s" % [starts])
		_unchanged(game, before, "Invalid start mutated cargo/slots/resources")
	_check(changes.count == 0, "Rejected setup emitted changed")
	game = _new(317, false)
	_elect(game, 0)
	before = _snapshot(game)
	_check(not game.buy_stock("ginseng", 1) and not game.buy_stock("unknown") and not game.buy_stock("jade", -1), "Unauthorized/unknown stock purchase accepted")
	_unchanged(game, before, "Rejected stock actor/id mutated state")
	game.players[0].cash = 4
	before = _snapshot(game)
	_check(not game.buy_stock("ginseng"), "Unaffordable stock accepted")
	_unchanged(game, before, "Unaffordable stock mutated state")
	game.players[0].cash = 30
	var old_stock: int = game.stock.ginseng
	var old_holding: int = game.players[0].holdings.ginseng
	_check(game.buy_stock("ginseng"), "Setup stock purchase rejected")
	_check(game.players[0].cash == 25 and game.stock.ginseng == old_stock - 1 and game.players[0].holdings.ginseng == old_holding + 1, "Purchase did not transfer exactly one card/cost five")
	before = _snapshot(game)
	_check(not game.buy_stock("jade"), "Second stock purchase in one voyage accepted")
	_unchanged(game, before, "Second stock purchase mutated state")
	_check(game.begin_voyage(["nutmeg", "silk", "jade"], [0, 4, 5]), "Valid custom setup rejected")
	_check(game.positions == [0, 4, 5] and game.slots.ships == ["nutmeg", "silk", "jade"], "Custom setup did not propagate to slot model")
	before = _snapshot(game)
	_check(not game.begin_voyage() and not game.buy_stock("nutmeg"), "Setup operation accepted after voyage began")
	_unchanged(game, before, "Rejected live setup mutated state")
	game = _new(317, false)
	_elect(game, 0)
	game.stock.jade = 0
	before = _snapshot(game)
	_check(not game.buy_stock("jade"), "Sold-out stock purchase accepted")
	_unchanged(game, before, "Sold-out purchase mutated state")
	game.stock.jade = 1
	game.prices.jade = 20
	_check(game.buy_stock("jade") and game.players[0].cash == 9, "Stock purchase did not use market price above five")


func _test_placement_validation() -> void:
	var game = _new()
	var before := _snapshot(game)
	_check(not game.place("ship_0_0") and not game.pass_turn() and not game.ai_step() and not game.roll([1, 1, 1]), "Setup accepted dispatch/sailing actions")
	_unchanged(game, before, "Rejected setup action mutated model")
	game.begin_voyage()
	for request in [["missing", 0], ["ship_0_1", 0], ["pirate_1", 0], ["ship_0_0", 1], ["ship_0_0", -2], ["ship_0_0", 99]]:
		before = _snapshot(game)
		_check(not game.placement_reason(request[0], request[1]).is_empty(), "Invalid placement has no reason")
		_check(not game.place(request[0], request[1]), "Invalid placement accepted")
		_unchanged(game, before, "Invalid placement changed cash/crew/turn/owners")
	game.players[0].cash = 0
	before = _snapshot(game)
	_check(not game.place("ship_0_0") and game.placement_reason("ship_0_0").contains("现金"), "Unaffordable placement accepted/no reason")
	_unchanged(game, before, "Insufficient funds mutated state")
	_check(game.place("insurance_0") and game.players[0].cash == 10, "Cash-zero actor could not choose free insurance")
	before = _snapshot(game)
	_check(not game.place("insurance_0") and not game.place("ship_0_0", 0) and not game.pass_turn(0), "Duplicate/wrong-turn action accepted")
	_unchanged(game, before, "Duplicate/wrong-turn changed resources")
	game.slots.arrived[0] = true
	before = _snapshot(game)
	_check(not game.place("ship_0_0") and game.placement_reason("ship_0_0").contains("到港"), "Arrived ship accepted crew")
	_unchanged(game, before, "Arrived ship rejection mutated state")
	game.players[1].crew = 0
	before = _snapshot(game)
	_check(not game.place("harbor_0") and not game.pass_turn(), "Exhausted player accepted an action")
	_unchanged(game, before, "Exhausted action mutated state")
	# Same-cost jade seats are both legal once the cheaper seats are filled.
	game = _new()
	_opening(game, ["ship_2_0", "ship_2_1", "ship_2_3"])
	_check(game.slots.owners.has("ship_2_3"), "Equal-cost seat was incorrectly blocked")


func _test_sequential_ai_and_rounds() -> void:
	var game = _new(53)
	game.begin_voyage()
	var before := _snapshot(game)
	_check(not game.ai_step(), "AI moved for the human")
	_unchanged(game, before, "Rejected human AI step mutated state")
	for round_number in range(1, 5):
		_check(game.phase == "dispatch" and game.dispatch_round == round_number and game.current_player == 0, "Dispatch round did not start at human: %d" % round_number)
		for actor in 3:
			_check(game.current_player == actor, "AI/placement skipped or repeated an actor")
			var crew: int = game.players[actor].crew
			var owner_count: int = game.slots.owners.size()
			var id := _first_legal(game)
			var success: bool = game.place(id) if actor == 0 else game.ai_step()
			_check(success, "Sequential placement/AI failed")
			_check(game.players[actor].crew == crew - 1 and game.slots.owners.size() == owner_count + 1, "One action did not place exactly one pawn")
		if round_number == 1:
			_check(game.phase == "dispatch" and game.dispatch_round == 2 and game.sail_count == 0, "First sail occurred before two opening rounds")
		else:
			_check(game.phase == "sailing" and game.sail_count == round_number - 2, "Round ended at wrong sailing count")
			before = _snapshot(game)
			_check(not game.ai_step() and not game.place("harbor_2") and not game.pass_turn(), "Dispatch action accepted while sailing")
			_unchanged(game, before, "Rejected sailing dispatch action mutated state")
			_check(game.roll([1, 1, 1]), "Legal sequential roll rejected")
	_check(game.phase == "settlement" and game.sail_count == 3 and game.dispatch_round == 4, "Four dispatch rounds did not end in third-sail settlement")
	_check(game.players.all(func(player): return player.crew == 0), "Normal dispatch did not use four crew each")
	# AI with no affordable empty destination must permanently pass, once.
	game = _new()
	_opening(game, ["insurance_0"])
	game.players[1].cash = 0
	var crew: int = game.players[1].crew
	_check(game.ai_step() and game._passed[1] and game.players[1].crew == crew and game.current_player == 2, "Poor AI did not make exactly one permanent pass")


func _test_permanent_pass_and_dice() -> void:
	var game = _new()
	game.begin_voyage()
	_check(game.pass_turn(0), "Human permanent pass rejected")
	_check(game.ai_step() and game.ai_step(), "AI could not finish first passed round")
	_check(game.dispatch_round == 2 and game.current_player == 1, "Permanently passed human re-entered round two")
	var before := _snapshot(game)
	_check(not game.place("ship_0_0", 0) and not game.pass_turn(0), "Passed human re-entered voyage")
	_unchanged(game, before, "Passed player's rejected action mutated state")
	_pass_dispatch(game)
	_check(game.phase == "sailing" and game.dispatch_round == 2, "All-pass opening failed to reach sailing")
	var invalid := [[1, 2], [1, 2, 3, 4], [0, 1, 1], [1, 7, 1], [1.0, 2, 3], [true, 2, 3], ["1", 2, 3], [null, 1, 1]]
	for values in invalid:
		before = _snapshot(game)
		_check(not game.roll(values), "Invalid dice accepted: %s" % [values])
		_unchanged(game, before, "Invalid dice changed state or RNG")
	for step in 3:
		_check(game.roll([1, 2, 3]), "All-pass sailing failed")
		_check(game.sail_count == step + 1 and game.dice == [1, 2, 3], "Roll committed wrong dice/count")
		if step < 2:
			_check(game.phase == "sailing" and game.dispatch_round == step + 3, "All-pass empty dispatch did not automatically skip")
	before = _snapshot(game)
	_check(not game.roll() and not game.roll([1, 2, 3]), "Settlement accepted another roll")
	game._settle()
	_unchanged(game, before, "Repeated settlement paid or advanced market twice")


func _test_per_pawn_and_shore_payouts() -> void:
	var game = _new()
	_opening(game, ["ship_2_0", "ship_2_1", "shipyard_0", "ship_2_2", "harbor_0", "harbor_1"])
	var before := _cash(game)
	_finish_with(game, [1, 1, 6], [1, 1, 4], [1, 1, 1])
	_check(_cash(game) == [before[0] + 24, before[1] + 12 + 6, before[2] + 6], "Mixed jade crew was not paid 24/12 per pawn; shore count rewards wrong")
	_check(game.slots.arrived == [false, false, true] and game.prices.jade == 5, "Early jade arrival/market result wrong")
	_check(game.positions[2] == 14, "Already-arrived ship moved again")
	# All three shore berths activate by count, not by the ship's cargo/index.
	for group in ["harbor", "shipyard"]:
		game = _new()
		_opening(game, [group + "_0", group + "_1", group + "_2", "pass", "pass", "pass"])
		before = _cash(game)
		var values: Array = [6, 6, 6] if group == "harbor" else [1, 1, 1]
		_finish_with(game, values, values, values)
		_check(_cash(game) == [before[0] + 6, before[1] + 8, before[2] + 15], "%s berth rewards must be 6/8/15" % group)
	# Every cargo payout, with one owner taking all three occupied seats.
	for id in game.CARGO_IDS:
		game = _new()
		var ids: Array = [id, "silk", "jade"] if id in ["ginseng", "nutmeg"] else [id, "ginseng", "nutmeg"]
		game.begin_voyage(ids, [3, 3, 3])
		# Settlement fixture: 3 real pawn entries (not a set of unique owners).
		game.slots.owners = {"ship_0_0": 0, "ship_0_1": 0, "ship_0_2": 0}
		game.players[0].crew = 1
		before = _cash(game)
		_finish_with(game, [6, 1, 1], [6, 1, 1], [1, 1, 1])
		_check(game.players[0].cash == before[0] + game.PAYOUTS[id], "Cargo payout wrong for " + id)


func _test_insurance() -> void:
	var game = _new()
	_opening(game, ["insurance_0", "shipyard_0", "harbor_0", "pass", "pass", "pass"])
	_check(game.players[0].cash == 39, "Insurance did not immediately pay exactly ten")
	var before := _cash(game)
	_finish_with(game, [1, 1, 1], [1, 1, 1], [1, 1, 1])
	_check(_cash(game) == [before[0] - 29, before[1] + 6, before[2]], "Insurance did not owe 29 including unoccupied repair berths, or repeated immediate bonus")
	_check(game.settlement_lines.any(func(line): return line.contains("保险责任 29")), "Insurance liability not explained")
	var snapshot := _snapshot(game)
	_check(not game.roll([1, 1, 1]), "Insurance could be settled twice")
	game._settle()
	_unchanged(game, snapshot, "Repeated insurance settlement mutated cash")
	game = _new()
	_opening(game, ["insurance_0", "shipyard_1", "harbor_0", "shipyard_0", "pass", "pass"])
	# Exercise insolvent insurer after costs; retain self-owned repair berth income.
	game.players[0].cash = 0
	before = _cash(game)
	_finish_with(game, [1, 1, 1], [1, 1, 1], [1, 1, 1])
	_check(game.players[0].cash == 0 and game.players[1].cash == before[1] + 8, "Bank did not cover insolvent insurer without negative cash")
	_check(game.settlement_lines.any(func(line): return line.contains("银行补足 23")), "Insurer should use own six income first, then bank cover remaining 23")
	_check(game.players.all(func(player): return player.cash >= 0), "Settlement generated negative cash")
	game = _new()
	_opening(game, ["insurance_0", "pass", "pass", "pass"])
	_finish_with(game, [6, 6, 6], [6, 6, 6], [6, 6, 6])
	_check(game.players[0].cash == 39, "Undamaged voyage charged insurer or paid ten again")


func _test_exact_thirteen_and_pirates() -> void:
	var game = _new()
	_opening(game, ["ship_0_0", "harbor_0", "shipyard_0", "pass", "pass", "pass"])
	var before := _cash(game)
	_finish_with(game, [4, 3, 2], [4, 3, 2], [3, 1, 1])
	_check(game.positions == [13, 10, 9] and game.slots.arrived == [true, false, false], "Third-sail exact 13 without pirates did not arrive normally")
	_check(_cash(game) == [before[0] + 18, before[1] + 6, before[2] + 6], "Exact13 normal payout/repair counts wrong")
	_check(game.prices.ginseng == 5 and game.prices.silk == 0, "Exact13 normal arrival market wrong")
	game = _new()
	_opening(game, ["pirate_0", "ship_0_0", "shipyard_0", "pirate_1", "ship_0_1", "harbor_0"])
	before = _cash(game)
	_finish_with(game, [4, 1, 1], [4, 1, 1], [3, 1, 1])
	_check(_cash(game) == [before[0] + 18, before[1], before[2] + 12], "Two pirate pawns of same owner did not split full cargo; crew wrongly got dividend")
	_check(game.players[1].crew == 4 and game.slots.ship_occupants(0) == [null, null, null], "Plundered original crew did not return")
	_check(game.slots.arrived[0] and game.prices.ginseng == 5, "Plunder did not automatically send port/raise price")
	_check(game.settlement_lines.any(func(line): return line.contains("劫掠后自动送港")), "Pirate simplification not logged explicitly")
	# Different pirate owners receive one share each across multiple plundered ships.
	game = _new()
	_opening(game, ["pirate_0", "pirate_1", "ship_2_0", "pass", "pass", "pass"])
	before = _cash(game)
	_finish_with(game, [4, 4, 3], [4, 4, 3], [3, 2, 3])
	_check(game.positions == [13, 13, 13] and game.slots.arrived == [true, true, true], "Multiple exact13 ships were not all sent to port")
	_check(_cash(game) == [before[0] + 42, before[1] + 42, before[2]], "Multiple plundered cargoes did not pay two pirates (18+30+36)/2")
	# Sail two exactly 13 remains on water; pirates explicitly stay in their seats.
	game = _new()
	_opening(game, ["pirate_0", "ship_0_0", "pass", "pass", "pass"])
	_check(game.roll([5, 1, 1]) and game.roll([6, 1, 1]), "Second-sail exact13 setup failed")
	_check(game.positions[0] == 13 and not game.slots.arrived[0], "Second-sail exact13 was treated as immediate arrival")
	_check(game.slots.owners.pirate_0 == 0 and game.slots.owners.ship_0_0 == 1, "Demo pirates boarded on second sail")
	before = _cash(game)
	_check(game.roll([1, 1, 1]), "Exact13 ship did not sail onward")
	_check(game.players[0].cash == before[0] and game.players[1].cash == before[1] + 18, "Pirates plundered a ship that crossed 13 on sail three")


func _test_pilots() -> void:
	var game = _new()
	_opening(game, ["ship_0_0", "ship_1_0", "ship_2_0", "pilot_0", "pilot_1", "pass"])
	_check(game.roll([4, 4, 4]), "Pilot first sailing setup failed")
	_pass_dispatch(game)
	_check(game.roll([6, 6, 1]), "Pilot second sailing setup failed")
	_check(game.positions == [12, 13, 9] and not game._pilots_done, "Pilots acted before third sailing")
	var before := _snapshot(game)
	_check(not game.roll([0, 1, 1]), "Invalid final die accepted")
	_unchanged(game, before, "Invalid final dice applied pilot effects")
	_check(game.roll([1, 1, 1]), "Final sailing with pilots failed")
	_check(game.positions == [14, 14, 10] and game.slots.arrived == [true, true, false], "Small/big pilots did not advance owner ships before dice")
	_check(game._pilots_done and game.log_lines.any(func(line): return line.contains("由引航直接到港")), "Pilot arrival or once-only tracking missing")
	before = _snapshot(game)
	game._apply_pilots()
	_unchanged(game, before, "Pilots applied more than once")
	# Benefit selection: near-arrival ginseng gains its full payout, while jade
	# already reaches port with any final die and gains nothing from the pilot.
	game = _new()
	game.begin_voyage()
	game.slots.owners = {"ship_0_0": 0, "ship_2_0": 0, "pilot_1": 0}
	game.positions.assign([5, 6, 12])
	_check(game._pilot_target(0, 2) == 0, "Pilot picked higher-value ship instead of greatest incremental benefit")
	game = _new()
	_opening(game, ["pilot_0", "pass", "pass", "pass"])
	_finish_with(game, [1, 1, 1], [1, 1, 1], [1, 1, 1])
	_check(game.positions == [5, 6, 7] and game.log_lines.any(func(line): return line.contains("自动放弃")), "Pilot without owned ship did not log a no-op")


func _test_next_voyage_and_game_end() -> void:
	var game = _new(317, false)
	_elect(game, 0)
	var before := _snapshot(game)
	_check(not game.next_voyage(), "next_voyage accepted outside settlement")
	_unchanged(game, before, "Rejected next voyage mutated setup")
	game.buy_stock("ginseng")
	_opening(game, ["ship_0_0", "insurance_0", "harbor_0", "pass", "pass", "pass"])
	_finish_with(game, [6, 6, 6], [6, 6, 6], [6, 6, 6])
	var cash := _cash(game)
	var holdings: Array = game.players.map(func(player): return player.holdings.duplicate())
	var prices: Dictionary = game.prices.duplicate()
	var inventory: Dictionary = game.stock.duplicate()
	_check(game.next_voyage(), "Valid next voyage rejected")
	_check(game.phase == "auction" and game.voyage == 2 and game.dispatch_round == 0 and game.sail_count == 0, "Next voyage counters wrong")
	_check(game.positions == [2, 3, 4] and game.slots.owners.is_empty() and game.slots.arrived == [false, false, false], "Next voyage did not reset positions/owners/arrival")
	_check(game.players.all(func(player): return player.crew == 4) and game.settlement_lines.is_empty(), "Next voyage did not restore crew/clear previous settlement")
	_check(_cash(game) == cash and game.prices == prices and game.stock == inventory, "Next voyage did not preserve cash/prices/inventory")
	for actor in 3:
		_check(game.players[actor].holdings == holdings[actor], "Next voyage changed holdings")
	_elect(game, 0)
	_check(game.buy_stock("jade"), "New voyage did not reopen single stock purchase")
	# Full three-voyage demo reaches final confirmation without a fourth voyage.
	for expected_voyage in [2, 3]:
		if game.phase == "auction":
			_elect(game, 0)
			game.skip_stock(0)
		game.begin_voyage()
		_finish_with(game, [6, 6, 6], [6, 6, 6], [6, 6, 6])
		_check(game.phase == "settlement" and game.voyage == expected_voyage, "Final settlement was hidden or voyage incremented early")
		_check(game.next_voyage(), "Settlement confirmation failed")
	_check(game.phase == "finished" and game.voyage == 3 and game.prices.ginseng == 20, "Demo did not end after three voyages with stepped price 20")
	before = _snapshot(game)
	_check(not game.next_voyage() and not game.begin_voyage() and not game.buy_stock("jade") and not game.roll() and not game.ai_step(), "Finished game accepted more operations")
	_unchanged(game, before, "Finished action mutated final state")
	# Print market is 0 -> 5 -> 10 -> 20 -> 30, not arithmetic increments.
	game = _new()
	game.max_voyages = 10
	for expected_price in [5, 10, 20, 30]:
		if game.phase == "auction":
			_elect(game, 0)
			game.skip_stock(0)
		game.begin_voyage()
		_finish_with(game, [6, 6, 6], [6, 6, 6], [6, 6, 6])
		_check(game.prices.ginseng == expected_price, "Market skipped/miscomputed printed step %d" % expected_price)
		game.next_voyage()
	_check(game.phase == "finished" and game.voyage == 4, "Any cargo reaching 30 did not end game before configured limit")
	game = _new()
	game.players[0].cash = 20
	game.players[1].cash = 10
	game.players[2].cash = 20
	for player in game.players:
		player.holdings = {"ginseng": 0, "nutmeg": 0, "silk": 0, "jade": 0}
	game.prices.jade = 20
	game.players[1].holdings.jade = 2
	_check(game.wealth(0) == 20 and game.wealth(1) == 50 and game.wealth(-1) == 0 and game.wealth(3) == 0, "Wealth formula/actor validation wrong")
	_check(game.ranking() == [1, 0, 2], "Ranking did not sort wealth descending with stable ties")


func _test_bounded_full_games() -> void:
	# Public-API-only playthroughs catch interactions not represented by fixtures.
	for seed_value in range(24):
		var game = _new(seed_value, false)
		var steps := 0
		while game.phase != "finished" and steps < 160 and Time.get_ticks_msec() < _deadline:
			var success := false
			match game.phase:
				"auction":
					success = game.pass_bid(0) if game.current_player == 0 else game.ai_step()
				"stock":
					success = game.skip_stock(0) if game.harbormaster == 0 else game.ai_step()
				"setup":
					success = game.begin_voyage([], [], 0) if game.harbormaster == 0 else game.ai_step()
				"dispatch":
					if game.current_player > 0:
						success = game.ai_step()
					else:
						var id := _first_legal(game)
						success = game.pass_turn() if id.is_empty() or seed_value % 5 == 0 else game.place(id)
				"sailing":
					success = game.roll([], game.harbormaster)
				"settlement":
					success = game.next_voyage()
			_check(success, "Full game got stuck: seed=%d phase=%s step=%d" % [seed_value, game.phase, steps])
			if not success:
				break
			_check(game.players.all(func(player): return player.cash >= 0 and player.crew >= 0 and player.crew <= 4), "Full game broke resource invariant")
			for id in game.CARGO_IDS:
				var quantity: int = game.stock[id]
				for player in game.players:
					quantity += player.holdings[id]
				_check(quantity == 5 and game.stock[id] >= 0, "Full game broke stock conservation")
			steps += 1
		_check(game.phase == "finished", "Full game exceeded 160-step/15-second bound: seed=%d" % seed_value)
