"""Create G23 authored material surfaces inside the owned GUI Blender MCP.
RGB is sRGB reflectance, alpha is linear surface height. No baked sun shadows.
This is repeatable texture authoring, not a replay of prior geometry edits.
"""
import bpy, json, math, struct, zlib, numpy as np
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/ground_integration_20261123'; OUT=ROOT/'assets/reference'

def ss(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

def save_image(name,rgb,height,linear=False):
    rgba=np.concatenate((np.clip(rgb,0,1),np.clip(height,0,1)[...,None]),axis=2)
    h,w=rgba.shape[:2];data=np.round(rgba[::-1]*255).astype(np.uint8)
    def chunk(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    raw=b''.join(b'\0'+r.tobytes() for r in data)
    path=OUT/(name+'.png')
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b''))
    old=bpy.data.images.get(name)
    if old:bpy.data.images.remove(old)
    im=bpy.data.images.load(str(path),check_existing=False);im.name=name
    im.colorspace_settings.name='Non-Color' if linear else 'sRGB'
    im.alpha_mode='CHANNEL_PACKED';im.pack()
    return im

def noise(n,cells,seed):
    rng=np.random.default_rng(seed);grid=rng.random((cells,cells)).astype(np.float32)
    v,u=np.mgrid[0:n,0:n].astype(np.float32)*cells/n
    ix=u.astype(np.int32);iy=v.astype(np.int32);fx=ss(0,1,u-ix);fy=ss(0,1,v-iy)
    return ((grid[iy%cells,ix%cells]*(1-fx)+grid[iy%cells,(ix+1)%cells]*fx)*(1-fy)
        +(grid[(iy+1)%cells,ix%cells]*(1-fx)+grid[(iy+1)%cells,(ix+1)%cells]*fx)*fy)-.5

def ellipse(rgb,h,cx,cy,rx,ry,angle,tint,lift,edge=.2):
    n=len(h);extent=max(rx,ry)*1.1
    for ox in (-1,0,1):
      for oy in (-1,0,1):
        x,y=cx+ox,cy+oy
        x0=max(0,int((x-extent)*n));x1=min(n,int((x+extent)*n)+1)
        y0=max(0,int((y-extent)*n));y1=min(n,int((y+extent)*n)+1)
        if x1<=x0 or y1<=y0:continue
        Y,X=np.mgrid[y0:y1,x0:x1].astype(np.float32)/n;X-=x;Y-=y
        a=X*math.cos(angle)+Y*math.sin(angle);b=-X*math.sin(angle)+Y*math.cos(angle)
        d=np.sqrt((a/rx)**2+(b/ry)**2)
        weight=1-ss(1-edge,1,d)
        rgb[y0:y1,x0:x1]+=weight[...,None]*np.asarray(tint)
        h[y0:y1,x0:x1]+=weight*lift

images={};n=1024
# Tufts have directional short leaves and dark roots, with quiet patches between.
broad=noise(n,4,101);mid=noise(n,17,102);fine=noise(n,95,103)
rgb=np.empty((n,n,3),np.float32);rgb[:]=[.315,.422,.142]
rgb+=(broad*.085+mid*.036+fine*.015)[...,None]*[.85,1,.46]
h=.38+broad*.09+mid*.08
rng=np.random.default_rng(123)
for k in range(2600):
    cx,cy=rng.random(2);angle=rng.uniform(0,math.tau)
    # A clump's leaves share direction locally, rather than independent white speckles.
    variation=rng.uniform(-.018,.027)
    ellipse(rgb,h,cx,cy,.012,.008,angle,[-.024,-.026,-.011],-.08,.55)
    for blade in range(3):
        a=angle+rng.uniform(-.6,.6);length=rng.uniform(.013,.036)
        bx=cx+math.cos(a)*length*.35;by=cy+math.sin(a)*length*.35
        ellipse(rgb,h,bx,by,length,.0025+rng.random()*.002,a,
                [variation+.031,variation+.043,variation*.5+.013],rng.uniform(.09,.20),.5)
images['G23_Grass']=save_image('G23_Grass',rgb,h)
# Packed footpath: compacted broad patches and sparse embedded grit, not a yellow stripe.
broad=noise(n,5,201);mid=noise(n,24,202);grain=noise(n,157,203)
rgb=np.empty((n,n,3),np.float32);rgb[:]=[.526,.456,.344]
rgb+=(broad*.075+mid*.033+grain*.022)[...,None]*[1,.92,.78]
h=.43+mid*.1+grain*.1
rng=np.random.default_rng(224)
for k in range(1150):
    cx,cy=rng.random(2);r=rng.uniform(.0015,.0065);tint=rng.uniform(-.05,.05)
    ellipse(rgb,h,cx,cy,r,r*rng.uniform(.45,.85),rng.uniform(0,math.tau),[tint,tint*.92,tint*.82],rng.uniform(.04,.14),.4)
images['G23_Path']=save_image('G23_Path',rgb,h)
# Exposed soil: compact larger aggregates, lower pockets and a fine granular matrix.
broad=noise(n,6,301);mid=noise(n,26,302);grain=noise(n,142,303)
rgb=np.empty((n,n,3),np.float32);rgb[:]=[.466,.353,.225]
rgb+=(broad*.085+mid*.054+grain*.024)[...,None]*[1,.88,.64]
h=.35+broad*.13+mid*.19+grain*.08
rng=np.random.default_rng(324)
for k in range(620):
    cx,cy=rng.random(2);r=rng.uniform(.006,.024);a=rng.uniform(0,math.tau)
    ellipse(rgb,h,cx,cy,r,r*rng.uniform(.46,.8),a,[-.026,-.021,-.015],-.09,.3)
    ellipse(rgb,h,cx+r*.10,cy+r*.07,r*.83,r*.58,a,[.048,.040,.028],.24,.25)
images['G23_Soil']=save_image('G23_Soil',rgb,h)
# Fine sand retains broad calm areas. Larger mottles are deposited grains, not ripples.
broad=noise(n,4,401);mid=noise(n,19,402);grain=noise(n,211,403)
rgb=np.empty((n,n,3),np.float32);rgb[:]=[.786,.711,.548]
rgb+=(broad*.055+mid*.020+grain*.018)[...,None]*[1,.96,.83]
h=.47+mid*.10+grain*.13
rng=np.random.default_rng(424)
for k in range(300):
    cx,cy=rng.random(2);r=rng.uniform(.001,.0035)
    ellipse(rgb,h,cx,cy,r,r*.7,rng.uniform(0,6.28),[-.05,-.047,-.04],.10,.25)
images['G23_Sand']=save_image('G23_Sand',rgb,h)
# Broad fractured mineral planes. Unequal cells, non-horizontal fractures and
# partial narrow edges replace the old repeating five rows of rounded blocks.
n=2048;Y,X=np.mgrid[0:n,0:n].astype(np.float32)/n
gx=X*5;gy=Y*5
ix=gx.astype(np.int32);iy=gy.astype(np.int32)
rng=np.random.default_rng(521);jitter=rng.uniform(.12,.88,(5,5,2)).astype(np.float32)
cell_tint=rng.uniform(-.045,.045,(5,5)).astype(np.float32)
cell_plane=rng.uniform(-.10,.10,(5,5,2)).astype(np.float32)
d0=np.full((n,n),100,np.float32);d1=d0.copy()
ids=np.zeros((n,n),np.int32);px=np.zeros_like(d0);py=px.copy()
warp=noise(n,11,525)*.075
for dy in (-1,0,1):
  for dx in (-1,0,1):
    qx=ix+dx;qy=iy+dy;cx=qx+jitter[qy%5,qx%5,0];cy=qy+jitter[qy%5,qx%5,1]
    ax=(gx-cx)+.24*(gy-cy)+warp;ay=(gy-cy)*1.12
    d=ax*ax+ay*ay;near=d<d0
    d1=np.where(near,d0,np.minimum(d1,d));d0=np.where(near,d,d0)
    ids=np.where(near,(qy%5)*5+qx%5,ids);px=np.where(near,ax,px);py=np.where(near,ay,py)
cy=ids//5;cx=ids%5;edge=np.sqrt(d1)-np.sqrt(d0)
face=ss(.008,.060,edge)
plane=cell_plane[cy,cx,0]*px+cell_plane[cy,cx,1]*py
macro=noise(n,7,531);small=noise(n,63,532);micro=noise(n,193,533)
# Only selected boundaries are open fissures. Others are simple changes of plane.
open_edge=(cell_tint[cy,cx]>.002).astype(np.float32)*(1-ss(.003,.023,edge))
rgb=np.empty((n,n,3),np.float32);rgb[:]=[.424,.449,.419]
rgb+=(cell_tint[cy,cx]+macro*.030+small*.015+micro*.008-open_edge*.045)[...,None]
rgb+=(1-face)[...,None]*[-.013,-.014,-.011]
h=.49+plane+macro*.06+small*.035+micro*.009-(1-face)*.15-open_edge*.09
# Sparse shallow mineral laminations stop inside faces and do not form full rows.
lam=np.exp(-((np.sin((Y*19+X*3.8+noise(n,8,534)*.18)*math.tau))/.15)**2)
lam*=ss(.10,.24,edge)*ss(.03,.18,macro)
rgb-=lam[...,None]*.009;h-=lam*.018
images['G23_Rock']=save_image('G23_Rock',rgb,h)
mat=bpy.data.objects['C25_ContourBuiltCoast'].data.materials[0]
for name,im in images.items():
    node=mat.node_tree.nodes.get(name) or mat.node_tree.nodes.new('ShaderNodeTexImage')
    node.name=name;node.label=name+' | RGB reflectance / A height';node.image=im
(LOG/'surfaces.json').write_text(json.dumps({'materials':list(images),'sizes':{'G23_Rock':2048,'others':1024},'authoring':'GUI Blender MCP','rgb':'sRGB','alpha':'linear independent height','sun_shadows_baked':False},indent=2),encoding='utf8')
print('Generated five independent G23 albedo/height surfaces in live Blender')
