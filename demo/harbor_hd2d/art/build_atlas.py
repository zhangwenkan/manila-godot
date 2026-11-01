"""Rebuild the local 16-tile harbor atlas; Pillow only, deterministic seed 1847.

64px cells contain 60px authored interiors with 2px replicated gutters.
All marks describe material features rather than an undirected noise overlay.
"""
from pathlib import Path
import hashlib
import random
from PIL import Image, ImageDraw

SIZE, CELL, GUTTER, SEED = 60, 64, 2, 1847
TILE_NAMES = (
    "wood", "roof_brown", "roof_rust", "wall_teal", "wall_tan", "stone", "grass", "sand",
    "darkwood", "crate", "roof_charcoal", "paper", "leaf", "red_paint", "hull", "sail",
)


class Paint:
    def __init__(self, background, salt):
        self.image = Image.new("RGB", (SIZE, SIZE), background)
        self.draw = ImageDraw.Draw(self.image)
        self.rng = random.Random(SEED + salt)

    def rect(self, box, color):
        x0, y0, x1, y1 = box
        for dx in (-SIZE, 0, SIZE):
            for dy in (-SIZE, 0, SIZE):
                self.draw.rectangle((x0+dx, y0+dy, x1+dx, y1+dy), fill=color)

    def line(self, points, color, width=1):
        for dx in (-SIZE, 0, SIZE):
            for dy in (-SIZE, 0, SIZE):
                self.draw.line([(x+dx, y+dy) for x, y in points], fill=color, width=width)

    def poly(self, points, color):
        for dx in (-SIZE, 0, SIZE):
            for dy in (-SIZE, 0, SIZE):
                self.draw.polygon([(x+dx, y+dy) for x, y in points], fill=color)

    def ellipse(self, box, color):
        x0, y0, x1, y1 = box
        for dx in (-SIZE, 0, SIZE):
            for dy in (-SIZE, 0, SIZE):
                self.draw.ellipse((x0+dx, y0+dy, x1+dx, y1+dy), fill=color)


WOOD = ("#463226", "#795037", "#aa7549", "#b17d50", "#d09a61", "#91613e")
TAN = ("#624c34", "#967447", "#bd985f", "#c39e66", "#ddbb7e", "#a88655")
TEAL = ("#354b4a", "#526764", "#748e87", "#7c948c", "#a1b4a0", "#657c75")
DARK = ("#302921", "#4c382b", "#715039", "#795740", "#976d49", "#604530")
HULL = ("#49372c", "#775037", "#9b6b42", "#a97547", "#c38e58", "#835738")


def boards(salt, palette, vertical=False):
    ink, shade, base, alternate, light, grain = palette
    p = Paint(base, salt)
    for row in range(5):
        y, end = row*12, (8, 37, 19, 49, 29)[row]
        p.rect((0,y,59,y+11), alternate if row % 2 else base)
        p.line([(0,y),(59,y)], ink)
        p.line([(0,y+1),(59,y+1)], shade)
        p.line([(0,y+2),(59,y+2)], light)
        p.line([(end,y+2),(end,y+11)], ink)
        p.line([(end+1,y+3),(end+1,y+10)], light)
        for offset, gy in ((6,5),(29,9)):
            x, length = end+offset, p.rng.randint(12,21)
            p.line([(x,y+gy),(x+5,y+gy),(x+7,y+gy-1),(x+length,y+gy-1)], grain)
        if row in (1,3):
            x = end+23
            p.ellipse((x-4,y+4,x+5,y+9), grain)
            p.ellipse((x-2,y+5,x+3,y+8), light)
            p.line([(x,y+6),(x+2,y+6)], shade)
            p.line([(x+7,y+6),(x+12,y+5)], grain)
        for ny in (4,9):
            p.rect((end+3,y+ny,end+3,y+ny), ink)
            p.rect((end+4,y+ny,end+4,y+ny), light)
    return p.image.transpose(Image.Transpose.ROTATE_90) if vertical else p.image


def roof(salt, palette, rust=False):
    ink, shadow, base, light, ridge = palette
    p = Paint(base, salt)
    for x in range(0,60,10):
        p.rect((x,0,x+1,59), ink)
        p.rect((x+2,0,x+3,59), shadow)
        p.rect((x+6,0,x+8,59), light)
        p.line([(x+6,0),(x+6,59)], ridge)
    if rust:
        for x,y,h in ((3,6,12),(23,36,16),(43,18,10),(53,48,15)):
            p.poly([(x,y),(x+3,y),(x+3,y+3),(x+4,y+3),(x+4,y+h-3),(x+2,y+h-3),(x+2,y+h),(x,y+h)], "#8a533b")
            p.line([(x+1,y+2),(x+1,y+h-4)], "#b57446")
    for x in range(0,60,10):
        y = 29 if (x//10)%2 == 0 else 32
        p.line([(x+2,y),(x+9,y)], ink)
        p.line([(x+2,y+1),(x+9,y+1)], ridge)
        for ny in (y-2,y+4):
            p.rect((x+7,ny,x+8,ny+1), ink)
            p.rect((x+7,ny,x+7,ny), light)
    return p.image


def stone():
    p = Paint("#605e4c",5)
    tones = ("#a39c7e","#959881","#b0a889","#a1a389")
    for row in range(4):
        y = row*15
        for col in range(3):
            x = col*20+(10 if row%2 else 0)
            p.poly([(x+3,y+1),(x+17,y+1),(x+19,y+4),(x+19,y+11),(x+16,y+13),(x+3,y+13),(x+1,y+10),(x+1,y+4)], tones[(col+row*2)%4])
            p.line([(x+3,y+2),(x+16,y+2),(x+18,y+4)], "#c3bca0")
            p.line([(x+3,y+12),(x+15,y+12),(x+18,y+10)], "#81816b")
            if (col+row)%3 == 0:
                p.line([(x+8,y+8),(x+11,y+8),(x+12,y+7)], "#8b8b74")
    return p.image


def grass():
    p = Paint("#97a957",6)
    for x,y in ((6,8),(38,1),(24,27),(51,43),(2,53)):
        p.poly([(x-9,y),(x-4,y-3),(x+9,y-3),(x+13,y),(x+10,y+5),(x-6,y+5)], "#a1b461")
        p.line([(x-3,y+5),(x+7,y+5)], "#8da152")
    for x,y in ((4,17),(17,6),(36,16),(51,7),(14,37),(32,40),(48,30),(5,55),(24,56),(52,51)):
        p.line([(x-3,y-2),(x,y+1),(x+2,y-4)], "#718746")
        p.line([(x,y),(x,y-4)], "#c1c775")
        p.line([(x+1,y+1),(x+4,y-1)], "#b9c36b")
    return p.image


def sand():
    p = Paint("#cbb077",7)
    for x,y,w in ((3,9,22),(36,25,29),(13,44,31),(47,56,19)):
        p.line([(x,y),(x+5,y-1),(x+w-5,y-1),(x+w,y-2)], "#dcc08a")
        p.line([(x+5,y+1),(x+w-6,y+1)], "#bfa36b")
    for x,y in ((11,23),(28,8),(51,39),(34,51),(4,55),(42,14)):
        p.line([(x,y),(x+2,y)], "#a68b5d")
        p.line([(x,y-1),(x+1,y-1)], "#e3c993")
    return p.image


def crate():
    p = Paint("#a17348",9)
    p.image = boards(9,WOOD,True)
    p.draw = ImageDraw.Draw(p.image)
    for box in ((0,0,59,6),(0,53,59,59),(0,0,6,59),(53,0,59,59)):
        p.rect(box,"#61432f")
    for box in ((2,2,57,5),(2,54,57,57),(2,6,5,53),(54,6,57,53)):
        p.rect(box,"#b18452")
    p.line([(7,49),(49,7)],"#533d2b",9)
    p.line([(8,49),(49,8)],"#bb8c54",6)
    p.line([(9,46),(46,9)],"#d2a469")
    for x,y in ((4,4),(55,4),(4,55),(55,55),(10,48),(48,10)):
        p.rect((x,y,x+1,y+1),"#3e3529")
        p.rect((x,y-1,x+1,y-1),"#dec08c")
    return p.image


def paper():
    p = Paint("#d8c79d",11)
    for y in (12,36):
        p.line([(0,y),(59,y)],"#d3c196")
        p.line([(0,y+1),(59,y+1)],"#dfcea7")
    for x,y in ((8,6),(29,21),(47,45),(14,51),(56,14),(35,57)):
        p.line([(x,y),(x+3,y)],"#c9b98e")
    return p.image


def leaf():
    p = Paint("#52683d",12)
    for x,y,flip in ((8,8,1),(37,0,-1),(5,40,-1),(36,33,1)):
        def pts(points):
            return [(x+flip*u,y+v) for u,v in points]
        p.poly(pts([(-3,20),(-13,12),(-16,1),(-12,-11),(-2,-18),(9,-9),(14,4),(10,14)]),"#394f33")
        p.poly(pts([(-2,17),(-11,10),(-13,1),(-10,-9),(-2,-15),(6,-7),(11,4),(8,12)]),"#758b48")
        p.poly(pts([(-2,16),(-2,-15),(6,-7),(11,4),(8,12)]),"#8da255")
        p.line(pts([(-3,19),(-2,-13)]),"#b0b66b")
        for vy in (-6,1,8):
            p.line(pts([(-2,vy+4),(-9,vy-2)]),"#596f3c")
            p.line(pts([(-1,vy+4),(7,vy-2)]),"#708746")
    return p.image


def red_paint():
    p = Paint("#a4513d",13)
    p.image = boards(13,("#533832","#843e33","#a4513d","#ac5942","#c27b57","#934835"))
    p.draw = ImageDraw.Draw(p.image)
    for x,y in ((13,3),(39,27),(4,51),(49,16),(27,42)):
        p.poly([(x,y),(x+6,y),(x+6,y+1),(x+10,y+1),(x+10,y+2),(x+2,y+2),(x+2,y+1),(x,y+1)],"#c09a65")
        p.line([(x+3,y+3),(x+9,y+3)],"#713e30")
    return p.image


def sail():
    p = Paint("#dbd2af",15)
    for x in (0,30):
        p.rect((x,0,x+2,59),"#c3b796")
        p.line([(x+3,0),(x+3,59)],"#eee2bd")
        p.line([(x+6,0),(x+6,59)],"#d4c9a6")
        for y in range(3,60,6):
            p.line([(x+1,y),(x+2,y+1)],"#938c74")
    for x,y in ((12,12),(45,40),(18,51),(39,23)):
        p.line([(x,y),(x+5,y)],"#d1c6a5")
        p.line([(x+2,y+1),(x+8,y+1)],"#e3d9b6")
    return p.image


def build():
    tiles = (
        boards(0,WOOD), roof(1,("#494238","#70604b","#8d775a","#a18b69","#b6a17c")),
        roof(2,("#484840","#74776b","#929285","#a9a797","#c0bca6"),True),
        boards(3,TEAL,True), boards(4,TAN), stone(), grass(), sand(), boards(8,DARK), crate(),
        roof(10,("#343b3a","#4e5753","#667068","#7c8579","#959c8a"),True),
        paper(), leaf(), red_paint(), boards(14,HULL), sail(),
    )
    atlas = Image.new("RGB",(256,256))
    for index,image in enumerate(tiles):
        cell = Image.new("RGB",(CELL,CELL))
        for y in range(CELL):
            for x in range(CELL):
                cell.putpixel((x,y),image.getpixel((min(59,max(0,x-2)),min(59,max(0,y-2)))))
        atlas.paste(cell,((index%4)*CELL,(index//4)*CELL))
    for index,image in enumerate(tiles):
        ox,oy = (index%4)*CELL,(index//4)*CELL
        for y in range(CELL):
            for x in range(CELL):
                assert atlas.getpixel((ox+x,oy+y)) == image.getpixel((min(59,max(0,x-2)),min(59,max(0,y-2))))
    return atlas


if __name__ == "__main__":
    atlas = build()
    assert atlas.tobytes() == build().tobytes()
    output = Path(__file__).with_name("harbor_atlas.png")
    atlas.save(output,compress_level=9)
    print("HARBOR_ATLAS_PASS: 256x256 / 16 tiles / deterministic pixels and gutters")
    print(hashlib.sha256(output.read_bytes()).hexdigest())
