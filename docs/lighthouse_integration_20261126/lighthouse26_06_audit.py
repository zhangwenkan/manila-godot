"""Read-only source/GLB verification through the owned Blender MCP."""
import importlib.util
from pathlib import Path
ROOT = Path('F:/马尼拉godot/manila-godot')
path = ROOT / 'docs/lighthouse_integration_20261126/lighthouse26_audit.py'
spec = importlib.util.spec_from_file_location('lighthouse26_audit_entry', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
result = module.audit_lighthouse26(
    18904, 9891,
    str(ROOT / 'demo/tropical_harbor_3d/source/harbor_shore_control_mcp.blend'),
    str(ROOT / 'demo/tropical_harbor_3d/captures/lighthouse_integration_20261126'))
assert result['passed'], 'Lighthouse source/asset audit failed'
