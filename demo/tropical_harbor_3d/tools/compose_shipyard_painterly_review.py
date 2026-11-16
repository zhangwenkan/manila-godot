"""Compose unchanged in-engine captures for painterly shipyard review. No retouching."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "captures/shipyard_painterly_20261112"
BEFORE = ROOT / "captures/art_20261111_111944_599606"
AFTER = ROOT / "captures/art_20261112_135029_417323"
FONT = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 26)
SMALL = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)

def compare(name, crop, output):
    parts = [Image.open(p / name).convert("RGB") for p in (BEFORE, AFTER)]
    assert parts[0].size == parts[1].size == (1600, 900)
    parts = [im.crop(crop) for im in parts]
    w, h = parts[0].size
    sheet = Image.new("RGB", (w * 2 + 24, h + 70), "#eeeae0")
    draw = ImageDraw.Draw(sheet)
    for i, (im, label) in enumerate(zip(parts, ("调整前 · 已有铁皮质感", "调整后 · 灰蓝色面与克制磨损"))):
        x = i * (w + 24)
        sheet.paste(im, (x, 70))
        draw.text((x + 18, 20), label, font=FONT, fill="#263638")
    sheet.save(OUT / output)

compare("shipyard_combined_reference.png", (465, 135, 1195, 745), "before_after_reference.png")
compare("shipyard_combined_workbench_props.png", (355, 115, 1195, 895), "before_after_workbench.png")
compare("shipyard_combined_roof_metal.png", (240, 60, 1490, 870), "before_after_roof.png")

frames = json.loads((AFTER / "art_result.json").read_text())["frames"]
sheet = Image.new("RGB", (1600, 4 * 337), "#eeeae0")
draw = ImageDraw.Draw(sheet)
for i, name in enumerate(frames):
    im = Image.open(AFTER / name).convert("RGB")
    im.thumbnail((520, 292), Image.Resampling.LANCZOS)
    x = (i % 3) * 533
    y = (i // 3) * 337
    sheet.paste(im, (x, y + 30))
    draw.text((x + 6, y + 3), name.removeprefix("shipyard_combined_").removesuffix(".png"), font=SMALL, fill="#263638")
sheet.save(OUT / "inspection_contact_sheet.jpg", quality=92)
(OUT / "comparison_manifest.json").write_text(json.dumps({
    "before": str(BEFORE), "after": str(AFTER),
    "comparison": "Same camera, daylight and resolution. Identical unscaled crops; no colour adjustment or sharpening.",
    "contact_sheet": "Thumbnails only. Original 1600x900 captures are retained.",
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(OUT)

