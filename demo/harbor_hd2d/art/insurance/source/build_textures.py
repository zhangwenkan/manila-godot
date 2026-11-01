"""Deterministic, local pixel textures; no reference image is uploaded or copied."""
from pathlib import Path
from PIL import Image, ImageDraw
import random

out=Path(__file__).parent/'textures'
out.mkdir(exist_ok=True)
rng=random.Random(74108)


def save(name, base, mode):
    path=out/name
    if path.exists():
        raise RuntimeError('Refusing to overwrite '+str(path))
    image=Image.new('RGB',(128,128),base)
    draw=ImageDraw.Draw(image)
    if mode=='paint':
        for x in range(0,128,16):
            shift=rng.randint(-12,12)
            shade=tuple(max(0,min(255,c+shift)) for c in base)
            draw.rectangle((x,0,x+14,127),fill=shade)
            draw.line((x,0,x,127),fill=tuple(int(c*.65) for c in base))
            draw.line((x+1,0,x+1,127),fill=tuple(min(c+20,255) for c in base))
            for i in range(7):
                a=x+rng.randint(3,12); b=rng.randrange(125)
                draw.rectangle((a,b,a+1,min(127,b+rng.randint(3,18))),fill=tuple(max(0,c-16) for c in base))
        for i in range(45):
            x=rng.randrange(128); y=rng.choice([rng.randrange(14),rng.randrange(112,128)])
            draw.rectangle((x,y,x+rng.randint(1,4),min(127,y+2)),fill=(128,118,91))
    elif mode=='roof':
        for y in range(0,128,32):
            draw.rectangle((0,y,127,y+2),fill=(54,67,70))
            draw.line((0,y+3,127,y+3),fill=(162,169,152))
        for x in [2,63,125]:
            draw.line((x,0,x,127),fill=(62,74,77),width=2)
        for i in range(80):
            x=rng.randrange(128); seam=rng.choice([0,32,64,96,126]); y=max(0,min(125,seam+rng.randint(-6,4)))
            draw.rectangle((x,y,min(127,x+rng.randint(2,10)),min(127,y+rng.randint(1,4))),fill=rng.choice([(135,91,61),(162,114,66),(99,76,60),(180,133,79)]))
        for y in [8,40,72,104]:
            for x in [7,58,69,120]:
                draw.rectangle((x,y,x+1,y+1),fill=(43,52,57))
                draw.point((x,y-1),fill=(194,195,167))
    elif mode=='red':
        for i in range(170):
            x=rng.choice([rng.randrange(14),rng.randrange(112,128)])
            y=rng.randrange(128)
            draw.rectangle((x,y,min(127,x+rng.randint(1,5)),min(127,y+rng.randint(2,8))),fill=rng.choice([(95,64,54),(187,102,69),(81,78,68)]))
        draw.line((2,0,2,127),fill=(225,125,86),width=2)
    elif mode=='wood':
        for y in range(0,128,16):
            tint=rng.randint(-15,15)
            draw.rectangle((0,y,127,y+14),fill=tuple(max(0,c+tint) for c in base))
            draw.line((0,y+15,127,y+15),fill=(67,52,43))
            for j in range(8):
                x=rng.randrange(120); yy=y+rng.randint(3,12)
                draw.line((x,yy,min(127,x+rng.randint(6,30)),yy),fill=(110,83,53))
        for i in range(15):
            x=rng.randrange(128); y=rng.randrange(128)
            draw.rectangle((x,y,min(127,x+5),min(127,y+1)),fill=(167,136,84))
    image.save(path)
    print(path.name)

save('wall_blue.png',(89,128,141),'paint')
save('roof_tin.png',(125,139,137),'roof')
save('crane_red.png',(162,69,47),'red')
save('dock_wood.png',(151,119,76),'wood')
