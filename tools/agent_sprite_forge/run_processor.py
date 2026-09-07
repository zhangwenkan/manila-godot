#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL_ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = ROOT / "generated" / "agent_sprite_forge"

SPRITE_SCRIPT = TOOL_ROOT / "skills" / "generate2dsprite" / "scripts" / "generate2dsprite.py"
LAYOUT_SCRIPT = TOOL_ROOT / "skills" / "generate2dsprite" / "scripts" / "make_layout_guide.py"
EXTRACT_SCRIPT = TOOL_ROOT / "skills" / "generate2dmap" / "scripts" / "extract_prop_pack.py"
COMPOSE_SCRIPT = TOOL_ROOT / "skills" / "generate2dmap" / "scripts" / "compose_layered_preview.py"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="项目内 agent-sprite-forge 入口。未显式指定输出目录时，默认输出到 generated/agent_sprite_forge。"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sprite = subparsers.add_parser("sprite", help="转发到 generate2dsprite.py")
    sprite.add_argument("args", nargs=argparse.REMAINDER)

    layout = subparsers.add_parser("layout", help="转发到 make_layout_guide.py")
    layout.add_argument("args", nargs=argparse.REMAINDER)

    props = subparsers.add_parser("props", help="转发到 extract_prop_pack.py")
    props.add_argument("args", nargs=argparse.REMAINDER)

    preview = subparsers.add_parser("preview", help="转发到 compose_layered_preview.py")
    preview.add_argument("args", nargs=argparse.REMAINDER)

    return parser


def has_option(args: list[str], option: str) -> bool:
    return any(item == option or item.startswith(f"{option}=") for item in args)


def with_default_output(command: str, args: list[str]) -> list[str]:
    updated = list(args)
    if command == "sprite" and updated[:1] == ["process"] and not has_option(updated, "--output-dir"):
        updated.extend(["--output-dir", str(OUTPUT_ROOT / "sprites")])
    elif command == "props" and not has_option(updated, "--output-dir"):
        updated.extend(["--output-dir", str(OUTPUT_ROOT / "maps" / "props")])
    elif command == "layout" and not has_option(updated, "--output"):
        updated.extend(["--output", str(OUTPUT_ROOT / "raw" / "layout-guide.png")])
    elif command == "preview" and not has_option(updated, "--output"):
        updated.extend(["--output", str(OUTPUT_ROOT / "maps" / "layered-preview.png")])
    return updated


def run(script: Path, args: list[str]) -> int:
    return subprocess.call([sys.executable, str(script), *args], cwd=ROOT)


def main() -> int:
    parsed = build_parser().parse_args()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    if parsed.command == "sprite":
        return run(SPRITE_SCRIPT, with_default_output("sprite", parsed.args))
    if parsed.command == "layout":
        return run(LAYOUT_SCRIPT, with_default_output("layout", parsed.args))
    if parsed.command == "props":
        return run(EXTRACT_SCRIPT, with_default_output("props", parsed.args))
    if parsed.command == "preview":
        return run(COMPOSE_SCRIPT, with_default_output("preview", parsed.args))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
