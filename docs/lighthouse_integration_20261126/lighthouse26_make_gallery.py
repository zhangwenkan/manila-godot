"""Assemble unchanged engine screenshots for review; no visual retouching."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2] / 'demo/tropical_harbor_3d'
LOG = ROOT / 'captures/lighthouse_integration_20261126'
CAP = ROOT / 'captures/art_20261126_030424_927844'
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 24)
rows = [
    ('lighthouse26_front_quarter.png', '当前场景 · 灯塔近景'),
    ('lighthouse26_normal_8_5.png', '正常航行镜头 · 三船刻度 8.5'),
    ('lighthouse26_lantern_detail.png', '灯室与未来领航光束起点'),
    ('lighthouse26_reef_shore_contact.png', '礁台与岸边隔水关系'),
]
gallery = Image.new('RGB', (1600, 972), (25, 42, 43))
draw = ImageDraw.Draw(gallery)
for index, (name, label) in enumerate(rows):
    x, y = (index % 2) * 800, (index // 2) * 486
    with Image.open(CAP / name) as image:
        gallery.paste(image.convert('RGB').resize((800, 450), Image.Resampling.LANCZOS), (x, y + 36))
    draw.text((x + 14, y + 3), label, fill=(238, 232, 216), font=font)
gallery.save(LOG / 'final_gallery.jpg', quality=91)
with Image.open(CAP / 'lighthouse26_front_quarter.png') as image:
    image.convert('RGB').resize((1280,720), Image.Resampling.LANCZOS).save(LOG/'lighthouse_preview.jpg',quality=91)
print(LOG / 'final_gallery.jpg')
