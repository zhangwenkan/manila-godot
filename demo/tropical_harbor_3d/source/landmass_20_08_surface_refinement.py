# Remove periodic brush-like color, keep mineral faces distinct from grass tops.
def random_field(n,seed):
    rng=np.random.default_rng(seed);result=np.zeros((n,n),np.float32)
    for cell,amp in [(4,.50),(10,.28),(27,.15),(69,.07)]:
        coarse=rng.uniform(-1,1,(cell+1,cell+1));coarse[-1]=coarse[0];coarse[:,-1]=coarse[:,0]
        v=np.arange(n)*cell/n;i=np.floor(v).astype(int);f=v-i;f=f*f*(3-2*f)
        rows=coarse[:,i]*(1-f)[None,:]+coarse[:,i+1]*f[None,:]
        arr=rows[i,:]*(1-f)[:,None]+rows[i+1,:]*f[:,None]
        result+=arr*amp
    return result
def replace_image(im,rgb):
    rgba=np.ones((*rgb.shape[:2],4),np.float32);rgba[:,:,:3]=np.clip(rgb,0,1)
    im.pixels.foreach_set(rgba.ravel());im.save();im.pack()
n=768
for kind,hexcolor in [('Grass','6c873c'),('Earth','8c7554'),('Path','baa16f'),('Rock','727d78')]:
    seed={'Grass':445,'Earth':887,'Path':334,'Rock':116}[kind];rng=np.random.default_rng(seed)
    base=np.array([int(hexcolor[i:i+2],16)/255 for i in (0,2,4)])
    field=random_field(n,seed);rgb=np.broadcast_to(base,(n,n,3)).copy()*(1+field[:,:,None]*.15)
    if kind=='Grass':
        for k in range(15000):
            px,py=rng.integers(0,n,2);length=int(rng.integers(2,7));dx,dy=rng.uniform(-1,1,2);tone=rng.uniform(.90,1.11)
            for j in range(length):rgb[(py+int(dy*j))%n,(px+int(dx*j))%n]=base*tone
    if kind=='Rock':
        # A few open, branching cracks. No complete Voronoi-cell tiling.
        for k in range(15):
            px,py=rng.uniform(0,n,2);angle=rng.uniform(0,math.tau);length=int(rng.integers(75,240))
            for j in range(length):
                angle+=rng.uniform(-.12,.12);px+=math.cos(angle);py+=math.sin(angle)
                if j%31<25:
                    rgb[int(py)%n,int(px)%n]*=.78
                    rgb[(int(py)+1)%n,int(px)%n]*=.92
    else:rgb+=rng.normal(0,.003,(n,n,1))
    replace_image(images[kind],rgb)

coords=np.empty((len(terrain.data.vertices),3),np.float32);terrain.data.vertices.foreach_get('co',coords.ravel())
mx=coords[:,0];mz=-coords[:,1];md=mx-shore(mz);my=coords[:,2]
lowf,*_=mass_fraction(md,mz,LOW_TOE,LOW_TOP);highf,*_=mass_fraction(md,mz,HIGH_TOE,HIGH_TOP)
normal=np.empty_like(coords);terrain.data.vertices.foreach_get('normal',normal.ravel());steep=1-np.clip(normal[:,2],0,1)
attr=terrain.data.color_attributes['LandUse'];weights=np.empty((len(coords),4),np.float32);attr.data.foreach_get('color',weights.ravel())
grass=weights[:,0];rock=weights[:,1];path=weights[:,2];soil=weights[:,3]
exposed=(smooth(.035,.12,highf)*(1-smooth(.965,.998,highf)))*smooth(.08,.24,steep)*(1-path)
rock=np.maximum(rock,exposed)
lowsoil=smooth(.035,.12,lowf)*(1-smooth(.94,.998,lowf))*(1-smooth(.005,.025,highf))*(1-path)
soil=np.maximum(soil,lowsoil)
grass*=1-np.maximum(rock,soil)
weights=np.column_stack([grass,rock,path,soil]).astype(np.float32);weights/=np.maximum(weights.sum(1),1)[:,None]
attr.data.foreach_set('color',weights.ravel())
terrain.data.update();export_land()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_landform_mass_mcp.blend'))
print('SURFACE_REFINED nonperiodic grass; open rock seams; material boundaries follow mass geometry')
