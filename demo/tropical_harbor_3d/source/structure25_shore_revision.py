"""Run the reviewed whole-shore correction in the owned GUI only."""
import bpy,json,time
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/terrain_structure_20261123'
started=time.time()
for stage_filename25 in ['structure25_grade_review.py','structure23_11_finalize_surface.py','structure25_export_review.py','structure23_09_final_check.py']:
    (LOG/'revision_progress.json').write_text(json.dumps({'phase':stage_filename25,'state':'running','started':started,'time':time.time()}),encoding='utf8')
    exec(compile((ROOT/'source'/stage_filename25).read_text(encoding='utf8'),stage_filename25,'exec'),globals())
    if stage_filename25=='structure25_grade_review.py':
        assert json.loads((LOG/'structure_audit.json').read_text(encoding='utf8'))['technical_pass']
    (LOG/'revision_progress.json').write_text(json.dumps({'phase':stage_filename25,'state':'completed','started':started,'time':time.time()}),encoding='utf8')
print('WHOLE_SHORE_REVISION_SAVED_AND_VERIFIED')
