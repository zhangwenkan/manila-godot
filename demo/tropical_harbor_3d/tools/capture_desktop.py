"""Compatibility command: capture the same harbor used by F5."""
from pathlib import Path
import subprocess
import sys

raise SystemExit(subprocess.call([sys.executable, str(Path(__file__).with_name("capture_art.py"))]))
