extends SceneTree

const STATE = preload("res://fleet/fleet_state.gd")
const SHIP = preload("res://ships/ship_view.gd")
const PIER = preload("res://environment/pier_builder.gd")
const ENVIRONMENT = preload("res://environment/harbor_environment.gd")
var checks := 0
var failures := 0


func check(condition: bool, message: String) -> void:
    checks += 1
    if not condition:
        failures += 1
        push_error("FLEET_GEOMETRY_FAIL: " + message)


func meshes(node: Node3D, relative: Transform3D = Transform3D.IDENTITY) -> Array[Dictionary]:
    var result: Array[Dictionary] = []
    var transform_ := relative * node.transform
    if node is MeshInstance3D:
        result.append({"node": node, "transform": transform_})
    for child in node.get_children():
        if child is Node3D:
            result.append_array(meshes(child, transform_))
    return result


# Triangle / box SAT checks actual surfaces, not the AABB around a hollow hull.
func triangle_hits_box(a: Vector3, b: Vector3, c: Vector3, box: AABB) -> bool:
    var center := box.get_center()
    a -= center
    b -= center
    c -= center
    var half := box.size * 0.5
    var edges := [b - a, c - b, a - c]
    var axes: Array[Vector3] = [Vector3.RIGHT, Vector3.UP, Vector3.BACK, (b - a).cross(c - a)]
    for edge in edges:
        for axis in [Vector3.RIGHT, Vector3.UP, Vector3.BACK]:
            axes.append(edge.cross(axis))
    for axis in axes:
        if axis.length_squared() < 0.00000001:
            continue
        var pa := a.dot(axis)
        var pb := b.dot(axis)
        var pc := c.dot(axis)
        var radius := half.dot(axis.abs())
        if minf(pa, minf(pb, pc)) > radius or maxf(pa, maxf(pb, pc)) < -radius:
            return false
    return true


func intersects(item: Dictionary, box: AABB) -> bool:
    var mesh: Mesh = item.node.mesh
    var transform_: Transform3D = item.transform
    if not (transform_ * mesh.get_aabb()).intersects(box):
        return false
    var faces := mesh.get_faces()
    for i in range(0, faces.size(), 3):
        if triangle_hits_box(transform_ * faces[i], transform_ * faces[i + 1], transform_ * faces[i + 2], box):
            return true
    return false


func floor_support(hull: Array[Dictionary], point: Vector3) -> bool:
    for item in hull:
        if not str(item.node.name).begins_with("Floorboard"):
            continue
        var faces: PackedVector3Array = item.node.mesh.get_faces()
        for i in range(0, faces.size(), 3):
            var hit = Geometry3D.segment_intersects_triangle(point + Vector3(0, 0.01, 0), point - Vector3(0, 0.04, 0),
                item.transform * faces[i], item.transform * faces[i + 1], item.transform * faces[i + 2])
            if hit != null:
                return true
    return false


func _initialize() -> void:
    run.call_deferred()


func run() -> void:
    var state := STATE.new()
    for cargo in STATE.CARGO:
        var cargos: Array = STATE.CARGO.keys()
        cargos.erase(cargo)
        state.start_voyage([cargo, cargos[0], cargos[1]], [3, 3, 3])
        var data: Dictionary = state.ships[0]
        for i in data.slots.size():
            data.slots[i].owner = i % 3
        var ship := SHIP.new()
        root.add_child(ship)
        ship.build(data)
        var hull := meshes(ship.get_child(0))
        var cargo_meshes := meshes(ship.cargo_root)
        for item in hull:
            check(not ("cabin" in str(item.node.name).to_lower() or "roof" in str(item.node.name).to_lower()), "legacy cabin remains")
            check((item.transform * item.node.mesh.get_aabb()).end.y < 1.10, "empty hull silhouette is too tall")
        for pawn in ship.pawn_roots:
            for child in pawn.get_children():
                if not child is MeshInstance3D:
                    continue
                var box: AABB = child.mesh.get_aabb()
                for corner in 8:
                    var point: Vector3 = child.transform * box.get_endpoint(corner)
                    check(absf(point.x) <= SHIP.PAWN_SIZE.x / 2 + 0.001 and absf(point.z) <= SHIP.PAWN_SIZE.z / 2 + 0.001
                        and point.y >= -0.001 and point.y <= SHIP.PAWN_SIZE.y + 0.001, "actual mesh exceeds replaceable pawn envelope")
        for anchor in ship.slot_roots:
            var at: Vector3 = anchor.position
            var body := AABB(at - Vector3(SHIP.PAWN_SIZE.x / 2, -0.012, SHIP.PAWN_SIZE.z / 2), SHIP.PAWN_SIZE - Vector3(0, 0.012, 0))
            for item in hull + cargo_meshes:
                check(not intersects(item, body), "%s crew overlaps %s" % [cargo, item.node.name])
            check(is_equal_approx(at.y, SHIP.DECK_HEIGHT), "feet must match the floor height")
            for side in [-1, 1]:
                check(floor_support(hull, at + Vector3(side * 0.13, 0, 0)), "feet must have real floorboard support")
        ship.free()
    for scene in [PIER.WORKING, PIER.BROKEN]:
        var pier := scene.instantiate() as Node3D
        var piles := 0
        var boards := 0
        for item in meshes(pier):
            var name_: String = str(item.node.name).to_lower()
            if "waterpile_" in name_:
                piles += 1
            if not ("walkboard" in name_ or "broken board" in name_):
                continue
            boards += 1
            var top_faces := 0
            var bottom_faces := 0
            var mesh: Mesh = item.node.mesh
            for surface in mesh.get_surface_count():
                var normals: PackedVector3Array = mesh.surface_get_arrays(surface)[Mesh.ARRAY_NORMAL]
                for normal in normals:
                    var n: Vector3 = item.transform.basis * normal
                    top_faces += int(n.y > 0.98)
                    bottom_faces += int(n.y < -0.98)
            check(top_faces > 0 and bottom_faces > 0, "MCP board must have top and bottom faces")
        check(piles == 8 and boards >= 25, "MCP pier structural components missing")
        pier.free()
    print("FLEET_GEOMETRY_%s checks=%d failures=%d" % ["PASS" if failures == 0 else "FAIL", checks, failures])
    quit(0 if failures == 0 else 2)
