extends RefCounted

# Shared world dimensions, in metres. Boat hulls are about 4.7 x 1.8 m.
const COAST_SHAPE := Vector4(8.0, 2.0, 0.6, 0.0)
const BAY_SHAPE := Vector4(-2.5, 3.6, 2.2, 0.85)
const LANES := [-6.0, -2.7, 0.6]
const START_Z := 10.0
const STEP := 1.4
const BERTH_X := [-4.15, -0.85, 2.45]
const BERTH_Z := -16.6
const DOCK_ENTRY_Z := -8.8
const APRON_FRONT_Z := -19.55
const LANDING_BOUNDS := AABB(Vector3(-7.77, -4.8, -19.68), Vector3(2.24, 6.3, 8.06))
const PORT_POSTS := [Vector3(-4.15, 0.913, -20.65), Vector3(-0.85, 0.913, -20.65), Vector3(2.45, 0.913, -20.65)]
const TERMINAL_ORIGIN := Vector3(1.0, 0.913, -23.6)
const WORKING_PIER := Vector3(7.01, 0, 7.3)
const BROKEN_PIER := Vector3(7.01, 0, 11.6)
const LANDING := Vector3(1.5, 0, -17.8)
# The cargo veranda joins the right side of the terminal apron.
const CARGO_PLATFORM_BOUNDS := AABB(Vector3(8.60, -2.0, -22.51), Vector3(2.35, 5.0, 6.62))
const COAST_BUILDINGS := [
    {"id": "ArrivalTerminal", "asset": "harbor_terminal", "label": "终点码头 · A / B / C", "at": TERMINAL_ORIGIN, "height": 11.4},
    {"id": "HarborOffice", "asset": "harbor_office", "label": "港口货仓", "at": Vector3(13.2, 0.88, -19.2), "height": 5.0},
    {"id": "Warehouse", "asset": "warehouse", "label": "货仓", "at": Vector3(16.7, 0.88, -8.8), "height": 5.3},
    {"id": "Insurance", "asset": "insurance", "label": "保险公司", "at": Vector3(14.0, 0.88, 1.0), "height": 5.4},
    {"id": "PilotHouse", "asset": "pilot_house", "label": "引航所", "at": Vector3(12.0, 0.88, 7.0), "height": 3.8},
    {"id": "Shipyard", "asset": "shipyard", "label": "修船厂 A · B · C", "at": Vector3(6.4, 0.0, 16.0), "height": 5.8},
    {"id": "Market", "asset": "market", "label": "行情与交易", "at": Vector3(23.2, 0.9, -17.0), "height": 3.8},
    {"id": "PirateWatch", "asset": "pirate_watch", "label": "海盗停泊点", "at": Vector3(-10.5, 0.0, -8.6), "height": 3.3}
]
const REPAIR_BERTHS := [Vector3(3.4, 0, 12.0), Vector3(3.4, 0, 16.0), Vector3(3.4, 0, 20.0)]


static func overview_landmarks(fleet_center_z: float) -> Array[Vector3]:
    # Follow the active part of the harbor. Fitting both ends of an empty route
    # would shrink the opening fleet and reintroduce the scale problem.
    var arrival := smoothstep(9.0, 20.0, START_Z - fleet_center_z)
    var result: Array[Vector3] = []
    for i in 2:
        for j in 2:
            var departure := Vector3(2.2 if i == 0 else 11.4, 1.6, 5.8 if j == 0 else 12.8)
            var destination := Vector3(-7.8 if i == 0 else 10.65, 1.6, -19.55 if j == 0 else -11.6)
            result.append(departure.lerp(destination, arrival))
    return result
