"""Make a bounded, source-labelled video research overview without desktop input."""
from pathlib import Path
import hashlib
import json
import cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "captures/author_videos_20261113"
SELECTIONS = [
    ("01", 25.8, "01 神龛 V3 · 00:25.80", "分块石基、立柱、晶体与局部植物"),
    ("02", 0.2, "02 鱼摊试验 · 00:00.20", "构造与道具迭代；未确认纳入游戏"),
    ("03", 25.0, "03 灌木制作 · 00:25.00", "尖叶、折面、叠层与嵌入的果实"),
    ("04", 0.0, "04 河岸桥头 · 00:00.00", "桥面、草地、土路和岸坡的衔接"),
    ("05", 15.133, "05 Demo 发布片 · 00:15.13", "城镇布局参考；暖光不作白天取色"),
    ("06", 46.8, "06 开发回顾 · 00:46.80", "同类城镇画面；不另算一座新城镇"),
]


def main():
    cv2.setNumThreads(1)
    catalog = json.loads((OUT / "sources_manifest.json").read_text(encoding="utf-8"))
    board = Image.new("RGB", (1232, 722), "#eeeae1")
    draw = ImageDraw.Draw(board)
    title = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 28)
    label = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 19)
    small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 17)
    draw.text((16, 12), "作者视频复核 · 三种制作过程与河岸、城镇环境", font=title, fill="#243e3a")
    draw.text((16, 53), "六段用户提供的公开视频；截图只显示选定时刻。制作试验、开发回顾与宣传实景分别标注。", font=small, fill="#52615d")
    records = []
    for i, (prefix, seconds, heading, note) in enumerate(SELECTIONS):
        source = next(row for row in catalog["videos"] if row["file"].startswith(prefix + "_"))
        video = OUT / source["file"]
        cap = cv2.VideoCapture(str(video))
        fps = cap.get(cv2.CAP_PROP_FPS)
        requested_frame = round(seconds * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, requested_frame)
        ok, bgr = cap.read()
        if not ok:
            raise RuntimeError(f"Unable to decode {video.name} at {seconds}")
        actual_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        pts_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
        cap.release()
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        still = Image.fromarray(rgb)
        native_size = list(still.size)
        still.thumbnail((392, 221), Image.Resampling.LANCZOS)
        x, y = 16 + (i % 3) * 404, 94 + (i // 3) * 308
        draw.rectangle((x, y, x + 391, y + 220), fill="#c6d2cf")
        board.paste(still, (x + (392 - still.width) // 2, y + (221 - still.height) // 2))
        draw.text((x, y + 230), heading, font=label, fill="#243e3a")
        draw.text((x, y + 260), note, font=small, fill="#52615d")
        records.append({"video": source["file"], "source_url": source["source_url"], "source_sha256": source["sha256"],
                        "requested_seconds": seconds, "decoded_frame_index_zero_based": actual_frame,
                        "nominal_seconds_from_frame_rate": actual_frame / fps, "opencv_timestamp_ms": pts_ms,
                        "native_dimensions": native_size, "decoded_rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest(),
                        "crop": None, "heading": heading, "note": note})
    destination = OUT / "author_overview.jpg"
    board.save(destination, quality=78, optimize=True)
    manifest = {"output": destination.name, "dimensions": list(board.size), "bytes": destination.stat().st_size,
                "processing": "Full-frame OpenCV decoding, downsampling, JPEG and external labels. No recolouring, sharpening or synthesis.",
                "limits": "Overview of selected content, not proof of unshown editing commands, texture nodes, material values or released-version parity.",
                "sources": records}
    (OUT / "author_overview_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"image": destination.name, "bytes": manifest["bytes"], "dimensions": manifest["dimensions"]}))


if __name__ == "__main__":
    main()
