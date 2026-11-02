"""Bounded graphical preview and capture; no changes to the parent project."""
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
parser.add_argument('--demo', action='store_true', help='18-second preview, then exit')
parser.add_argument('--resolution', default='1600x900', choices=('1600x900', '1200x675'))
args = parser.parse_args()
candidates = [os.environ.get('GODOT_EXE'), shutil.which('godot'),
              str(Path.home() / 'Desktop/Godot_v4.6.1-stable_win64.exe')]
engine = next((Path(p) for p in candidates if p and Path(p).is_file()), None)
if engine is None:
    sys.exit('Godot not found. Set GODOT_EXE to your Godot 4.6 executable.')
run = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
output = ROOT / 'captures' / run
log = ROOT / 'captures' / (run + '.log')
log.parent.mkdir(exist_ok=True)
ignore = log.parent / '.gdignore'
if not ignore.exists():
    with ignore.open('x', encoding='utf-8') as stream:
        stream.write('# Rendered diagnostics are not runtime assets.\n')
mode = '--demo' if args.demo else '--capture'
marker = 'WATER_STUDY_DEMO_PASS' if args.demo else 'WATER_STUDY_CAPTURE_PASS'
command = [str(engine), '--path', str(ROOT), '--resolution', args.resolution,
           '--', mode, '--output=' + output.as_posix()]
with log.open('x', encoding='utf-8') as stream:
    process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)
    try:
        code = process.wait(timeout=180)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
        sys.exit('PREVIEW_FAILED: external 180-second watchdog')
text = log.read_text(encoding='utf-8', errors='replace')
print(text)
print('LOG', log)
if code != 0 or marker not in text or re.search(r'\bERROR\b|Shader compilation failed', text):
    sys.exit(2)
if not args.demo:
    required = ['01_water_overview.png', '02_water_motion.png', '03_shore_closeup.png',
                '04_controls.png', '05_reset.png', '06_wake_moving.png', '07_wake_fading.png',
                '08_wake_stopped.png', '09_seafloor_diagnostic.png', '10_low_angle.png', 'result.json']
    required += [f'shore_phase_{i:02d}.png' for i in range(6)]
    required += [f'foam_mask_{i:02d}.png' for i in range(3)]
    required += ['surface_fixed_00.png', 'surface_fixed_01.png', 'surface_fixed_low.png']
    if any(not (output / name).is_file() or (output / name).stat().st_size == 0 for name in required):
        sys.exit('CAPTURE_FAILED: output files missing or empty')
    result = json.loads((output / 'result.json').read_text(encoding='utf-8'))
    png_names = {name for name in required if name.endswith('.png')}
    frame_captures = result.get('frame_captures', [])
    if ({item['file'] for item in frame_captures} != png_names
            or not all(item.get('frozen') is True for item in frame_captures)):
        sys.exit('CAPTURE_FAILED: missing frozen-frame checks')
    if any(result['frame_timing'][view].get('wall_seconds', 0) < 5.0
           for view in ('overview', 'near', 'low')):
        sys.exit('CAPTURE_FAILED: insufficient wall-clock measurement duration')
    if any(result['frame_timing'][view].get('frames', 0) < 30 for view in ('overview', 'near', 'low')):
        sys.exit('CAPTURE_FAILED: insufficient frame samples')
    if result.get('study_version') != 2 or result.get('contact_objects') != 8:
        sys.exit('CAPTURE_FAILED: wrong study configuration')
    fixed = result.get('surface_diagnostics', {})
    if (fixed.get('overview_seconds') != [1.7, 3.4] or fixed.get('low_seconds') != 1.7
            or fixed.get('boat_position') != [-4.5, 0.0, 0.5]
            or fixed.get('boat_rotation') != [0.0, 0.0, 0.0] or fixed.get('wake') != 0.0):
        sys.exit('CAPTURE_FAILED: wrong fixed surface configuration')
    from PIL import Image, ImageChops, ImageStat
    phase_images = []
    foam_masks = []
    for name in required:
        if name.endswith('.png'):
            with Image.open(output / name) as image:
                image.load()
                if image.size != tuple(map(int, args.resolution.split('x'))):
                    sys.exit('CAPTURE_FAILED: screenshot size does not match requested window')
                if name.startswith('shore_phase_'):
                    phase_images.append(image.convert('RGB'))
                elif name.startswith('foam_mask_'):
                    foam_masks.append(image.convert('RGB'))
    differences = [sum(ImageStat.Stat(ImageChops.difference(phase_images[0], image)).mean) / 3
                   for image in phase_images[1:]]
    if max(differences) < 0.05:
        sys.exit('CAPTURE_FAILED: shoreline phase images are unchanged')
    foam_changes = [sum(ImageStat.Stat(ImageChops.difference(foam_masks[i], foam_masks[i + 1])).mean) / 3
                    for i in range(2)]
    if min(foam_changes) < 0.05:
        sys.exit('CAPTURE_FAILED: isolated foam did not advance and recede')
    print('ISOLATED_FOAM_CHANGES', foam_changes)
    print('SHORE_PHASE_PIXEL_CHANGES', differences, '(change check only, not visual acceptance)')
    print('OUTPUT', output)
    print(json.dumps(result['frame_timing'], indent=2))
    flagged = {view: result['frame_timing'][view]['flags'] for view in ('overview', 'near', 'low')
               if result['frame_timing'][view]['flags']}
    print('FUNCTIONAL_CAPTURE_PASS: controls and frozen images checked; not visual or performance acceptance')
    print('TIMING_REVIEW_REQUIRED' if flagged else 'TIMING_NO_FLAGS_IN_THIS_SAMPLE', json.dumps(flagged))
