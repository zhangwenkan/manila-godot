@tool
extends ColorRect
## Procedural pixel sea. The shader's layout texture contains only coastline data.
## Palette, depth, pixel size and wave density are editable under Material.

@export var animation_enabled := true
@export var animate_in_editor := false
@export_range(0.0, 4.0, 0.05) var playback_speed := 1.0

var _elapsed := 0.0


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	seek(0.0)


func _process(delta: float) -> void:
	if not animation_enabled or (Engine.is_editor_hint() and not animate_in_editor):
		return
	seek(_elapsed + delta * playback_speed)


## Set a deterministic frame for previewing or capturing the water.
func seek(seconds: float) -> void:
	_elapsed = maxf(seconds, 0.0)
	if material is ShaderMaterial:
		(material as ShaderMaterial).set_shader_parameter("ocean_time", _elapsed)
