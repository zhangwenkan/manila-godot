exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
assert not terrain.get('rock21_materials'),'Already applied'
n=1024;yy,xx=np.mgrid[0:n,0:n].astype(np.float32)/n
def field(seed):
    rng=np.random.default_rng(seed);v=np.zeros((n,n),np.float32)
    for freq,amp in [(1,.30),(3,.25),(7,.18),(19,.09),(45,.035)]:
        for j in range(5):
            ax=int(rng.integers(1,freq+1));ay=int(rng.integers(-freq,freq+1))
            v+=amp*np.sin(math.tau*(xx*ax+yy*ay)+rng.uniform(0,math.tau))/5
    return v
def save_img(name,rgb,linear=False):
    rgba=np.ones((n,n,4),np.float32);rgba[:,:,:3]=np.clip(rgb,0,1)
    img=bpy.data.images.new(name,width=n,height=n,alpha=True)
    if linear:img.colorspace_settings.name='Non-Color'
    img.pixels.foreach_set(rgba.ravel());img.filepath_raw=str(OUT/(name+'.png'));img.file_format='PNG';img.save();img.pack();return img
warp=field(72);noise=field(73)
wx=(xx+.045*np.sin(math.tau*yy)+.025*warp)%1
wy=(yy+.035*np.sin(math.tau*xx*2))%1
rng=np.random.default_rng(2702);first=np.full((n,n),9,np.float32);second=first.copy();cell=np.zeros((n,n),np.int32)
seeds=[]
for j in range(4):
    for i in range(5):seeds.append(((i+rng.uniform(.08,.92))/5,(j+rng.uniform(.08,.92))/4))
for k,(sx,sy) in enumerate(seeds):
    dx=np.abs(wx-sx);dy=np.abs(wy-sy);dx=np.minimum(dx,1-dx);dy=np.minimum(dy,1-dy)
    distance=np.sqrt(dx*dx+dy*dy*.92)
    better=distance<first;second=np.where(better,first,np.minimum(second,distance));cell=np.where(better,k,cell);first=np.minimum(first,distance)
gap=second-first;seam=1-smooth(.0016,.0068,gap);edge=1-smooth(.008,.028,gap)
tone=rng.uniform(.89,1.10,len(seeds))[cell]
base=np.array([.404,.445,.468],np.float32)
rock=np.broadcast_to(base,(n,n,3)).copy()*(tone*(1+noise*.24))[:,:,None]
rock*=1-.28*seam[:,:,None]-.04*edge[:,:,None]
rock+=np.maximum(0,np.roll(edge,2,axis=1)-edge)[:,:,None]*.045
rock_height=.22+.56*smooth(.001,.027,gap)+noise*.23+field(710)*.08
rock_albedo=save_img('R27_Rock_Albedo',rock)
rock_height_img=save_img('R27_Rock_Height',np.repeat(rock_height[:,:,None],3,axis=2),True)
earthnoise=field(927);clod=field(928);fine=field(929)
earth=np.broadcast_to(np.array([.565,.457,.314]),(n,n,3)).copy()
earth*=1+(earthnoise*.40+clod*.15+fine*.05)[:,:,None]
fleck=rng.random((n,n));earth-=np.where(fleck>.997,.055,0)[:,:,None]
earth_height=.5+earthnoise*.6+clod*.25+fine*.12
earth_albedo=save_img('R27_Earth_Albedo',earth)
earth_height_img=save_img('R27_Earth_Height',np.repeat(earth_height[:,:,None],3,axis=2),True)
# Keep the editable Blender material in agreement with the exported terrain role textures.
mat=bpy.data.materials['Ref_L24_Landform'];nodes=mat.node_tree.nodes;links=mat.node_tree.links
for node in nodes:
    if node.type=='TEX_IMAGE' and node.image:
        if node.image.name.startswith('L24_Rock'):node.image=rock_albedo
        elif node.image.name.startswith('L24_Earth'):node.image=earth_albedo
bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
tex=nodes.new('ShaderNodeTexImage');tex.image=rock_height_img;tex.name='R27 geological relief'
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.6;bump.inputs['Distance'].default_value=.055
links.new(tex.outputs['Color'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
terrain['rock21_materials']=True
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print('CREATED R27 rock/earth albedo and height textures via Blender MCP; source saved')
