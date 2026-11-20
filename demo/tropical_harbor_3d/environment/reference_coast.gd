extends RefCounted

const ART := "res://demo/tropical_harbor_3d/assets/reference/"
const TOWN_PATH = preload("res://demo/tropical_harbor_3d/materials/town_path.gdshader")
const GROUND_NOISE = preload("res://demo/tropical_harbor_3d/assets/water_noise.png")
var root: Node3D
var landmarks: Array[Vector3] = []
var buildings: Array[Node3D] = []

func build(parent: Node3D) -> void:
    root = Node3D.new()
    root.name = "ReferenceCoast"
    parent.add_child(root)
    for filename in ["coast", "town", "cargo_port", "foliage", "rocks"]:
        var instance := (load(ART + filename + ".glb") as PackedScene).instantiate() as Node3D
        instance.set_meta("reference_asset", filename)
        root.add_child(instance)
        buildings.append(instance)
        for item in instance.find_children("*", "MeshInstance3D", true, false):
            var mesh := item as MeshInstance3D
            var is_ground_overlay := false
            for i in mesh.mesh.get_surface_count():
                var material := mesh.get_active_material(i) as StandardMaterial3D
                if material != null:
                    material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
                    if material.resource_name == "Ref_Town_Path":
                        var path_material := ShaderMaterial.new()
                        path_material.shader = TOWN_PATH
                        path_material.set_shader_parameter("detail_noise", GROUND_NOISE)
                        mesh.set_surface_override_material(i, path_material)
                        is_ground_overlay = true
            if is_ground_overlay:
                mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
                continue
            if str(mesh.name).begins_with("Leaf"):
                continue
            var body := StaticBody3D.new()
            body.collision_layer = 4
            body.collision_mask = 0
            mesh.add_child(body)
            var shape := CollisionShape3D.new()
            shape.shape = mesh.mesh.create_trimesh_shape()
            body.add_child(shape)

func sync_life(_t: float, _audio_active: bool) -> void:
    pass

func set_observing(_value: bool) -> void:
    pass
