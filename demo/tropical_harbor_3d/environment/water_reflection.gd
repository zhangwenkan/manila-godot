extends Node

const CLIP = preload("res://demo/tropical_harbor_3d/materials/fleet_reflect_clip.gdshader")
const LAYER_BIT := 4

var viewport: SubViewport
var camera: Camera3D
var main: Camera3D
var clip_shader: Shader
var enabled := false


func setup(root: Node3D, main_camera: Camera3D) -> void:
    main = main_camera
    main.cull_mask = main.cull_mask & ~(1 << LAYER_BIT)
    clip_shader = CLIP
    viewport = SubViewport.new()
    viewport.name = "WaterReflection"
    viewport.size = Vector2i(512, 288)
    viewport.transparent_bg = true
    viewport.own_world_3d = false
    viewport.world_3d = root.get_world_3d()
    viewport.render_target_update_mode = SubViewport.UPDATE_DISABLED
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
    # A separate sky resource is required: sharing its radiance cache between
    # the main ACES view and the linear reflection view makes lighting alternate.
    var environment := root.get_world_3d().environment.duplicate(true) as Environment
    environment.background_mode = Environment.BG_CLEAR_COLOR
    environment.ssao_enabled = false
    environment.glow_enabled = false
    environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
    camera.environment = environment
    viewport.add_child(camera)


func add_subject(node: Node) -> void:
    # The proxies own these materials. Keeping the cache local lets completed
    # voyages release their ships and textures when the scene rebuilds them.
    var materials: Dictionary = {}
    for item in node.find_children("*", "MeshInstance3D", true, false):
        var mesh := item as MeshInstance3D
        if mesh.mesh == null or mesh.layers == 1 << LAYER_BIT:
            continue
        var label := str(mesh.name).to_lower()
        if "fiber" in label:
            continue
        # These authored meshes stay above the water; reuse their live shader so
        # wind and flame do not become white, motionless shapes in reflections.
        if label.begins_with("terminallive_flags_") or label.begins_with("terminallive_flame"):
            mesh.layers |= 1 << LAYER_BIT
            continue
        var proxy := MeshInstance3D.new()
        proxy.name = "ReflectProxy"
        proxy.mesh = mesh.mesh
        proxy.layers = 1 << LAYER_BIT
        proxy.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        for surface in mesh.mesh.get_surface_count():
            var source := mesh.get_active_material(surface)
            if not materials.has(source):
                var material := ShaderMaterial.new()
                material.shader = clip_shader
                if source is StandardMaterial3D:
                    var standard := source as StandardMaterial3D
                    material.set_shader_parameter("albedo_tint", standard.albedo_color)
                    material.set_shader_parameter("use_vertex_color", standard.vertex_color_use_as_albedo)
                    if standard.albedo_texture != null:
                        material.set_shader_parameter("albedo_texture", standard.albedo_texture)
                        material.set_shader_parameter("use_albedo_texture", true)
                materials[source] = material
            proxy.set_surface_override_material(surface, materials[source])
        mesh.add_child(proxy)


func texture() -> ViewportTexture:
    return viewport.get_texture()


func set_enabled(value: bool) -> void:
    enabled = value
    viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS if value else SubViewport.UPDATE_DISABLED


func sync() -> void:
    if not enabled:
        return
    # Preserve screen-space alignment for both reference perspective views and
    # the orthographic gameplay camera, including window aspect changes.
    var size := main.get_viewport().get_visible_rect().size
    # Resizing/minimizing an embedded game can briefly report a tiny width.
    # Bound both axes instead of letting a fixed width create a huge texture.
    if size.x < 64.0 or size.y < 64.0:
        viewport.render_target_update_mode = SubViewport.UPDATE_DISABLED
        return
    viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
    var scale := 512.0 / maxf(size.x, size.y)
    var target_size := Vector2i(maxi(1, roundi(size.x * scale)), maxi(1, roundi(size.y * scale)))
    if viewport.size != target_size:
        viewport.size = target_size
    camera.projection = main.projection
    camera.keep_aspect = main.keep_aspect
    camera.fov = main.fov
    camera.size = main.size
    camera.near = main.near
    camera.far = main.far
    var src := main.global_transform
    var origin := src.origin
    origin.y = -origin.y
    var basis := src.basis
    var right := Vector3(basis.x.x, -basis.x.y, basis.x.z) * -1.0
    var up := Vector3(basis.y.x, -basis.y.y, basis.y.z)
    var forward := Vector3(basis.z.x, -basis.z.y, basis.z.z)
    camera.global_transform = Transform3D(Basis(right, up, forward).orthonormalized(), origin)
