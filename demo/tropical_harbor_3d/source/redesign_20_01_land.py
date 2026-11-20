# This file is a payload: execute only through the verified Blender MCP session.
# A new continuous terrain, authored from independent sections, not the old berms.
import bmesh

archive=bpy.data.collections.new('Archive_RejectedLandscape_20261120')
bpy.context.scene.collection.children.link(archive)
for ob in list(C.objects):
    archive.objects.link(ob);C.objects.unlink(ob)
for ob in list(town.objects):
    if ob.name.startswith('Town20_ConnectedApron') or any(m and m.name=='Ref_Town_Path' for m in ob.data.materials):
        archive.objects.link(ob);town.objects.unlink(ob)
for ob in list(coast.objects):
    if ob.name.startswith('R21_TavernAccessStep'):
        archive.objects.link(ob);coast.objects.unlink(ob)
for ob in list(fol.objects):
    if ob.name.startswith(('S20_Grass','R21_','S22_','S22F_')):
        archive.objects.link(ob);fol.objects.unlink(ob)
archive.hide_render=True;archive.hide_viewport=True

def curve(z,points):
    for (a,av),(b,bv) in zip(points,points[1:]):
        if a<=z<=b:
            t=(z-a)/(b-a);t=t*t*(3-2*t)
            return av+(bv-av)*t
    return points[0][1] if z<points[0][0] else points[-1][1]

def edge(z):
    return curve(z,[(-20,3.2),(0,3.2),(8,3.55),(17,2.85),(25,3.10),(34,3.75),(41,4.15),(46,3.55),(54,2.9),(60,3.3),(68,3.7),(75,3.1),(86,3.4)])+.045*math.sin(z*2.15)+.025*math.sin(z*4.7)

def levels(z):
    h1=curve(z,[(-20,1.1),(0,1.4),(16,1.50),(30,1.46),(44,1.54),(57,1.51),(70,1.42),(86,1.22)])
    h2=curve(z,[(-20,3.0),(0,3.35),(18,3.60),(34,3.55),(49,3.68),(64,3.50),(86,3.1)])
    return h1,h2

def path_gap(z,offset=0):
    # Two streets between neighborhoods, rather than a scallop at every house.
    return max(1-smooth(1.05,1.65,abs(z-34.8-offset)),1-smooth(1.05,1.65,abs(z-53.0-offset)))

def sections(z):
    e=edge(z);h1,h2=levels(z);rear=10.65+.32*math.sin(z*.13)
    # (distance inland, height, grass, exposed bank, worn soil)
    s=[(-180,-30,0,0,0),(-80,-20,0,0,0),(-35,-10,0,0,0),(-15,-4,0,0,0),(-8,-1.8,0,0,0),(-4,-.7,0,0,0),(-2,-.3,0,0,0),(-1,-.12,0,0,0),(0,0,0,0,0),(.65,.12,0,0,0),(1.35,.24,0,0,.15),
       (e-.85,.31,0,0,.45),(e-.38,.36,0,.25,.55),(e-.10,.47,0,.92,.05),(e+.18,h1*.66,0,1,0),(e+.48,h1-.13,0,1,0),
       (e+.62,h1-.015,.50,.5,0),(e+.78,h1+.035,1,0,0),(e+1.10,h1+.07,1,0,0),
       (5.65,h1+.035,1,0,0),(5.96,h1+.005,0,0,1),(6.35,h1,0,0,1),(7.15,h1,0,0,1),(7.90,h1,0,0,1),
       (8.65,h1,0,0,1),(9.35,h1,0,0,1),(10.05,h1+.025,.8,0,.2),
       (rear,h1+.06,1,0,0),(rear+.45,h1+.16,.7,.3,0),(rear+.83,h1+.40,.15,.85,0),
       (rear+1.28,h1+.80,.35,.65,0),(rear+1.65,h1+1.04,1,0,0),(rear+2.35,h1+1.43,1,0,0),
       (14.45,h2-.10,1,0,0),(14.85,h2+.015,1,0,0),(15.15,h2+.025,.85,0,.15),(15.45,h2,0,0,1),
       (16.15,h2,0,0,1),(17.0,h2,0,0,1),(18.0,h2,0,0,1),(19.0,h2,0,0,1),(20.0,h2+.035,.8,0,.2),
       (21.2,h2+.10,1,0,0),(22.8,h2+.28,1,0,0),(24.6,h2+.78,1,0,0),(26.2,h2+1.28,1,0,0),
       (28.2,h2+1.80,1,0,0),(31,h2+2.25,1,0,0),(35,h2+2.40,1,0,0),(42,h2+2.65,1,0,0),(60,h2+2.60,1,0,0),(120,h2+2.60,1,0,0)]
    # This explicit contour topology never crosses and never builds a separate cap.
    assert all(b[0]>a[0] for a,b in zip(s,s[1:])),(z,e,rear)
    return s

def new_sample(d,z,section=None):
    ss=section or sections(z)
    for a,b in zip(ss,ss[1:]):
        if a[0]<=d<=b[0]:
            t=(d-a[0])/(b[0]-a[0]);v=[a[k]+(b[k]-a[k])*t for k in range(1,5)];break
    else:v=list(ss[0][1:] if d<ss[0][0] else ss[-1][1:])
    h,g,bare,worn=v;x=shore(z)+d;e=edge(z);h1,h2=levels(z)
    if d<=0:
        return old_ground(x,z),0,0,0
    # Wide natural entry slopes through the front bank at two real streets.
    gate=path_gap(z)
    if .8<d<6.0:
        ramp=.20+(h1-.20)*smooth(1.1,5.95,d)
        h=h*(1-gate)+ramp*gate;g*=1-gate;bare*=1-gate;worn=max(worn,gate)
    if 10.0<d<15.4:
        diagonal=(d-10.2)*.60
        lane=path_gap(z,diagonal)
        ramp=h1+(h2-h1)*smooth(10.1,15.4,d)
        h=h*(1-lane)+ramp*lane;g*=1-lane;bare*=1-lane;worn=max(worn,lane)
    # Yard grass joins the shared slope between houses, without building pads.
    if 7.85<d<10.1:
        use=max(1-smooth(s['w']/2+.15,s['w']/2+.65,abs(z-s['gz'])) for s in SITES if s['d']<11)
        yard=(1-use)*smooth(7.85,8.3,d)
        g=max(g,yard);worn*=1-yard
    if 16.8<d<20.1:
        use=max(1-smooth(s['w']/2+.25,s['w']/2+.75,abs(z-s['gz'])) for s in SITES if s['d']>11)
        yard=(1-use)*smooth(16.8,17.3,d);g=max(g,yard);worn*=1-yard
    # The vegetated ground itself swells gently; no offset grass surfaces.
    relief=(.027*math.sin(z*2.7+d*3.1)+.018*math.sin(z*5.1-d*2.3))
    h+=g*relief
    h+=g*smooth(21,26,d)*(.22*math.sin(z*.21+d*.33)+.11*math.sin(z*.49-d*.57))
    # Preserve the separate working basin and its underwater hull clearance.
    protect=(1-smooth(2.75,3.6,abs(z-65.2)))*(1-smooth(17.1,18.4,x))
    h=h*(1-protect)+old_ground(x,z)*protect
    g*=1-protect;bare*=1-protect;worn*=1-protect
    return h,g,bare,worn

zs=sorted(set([-70+i*2 for i in range(26)]+[-20+i*.5 for i in range(40)]+[i*.25 for i in range(329)]+[82+i for i in range(19)]))
vertices=[];colors=[];faces=[];rows=[]
for z in zs:
    ss=sections(z);ds=[]
    for a,b in zip(ss,ss[1:]):
        subdivisions=max(1,math.ceil((b[0]-a[0])/.65)) if 0<=a[0]<35 else 1
        ds.extend(a[0]+(b[0]-a[0])*k/subdivisions for k in range(subdivisions))
    ds.append(ss[-1][0]);rows.append(ds)
# Fixed per-span subdivisions prevent cross-row topology mismatches.
counts=[max(1,max(math.ceil((sections(z)[i+1][0]-sections(z)[i][0])/.65) for z in zs)) if 0<=sections(0)[i][0]<35 else 1 for i in range(len(sections(0))-1)]
for z in zs:
    ss=sections(z);ds=[]
    for i,(a,b) in enumerate(zip(ss,ss[1:])):ds.extend(a[0]+(b[0]-a[0])*k/counts[i] for k in range(counts[i]))
    ds.append(ss[-1][0])
    for d in ds:
        h,g,soil,path=new_sample(d,z,ss);vertices.append((shore(z)+d,-z,h));colors.append((g,soil,path,1))
width=len(ds)
for j in range(len(zs)-1):
    for i in range(width-1):
        a=j*width+i;faces.append((a,a+width,a+width+1,a+1))
data=bpy.data.meshes.new('S23_UnifiedLandformTopology');data.from_pydata(vertices,[],faces);data.update()
terrain=bpy.data.objects.new('S23_ContinuousCoastalLandform',data);C.objects.link(terrain)
uv=data.uv_layers.new(name='UVMap');vi=np.empty(len(data.loops),np.int32);data.loops.foreach_get('vertex_index',vi)
xyz=np.asarray(vertices,np.float32);uv.data.foreach_set('uv',(xyz[vi,:2]/2.4).ravel())
color=data.color_attributes.new(name='LandUse',type='FLOAT_COLOR',domain='POINT');color.data.foreach_set('color',np.asarray(colors,np.float32).ravel())
data.color_attributes.active_color=color
for p in data.polygons:p.use_smooth=True

def painted_image(name,kind):
    n=512;yy,xx=np.mgrid[0:n,0:n].astype(np.float32);rng=np.random.default_rng(930+kind)
    field=np.zeros((n,n),np.float32)
    for freq,amp in [(1,.05),(3,.04),(7,.018),(17,.006)]:
        for k in range(3):
            ax=int(rng.integers(1,freq+2));ay=int(rng.integers(1,freq+2));ph=rng.uniform(0,math.tau)
            field+=amp/3*np.sin((xx*ax+yy*ay)*math.tau/n+ph)
    base=np.array([[.43,.56,.22],[.40,.28,.16],[.66,.49,.26]][kind],np.float32)
    rgb=base[None,None,:]*(1+field[:,:,None]);rgb=np.broadcast_to(rgb,(n,n,3)).copy()
    if kind==0:
        # Grouped leaf strokes with low contrast; not evenly sprayed grit.
        for k in range(7800):
            x,y=rng.integers(0,n,2);length=int(rng.integers(3,9));lean=rng.uniform(-.35,.35);tone=rng.uniform(.82,1.16)
            for t in range(length):
                px=(x+int(t*lean))%n;py=(y+t)%n
                rgb[py,px]=base*tone*(.98+.04*t/length)
    if kind==1:
        rgb*=1+.018*np.sin(yy[:,:,None]*.065+.8*np.sin(xx[:,:,None]*.022))
    rgba=np.ones((n,n,4),np.float32);rgba[:,:,:3]=np.clip(rgb,0,1)
    im=bpy.data.images.new(name,width=n,height=n);im.pixels.foreach_set(rgba.ravel());im.filepath_raw=str(OUT/(name+'.png'));im.file_format='PNG';im.save();im.pack();return im

grass_image=painted_image('S23_LivingGrass',0);soil_image=painted_image('S23_CutEarth',1);path_image=painted_image('S23_WornEarth',2)
landmat=bpy.data.materials.new('Ref_S23_Landscape');landmat.use_nodes=True
nodes=landmat.node_tree.nodes;links=landmat.node_tree.links;p=nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.96;p.inputs['Specular IOR Level'].default_value=.1
attr=nodes.new('ShaderNodeVertexColor');attr.layer_name='LandUse';separate=nodes.new('ShaderNodeSeparateColor');links.new(attr.outputs['Color'],separate.inputs['Color'])
textures=[]
for im in [path_image,soil_image,grass_image]:
    tx=nodes.new('ShaderNodeTexImage');tx.image=im;textures.append(tx)
mix1=nodes.new('ShaderNodeMixRGB');links.new(separate.outputs['Green'],mix1.inputs[0]);links.new(textures[0].outputs['Color'],mix1.inputs[1]);links.new(textures[1].outputs['Color'],mix1.inputs[2])
mix2=nodes.new('ShaderNodeMixRGB');links.new(separate.outputs['Red'],mix2.inputs[0]);links.new(mix1.outputs[0],mix2.inputs[1]);links.new(textures[2].outputs['Color'],mix2.inputs[2]);links.new(mix2.outputs[0],p.inputs['Base Color'])
data.materials.append(landmat)
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
def ground(x,z):
    hit,n,i,d=ground_bvh.ray_cast(Vector((x,-z,60)),Vector((0,0,-1)),300)
    return hit.z if hit else new_sample(x-shore(z),z)[0]

# Export collision queries from the actual finished surface, not a second formula.
samples=[round(ground(shore(z)+d,z),5) for z in np.arange(-30,90.001,.25) for d in np.arange(-20,50.001,.25)]
(OUT/'shore_relief_height.json').write_text(json.dumps({'d0':-20,'z0':-30,'step':.25,'columns':281,'rows':481,'heights':samples}),encoding='utf8')
(LOG/'new_landform.json').write_text(json.dumps({'source':bpy.data.filepath,'vertices':len(data.vertices),'faces':len(data.polygons),'continuous_surface':True,'separate_turf_skins':0,'terrace_levels':[levels(z) for z in [0,20,40,60,80]]},indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_landscape_redesign_mcp.blend'))
print('NEW_LANDFORM',len(data.vertices),len(data.polygons),'archived',len(archive.objects),'objects')
