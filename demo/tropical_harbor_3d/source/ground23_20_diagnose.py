"""Read-only live-scene precommit diagnostic for continuous shoulders.

Imports definitions only. No Blender geometry, object visibility, materials,
exports or source-save state is modified. JSON and NPZ diagnostics go to the
current ground integration capture folder.
"""
import ast
from pathlib import Path
import bpy

path=Path(bpy.data.filepath).parent/'ground23_20_integrated_shoulders.py'
source=ast.parse(path.read_text(encoding='utf8'))
definitions=[node for node in source.body
             if isinstance(node,(ast.Import,ast.ImportFrom,ast.FunctionDef))]
namespace={}
exec(compile(ast.Module(body=definitions,type_ignores=[]),str(path),'exec'),namespace)
namespace['run'](diagnose_only=True)
