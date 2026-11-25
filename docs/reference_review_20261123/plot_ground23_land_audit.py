"""Read-only plan view of G23 authored roles, terrain height and fixed floors."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
CAP = ROOT / "demo/tropical_harbor_3d/captures"
LOG = CAP / "ground_integration_20261123"
data = np.load(LOG / "land_data.npz")
land, height, normal = data["land"], data["height"], data["normal"]
n = len(land)
x = -4 + 48 * (np.arange(n) + .5) / n
z = -15 + 97 * (np.arange(n) + .5) / n
sand = np.maximum(0, 1 - land.sum(axis=2))
weights = np.concatenate([land, sand[..., None]], axis=2)
palette = np.array([[.28,.57,.20], [.48,.50,.55], [.63,.46,.27], [.40,.25,.13], [.91,.82,.60]])
rgb = np.clip(weights @ palette, 0, 1)
floors = json.loads((CAP / "rock_path_sample_20261123/foundations.json").read_text(encoding="utf-8"))
canvas=Image.new('RGB',(1800,1950),'#f7f8fa');draw=ImageDraw.Draw(canvas)
fontpath='C:/Windows/Fonts/arial.ttf'
font=ImageFont.truetype(fontpath,20);small=ImageFont.truetype(fontpath,16)
big=ImageFont.truetype(fontpath,28);bold=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',20)
draw.text((50,25),'G23 land occupation audit — role weights + 1 m height contours',font=big,fill='#172a32')
draw.text((50,65),'Top view: screen up is +Z. White rectangles = 9 preserved building floors. Dark contours = integer metres.',font=font,fill='#34444f')
for bounds,box,title in [((-4,44,-15,82),(100,180,820,1635),'Whole map: x -4..44, z -15..82'),
                         ((8,30,0,54),(1030,180,1623,1635),'Focus: x 8..30, z 0..54')]:
    xmin,xmax,zmin,zmax=bounds;left,top,right,bottom=box
    w,h=right-left,bottom-top
    ix=np.clip(((np.linspace(xmin,xmax,w,endpoint=False)+(xmax-xmin)/(2*w)+4)/48*n).astype(int),0,n-1)
    iz=np.clip(((np.linspace(zmax,zmin,h,endpoint=False)-(zmax-zmin)/(2*h)+15)/97*n).astype(int),0,n-1)
    panel=np.round(rgb[iz[:,None],ix[None,:]]*255).astype(np.uint8)
    ph=height[iz[:,None],ix[None,:]];levels=np.floor(ph).astype(int)
    contour=np.zeros((h,w),bool)
    contour[1:]|=(levels[1:]!=levels[:-1]);contour[:,1:]|=(levels[:,1:]!=levels[:,:-1])
    contour&=(ph>=0)&(ph<=9)
    panel[contour]=(panel[contour]*.35+np.array([23,42,50])*.65).astype(np.uint8)
    canvas.paste(Image.fromarray(panel), (left,top))
    def xy(wx,wz):return (left+(wx-xmin)/(xmax-xmin)*w,top+(zmax-wz)/(zmax-zmin)*h)
    draw.rectangle(box,outline='#1c2830',width=2)
    draw.text((left,135),title,font=bold,fill='#172a32')
    for xt in np.arange(np.ceil(xmin/2)*2,xmax+.1,2):
        px,_=xy(xt,zmin);draw.line((px,bottom,px,bottom+8),fill='#172a32',width=1)
        draw.text((px-8,bottom+13),str(int(xt)),font=small,fill='#172a32')
    for zt in np.arange(np.ceil(zmin/5)*5,zmax+.1,5):
        _,py=xy(xmin,zt);draw.line((left-8,py,left,py),fill='#172a32',width=1)
        draw.text((left-45,py-8),str(int(zt)),font=small,fill='#172a32')
    draw.text((left+w/2-80,bottom+42),'Godot world X (m)',font=font,fill='#172a32')
    draw.text((left-55,top-30),'Z (m)',font=small,fill='#172a32')
    for i,row in enumerate(floors,1):
        p=np.array(row['corners'][:4])[:,[0,1]];p[:,1]*=-1
        center=p.mean(axis=0)
        if not (xmin<=center[0]<=xmax and zmin<=center[1]<=zmax):continue
        poly=[xy(*v) for v in p]
        draw.polygon(poly,fill='#f3f0e4',outline='#172a32',width=3)
        cx,cy=xy(*center);draw.text((cx-7,cy-12),str(i),font=bold,fill='#172a32')
    if xmin<0:
        a=xy(8,54);b=xy(30,0);draw.rectangle((*a,*b),outline='#ce2832',width=3)
roles=['Grass (R)','Rock (G)','Path (B)','Soil (A)','Sand (residual)']
for i,(color,name) in enumerate(zip(palette,roles)):
    sx=100+i*315
    draw.rectangle((sx,1745,sx+30,1773),fill=tuple(np.round(color*255).astype(int)))
    draw.text((sx+42,1747),name,font=font,fill='#172a32')
for i,row in enumerate(floors,1):
    sx=100+((i-1)%3)*530;sy=1810+((i-1)//3)*36
    draw.text((sx,sy),f"{i}: {row['name']}",font=font,fill='#172a32')
path=LOG/'land_audit_v2.png';canvas.save(path)
mask=(x[None,:]>=10)&(x[None,:]<=32)&(z[:,None]>=12)&(z[:,None]<=52)&(height>.4)
steep=mask&(normal<.65)
summary={"file":str(path), "floor_count":len(floors), "roles_rgba":"grass,rock,path,soil; residual sand",
         "orientation":"array bottom row z=-15, top row z=82", "core_old_map_mix_region_xz":[10,12,32,52],
         "core_steep_pixels":int(steep.sum()), "steep_rock_dominant":int((steep&(land[:,:,1]>.5)).sum()),
         "steep_grass_dominant":int((steep&(land[:,:,0]>.5)).sum()),
         "steep_soil_dominant":int((steep&(land[:,:,3]>.5)).sum())}
(LOG/'land_audit_v2.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary))
