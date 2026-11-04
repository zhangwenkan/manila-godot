extends RefCounted

# Geometry and materials are authored in Blender MCP, not generated here.
const WORKING = preload("res://assets/pier_working_mcp.glb")
const BROKEN = preload("res://assets/pier_broken_mcp.glb")
const WETNESS = preload("res://materials/fleet_hull_wet.gdshader")
var contacts := PackedVector4Array()


func build(parent: Node3D, environment: RefCounted) -> void:
    contacts.clear()
    var root := Node3D.new()
    root.name = "TimberPiers"
    parent.add_child(root)
    for i in 2:
        var scene: PackedScene = WORKING if i == 0 else BROKEN
        var pier := scene.instantiate() as Node3D
        pier.name = "WorkingPier" if i == 0 else "BrokenPier"
        pier.position = Vector3(7.01, 0, 7.3 if i == 0 else 11.6)
        root.add_child(pier)
        for item in pier.find_children("*", "MeshInstance3D", true, false):
            var mesh := item as MeshInstance3D
            var label := str(mesh.name).to_lower()
            if "fiber" in label:
                mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
                continue
            if mesh.material_overlay == null:
                var overlay := ShaderMaterial.new()
                overlay.shader = WETNESS
                overlay.render_priority = 1
                mesh.material_overlay = overlay
            if "waterpile_" in label:
                var p := mesh.global_position
                if environment._sand_height(p.x - environment._shore(p.z), p.z) < 0:
                    contacts.append(Vector4(p.x, p.z, 0.13, 0.38))
            if "pin" in label or "binding" in label:
                continue
            var body := StaticBody3D.new()
            body.collision_layer = 4
            body.collision_mask = 0
            mesh.add_child(body)
            var collision := CollisionShape3D.new()
            collision.shape = mesh.mesh.create_trimesh_shape()
            body.add_child(collision)
