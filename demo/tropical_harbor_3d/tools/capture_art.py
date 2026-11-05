"""Short, bounded art-only preview; does not exercise gameplay or invoke Blender."""
from datetime import datetime
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
root = Path(__file__).resolve().parents[1]
project = root.parents[1]
candidates = [os.environ.get('GODOT_EXE'), shutil.which('godot'),
              str(Path.home() / 'Desktop/Godot_v4.6.1-stable_win64.exe')]
engine = next((p for p in candidates if p and Path(p).is_file()), None)
if not engine:
    sys.exit('Godot not found. Set GODOT_EXE.')
mode = sys.argv[1] if len(sys.argv) > 1 else 'preview'
output = root / 'captures' / ('art_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
output.mkdir(parents=True, exist_ok=False)
user = ['--art-preview', '--art-output=' + output.as_posix()]
if mode == 'diagnose':
    user.append('--art-diagnose=hull')
elif mode in ('water-profile', 'water-profile-diagnose', 'water-profile-compare'):
    profile_mode = mode.removeprefix('water-profile').lstrip('-') or 'views'
    user.append('--water-profile=' + profile_mode)
    if profile_mode == 'compare':
        if len(sys.argv) < 4:
            sys.exit('Pass resolution and a saved baseline source directory for comparison.')
        user.append('--profile-baseline=' + Path(sys.argv[3]).resolve().as_posix())
elif mode in ('water', 'water-diagnose'):
    user.append('--water-review')
    if mode == 'water-diagnose':
        user.append('--water-diagnose')
elif mode in ('reference-stills', 'reference-idle', 'reference-sail', 'reference-detail', 'reference-reflection'):
    user.append('--reference-review=' + mode.removeprefix('reference-'))
elif mode != 'preview':
    sys.exit('Unknown art mode: ' + mode)
resolution = sys.argv[2] if len(sys.argv) > 2 else '1600x900'
if resolution not in ('1600x900', '2560x1440'):
    sys.exit('Resolution must be 1600x900 or 2560x1440')
commands = [
    ('import', [engine, '--headless', '--path', str(project), '--editor', '--import', '--quit'], 120),
    ('preview', [engine, '--path', str(project), '--resolution', resolution,
                 '--'] + user, 70),
]
for label, command, timeout in commands:
    log = output / (label + '.log')
    with log.open('x', encoding='utf-8') as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
            sys.exit(f'ART_PREVIEW_TIMEOUT: {label}; {log}')
    text = log.read_text(encoding='utf-8', errors='replace')
    if code != 0 or re.search(r'\bERROR\b|SCRIPT ERROR', text):
        print(text)
        sys.exit(f'ART_PREVIEW_FAILED: {label}; {log}')
result = json.loads((output / 'art_result.json').read_text(encoding='utf-8'))
print('ART_PREVIEW_SAVED', len(result['frames']), 'images')
print('OUTPUT', output)
print('Art review only. No gameplay regression or visual acceptance claimed.')
