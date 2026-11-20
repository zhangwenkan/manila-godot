"""Connection only; all authoring is sent through the real Blender MCP server."""
import bpy, importlib.util, os, sys
from pathlib import Path
expected = Path(__file__).with_name('harbor_landform_mass_mcp.blend').resolve()
assert Path(bpy.data.filepath).resolve() == expected
spec = importlib.util.spec_from_file_location('manila_landform_mcp', 'D:/一些好玩的例子/blender-mcp/addon.py')
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
addon.register()
server = addon.BlenderMCPServer(host='127.0.0.1', port=9879)
server.start()
assert server.running
bpy.app.driver_namespace['manila_landform_server'] = server
print('MANILA_LANDFORM_MCP_READY', os.getpid(), bpy.data.filepath, flush=True)
