"""Silently sample the user's existing reference recording, never desktop input."""
from pathlib import Path
import argparse
import json
import hashlib
import cv2
from PIL import Image, ImageDraw, ImageFont

VIDEO = Path("C:/Users/51440/WorkBuddy AI/2026-11-02-00-03-24/forkedpush_2106313584829431901/video/forkedpush_2106313584829431901.mp4")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "captures/reference_recording_review_20261112"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, nargs="+", help="Additional exact timestamps; preserves the initial sampling manifest.")
    args = parser.parse_args()
    cv2.setNumThreads(1)
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot read the existing reference recording")
    fps = cap.get(cv2.CAP_PROP_FPS)
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = count / fps
    OUT.mkdir(exist_ok=True)
    frames = []
    timestamps = sorted(set(args.seconds)) if args.seconds else range(0, int(duration), 5)
    for timestamp in timestamps:
        if not 0 <= timestamp < duration:
            raise ValueError(f"Timestamp outside recording: {timestamp}")
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ok, bgr = cap.read()
        if not ok:
            raise RuntimeError(f"Could not decode frame at {timestamp}s")
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        p = OUT / f"frame_{timestamp:03d}s.png"
        Image.fromarray(rgb).save(p, compress_level=2)
        frames.append({"timestamp_seconds": timestamp, "file": p.name,
                       "decoded_frame_index": int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1,
                       "decoded_timestamp_seconds": cap.get(cv2.CAP_PROP_POS_MSEC) / 1000,
                       "native_size": [rgb.shape[1], rgb.shape[0]]})
    cap.release()
    columns, cell_w, cell_h = 4, 410, 261
    rows = (len(frames) + columns - 1) // columns
    board = Image.new("RGB", (columns * cell_w, 106 + rows * cell_h), "#f4f1e9")
    d = ImageDraw.Draw(board)
    title = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 30)
    label = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    heading = "参考游戏录像 · 邻近时间点补样" if args.seconds else "参考游戏完整录像 · 每 5 秒取样"
    d.text((16, 12), heading, font=title, fill="#24423c")
    d.text((16, 57), "原始用户录像；非本轮新操作游戏截图。缩略图只作筛选，完整 2560×1440 帧另存。", font=label, fill="#586c65")
    for i, row in enumerate(frames):
        x, y = (i % columns) * cell_w, 106 + (i // columns) * cell_h
        im = Image.open(OUT / row["file"])
        thumb = im.resize((394, 222), Image.Resampling.LANCZOS)
        board.paste(thumb, (x+8, y))
        ts = row["timestamp_seconds"]
        d.text((x+12, y+227), f"{ts//60:02d}:{ts%60:02d}  ·  {row['file']}", font=label, fill="#24423c")
    sheet_name = "supplement_samples.jpg" if args.seconds else "all_samples.jpg"
    manifest_name = "supplement_manifest.json" if args.seconds else "manifest.json"
    board.save(OUT / sheet_name, quality=94)
    digest = hashlib.sha256()
    with VIDEO.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    report = {"source": str(VIDEO), "source_sha256": digest.hexdigest(),
              "scope": "Existing reference game recording sampled silently; not new interactive gameplay captures.",
              "width": width, "height": height, "fps": fps, "frame_count": count, "duration_seconds": duration,
              "processing": "Decode native frames to PNG; no recolouring or sharpening. Contact sheet is resized for review.",
              "samples": frames}
    (OUT / manifest_name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    print(json.dumps({"duration_seconds":duration,"samples":len(frames),"native_size":[width,height],"sheet":str(OUT/sheet_name)},ensure_ascii=False))


if __name__ == "__main__":
    main()
