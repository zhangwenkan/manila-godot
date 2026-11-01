"""Paint the revised asset locally: authored clusters, no PBR baking or filtering."""
from pathlib import Path
import json
import random
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / 'textures'
OUT.mkdir(exist_ok=True)
for name in ['harbor_pixels.png', 'harbor_signs.png', 'palette.json']:
    assert not (OUT / name).exists(), name

PALETTE = {
    'wall': ['#394851','#566970','#6b8086','#829196','#8e8980'],
    'roof': ['#424950','#616d77','#7b8387','#939695','#956243','#b0794d'],
    'red': ['#482d33','#71393b','#934742','#ac5b4c','#c07959'],
    'wood': ['#4e433b','#77624e','#998267','#b29b77','#c2ab86'],
}
ATLAS = Image.new('RGB', (512,512))
for kind,(ox,oy) in {'wall':(0,0),'roof':(256,0),'red':(0,256),'wood':(256,256)}.items():
    p=PALETTE[kind]
    im=Image.new('RGB',(248,248),p[2]); d=ImageDraw.Draw(im)
    rng=random.Random({'wall':31,'roof':53,'red':77,'wood':91}[kind])
    if kind=='wall':
        for x in range(0,248,9):
            d.rectangle((x,0,x+8,247), fill=rng.choices(p[1:4],[1,5,2])[0])
            d.line((x,0,x,247),fill=p[1])
            d.line((x+1,0,x+1,247),fill=p[3])
            if x%27==0: d.rectangle((x+2,170,x+7,247),fill=p[1])
        for _ in range(25):
            x=rng.randrange(3,240); y=rng.randrange(4,224); h=rng.randrange(5,22)
            d.polygon([(x,y),(x+2,y),(x+2,y+3),(x+4,y+3),(x+4,y+h),(x+1,y+h),(x+1,y+h-5),(x,y+h-5)],fill=p[4])
    elif kind=='roof':
        # Long corrugation runs, with broad irregular rust regions instead of stamps.
        for x in range(0,248,5):
            d.line((x,0,x,247),fill=p[1]); d.line((x+1,0,x+1,247),fill=p[3])
        for _ in range(19):
            x=rng.randrange(-15,230); y=rng.randrange(-12,235)
            w=rng.randrange(12,43); h=rng.randrange(8,31)
            points=[(x+4,y),(x+w-5,y),(x+w-5,y+3),(x+w,y+3),(x+w,y+h-5),(x+w-4,y+h-5),(x+w-4,y+h),(x+7,y+h),(x+7,y+h-3),(x,y+h-3),(x,y+4),(x+4,y+4)]
            d.polygon(points,fill=p[4])
            if w >= 16: d.rectangle((x+7,y+4,x+w-8,y+6),fill=p[5])
            for col in range(x+5,x+w-3,10):
                d.line((col,y+4,col,y+h-5),fill=p[1])
        for y in [63,131,201]:
            d.line((0,y,247,y),fill=p[0]); d.line((0,y+1,247,y+1),fill=p[3])
    elif kind=='red':
        im.paste(p[2],(0,0,248,248)); d=ImageDraw.Draw(im)
        for _ in range(28):
            x=rng.randrange(2,235); y=rng.randrange(2,236)
            w=rng.randrange(2,8); h=rng.randrange(3,10)
            d.polygon([(x,y),(x+w,y),(x+w,y+2),(x+w-2,y+2),(x+w-2,y+h),(x,y+h)],fill=p[3])
            if y%3==0: d.line((x,y,x+w-1,y),fill=p[4])
        for _ in range(16):
            x=rng.randrange(1,245); y=rng.randrange(1,245)
            d.rectangle((x,y,x+2,y+2),fill=p[1])
    else:
        for x in range(0,248,11):
            d.rectangle((x,0,x+10,247),fill=rng.choice(p[1:4]))
            d.line((x,0,x,247),fill=p[0]); d.line((x+1,0,x+1,247),fill=p[3])
            for y in range(rng.randrange(25,65),248,77):
                d.line((x+1,y,x+10,y),fill=p[0])
                d.point((x+3,y+2),fill=p[0]); d.point((x+8,y+2),fill=p[0])
            for _ in range(3):
                y=rng.randrange(10,200)
                d.line((x+4,y,x+4,y+20),fill=p[1]); d.line((x+5,y+20,x+5,y+28),fill=p[1])
    ATLAS.paste(im,(ox+4,oy+4))
    ATLAS.paste(im.crop((0,0,1,248)).resize((4,248)),(ox,oy+4))
    ATLAS.paste(im.crop((247,0,248,248)).resize((4,248)),(ox+252,oy+4))
    ATLAS.paste(ATLAS.crop((ox,oy+4,ox+256,oy+5)).resize((256,4)),(ox,oy))
    ATLAS.paste(ATLAS.crop((ox,oy+251,ox+256,oy+252)).resize((256,4)),(ox,oy+252))
ATLAS.save(OUT/'harbor_pixels.png')

GLYPHS={
 'A':['01110','10001','10001','11111','10001','10001','10001'],
 'C':['01111','10000','10000','10000','10000','10000','01111'],
 'E':['11111','10000','10000','11110','10000','10000','11111'],
 'G':['01111','10000','10000','10111','10001','10001','01111'],
 'I':['11111','00100','00100','00100','00100','00100','11111'],
 'N':['10001','11001','11001','10101','10011','10011','10001'],
 'O':['01110','10001','10001','10001','10001','10001','01110'],
 'R':['11110','10001','10001','11110','10100','10010','10001'],
 'S':['01111','10000','10000','01110','00001','00001','11110'],
 'U':['10001','10001','10001','10001','10001','10001','01110'],
 '.':['00000','00000','00000','00000','00000','00100','00100'],
 ' ':['00000']*7,
}
signs=Image.new('RGB',(512,128),'#30343c'); d=ImageDraw.Draw(signs)
records={}
for text,rect,bg,fg in [('INSURANCE CO.',(8,8,248,56),'#465765','#dfd9bd'),('CARGO CRANE',(264,8,504,56),'#873d39','#e6c49a')]:
    x0,y0,x1,y1=rect
    d.rectangle((x0,y0,x1-1,y1-1),fill=bg)
    d.rectangle((x0+2,y0+2,x1-3,y1-3),outline=fg,width=1)
    sx=3; sy=4; width=(len(text)*6-1)*sx
    start=x0+(x1-x0-width)//2; top=y0+10
    for shadow in [True,False]:
        for index,ch in enumerate(text):
            for y,row in enumerate(GLYPHS[ch]):
                for x,bit in enumerate(row):
                    if bit=='1':
                        xx=start+index*6*sx+x*sx+(1 if shadow else 0)
                        yy=top+y*sy+(1 if shadow else 0)
                        d.rectangle((xx,yy,xx+sx-1,yy+sy-1),fill='#35303a' if shadow else fg)
    records[text]=rect
signs.save(OUT/'harbor_signs.png')
(OUT/'palette.json').write_text(json.dumps({'palette':PALETTE,'density':32,'sign_rects':records,'method':'Locally painted finite-color clusters; no normal maps, smoothing or AI texture baking.'},indent=2),encoding='utf-8')
print('R2_TEXTURES_READY',len(ATLAS.getcolors(512*512)),'atlas colors')
