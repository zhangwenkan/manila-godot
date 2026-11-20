# Ground material content and authored weights created in Blender MCP.
# Keep broad quiet surface color; rock fissures are sparse and non-directional.
def noise_field(n,seed):
    rng=np.random.default_rng(seed);yy,xx=np.mgrid[0:n,0:n]/n
    field=np.zeros((n,n),np.float32)
    for freq,amplitude in [(1,.35),(3,.25),(7,.17),(17,.09),(43,.04)]:
        for k in range(5):
            ax=int(rng.integers(1,freq+1));ay=int(rng.integers(-freq,freq+1))
            field+=amplitude/5*np.sin(math.tau*(xx*ax+yy*ay)+rng.uniform(0,math.tau))
    return field
def save_color(name,rgb):
    rgba=np.ones((*rgb.shape[:2],4),np.float32)
    rgba[:,:,:3]=np.clip(rgb,0,1)
    im=bpy.data.images.new(name,width=rgb.shape[1],height=rgb.shape[0]);im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw=str(OUT/(name+'.png'));im.file_format='PNG';im.save();im.pack();return im
n=768;yy,xx=np.mgrid[0:n,0:n].astype(np.float32)/n
images={}
for kind,hexcolor in [('Grass','798e43'),('Earth','8c7554'),('Path','ba9f68'),('Rock','858b7f')]:
    seed={'Grass':442,'Earth':883,'Path':331,'Rock':113}[kind];rng=np.random.default_rng(seed)
    field=noise_field(n,seed)
    base=np.array([int(hexcolor[i:i+2],16)/255 for i in (0,2,4)])
    rgb=np.broadcast_to(base,(n,n,3)).copy()*(1+field[:,:,None]*.30)
    if kind=='Grass':
        for k in range(11000):
            px,py=rng.integers(0,n,2);length=int(rng.integers(2,9));dx,dy=rng.uniform(-1,1,2);tone=rng.uniform(.83,1.16)
            for j in range(length):
                a=(px+int(dx*j))%n;b=(py+int(dy*j))%n;rgb[b,a]=base*tone
    elif kind=='Rock':
        # Irregular slabs and a few discontinuous seams, not horizontal brush bands.
        f1=np.full((n,n),10,dtype=np.float32);f2=f1.copy();cell=np.zeros((n,n),np.int32)
        for k in range(28):
            sx,sy=rng.random(2);dx=np.abs(xx-sx);dy=np.abs(yy-sy);dx=np.minimum(dx,1-dx);dy=np.minimum(dy,1-dy)
            dist=(dx*dx+dy*dy)**.5
            better=dist<f1;f2=np.where(better,f1,np.minimum(f2,dist));cell=np.where(better,k,cell);f1=np.minimum(f1,dist)
        celltone=rng.uniform(.94,1.06,28)[cell]
        seam=(1-smooth(.001,.0045,f2-f1))*smooth(-.1,.12,noise_field(n,201))
        rgb*=celltone[:,:,None]*(1-.15*seam[:,:,None])
    else:
        grains=rng.normal(0,.006,(n,n,1));rgb+=grains
    images[kind]=save_color('L24_'+kind,rgb)

# Calculate material roles on the real surface. Height and slope are geometric.
bpy.context.view_layer.update();data=terrain.data
coords=np.empty((len(data.vertices),3),np.float32);data.vertices.foreach_get('co',coords.ravel())
normals=np.empty_like(coords);data.vertices.foreach_get('normal',normals.ravel())
mx=coords[:,0];mz=-coords[:,1];md=mx-shore(mz);my=coords[:,2]
flat=np.clip(normals[:,2],0,1);steep=1-flat
roadweight=np.zeros(len(coords))
for points in RAMPS:
    distance,elev=route_distance(md,mz,points);roadweight=np.maximum(roadweight,1-smooth(.82,1.14,distance))
# A pair of connected winding lanes sits on the available tops, behind the lips.
lower_lane=np.interp(mz,[-70,0,8,15,24,31,35,40,44,49,54,60,70,110],[6.1,5.7,5.7,5.0,5.9,5.0,8.8,5.8,4.5,6.6,7.0,6.0,6.2,6.2])
upper_lane=np.interp(mz,[-70,0,12,20,29,36,43,50,56,64,72,110],[15.8,15.3,15.0,15.7,15.4,20.1,15.4,16.5,15.4,15.6,20,15.5])
for lane,halfwidth in [(lower_lane,.60),(upper_lane,.65)]:
    roadweight=np.maximum(roadweight,(1-smooth(halfwidth,halfwidth+.24,np.abs(md-lane)))*smooth(.72,.93,flat))
for s in SITES:
    cx,cz=s['center'][0],s['gz']
    apron=(1-smooth(s['depth']*.5+.25,s['depth']*.5+.65,np.abs(mx-cx)))*(1-smooth(s['w']*.5+.3,s['w']*.5+.7,np.abs(mz-cz)))
    roadweight=np.maximum(roadweight,apron*smooth(.72,.94,flat))
grain=.07*np.sin(mx*1.73+mz*.79)+.035*np.sin(mz*2.61-mx*.81)
grassline=np.interp(mz,[-70,0,8,16,23,30,36,41,46,52,58,65,75,110],[1.8,2.4,2.0,3.6,2.4,3.5,5.4,1.5,2.2,3.7,2.5,3,2,2])
vegetated=smooth(grassline-.16,grassline+.16,md+grain)
grass=vegetated*(1-smooth(.20,.36,steep))*(1-roadweight)
rock=smooth(.22,.42,steep)*(1-roadweight)*smooth(1.35,1.85,my)
soil=smooth(.20,.40,steep)*(1-roadweight)*(1-rock)
path=roadweight
grass*=smooth(.18,.36,my);soil*=smooth(.20,.42,my);rock*=smooth(.2,.4,my);path*=smooth(.13,.3,my)
colors=np.column_stack([grass,rock,path,soil]).astype(np.float32)
tot=colors.sum(1);colors/=np.maximum(tot,1)[:,None]
if data.color_attributes.get('LandUse'):data.color_attributes.remove(data.color_attributes['LandUse'])
attr=data.color_attributes.new(name='LandUse',type='FLOAT_COLOR',domain='POINT');attr.data.foreach_set('color',colors.ravel());data.color_attributes.active_color=attr
mat=bpy.data.materials['Ref_L24_Landform'];nodes=mat.node_tree.nodes;links=mat.node_tree.links
for node in list(nodes):nodes.remove(node)
out=nodes.new('ShaderNodeOutputMaterial');bs=nodes.new('ShaderNodeBsdfPrincipled');bs.inputs['Roughness'].default_value=.94;links.new(bs.outputs['BSDF'],out.inputs['Surface'])
# Blender source also retains role colors through the named attribute.
vc=nodes.new('ShaderNodeVertexColor');vc.layer_name='LandUse';sep=nodes.new('ShaderNodeSeparateColor');links.new(vc.outputs['Color'],sep.inputs['Color'])
tex=[]
for kind in ['Path','Earth','Rock','Grass']:
    node=nodes.new('ShaderNodeTexImage');node.image=images[kind];tex.append(node)
mix=nodes.new('ShaderNodeMixRGB');links.new(vc.outputs['Alpha'],mix.inputs[0]);links.new(tex[0].outputs['Color'],mix.inputs[1]);links.new(tex[1].outputs['Color'],mix.inputs[2])
mix2=nodes.new('ShaderNodeMixRGB');links.new(sep.outputs['Green'],mix2.inputs[0]);links.new(mix.outputs[0],mix2.inputs[1]);links.new(tex[2].outputs['Color'],mix2.inputs[2])
mix3=nodes.new('ShaderNodeMixRGB');links.new(sep.outputs['Red'],mix3.inputs[0]);links.new(mix2.outputs[0],mix3.inputs[1]);links.new(tex[3].outputs['Color'],mix3.inputs[2]);links.new(mix3.outputs[0],bs.inputs['Base Color'])
for p in data.polygons:p.use_smooth=True
# Preserve smooth vertex shading, without splitting individual grid triangles.
sharp=data.attributes.get('sharp_edge')
if sharp: data.attributes.remove(sharp)
data.update();export_land()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_landform_mass_mcp.blend'))
print('SURFACE_AUTHORED',len(images),'textures, vertex weights grass/rock/path/soil; terrain exported')
