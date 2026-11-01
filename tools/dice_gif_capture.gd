extends SceneTree
## Drive the in-game dice roll and let Godot's Movie Maker record it.
## Run: godot --path . --write-movie .godot/dice_gif/movie.png --fixed-fps 30 \
##            --script res://tools/dice_gif_capture.gd
## Prints the recorded frame range so the encoder can trim the setup frames.

const DEMO := preload("res://demo/harbor_pixel/harbor_demo.tscn")
const MAX_FRAMES := 900


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	Engine.max_fps = 0
	root.content_scale_size = Vector2i(1448, 1086)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT

	var demo := DEMO.instantiate()
	root.add_child(demo)
	await process_frame
	await process_frame
	await process_frame
	print("DEMO_READY phase=%s" % demo.game.phase)

	# Jump straight to the sailing phase so the dice overlay can be thrown.
	demo.game.phase = "sailing"
	demo.game.harbormaster = 0
	demo.game.current_player = 0
	demo.game.sail_count = 0
	demo.game._settled = false
	demo.busy = false
	demo.queue_redraw()
	await process_frame
	await process_frame

	seed(429)
	var throw_frame: int = Engine.get_process_frames()
	var started: bool = demo.start_roll()
	print("START_ROLL=%s overlay_state=%s throw_frame=%d" % [started, demo.dice_overlay.state, throw_frame])
	if not started:
		push_error("DICE_GIF_CAPTURE: start_roll refused")
		quit(2)
		return

	var settled_frame := -1
	for i in MAX_FRAMES:
		await process_frame
		if settled_frame < 0 and demo.dice_overlay.state == "result":
			settled_frame = Engine.get_process_frames()
		elif settled_frame >= 0:
			# Stop before the overlay closes, so the clip ends on the settled tray.
			if demo.dice_overlay.state != "result" or Engine.get_process_frames() - settled_frame > 12:
				break
	print("DICE_GIF_CAPTURE throw_frame=%d settled_frame=%d end_frame=%d values=%s" % [
		throw_frame, settled_frame, Engine.get_process_frames(), str(demo.game.dice)])
	quit(0)
