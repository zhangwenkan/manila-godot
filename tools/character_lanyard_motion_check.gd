extends SceneTree
## Deterministic containment checks during held drags and every release step.

const Motion = preload("res://character_preview/lanyard_motion.gd")
const Card = preload("res://character_preview/carmen_collectible_card.gd")

var _failures: Array[String] = []
var _peak := 0.0
var _foreground := false


func _initialize() -> void:
	_foreground = "--foreground" in OS.get_cmdline_user_args()
	for dimensions: Vector2 in [Vector2(433, 514), Vector2(693, 822), Vector2(520, 551), Vector2(211, 452), Vector2(211, 328)]:
		var narrow := dimensions.x < 300
		var view_height := maxf(5.20, (3.0 if narrow else 3.65) / dimensions.aspect())
		var safe := Rect2(Vector2(-view_height * dimensions.aspect(), -view_height) * 0.5, Vector2(view_height * dimensions.aspect(), view_height)).grow(-0.035)
		for target: Vector2 in [Vector2(-30, 30), Vector2(30, 30), Vector2(-30, -30), Vector2(30, -30), Vector2.ZERO]:
			var motion := Motion.new()
			motion.configure(safe, narrow)
			motion.anchor.y = minf(motion.anchor.y, 2.52)
			motion.reset()
			if _foreground:
				var pixel_scale := dimensions.y / view_height
				var art_width := 2.4 * cos(Card.REST_YAW) * pixel_scale
				motion.protect_right_edge(1.2 * cos(Card.REST_YAW) + 0.089 * sin(Card.REST_YAW) + (maxf(2.0, art_width * 0.01) - 1.0) / pixel_scale)
			motion.begin(Vector2(0.75, 0.6), motion.center + Vector2(0.75, 0.6))
			motion.target = target
			for step in 1860:
				if step == 360:
					motion.release()
				motion.advance(Motion.STEP)
				var phase := "held" if step < 360 else "release"
				var key := "%s %s %s" % [dimensions, target, phase]
				_peak = maxf(_peak, motion.max_link_error())
				_check(motion.max_link_error() < 0.04 and motion.center.is_finite(), "Constraint " + key)
				var pose := Basis(Vector3.BACK, motion.angle) * Basis(Vector3.UP, Card.REST_YAW + motion.yaw)
				for corner: Vector3 in [Vector3(-1.2, -1.8, 0.089), Vector3(1.2, -1.8, 0.089), Vector3(1.2, 1.8, 0.089), Vector3(-1.2, 1.8, 0.089)]:
					_check(motion.center.x + (pose * corner).x <= motion.artwork_right_limit + 0.005, "Entire artwork clear of foreground " + key)
				for i in 8:
					var corner := pose * Card.BODY_BOUNDS.get_endpoint(i)
					_check(safe.grow(0.005).has_point(motion.center + Vector2(corner.x, corner.y)), "Projection " + key)
			_check(motion.sleeping, "Settle %s %s" % [dimensions, target])
	print("LANYARD_MOTION_", "PASS" if _failures.is_empty() else "FAIL", " cases=25 steps=46500 peak_stretch=", _peak, " failures=", _failures)
	quit(0 if _failures.is_empty() else 1)


func _check(condition: bool, description: String) -> void:
	if not condition and not _failures.has(description):
		_failures.append(description)
