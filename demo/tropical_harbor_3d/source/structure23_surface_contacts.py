"""Terrain material topology helpers; called only inside the GUI Blender pass."""
import numpy as np

def clean_cliff_grass(grass,rock,soil,height,normal):
    rows,cols=grass.shape;dx=48/cols;dz=97/rows
    mask=grass>.50
    # Label actual connected grass coverage using row spans, without optional
    # packages. This finds isolated little green faces within an exposed cliff.
    labels=np.zeros(mask.shape,np.int32);parents=[0];prior=[]
    def root(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    for y in range(rows):
        edges=np.diff(np.r_[False,mask[y],False].astype(np.int8))
        starts=np.flatnonzero(edges==1);ends=np.flatnonzero(edges==-1);current=[];j=0
        for a,b in zip(starts,ends):
            ident=len(parents);parents.append(ident)
            while j<len(prior) and prior[j][1]<=a:j+=1
            k=j
            while k<len(prior) and prior[k][0]<b:
                old=root(prior[k][2]);now=root(ident)
                if old!=now:parents[max(old,now)]=min(old,now)
                k+=1
            labels[y,a:b]=ident;current.append((a,b,ident))
        prior=current
    lookup=np.array([root(i) for i in range(len(parents))],np.int32)
    labels=lookup[labels];sizes=np.bincount(labels.ravel())*dx*dz
    # A small morphological opening removes only narrow tongues on steep
    # grass/rock contacts; genuine flat shelves retain their rooted cover.
    offsets=[(iy,ix) for iy in range(-3,4) for ix in range(-6,7)
             if (iy*dz)**2+(ix*dx)**2<=.13**2]
    eroded=mask.copy()
    for iy,ix in offsets:eroded&=np.roll(np.roll(mask,iy,0),ix,1)
    opened=np.zeros_like(mask)
    for iy,ix in offsets:opened|=np.roll(np.roll(eroded,iy,0),ix,1)
    halo=rock.copy()
    for iy,ix in [(0,8),(0,-8),(4,0),(-4,0),(3,6),(3,-6),(-3,6),(-3,-6)]:
        halo=np.maximum(halo,np.roll(np.roll(rock,iy,0),ix,1))
    islands=mask&(sizes[labels]<.65)&(labels>0)&(halo>.35)&(height>1.15)
    tongues=mask&~opened&(normal<.88)&(halo>.35)&(height>1.15)
    cut=islands|tongues
    amount=cut.astype(np.float32)
    # Keep contact width to one texel; broad blur would make another color band.
    amount=np.maximum(amount,(np.roll(amount,1,0)+np.roll(amount,-1,0)+np.roll(amount,1,1)+np.roll(amount,-1,1))*.125)
    transfer=grass*amount
    grass=grass-transfer;rock=rock+transfer
    return grass,rock,soil,{'isolated_grass_pixels_removed':int(islands.sum()),
         'thin_cliff_grass_pixels_removed':int(tongues.sum()),
         'cliff_grass_area_m2':float(cut.sum()*dx*dz)}
