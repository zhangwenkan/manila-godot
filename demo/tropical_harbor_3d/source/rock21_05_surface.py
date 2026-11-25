exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
assert terrain.get('rock21_contours') and not terrain.get('rock21_surface'),'Wrong stage'
n=1024;yy,xx=np.mgrid[0:n,0:n].astype(np.float32)/n
rng=np.random.default_rng(275)
noise=np.zeros((n,n),np.float32)
for freq,amp in [(1,.1),(3,.08),(9,.025),(31,.012)]:
    for k in range(6):noise+=amp/6*np.sin(math.tau*(xx*rng.integers(1,freq+1)+yy*rng.integers(-freq,freq+1))+rng.uniform(0,math.tau))
seam=np.zeros((n,n),np.float32);hollow=seam.copy()
for j,base in enumerate([.16,.49,.83]):
    curve=base+.036*np.sin(math.tau*(xx*(j+1)+j*.31))+.014*np.sin(math.tau*(xx*5+.4*j))
    dist=np.abs(yy-curve);dist=np.minimum(dist,1-dist)
    window=smooth(-.65,-.15,np.sin(math.tau*(xx*(j+1)+j*.23)))
    seam=np.maximum(seam,(1-smooth(.002,.009,dist))*window)
    hollow=np.maximum(hollow,(1-smooth(.007,.040,dist))*window)
for j,(cx,lo,hi) in enumerate([(.19,.20,.43),(.70,.06,.39),(.46,.54,.78),(.88,.50,.70),(.31,.86,1.08)]):
    cy=(yy-lo)%1;valid=smooth(0,.035,cy)*(1-smooth(hi-lo-.04,hi-lo,cy))
    bend=cx+.017*np.sin(cy*14+j)+.006*np.sin(cy*39+j)
    dx=np.abs(xx-bend);dx=np.minimum(dx,1-dx)
    seam=np.maximum(seam,(1-smooth(.0018,.007,dx))*valid*.8)
    hollow=np.maximum(hollow,(1-smooth(.006,.026,dx))*valid*.65)
# Broad convex stone cheeks, wide concave weathering joints; no closed masonry cells.
height=.57+noise*1.4-hollow*.30-seam*.075
base=np.array([.255,.31,.335]);rgb=np.broadcast_to(base,(n,n,3)).copy()
rgb*=1+(noise*.9-hollow*.075-seam*.10)[:,:,None]
rim=np.clip(np.roll(hollow,3,axis=0)-hollow,0,1)
rgb+=rim[:,:,None]*.025
for name,data,linear in [('R27_Rock_Albedo',rgb,False),('R27_Rock_Height',np.repeat(height[:,:,None],3,axis=2),True)]:
    im=bpy.data.images[name];rgba=np.ones((n,n,4),np.float32);rgba[:,:,:3]=np.clip(data,0,1)
    im.pixels.foreach_set(rgba.ravel());im.filepath_raw=str(OUT/(name+'.png'));im.save();im.pack()
terrain['rock21_surface']=True
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print('Broad weathered rock relief saved with terminating joints')
