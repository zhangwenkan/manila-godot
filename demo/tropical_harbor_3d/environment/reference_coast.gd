extends RefCounted

const ART := "res://demo/tropical_harbor_3d/assets/reference/"
var root: Node3D
var landmarks: Array[Vector3] = []
var buildings: Array[Node3D] = []

func build(parent: Node3D) -> void:
    root = Node3D.new()
    root.name = "ReferenceCoast"
    parent.add_child(root)
    for filename in ["coast", "foliage", "rocks"]:
        var instance := (load(ART + filename + ".glb") as PackedScene).instantiate() as Node3D
        root.add_child(instance)
        buildings.append(instance)
        for item in instance.find_children("*", "MeshInstance3D", true, false):
            var mesh := item as MeshInstance3D
            for i in mesh.mesh.get_surface_count():
                var material := mesh.get_active_material(i) as StandardMaterial3D
                if material != null:
                    material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
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
