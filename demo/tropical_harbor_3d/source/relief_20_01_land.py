# Run only inside the verified, isolated Blender MCP session.
import bmesh

def center(ob):
    return sum((ob.matrix_world@Vector(p) for p in ob.bound_box),Vector())/8
def foot(ob):
    ps=[ob.matrix_world@v.co for v in ob.data.vertices];low=min(p.z for p in ps)
    bottom=[p for p in ps if p.z<low+.04]
    return sum(bottom,Vector())/len(bottom)
def suffix(ob):
    s=ob.name.rsplit('.',1)[-1]
    return int(s) if s.isdigit() else 0

def profile(z,points):
    if z<=points[0][0]:return points[0][1]
    for (a,av),(b,bv) in zip(points,points[1:]):
        if a<=z<=b:return av+(bv-av)*smooth(a,b,z)
    return points[-1][1]
def edge1(z):
    return profile(z,[(0,3.2),(5,2.8),(10,4.2),(14,2.35),(20,3.4),(25,2.4),(30,4.0),(34,2.15),(39,4.8),(43,4.8),(47,2.15),(51,2.5),(54,3.25),(58,2.2),(62,3.7),(68,4.1),(71,2.25),(75,4.1),(80,3.1)])+.075*math.sin(z*1.5)+.04*math.sin(z*3.3)
def edge2(z):return 10.85+.45*math.sin(z*.21)+.20*math.sin(z*.57)
def edge3(z):return 20.7+.65*math.sin(z*.14)+.23*math.sin(z*.47)
def pierdist(z):return min(abs(z-k) for k in [73,43,38,9])
def courtyard_open(z):
    return max(1-smooth(2.0,3.6,abs(z-40.5)),1-smooth(.8,2.1,abs(z-9)),1-smooth(.8,2.1,abs(z-73)))
def new_land(x,z):
    d=x-shore(z);old=old_ground(x,z)
    if d<.1 or d>36 or z<0 or z>82:return old
    h=.38*smooth(0,2.0,d)
    first=1.52*smooth(edge1(z)-.40,edge1(z)+.16,d)
    opening=courtyard_open(z)
    first=first*(1-opening)+1.52*smooth(4.5,6.35,d)*opening
    second=.86*smooth(edge2(z)-.28,edge2(z)+.13,d)+1.49*smooth(edge2(z)+1.72,edge2(z)+2.16,d)
    third=.94*smooth(edge3(z)-.35,edge3(z)+.20,d)+1.71*smooth(edge3(z)+2.2,edge3(z)+2.75,d)
    for cross in [61,44,29,12]:
        r=1-smooth(.85,1.9,abs(z-cross))
        second=second*(1-r)+2.35*smooth(9.3,14.5,d)*r
    h+=first+second+third+.05*math.sin(z*.16)*smooth(3,6,d)
    h+=(.065*math.sin(z*.65+d*.7)+.03*math.sin(z*1.5-d*.8))*smooth(6.8,8,d)
    pad=0
    for s in SITES:
        keep=(1-smooth(s['w']/2+.25,s['w']/2+.9,abs(z-s['gz'])))*(1-smooth(s['depth']/2+.35,s['depth']/2+.85,abs(d-s['d'])))
        pad=max(pad,keep)
    h=h*(1-pad)+(old+.65)*pad
    cargo=(1-smooth(3.0,4.5,abs(z-65.2)))*(1-smooth(10,12,d))
    pier=(1-smooth(.7,1.35,pierdist(z)))*(1-smooth(1.7,3.0,d))
    blend=smooth(0,4,z)*(1-smooth(77,82,z))*(1-smooth(33,36,d))*(1-max(cargo,pier))
    return old+(h-old)*blend

# Authored surface images: clustered grass strokes and compacted earth,
# all image and material creation occurs in this Blender MCP execution.
def image_material(name,kind):
    n=1024;yy,xx=np.mgrid[0:n,0:n].astype(np.float32);rng=np.random.default_rng(521 if kind=='turf' else 612)
    field=np.zeros((n,n),np.float32)
    for scale,amp in [(2,.055),(5,.045),(13,.018),(39,.008)]:
        for k in range(3):
            angle=rng.random()*math.tau;phase=rng.random()*math.tau
            field+=amp/3*np.sin((xx*math.cos(angle)+yy*math.sin(angle))*math.tau*scale/n+phase)
    base=np.array([.38,.52,.16] if kind=='turf' else [.38,.24,.12],np.float32)
    rgb=np.clip(base[None,None,:]*(1+field[:,:,None]*2),0,1)*np.ones((n,n,3),np.float32)
    heightmap=np.ones((n,n),np.float32)*.5
    if kind=='turf':
        for i in range(23000):
            x,y=rng.integers(0,n,2);length=int(rng.integers(3,12));width=int(rng.integers(1,3));theta=rng.uniform(-.7,.7)
            tone=rng.choice([.65,.78,.9,1.05,1.13,1.23]);lean=math.sin(theta)
            for k in range(length):
                a=(x+int(k*lean))%n;b=(y-k)%n;w=max(1,int(width*(1-k/length)))
                for off in range(-w,w+1):
                    rgb[b,(a+off)%n]=np.clip(base*tone*(.93+.12*k/length),0,1);heightmap[b,(a+off)%n]=.55+.32*k/length
    else:
        for i in range(16000):
            x,y=rng.integers(0,n,2);rx=int(rng.integers(1,7));ry=int(rng.integers(1,4));tone=rng.uniform(.82,1.14)
            for dy in range(-ry,ry+1):
                for dx in range(-rx,rx+1):
                    if (dx/rx)**2+(dy/ry)**2<1:
                        rgb[(y+dy)%n,(x+dx)%n]*=tone;heightmap[(y+dy)%n,(x+dx)%n]=tone*.5
    rgba=np.ones((n,n,4),np.float32);rgba[:,:,:3]=np.clip(rgb,0,1)
    im=bpy.data.images.new('Ref_'+name+'_Albedo',width=n,height=n);im.pixels.foreach_set(rgba.ravel());im.filepath_raw=str(OUT/(im.name+'.png'));im.file_format='PNG';im.save();im.pack()
    dx=np.roll(heightmap,1,1)-np.roll(heightmap,-1,1);dy=np.roll(heightmap,1,0)-np.roll(heightmap,-1,0)
    normal=np.stack([dx*.30,dy*.30,np.ones_like(dx)],2);normal/=np.linalg.norm(normal,axis=2)[:,:,None]
    rgba[:,:,:3]=normal*.5+.5
    ni=bpy.data.images.new('Ref_'+name+'_Normal',width=n,height=n);ni.colorspace_settings.name='Non-Color';ni.pixels.foreach_set(rgba.ravel());ni.filepath_raw=str(OUT/(ni.name+'.png'));ni.file_format='PNG';ni.save();ni.pack()
    m=material(name,'66852a' if kind=='turf' else '64401f','plain');nodes=m.node_tree.nodes;links=m.node_tree.links;p=nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.96;p.inputs['Specular IOR Level'].default_value=.12
    tex=nodes.new('ShaderNodeTexImage');tex.image=im;links.new(tex.outputs['Color'],p.inputs['Base Color'])
    tex=nodes.new('ShaderNodeTexImage');tex.image=ni;nm=nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.50;links.new(tex.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],p.inputs['Normal'])
    return m

turfmat=image_material('R21_Turf','turf');soilmat=image_material('R21_BankSoil','soil')
rootmat=material('R21_TurfRoot','4d6327','plain');rootmat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.98
archive=bpy.data.collections.new('Archive_R21_FlatGround');bpy.context.scene.collection.children.link(archive);archive.hide_render=True;archive.hide_viewport=True
old=terrain.copy();old.data=terrain.data.copy();archive.objects.link(old);old.name='R21_PreviousGround'
for ob in list(fol.objects):
    if ob.name.startswith(('S20_GrassCapTufts','S20_GrassRootLip')):archive.objects.link(ob);fol.objects.unlink(ob)

# Each shoreline row explicitly samples foot, wall, shoulder and shelf.
zs=sorted(set([-70+j*.75 for j in range(94)]+[j*.25 for j in range(329)]+[83+j*.75 for j in range(22)]))
vs=[];fs=[];rowds=[]
for z in zs:
    e=edge1(z);a=edge2(z);b=edge3(z)
    ds=[-180,-120,-65,-35,-20,-12,-8,-5,-3,-2,-1,0,.45,.9,1.35]
    ds += [e-.55,e-.40,e-.23,e-.08,e+.16,e+.32]
    ds += [e+.32+(8.8-e-.32)*j/20 for j in range(1,21)]
    ds += [a-.6,a-.28,a-.1,a+.13,a+.32,a+.85,a+1.42,a+1.72,a+1.90,a+2.16,a+2.35]
    ds += [a+2.35+(19.3-a-2.35)*j/20 for j in range(1,21)]
    ds += [b-.6,b-.35,b-.1,b+.2,b+.4,b+1.0,b+1.8,b+2.2,b+2.45,b+2.75,b+3.0]
    ds += [b+3+(36-b-3)*j/16 for j in range(1,17)]+[40,65,120]
    assert all(v>u for u,v in zip(ds,ds[1:])),(z,ds)
    rowds.append(ds)
    for d in ds:
        x=shore(z)+d;vs.append((x,-z,new_land(x,z)))
w=len(rowds[0]);assert all(len(ds)==w for ds in rowds)
for j in range(len(zs)-1):
    for i in range(w-1):a=j*w+i;fs.append((a,a+w,a+w+1,a+1))
C=bpy.data.collections['Reference_Terrain'];temp=mesh('R21_SculptedGround',vs,fs,terrain.data.materials[0],.8);terrain.data=temp.data;bpy.data.objects.remove(temp,do_unlink=True)
terrain.data.materials.append(soilmat)
for p in terrain.data.polygons:
    z=-p.center.y;p.material_index=1 if 0<z<82 and p.normal.z<.74 and p.center.z>.40 else 0;p.use_smooth=True
# Split the top/soil seam so a rounded normal cannot erase the ledge.
bm=bmesh.new();bm.from_mesh(terrain.data)
bmesh.ops.split_edges(bm,edges=[e for e in bm.edges if len(e.link_faces)==2 and e.link_faces[0].material_index!=e.link_faces[1].material_index]);bm.to_mesh(terrain.data);bm.free()
terrain.data.update();bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
def ground(x,z):
    hit,n,i,d=ground_bvh.ray_cast(Vector((x,-z,40)),Vector((0,0,-1)),120)
    return hit.z if hit else new_land(x,z)

# Move complete building/plant/prop assemblies, preserving their internal joints.
moved=set();moves=[]
def raise_group(obs,x,z,mode='delta'):
    dh=ground(x,z)-old_ground(x,z)
    if abs(dh)<.001:return
    for ob in obs:
        if ob.name in moved:continue
        ob.matrix_world=Matrix.Translation((0,0,dh))@ob.matrix_world;moved.add(ob.name)
    moves.append({'x':x,'z':z,'height_delta':dh,'components':len(obs)})
for s in SITES:
    obs=[o for o in town.objects if o.get('town_building')==s['name'] and not o.name.startswith('Town20_ConnectedApron')]
    raise_group(obs,shore(s['gz'])+s['d'],s['gz'])
for ob in town.objects:
    if ob.name.startswith('Town20_ConnectedApron'):
        inv=ob.matrix_world.inverted()
        for v in ob.data.vertices:
            p=ob.matrix_world@v.co;p.z=ground(p.x,-p.y)+.025;v.co=inv@p
        ob.data.update()
trunks=sorted([o for o in fol.objects if o.name=='Tree_Trunk' or o.name.startswith('Tree_Trunk.')],key=suffix)
crowns=sorted([o for o in fol.objects if o.name.startswith('D19_Tree_Crown')],key=suffix);branches=sorted([o for o in fol.objects if o.name=='Tree_Branch' or o.name.startswith('Tree_Branch.')],key=suffix)
for i,t in enumerate(trunks):
    p=foot(t);raise_group([t]+crowns[i*6:(i+1)*6]+branches[i*5:(i+1)*5],p.x,-p.y)
palms=sorted([o for o in fol.objects if o.name=='Palm_Trunk' or o.name.startswith('Palm_Trunk.')],key=suffix)
parts={k:sorted([o for o in fol.objects if o.name.startswith(prefix)],key=suffix) for k,prefix in [('rachis','D19_Palm_FrondRachis'),('leaves','D19_Palm_FrondLeaflets'),('nuts','Palm_Coconut'),('rings','D19_Palm_GrowthRing')]}
for i,t in enumerate(palms):
    p=foot(t);obs=[t]+parts['rachis'][i*8:(i+1)*8]+parts['leaves'][i*8:(i+1)*8]+parts['nuts'][i*3:(i+1)*3]+parts['rings'][i*12:(i+1)*12];raise_group(obs,p.x,-p.y)
# Ground-level foliage is moved individually, then pushed into its actual support.
for ob in fol.objects:
    if ob.name in moved:continue
    p=center(ob);z=-p.y
    if not 0<z<82:continue
    raise_group([ob],p.x,z)
    if ob.name.startswith('S20_CourtyardShrub'):
        ps=[ob.matrix_world@v.co for v in ob.data.vertices];lo=Vector([min(p[k] for p in ps) for k in range(3)]);hi=Vector([max(p[k] for p in ps) for k in range(3)]);mid=(lo+hi)/2
        hs=[ground(mid.x+(hi.x-lo.x)*a,-mid.y+(hi.y-lo.y)*b) for a,b in [(0,0),(-.4,0),(.4,0),(0,-.4),(0,.4)]]
        ob.location.z+=min(hs)-.10-lo.z
# Connected components by overlapping XY bounds keep crate rails, barrel hoops,
# net cords and hut joinery together rather than changing each part's height.
remaining=[o for o in coast.objects if not o.name.startswith(('Pier_','Arrival_','S20_DeckPeg','S20_PileEndGrain','S20_MooringKnot','S20_RopeTail','S20_PileBracket','D19_Deck','D19_Pile','D19_Mooring','D19_RopeTail'))]
# Residential hut pieces are associated with their floor first.
floors=[o for o in remaining if o.name.startswith('Hut_Floor')];hutgroups={o.name:[] for o in floors}
for ob in remaining:
    if ob.name.startswith(('Hut_','D19_Hut','D19_Thatch','D19_Reed')):
        p=center(ob);f=min(floors,key=lambda f:(center(f).xy-p.xy).length);hutgroups[f.name].append(ob)
for f in floors:
    p=center(f);raise_group(hutgroups[f.name],p.x,-p.y)
# For ground props use compact 2D groups and common mean support delta.
obs=[o for o in remaining if o.name not in moved];bounds=[]
for ob in obs:
    ps=[ob.matrix_world@Vector(p) for p in ob.bound_box];bounds.append((min(p.x for p in ps),max(p.x for p in ps),min(p.y for p in ps),max(p.y for p in ps)))
parent=list(range(len(obs)))
def find(a):
    while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
    return a
for i,(x0,x1,y0,y1) in enumerate(bounds):
    for j in range(i):
        a,b,c,d=bounds[j]
        if x0<=b+.07 and x1>=a-.07 and y0<=d+.07 and y1>=c-.07:parent[find(i)]=find(j)
groups={}
for i,o in enumerate(obs):groups.setdefault(find(i),[]).append(o)
for objects in groups.values():
    ps=[center(o) for o in objects];p=sum(ps,Vector())/len(ps);raise_group(objects,p.x,-p.y)
for ob in bpy.data.collections['Reference_Rocks'].objects:
    p=center(ob);raise_group([ob],p.x,-p.y)

bpy.context.view_layer.update()
(LOG/'land_authored.json').write_text(json.dumps({'vertices':len(terrain.data.vertices),'faces':len(terrain.data.polygons),'moved_components':len(moved),'groups':moves},indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/reference_harbor_mcp.blend'))
print('RELIEF_LAND',len(terrain.data.vertices),'vertices',len(moved),'components regrounded')
