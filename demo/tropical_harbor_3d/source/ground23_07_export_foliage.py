"""Export only Reference_Foliage via the previously verified pure helper.

Executed in the owned live Blender MCP after ground23_06. The source is not
saved here; the caller owns the final save. No historical top-level code runs.
"""
import ast
import hashlib
import json
from pathlib import Path

import bpy


ROOT = Path(bpy.data.filepath).parent.parent
OUT = ROOT / 'assets/reference'
LOG = ROOT / 'captures/ground_integration_20261123'
assert bpy.data.objects['L24_GrassTuftClusters'].get('ground23_reground_grass')
assert not bpy.data.collections.get('D19_EXPORT'), 'An earlier export is still active'
helper_source = json.loads((ROOT / 'source/reference_detail_01_materials.mcp.json').read_text(encoding='utf8'))['code']
helpers = [node for node in ast.parse(helper_source).body
           if isinstance(node, ast.FunctionDef) and node.name == 'export_collection']
assert len(helpers) == 1, 'Known export_collection helper is missing/ambiguous'
exec(compile(ast.Module(body=helpers, type_ignores=[]), 'G23 isolated export helper', 'exec'), globals())
source = bpy.data.collections['Reference_Foliage']
was_hidden = source.hide_viewport
try:
    export_collection('Reference_Foliage', 'foliage.glb')
finally:
    # The original helper cleans on success; also clean temporary copies if an
    # exporter error interrupts it. Original source objects are not modified.
    temporary = bpy.data.collections.get('D19_EXPORT')
    if temporary:
        for obj in list(temporary.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(temporary)
    source.hide_viewport = was_hidden
output = OUT / 'foliage.glb'
assert output.is_file() and output.stat().st_size > 1000
report = {'asset': str(output), 'bytes': output.stat().st_size,
          'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
          'only_exported_collection': 'Reference_Foliage', 'saved_blend': False,
          'helper': 'reference_detail_01_materials.mcp.json:export_collection (function only)'}
(LOG / 'foliage_export.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
print(json.dumps(report, ensure_ascii=False))
