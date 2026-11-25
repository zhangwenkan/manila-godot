"""Export this round's already-transformed island in the owned GUI Blender."""
import bpy, importlib.util, json
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/pirate_orientation_20261125'
assert (LOG/'transform.json').exists()
path=ROOT.parent.parent/'docs/pirate_orientation_20261125/pirate_orientation25_export.py'
spec=importlib.util.spec_from_file_location('orientation_export',path)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
expected=[[0,-1,0,-17.5],[1,0,0,14],[0,0,1,0],[0,0,0,1]]
result=helper.export_pirate_orientation25(38548,9881,bpy.data.filepath,LOG,expected)
print(json.dumps(result,default=str))
