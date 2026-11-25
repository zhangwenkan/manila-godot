"""Connect one independent GUI Blender process. Never save or build models."""
import addon_utils
import bpy
import json
import os
from pathlib import Path
import sys

expected = os.environ.get("MANILA_EXPECTED_BLEND", "")
if expected:
    assert Path(bpy.data.filepath).resolve() == Path(expected).resolve(), "Wrong Blender file"
else:
    assert not bpy.data.filepath, "Expected a fresh unsaved scene"

if "blender_mcp" not in bpy.context.preferences.addons:
    addon_utils.enable("blender_mcp", default_set=False)
addon = sys.modules["blender_mcp"]
addon._blendermcp_unregister_auto_start()
old_server = getattr(bpy.types, "blendermcp_server", None)
if old_server:
    old_server.stop()
port = int(os.environ.get("MANILA_MCP_PORT", "9879"))
for scene in bpy.data.scenes:
    scene.blendermcp_auto_start_server = False
    scene.blendermcp_port = port
preferences = bpy.context.preferences.addons["blender_mcp"].preferences
preferences.bind_address = "127.0.0.1"
preferences.allow_remote_connections = False
preferences.telemetry_consent = False
server = addon.BlenderMCPServer(host="127.0.0.1", port=port)
bpy.types.blendermcp_server = server
server.start()
assert server.running, "MCP failed to start"
bpy.context.scene.blendermcp_server_running = True
print("MANILA_MCP_READY " + json.dumps({
    "pid": os.getpid(), "file": bpy.data.filepath,
    "port": port, "objects": len(bpy.data.objects),
    "blender": bpy.app.version_string,
}), flush=True)
