extends RefCounted

var host: Node
var harbor: Node3D
var checks := 0
var observations: Array[Dictionary] = []


func verify(ok: bool, message: String) -> bool:
    checks += 1
    if not ok:
        push_error("LAYOUT_REVIEW: " + message)
        host.get_tree().quit(2)
    return ok


func fixture(progress: Array) -> void:
    harbor.state.start_voyage(["jade", "silk", "ginseng"], [3, 3, 3])
    for i in 3:
        harbor.state.ships[i].progress = progress[i]
        for j in mini(i + 1, harbor.state.ships[i].slots.size()):
            harbor.state.ships[i].slots[j].owner = (i + j) % 3
    harbor.rebuild_ships()
    harbor.camera.local_harbor = true
    harbor.camera.focus_ship = -1
    harbor.camera.update_view(harbor.ships, 0, true)


func record(label: String, require_all: bool = true) -> bool:
    var screen := host.get_viewport().get_visible_rect()
    var sizes: Array[Dictionary] = []
    for ship in harbor.ships:
        var min_ := Vector2(INF, INF)
        var max_ := Vector2(-INF, -INF)
        for p in ship.envelope_points():
            var projected: Vector2 = harbor.camera.unproject_position(p)
            min_ = min_.min(projected)
            max_ = max_.max(projected)
        var bounds := Rect2(min_, max_ - min_)
        sizes.append({"ship": ship.ship_id, "screen_rect": [min_.x, min_.y, bounds.size.x, bounds.size.y], "fully_visible": screen.grow(-22).encloses(bounds)})
        if require_all and not verify(screen.grow(-22).encloses(bounds), label + ": all three ship envelopes visible"):
            return false
        if require_all and not verify(maxf(bounds.size.x, bounds.size.y) >= 85, label + ": ships retain a readable screen size"):
            return false
        # Actual environment collision check on the line to the center of each hull.
        if require_all:
            var ray := PhysicsRayQueryParameters3D.create(harbor.camera.position, ship.position + Vector3(0, .35, 0), 4)
            if not verify(harbor.get_world_3d().direct_space_state.intersect_ray(ray).is_empty(), label + ": building does not block boat center"):
                return false
    observations.append({"view": label, "ships": sizes, "camera": harbor.camera.position, "fov": harbor.camera.fov})
    return true


func run(preview: Node) -> void:
    host = preview
    harbor = host.harbor
    harbor.capture_lock = true
    harbor.coast.set_observing(true)
    harbor.camera.local_harbor = true
    if "--layout-motion" in OS.get_cmdline_user_args():
        await motion()
        return
    var stages := [{"id": "01_departure", "progress": [3, 3, 3]}, {"id": "02_midway", "progress": [7, 7, 7]},
        {"id": "03_pirates", "progress": [13, 13, 13]}, {"id": "04_spread", "progress": [3, 8, 13]},
        {"id": "07_initial", "progress": [0, 4, 5]}, {"id": "08_extreme", "progress": [0, 13, 13]}]
    for stage in stages:
        fixture(stage.progress)
        await host.get_tree().physics_frame
        for bank in [false, true]:
            harbor.blockout.set_western_land(bank)
            var label: String = stage.id + ("_land" if bank else "_sea")
            await host.capture(label)
            if not record(label):
                return
    harbor.blockout.set_western_land(false)
    fixture([7, 7, 7])
    harbor.blockout.set_labels(false)
    await host.capture("02_midway_clean")
    harbor.blockout.set_labels(true)
    for profile in [{"offset": Vector3(12, 19, 23), "fov": 36.0, "id": "closer"},
            {"offset": Vector3(18, 28, 36), "fov": 30.0, "id": "longer_lens"},
            {"offset": Vector3(20, 23, 38), "fov": 30.0, "id": "shallower"}]:
        harbor.camera.local_offset = profile.offset
        harbor.camera.local_fov = profile.fov
        harbor.camera.update_view(harbor.ships, 0, true)
        await host.capture("angle_" + profile.id)
    harbor.camera.local_offset = Vector3(18, 28, 36)
    harbor.camera.local_fov = 26.0
    fixture([13, 13, 13])
    # Exercise real dice and the visible lane / arrival cut, rather than
    # inventing a new scene just to show a favorable stopped pose.
    harbor.paused = false
    harbor.roll_dice()
    var saw_opaque := false
    var moved_during_opaque := false
    var pause_checked := false
    var stall_checked := false
    var previous: Array[Vector3] = []
    for ship in harbor.ships:
        previous.append(ship.position)
    for step in range(1200):
        harbor.time += .025
        for i in 3:
            harbor.ships[i].advance(.025, harbor.time)
        if harbor.arrival_transition and not pause_checked:
            var elapsed: float = harbor.arrival_elapsed
            harbor.paused = true
            harbor.capture_lock = false
            harbor._process(.15)
            harbor.capture_lock = true
            harbor.paused = false
            if not verify(is_equal_approx(harbor.arrival_elapsed, elapsed), "pause freezes the arrival transition"):
                return
            pause_checked = true
        var fade_delta := .025
        if harbor.arrival_transition and not stall_checked:
            fade_delta = .8
            stall_checked = true
        harbor._advance_arrival_transition(fade_delta)
        if harbor.arrival_cover.color.a >= .99:
            saw_opaque = true
        for i in 3:
            if absf(harbor.ships[i].position.x - previous[i].x) > .01:
                moved_during_opaque = harbor.arrival_cover.color.a >= .99
                if not verify(moved_during_opaque, "berth relocation happens behind an opaque transition"):
                    return
            previous[i] = harbor.ships[i].position
        if not harbor.is_moving():
            break
    if not verify(saw_opaque and moved_during_opaque and not harbor.is_moving(), "arrival transition completes and preserves A/B/C destinations"):
        return
    for i in 3:
        if not verify(harbor.ships[i].position.distance_to(harbor.state.world_position(harbor.state.ships[i])) < .15, "ship rests in its rule-assigned berth"):
            return
    harbor.camera.update_view(harbor.ships, 0, true)
    await host.capture("05_arrived")
    if not record("05_arrived"):
        return
    harbor.ui.visible = true
    await host.capture("06_interface")
    var before: Basis = harbor.camera.global_basis
    harbor.camera.orbit(Vector2(350, 200))
    harbor.camera.zoom_inspection(3)
    harbor.camera.update_view(harbor.ships, 0, true)
    if not verify(harbor.camera.global_basis.is_equal_approx(before), "player orbit input cannot turn the fixed local camera"):
        return
    harbor.ui.visible = false
    # The rightmost lane arrives first and must occupy the actual A berth.
    fixture([0, 0, 13])
    harbor.roll_dice()
    for step in 1200:
        harbor.time += .025
        for ship in harbor.ships:
            ship.advance(.025, harbor.time)
        harbor._advance_arrival_transition(.025)
        if not harbor.is_moving():
            break
    if not verify(not harbor.is_moving() and harbor.state.ships[2].berth == 0, "rightmost first arrival receives A"):
        return
    if not verify(absf(harbor.ships[2].position.x - harbor.STATE.LAYOUT.BERTH_X[0]) < .01, "rightmost first arrival actually rests at A"):
        return
    harbor.camera.update_view(harbor.ships, 0, true)
    await host.capture("09_mixed_arrival")
    if not record("09_mixed_arrival"):
        return
    var docked: Vector3 = harbor.ships[2].position
    harbor.roll_dice()
    if not verify(not 2 in harbor.pending_berths and harbor.ships[2].waypoints.is_empty(), "later rolls leave the docked ship in place"):
        return
    var state_before: Array = harbor.state.ships.duplicate(true)
    harbor.blockout.set_western_land(true)
    harbor.select_ship(1)
    harbor.overview()
    harbor.blockout.set_western_land(false)
    if not verify(state_before == harbor.state.ships and docked == harbor.ships[2].position, "camera and layout toggles preserve gameplay state"):
        return
    host.finish({"kind": "local harbor blockout", "checks": checks, "observations": observations, "western_land_default": false,
        "rules": "pirates at 13; pilot +/-1 or up to +/-2; building gameplay not implemented", "visual_accepted": false})


func motion() -> void:
    fixture([3, 3, 3])
    harbor.blockout.set_western_land(false)
    harbor.blockout.set_labels(false)
    for i in 3:
        harbor.ships[i].travel_to(Vector3(harbor.STATE.LANES[i], 0, -8.2 + i*.7), false)
    for frame in range(96):
        for step in 2:
            harbor.time += 1.0/16.0
            for ship in harbor.ships:
                ship.advance(1.0/16.0, harbor.time)
            harbor.camera.update_view(harbor.ships, 1.0/16.0)
        if not await host.capture("voyage_%03d" % frame, false, 2):
            return
    host.finish({"kind": "fixed local harbor voyage", "frames_per_second": 8, "duration": 12, "visual_accepted": false})
