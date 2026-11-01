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
                '04_controls.png', '05_reset.png', 'result.json']
    if any(not (output / name).is_file() or (output / name).stat().st_size == 0 for name in required):
        sys.exit('CAPTURE_FAILED: output files missing or empty')
    result = json.loads((output / 'result.json').read_text(encoding='utf-8'))
    if any(result['frame_timing'][view].get('frames', 0) < 30 for view in ('overview', 'near')):
        sys.exit('CAPTURE_FAILED: insufficient frame samples')
    print('OUTPUT', output)
    print(json.dumps(result['frame_timing'], indent=2))
