"""Install-time preferences only; does not save or change model data."""
import addon_utils
import bpy
import json
import os
import sys

addon_utils.modules_refresh()
addon_utils.enable("blender_mcp", default_set=True, persistent=True)
addon = sys.modules["blender_mcp"]
addon._blendermcp_unregister_auto_start()
preferences = bpy.context.preferences.addons["blender_mcp"].preferences
preferences.bind_address = "127.0.0.1"
preferences.allow_remote_connections = False
preferences.telemetry_consent = False
bpy.ops.wm.save_userpref()
print("MANILA_ADDON_ENABLED " + json.dumps({
    "blender": bpy.app.version_string,
    "module": addon.__file__,
    "enabled": "blender_mcp" in bpy.context.preferences.addons,
    "host": preferences.bind_address,
    "telemetry": preferences.telemetry_consent,
}), flush=True)
