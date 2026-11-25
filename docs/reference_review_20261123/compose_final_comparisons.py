"""Compose actual fixed-camera captures; no retouching or asset generation."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
root=Path(__file__).resolve().parents[2]
captures=root/'demo/tropical_harbor_3d/captures'
before=captures/'art_20261121_220358_404352'
after=captures/'art_20261123_184537_894398'
out=captures/'rock_path_sample_20261123'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',23)
for name,title in [('terrace_cross_street','岩壁样段'),('town_market_chapel','门前道路样段')]:
 canvas=Image.new('RGB',(1600,494),'#182324');draw=ImageDraw.Draw(canvas)
 for i,(folder,label) in enumerate([(before,'11月21日 · 修改前'),(after,'11月23日 · 当前样段')]):
  im=Image.open(folder/(name+'.png')).convert('RGB');assert im.size==(1600,900)
  canvas.paste(im.resize((800,450),Image.Resampling.LANCZOS),(800*i,44))
  draw.text((18+800*i,9),title+'  |  '+label,font=font,fill='#ecf0e8')
 path=out/(name+'_compare.jpg');canvas.save(path,quality=90);print(path)
for name in ['terrace_cross_street','town_market_chapel','town_civic_street','03_mid_coast']:
 im=Image.open(after/(name+'.png')).convert('RGB');im.thumbnail((1200,675));im.save(out/(name+'_final.jpg'),quality=90)
