"""Make labelled evidence crops only; no game image repainting or asset edits."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
CAP = ROOT / 'demo/tropical_harbor_3d/captures/art_20261123_220019_536387'
OUT = ROOT / 'demo/tropical_harbor_3d/captures/terrain_logic_review_20261123'
cards = [
    ('01 医院转弯', '直角草条、陡坎与道路混在一起', 'town_market_chapel.png', (1220, 400, 1600, 730), (1480, 488, 1555, 577)),
    ('02 贸易行沙口', '道路、土坎、沙口和岸石挤在同一处', 'town_market_chapel.png', (285, 515, 785, 750), (450, 585, 715, 685)),
    ('03 Sea Breeze 前院', '院地边直接变成裸土坎，下降口不清楚', 'town_market_chapel.png', (780, 650, 1455, 900), (910, 745, 1285, 882)),
    ('04 酒吧与码头', '浅路与沙舌贴过高草台，缺完整下行面', '06_hut_pier_detail.png', (380, 225, 1235, 590), (545, 255, 1020, 490)),
    ('05 Diner—Sari', '两边路面伸向沙沟，共同通路不成立', 'shared_supply_yard.png', (90, 535, 1265, 900), (450, 645, 840, 890)),
    ('06 后排台地与长岸段', '坡顶、岩壁、道路仍像平行色带', '04_later_coast.png', (0, 0, 830, 320), (160, 60, 750, 250)),
]
W, H, GAP = 720, 405, 18
canvas = Image.new('RGB', (W * 2 + GAP * 3, H * 3 + GAP * 4 + 80), '#202526')
draw = ImageDraw.Draw(canvas)
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 22)
small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 19)
draw.text((GAP, 16), '现状问题核查 · 6处代表位置', font=font, fill='#f0e9dc')
draw.text((GAP, 49), '均来自当前实机截图，仅裁切、等比缩放和标框；本轮未修改模型', font=small, fill='#b9c7c0')
for i, (title, caption, filename, crop_box, mark) in enumerate(cards):
    x, y = GAP + (i % 2) * (W + GAP), 85 + GAP + (i // 2) * (H + GAP)
    draw.rectangle((x, y, x + W, y + H), fill='#2b3232')
    draw.text((x + 12, y + 8), title, font=font, fill='#f0e9dc')
    draw.text((x + 12, y + 41), caption, font=small, fill='#c8d1cb')
    img = Image.open(CAP / filename).convert('RGB').crop(crop_box)
    scale = min((W - 20) / img.width, (H - 80) / img.height)
    size = (round(img.width * scale), round(img.height * scale))
    img = img.resize(size, Image.Resampling.LANCZOS)
    px, py = x + (W - size[0]) // 2, y + 76 + (H - 80 - size[1]) // 2
    canvas.paste(img, (px, py))
    coords = [px + (mark[0] - crop_box[0]) * scale, py + (mark[1] - crop_box[1]) * scale,
              px + (mark[2] - crop_box[0]) * scale, py + (mark[3] - crop_box[1]) * scale]
    draw.rectangle(coords, outline='#28b8de', width=3)
OUT.mkdir(exist_ok=True)
canvas.save(OUT / 'terrain_logic_issues.jpg', quality=94, subsampling=0)
