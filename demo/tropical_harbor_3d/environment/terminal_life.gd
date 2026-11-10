extends Node3D

const CLOTH = preload("res://demo/tropical_harbor_3d/materials/harbor_cloth.gdshader")
const FLAME = preload("res://demo/tropical_harbor_3d/materials/harbor_flame.gdshader")
const FALL_LENGTH := 2.56
const DRUM_RADIUS := 0.164
const CYCLE := 12.0
var rigs: Dictionary = {}
var bases: Dictionary = {}
var cloth_surfaces: Array[Dictionary] = []
var cloth_materials: Array[ShaderMaterial] = []
var flame_material: ShaderMaterial
var lights: Array[OmniLight3D] = []
var flames: Array[Node3D] = []
var mode := "live"
var last_time := -1000.0
var time_override := -1.0
var height := 0.0
var velocity := 0.0
var sound: AudioStreamPlayer3D
var last_sound_slot := -1


func setup(terminal: Node3D) -> void:
    for key in ["Load", "Fall", "Drum", "HeadWheel", "LeadWheel", "Flags", "FlameWest", "FlameEast", "FlameGalleryL", "FlameGalleryR"]:
        var rig := terminal.find_child("TerminalRig_" + key, true, false) as Node3D
        assert(rig != null, "Terminal live asset is missing " + key)
        rigs[key] = rig
        bases[key] = rig.transform
    var materials: Dictionary = {}
    for node in rigs.Flags.find_children("*", "MeshInstance3D", true, false):
        var mesh := node as MeshInstance3D
        mesh.extra_cull_margin = 0.45
        for i in mesh.mesh.get_surface_count():
            var original := mesh.get_active_material(i) as StandardMaterial3D
            var key := original.resource_name
            if not materials.has(key):
                var material := ShaderMaterial.new()
                material.shader = CLOTH
                material.set_shader_parameter("textured", original.albedo_texture != null)
                material.set_shader_parameter("plain_color", original.albedo_color)
                if original.albedo_texture != null:
                    material.set_shader_parameter("cloth_albedo", original.albedo_texture)
                    material.set_shader_parameter("cloth_normal", original.normal_texture)
                    material.set_shader_parameter("cloth_roughness", original.roughness_texture)
                materials[key] = material
                cloth_materials.append(material)
            cloth_surfaces.append({"mesh": mesh, "surface": i, "static": original, "live": materials[key]})
            mesh.set_surface_override_material(i, materials[key])
    flame_material = ShaderMaterial.new()
    flame_material.shader = FLAME
    for i in 4:
        var rig: Node3D = rigs[["FlameWest", "FlameEast", "FlameGalleryL", "FlameGalleryR"][i]]
        flames.append(rig)
        for node in rig.find_children("*", "MeshInstance3D", true, false):
            var mesh := node as MeshInstance3D
            mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
            mesh.extra_cull_margin = 0.03
            mesh.material_override = flame_material
            mesh.set_instance_shader_parameter("flame_phase", i * 1.71)
        var light := OmniLight3D.new()
        light.name = "LampWarmth"
        light.light_color = Color(1.0, 0.72, 0.40)
        light.light_energy = 0.10
        light.omni_range = 0.85
        light.omni_attenuation = 1.8
        light.shadow_enabled = false
        rig.add_child(light)
        light.position = Vector3(0, 0.035, 0)
        lights.append(light)
    sound = AudioStreamPlayer3D.new()
    sound.name = "WinchWoodCreak"
    var sound_path := "res://demo/tropical_harbor_3d/assets/coast/winch_creak.wav"
    if ResourceLoader.exists(sound_path):
        sound.stream = load(sound_path)
    sound.volume_db = -25.0
    sound.max_distance = 19.0
    sound.unit_size = 2.0
    sound.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_DISTANCE
    rigs.Drum.add_child(sound)
    set_mode("static" if "--terminal-still" in OS.get_cmdline_user_args() else "live")


func set_mode(value: String) -> void:
    assert(value in ["static", "frozen", "live"])
    mode = value
    last_time = -1000.0
    for item in cloth_surfaces:
        item.mesh.set_surface_override_material(item.surface, item.static if mode == "static" else item.live)
    for flame in flames:
        flame.visible = mode != "static"
    if sound != null:
        sound.stop()


static func lift_at(t: float) -> float:
    # Slow lift, hold, controlled lowering, hold. Zero speed at every transition.
    var phase := fposmod(t, CYCLE)
    if phase < 4.0:
        return 0.24 * smoothstep(0.0, 4.0, phase)
    if phase < 5.5:
        return 0.24
    if phase < 9.5:
        return 0.24 * (1.0 - smoothstep(5.5, 9.5, phase))
    return 0.0


func sync(t: float, audio_active: bool) -> void:
    if not audio_active and sound != null and sound.playing:
        sound.stop()
    var live_clock := time_override if time_override >= 0.0 else t
    var sample := live_clock if mode == "live" else 1.7
    if is_equal_approx(sample, last_time):
        return
    height = lift_at(sample) if mode != "static" else 0.0
    velocity = (lift_at(sample + .01) - lift_at(sample - .01)) / .02 if mode == "live" else 0.0
    rigs.Load.transform = bases.Load
    rigs.Load.position.y += height
    rigs.Fall.transform = bases.Fall
    rigs.Fall.scale.y = (FALL_LENGTH - height) / FALL_LENGTH
    for key in ["Drum", "HeadWheel", "LeadWheel"]:
        rigs[key].transform = bases[key]
        # Blender +Y axle is Godot -Z after GLTF conversion.
        var radius := DRUM_RADIUS if key == "Drum" else (0.15 if key == "HeadWheel" else 0.12)
        rigs[key].rotate_object_local(Vector3.FORWARD, -height / radius)
    for material in cloth_materials:
        material.set_shader_parameter("live_time", sample)
    flame_material.set_shader_parameter("live_time", sample)
    for i in lights.size():
        lights[i].light_energy = .10 * (1.0 + .13 * sin(sample * 9.3 + i * 1.71) + .055 * sin(sample * 15.7 + i * 3.42))
    var slot := int(floor(sample / 6.0))
    if audio_active and mode == "live" and absf(velocity) > .025 and slot != last_sound_slot and sound.stream != null:
        sound.pitch_scale = 0.94 + 0.07 * sin(slot * 2.3)
        sound.play()
        last_sound_slot = slot
    last_time = sample


func snapshot() -> Dictionary:
    return {"mode": mode, "time": last_time, "load_height": height, "load_position": rigs.Load.position,
        "fall_scale": rigs.Fall.scale.y, "drum_rotation": rigs.Drum.rotation,
        "lamp_energy": lights[0].light_energy, "lights": lights.size(), "shadow_lights": 0}
