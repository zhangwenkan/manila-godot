"""Compose a small, source-labelled research board; never modifies game assets."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RECORDING = ROOT / "captures/reference_recording_review_20261112"
OUT = ROOT / "captures/reference_review_20261113"
SOURCES = [
    (RECORDING / "frame_005s.png", "原作录像 00:05 · 栈桥与泊船", "桥面、泊船与桥下投影的并置", "recording", 5),
    (RECORDING / "frame_020s.png", "原作录像 00:20 · 沙湾", "硬岩、柔和沙坡与植被同时存在", "recording", 20),
    (RECORDING / "frame_110s.png", "原作录像 01:50 · 沿岸通路", "观察岩岸、草地与可走空间", "recording", 110),
    (RECORDING / "frame_126s.png", "原作录像 02:06 · 屋旁平台", "支撑与接岸处有遮挡，不能补猜", "recording", 126),
    (ROOT / "captures/art_20261112_135029_417323/shipyard_combined_actual_local_camera.png", "本项目 · 保存的航行机位", "石坞铺地、挡墙、外缘需有主次", "project_saved_capture", None),
    (Path("C:/Users/51440/.codex/skills/harbor-blender-craft/references/images/current-harbor.png"), "本项目 · 货仓与船桥基线", "保留已认可的构件与材料角色", "project_skill_baseline", None),
]


def main():
    OUT.mkdir(exist_ok=True)
    board = Image.new("RGB", (1232, 722), "#eeeae1")
    draw = ImageDraw.Draw(board)
    bold = "C:/Windows/Fonts/msyhbd.ttc"
    normal = "C:/Windows/Fonts/msyh.ttc"
    title = ImageFont.truetype(bold, 28)
    label = ImageFont.truetype(bold, 19)
    small = ImageFont.truetype(normal, 17)
    draw.text((16, 12), "多图复核 · 先区分构件与空间，再判断软硬和明暗", font=title, fill="#243e3a")
    draw.text((16, 53), "同一录像的四个邻近区域；本轮未进入游戏补拍。不同机位只解释关系，不作为质量前后对比。", font=small, fill="#52615d")
    records = []
    for index, (source, heading, note, source_kind, seconds) in enumerate(SOURCES):
        x, y = 16 + (index % 3) * 404, 94 + (index // 3) * 308
        with Image.open(source) as original:
            native_size = list(original.size)
            thumb = original.convert("RGB")
            thumb.thumbnail((392, 221), Image.Resampling.LANCZOS)
        draw.rectangle((x, y, x + 391, y + 220), fill="#c6d2cf")
        board.paste(thumb, (x + (392 - thumb.width) // 2, y + (221 - thumb.height) // 2))
        draw.text((x, y + 230), heading, font=label, fill="#243e3a")
        draw.text((x, y + 260), note, font=small, fill="#52615d")
        records.append({"source": str(source), "source_kind": source_kind, "timestamp_seconds": seconds,
                        "native_size": native_size, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "label": heading, "note": note})
    destination = OUT / "overview.jpg"
    board.save(destination, quality=78, optimize=True)
    report = {"date": "2026-11-13", "output": str(destination), "dimensions": list(board.size),
              "bytes": destination.stat().st_size,
              "processing": "Full-frame downsampling, JPEG encoding and external labels only. No recolouring, sharpening, cropping or synthesis.",
              "limits": "A compact comparison of spatial relationships, not surface-detail or same-camera before/after evidence.",
              "sources": records}
    (OUT / "overview_manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"image": str(destination), "dimensions": list(board.size), "bytes": report["bytes"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
