import bpy,importlib.util,json
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/shipyard_integration_20261126'
path=ROOT.parent.parent/'docs/shipyard_integration_20261126/shipyard26_export.py'
spec=importlib.util.spec_from_file_location('yard26_export',path);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
m=json.loads((LOG/'mutation.json').read_text(encoding='utf8'))
helper.export_shipyard26(expected_pid=29492,expected_port=9881,expected_source=ROOT/'source/harbor_shore_control_mcp.blend',log_path=LOG,targets=m['targets'],allowed_changed_names=m['allowed_changed_names'])
