"""Bounded main-scene art capture; add --background for an invisible Windows desktop.

Layout review also checks camera/arrival behavior. Visual acceptance is separate.
"""
from datetime import datetime
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys
from capture_process import run_capture

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
root = Path(__file__).resolve().parents[1]
project = root.parents[1]
candidates = [os.environ.get('GODOT_EXE'), shutil.which('godot'),
              str(Path.home() / 'Desktop/Godot_v4.6.1-stable_win64.exe')]
engine = next((p for p in candidates if p and Path(p).is_file()), None)
if not engine:
    sys.exit('Godot not found. Set GODOT_EXE.')
background = '--background' in sys.argv
if background:
    sys.argv.remove('--background')
mode = sys.argv[1] if len(sys.argv) > 1 else 'preview'
output = root / 'captures' / ('art_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
output.mkdir(parents=True, exist_ok=False)
user = ['--art-preview', '--art-output=' + output.as_posix()]
if mode in ('rebuild', 'rebuild-sample', 'rebuild-composition', 'rebuild-clay'):
    user.extend(['--reference-rebuild', '--local-voyage-review'])
    if mode == 'rebuild-sample':
        user.append('--reference-rebuild-sample')
    if mode == 'rebuild-composition':
        user.append('--reference-composition-study')
    if mode == 'rebuild-clay':
        user.append('--reference-landform-clay')
elif mode == 'diagnose':
    user.append('--art-diagnose=hull')
elif mode in ('shipyard', 'shipyard-sample', 'shipyard-compare', 'environment'):
    user.append('--shipyard-review')
    if mode == 'environment':
        user.append('--coastal-environment-review')
    if mode == 'shipyard-compare':
        user.append('--shipyard-compare')
    if mode == 'shipyard-sample':
        user.append('--shipyard-sample')
elif mode == 'coast':
    user.append('--coast-review')
elif mode == 'coast-light':
    user.extend(['--coast-review', '--coast-light-study'])
elif mode == 'surface':
    user.extend(['--coast-review', '--surface-review'])
elif mode in ('terminal', 'terminal-structure'):
    user.extend(['--coast-review', '--terminal-review'])
    if mode == 'terminal-structure':
        user.append('--terminal-structure')
elif mode in ('layout', 'layout-motion', 'voyage', 'voyage-motion', 'voyage-frames', 'composition'):
    user.append('--local-voyage-review')
    if mode == 'composition':
        user.append('--coastal-composition-study')
    if mode == 'voyage-frames':
        user.append('--local-voyage-frames')
    if mode.endswith('-motion'):
        user.append('--local-voyage-motion')
elif mode == 'terminal-life':
    user.append('--terminal-life-review')
elif mode == 'terminal-life-perf':
    user.append('--terminal-life-perf')
elif mode in ('water-profile', 'water-profile-diagnose', 'water-profile-compare', 'water-profile-stability'):
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
elif mode in ('reference-stills', 'reference-idle', 'reference-sail', 'reference-detail', 'reference-reflection', 'reference-layout'):
    user.append('--reference-review=' + mode.removeprefix('reference-'))
elif mode != 'preview':
    sys.exit('Unknown art mode: ' + mode)
resolution = sys.argv[2] if len(sys.argv) > 2 else '1600x900'
if resolution not in ('1600x900', '2560x1440'):
    sys.exit('Resolution must be 1600x900 or 2560x1440')
commands = [
    ('import', [engine, '--headless', '--path', str(project), '--editor', '--import', '--quit'], 120),
    ('preview', [engine, '--path', str(project), '--resolution', resolution,
                 '--'] + user, 110 if '--local-voyage-review' in user else 70),
]
for label, command, timeout in commands:
    log = output / (label + '.log')
    with log.open('x', encoding='utf-8') as stream:
        try:
            code = run_capture(command, stream, timeout, background=background)
        except subprocess.TimeoutExpired:
            sys.exit(f'ART_PREVIEW_TIMEOUT: {label}; {log}')
    text = log.read_text(encoding='utf-8', errors='replace')
    if code != 0 or re.search(r'\bERROR\b|SCRIPT ERROR', text):
        print(text)
        sys.exit(f'ART_PREVIEW_FAILED: {label}; {log}')
result = json.loads((output / 'art_result.json').read_text(encoding='utf-8'))
print('ART_PREVIEW_SAVED', len(result['frames']), 'images')
print('OUTPUT', output)
if mode in ('layout', 'voyage', 'rebuild'):
    print('LOCAL_NAVIGATION_CHECKS', result.get('checks', 0))
    print('This checks the camera/navigation prototype, not the complete Manila rules or visual acceptance.')
else:
    print('Art review only. No gameplay regression or visual acceptance claimed.')
