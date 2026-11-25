"""Compose unretouched same-camera review sheets from observed runtime images."""
from pathlib import Path
import argparse,json
from PIL import Image,ImageDraw,ImageFont

p=argparse.ArgumentParser()
p.add_argument('--before',type=Path,required=True)
p.add_argument('--after',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',26)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
views=[('town_civic_street.png','医院—餐厅—酒吧'),('town_market_chapel.png','医院岩脚与餐厅院地'),('terrace_cross_street.png','酒吧后方岩面与上层街道')]
w,h=960,540
sheet=Image.new('RGB',(w*2,(h+44)*len(views)),(29,35,39));d=ImageDraw.Draw(sheet)
for i,(name,title) in enumerate(views):
    for j,(folder,label) in enumerate(((a.before,'上轮'),(a.after,'本轮'))):
        image=Image.open(folder/name).convert('RGB')
        assert image.size==(1600,900)
        sheet.paste(image.resize((w,h),Image.Resampling.LANCZOS),(j*w,i*(h+44)+44))
        d.text((j*w+18,i*(h+44)+6),label+' · '+title,font=font,fill=(238,238,231))
sheet.save(a.out/'final_before_after.jpg',quality=93,subsampling=0)
gallery=Image.new('RGB',(1600,988),(29,35,39));d=ImageDraw.Draw(gallery)
for i,(name,title) in enumerate(views+[('02_town_waterfront.png','正常海岸机位')]):
    x=(i%2)*800;y=(i//2)*494
    gallery.paste(Image.open(a.after/name).convert('RGB').resize((800,450),Image.Resampling.LANCZOS),(x,y+44))
    d.text((x+16,y+9),title,font=small,fill=(238,238,231))
gallery.save(a.out/'final_gallery.jpg',quality=93,subsampling=0)
(a.out/'review_image_sources.json').write_text(json.dumps({'before':str(a.before),'after':str(a.after),'views':views,'method':'Only whole-image scaling and labels; no local edits or retouching.'},ensure_ascii=False,indent=2),encoding='utf8')
print(a.out/'final_before_after.jpg')
