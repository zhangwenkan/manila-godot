# Actual support correction for reused assets, through Blender MCP.
contact_changes=[]
def translate_to_ground(objects,x,z,embed=.02):
    ps=[ob.matrix_world@Vector(p) for ob in objects for p in ob.bound_box]
    minx,maxx=min(p.x for p in ps),max(p.x for p in ps)
    miny,maxy=min(p.y for p in ps),max(p.y for p in ps)
    minz=min(p.z for p in ps);cx=(minx+maxx)/2;cy=(miny+maxy)/2
    dx,dy=x-cx,-z-cy
    samples=[ground(x+(maxx-minx)*a,z+(maxy-miny)*b) for a,b in [(0,0),(-.4,-.4),(-.4,.4),(.4,-.4),(.4,.4)]]
    dz=max(samples)-minz-embed
    for ob in objects:ob.matrix_world=Matrix.Translation((dx,dy,dz))@ob.matrix_world
    contact_changes.append({'objects':len(objects),'x':x,'z':z,'support_spread':max(samples)-min(samples),'delta':[dx,dy,dz]})

for item in moves:
    names=[n for n in item['objects'] if not n.startswith('S20_Net')]
    if not any(n.startswith('S20_fishing') for n in names):continue
    objects=[bpy.data.objects[n] for n in names];z=item['z']
    if 44<z<46.2:target_d=6.0
    elif 46.2<=z<48:target_d=1.75
    elif 40<z<44:target_d=1.95
    else:target_d=7.0
    translate_to_ground(objects,shore(z)+target_d,z)
netobjects=[o for o in coast.objects if o.name.startswith('S20_Net')]
translate_to_ground(netobjects,shore(41.1)+2.0,41.1,.06)

# Tree and palm bases must meet the real surface; old offsets are not trusted.
for i,t in enumerate(trunks):
    p=foot(t);delta=ground(p.x,-p.y)-p.z-.10
    for ob in [t]+crowns[i*6:(i+1)*6]+branches[i*5:(i+1)*5]:ob.location.z+=delta
for i,t in enumerate(palms):
    p=foot(t);delta=ground(p.x,-p.y)-p.z-.075
    obs=[t]+parts['rachis'][i*8:(i+1)*8]+parts['leaves'][i*8:(i+1)*8]+parts['nuts'][i*3:(i+1)*3]+parts['rings'][i*12:(i+1)*12]
    for ob in obs:ob.location.z+=delta
removed=0
for ob in list(fol.objects):
    if not ob.name.startswith('Grass_Tuft'):continue
    p=center(ob);d=p.x-shore(-p.y);h,g,soil,path=new_sample(d,-p.y)
    if g<.8 or soil>.15:
        archive.objects.link(ob);fol.objects.unlink(ob);removed+=1
    else:
        low=min((ob.matrix_world@v.co).z for v in ob.data.vertices);ob.location.z+=ground(p.x,-p.y)-low-.025

# Dense small growth occurs at shoulders and garden edges, not on vertical soil.
ob=bpy.data.objects['S23_GrassTufts'];bpy.data.objects.remove(ob,do_unlink=True)
rng=random.Random(231126);vv=[];ff=[];accepted=0
for k in range(48000):
    z=rng.uniform(.5,81.5)
    if k%3==0:d=edge(z)+rng.uniform(.75,2.2)
    elif k%3==1:d=rng.uniform(10.8,15.3)
    else:d=rng.uniform(4.5,25)
    h,g,soil,path=new_sample(d,z)
    if g<.86 or soil>.15 or path>.18:continue
    if math.sin(z*1.14+d*1.71)+.6*math.sin(z*2.1-d*.91)<-.2:continue
    x=shore(z)+d;accepted+=1
    for n in range(3):
        angle=rng.uniform(0,math.tau);w=rng.uniform(.019,.033);height=rng.uniform(.065,.135)
        dx=math.cos(angle);dy=math.sin(angle);cx=x+rng.uniform(-.08,.08);cy=-z+rng.uniform(-.08,.08);root=ground(cx,-cy)-.012
        a=len(vv);vv.extend([(cx-w*dx,cy-w*dy,root),(cx+w*dx,cy+w*dy,root),(cx+dy*.035,cy-dx*.035,root+height)]);ff.append((a,a+1,a+2))
    if accepted>=7000:break
tm=bpy.data.meshes.new('S23_RootedGrassGrowth');tm.from_pydata(vv,[],ff);tm.update();tufts=bpy.data.objects.new('S23_GrassTufts',tm);fol.objects.link(tufts);tm.materials.append(bpy.data.materials['Ref_S23_GrassGrowth'])
(LOG/'contact_corrections.json').write_text(json.dumps({'groups':contact_changes,'old_wall_tufts_archived':removed,'new_rooted_clusters':accepted},indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_landscape_redesign_mcp.blend'))
print('CONTACTS',contact_changes,'old wall tufts',removed,'new clusters',accepted)
