extends Node3D

# Spatial study only: every mesh comes from the isolated Blender MCP session.
const ART := "res://demo/tropical_harbor_3d/assets/coast/layout_"
const ROUTE = preload("res://demo/tropical_harbor_3d/fleet/harbor_route.gd")
const SPECS := [
    {"id": "PilotLighthouse", "asset": "lighthouse", "at": Vector3(-10.8, 0, 6.0), "label": "领航灯塔 · 大 / 小", "anchor": Vector3(0, 6.0, 0)},
    {"id": "PirateIsland", "asset": "pirate_island", "at": Vector3(-12.6, 0, -8.2), "label": "海盗 · 13号位", "anchor": Vector3(0, 6.5, 0)},
    {"id": "RepairYard", "asset": "shipyard", "at": Vector3(10.2, 0, 0), "label": "修船厂 · A / B / C", "anchor": Vector3(0, 5.1, 0)},
    {"id": "InsuranceOffice", "asset": "insurance", "at": Vector3(10.7, 0, -9.1), "label": "保险公司", "anchor": Vector3(0, 4.7, 0)},
    {"id": "AuctionBoard", "asset": "auction", "at": Vector3(12.0, .65, 11.8), "label": "竞拍 / 行情", "anchor": Vector3(0, 3.5, 0)},
    {"id": "BackdropVillage", "asset": "village", "at": Vector3(17.0, 0, -.8), "label": "", "anchor": Vector3.ZERO},
    {"id": "WesternLand", "asset": "western_land", "at": Vector3.ZERO, "label": "", "anchor": Vector3.ZERO}
]
var western_land := false
var labels_visible := true
var labels: Array[Label3D] = []
var shipyard_variant := "combined"


func build(scenic: bool = false) -> void:
    var specs: Array = SPECS.duplicate(true)
    if scenic:
        specs[0].at = ROUTE.lighthouse()
        specs[1].at = Vector3(-15.3, 0, -6.4)
        specs[2].at = Vector3(10.5, 0, 34.0)
        specs[3].at = Vector3(10.5, 0, 9.0)
        specs[4].at = Vector3(10.5, .65, 60.0)
        specs[5].at = Vector3(25, 0, 48)
        specs[2]["yaw"] = -12.0
        specs[3]["yaw"] = 12.0
        specs.append({"id": "CoastalGrove", "asset": "route_grove", "at": Vector3.ZERO, "label": "", "anchor": Vector3.ZERO})
        specs.append({"id": "LowerVillage", "asset": "village", "at": Vector3(20, 0, 14), "label": "", "anchor": Vector3.ZERO})
    for spec in specs:
        if scenic and spec.id in ["BackdropVillage", "LowerVillage", "CoastalGrove"]:
            # The authored coastal landscape replaces these spatial placeholders.
            continue
        if scenic and spec.id == "RepairYard":
            _build_shipyards()
            continue
        var model := (load(ART + spec.asset + ".glb") as PackedScene).instantiate() as Node3D
        model.name = spec.id
        model.position = spec.at
        model.rotation_degrees.y = spec.get("yaw", 0.0)
        add_child(model)
        for item in model.find_children("*", "MeshInstance3D", true, false):
            var mesh := item as MeshInstance3D
            var body := StaticBody3D.new()
            body.collision_layer = 4
            body.collision_mask = 0
            mesh.add_child(body)
            var shape := CollisionShape3D.new()
            shape.shape = mesh.mesh.create_trimesh_shape()
            body.add_child(shape)
        if not spec.label.is_empty():
            _label(model, spec.label, spec.anchor)
    if scenic:
        _build_coastal_environment()
    # Mark the start and the pirate event line without filling the sea with UI.
    for lane in 3:
        for progress in ([0, 4, 8, 13] if scenic else [0, 13]):
            var buoy := (load(ART + "buoy.glb") as PackedScene).instantiate() as Node3D
            buoy.position = ROUTE.point(lane, progress) + Vector3(1.5, 0, 0) if scenic else Vector3([-6.0, -2.7, .6][lane] + 1.35, 0, 10.0 - progress * 1.4)
            add_child(buoy)
            _label(buoy, str(progress), Vector3(0, 1.05, 0), 25)
    set_western_land(false)


func _build_coastal_environment() -> void:
    var path := "res://demo/tropical_harbor_3d/assets/coast/coastal_environment.glb"
    var model := (load(path) as PackedScene).instantiate() as Node3D
    model.name = "CoastalEnvironment"
    add_child(model)
    for item in model.find_children("*", "MeshInstance3D", true, false):
        var mesh := item as MeshInstance3D
        # Soft foliage does not become an invisible wall. Authored ground,
        # rocks and buildings retain solid geometry for camera/route checks.
        if "_Leaf_" in str(mesh.name) or "_Grass_" in str(mesh.name):
            continue
        var body := StaticBody3D.new()
        body.collision_layer = 4
        body.collision_mask = 0
        mesh.add_child(body)
        var shape := CollisionShape3D.new()
        shape.shape = mesh.mesh.create_trimesh_shape()
        body.add_child(shape)


func _build_shipyards() -> void:
    var yard := Node3D.new()
    yard.name = "RepairYard"
    yard.position = Vector3(12.35, 0, 34)
    # Set the work platforms inside the shore; only the central slip reaches water.
    yard.rotation_degrees.y = -81.5
    add_child(yard)
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--shipyard=") and arg.trim_prefix("--shipyard=") in ["a", "b", "combined"]:
            shipyard_variant = arg.trim_prefix("--shipyard=")
    var variants := [shipyard_variant]
    if "--shipyard-compare" in OS.get_cmdline_user_args():
        variants = ["a", "b", "combined"]
    for variant in variants:
        var path: String = "res://demo/tropical_harbor_3d/assets/coast/shipyard_" + variant + ".glb"
        if not ResourceLoader.exists(path):
            continue
        var model := (load(path) as PackedScene).instantiate() as Node3D
        model.name = variant.to_upper()
        yard.add_child(model)
        for item in model.find_children("*", "MeshInstance3D", true, false):
            var mesh := item as MeshInstance3D
            if "M14_SculptedBank" in str(mesh.name):
                # The bank is authored in Blender. Share the beach response so
                # its buried perimeter blends with the surrounding sand.
                mesh.material_override = get_parent().environment.sand_material
            if "Shipyard_SignInk" in str(mesh.name):
                mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
            if "SP13_CompactedAccess" in str(mesh.name):
                # This thin ground colour layer receives light but must not cast
                # a second, dithered shadow onto the sand directly beneath it.
                mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
                for surface in mesh.mesh.get_surface_count():
                    var source := mesh.get_active_material(surface) as StandardMaterial3D
                    if source != null:
                        var soil := source.duplicate() as StandardMaterial3D
                        soil.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
                        soil.depth_draw_mode = BaseMaterial3D.DEPTH_DRAW_DISABLED
                        mesh.set_surface_override_material(surface, soil)
                continue
            var body := StaticBody3D.new()
            body.collision_mask = 0
            mesh.add_child(body)
            var shape := CollisionShape3D.new()
            shape.shape = mesh.mesh.create_trimesh_shape()
            body.add_child(shape)
    set_shipyard_variant(shipyard_variant)


func set_shipyard_variant(variant: String) -> void:
    var yard := get_node_or_null("RepairYard")
    if yard == null or not yard.has_node(variant.to_upper()):
        return
    shipyard_variant = variant
    for model in yard.get_children():
        model.visible = model.name == variant.to_upper()
        for body in model.find_children("*", "StaticBody3D", true, false):
            body.collision_layer = 4 if model.visible else 0


func _label(parent: Node3D, title: String, at: Vector3, font_size: int = 33) -> void:
    var label := Label3D.new()
    label.text = title
    label.position = at
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    label.font_size = font_size
    label.pixel_size = .014
    label.modulate = Color("fff0d0")
    label.outline_modulate = Color("263a3b")
    label.outline_size = 7
    label.no_depth_test = true
    label.render_priority = 10
    parent.add_child(label)
    labels.append(label)


func set_labels(value: bool) -> void:
    labels_visible = value
    for label in labels:
        label.visible = value


func set_western_land(value: bool) -> void:
    western_land = value
    var land := get_node("WesternLand") as Node3D
    land.visible = value
    for body in land.find_children("*", "StaticBody3D", true, false):
        body.collision_layer = 4 if value else 0
