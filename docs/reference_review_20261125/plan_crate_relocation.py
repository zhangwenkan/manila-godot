"""Read-only candidate check from cliff25 snapshots; never opens Blender."""
import json, sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]/'demo/tropical_harbor_3d'
LOG=ROOT/'captures/cliff_contacts_20261125'
sys.path.insert(0,str(ROOT/'source'))
from structure23_common import route_profile,polygon_distance
data=np.load(LOG/'sculpt.npz'); p=data['positions'];tri=p[data['triangles']]
q=tri[:,:,[0,1]].copy();q[:,:,1]*=-1;mn=q.min(1);mx=q.max(1)
def sample(x,z):
    mask=(mn[:,0]<=x)&(mx[:,0]>=x)&(mn[:,1]<=z)&(mx[:,1]>=z)
    a=q[mask];h=tri[mask,:,2]
    den=(a[:,1,1]-a[:,2,1])*(a[:,0,0]-a[:,2,0])+(a[:,2,0]-a[:,1,0])*(a[:,0,1]-a[:,2,1])
    ok=np.abs(den)>1e-12;a=a[ok];h=h[ok];den=den[ok]
    u=((a[:,1,1]-a[:,2,1])*(x-a[:,2,0])+(a[:,2,0]-a[:,1,0])*(z-a[:,2,1]))/den
    v=((a[:,2,1]-a[:,0,1])*(x-a[:,2,0])+(a[:,0,0]-a[:,2,0])*(z-a[:,2,1]))/den;w=1-u-v
    inside=(u>=-1e-6)&(v>=-1e-6)&(w>=-1e-6)
    hh=(u*h[:,0]+v*h[:,1]+w*h[:,2])[inside]
    assert len(hh)
    return float(hh.max())
spec=json.loads((LOG/'design.json').read_text(encoding='utf8'))
objects=json.loads((LOG/'objects_before.json').read_text(encoding='utf8'))
reports=[]
for x,z in [(23.5,43.2),(24,43.2),(24,43.25),(24.5,43.2),(25,43.2),(22.75,43.2)]:
    xy=np.array([(x+dx,z+dz) for dx in np.linspace(-.37,.37,9) for dz in np.linspace(-.37,.37,9)])
    hh=np.array([sample(*c) for c in xy]);overlaps=[]
    for o in objects:
        if any(s in o['name'] for s in ['Grass','ContourBuilt','G23_Embedded','G23_Surface','Cliff25_','C25_']):continue
        b=np.array(o['bounds']);lo=np.array([b[0,0],-b[1,1]]);hi=np.array([b[1,0],-b[0,1]])
        if hi[0]>x-.42 and lo[0]<x+.42 and hi[1]>z-.42 and lo[1]<z+.42 and b[1,2]>hh.min()-.08 and b[0,2]<hh.max()+.8:
            overlaps.append(o['name'])
    roads=[]
    for r in spec['routes']:
        margin=float(route_profile(xy[:,0],xy[:,1],r['points'])[0].min()-r['halfwidth'])
        if margin<1:roads.append([r['name'],margin])
    reports.append(dict(target=[x,z],height_range=[float(hh.min()),float(hh.max())],spread=float(np.ptp(hh)),overlaps=overlaps,nearby_road_clearance=roads))
(LOG/'crate_relocation_candidates.json').write_text(json.dumps(reports,indent=2),encoding='utf8')
print(json.dumps(reports,indent=2))
