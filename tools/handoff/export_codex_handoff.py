"""Export local project chats, working files, local Blender sources and portable Windows tools.

No Codex database is modified or copied wholesale. Exports are private and stay outside Git.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import tomllib
import zipfile
def ZoneInfo(name):
    assert name == 'Asia/Shanghai'
    return timezone(timedelta(hours=8), name)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PROJECT_ID = "90132340-352d-4952-8478-9c6084c6b5aa"
SKIP_DIRS = {".git", ".godot", ".claude", ".workbuddy", ".workbuddy-ai", ".venv",
             "node_modules", "__pycache__", ".cache", ".pytest_cache", "tmp"}
SECRET_NAMES = {"auth.json", "auth.json.bak", ".env", ".env.local", ".env.production"}
SECRET_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_-]{20,}|\bBearer[ \t]+[A-Za-z0-9._~+/=-]{16,}", re.I)
CREDENTIAL_PATTERN = re.compile(
    r'((?:\\?["\'])(?:api[_-]?key|access_token|refresh_token|password)(?:\\?["\'])\s*[:=]\s*(?:\\?["\']))([^"\r\n\\]+)', re.I)
REDACTIONS = Counter()


def log(*parts):
    print(*parts, flush=True)


def scrub(text):
    text, count = SECRET_PATTERN.subn("[REDACTED_CREDENTIAL]", text)
    text, count2 = CREDENTIAL_PATTERN.subn(lambda m: m[1] + "[REDACTED_CREDENTIAL]", text)
    REDACTIONS["common_credentials"] += count + count2
    return text


def safe_object(value):
    if isinstance(value, str):
        return scrub(value)
    if isinstance(value, list):
        return [safe_object(x) for x in value]
    if isinstance(value, dict):
        return {k: ("[REDACTED_CREDENTIAL]" if k.lower() in
                    {"api_key", "apikey", "access_token", "refresh_token", "password"}
                    and isinstance(v, str) and v else safe_object(v)) for k, v in value.items()}
    return value


def json_file(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def digest_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def files_in(root):
    for base, directories, files in os.walk(root):
        directories[:] = sorted(d for d in directories if d not in SKIP_DIRS)
        for name in sorted(files):
            path = Path(base) / name
            if name in SECRET_NAMES or name.endswith(".pyc"):
                continue
            yield path


def git(*arguments, binary=False):
    return subprocess.check_output(["git", "-C", str(ROOT), *arguments],
                                   text=not binary, encoding=None if binary else "utf-8")


def related(meta):
    return "manila-godot" in str(meta.get("cwd", "")).lower() or meta.get("project_id") == PROJECT_ID


def connect_readonly(path):
    connection = sqlite3.connect("file:" + path.as_posix() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("BEGIN")
    return connection


def strip_large_media(value):
    """Keep readable files small; full media data remains in the JSONL archives."""
    if isinstance(value, str):
        if value.startswith("data:") and ";base64," in value:
            return "[embedded media retained in structured/raw history]"
        return value
    if isinstance(value, list):
        return [strip_large_media(v) for v in value]
    if isinstance(value, dict):
        return {k: strip_large_media(v) for k, v in value.items()}
    return value


def item_text(item):
    parts = []
    for block in item.get("content", []):
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
        elif block.get("type") in {"image", "input_image", "localImage"}:
            parts.append("[图片附件；见完整结构化记录及附件索引]")
    return "\n\n".join(parts)


def export_history(home, out):
    history_dir = out / "history"
    for name in ["readable", "structured", "raw", "attachments"]:
        (history_dir / name).mkdir(parents=True, exist_ok=True)
    state = connect_readonly(home / "state_5.sqlite")
    hist = connect_readonly(home / "thread_history_1.sqlite")
    all_meta = {r["id"]: dict(r) for r in state.execute("select * from threads")}
    selected = {k for k, v in all_meta.items() if related(v)}
    ui_path = ROOT / "tools/codex_handoff_ui_threads.json"
    ui = json.loads(ui_path.read_text(encoding="utf-8")) if ui_path.exists() else []
    ui_meta = {r["id"]: r for r in ui}
    selected.update(ui_meta)
    raw_paths = {}
    raw_headers = {}
    for folder in ["sessions", "archived_sessions"]:
        for path in (home / folder).rglob("*.jsonl"):
            try:
                with path.open(encoding="utf-8") as stream:
                    first = json.loads(stream.readline())
                meta = first.get("payload", {})
                thread_id = meta.get("id") or meta.get("session_id")
                if thread_id:
                    raw_paths.setdefault(thread_id, []).append(path)
                    raw_headers[thread_id] = meta
                    if related(meta):
                        selected.add(thread_id)
            except (OSError, ValueError):
                continue
    edges = [dict(r) for r in state.execute("select * from thread_spawn_edges")]
    changed = True
    while changed:
        before = len(selected)
        for edge in edges:
            if edge["parent_thread_id"] in selected:
                selected.add(edge["child_thread_id"])
        for key, meta in all_meta.items():
            if meta.get("attached_thread_parent_id") in selected:
                selected.add(key)
        changed = before != len(selected)
    selected_edges = [e for e in edges if e["parent_thread_id"] in selected]
    child_ids = {e["child_thread_id"] for e in selected_edges}
    attachment_refs = set()
    coverage = []
    index_lines = ["# 项目聊天存档\n", "本机可读取范围，按创建时间排列。原始日志缺失不代表结构化记录缺失。\n",
                   "| 日期 | 会话原题/ID | 类型 | 用户/助手消息 | 原始日志 |", "| --- | --- | --- | --- | --- |"]
    ordered = sorted(selected, key=lambda k: all_meta.get(k, {}).get("created_at", 0))
    for number, thread_id in enumerate(ordered, 1):
        meta = all_meta.get(thread_id, raw_headers.get(thread_id, {}))
        title = ui_meta.get(thread_id, {}).get("title") or meta.get("title") or meta.get("first_user_message") or thread_id
        turns = [dict(r) for r in hist.execute("select * from thread_turns where thread_id=? order by rollout_ordinal", (thread_id,))]
        items = [dict(r) for r in hist.execute("select * from thread_items where thread_id=? order by rollout_ordinal", (thread_id,))]
        kind_counts = Counter(r["item_type"] for r in items)
        role = "子代理" if thread_id in child_ids or meta.get("agent_path") else "主会话"
        date = datetime.fromtimestamp(meta.get("created_at", 0), ZoneInfo("Asia/Shanghai")).isoformat()
        md = [f"# {scrub(title)}\n", f"会话：{thread_id}  |  创建时间：{date}  |  类型：{role}\n",
              "以本机历史数据库的用户/助手消息为阅读主体；命令、工具调用和输出放入可展开区域，完整记录另存 JSONL。\n"]
        json_file(history_dir / "structured" / (thread_id + ".meta.json"),
                  safe_object({"metadata": meta, "ui_listing": ui_meta.get(thread_id), "turns": turns}))
        with (history_dir / "structured" / (thread_id + ".items.jsonl")).open("w", encoding="utf-8") as target:
            last_turn = None
            for row in items:
                item = safe_object(json.loads(row["item_json"]))
                target.write(json.dumps({**{k: v for k, v in row.items() if k != "item_json"}, "item": item},
                                        ensure_ascii=False) + "\n")
                if row["turn_id"] != last_turn:
                    md.append("\n## 轮次 " + row["turn_id"] + "\n")
                    last_turn = row["turn_id"]
                typ = item.get("type", row["item_type"])
                if typ == "userMessage":
                    text = item_text(item)
                    md.extend(["\n### 用户\n", text, "\n"])
                    for line in text.splitlines():
                        match = re.match(r"##\s+.+?:\s+([A-Za-z]:[/\\].+?)\s*$", line)
                        if match:
                            attachment_refs.add(match[1])
                elif typ == "agentMessage":
                    phase = item.get("phase", "")
                    md.extend(["\n### 助手 " + phase + "\n", item.get("text", ""), "\n"])
                elif typ == "reasoning":
                    # Never promote internal reasoning to the conversation transcript.
                    continue
                else:
                    compact = json.dumps(strip_large_media(item), ensure_ascii=False, indent=2)
                    md.append("\n<details><summary>" + html.escape(typ) + "</summary><pre>" +
                              html.escape(compact) + "</pre></details>\n")
        original_logs = raw_paths.get(thread_id, [])
        if not original_logs and meta.get("rollout_path"):
            candidate = Path(meta["rollout_path"])
            if candidate.is_file():
                original_logs = [candidate]
        raw_reports = []
        for raw_no, raw_path in enumerate(original_logs):
            dest = history_dir / "raw" / (thread_id + (f"_{raw_no}" if raw_no else "") + ".jsonl")
            original_digest = hashlib.sha256()
            with raw_path.open("rb") as source, dest.open("wb") as target:
                limit = raw_path.stat().st_size
                consumed = 0
                while consumed < limit:
                    line = source.readline(limit - consumed)
                    if not line:
                        break
                    consumed += len(line)
                    original_digest.update(line)
                    try:
                        text = line.decode("utf-8")
                        target.write(scrub(text).encode("utf-8"))
                    except UnicodeError:
                        target.write(line)
            raw_reports.append({"source": str(raw_path), "export": dest.relative_to(out).as_posix(),
                                "source_snapshot_sha256": original_digest.hexdigest(), "export_sha256": digest_file(dest)})
        caveats = []
        if not raw_reports:
            caveats.append("原始 rollout 已不在本机；保留可读取的结构化记录")
        if not kind_counts["agentMessage"]:
            caveats.append("没有可读取的助手回答；不臆造补全")
        if not items:
            caveats.append("无结构化消息；仅有元数据或原始日志")
        coverage.append({"id": thread_id, "title": title, "created": date, "role": role,
                         "counts": dict(kind_counts), "turns": len(turns), "raw_logs": raw_reports, "caveats": caveats})
        (history_dir / "readable" / (thread_id + ".md")).write_text("\n".join(md), encoding="utf-8")
        label = scrub(title).replace("|", "\\|").replace("\n", " ")[:120]
        index_lines.append(f"| {date[:10]} | [{label}](readable/{thread_id}.md) | {role} | "
                           f"{kind_counts['userMessage']}/{kind_counts['agentMessage']} | "
                           f"{'有' if raw_reports else '缺失，见结构化记录'} |")
        log("CHAT", number, "/", len(ordered), thread_id, "items", len(items), "raw", len(raw_reports))
    state.close()
    hist.close()
    copied_attachments = []
    attachment_refs.add(str(Path.home() / "Downloads/Create_stock_value_board_3e7c69c9_2K.jpg"))
    for source_text in sorted(attachment_refs):
        source = Path(source_text)
        report = {"source": source_text, "available": source.is_file()}
        if source.is_file():
            try:
                report["project_relative"] = source.resolve().relative_to(ROOT).as_posix()
            except ValueError:
                safe_name = hashlib.sha256(source_text.encode("utf-8")).hexdigest()[:10] + "_" + source.name
                dest = history_dir / "attachments" / safe_name
                shutil.copy2(source, dest)
                report["export"] = dest.relative_to(out).as_posix()
                report["sha256"] = digest_file(dest)
        copied_attachments.append(report)
    json_file(history_dir / "attachment_index.json", copied_attachments)
    portable_media = {r["source"].replace("\\", "/").lower(): "../../" + r["export"]
                      for r in copied_attachments if r.get("export")}
    root_prefix = ROOT.as_posix().lower() + "/"
    link_pattern = re.compile(r"\]\((<?)([A-Za-z]:[^)\r\n]+?)(>?)\)")
    def relocate_link(match):
        normalized = match[2].replace("\\", "/")
        target = ("../../manila-godot/" + normalized[len(root_prefix):]
                  if normalized.lower().startswith(root_prefix) else portable_media.get(normalized.lower()))
        return "](<" + target + ">)" if target else match[0]
    for markdown in (history_dir / "readable").glob("*.md"):
        markdown.write_text(link_pattern.sub(relocate_link, markdown.read_text(encoding="utf-8")), encoding="utf-8")
    json_file(history_dir / "coverage.json", {"generated": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
              "selection": "project_id, current/old project cwd, UI listing, rollout headers, child-thread edges",
              "threads": coverage, "edges": selected_edges, "redactions": dict(REDACTIONS)})
    index_lines.extend(["\n## 覆盖说明\n", f"共 {len(coverage)} 会话，{len(child_ids)} 个父子关系中的子代理。",
                        "逐会话缺失/无回答情况见 coverage.json。原始格式日志不作为可保证导入侧栏的格式。",
                        "Markdown 不展开内部推理；工具记录、图片数据在结构化及原始格式存档中保留。"])
    (history_dir / "INDEX.md").write_text("\n".join(index_lines), encoding="utf-8")
    return coverage


def write_archive(path, entries, manifest):
    total = sum(source.stat().st_size for source, _ in entries)
    processed = 0
    last = time.monotonic()
    with zipfile.ZipFile(path, "w", allowZip64=True) as archive:
        for source, relative in entries:
            extension = source.suffix.lower()
            compressed = extension not in {".png", ".jpg", ".jpeg", ".gif", ".mp4", ".webm", ".zip", ".whl", ".blend", ".blend1"}
            info = zipfile.ZipInfo(relative, time.localtime(source.stat().st_mtime)[:6])
            info.compress_type = zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED
            info._compresslevel = 1
            checksum = hashlib.sha256()
            size = 0
            with source.open("rb") as stream, archive.open(info, "w", force_zip64=True) as target:
                for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                    checksum.update(block)
                    target.write(block)
                    size += len(block)
            manifest.append({"path": relative, "bytes": size, "sha256": checksum.hexdigest(), "archive": path.name})
            processed += size
            if time.monotonic() - last > 12:
                log("PACK", path.name, f"{processed / 1e9:.2f}/{total / 1e9:.2f} GB", relative)
                last = time.monotonic()
    log("PACKED", path.name, len(entries), "files", f"{path.stat().st_size / 1e9:.2f} GB")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--godot", type=Path, default=Path.home() / "Desktop/Godot_v4.6.1-stable_win64.exe")
    parser.add_argument("--blender", type=Path, default=Path(shutil.which("blender") or "blender.exe").resolve().parent)
    parser.add_argument("--mcp-root", type=Path, default=Path("D:/一些好玩的例子/blender-mcp"))
    parser.add_argument("--wheelhouse", type=Path)
    args = parser.parse_args()
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    out = (args.output or ROOT.parent / ("manila-codex-handoff-" + now.strftime("%Y%m%d-%H%M%S"))).resolve()
    if out.is_relative_to(ROOT):
        raise SystemExit("Export must be outside the Git project.")
    out.mkdir(parents=True, exist_ok=False)
    snapshot = {"created": now.isoformat(), "head": git("rev-parse", "HEAD").strip(),
                "branch": git("branch", "--show-current").strip(), "origin": git("remote", "get-url", "origin").strip(),
                "status": git("status", "--porcelain=v1"), "tracked": git("ls-files", "-z").split("\0"),
                "source_root": str(ROOT)}
    log("OUTPUT", out)
    json_file(out / "git/snapshot.json", snapshot)
    (out / "git/staged.patch").write_bytes(git("diff", "--cached", "--binary", binary=True))
    (out / "git/unstaged.patch").write_bytes(git("diff", "--binary", binary=True))
    subprocess.run(["git", "-C", str(ROOT), "bundle", "create", str(out / "git/git-history.bundle"), "--all"], check=True)
    subprocess.run(["git", "-C", str(ROOT), "bundle", "verify", str(out / "git/git-history.bundle")], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log("GIT_HISTORY_SAVED")
    coverage = export_history(args.codex_home, out)
    shutil.copy2(ROOT / "docs/换电脑接续.md", out / "START_HERE.md")
    prompt = ("请接续这个马尼拉 Godot 项目。先读 docs/换电脑接续.md、AGENTS.md 和 "
              "docs/harbor-reference-rebuild-20261116.md，然后核对工作区与当前主场景。"
              "11月16日参考图重建首版已接入，仍待整屏视觉评价；不要当作已验收。"
              "保持唯一主场景、三船同步、独立航道、真实A/B/C和独立Blender MCP制作约束。"
              "历史聊天在项目旁边的 history/INDEX.md，按需查逐会话记录，不要一次重载全部图片。"
              "旧原始日志缺失处见 history/coverage.json。UI暂不制作，先总结当前实际状态和剩余宏观问题，"
              "再根据我接下来的反馈继续。\n")
    (out / "resume_prompt.txt").write_text(prompt, encoding="utf-8")
    for name in ["open_project.ps1", "setup_tools.ps1", "restore_git.ps1", "verify_package.py"]:
        shutil.copy2(HERE / name, out / name)
    env_dir = out / "environment"
    env_dir.mkdir(exist_ok=True)
    (env_dir / "requirements.txt").write_text("mcp>=1.26.0,<2\nhttpx>=0.27.0\nPillow\nnumpy\n", encoding="utf-8")
    config = tomllib.loads((args.codex_home / "config.toml").read_text(encoding="utf-8"))
    json_file(env_dir / "codex-settings-summary.json",
              {"model": config.get("model"), "model_provider": config.get("model_provider"),
               "model_reasoning_effort": config.get("model_reasoning_effort"),
               "note": "Reauthenticate/configure provider on the new computer. No secrets or full app state were exported."})
    subprocess.run([str(args.blender / "blender.exe"), "--version"], check=True,
                   stdout=(env_dir / "blender-version.txt").open("w", encoding="utf-8"))
    (env_dir / "python-version.txt").write_text(sys.version + "\n" + sys.base_prefix, encoding="utf-8")
    core = [(p, p.relative_to(out).as_posix()) for p in files_in(out)]
    evidence = []
    newest_prefixes = ("demo/tropical_harbor_3d/captures/art_20261116_161256_644127/",
                       "demo/tropical_harbor_3d/captures/reference_rebuild_20261116/")
    for source in files_in(ROOT):
        rel = source.relative_to(ROOT).as_posix()
        if "/captures/" in rel and not rel.startswith(newest_prefixes):
            evidence.append((source, "manila-godot/" + rel))
        else:
            core.append((source, "manila-godot/" + rel))
    import_cache = ROOT / '.godot/imported'
    if import_cache.exists():
        for source in files_in(import_cache):
            core.append((source, 'manila-godot/.godot/imported/' + source.relative_to(import_cache).as_posix()))
    for source in files_in(Path(sys.base_prefix)):
        core.append((source, "runtime/python/" + source.relative_to(sys.base_prefix).as_posix()))
    for source in files_in(args.blender):
        core.append((source, "runtime/blender/" + source.relative_to(args.blender).as_posix()))
    core.append((args.godot, "runtime/" + args.godot.name))
    mcp_top = {"addon.py", "pyproject.toml", "uv.lock", "LICENSE", "README.md", ".python-version"}
    for source in files_in(args.mcp_root):
        rel = source.relative_to(args.mcp_root).as_posix()
        if rel.startswith("src/") or rel in mcp_top:
            core.append((source, "environment/blender-mcp/" + rel))
    skill_root = args.codex_home / "skills/harbor-blender-craft"
    for source in files_in(skill_root):
        core.append((source, "environment/skills/harbor-blender-craft/" + source.relative_to(skill_root).as_posix()))
    research_root = Path('D:/steam/steamapps/common/I Just Wanted to Fish Demo/analysis')
    if research_root.exists():
        for source in files_in(research_root):
            if source.suffix.lower() in {'.md', '.txt', '.py'}:
                core.append((source, 'reference_research/' + source.relative_to(research_root).as_posix()))
    lfs_root = ROOT / ".git/lfs/objects"
    if lfs_root.exists():
        for source in files_in(lfs_root):
            core.append((source, "git/lfs-objects/" + source.relative_to(lfs_root).as_posix()))
    wheelhouse = args.wheelhouse
    if wheelhouse is None:
        wheelhouse = out / "environment/wheelhouse"
        wheelhouse.mkdir(parents=True)
        subprocess.run([sys.executable, "-m", "pip", "download", "--dest", str(wheelhouse),
                        "-r", str(env_dir / "requirements.txt")], check=True)
    for source in files_in(wheelhouse):
        core.append((source, "environment/wheelhouse/" + source.name))
    # A few historical tracked files live in normally skipped cache/tool directories.
    # Preserve them so restoring Git does not invent deletions in the working tree.
    already_packed = {name for _, name in core + evidence}
    for relative in snapshot['tracked']:
        source = ROOT / relative
        archive_name = 'manila-godot/' + relative.replace('\\', '/')
        if relative and source.is_file() and source.name not in SECRET_NAMES and archive_name not in already_packed:
            core.append((source, archive_name))
            already_packed.add(archive_name)
    all_names = [name for _, name in core + evidence]
    if len(all_names) != len(set(all_names)):
        raise SystemExit("Duplicate archive paths detected.")
    manifest = []
    write_archive(out / "01-resume-core.zip", core, manifest)
    write_archive(out / "02-history-materials.zip", evidence, manifest)
    unchanged = git("status", "--porcelain=v1") == snapshot["status"] and git("rev-parse", "HEAD").strip() == snapshot["head"]
    if not unchanged:
        raise SystemExit("Git changed during export. Preserve this snapshot but regenerate for an exact current handoff.")
    summary = {"created": now.isoformat(), "finished": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
               "project": str(ROOT), "head": snapshot["head"], "git_state_stable": unchanged,
               "threads": len(coverage), "subagents": sum(c["role"] == "子代理" for c in coverage),
               "threads_with_raw": sum(bool(c["raw_logs"]) for c in coverage),
               "threads_without_assistant": sum(not c["counts"].get("agentMessage") for c in coverage),
               "redactions": dict(REDACTIONS), "files": manifest,
               "exclusions": sorted(SKIP_DIRS | SECRET_NAMES),
               "coverage_note": "Only locally available project data. Not a guaranteed app-sidebar import. Current chat ends at export snapshot."}
    json_file(out / "manifest.json", summary)
    with zipfile.ZipFile(out / "01-resume-core.zip", "a", allowZip64=True) as archive:
        archive.write(out / "manifest.json", "manifest.json", compress_type=zipfile.ZIP_DEFLATED, compresslevel=1)
    log("VERIFYING_ARCHIVES")
    for name in ["01-resume-core.zip", "02-history-materials.zip"]:
        with zipfile.ZipFile(out / name) as archive:
            failed = archive.testzip()
        if failed:
            raise SystemExit("CRC failure: " + failed)
        log("CRC_OK", name)
    checksums = []
    for name in ["01-resume-core.zip", "02-history-materials.zip"]:
        checksums.append(digest_file(out / name) + "  " + name)
    (out / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="ascii")
    report = {"threads": summary["threads"], "subagents": summary["subagents"], "threads_with_raw": summary["threads_with_raw"],
              "threads_without_assistant": summary["threads_without_assistant"], "git_state_stable": unchanged,
              "archive_crc": "passed", "files": len(manifest),
              "archives": {n: (out / n).stat().st_size for n in ["01-resume-core.zip", "02-history-materials.zip"]}}
    json_file(out / "export_report.json", report)
    log("EXPORT_COMPLETE", json.dumps(report, ensure_ascii=False), "OUTPUT", out)


if __name__ == "__main__":
    main()
