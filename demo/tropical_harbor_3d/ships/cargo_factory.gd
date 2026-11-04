extends RefCounted


static func material(color: String, roughness: float = 0.85) -> StandardMaterial3D:
    var result := StandardMaterial3D.new()
    result.albedo_color = Color(color)
    result.roughness = roughness
    return result


static func mesh(parent: Node3D, shape: Mesh, at: Vector3, mat: Material) -> MeshInstance3D:
    var instance := MeshInstance3D.new()
    instance.mesh = shape
    instance.position = at
    instance.material_override = mat
    parent.add_child(instance)
    return instance


static func box(parent: Node3D, at: Vector3, size_: Vector3, mat: Material) -> MeshInstance3D:
    var shape := BoxMesh.new()
    shape.size = size_
    return mesh(parent, shape, at, mat)


static func cylinder(parent: Node3D, at: Vector3, radius: float, height: float, mat: Material, top: float = -1.0) -> MeshInstance3D:
    var shape := CylinderMesh.new()
    shape.top_radius = radius if top < 0.0 else top
    shape.bottom_radius = radius
    shape.height = height
    shape.radial_segments = 12
    return mesh(parent, shape, at, mat)


static func sphere(parent: Node3D, at: Vector3, scale_: Vector3, mat: Material) -> MeshInstance3D:
    var shape := SphereMesh.new()
    shape.radius = 0.5
    shape.height = 1.0
    shape.radial_segments = 12
    shape.rings = 6
    var instance := mesh(parent, shape, at, mat)
    instance.scale = scale_
    return instance


static func make(cargo_id: String) -> Node3D:
    var root := Node3D.new()
    root.name = "CargoRoot"
    var timber := material("ac7a40")
    var rim := material("d3ac6f")
    match cargo_id:
        "ginseng":
            var skin := material("e2c487")
            for z in [-0.42, 0.30]:
                box(root, Vector3(0, 0.04, z), Vector3(0.40, 0.08, 0.50), timber)
                for x in [-0.20, 0.20]:
                    box(root, Vector3(x, 0.14, z), Vector3(0.035, 0.20, 0.52), rim)
                for end in [-0.25, 0.25]:
                    box(root, Vector3(0, 0.14, z + end), Vector3(0.40, 0.20, 0.025), rim)
                for i in 4:
                    var x := -0.13 + i * 0.085
                    var body := cylinder(root, Vector3(x, 0.18, z), 0.035, 0.33, skin, 0.022)
                    body.rotation.x = PI / 2.0
                    for side in [-1, 1]:
                        var twig := cylinder(root, Vector3(x + side * 0.018, 0.16, z + 0.18), 0.012, 0.12, skin, 0.006)
                        twig.rotation.x = PI / 2.0
                        twig.rotation.z = side * 0.20
        "nutmeg":
            var sack := material("b68b57")
            var beans := material("634732")
            for z in [-0.48, 0.0, 0.48]:
                sphere(root, Vector3(0, 0.19, z), Vector3(0.39, 0.38, 0.43), sack)
                cylinder(root, Vector3(0, 0.36, z), 0.125, 0.07, rim, 0.14)
                for i in 5:
                    var a := i * TAU / 5.0
                    sphere(root, Vector3(cos(a) * 0.065, 0.405, z + sin(a) * 0.065), Vector3.ONE * 0.07, beans)
        "silk":
            var fabrics := [material("609bb4"), material("b7d4cc"), material("d0a06e")]
            for i in 3:
                var z := -0.45 + i * 0.45
                var roll := cylinder(root, Vector3(0, 0.12, z), 0.115, 0.38, fabrics[i])
                roll.rotation.z = PI / 2.0
                for side in [-1, 1]:
                    var core := cylinder(root, Vector3(side * 0.197, 0.12, z), 0.038, 0.016, timber)
                    core.rotation.z = PI / 2.0
                box(root, Vector3(0, 0.232, z), Vector3(0.032, 0.018, 0.17), rim)
        "jade":
            box(root, Vector3(0, 0.04, 0), Vector3(0.44, 0.08, 1.48), timber)
            var stones := [material("559c7d"), material("81c7a1"), material("acd4aa")]
            for i in 5:
                var shape := PrismMesh.new()
                shape.size = Vector3(0.24, 0.24 + (i % 2) * 0.08, 0.28)
                var stone := mesh(root, shape, Vector3(0.035 * (-1 if i % 2 else 1), 0.20, -0.56 + i * 0.28), stones[i % 3])
                stone.rotation.y = 0.3 * (i - 2)
    return root
