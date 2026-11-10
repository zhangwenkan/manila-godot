"""Connection bootstrap only. No geometry is created or changed here."""
import bpy
import importlib.util
import os
from pathlib import Path
import sys

expected = Path(__file__).with_name('harbor_coast_mcp.blend').resolve()
if Path(bpy.data.filepath).resolve() != expected:
    raise RuntimeError('Refusing to connect an unrelated Blender file')
spec = importlib.util.spec_from_file_location('manila_isolated_mcp', 'D:/一些好玩的例子/blender-mcp/addon.py')
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
addon.register()
server = addon.BlenderMCPServer(host='127.0.0.1', port=9878)
server.start()
if not server.running:
    raise RuntimeError('The isolated port could not be opened')
bpy.app.driver_namespace['manila_coast_mcp_server'] = server
print('MANILA_COAST_MCP_READY', os.getpid(), bpy.data.filepath, '127.0.0.1:9878', flush=True)
