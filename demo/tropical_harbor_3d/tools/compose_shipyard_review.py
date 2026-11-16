"""Compose equal crops of the same-camera runtime captures, without retouching."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json
import shutil
import sys

source = Path(sys.argv[1]).resolve()
target = Path(sys.argv[2]).resolve()
target.mkdir(parents=True, exist_ok=True)
report = json.loads((source / "art_result.json").read_text(encoding="utf-8"))
for filename in report["frames"] + ["art_result.json", "import.log", "preview.log"]:
    shutil.copy2(source / filename, target / filename)
font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 27)
small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
board = Image.new("RGB", (1860, 928), "#18383b")
draw = ImageDraw.Draw(board)
for index, (variant, title, caption) in enumerate([
    ("a", "A · 石砌修理船坞", "敞开作业区 / 架船维修 / 石墙工坊"),
    ("b", "B · 工业修船厂", "蓝灰板墙 / 金属屋顶与天窗 / 吊机与临水平台"),
]):
    left = 20 + index * 920
    draw.text((left, 15), title, font=font, fill="#f1e4c5")
    draw.text((left, 54), caption, font=small, fill="#bed0ca")
    with Image.open(source / f"shipyard_{variant}_reference.png") as image:
        # Identical crop and size preserve the actual relative model scale.
        board.paste(image.crop((350, 80, 1250, 900)).convert("RGB"), (left, 88))
board.save(target / "shipyard_comparison.png")
print(target / "shipyard_comparison.png")
