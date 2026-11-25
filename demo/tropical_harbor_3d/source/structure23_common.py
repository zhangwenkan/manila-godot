"""Pure geometric helpers; authoring callers run inside the owned GUI MCP."""
import numpy as np

def ss(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

def polygon_distance(x,z,polygon):
    inside=np.zeros(np.shape(x),bool);d=np.full(np.shape(x),1e6,dtype=float)
    p=np.array(polygon,float)
    for a,b in zip(p,np.roll(p,-1,axis=0)):
        dx,dz=b-a;den=dx*dx+dz*dz
        if den<1e-12:continue
        if abs(dz)>1e-12:inside^=((a[1]>z)!=(b[1]>z))&(x<dx*(z-a[1])/dz+a[0])
        t=np.clip(((x-a[0])*dx+(z-a[1])*dz)/den,0,1)
        d=np.minimum(d,np.hypot(x-a[0]-t*dx,z-a[1]-t*dz))
    return np.where(inside,-d,d)

def route_profile(x,z,points):
    pp=np.array(points,float);axis=pp[-1,:2]-pp[0,:2];length=np.linalg.norm(axis);axis/=length
    offsets=pp[:,:2]-pp[0,:2];stations=offsets@axis
    if np.max(np.abs(offsets[:,0]*axis[1]-offsets[:,1]*axis[0]))<1e-5 and np.all(np.diff(stations)>0):
        # Monotone Hermite grades avoid the slope overshoot produced when
        # overlapping a level approach and its straight downhill continuation.
        step=np.diff(stations);sec=np.diff(pp[:,2])/step;m=np.zeros(len(pp))
        for i in range(1,len(pp)-1):
            if sec[i-1]*sec[i]>0:
                w1=2*step[i]+step[i-1];w2=step[i]+2*step[i-1]
                m[i]=(w1+w2)/(w1/sec[i-1]+w2/sec[i])
        t=(x-pp[0,0])*axis[0]+(z-pp[0,1])*axis[1];cl=np.clip(t,0,length)
        j=np.clip(np.searchsorted(stations,cl,side='right')-1,0,len(pp)-2);u=(cl-stations[j])/step[j]
        h=(2*u**3-3*u*u+1)*pp[j,2]+(u**3-2*u*u+u)*step[j]*m[j]+(-2*u**3+3*u*u)*pp[j+1,2]+(u**3-u*u)*step[j]*m[j+1]
        d=np.hypot(x-pp[0,0]-cl*axis[0],z-pp[0,1]-cl*axis[1])
        return d,h
    d=np.full(np.shape(x),1e6,dtype=float);h=np.zeros(np.shape(x),float)
    segments=[]
    for si,(a,b) in enumerate(zip(points,points[1:])):
        dx,dz=b[0]-a[0],b[1]-a[1];den=dx*dx+dz*dz
        if den<1e-12:continue
        raw=((x-a[0])*dx+(z-a[1])*dz)/den
        t=np.clip(raw,0,1)
        ds=np.hypot(x-a[0]-t*dx,z-a[1]-t*dz);take=ds<d
        ht=raw
        if si==0:ht=np.maximum(ht,0)
        if si==len(points)-2:ht=np.minimum(ht,1)
        hh=a[2]+ht*(b[2]-a[2]);segments.append((ds,hh));d=np.minimum(d,ds)
    # Blend neighbouring segment profiles continuously across bend bisectors.
    # The footprint remains the exact union of full-width segment corridors.
    den=np.zeros_like(h)
    for ds,hh in segments:
        w=np.exp(-np.maximum(ds*ds-d*d,0)/.25)
        h+=hh*w;den+=w
    h=np.divide(h,den,out=h,where=den>1e-12)
    return d,h

def design_field(x,z,spec):
    strength=np.zeros(np.shape(x));numer=np.zeros(np.shape(x));denom=np.zeros(np.shape(x));paint=np.zeros(np.shape(x))
    # The geometric bench extends beyond its painted edge. A feathered margin
    # lies on the bench; it cannot climb the transitional side slope.
    for r in spec['routes']:
        w=r['halfwidth'];s=r.get('shoulder_width',1.8);pts=np.array(r['points']);pad=w+s+.3
        box=(x>pts[:,0].min()-pad)&(x<pts[:,0].max()+pad)&(z>pts[:,1].min()-pad)&(z<pts[:,1].max()+pad)
        xx,zz=x[box],z[box];d,h=route_profile(xx,zz,r['points'])
        margin=r.get('bench_margin',.28)
        influence=1-ss(w+margin,w+margin+s,d);weight=influence**8
        numer[box]+=h*weight;denom[box]+=weight;strength[box]=np.maximum(strength[box],influence)
        edge=.035*np.sin(xx*5.6+zz*3.7)+.025*np.sin(zz*8.1-xx*2.4)
        wear_width=r.get('paint_halfwidth',w)
        paint[box]=np.maximum(paint[box],(1-ss(wear_width-.17,wear_width+.02,d+edge))*r.get('paint_strength',1.0))
    for q in spec['platforms']:
        pts=np.array(q['polygon']);pad=q.get('blend_width',1.6)+.2
        box=(x>pts[:,0].min()-pad)&(x<pts[:,0].max()+pad)&(z>pts[:,1].min()-pad)&(z<pts[:,1].max()+pad)
        xx,zz=x[box],z[box];d=polygon_distance(xx,zz,q['polygon']);influence=1-ss(.18,.18+q.get('blend_width',1.6),d)
        weight=influence**8;numer[box]+=q['height']*weight;denom[box]+=weight;strength[box]=np.maximum(strength[box],influence)
        edge=.03*np.sin(xx*4.4-zz*5.1)+.025*np.cos(zz*7.3+xx)
        paint[box]=np.maximum(paint[box],(1-ss(-.10,.04,d+edge))*q.get('paint_strength',1.0))
    target=np.divide(numer,denom,out=np.zeros_like(numer),where=denom>1e-12)
    # Door approaches are graded wedges within courts, and must reach the
    # actual bottom step rather than averaging with a lower court plateau.
    for r in spec['routes']:
        if not r['name'].endswith('_entry'):continue
        pts=np.array(r['points']);pad=r['halfwidth']+.6
        box=(x>pts[:,0].min()-pad)&(x<pts[:,0].max()+pad)&(z>pts[:,1].min()-pad)&(z<pts[:,1].max()+pad)
        d,h=route_profile(x[box],z[box],r['points']);w=1-ss(r['halfwidth']+.14,r['halfwidth']+.50,d)
        target[box]=target[box]*(1-w)+h*w
    return target,strength,paint

def convex_hull(points):
    points=sorted(set(tuple(map(float,p)) for p in points))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lo=[];hi=[]
    for p in points:
        while len(lo)>1 and cross(lo[-2],lo[-1],p)<=0:lo.pop()
        lo.append(p)
    for p in reversed(points):
        while len(hi)>1 and cross(hi[-2],hi[-1],p)<=0:hi.pop()
        hi.append(p)
    return np.array(lo[:-1]+hi[:-1])

def intersections(tri,poly):
    mask=np.all(tri.max(1)>=poly.min(0),axis=1)&np.all(tri.min(1)<=poly.max(0),axis=1)
    ids=np.flatnonzero(mask);t=tri[ids];hit=np.ones(len(ids),bool)
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
        e=b-a;rel=t-a;v=e[0]*rel[...,1]-e[1]*rel[...,0];hit&=~np.all(v< -1e-8,axis=1)
    # Works for either triangle winding.
    for j in range(3):
        a=t[:,j];e=t[:,(j+1)%3]-a;rel=poly[None]-a[:,None]
        v=e[:,None,0]*rel[...,1]-e[:,None,1]*rel[...,0]
        other=t[:,(j+2)%3]-a;sg=e[:,0]*other[:,1]-e[:,1]*other[:,0]
        hit&=~np.all(v*np.sign(sg[:,None])< -1e-8,axis=1)
    mask[:]=False;mask[ids[hit]]=True;return mask
