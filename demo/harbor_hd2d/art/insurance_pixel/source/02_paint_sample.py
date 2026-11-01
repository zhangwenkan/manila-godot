"""Paint deterministic pixel clusters and bitmap signs, not downsampled PBR maps."""
from pathlib import Path
import json
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "textures"
OUT.mkdir(exist_ok=True)
for filename in ["sample_atlas.png", "sample_signs.png", "sample_palette.json"]:
    if (OUT / filename).exists():
        raise FileExistsError(filename)

PALETTE = {
    "wall": ["#394952", "#526772", "#718690", "#95a4aa"],
    "roof": ["#464a4c", "#666762", "#89887b", "#aaa493", "#805e45"],
    "red": ["#553233", "#893d36", "#b65441", "#d57852"],
    "wood": ["#4c423a", "#77614b", "#9c8060", "#c1a47a"],
    "sign": ["#303841", "#495660", "#cad0c1", "#f0e0b8"],
}
image = Image.new("RGB", (512, 512), PALETTE["wall"][0])
TILES = {"wall": (0, 0), "roof": (256, 0), "red": (0, 256), "wood": (256, 256)}
for kind, (ox, oy) in TILES.items():
    tile = Image.new("RGB", (248, 248), PALETTE[kind][2 if kind != "red" else 1])
    d = ImageDraw.Draw(tile)
    p = PALETTE[kind]
    if kind == "wall":
        for x in range(0, 248, 10):
            d.rectangle((x, 0, x, 247), fill=p[0])
            d.rectangle((x + 1, 0, x + 2, 247), fill=p[1])
            d.rectangle((x + 8, 0, x + 9, 247), fill=p[3])
            for row in range(3):
                y = (x * 7 + row * 79) % 225
                d.rectangle((x + 4, y, x + 5, y + 13), fill=p[1])
                d.rectangle((x + 5, y + 14, x + 7, y + 18), fill=p[1])
    elif kind == "roof":
        for x in range(0, 248, 24):
            d.rectangle((x, 0, x + 1, 247), fill=p[0])
            d.rectangle((x + 2, 0, x + 3, 247), fill=p[3])
            for row in range(0, 248, 43):
                y = row + (x // 24 % 2) * 18
                d.rectangle((x + 4, y, x + 22, y + 1), fill=p[1])
                d.polygon([(x+8,y+8),(x+16,y+8),(x+16,y+11),(x+20,y+11),(x+20,y+15),(x+17,y+15),(x+17,y+19),(x+10,y+19),(x+10,y+16),(x+7,y+16),(x+7,y+11),(x+8,y+11)], fill=p[4])
                d.rectangle((x + 10, y + 9, x + 15, y + 10), fill=p[3])
    elif kind == "red":
        for x in range(0, 248, 19):
            for row in range(0, 248, 53):
                y = row + (x // 19 % 3) * 9
                d.polygon([(x+4,y+8),(x+10,y+8),(x+10,y+10),(x+12,y+10),(x+12,y+15),(x+8,y+15),(x+8,y+13),(x+4,y+13)], fill=p[2])
                d.rectangle((x+5,y+8,x+8,y+8), fill=p[3])
                d.rectangle((x+8,y+14,x+10,y+15), fill=p[0])
    else:
        for y in range(0, 248, 12):
            d.rectangle((0,y,247,y), fill=p[0])
            d.rectangle((0,y+1,247,y+1), fill=p[1])
            d.rectangle((0,y+10,247,y+11), fill=p[3])
            for x in range(-48, 248, 72):
                x += (y // 12 % 3) * 24
                d.rectangle((x,y+2,x,y+9), fill=p[0])
                d.rectangle((x+9,y+4,x+34,y+4), fill=p[1])
                d.rectangle((x+30,y+5,x+44,y+5), fill=p[1])
    image.paste(tile, (ox+4, oy+4))
    image.paste(tile.crop((0,0,1,248)).resize((4,248), Image.Resampling.NEAREST), (ox,oy+4))
    image.paste(tile.crop((247,0,248,248)).resize((4,248), Image.Resampling.NEAREST), (ox+252,oy+4))
    strip = image.crop((ox,oy+4,ox+256,oy+5)).resize((256,4), Image.Resampling.NEAREST)
    image.paste(strip,(ox,oy))
    strip = image.crop((ox,oy+251,ox+256,oy+252)).resize((256,4), Image.Resampling.NEAREST)
    image.paste(strip,(ox,oy+252))
image.save(OUT / "sample_atlas.png")

GLYPHS = {
    "A": ["01110","11011","11011","11111","11011","11011","11011"],
    "C": ["01111","11000","11000","11000","11000","11000","01111"],
    "E": ["11111","11000","11000","11110","11000","11000","11111"],
    "G": ["01111","11000","11000","11011","11011","11011","01111"],
    "I": ["11111","00100","00100","00100","00100","00100","11111"],
    "N": ["11001","11001","11101","11111","11011","11001","11001"],
    "O": ["01110","11011","11011","11011","11011","11011","01110"],
    "R": ["11110","11011","11011","11110","11100","11010","11011"],
    "S": ["01111","11000","11000","01110","00011","00011","11110"],
    "U": ["11011","11011","11011","11011","11011","11011","01110"],
    ".": ["00000","00000","00000","00000","00000","00110","00110"],
    " ": ["00000"] * 7,
}
signs = Image.new("RGB", (256, 64), PALETTE["sign"][0])
d = ImageDraw.Draw(signs)
records = {}
for text, rect in [("INSURANCE CO.", (4,4,124,28)), ("CARGO CRANE", (132,4,248,28))]:
    x0,y0,x1,y1 = rect
    d.rectangle((x0,y0,x1-1,y1-1), fill=PALETTE["sign"][1])
    d.rectangle((x0+2,y0+2,x1-3,y1-3), fill=PALETTE["sign"][2])
    width = len(text)*6-1
    start = x0 + (x1-x0-width)//2
    for i, char in enumerate(text):
        for y, row in enumerate(GLYPHS[char]):
            for x, bit in enumerate(row):
                if bit == "1":
                    d.point((start+i*6+x,y0+8+y), fill=PALETTE["sign"][0])
    records[text] = rect
signs.save(OUT / "sample_signs.png")
(OUT / "sample_palette.json").write_text(json.dumps({"colors":PALETTE,"texels_per_unit":24,"tile_inner_pixels":248,"tile_padding":4,"tiles":TILES,"sign_rects":records,"method":"Integer-coordinate authored clusters and bitmap glyphs; no interpolation, noise or generated-model baking."},indent=2),encoding="utf-8")
print("PIXEL_TEXTURES_CREATED", len(image.getcolors(262144)), "atlas colors;", len(signs.getcolors(16384)), "sign colors")
