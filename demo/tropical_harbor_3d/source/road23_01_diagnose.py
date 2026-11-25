"""Read-only contact-lock diagnosis for the road grade proposal, via owned MCP."""
import ast
from pathlib import Path
import bpy
root = Path(bpy.data.filepath).parent.parent
source = ast.parse((root / 'source/road23_01_contacts_grade.py').read_text(encoding='utf8'))
source.body = [node for node in source.body if not (
    isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
    and isinstance(node.value.func, ast.Name) and node.value.func.id == 'run')]
scope = {'__name__': 'road23_readonly_diagnosis'}
exec(compile(source, 'road23_01 definitions only', 'exec'), scope)
scope['run'](diagnose_only=True)
