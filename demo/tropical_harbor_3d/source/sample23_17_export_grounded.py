# Export explicitly affected foliage and coast assemblies using known helper.
import bpy,json,ast,math
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(bpy.data.filepath).parent.parent;OUT=ROOT/'assets/reference'
code=json.loads((ROOT/'source/reference_detail_01_materials.mcp.json').read_text(encoding='utf8'))['code']
for node in ast.parse(code).body:
 if isinstance(node,ast.FunctionDef) and node.name=='export_collection':exec(compile(ast.Module(body=[node],type_ignores=[]),'export','exec'),globals())
export_collection('Reference_Foliage','foliage.glb')
export_collection('Reference_Coast','coast.glb')
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Exported grounded foliage/coast, saved source')
