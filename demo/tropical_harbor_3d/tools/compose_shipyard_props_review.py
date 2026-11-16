"""Unretouched same-camera comparison and inspection contact sheet."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / "captures/shipyard_props_20261111"
BEFORE = ROOT / "captures/art_20261111_013613_720894"
AFTER = ROOT / "captures/art_20261111_111944_599606"
font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24)
small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
crop = (915, 235, 1555, 865)
board = Image.new("RGB", (1328, 720), "#1c302e")
d = ImageDraw.Draw(board)
for i, (folder, title) in enumerate([(BEFORE, "精修前"), (AFTER, "本轮道具精修")]):
    x = 16 + i * 656
    d.text((x, 12), title, fill="#eee4cc", font=font)
    with Image.open(folder / "shipyard_combined_detail.png") as im:
        board.paste(im.crop(crop), (x, 53))
d.text((16, 684), "同机位 · 同日光 · 原尺寸相同裁切，无调色或锐化", fill="#c3d1c8", font=small)
board.save(CAP / "before_after_props.png")
names = ["reference", "front", "back", "sailing_context", "actual_local_camera", "door_connection"]
sheet = Image.new("RGB", (1600, 1434), "#1c302e")
d = ImageDraw.Draw(sheet)
for i, name in enumerate(names):
    x = (i % 2) * 800
    y = (i // 2) * 478
    d.text((x + 8, y + 3), name, fill="white", font=small)
    with Image.open(AFTER / ("shipyard_combined_" + name + ".png")) as im:
        sheet.paste(im.resize((800, 450)), (x, y + 28))
sheet.save(CAP / "inspection_contact_sheet.jpg", quality=95)
print(CAP / "before_after_props.png")
