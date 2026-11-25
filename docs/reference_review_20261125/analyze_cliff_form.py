"""Read-only terrain analysis. Writes diagnostic JSON and PNG, never runtime assets."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont

REPO=Path(__file__).resolve().parents[2]
ROOT=REPO/'demo/tropical_harbor_3d'
LOG=ROOT/'captures/terrain_structure_20261123'
OUT=Path(__file__).resolve().parent
n=np.load(LOG/'slope_cleanup.npz')
p=n['positions'].astype(float); p[:,1]*=-1
tri=n['triangles']; tp=p[tri]
spec=json.loads((LOG/'design.json').read_text())
objects=json.loads((LOG/'objects_before.json').read_text())

def sample(xs,z):
    a=tp[(tp[:,:,1].min(1)<=z+1e-7)&(tp[:,:,1].max(1)>=z-1e-7)]
    out=[]
    for x in xs:
        v=a[(a[:,:,0].min(1)<=x+1e-7)&(a[:,:,0].max(1)>=x-1e-7)]
        d=v[:,1:,:2]-v[:,:1,:2]
        rhs=np.array([x,z])-v[:,0,:2]
        uv=np.linalg.solve(np.transpose(d,(0,2,1)),rhs[...,None])[...,0]
        hit=(uv.min(1)>=-1e-6)&(uv.sum(1)<=1+1e-6)
        hh=v[:,0,2]+np.sum(uv*(v[:,1:,2]-v[:,:1,2]),axis=1)
        out.append(float(hh[hit].max()) if hit.any() else None)
    return out

xs=np.arange(12,24.001,.125)
sections=[]
for z in [20,21.5,23,25,27,28.5,30,31.5,33,34.5,36,38,40,42,44]:
    heights=sample(xs,z)
    sections.append({'z':z,'x':xs.tolist(),'height':heights})
(OUT/'cliff_existing_sections.json').write_text(json.dumps(sections,indent=2),encoding='utf8')

W,H=1200,1500
im=Image.new('RGB',(W,H),'#f4f2e9');dr=ImageDraw.Draw(im)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
def xy(x,z):return (80+(x-8)*45,70+(z-17)*43)
mask=(tp[:,:,0].min(1)<30)&(tp[:,:,0].max(1)>8)&(tp[:,:,1].min(1)<48)&(tp[:,:,1].max(1)>17)
for vv in tp[mask]:
    h=vv[:,2].mean(); t=np.clip((h-.3)/4.7,0,1)
    color=tuple(int(c) for c in (np.array([213,207,167])*(1-t)+np.array([67,109,74])*t))
    dr.polygon([xy(x,z) for x,z,_ in vv],fill=color)
for route in spec['routes']:
    pts=route['points']; dr.line([xy(*q[:2]) for q in pts],fill='#e7b444',width=max(1,int(route['halfwidth']*2*45)))
    dr.line([xy(*q[:2]) for q in pts],fill='#a64b20',width=2)
for court in spec['platforms']:
    dr.polygon([xy(*q) for q in court['polygon']],outline='#dd6a25',width=2)
for obj in objects:
    if not obj['name'].startswith(('Town_Floor','Hut_Floor')):continue
    lo,hi=np.array(obj['bounds']);xz=[lo[0],-hi[1],hi[0],-lo[1]]
    if xz[1]>48 or xz[3]<17:continue
    dr.rectangle([xy(xz[0],xz[1]),xy(xz[2],xz[3])],fill='#bec5ca',outline='#202c39',width=2)
    dr.text(xy(xz[0],(xz[1]+xz[3])/2),obj['name'],fill='#10151b',font=small)
for x in range(8,31,2):
    q=xy(x,17);dr.text((q[0]-8,44),str(x),fill='black',font=font)
for z in range(18,49,2):
    q=xy(8,z);dr.text((38,q[1]-8),str(z),fill='black',font=font)
dr.text((80,12),'Final saved terrain: height + protected route/court/floor footprints (Godot X/Z)',fill='black',font=font)
im.save(OUT/'cliff_existing_plan.png')

im=Image.new('RGB',(1200,1160),'#f4f2e9');dr=ImageDraw.Draw(im)
for i,s in enumerate(sections):
    col=i%3;row=i//3;ox=col*400+28;oy=row*220+35
    dr.text((ox,oy-25),'Z = '+str(s['z']),fill='black',font=font)
    dr.rectangle((ox,oy,ox+350,oy+170),outline='#bbb')
    for hh in [1,2,3,4]:
        yy=oy+170-hh*34;dr.line((ox,yy,ox+350,yy),fill='#ddd');dr.text((ox,yy),str(hh),fill='#888',font=small)
    pts=[(ox+(x-12)/12*350,oy+170-h*34) for x,h in zip(s['x'],s['height']) if h is not None]
    dr.line(pts,fill='#61442a',width=3)
    for x in [12,16,20,24]:dr.text((ox+(x-12)/12*350-5,oy+174),str(x),fill='black',font=small)
im.save(OUT/'cliff_existing_sections.png')
print('Saved diagnostics. Coarse heights at X=14,16,18,20,22,24:')
for s in sections:print(s['z'],[round(s['height'][int((x-12)/.125)],2) for x in [14,16,18,20,22,24]])
