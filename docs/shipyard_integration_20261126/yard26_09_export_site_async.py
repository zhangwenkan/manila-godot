"""Queue the site-only export in Blender's main loop to avoid transport timeout."""
import bpy,os,json,importlib.util,traceback
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/shipyard_integration_20261126'
assert os.getpid()==29492 and bpy.types.blendermcp_server.port==9881
assert (LOG/'hut_support_revision.json').exists()
def run_site_export():
 try:
  p=ROOT.parent.parent/'docs/shipyard_integration_20261126/shipyard26_export.py'
  spec=importlib.util.spec_from_file_location('yard26_export_site',p);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
  m=json.loads((LOG/'mutation.json').read_text(encoding='utf8'))
  r=helper.export_shipyard26(29492,9881,ROOT/'source/harbor_shore_control_mcp.blend',LOG,['Reference_Terrain','Reference_Foliage','Reference_GroundCover'],m['allowed_changed_names'])
  (LOG/'site_export_async_done.json').write_text(json.dumps({'status':'completed','source_sha256':r['source_sha256']}),encoding='utf8')
 except Exception:
  (LOG/'site_export_async_done.json').write_text(json.dumps({'status':'failed','error':traceback.format_exc()}),encoding='utf8')
 return None
bpy.app.timers.register(run_site_export,first_interval=.5)
print('Queued site-only export in owned Blender main loop; inspect site_export_async_done.json before further MCP operations.')
