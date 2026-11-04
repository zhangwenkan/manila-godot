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
commands = [
    ('import', [engine, '--headless', '--path', str(root), '--editor', '--import', '--quit'], 90),
    ('preview', [engine, '--path', str(root), 'res://fleet_harbor.tscn', '--resolution', '1600x900',
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
