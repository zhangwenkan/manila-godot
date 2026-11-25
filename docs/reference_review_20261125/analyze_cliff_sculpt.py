"""Read-only compare immutable baseline and live-exported sculpt snapshots."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
REPO=Path(__file__).resolve().parents[2];ROOT=REPO/'demo/tropical_harbor_3d'
LOG=ROOT/'captures/cliff_contacts_20261125';OUT=Path(__file__).resolve().parent
b=np.load(LOG/'baseline.npz');s=np.load(LOG/'sculpt.npz')
p=b['positions'].astype(float);q=s['positions'].astype(float);tri=b['triangles']
p[:,1]*=-1;q[:,1]*=-1
delta=q[:,2]-p[:,2];changed=np.any(abs(delta[tri])>1e-6,axis=1)
def slopes(v):
    n=np.cross(v[tri[:,1]]-v[tri[:,0]],v[tri[:,2]]-v[tri[:,0]])
    return np.rad2deg(np.arctan2(np.linalg.norm(n[:,:2],axis=1),abs(n[:,2]))),n
old,on=slopes(p);new,nn=slopes(q);cen=q[tri].mean(1)
ids=np.flatnonzero(changed);top=ids[np.argsort(new[ids])[-35:][::-1]]
records=[]
for i in top:
    pts=q[tri[i],:2];ed=np.linalg.norm(np.roll(pts,-1,axis=0)-pts,axis=1)
    area=abs(np.cross(pts[1]-pts[0],pts[2]-pts[0]))*.5
    records.append({'face':int(i),'vertices':tri[i].tolist(),'center_xzh':cen[i].tolist(),
      'old_slope':float(old[i]),'new_slope':float(new[i]),'delta_slope':float(new[i]-old[i]),
      'projected_area':float(area),'min_altitude':float(2*area/max(ed)),
      'old_xzh':p[tri[i]].tolist(),'new_xzh':q[tri[i]].tolist(),
      'freedom':s['freedom'][tri[i]].tolist(),'weight':s['applied_weight'][tri[i]].tolist()})
regions=[]
for name,z0,z1 in [('A',22.2,27.55),('B',26.95,33.5),('C',37.6,45.0)]:
    ix=changed&(cen[:,1]>=z0)&(cen[:,1]<=z1)
    regions.append({'region':name,'faces':int(ix.sum()),'old_max':float(old[ix].max()),'new_max':float(new[ix].max()),
       'old_p95':float(np.percentile(old[ix],95)),'new_p95':float(np.percentile(new[ix],95)),
       'new_over_75':int(np.count_nonzero(ix&(new>75))),
       'new_over_75_increased_over_10':int(np.count_nonzero(ix&(new>75)&(new-old>10)))})
summary={'top_faces':records,'regions':regions,'changed_faces':int(changed.sum()),
         'over75':int(np.count_nonzero(changed&(new>75))),
         'over75_more10':int(np.count_nonzero(changed&(new>75)&(new-old>10)))}
(OUT/'cliff_sculpt_slope_review.json').write_text(json.dumps(summary,indent=2),encoding='utf8')

def sample(v,xs,z):
    tp=v[tri];a=tp[(tp[:,:,1].min(1)<=z+1e-7)&(tp[:,:,1].max(1)>=z-1e-7)];out=[]
    for x in xs:
        v=a[(a[:,:,0].min(1)<=x+1e-7)&(a[:,:,0].max(1)>=x-1e-7)]
        d=v[:,1:,:2]-v[:,:1,:2];rhs=np.array([x,z])-v[:,0,:2]
        uv=np.linalg.solve(np.transpose(d,(0,2,1)),rhs[...,None])[...,0]
        hit=(uv.min(1)>=-1e-6)&(uv.sum(1)<=1+1e-6)
        hh=v[:,0,2]+np.sum(uv*(v[:,1:,2]-v[:,:1,2]),axis=1)
        out.append(float(hh[hit].max()) if hit.any() else None)
    return out
zs=[23,25,26.8,27.5,28.5,29,30,31.5,32.8,38.2,40.2,41.4,42,43.4,43.8]
xs=np.arange(16,23.001,.025)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
im=Image.new('RGB',(1200,1160),'#f4f2e9');dr=ImageDraw.Draw(im)
for i,z in enumerate(zs):
    col=i%3;row=i//3;ox=col*400+28;oy=row*220+35
    dr.text((ox,oy-25),'Z = '+str(z)+'   grey before / red sculpt',fill='black',font=small)
    dr.rectangle((ox,oy,ox+350,oy+170),outline='#bbb')
    for hh in [1,2,3,4]:
        yy=oy+170-hh*34;dr.line((ox,yy,ox+350,yy),fill='#ddd');dr.text((ox,yy),str(hh),fill='#888',font=small)
    for v,color in [(p,'#888888'),(q,'#a82c28')]:
        hs=sample(v,xs,z);pts=[(ox+(x-16)/7*350,oy+170-h*34) for x,h in zip(xs,hs) if h is not None]
        dr.line(pts,fill=color,width=2)
    for x in [16,18,20,22]:dr.text((ox+(x-16)/7*350-5,oy+174),str(x),fill='black',font=small)
im.save(OUT/'cliff_sculpt_section_comparison.png')

im=Image.new('RGB',(1240,1250),'#f4f2e9');dr=ImageDraw.Draw(im)
def xy(x,z):return (60+(x-15.5)*110,70+(z-21.5)*49)
for i in np.flatnonzero((cen[:,0]>15.5)&(cen[:,0]<25.5)&(cen[:,1]>21.5)&(cen[:,1]<45.5)):
    if not changed[i]:color='#deded5'
    else:
        t=np.clip(new[i]/85,0,1);color=tuple(int(c) for c in np.array([91,152,93])*(1-t)+np.array([190,45,30])*t)
    dr.polygon([xy(x,z) for x,z,_ in q[tri[i]]],fill=color)
for rec in records[:15]:
    x,z,h=rec['center_xzh'];px,py=xy(x,z)
    dr.ellipse((px-5,py-5,px+5,py+5),outline='#111',width=2)
    dr.text((px+6,py),str(rec['face']),fill='#111',font=small)
dr.text((60,15),'Changed-face slopes: green low / red near vertical; grey untouched',fill='#111',font=font)
for x in np.arange(16,26,1):px,py=xy(x,21.5);dr.text((px-7,45),str(x),fill='#111',font=small)
for z in np.arange(22,46,1):px,py=xy(15.5,z);dr.text((27,py-7),str(z),fill='#111',font=small)
im.save(OUT/'cliff_sculpt_slope_plan.png')
print(json.dumps({'regions':regions,'top':[{k:r[k] for k in ['face','center_xzh','old_slope','new_slope','min_altitude','freedom']} for r in records[:12]]},indent=2))
