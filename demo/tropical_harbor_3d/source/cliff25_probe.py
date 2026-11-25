import bpy, os, json, hashlib
from pathlib import Path
print(json.dumps({'pid':os.getpid(),'file':bpy.data.filepath,'dirty':bpy.data.is_dirty,'background':bpy.app.background,'sha':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'port':bpy.types.blendermcp_server.port}))
