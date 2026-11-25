"""Unaltered same-camera crops; only crop, equal-scale resize and label."""
from pathlib import Path
import argparse
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument('--after', required=True, type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
captures = root / 'demo/tropical_harbor_3d/captures'
before = Image.open(captures / 'art_20261123_210700_848847/town_market_chapel.png').convert('RGB')
after = Image.open(args.after / 'town_market_chapel.png').convert('RGB')
assert before.size == after.size == (1600, 900)
regions = [('贸易行旁：沙口接路', (285, 520, 745, 740)),
           ('餐厅前：院地与土坡', (805, 670, 1430, 900)),
           ('医院右侧：坡顶转弯', (1250, 420, 1600, 690))]
width, gap = 650, 18
heights = [round((box[3] - box[1]) * width / (box[2] - box[0])) for _, box in regions]
canvas = Image.new('RGB', (width * 2 + gap * 3, sum(heights) + 64 * len(regions) + 60), '#202526')
draw = ImageDraw.Draw(canvas)
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 23)
draw.text((gap, 14), '修改前 · G23', fill='#e5e4df', font=font)
draw.text((width + 2 * gap, 14), '本轮修改后 · 同机位', fill='#e5e4df', font=font)
y = 56
for (label, box), height in zip(regions, heights):
    draw.text((gap, y), label, fill='#d2d8d5', font=font)
    y += 42
    for col, img in enumerate((before, after)):
        crop = img.crop(box).resize((width, height), Image.Resampling.LANCZOS)
        canvas.paste(crop, (gap + col * (width + gap), y))
    y += height + 22
out = captures / 'road_contacts_20261123'
canvas.save(out / 'before_after_contacts.jpg', quality=94, subsampling=0)
after.save(out / 'final_market_chapel.png')
print(out / 'before_after_contacts.jpg')
