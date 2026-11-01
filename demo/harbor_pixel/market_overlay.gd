extends CanvasLayer

signal open_requested
signal closed

const Stage = preload("res://demo/harbor_pixel/market_stage_3d.gd")
const ICON = preload("res://demo/harbor_pixel/art/market_icon.png")
const FONT = preload("res://card/fonts/fusion-pixel-12px-proportional-zh_hans.otf")
const DialogSkin = preload("res://ui/harbor_dialog_skin.gd")
const BASE = Vector2(1448, 1086)

var is_open = false
var launcher: Button
var screen: Control
var close_button: Button
var stage: SubViewportContainer
var _prices: Dictionary = {}
var _previous_focus: WeakRef


func _ready() -> void:
	layer = 30
	launcher = Button.new()
	launcher.name = "MarketLauncher"
	launcher.icon = ICON
	launcher.expand_icon = true
	launcher.tooltip_text = "查看股票市值（M）"
	# The harbor owns its Tab/Enter cycle; M is the global keyboard entry.
	launcher.focus_mode = Control.FOCUS_NONE
	launcher.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	launcher.add_theme_constant_override("icon_max_width", 44)
	for state in ["normal", "hover", "pressed", "disabled"]:
		launcher.add_theme_stylebox_override(state, StyleBoxEmpty.new())
	launcher.pressed.connect(func(): open_requested.emit())
	add_child(launcher)
	screen = Control.new()
	screen.name = "MarketScreen"
	screen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	screen.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(screen)
	var dimmer = ColorRect.new()
	dimmer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dimmer.color = Color(0.02, 0.06, 0.08, 0.9)
	dimmer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	screen.add_child(dimmer)
	close_button = Button.new()
	close_button.text = "×"
	close_button.tooltip_text = "收起行情（Esc）"
	close_button.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	close_button.offset_left = -82
	close_button.offset_right = -22
	close_button.offset_top = 24
	close_button.offset_bottom = 84
	close_button.add_theme_font_override("font", FONT)
	close_button.add_theme_font_size_override("font_size", 32)
	DialogSkin.decorate_close(close_button)
	close_button.pressed.connect(close)
	screen.add_child(close_button)
	get_viewport().size_changed.connect(_layout)
	screen.hide()
	_layout()


func _layout() -> void:
	var extent := get_viewport().get_visible_rect().size
	var zoom := minf(extent.x / BASE.x, extent.y / BASE.y)
	var origin := (extent - BASE * zoom) * 0.5
	launcher.position = origin + Vector2(1204, 24) * zoom
	launcher.size = Vector2(54, 54) * zoom
	launcher.add_theme_constant_override("icon_max_width", maxi(16, roundi(44 * zoom)))
	if is_instance_valid(stage):
		stage.position = Vector2(16, 16)
		stage.size = Vector2(maxf(1, extent.x - 32), maxf(1, extent.y - 32))


func open(values: Dictionary) -> void:
	if is_open:
		sync_prices(values)
		return
	_previous_focus = weakref(get_viewport().gui_get_focus_owner())
	if not is_instance_valid(stage):
		stage = Stage.new()
		screen.add_child(stage)
		screen.move_child(stage, 1)
	is_open = true
	launcher.hide()
	sync_prices(values)
	screen.show()
	_layout()
	stage.set_active(true)
	close_button.grab_focus()


func sync_prices(values: Dictionary) -> void:
	_prices = values.duplicate()
	if is_instance_valid(stage):
		stage.sync_prices(_prices)


func close() -> void:
	if not is_open:
		return
	is_open = false
	screen.hide()
	launcher.show()
	stage.set_active(false)
	close_button.release_focus()
	if _previous_focus != null:
		var previous = _previous_focus.get_ref()
		if is_instance_valid(previous) and previous is Control and previous.is_visible_in_tree():
			previous.grab_focus()
	closed.emit()
