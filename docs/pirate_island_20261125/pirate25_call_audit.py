"""Read-only source check wrapper: execute only through the owned MCP."""
from pathlib import Path

project = Path(r"F:/马尼拉godot/manila-godot")
source = project / "demo/tropical_harbor_3d/source/harbor_shore_control_mcp.blend"
definition = project / "docs/pirate_island_20261125/pirate25_audit.py"
namespace = {"__name__": "pirate25_audit_owned_call"}
exec(compile(definition.read_text(encoding="utf8"), str(definition), "exec"), namespace)
namespace["audit_pirate25"](1028, 9881, source, source.parent.parent / "captures/pirate_island_20261125", maximum_world_x=-10.5)
