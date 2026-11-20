"""Serialize code for transport; never executes authoring outside Blender MCP."""
import json, sys
from pathlib import Path
source=Path(sys.argv[1]).resolve()
code=source.read_text(encoding='utf8')
payload={'code': 'import bpy\nexec('+repr(code)+", bpy.app.driver_namespace['landmass20'])"}
source.with_suffix('.mcp.json').write_text(json.dumps(payload),encoding='utf8')
