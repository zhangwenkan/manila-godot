@tool
extends Control

signal changed

const Pixel := preload("res://card/pixel_card_theme.gd")
const PersonalBar := preload("res://ui/personal_bar.gd")
const CharacterCard := preload("res://card/character_card.gd")
const DESIGN_SIZE := Vector2(560, 32)
const PHASE_NAMES := ["竞拍港务长", "派遣", "投骰航行", "海盗登船", "引航调整", "航程结算"]
enum Phase { AUCTION, DISPATCH, SAILING, PIRATES, PILOTS, SETTLEMENT }

var players: Array[CharacterCard] = []
var current_player_index := 0
var harbor_master_index := 2
var voyage_number := 1
var deployment_round := 1
var sailing_number := 0
var phase: Phase = Phase.DISPATCH
var _stage_title: Label
var _master_hint: Label
var _master_width := 0.0


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_stage_title = Pixel.label(self, "", Rect2(8, 0, 136, 28), 22, PersonalBar.TEXT)
	_stage_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_master_hint = Pixel.label(self, "", Rect2(172, 0, 380, 28), 20, PersonalBar.TEXT)
	resized.connect(_refresh)
	_refresh()


func set_players(cards: Array[CharacterCard]) -> void:
	players.assign(cards)
	current_player_index = mini(current_player_index, players.size() - 1)
	harbor_master_index = mini(harbor_master_index, players.size() - 1)
	_refresh()
	changed.emit()


func set_current_player(index: int) -> void:
	current_player_index = index
	_refresh()
	changed.emit()


func set_harbor_master(index: int) -> void:
	harbor_master_index = index
	_refresh()
	changed.emit()


func set_stage(new_phase: Phase, voyage: int, deployment: int, sailing: int) -> void:
	phase = new_phase
	voyage_number = voyage
	deployment_round = deployment
	sailing_number = sailing
	_refresh()
	changed.emit()


func _refresh() -> void:
	if not is_instance_valid(_stage_title):
		return
	_stage_title.text = PHASE_NAMES[phase]
	if phase == Phase.DISPATCH:
		_stage_title.text = "派遣 %d/%d" % [deployment_round, 4 if players.size() == 3 else 3]
	elif phase == Phase.SAILING:
		_stage_title.text = "航行 %d/3" % sailing_number
	_master_hint.visible = not players.is_empty() and current_player_index != harbor_master_index
	if _master_hint.visible:
		var distance := (harbor_master_index - current_player_index + players.size()) % players.size()
		var relation := "下家" if distance == 1 else "后 %d 位" % distance
		_master_hint.text = "港务长：%s · %s" % [players[harbor_master_index].character_name, relation]
		_master_hint.size.x = maxf(1, size.x - _master_hint.position.x - 8)
		var font_size := 20
		while Pixel.FONT.get_string_size(_master_hint.text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x > _master_hint.size.x and font_size > 12:
			font_size -= 2
		_master_hint.add_theme_font_size_override("font_size", font_size)
		_master_width = minf(size.x - 164, Pixel.FONT.get_string_size(_master_hint.text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x + 16)
	queue_redraw()


func _draw() -> void:
	if not is_instance_valid(_stage_title):
		return
	_plaque(Rect2(0, 0, 152, 28))
	if _master_hint.visible:
		_plaque(Rect2(164, 0, _master_width, 28))


func _plaque(rect: Rect2) -> void:
	Pixel.step_rect(self, Rect2(rect.position + Vector2(0, 2), rect.size), 4, PersonalBar.SHADOW)
	Pixel.step_rect(self, rect, 4, PersonalBar.WOOD_DARK)
	Pixel.step_rect(self, rect.grow(-2), 2, PersonalBar.PAPER)
