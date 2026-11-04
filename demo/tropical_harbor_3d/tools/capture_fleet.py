"""Run the real three-ship scene, exercise inputs, capture evidence, and exit."""
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parents[1]
parser = ArgumentParser(description=__doc__)
parser.add_argument('--resolution', default='1600x900', choices=('1600x900', '1200x675'))
args = parser.parse_args()
candidates = [os.environ.get('GODOT_EXE'), shutil.which('godot'),
              str(Path.home() / 'Desktop/Godot_v4.6.1-stable_win64.exe')]
engine = next((Path(p) for p in candidates if p and Path(p).is_file()), None)
if engine is None:
    sys.exit('Godot not found. Set GODOT_EXE.')
run = 'fleet_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f')
output = ROOT / 'captures' / run
log = ROOT / 'captures' / (run + '.log')
log.parent.mkdir(exist_ok=True)
ignore = log.parent / '.gdignore'
if not ignore.exists():
    ignore.write_text('# Local graphical evidence, not runtime resources.\n', encoding='utf-8')
command = [str(engine), '--path', str(ROOT), 'res://fleet_harbor.tscn', '--resolution', args.resolution,
           '--', '--fleet-capture', '--output=' + output.as_posix()]
with log.open('x', encoding='utf-8') as stream:
    process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)
    try:
        code = process.wait(timeout=180)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
        sys.exit(f'FLEET_FAILED: external watchdog; log {log}')
text = log.read_text(encoding='utf-8', errors='replace')
print(text)
print('LOG', log)
if code != 0 or 'FLEET_CAPTURE_PASS' not in text or re.search(r'\bERROR\b|Shader compilation failed', text):
    sys.exit(2)
result = json.loads((output / 'result.json').read_text(encoding='utf-8'))
required = ['01_parallel_overview', '02_jade_full_crew', '03_extreme_overview',
            '04_three_wakes', '05_moved_ship_dispatch', '06_single_wake',
            '07_timber_and_broken_pier', '08_fleet_water_no_wake',
            '09_reference_water_no_wake', '10_fleet_water_contact_free',
            '11_completed_voyage', '12_new_cargo_voyage', '13_open_hull_structure',
            'cargo_jade', 'cargo_silk', 'cargo_ginseng', 'cargo_nutmeg']
frames = result.get('frames', [])
if {f['file'] for f in frames} != {name + '.png' for name in required} or not all(f.get('frozen') for f in frames):
    sys.exit('FLEET_FAILED: missing frozen captures')
from PIL import Image, ImageChops
for name in required:
    with Image.open(output / (name + '.png')) as image:
        image.load()
        if image.size != tuple(map(int, args.resolution.split('x'))):
            sys.exit('FLEET_FAILED: incorrect image dimensions')
with Image.open(output / '09_reference_water_no_wake.png') as a, Image.open(output / '10_fleet_water_contact_free.png') as b:
    if ImageChops.difference(a.convert('RGB'), b.convert('RGB')).getbbox() is not None:
        sys.exit('FLEET_FAILED: fleet shader changed the contact-free no-wake image')
for view, values in result['timing'].items():
    if values['wall_seconds'] < 5.0 or values['frames'] < 30:
        sys.exit('FLEET_FAILED: insufficient timing samples')
    values['review_required'] = (values['focus_fraction'] < .95 or values['minimized_frames'] > 0
                                 or values['drawn_frames'] < values['frames'] * .95 or values['p95_ms'] > 33.333)
print('FLEET_FUNCTIONAL_PASS checks=', result['checks'])
print('NO_WAKE_SHADER_EQUIVALENCE_PASS')
print('TIMING', json.dumps(result['timing'], ensure_ascii=False))
print('OUTPUT', output)
print('Visual acceptance remains a separate review of the images.')
