import bpy,importlib.util
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/shipyard_integration_20261126'
p=ROOT.parent.parent/'docs/shipyard_integration_20261126/shipyard26_final_readonly.py'
spec=importlib.util.spec_from_file_location('yard26_final_readonly',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.audit_shipyard26(29492,9881,ROOT/'source/harbor_shore_control_mcp.blend',LOG)
