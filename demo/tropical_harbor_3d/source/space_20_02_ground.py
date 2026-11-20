# Executed only inside the verified independent Blender MCP session.
old_bvh = BVHTree.FromObject(terrain, bpy.context.evaluated_depsgraph_get())
def previous_ground(x, z):
    hit, normal, index, distance = old_bvh.ray_cast(Vector((x, -z, 35)), Vector((0, 0, -1)), 100)
    return hit.z if hit is not None else height(x-shore(z), z)

def first_edge(z): return 2.9 + .48*math.sin(z*.38) + .24*math.sin(z*.87)
def second_edge(z): return 11.4 + .58*math.sin(z*.27) + .23*math.sin(z*.65)
def third_edge(z): return 22.1 + .65*math.sin(z*.19)
def access(z): return min(abs(z-k) for k in [61,44,29,12])
def pier_access(z): return min(abs(z-k) for k in [73,43,38,9])

def land(x,z):
    d=x-shore(z); old=previous_ground(x,z)
    if d<.1 or d>38 or z<0 or z>82: return old
    e=first_edge(z)
    low=.55*smooth(0,2.9,d)
    first=.70*smooth(e-.30,e+.20,d)
    second=2.35*smooth(second_edge(z)-.38,second_edge(z)+.28,d)
    third=2.65*smooth(third_edge(z)-.65,third_edge(z)+.45,d)
    for crossz in [61,44,29,12]:
        r=1-smooth(.8,1.9,abs(z-crossz))
        second+=(2.35*smooth(9.1,14.0,d)-second)*r
    # Broad sandy paths lead from each timber pier into a working clearing.
    opening=(1-smooth(1.0,2.0,pier_access(z)))
    first=first*(1-opening)+.70*smooth(1.6,4.0,d)*opening
    ground=low+first+second+third+.05*math.sin(z*.16)*smooth(3,6,d)
    # Modest unevenness in unbuilt ground; streets and building pads stay usable.
    ground+=(.07*math.sin(z*.81+d*.57)+.035*math.sin(z*1.9-d)) * smooth(6.7,7.4,d)
    preserve=0.0
    for s in SITES:
        dz=abs(z-s['gz']); dd=abs(d-s['d'])
        keep=(1-smooth(s['w']/2+.45,s['w']/2+1.2,dz))*(1-smooth(s['depth']/2+.65,s['depth']/2+1.2,dd))
        preserve=max(preserve,keep)
    # Keep the accepted cargo basin and every pier's shore-end contacts intact.
    cargo=(1-smooth(3.0,4.4,abs(z-65.2)))*(1-smooth(10,12,d))
    pier=(1-smooth(.8,1.5,pier_access(z)))*(1-smooth(2.2,3.1,d))
    preserve=max(preserve,cargo,pier)
    blend=smooth(0,4,z)*(1-smooth(77,82,z))*(1-smooth(33,38,d))*(1-preserve)
    return old+(ground-old)*blend

archive=bpy.data.collections.new('Archive_Space20_Ground')
bpy.context.scene.collection.children.link(archive)
old=terrain.copy();old.data=terrain.data.copy();old.name='Space20_BeforeGround';archive.objects.link(old)
archive.hide_render=True;archive.hide_viewport=True
C=bpy.data.collections['Reference_Terrain']
# More samples at the exposed grass lips; retain the broad offshore seabed.
offsets=sorted(set([-180,-120,-65,-35,-20,-12,-8,-5,-3,-2,-1,0]+[round(i*.25,4) for i in range(1,145)]+[40,65,120]))
zs=[-70+i*.75 for i in range(94)]+[i*.5 for i in range(165)]+[83+i*.75 for i in range(22)]
zs=sorted(set(zs));vs=[];fs=[]
for z in zs:
    for d in offsets:
        x=shore(z)+d;vs.append((x,-z,land(x,z)))
w=len(offsets)
for j in range(len(zs)-1):
    for i in range(w-1):
        a=j*w+i;fs.append((a,a+w,a+w+1,a+1))
temp=mesh('Space20_ShoreGround',vs,fs,terrain.data.materials[0]);terrain.data=temp.data
bpy.data.objects.remove(temp,do_unlink=True)
for p in terrain.data.polygons:p.use_smooth=False
bpy.context.view_layer.update()
ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
def ground(x,z):
    hit,n,i,dist=ground_bvh.ray_cast(Vector((x,-z,35)),Vector((0,0,-1)),100)
    assert hit is not None,(x,z)
    return hit.z

# Refit existing door aprons onto the edited continuous ground.
for ob in town.objects:
    if ob.name.startswith('Town20_ConnectedApron_'):
        inv=ob.matrix_world.inverted()
        for v in ob.data.vertices:
            p=ob.matrix_world@v.co;p.z=ground(p.x,-p.y)+.026;v.co=inv@p
        ob.data.update()

# Archive the row of decorative shrub coins and recompose them later as groups.
for ob in list(fol.objects):
    if ob.name.startswith(('L20_TerraceShrub','L20_ShrubLobe')):
        archive.objects.link(ob);fol.objects.unlink(ob)

C=fol;rr=random.Random(2026112002)
grass_mats=[]
for i,color in enumerate(['668337','6e8e3b','5b7931']):
    grass_mats.append(material('S20_Turf'+str(i),color,'plain'))
soil_mat=material('S20_RootSoil','746044','plain')
patches=[]
# Tufts grow along actual grass lips and around small side-garden islands.
for z in np.arange(3.0,78.0,.36):
    if access(z)<1.45 or pier_access(z)<1.6 or abs(z-65.2)<3.2:continue
    for level in [0,1,2]:
        if level==0: d=first_edge(z)+.38; width=.60
        elif level==1:d=second_edge(z)+.42;width=.62
        else:d=third_edge(z)+.70;width=1.4
        patches.append((d,z,width,.42))
for d,z,rx,rz in [(9.0,53.0,1.9,2.0),(9.1,35.8,1.7,1.6),(18.8,64.5,2.3,2.2),(19.0,51.8,1.8,1.7),(18.3,40.5,2.0,1.6),(9.1,19.8,1.5,1.2),(18.5,24.0,2.0,1.8)]:
    patches.append((d,z,rx,rz))
blade_verts=[];blade_faces=[];blade_mats=[]
for d,z,rx,rz in patches:
    for k in range(max(8,int(rx*rz*37))):
        a=rr.random()*math.tau;r=rr.random()**.5
        dz=z+math.sin(a)*rz*r;dd=d+math.cos(a)*rx*r
        if abs(dd-(5.6+.16*math.sin(dz*.15)))<1.05 or abs(dd-(13.9+.2*math.sin(dz*.13)))<.95:continue
        if access(dz)<1.05:continue
        x=shore(dz)+dd;h=ground(x,dz)-.025
        # Avoid bare cut faces: the geometry belongs to the grassy cap.
        if abs(ground(x+.1,dz)-ground(x-.1,dz))>.22:continue
        for j in range(3):
            angle=rr.random()*math.tau;length=rr.uniform(.08,.19);width=rr.uniform(.025,.048)
            dx=math.cos(angle)*width;dy=math.sin(angle)*width;lean=rr.uniform(.015,.05)
            n=len(blade_verts);blade_verts.extend([(x-dx,-dz-dy,h),(x+dx,-dz+dy,h),(x+math.sin(angle)*lean,-dz+math.cos(angle)*lean,h+length)])
            blade_faces.append((n,n+1,n+2));blade_mats.append(rr.randrange(3))
ob=mesh('S20_GrassCapTufts',blade_verts,blade_faces,grass_mats[0])
for m in grass_mats[1:]:ob.data.materials.append(m)
for p,i in zip(ob.data.polygons,blade_mats):p.material_index=i
# Narrow soil roots under selected lips give the edge real thickness.
for z0,z1 in [(46.0,47.7),(50.9,54.2),(55.1,59.0),(66.9,71.0),(32.1,36.2),(18.8,21.6)]:
    vv=[];ff=[]
    for z in np.arange(z0,z1+.15,.30):
        d=first_edge(z)+.20;x=shore(z)+d;h=ground(x,z)
        vv.extend([(x,-z,h-.04),(x-.08,-z,h-.20)])
    for i in range(len(vv)//2-1):a=i*2;ff.append((a,a+2,a+3,a+1))
    mesh('S20_GrassRootLip',vv,ff,soil_mat)

bpy.context.view_layer.update()
report={'terrain_vertices':len(vs),'terrain_faces':len(fs),'grass_triangles':len(blade_faces),'patches':len(patches)}
(LOG/'ground_report.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(report)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/reference_harbor_mcp.blend'))
