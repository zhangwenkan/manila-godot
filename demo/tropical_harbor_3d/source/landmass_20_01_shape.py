# Authored two-dimensional land masses. Execute only through Blender MCP.
# Toe and crown plans are independent. No repeating shore cross-section.
archive=bpy.data.collections.new('Archive_RejectedStripTerrain_20261120')
bpy.context.scene.collection.children.link(archive)
for ob in list(C.objects):
    archive.objects.link(ob);C.objects.unlink(ob)
for ob in list(fol.objects):
    if ob.name.startswith('S23_Grass'):
        archive.objects.link(ob);fol.objects.unlink(ob)
archive.hide_render=True;archive.hide_viewport=True

def close_plan(front):
    return front+[(140,front[-1][1]),(140,front[0][1])]
LOW_TOP=close_plan([(3,-70),(3,-20),(3.5,-5),(3.1,1),(2.3,6),(2.7,9),(4.8,13),(6.1,16),(5.8,19),(4.4,22),(4.6,26),(5.7,30),(7.3,34),(6.0,38),(3.0,40),(2.4,43),(3.6,46),(5.1,49),(5.8,53),(4.6,57),(3.3,60),(4.1,64),(4.5,69),(3,76),(2.7,84),(3,110)])
LOW_TOE=close_plan([(1.6,-70),(1.5,-20),(1.4,-4),(1.9,2),(1.0,5),(1.6,10),(3.5,13),(4.3,16),(4.5,20),(2.8,23),(3.2,27),(4.0,31),(5.5,35),(4.5,37),(1.7,40),(1.0,44),(2.7,48),(4.1,51),(4.6,54),(3.2,58),(1.8,61),(2.6,65),(2.9,70),(1.5,78),(1.4,86),(1.5,110)])
HIGH_TOP=close_plan([(17,-70),(17,-20),(15,-7),(13,1),(12.8,7),(11.5,10),(8.8,12),(8.1,14),(10.7,17),(13.5,20),(15.4,24),(14.7,27),(13.5,30),(14.6,32),(18.1,35),(18.5,37),(13.2,39),(11.8,42),(12.8,45),(14.7,48),(16.3,51),(17.2,53),(14.1,55),(12.3,58),(11.1,61),(13.6,64),(16.6,67),(18.1,71),(15,77),(13,84),(15,110)])
HIGH_TOE=close_plan([(12,-70),(12,-20),(10,-5),(10.8,2),(10.4,7),(9.0,9.5),(6.7,11.7),(6.1,14.2),(8.2,16.8),(11.9,21),(13.4,25),(12.4,28),(11.3,30.2),(12.4,33),(15.3,35.5),(15.6,37),(10.8,38.5),(9.8,41.5),(10.5,44),(12.4,47.5),(14.0,50.8),(14.7,53.6),(11.9,55.5),(10.4,58.3),(8.9,61.6),(11.7,64.4),(14.1,68),(15.7,72),(12.7,78),(10.8,85),(12,110)])

def signed_distance(d,z,polygon):
    # Positive inside; exact distances to the authored straight plan segments.
    inside=np.zeros_like(d,dtype=bool);distance=np.full_like(d,1e6)
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        ax,az=a;bx,bz=b;vx=bx-ax;vz=bz-az
        t=np.clip(((d-ax)*vx+(z-az)*vz)/(vx*vx+vz*vz),0,1)
        distance=np.minimum(distance,np.hypot(d-(ax+t*vx),z-(az+t*vz)))
        if abs(bz-az)>1e-8:
            inside^=((az>z)!=(bz>z)) & (d<(bx-ax)*(z-az)/(bz-az)+ax)
    return np.where(inside,distance,-distance)

def mass_fraction(d,z,toe,crown):
    a=signed_distance(d,z,toe);b=signed_distance(d,z,crown)
    t=np.clip(a/(np.maximum(a,0)+np.maximum(-b,0)+1e-5),0,1)
    # A broad toe, a substantial steeper face, then a short softened shoulder.
    f=np.interp(t,[0,.12,.32,.82,.94,1],[0,.035,.19,.86,.985,1])
    return np.where(b>=0,1,f),a,b

# Elevation-controlled access winds through existing gaps between buildings.
RAMPS=[[(.6,34.5,.15),(5.6,34.5,.85),(10,35.1,1.50),(15,36.0,2.7),(19.7,38.4,4.25)],
       [(.6,53.2,.15),(5.4,53.0,.9),(9.5,52.4,1.28),(14.4,52.0,2.55),(19.9,54.0,4.1)]]
def route_distance(d,z,points):
    best=np.full_like(d,1e6);elev=np.zeros_like(d)
    for a,b in zip(points,points[1:]):
        vx=b[0]-a[0];vz=b[1]-a[1]
        t=np.clip(((d-a[0])*vx+(z-a[1])*vz)/(vx*vx+vz*vz),0,1)
        dist=np.hypot(d-(a[0]+t*vx),z-(a[1]+t*vz))
        hit=dist<best;elev=np.where(hit,a[2]+(b[2]-a[2])*t,elev);best=np.minimum(best,dist)
    return best,elev

def shape(d,z):
    base=.12+.23*smooth(.3,2.3,d)+.07*smooth(3,8,d)
    lower,ld,lc=mass_fraction(d,z,LOW_TOE,LOW_TOP)
    lowheight=np.interp(z,[-70,0,9,20,28,34,40,44,49,57,62,69,85,110],[1.1,1.35,1.35,1.22,1.22,1.1,1.65,1.65,1.18,1.18,1.24,1.25,1.15,1.15])
    h=base+(lowheight-base)*lower
    upper,ud,uc=mass_fraction(d,z,HIGH_TOE,HIGH_TOP)
    highheight=np.interp(z,[-70,-10,10,19,29,38,46,54,63,73,90,110],[3.1,3.4,4.05,4.05,4.30,4.25,4.15,4.1,4.5,3.8,3.6,3.6])
    highheight+=.045*np.sin(d*.46+z*.17)*smooth(1,4,uc)
    h=h+(highheight-h)*upper
    # Two wide, asymmetric inland ridges; neither tracks the shoreline.
    ridge1=np.exp(-(((d-35)*.75+(z-20)*.23)/12)**4-((z-20)/27)**4)
    ridge2=np.exp(-(((d-37)*.8-(z-66)*.19)/15)**4-((z-66)/24)**4)
    h+=smooth(24,31,d)*(2.25*ridge1+3.1*ridge2)
    road=np.zeros_like(d)
    for points in RAMPS:
        distance,elev=route_distance(d,z,points)
        grade=1-smooth(1.05,2.35,distance)
        h=h*(1-grade)+elev*grade
        road=np.maximum(road,1-smooth(.85,1.25,distance))
    # Restrained, broad irregularities on exposed faces, not repetitive ripples.
    face=(4*lower*(1-lower)+4*upper*(1-upper))*(1-road)
    h+=face*(.045*np.sin(d*1.7+z*.57)+.022*np.sin(z*1.6-d*.73))
    return h,road,lower,upper

ds=np.concatenate(([-180,-120,-80,-50,-35,-25,-20,-15,-12,-9,-7,-5,-3,-2,-1,0],np.arange(.32,22.01,.32),np.arange(22.5,50.01,.5),[55,65,80,100,120]))
zs=np.concatenate((np.arange(-70,-15,2),np.arange(-15,90.001,.32),np.arange(92,111,2)))
dd,zz=np.meshgrid(ds,zs);width=len(ds);heightrows=len(zs)
rng=np.random.default_rng(20411)
interior=(dd>.1)&(dd<50)&(zz>-14)&(zz<89)
dd=dd+interior*rng.uniform(-.045,.045,dd.shape)
zz=zz+interior*rng.uniform(-.045,.045,dd.shape)
d=dd.ravel();z=zz.ravel();x=shore(z)+d
h,road,lower,upper=shape(d,z)
keep=(d<=0)|((np.abs(z-65.2)<3.6)&(x<18.4))
for i in np.where(keep)[0]:h[i]=old_ground(float(x[i]),float(z[i]))
# Blend the dry rim of the working basin while preserving its entire seabed.
rim=(1-smooth(3.6,4.6,np.abs(z-65.2)))*(1-smooth(18.4,19.5,x))
for i in np.where((rim>0)&~keep)[0]:h[i]=h[i]*(1-rim[i])+old_ground(float(x[i]),float(z[i]))*rim[i]
vv=np.column_stack((x,-z,h)).astype(np.float32)
faces=[]
for j in range(heightrows-1):
    for i in range(width-1):
        a=j*width+i;b=a+width
        if (i+j)%2:faces.extend([(a,b,b+1),(a,b+1,a+1)])
        else:faces.extend([(a,b,a+1),(a+1,b,b+1)])
data=bpy.data.meshes.new('L24_IndependentCrownToeTopology');data.from_pydata(vv.tolist(),[],faces);data.update()
terrain=bpy.data.objects.new('L24_AuthoredCoastalMasses',data);C.objects.link(terrain)
uv=data.uv_layers.new(name='UVMap');vi=np.empty(len(data.loops),np.int32);data.loops.foreach_get('vertex_index',vi)
uv.data.foreach_set('uv',(vv[vi,:2]/2.4).ravel())
for p in data.polygons:p.use_smooth=True
data.set_sharp_from_angle(angle=math.radians(48))
# Provisional neutral material; clay review overrides this in the main scene.
mat=bpy.data.materials.new('Ref_L24_Landform');mat.use_nodes=True
p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.30,.32,.29,1);p.inputs['Roughness'].default_value=.96
data.materials.append(mat)
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
def ground(x,z):
    hit,*_=ground_bvh.ray_cast(Vector((x,-z,80)),Vector((0,0,-1)),300)
    return hit.z if hit else -15
def refresh_height():
    samples=[round(ground(float(shore(z)+d),float(z)),5) for z in np.arange(-30,90.001,.25) for d in np.arange(-20,50.001,.25)]
    (OUT/'shore_relief_height.json').write_text(json.dumps({'d0':-20,'z0':-30,'step':.25,'columns':281,'rows':481,'heights':samples}),encoding='utf8')
refresh_height()
(LOG/'authored_plan.json').write_text(json.dumps({'low_toe':LOW_TOE,'low_crown':LOW_TOP,'high_toe':HIGH_TOE,'high_crown':HIGH_TOP,'ramps':RAMPS,'vertices':len(vv),'triangles':len(faces)},indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_landform_mass_mcp.blend'))
print('LAND_MASSES',len(vv),'vertices',len(faces),'triangles; independent toe/crown plans; two access valleys')
