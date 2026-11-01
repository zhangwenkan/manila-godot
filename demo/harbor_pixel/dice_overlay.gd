extends CanvasLayer

signal results_ready(values: Array, request: int)
signal skip_requested(request: int)
signal failed(message: String, request: int)

const STAGE = preload("res://dice3d/dice_stage_3d.tscn")
const FONT = preload("res://card/fonts/fusion-pixel-12px-proportional-zh_hans.otf")
const DialogSkin = preload("res://ui/harbor_dialog_skin.gd")
const TIMEOUT_MS = 25000

var screen: Control
var stage: DiceStage3D
var close_button: Button
var caption: Label
var state = "closed"
var request_id = 0
var _started_ms = 0
var _settled_callback: Callable


func _ready() -> void:
	layer = 20
	screen = Control.new()
	screen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	screen.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(screen)
	var dimmer = ColorRect.new()
	dimmer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dimmer.color = Color(0.02, 0.06, 0.08, 0.78)
	dimmer.mouse_filter = Control.MOUSE_FILTER_STOP
	screen.add_child(dimmer)
	caption = Label.new()
	caption.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	caption.offset_top = 26
	caption.offset_bottom = 80
	caption.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	caption.add_theme_font_override("font", FONT)
	caption.add_theme_font_size_override("font_size", 26)
	caption.add_theme_color_override("font_color", Color("f0dfba"))
	caption.mouse_filter = Control.MOUSE_FILTER_IGNORE
	screen.add_child(caption)
	close_button = Button.new()
	close_button.text = "×"
	close_button.tooltip_text = "收起骰盘并继续航行"
	close_button.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	close_button.offset_left = -82
	close_button.offset_right = -22
	close_button.offset_top = 24
	close_button.offset_bottom = 84
	close_button.add_theme_font_override("font", FONT)
	close_button.add_theme_font_size_override("font_size", 32)
	DialogSkin.decorate_close(close_button)
	close_button.pressed.connect(func():
		if state == "result":
			skip_requested.emit(request_id)
	)
	screen.add_child(close_button)
	screen.resized.connect(func():
		if state == "rolling":
			_abort("窗口尺寸改变，本次未结算，请重新投掷。")
	)
	screen.hide()


func open(cargo: Array, labels: Array, request: int, forced: Array = []) -> bool:
	if state != "closed" or cargo.size() != 3 or (not forced.is_empty() and not valid_values(forced)):
		return false
	request_id = request
	state = "rolling"
	_started_ms = Time.get_ticks_msec()
	close_button.disabled = true
	caption.text = "掷骰航行 · 等待骰子落定"
	screen.show()
	if not is_instance_valid(stage):
		stage = STAGE.instantiate()
		screen.add_child(stage)
		screen.move_child(stage, 1)
	stage.process_mode = Node.PROCESS_MODE_INHERIT
	stage._viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	stage.show()
	stage.configure_cargo(cargo, labels)
	_settled_callback = _on_settled.bind(request)
	stage.all_settled.connect(_settled_callback)
	if forced.is_empty():
		stage.throw_all()
	else:
		# Explicit deterministic fixture/replay path, never a fake physical throw.
		for i in 3:
			stage.set_value(i, forced[i])
		_on_settled(forced.duplicate(), request)
	return true


static func valid_values(values: Array) -> bool:
	if values.size() != 3:
		return false
	for value in values:
		if typeof(value) != TYPE_INT or value < 1 or value > 6:
			return false
	return true


func _on_settled(values: Array, request: int) -> void:
	if request != request_id or state != "rolling":
		return
	if not valid_values(values):
		_abort("骰子结果无效，请重新投掷。")
		return
	state = "result"
	close_button.disabled = false
	caption.text = "骰子已落定 · 即将启航"
	results_ready.emit(values.duplicate(), request)


func _process(_delta: float) -> void:
	if state == "rolling" and Time.get_ticks_msec() - _started_ms >= TIMEOUT_MS:
		_abort("骰子未能及时落定，本次未结算，请重新投掷。")


func _abort(message: String) -> void:
	var request = request_id
	close(request)
	failed.emit(message, request)


func close(request: int) -> void:
	if request != request_id:
		return
	var discard = state == "rolling"
	state = "closed"
	screen.hide()
	close_button.release_focus()
	if is_instance_valid(stage):
		if stage.all_settled.is_connected(_settled_callback):
			stage.all_settled.disconnect(_settled_callback)
		if discard:
			# An unfinished request must never leak its physics or callback into retry.
			screen.remove_child(stage)
			stage.queue_free()
			stage = null
		else:
			# Keep settled meshes/shaders warm; repeatedly rebuilding these can
			# stall the mobile renderer. Disable both simulation and rendering.
			for die: Dice3D in stage._dice:
				die.freeze = true
				die.linear_velocity = Vector3.ZERO
				die.angular_velocity = Vector3.ZERO
			stage.process_mode = Node.PROCESS_MODE_DISABLED
			stage._viewport.render_target_update_mode = SubViewport.UPDATE_DISABLED
			stage.hide()
