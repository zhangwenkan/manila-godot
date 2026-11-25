"""Revise only G23 rock surface: unequal overlapping mineral planes, live MCP."""
import bpy,ast,math,json,struct,zlib,numpy as np
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;OUT=ROOT/'assets/reference';LOG=ROOT/'captures/ground_integration_20261123'
for node in ast.parse((ROOT/'source/ground23_02_surfaces.py').read_text(encoding='utf8')).body:
    if isinstance(node,ast.FunctionDef) and node.name in ('ss','noise','save_image'):
        exec(compile(ast.Module(body=[node],type_ignores=[]),'surface helpers','exec'),globals())
n=2048;Y,X=np.mgrid[0:n,0:n].astype(np.float32)/n
macro=noise(n,5,901);mid=noise(n,24,902);fine=noise(n,110,903)
rgb=np.empty((n,n,3),np.float32);rgb[:]=[.40,.423,.396]
rgb+=(macro*.065+mid*.026+fine*.012)[...,None]
height=.39+macro*.06+mid*.045+fine*.014
rng=np.random.default_rng(941)
def face(poly,tint,tilt,raiseby,bevel):
    global rgb,height
    for ox in (-1,0,1):
      for oy in (-1,0,1):
        p=[(a+ox,b+oy) for a,b in poly]
        x0=max(0,int(min(a for a,b in p)*n)-1);x1=min(n,int(max(a for a,b in p)*n)+2)
        y0=max(0,int(min(b for a,b in p)*n)-1);y1=min(n,int(max(b for a,b in p)*n)+2)
        if x1<=x0 or y1<=y0:continue
        xx=X[y0:y1,x0:x1];yy=Y[y0:y1,x0:x1]
        inside=np.zeros(xx.shape,bool);dist=np.full(xx.shape,100,np.float32)
        for (a,b),(c,d) in zip(p,p[1:]+p[:1]):
            if abs(d-b)>1e-9:inside^=((b>yy)!=(d>yy))&(xx<(c-a)*(yy-b)/(d-b)+a)
            dx,dy=c-a,d-b;t=np.clip(((xx-a)*dx+(yy-b)*dy)/(dx*dx+dy*dy),0,1)
            dist=np.minimum(dist,np.hypot(xx-a-t*dx,yy-b-t*dy))
        weight=ss(0,.0012,dist)*inside;edge=ss(.0006,bevel,dist)
        cx=sum(a for a,b in p)/len(p);cy=sum(b for a,b in p)/len(p)
        plane=np.clip((xx-cx)*tilt[0]+(yy-cy)*tilt[1],-.12,.12)
        color=np.array([.421,.445,.414])+tint+(macro[y0:y1,x0:x1]*.050+mid[y0:y1,x0:x1]*.020+fine[y0:y1,x0:x1]*.010)[...,None]
        color-=(1-edge)[...,None]*.018
        rgb[y0:y1,x0:x1]=rgb[y0:y1,x0:x1]*(1-weight[...,None])+color*weight[...,None]
        newh=.43+raiseby+plane+mid[y0:y1,x0:x1]*.035-(1-edge)*.10
        height[y0:y1,x0:x1]=height[y0:y1,x0:x1]*(1-weight)+newh*weight
# Large planes overlap and break one another; no common five-row grid.
for k in range(54):
    cx,cy=rng.random(2);rx=rng.uniform(.045,.135);ry=rng.uniform(.026,.105)
    angle=rng.uniform(-.40,.40);poly=[]
    for theta in np.linspace(0,math.tau,7,endpoint=False):
        r=rng.uniform(.76,1.13);a=math.cos(theta)*rx*r;b=math.sin(theta)*ry*r
        poly.append((cx+a*math.cos(angle)-b*math.sin(angle),cy+a*math.sin(angle)+b*math.cos(angle)))
    face(poly,rng.uniform(-.043,.045),rng.uniform(-1.25,1.25,2),rng.uniform(.025,.15),rng.uniform(.003,.011))
# Selected smaller chips sit on planes; quiet areas remain broad and readable.
for k in range(38):
    cx,cy=rng.random(2);rx=rng.uniform(.014,.040);ry=rng.uniform(.008,.022)
    poly=[(cx-rx,cy-ry*.4),(cx-rx*.4,cy-ry),(cx+rx,cy-ry*.3),(cx+rx*.6,cy+ry),(cx-rx*.8,cy+ry*.6)]
    face(poly,rng.uniform(-.018,.035),rng.uniform(-1,1,2),rng.uniform(.02,.09),.0025)
image=save_image('G23_Rock',rgb,height)
mat=bpy.data.objects['C25_ContourBuiltCoast'].data.materials[0]
for nd in mat.node_tree.nodes:
    if nd.type=='TEX_IMAGE' and ('G23_Rock'==nd.name or nd.name=='G23Preview Rock'):nd.image=image
(LOG/'rock_revision.json').write_text(json.dumps({'planes':54,'local_chips':38,'layout':'unequal overlapping slanted mineral faces, no horizontal common rows','height_range':[float(height.min()),float(height.max())],'texture_only':True},indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Revised broad mineral planes, saved current source including rooted grass')
