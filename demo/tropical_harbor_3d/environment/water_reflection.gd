extends Node

const CLIP = preload("res://materials/fleet_reflect_clip.gdshader")
const LAYER_BIT := 4

var viewport: SubViewport
var camera: Camera3D
var main: Camera3D
var clip_shader: Shader


func setup(root: Node3D, main_camera: Camera3D) -> void:
    main = main_camera
    main.cull_mask = main.cull_mask & ~(1 << LAYER_BIT)
    clip_shader = CLIP
    viewport = SubViewport.new()
    viewport.name = "WaterReflection"
    viewport.size = Vector2i(640, 360)
    viewport.transparent_bg = true
    viewport.own_world_3d = false
    viewport.world_3d = root.get_world_3d()
    viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
    viewport.msaa_3d = Viewport.MSAA_2X
    viewport.handle_input_locally = false
    viewport.gui_disable_input = true
    viewport.positional_shadow_atlas_size = 0
    add_child(viewport)
    camera = Camera3D.new()
    camera.name = "ReflectionCamera"
    camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    camera.keep_aspect = Camera3D.KEEP_HEIGHT
    camera.cull_mask = 1 << LAYER_BIT
    camera.near = 0.05
    camera.far = 250.0
    camera.current = true
    viewport.add_child(camera)


func add_subject(node: Node) -> void:
    for item in node.find_children("*", "MeshInstance3D", true, false):
        var mesh := item as MeshInstance3D
        if mesh.layers == 1 << LAYER_BIT:
            continue
        var label := str(mesh.name).to_lower()
        if "fiber" in label:
            continue
        var proxy := MeshInstance3D.new()
        proxy.name = "ReflectProxy"
        proxy.mesh = mesh.mesh
        proxy.layers = 1 << LAYER_BIT
        proxy.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        var material := ShaderMaterial.new()
        material.shader = clip_shader
        material.set_shader_parameter("albedo_tint", _tint(mesh))
        proxy.material_override = material
        mesh.add_child(proxy)


func texture() -> ViewportTexture:
    return viewport.get_texture()


func set_enabled(value: bool) -> void:
    viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS if value else SubViewport.UPDATE_DISABLED


func sync() -> void:
    if viewport.render_target_update_mode == SubViewport.UPDATE_DISABLED:
        return
    camera.size = main.size
    camera.far = main.far
    var src := main.global_transform
    var origin := src.origin
    origin.y = -origin.y
    var basis := src.basis
    var right := Vector3(basis.x.x, -basis.x.y, basis.x.z) * -1.0
    var up := Vector3(basis.y.x, -basis.y.y, basis.y.z)
    var forward := Vector3(basis.z.x, -basis.z.y, basis.z.z)
    camera.global_transform = Transform3D(Basis(right, up, forward).orthonormalized(), origin)


func _tint(mesh: MeshInstance3D) -> Color:
    var material := mesh.material_override
    if material == null:
        material = mesh.get_active_material(0)
    if material is StandardMaterial3D:
        return (material as StandardMaterial3D).albedo_color
    return Color.WHITE
