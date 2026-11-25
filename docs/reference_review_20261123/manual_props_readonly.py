"""Read-only sampling of proposed specific prop placements."""
from pathlib import Path
import json,sys,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2]/'demo/tropical_harbor_3d'
LOG=ROOT/'captures/terrain_structure_20261123'
sys.path.insert(0,str(ROOT/'source'))
import structure23_common as util
rec={r['name']:r for r in json.loads((LOG/'objects_before.json').read_text(encoding='utf8'))}
report=json.loads((LOG/'props.json').read_text(encoding='utf8'))
groups={g['group']:g for g in report['groups']}
design=json.loads((LOG/'design.json').read_text(encoding='utf8'))
d=np.load(LOG/'land_data.npz');h=d['height'];normal=d['normal'];land=d['land'];N=len(h)
def samples(xz):
    xz=np.asarray(xz);ix=np.clip(((xz[:,0]+4)/48*N).astype(int),0,N-1);iy=np.clip(((xz[:,1]+15)/97*N).astype(int),0,N-1)
    return h[iy,ix],normal[iy,ix],land[iy,ix]
def box(name):
    b=np.array(rec[name]['bounds']);return np.array([b[0,0],-b[1,1],b[1,0],-b[0,1]])
def groupbox(key):
    gg=groups[key];foot=gg['before_support_blender'][2]
    bb=[box(name) for name in gg['objects'] if rec[name]['bounds'][0][2]<foot+1.15]
    bb=np.array(bb);return np.r_[bb[:,:2].min(0),bb[:,2:].max(0)]
def placed(key,shift=(0,0),angle=0,pivot=None):
    b=groupbox(key);p=np.array([[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]]]);pivot=(p.mean(0) if pivot is None else np.array(pivot))
    c,s=np.cos(np.radians(angle)),np.sin(np.radians(angle));r=np.array([[c,-s],[s,c]])
    return (p-pivot)@r.T+pivot+shift
def inspect(key,shift=(0,0),angle=0,pivot=None):
    pp=placed(key,shift,angle,pivot);lo,hi=pp.min(0),pp.max(0);xx,zz=np.meshgrid(np.linspace(lo[0],hi[0],8),np.linspace(lo[1],hi[1],10));p=np.c_[xx.ravel(),zz.ravel()];p=p[util.polygon_distance(p[:,0],p[:,1],pp)<=.001]
    hh,nn,ll=samples(p);routes=[]
    for r in design['routes']:
        dist,_=util.route_profile(p[:,0],p[:,1],r['points']);margin=float(dist.min()-r['halfwidth'])
        if margin<.2:routes.append((r['name'],margin))
    return dict(group=key,shift=list(shift),angle=angle,footprint=pp.tolist(),height_range=[float(hh.min()),float(hh.max())],height_span=float(np.ptp(hh)),min_normal=float(nn.min()),routes=routes)
def mapview(name,bounds,scale=75):
    x0,z0,x1,z1=bounds;W=int((x1-x0)*scale);H=int((z1-z0)*scale);yy,xx=np.mgrid[:H,:W];pp=np.c_[x0+(xx.ravel()+.5)/scale,z0+(yy.ravel()+.5)/scale];hh,nn,ll=samples(pp)
    colors=np.array([[89,139,67],[132,132,134],[182,153,107],[125,99,68]])
    rgb=ll@colors+np.maximum(0,1-ll.sum(1))[:,None]*np.array([236,215,173]);rgb*=np.clip(nn[:,None]*.22+.78,.7,1)
    contour=np.abs(hh/.25-np.round(hh/.25))<.035;rgb[contour]*=.65
    im=Image.fromarray(np.uint8(np.clip(rgb.reshape(H,W,3),0,255)));dr=ImageDraw.Draw(im)
    def point(p):return ((p[0]-x0)*scale,(p[1]-z0)*scale)
    for zz in np.arange(np.ceil(z0),z1,1):dr.text((2,(zz-z0)*scale),str(int(zz)),fill='white')
    for xx in np.arange(np.ceil(x0),x1,1):dr.text(((xx-x0)*scale,2),str(int(xx)),fill='white')
    for key,r in rec.items():
        if not key.startswith(('Town_Floor','Hut_Floor')):continue
        b=box(key);dr.rectangle([point(b[:2]),point(b[2:])],outline='white',width=2);dr.text(point(b[:2]),key.replace('Town_Floor','T').replace('Hut_Floor','H'),fill='white')
    for key,g in groups.items():
        b=groupbox(key);shift=np.array([g['delta_blender'][0],-g['delta_blender'][1]]);b+=np.tile(shift,2)
        if b[0]>x1 or b[2]<x0 or b[1]>z1 or b[3]<z0:continue
        dr.rectangle([point(b[:2]),point(b[2:])],outline=(245,90,80) if 'manual' in g['status'] else (45,55,45),width=2)
        dr.text(point(b[:2]),g['group'].split(':')[-1],fill=(255,255,255))
    out=Path(__file__).parent/(name+'.png');im.save(out);return str(out)
if __name__=='__main__':
    print(mapview('manual_north_positions',(12,11,19,24)))
    print(mapview('manual_shore_positions',(5.5,37,13,45)))
    cases=[('market_stall:Town_MarketPost.004',(0,-2.8),0,None),('market_stall:Town_MarketPost.004',(.1,-3.3),0,None),
           ('seating:Town_TableLeg.008',(.335,-.044),90,(13.885,22.064)),
           ('coast_prop:S20_NetPost',(-.25,0),0,None),('coast_prop:S20_NetPost',(-.25,1.2),0,None),
           ('coast_prop:S20_StackBearers',(-.45,1.4),0,None),('coast_prop:S20_fishing_Crate_Frame.005',(-1.0,1.8),0,None)]
    result=[inspect(*args) for args in cases];(Path(__file__).parent/'manual_props_candidates.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2))
