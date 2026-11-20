# Executed only inside the verified independent Blender MCP session.
C=fol;rr=random.Random(2026112003)
tree_sites=[(25,10.2,53.1,1.0),(24,19.0,64.8,1.10),(23,19.4,52.8,.88),
            (22,10.1,35.3,.92),(21,19.5,40.3,.82),(34,20.1,33.0,.72),
            (35,10.0,20.0,.88),(36,20.0,21.0,.94),(31,19.3,74.5,.83),(30,10.1,70.0,.88)]
tree_report=[]
for i,d,z,scale in tree_sites:
    source=foot(trunks[i]);x=shore(z)+d;h=ground(x,z)
    tf=Matrix.Translation((x,-z,h))@Matrix.Rotation(rr.uniform(-.5,.5),4,'Z')@Matrix.Diagonal((scale,scale,scale,1))@Matrix.Translation(-source)
    group=[trunks[i]]+crowns[i*6:(i+1)*6]+branches[i*5:(i+1)*5]
    for ob in group:ob.matrix_world=tf@ob.matrix_world
    tree_report.append({'tree':i,'x':x,'z':z,'ground':h,'scale':scale})

def clone_group(objects, x,z,scale=1.0,yaw=0,lift=0,label='Prop'):
    ps=[ob.matrix_world@Vector(v) for ob in objects for v in ob.bound_box]
    low=Vector([min(p[k] for p in ps) for k in range(3)]);high=Vector([max(p[k] for p in ps) for k in range(3)])
    origin=(low+high)/2;origin.z=low.z
    tf=Matrix.Translation((x,-z,ground(x,z)+lift))@Matrix.Rotation(yaw,4,'Z')@Matrix.Diagonal((scale,scale,scale,1))@Matrix.Translation(-origin)
    out=[]
    for src in objects:
        ob=src.copy();ob.data=src.data;C.objects.link(ob);ob.name='S20_'+label+'_'+src.name;ob.matrix_world=tf@src.matrix_world;out.append(ob)
    return out

# Bushes have clusters of overlapping crowns at the foot of trees and cut banks.
bush_sites=[(10.5,53.4,2.1,.85),(10.8,35.7,2.1,.85),(20.5,65.4,2.7,1.05),
            (19.5,53.8,1.9,.75),(18.5,41.3,1.6,.7),(10.7,20.4,1.8,.75),
            (19.6,22.0,2.1,.9),(10.3,70.8,2.0,.8),(3.8,55.1,1.3,.6),
            (3.9,46.8,1.2,.55),(3.8,31.5,1.6,.65),(12.0,57.4,1.4,.65),
            (12.1,50.4,1.2,.6),(22.0,61.7,2.1,.85),(22.4,48.5,2.0,.9)]
for i,(d,z,diam,h) in enumerate(bush_sites):
    for j in range(4):
        angle=j*2.2+i;radius=.20 if j==0 else diam*.27
        zz=z+math.sin(angle)*radius;xx=shore(zz)+d+math.cos(angle)*radius
        src=crowns[(i*13+j*7)%len(crowns)];ps=[src.matrix_world@v.co for v in src.data.vertices]
        lo=Vector([min(p[k] for p in ps) for k in range(3)]);hi=Vector([max(p[k] for p in ps) for k in range(3)]);size=hi-lo;mid=(hi+lo)/2
        factor=1 if j==0 else .67
        ob=src.copy();ob.data=src.data;C.objects.link(ob);ob.name='S20_CourtyardShrub'
        ob.matrix_world=Matrix.Translation((xx,-zz,ground(xx,zz)-.09))@Matrix.Diagonal((diam*.55*factor/size.x,diam*.50*factor/size.y,h*factor/size.z,1))@Matrix.Translation((-mid.x,-mid.y,-lo.z))@src.matrix_world

# Reuse complete boxes/barrels with their current UVs, hoops, lids and frames.
C=coast
barrel=[bpy.data.objects[n] for n in ['Prop_Barrel.007','Barrel_IronHoop.014','Barrel_IronHoop.015','Barrel_Lid.007']]
crate=[bpy.data.objects['Prop_Crate.013']]+[bpy.data.objects['Crate_Frame.%03d'%i] for i in range(52,56)]+[bpy.data.objects['Crate_Rail.%03d'%i] for i in range(52,56)]+[bpy.data.objects['Crate_Diagonal.%03d'%i] for i in range(26,28)]
rope=[bpy.data.objects['Rope_Coil.004']]
sack=[bpy.data.objects['TR20_ProduceSack']]
stacks=[(7.8,69.1,'cargo'),(7.2,71.1,'cargo'),(8.5,53.4,'shop'),(9.3,52.3,'shop'),
        (4.0,45.7,'fishing'),(4.4,40.1,'fishing'),(8.6,36.4,'fishing'),
        (17.7,64.4,'school'),(8.0,20.1,'grill'),(6.9,11.8,'trade')]
prop_count=0
for i,(d,z,kind) in enumerate(stacks):
    x=shore(z)+d
    for j in range(3 if kind in ['cargo','fishing'] else 2):
        obj=crate if j!=1 else barrel
        dx=(j%2)*.85;dz=(j//2)*.88;sc=1.28 if obj is crate else 1.42
        prop_count+=len(clone_group(obj,x+dx,z+dz,sc,rr.uniform(-.3,.3),label=kind))
    if i%2==0:
        prop_count+=len(clone_group(crate,x,z,1.15,.14,lift=.76,label=kind+'Stack'))
        prop_count+=len(clone_group(rope,x+.65,z-.60,1.5,.3,label=kind+'Rope'))
    if kind in ['shop','trade']:
        for j in range(3):prop_count+=len(clone_group(sack,x-.45+j*.25,z+.75,1.35,.3,label='SupplySack'))

# A short, supported bench and timber rack belong to the shaded side yard.
wood=bpy.data.materials['Ref_TR20_wood'];beam_mat=bpy.data.materials['Ref_D19_Wood'];cord=bpy.data.materials['Ref_Rope']
for d,z in [(9.9,51.6),(18.8,63.4)]:
    x=shore(z)+d;h=ground(x,z)
    for yoff in [-.14,.14]:box('S20_ShadeBenchSeat',(x,-z+yoff,h+.49),(1.7,.25,.065),wood,.01)
    for dx in [-.61,.61]:
        box('S20_ShadeBenchSupport',(x+dx,-z,h+.24),(.13,.42,.48),beam_mat,.012)
for d,z in [(3.6,40.2),(7.4,70.7)]:
    x=shore(z)+d;h=ground(x,z)
    for j in range(5):
        ob=box('S20_TimberStack',(x+(j%2)*.18,-z,h+.12+(j//2)*.11),(1.6,.13,.10),wood,.01)
        ob.rotation_euler.z=.09
    for dx in [-.58,.58]:box('S20_StackBearers',(x+dx,-z,h+.05),(.14,.46,.10),beam_mat,.012)

# Small net rack faces its pier, its loose lower edge stays above the ground.
x=shore(41.0)+4.3;z=41.0;h=ground(x,z)
for dx in [-1.0,1.0]:tube('S20_NetPost',[(x+dx,-z,h-.12),(x+dx,-z,h+1.5)],.055,wood,8)
beam('S20_NetRail',(x-1.04,-z,h+1.45),(x+1.04,-z,h+1.45),.065,wood)
for j in range(15):
    dx=-.93+j*1.86/14
    tube('S20_NetVertical',[(x+dx,-z+.10*math.sin(k/5*math.pi),h+1.39-k*.19-.09*math.cos(dx*1.5)) for k in range(6)],.009,cord,5)
for k in range(6):tube('S20_NetHorizontal',[(x-.93+j*1.86/14,-z+.10*math.sin(k/5*math.pi),h+1.39-k*.19-.09*math.cos((-.93+j*1.86/14)*1.5)) for j in range(15)],.009,cord,5)

# Embed stones where the grass banks change direction, preserving open beaches.
rocks=bpy.data.collections['Reference_Rocks'];rock_report=[]
rock_targets=[(1.5,74.8),(2.0,74.2),(2.7,75.2),(2.8,56.0),(3.1,55.5),(3.5,55.9),
              (2.3,46.6),(2.8,46.2),(3.1,46.9),(2.4,31.4),(2.9,30.8),(3.3,31.7),
              (2.0,20.4),(2.7,20.0),(3.3,20.8),(2.7,11.3),(3.2,10.8)]
active=[o for o in rocks.objects if 0 < -center(o).y < 80]
for i,ob in enumerate(active):
    d,z=rock_targets[i%len(rock_targets)];x=shore(z)+d
    ps=[ob.matrix_world@v.co for v in ob.data.vertices];low=min(p.z for p in ps);mid=sum(ps,Vector())/len(ps);mid.z=low
    sc=1.25 if i%3==0 else .68 if i%3==1 else .92
    tf=Matrix.Translation((x,-z,ground(x,z)-.25*sc))@Matrix.Rotation(rr.random()*math.tau,4,'Z')@Matrix.Diagonal((sc,sc,sc,1))@Matrix.Translation(-mid)
    ob.matrix_world=tf@ob.matrix_world;rock_report.append(ob.name)
# Larger embedded rock outcrops at two courtyard bank toes.
C=rocks
for i,(d,z) in enumerate([(11.0,54.5),(11.2,34.1),(21.6,64.0),(21.5,51.0)]):
    src=active[(i*3)%len(active)];x=shore(z)+d
    clone_group([src],x,z,1.1,rr.random(),lift=-.22,label='BankOutcrop')

bpy.context.view_layer.update()
report={'trees':tree_report,'shrub_groups':len(bush_sites),'supply_groups':len(stacks),'cloned_supply_parts':prop_count,'moved_rocks':len(rock_report)}
(LOG/'space_groups.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(report)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/reference_harbor_mcp.blend'))
