extends RefCounted

# Scene presentation only; rule progress and berth allocation remain in FleetState.
const START_Z := 66.0
const STEP := 5.7
const ENTRY := 13.12
const LIGHTHOUSE_PROGRESS := 7.5


static func center(progress: float) -> Vector3:
    # Approach the waterfront gently from open water, then run alongside it.
    # The bow follows this real bend instead of being turned for the camera.
    return Vector3(-6.0 + 3.0 * smoothstep(0.0, 6.0, progress), 0, START_Z - STEP * progress)


static func spacing(progress: float) -> float:
    return 4.4 + 3.6 * exp(-pow((progress - LIGHTHOUSE_PROGRESS) / 1.8, 2))


static func point(lane: int, progress: float) -> Vector3:
    return center(progress) + Vector3((lane - 1) * spacing(progress), 0, 0)


static func heading(lane: int, progress: float) -> float:
    var direction := point(lane, progress + .01) - point(lane, progress - .01)
    return atan2(-direction.x, -direction.z)


static func lighthouse() -> Vector3:
    return (point(1, LIGHTHOUSE_PROGRESS) + point(2, LIGHTHOUSE_PROGRESS)) * .5


static func aim_offset(progress: float) -> Vector3:
    # Show the next work area above the opening fleet, then follow the nearby
    # shore as it passes. These anchors do not depend on the spread of the dice.
    var coastal := Vector3(4.5, 1.5, -6.0).lerp(Vector3(3.0, 1.5, -1.0), smoothstep(3.0, 5.6, progress))
    return coastal.lerp(Vector3(2.0, 2.2, -1.5), smoothstep(11.5, 14.5, progress))


static func framing_origin(subject: Vector3, progress: float) -> Vector3:
    # Lane selection must not push the bank out of the picture. Keep the
    # along-route subject anchor, with only a small lateral shift between lanes.
    if progress >= 14.0:
        return subject
    return Vector3(lerpf(center(progress).x, subject.x, .25), subject.y, subject.z)


static func offset(progress: float) -> Vector3:
    # Stay over water, behind the fleet, looking almost along its heading.
    # The shore-aligned yard needs a slightly more seaward departure viewpoint.
    var approach_x := lerpf(-3.0, 3.5, smoothstep(3.0, 6.5, progress))
    return Vector3(approach_x, 17, 21).lerp(Vector3(4, 19, 22), smoothstep(11.5, 14.5, progress))


static func fits_local_shot(points: Array, headings: Array, progress: float, aspect: float, fov: float, space: PhysicsDirectSpaceState3D = null) -> bool:
    # A neighbor may enter the shot without pulling the camera off its subject.
    var center_: Vector3 = framing_origin(points[0], progress)
    var offset_ := offset(progress)
    var eye := center_ + aim_offset(progress) + offset_
    var basis_ := Basis.looking_at(-offset_.normalized())
    var vertical := tan(deg_to_rad(fov) * .5)
    for i in points.size():
        var turn := Basis(Vector3.UP, headings[i])
        for x in [-1.05, 1.05]:
            for y in [-.4, 1.3]:
                for z in [-2.55, 2.55]:
                    var relative: Vector3 = points[i] + turn * Vector3(x, y, z) - eye
                    var depth := -relative.dot(basis_.z)
                    if depth <= 0 or absf(relative.dot(basis_.x)) > depth * vertical * aspect * .90 or absf(relative.dot(basis_.y)) > depth * vertical * .82:
                        return false
        if space != null:
            for z in [-1.8, 0, 1.8]:
                var ray := PhysicsRayQueryParameters3D.create(eye, points[i] + turn * Vector3(0, .5, z), 4)
                if not space.intersect_ray(ray).is_empty():
                    return false
    return true
