"""Read-only audit of this round's saved source and rigid island placement."""
import bpy, importlib.util
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/pirate_orientation_20261125'
path=ROOT.parent.parent/'docs/pirate_orientation_20261125/pirate_orientation25_audit.py'
spec=importlib.util.spec_from_file_location('orientation_audit',path)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
expected=[[0,-1,0,-17.5],[1,0,0,14],[0,0,1,0],[0,0,0,1]]
result=helper.audit_pirate_orientation25(38548,9881,bpy.data.filepath,LOG,expected,ROOT/'captures/pirate_island_20261125/build.json',-10.5)
assert result['passed'],result['failed_checks']
