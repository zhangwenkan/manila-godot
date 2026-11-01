extends RefCounted
## Standalone, synchronous three-player demo rules. No UI, timers or scene dependencies.
## Demo concessions: auction bids use cash only (no loans); no poverty placements;
## pilots only advance one ship carrying their owner's pawn; pirates stay
## aboard until sail three and automatically send plundered ships to port. Ties in
## ranking keep player order. These choices are NOT the complete original rules.

signal changed

const CARGO_NAMES := {"ginseng": "人参", "nutmeg": "肉豆蔻", "silk": "丝绸", "jade": "玉石"}
const PAYOUTS := {"ginseng": 18, "nutmeg": 24, "silk": 30, "jade": 36}
const MARKET := [0, 5, 10, 20, 30]
const CARGO_IDS := ["ginseng", "nutmeg", "silk", "jade"]
const BERTH_PAYOUTS := [6, 8, 15]

var slots = preload("res://ui/placement_state.gd").new()
var players: Array = []
var positions: Array[int] = [2, 3, 4]
var prices: Dictionary = {}
var stock: Dictionary = {}
var cargo: Array = ["ginseng", "silk", "jade"]
var phase: String = "auction"
var current_player: int = 0
var harbormaster: int = -1
var previous_harbormaster: int = -1
var auction_bid: int = 0
var auction_leader: int = -1
var auction_passed: Array[bool] = [false, false, false]
var voyage: int = 1
var dispatch_round: int = 0
var sail_count: int = 0
var dice: Array[int] = [0, 0, 0]
var log_lines: Array[String] = []
var settlement_lines: Array[String] = []
var max_voyages: int = 3

var _rng := RandomNumberGenerator.new()
var _passed: Array[bool] = [false, false, false]
# Number of actors visited in this round, including passed/exhausted actors.
# Unlike current_player, this cursor never wraps and cannot omit player zero.
var _dispatch_visited: int = 0
var _bought_stock: bool = false
var _settled: bool = false
var _pilots_done: bool = false


func _init() -> void:
	reset()


func reset(seed: int = -1) -> void:
	if seed == -1:
		_rng.randomize()
	else:
		_rng.seed = seed
	players.clear()
	prices.clear()
	stock.clear()
	var deck: Array[String] = []
	for id in CARGO_IDS:
		prices[id] = 0
		stock[id] = 5
		for _copy in 5:
			deck.append(id)
	# Local seeded Fisher-Yates: dealing and dice never touch the global RNG.
	for i in range(deck.size() - 1, 0, -1):
		var other := _rng.randi_range(0, i)
		var card := deck[i]
		deck[i] = deck[other]
		deck[other] = card
	var names := ["你", "林船长", "陈掌柜"]
	var colors := [Color("e7b75a"), Color("6da9ba"), Color("ba7b89")]
	for actor in 3:
		var holdings := {"ginseng": 0, "nutmeg": 0, "silk": 0, "jade": 0}
		for _card in 2:
			var id: String = deck.pop_back()
			holdings[id] += 1
			stock[id] -= 1
		players.append({"name": names[actor], "cash": 30, "crew": 4,
			"holdings": holdings, "color": colors[actor]})
	voyage = 1
	harbormaster = -1
	previous_harbormaster = -1
	cargo = ["ginseng", "silk", "jade"]
	log_lines.clear()
	_reset_voyage()
	log_lines.append("演示规则：每航竞拍港务长；出价以现金为上限，不提供贷款与贫困派遣。")
	log_lines.append("引航简化：第三航前自动前推有己方船员且收益最有利的船；无目标则放弃。")
	log_lines.append("海盗简化：第二航不登船，留守至第三航；劫掠恰好 13 格的船并自动送港。")
	log_lines.append("第 1 航竞拍开始：由你先出价；全员弃权则按原顺序重新竞拍。")
	changed.emit()


func _reset_voyage() -> void:
	phase = "auction"
	harbormaster = -1
	current_player = previous_harbormaster if previous_harbormaster >= 0 else 0
	auction_bid = 0
	auction_leader = -1
	auction_passed.assign([false, false, false])
	dispatch_round = 0
	_dispatch_visited = 0
	sail_count = 0
	positions.assign([2, 3, 4])
	dice.assign([0, 0, 0])
	_passed.assign([false, false, false])
	_bought_stock = false
	_settled = false
	_pilots_done = false
	settlement_lines.clear()
	for player in players:
		player.crew = 4
	slots.set_voyage_cargo(cargo)


func bid(amount: Variant, actor: int = 0) -> bool:
	if typeof(amount) != TYPE_INT or not _can_bid(actor) or amount <= auction_bid or amount > players[actor].cash:
		return false
	auction_bid = amount
	auction_leader = actor
	log_lines.append("%s报价 %d 比索。" % [players[actor].name, amount])
	_advance_auction()
	changed.emit()
	return true


func pass_bid(actor: int = 0) -> bool:
	if not _can_bid(actor):
		return false
	auction_passed[actor] = true
	log_lines.append("%s退出本航竞拍。" % players[actor].name)
	_advance_auction()
	changed.emit()
	return true


func _can_bid(actor: int) -> bool:
	return phase == "auction" and actor >= 0 and actor < players.size() and actor == current_player and actor != auction_leader and not auction_passed[actor]


func _advance_auction() -> void:
	for offset in range(1, players.size() + 1):
		var actor := (current_player + offset) % players.size()
		if not auction_passed[actor] and actor != auction_leader:
			current_player = actor
			return
	if auction_leader >= 0:
		_award_auction(auction_leader)
	elif previous_harbormaster >= 0:
		_award_auction(previous_harbormaster)
	else:
		# No recursion: the caller schedules the next human or AI action.
		auction_passed.fill(false)
		current_player = 0
		log_lines.append("首航无人报价，按原顺序重新竞拍。")


func _award_auction(actor: int) -> void:
	harbormaster = actor
	previous_harbormaster = actor
	players[actor].cash -= auction_bid
	current_player = actor
	phase = "stock"
	log_lines.append("%s以 %d 比索担任本航港务局长。" % [players[actor].name, auction_bid])


func skip_stock(actor: int = 0) -> bool:
	if phase != "stock" or actor < 0 or actor != harbormaster:
		return false
	phase = "setup"
	log_lines.append("%s跳过买股，开始装货。" % players[actor].name)
	changed.emit()
	return true


func begin_voyage(cargo_ids: Array = [], starts: Array = [], actor: int = 0) -> bool:
	if phase != "setup" or actor < 0 or actor != harbormaster:
		return false
	var selected: Array = cargo if cargo_ids.is_empty() else cargo_ids
	var start_positions: Array = [2, 3, 4] if starts.is_empty() else starts
	if selected.size() != 3 or start_positions.size() != 3:
		return false
	var seen := {}
	for id in selected:
		if typeof(id) != TYPE_STRING or not CARGO_NAMES.has(id) or seen.has(id):
			return false
		seen[id] = true
	var total := 0
	for start in start_positions:
		if typeof(start) != TYPE_INT or start < 0 or start > 5:
			return false
		total += start
	if total != 9:
		return false
	# All validation precedes state changes, including cargo/slot rebuilding.
	cargo = selected.duplicate()
	positions.assign(start_positions)
	phase = "dispatch"
	current_player = harbormaster
	_dispatch_visited = 0
	dispatch_round = 1
	slots.set_voyage_cargo(cargo)
	log_lines.append("第 %d 航启航准备完成：%s / %s / %s，起点 %d / %d / %d。" % [
		voyage, CARGO_NAMES[cargo[0]], CARGO_NAMES[cargo[1]], CARGO_NAMES[cargo[2]],
		positions[0], positions[1], positions[2]])
	log_lines.append("派遣第 1 轮：每位玩家依次派出一人；首次投骰前共有两轮。")
	changed.emit()
	return true


func buy_stock(cargo_id: String, actor: int = 0) -> bool:
	if phase != "stock" or actor < 0 or actor != harbormaster or _bought_stock or not stock.has(cargo_id):
		return false
	var cost: int = maxi(5, prices[cargo_id])
	if stock[cargo_id] <= 0 or players[actor].cash < cost:
		return false
	players[actor].cash -= cost
	players[actor].holdings[cargo_id] += 1
	stock[cargo_id] -= 1
	_bought_stock = true
	phase = "setup"
	log_lines.append("%s以 %d 比索买入一张%s股票（本航限购一张）。" % [players[actor].name, cost, CARGO_NAMES[cargo_id]])
	changed.emit()
	return true


func _acting_reason(actor: int) -> String:
	if actor < 0 or actor >= players.size():
		return "无此玩家"
	if phase != "dispatch":
		return "当前不是派遣阶段"
	if _passed[actor]:
		return "本航程已放弃派遣"
	if actor != current_player:
		return "尚未轮到该玩家"
	if players[actor].crew <= 0:
		return "没有可用船员"
	return ""


func placement_reason(slot_id: String, actor: int = -1) -> String:
	var owner: int = current_player if actor == -1 else actor
	var reason := _acting_reason(owner)
	if not reason.is_empty():
		return reason
	reason = slots.unavailable_reason(slot_id)
	if not reason.is_empty():
		return reason
	var item: Dictionary = slots.get_position(slot_id)
	if players[owner].cash < item.cost:
		return "现金不足（演示版不提供贷款）"
	return ""


func place(slot_id: String, actor: int = -1) -> bool:
	var owner: int = current_player if actor == -1 else actor
	if not placement_reason(slot_id, owner).is_empty():
		return false
	var item: Dictionary = slots.get_position(slot_id)
	players[owner].cash -= item.cost
	players[owner].crew -= 1
	slots.owners[slot_id] = owner
	log_lines.append("%s派驻%s，支付 %d 比索。" % [players[owner].name, item.title, item.cost])
	if slot_id == "insurance_0":
		players[owner].cash += 10
		log_lines.append("%s承保立即领取 10 比索；结算承担所有受损泊位费用，包括空岗。" % players[owner].name)
	_dispatch_visited += 1
	_advance_dispatch()
	changed.emit()
	return true


func pass_turn(actor: int = -1) -> bool:
	var owner: int = current_player if actor == -1 else actor
	if not _acting_reason(owner).is_empty():
		return false
	_passed[owner] = true
	log_lines.append("%s放弃本航程余下全部派遣。" % players[owner].name)
	_dispatch_visited += 1
	_advance_dispatch()
	changed.emit()
	return true


func _advance_dispatch() -> void:
	# At most two opening rounds; passed/exhausted actors cannot stall the game.
	while phase == "dispatch":
		while _dispatch_visited < players.size():
			current_player = (harbormaster + _dispatch_visited) % players.size()
			if not _passed[current_player] and players[current_player].crew > 0:
				return
			_dispatch_visited += 1
		if dispatch_round == 1:
			dispatch_round = 2
			_dispatch_visited = 0
			log_lines.append("派遣第 2 轮：结束后进行第一次投骰。")
		else:
			phase = "sailing"
			current_player = harbormaster
			log_lines.append("派遣第 %d 轮结束，请进行第 %d 次航行。" % [dispatch_round, sail_count + 1])


func ai_step() -> bool:
	if current_player <= 0 or current_player >= players.size():
		return false
	var actor := current_player
	if phase == "auction":
		var budget: int = mini(players[actor].cash, 4 + voyage + actor)
		return bid(auction_bid + 1, actor) if auction_bid < budget else pass_bid(actor)
	if phase == "stock":
		var preferred := ""
		var best_value := -1
		for id in CARGO_IDS:
			var cost: int = maxi(5, prices[id])
			if stock[id] > 0 and players[actor].cash >= cost + 7:
				var value: int = players[actor].holdings[id] * 10 + PAYOUTS[id]
				if value > best_value:
					best_value = value
					preferred = id
		return skip_stock(actor) if preferred.is_empty() else buy_stock(preferred, actor)
	if phase == "setup":
		var goods: Array = CARGO_IDS.duplicate()
		goods.sort_custom(func(a: String, b: String) -> bool:
			var left: int = players[actor].holdings[a] * 100 + PAYOUTS[a]
			var right: int = players[actor].holdings[b] * 100 + PAYOUTS[b]
			return left > right)
		return begin_voyage(goods.slice(0, 3), [4, 3, 2], actor)
	if phase != "dispatch":
		return false
	var best_id := ""
	var best_score := 0.0
	for item in slots.positions:
		if not placement_reason(item.id, actor).is_empty():
			continue
		var score := _placement_score(item, actor)
		if score > best_score:
			best_score = score
			best_id = item.id
	# Exactly one action; the caller decides when to request the next AI action.
	return pass_turn(actor) if best_id.is_empty() else place(best_id, actor)


func _placement_score(item: Dictionary, actor: int) -> float:
	if item.ship >= 0:
		var count := _ship_owners(item.ship).size()
		var chance := clampf((float(positions[item.ship]) + (3 - sail_count) * 3.5 - 9.0) / 6.0, 0.05, 1.0)
		return float(PAYOUTS[cargo[item.ship]]) / (count + 1) * chance - item.cost
	match item.group:
		"insurance":
			return 4.0
		"harbor", "shipyard":
			var berth := int(item.id.get_slice("_", 1))
			return float(BERTH_PAYOUTS[berth]) * [0.75, 0.4, 0.12][berth] - item.cost
		"pilot":
			var distance := 1 if item.id == "pilot_0" else 2
			var target := _pilot_target(actor, distance)
			return _pilot_gain(actor, target, distance) - item.cost if target >= 0 else -1.0
		"pirate":
			return 0.5
	return -1.0


func roll(forced: Array = [], actor: int = 0) -> bool:
	if phase != "sailing" or actor < 0 or actor != harbormaster or sail_count >= 3 or _settled:
		return false
	if not forced.is_empty():
		if forced.size() != 3:
			return false
		for value in forced:
			if typeof(value) != TYPE_INT or value < 1 or value > 6:
				return false
	# Reject invalid dice before advancing RNG, pilots, counters, logs or ships.
	var result: Array[int] = []
	if forced.is_empty():
		for _ship in 3:
			result.append(_rng.randi_range(1, 6))
	else:
		result.assign(forced)
	if sail_count == 2:
		_apply_pilots()
	dice.assign(result)
	sail_count += 1
	log_lines.append("第 %d 次航行：骰子 %d / %d / %d。" % [sail_count, dice[0], dice[1], dice[2]])
	for ship in 3:
		if slots.arrived[ship]:
			continue
		positions[ship] = mini(14, positions[ship] + dice[ship])
		if positions[ship] > 13:
			slots.arrived[ship] = true
			log_lines.append("%s越过 13 格，到达港口。" % CARGO_NAMES[cargo[ship]])
	if sail_count == 3:
		_settle()
	else:
		if sail_count == 2 and not _pirate_owners().is_empty():
			log_lines.append("海盗简化：第二航不登船，继续留守等待第三航恰好 13 格的货船。")
		dispatch_round = sail_count + 2
		phase = "dispatch"
		current_player = harbormaster
		_dispatch_visited = 0
		log_lines.append("派遣第 %d 轮开始（已放弃或无船员的玩家自动略过）。" % dispatch_round)
		# If everyone has permanently passed, this empty round immediately ends.
		_advance_dispatch()
	changed.emit()
	return true


func _ship_owners(ship: int) -> Array[int]:
	var result: Array[int] = []
	for owner in slots.ship_occupants(ship):
		if owner != null:
			result.append(int(owner))
	return result


func _pirate_owners() -> Array[int]:
	var result: Array[int] = []
	for id in ["pirate_0", "pirate_1"]:
		if slots.owners.has(id):
			result.append(int(slots.owners[id]))
	return result


func _pilot_target(actor: int, distance: int) -> int:
	var best := -1
	var best_gain := -1.0
	var best_exposure := -1.0
	for ship in 3:
		var owners := _ship_owners(ship)
		if slots.arrived[ship] or not owners.has(actor):
			continue
		var gain := _pilot_gain(actor, ship, distance)
		var exposure := float(PAYOUTS[cargo[ship]]) * owners.count(actor) / owners.size()
		if gain > best_gain or (is_equal_approx(gain, best_gain) and exposure > best_exposure):
			best = ship
			best_gain = gain
			best_exposure = exposure
	return best


func _pilot_gain(actor: int, ship: int, distance: int) -> float:
	if ship < 0:
		return 0.0
	var owners := _ship_owners(ship)
	if owners.is_empty():
		return 0.0
	var share := float(PAYOUTS[cargo[ship]]) * owners.count(actor) / owners.size()
	var price_index: int = MARKET.find(prices[cargo[ship]])
	var rise: int = MARKET[mini(price_index + 1, MARKET.size() - 1)] - prices[cargo[ship]]
	var stock_gain: int = players[actor].holdings[cargo[ship]] * rise
	var has_pirates := not _pirate_owners().is_empty()
	var gain := 0.0
	# Expected incremental benefit before seeing the final die; never peek at forced dice.
	for value in range(1, 7):
		var before: int = positions[ship] + value
		var after: int = positions[ship] + distance + value
		var before_crew := before > 13 or (before == 13 and not has_pirates)
		var after_crew := after > 13 or (after == 13 and not has_pirates)
		gain += share * (int(after_crew) - int(before_crew))
		gain += stock_gain * (int(after >= 13) - int(before >= 13))
	return gain / 6.0


func _apply_pilots() -> void:
	if _pilots_done:
		return
	_pilots_done = true
	for index in 2:
		var id := "pilot_%d" % index
		if not slots.owners.has(id):
			continue
		var actor: int = slots.owners[id]
		var distance := index + 1
		var ship := _pilot_target(actor, distance)
		if ship < 0:
			log_lines.append("引航简化：%s没有未到港且有己方船员的船，自动放弃。" % players[actor].name)
			continue
		positions[ship] = mini(14, positions[ship] + distance)
		log_lines.append("引航简化：%s自动将收益最有利的%s前推 %d 格至 %d。" % [
			players[actor].name, CARGO_NAMES[cargo[ship]], distance, positions[ship]])
		if positions[ship] > 13:
			slots.arrived[ship] = true
			log_lines.append("%s由引航直接到港，本次不再移动。" % CARGO_NAMES[cargo[ship]])


func _settlement_log(line: String) -> void:
	settlement_lines.append(line)
	log_lines.append(line)


func _pay_pawns(owners: Array[int], total: int, source: String) -> void:
	if owners.is_empty():
		_settlement_log("%s：无船员领取分红。" % source)
		return
	var share: int = int(total / owners.size())
	var paid := {}
	for actor in owners:
		players[actor].cash += share
		paid[actor] = int(paid.get(actor, 0)) + share
	for actor in paid:
		_settlement_log("%s：%s的 %d 名小人领取 %d 比索（每人 %d）。" % [
			source, players[actor].name, owners.count(actor), paid[actor], share])


func _settle() -> void:
	if _settled:
		return
	_settled = true
	phase = "settlement"
	current_player = 0
	_settlement_log("第 %d 航结算" % voyage)
	var pirates := _pirate_owners()
	var arrived_count := 0
	for ship in 3:
		var label: String = CARGO_NAMES[cargo[ship]]
		var plundered: bool = not slots.arrived[ship] and positions[ship] == 13 and not pirates.is_empty()
		if not slots.arrived[ship] and positions[ship] == 13:
			slots.arrived[ship] = true
			if plundered:
				_settlement_log("海盗简化：%s恰好 13 格，被劫掠后自动送港；原船员无分红。" % label)
				_pay_pawns(pirates, PAYOUTS[cargo[ship]], "%s劫掠" % label)
				for item in slots.positions:
					if item.ship == ship and slots.owners.has(item.id):
						players[slots.owners[item.id]].crew += 1
						slots.owners.erase(item.id)
			else:
				_settlement_log("%s恰好 13 格且无海盗，正常到港。" % label)
		if slots.arrived[ship]:
			arrived_count += 1
			if not plundered:
				_pay_pawns(_ship_owners(ship), PAYOUTS[cargo[ship]], "%s到港" % label)
		else:
			_settlement_log("%s停在 %d 格，进入修船厂。" % [label, positions[ship]])
	var damaged_count := 3 - arrived_count
	_settlement_log("到港 %d 艘 / 受损 %d 艘；岸上泊位按船数依次启用。" % [arrived_count, damaged_count])
	# Credit every income first, then charge the insurer once. An occupied repair
	# berth's reward is the destination of this liability, not an extra expense.
	for group in ["harbor", "shipyard"]:
		var count: int = arrived_count if group == "harbor" else damaged_count
		for berth in count:
			var id := "%s_%d" % [group, berth]
			if slots.owners.has(id):
				var actor: int = slots.owners[id]
				players[actor].cash += BERTH_PAYOUTS[berth]
				_settlement_log("%s的%s领取 %d 比索。" % [
					players[actor].name, slots.get_position(id).title, BERTH_PAYOUTS[berth]])
	if slots.owners.has("insurance_0"):
		var insurer: int = slots.owners["insurance_0"]
		var liability := 0
		for berth in damaged_count:
			liability += BERTH_PAYOUTS[berth]
		var paid: int = mini(players[insurer].cash, liability)
		players[insurer].cash -= paid
		_settlement_log("%s保险责任 %d，实际支付 %d 比索（包括无人派驻的受损泊位；不再领取 10）。" % [
			players[insurer].name, liability, paid])
		if paid < liability:
			_settlement_log("演示版不抵押股票：保险现金不足，银行补足 %d 比索，不产生债务。" % (liability - paid))
	for ship in 3:
		if not slots.arrived[ship]:
			continue
		var id: String = cargo[ship]
		var index: int = MARKET.find(prices[id])
		var old_price: int = prices[id]
		prices[id] = MARKET[mini(index + 1, MARKET.size() - 1)]
		_settlement_log("%s行情 %d → %d。" % [CARGO_NAMES[id], old_price, prices[id]])
	if _game_over():
		_settlement_log("终局条件已达成：确认本航结算后查看最终排名。")


func _game_over() -> bool:
	return prices.values().has(30) or voyage >= max_voyages


func next_voyage() -> bool:
	if phase != "settlement" or not _settled:
		return false
	# Always expose the third roll's settlement first, even for the last voyage.
	if _game_over():
		phase = "finished"
		log_lines.append("演示结束：按现金加持股市值排名（同分并列，列表按玩家顺序）。")
	else:
		voyage += 1
		_reset_voyage()
		log_lines.append("第 %d 航竞拍：船员已收回，由上任局长先报价。" % voyage)
	changed.emit()
	return true


func wealth(actor: int) -> int:
	if actor < 0 or actor >= players.size():
		return 0
	var total: int = players[actor].cash
	for id in CARGO_IDS:
		total += int(players[actor].holdings[id]) * int(prices[id])
	return total


func ranking() -> Array[int]:
	var result: Array[int] = [0, 1, 2]
	result.sort_custom(func(a: int, b: int) -> bool:
		var left := wealth(a)
		var right := wealth(b)
		return a < b if left == right else left > right)
	return result
