extends RefCounted

const ART := "res://demo/tropical_harbor_3d/assets/coast/"
const LAYOUT = preload("res://demo/tropical_harbor_3d/environment/harbor_layout.gd")
const TERMINAL_LIFE = preload("res://demo/tropical_harbor_3d/environment/terminal_life.gd")
var root: Node3D
var landmarks: Array[Vector3] = []
var buildings: Array[Node3D] = []
var life: Node3D


func build(parent: Node3D) -> void:
    root = Node3D.new()
    root.name = "CoastalTown"
    parent.add_child(root)
    for spec in LAYOUT.COAST_BUILDINGS:
        var path: String = ART + spec.asset + ".glb"
        if not ResourceLoader.exists(path):
            continue
        var scene := load(path) as PackedScene
        var instance := scene.instantiate() as Node3D
        instance.name = spec.id
        instance.position = spec.at
        root.add_child(instance)
        buildings.append(instance)
        _materials(instance)
        for item in instance.find_children("*", "MeshInstance3D", true, false):
            var mesh := item as MeshInstance3D
            if mesh.mesh == null:
                continue
            var bounds: AABB = mesh.global_transform * mesh.mesh.get_aabb()
            for i in 8:
                landmarks.append(bounds.get_endpoint(i))
            # Small animated cloth, fire and machinery do not form camera walls.
            if mesh.name.begins_with("TerminalLive_"):
                continue
            var body := StaticBody3D.new()
            body.collision_layer = 4
            body.collision_mask = 0
            mesh.add_child(body)
            var collision := CollisionShape3D.new()
            collision.shape = mesh.mesh.create_trimesh_shape()
            body.add_child(collision)
        var label := Label3D.new()
        label.name = "AreaLabel"
        label.text = spec.label
        label.position = Vector3(-1.0, spec.height + 1.0, 0)
        label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
        label.font_size = 48
        label.pixel_size = 0.012
        label.outline_size = 9
        label.modulate = Color("fff0d0")
        label.outline_modulate = Color("23413a")
        instance.add_child(label)
        if spec.id == "ArrivalTerminal":
            life = TERMINAL_LIFE.new()
            life.name = "TerminalLife"
            instance.add_child(life)
            life.setup(instance)


func sync_life(t: float, audio_active: bool) -> void:
    if life != null:
        life.sync(t, audio_active)


func set_observing(value: bool) -> void:
    for building in buildings:
        building.get_node("AreaLabel").visible = not value


func _materials(instance: Node) -> void:
    var cache: Dictionary = {}
    for item in instance.find_children("*", "MeshInstance3D", true, false):
        var mesh := item as MeshInstance3D
        for i in mesh.mesh.get_surface_count():
            var source := mesh.get_active_material(i) as StandardMaterial3D
            if source == null:
                continue
            if not cache.has(source):
                var material := source.duplicate() as StandardMaterial3D
                material.metallic = 0
                material.metallic_specular = 0.2
                # New mineral surfaces keep distinct reflection responses;
                # their roughness textures already contain the absolute values.
                match source.resource_name:
                    "HarborCraft_WeatheredCanvas", "HarborCraft_CanvasHem":
                        # COLOR_0 stores pin weights and phase, never cloth tint.
                        material.vertex_color_use_as_albedo = false
                    "HarborCraft_Terminal_Slate":
                        material.metallic_specular = 0.36
                    "HarborCraft_WeatheredTimber":
                        material.metallic_specular = 0.16
                    "HarborCraft_WorkingTimber":
                        material.metallic_specular = 0.20
                    "HarborCraft_CraneForgedIron", "HarborCraft_AnchorWeatheredIron":
                        material.metallic = 0.45
                        material.metallic_specular = 0.32
                    "HarborCraft_LanternAgedBrass", "HarborCraft_LanternBurner":
                        material.metallic = 0.55
                        material.metallic_specular = 0.32
                    "HarborCraft_LanternSmokyGlass":
                        material.metallic_specular = 0.45
                    "HarborCraft_Terminal_Stone":
                        material.metallic_specular = 0.28
                    "HarborCraft_Terminal_Lime":
                        material.metallic_specular = 0.18
                material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
                # The craft asset carries its authored palette and complete UVs.
                # Legacy prototypes still need their temporary material correction.
                if material.albedo_texture != null and not source.resource_name.begins_with("HarborCraft_"):
                    var name_: String = source.resource_name.to_lower()
                    material.albedo_color = Color(1.16, 1.05, 0.91)
                    if "dark structural" in name_:
                        material.albedo_color = Color(0.82, 0.76, 0.65)
                    elif "pale joinery" in name_:
                        material.albedo_color = Color(1.75, 1.65, 1.42)
                    elif "siding" in name_:
                        material.albedo_color = Color(1.24, 0.94, 0.79)
                        material.albedo_color *= 0.91 + float(name_.right(1).to_int()) * 0.05
                    elif "roof redwood" in name_:
                        material.albedo_color = Color(1.22, 1.02, 0.87)
                        material.albedo_color *= 0.92 + float(name_.right(1).to_int()) * 0.045
                    elif "shingle" in name_:
                        material.albedo_color = Color(1.05, 0.95, 0.80)
                    material.roughness = 0.93
                cache[source] = material
            mesh.set_surface_override_material(i, cache[source])
