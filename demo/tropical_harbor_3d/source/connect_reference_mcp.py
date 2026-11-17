"""Connection bootstrap only for the independently authored reference harbor."""
import bpy
import importlib.util
import os
import sys
from pathlib import Path

expected = Path(__file__).with_name('reference_harbor_mcp.blend').resolve()
assert not bpy.data.filepath or Path(bpy.data.filepath).resolve() == expected, 'Refusing an unrelated Blender file'
spec = importlib.util.spec_from_file_location('manila_reference_mcp', 'D:/一些好玩的例子/blender-mcp/addon.py')
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
addon.register()
server = addon.BlenderMCPServer(host='127.0.0.1', port=9879)
server.start()
assert server.running, 'Reference MCP port unavailable'
bpy.app.driver_namespace['manila_reference_mcp_server'] = server
print('MANILA_REFERENCE_MCP_READY', os.getpid(), '127.0.0.1:9879', flush=True)
