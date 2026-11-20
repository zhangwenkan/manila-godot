# Verified Blender MCP payload; reposition entire reusable assemblies.
def center(ob):
    return sum((ob.matrix_world@Vector(p) for p in ob.bound_box),Vector())/8
def foot(ob):
    ps=[ob.matrix_world@v.co for v in ob.data.vertices];low=min(p.z for p in ps)
    bottom=[p for p in ps if p.z<low+.04]
    return sum(bottom,Vector())/len(bottom)
def suffix(ob):
    s=ob.name.rsplit('.',1)[-1];return int(s) if s.isdigit() else 0
moved=set();moves=[]
def reground(obs,x,z):
    dh=ground(x,z)-old_ground(x,z)
    for ob in obs:
        if ob.name in moved:continue
        ob.matrix_world=Matrix.Translation((0,0,dh))@BASE[ob.name];moved.add(ob.name)
    moves.append({'x':x,'z':z,'delta':dh,'objects':[o.name for o in obs]})
for s in SITES:
    obs=[o for o in town.objects if o.get('town_building')==s['name']]
    reground(obs,s['center'][0],s['gz'])
trunks=sorted([o for o in fol.objects if o.name=='Tree_Trunk' or o.name.startswith('Tree_Trunk.')],key=suffix)
crowns=sorted([o for o in fol.objects if o.name.startswith('D19_Tree_Crown')],key=suffix)
branches=sorted([o for o in fol.objects if o.name=='Tree_Branch' or o.name.startswith('Tree_Branch.')],key=suffix)
assert len(crowns)==len(trunks)*6 and len(branches)==len(trunks)*5
for i,t in enumerate(trunks):
    p=foot(t);reground([t]+crowns[i*6:(i+1)*6]+branches[i*5:(i+1)*5],p.x,-p.y)
palms=sorted([o for o in fol.objects if o.name=='Palm_Trunk' or o.name.startswith('Palm_Trunk.')],key=suffix)
parts={k:sorted([o for o in fol.objects if o.name.startswith(prefix)],key=suffix) for k,prefix in [('rachis','D19_Palm_FrondRachis'),('leaves','D19_Palm_FrondLeaflets'),('nuts','Palm_Coconut'),('rings','D19_Palm_GrowthRing')]}
assert all(len(parts[k])==len(palms)*n for k,n in [('rachis',8),('leaves',8),('nuts',3),('rings',12)])
for i,t in enumerate(palms):
    p=foot(t);obs=[t]+parts['rachis'][i*8:(i+1)*8]+parts['leaves'][i*8:(i+1)*8]+parts['nuts'][i*3:(i+1)*3]+parts['rings'][i*12:(i+1)*12];reground(obs,p.x,-p.y)
for ob in list(fol.objects):
    if ob.name in moved:continue
    p=center(ob);reground([ob],p.x,-p.y)
    if ob.name.startswith('S20_CourtyardShrub'):
        ps=[ob.matrix_world@v.co for v in ob.data.vertices];low=min(v.z for v in ps)
        ob.location.z+=ground(p.x,-p.y)-low-.10
remaining=[o for o in coast.objects if not o.name.startswith(('Pier_','Arrival_','Pile_Lashing','S20_DeckPeg','S20_PileEndGrain','S20_MooringKnot','S20_RopeTail','S20_PileBracket','D19_Deck','D19_Pile','D19_Mooring','D19_RopeTail'))]
floors=[o for o in remaining if o.name.startswith('Hut_Floor')];hutgroups={o.name:[] for o in floors}
for ob in remaining:
    if ob.name.startswith(('Hut_','D19_Hut','D19_Thatch','D19_Reed')):
        p=center(ob);f=min(floors,key=lambda f:(center(f).xy-p.xy).length);hutgroups[f.name].append(ob)
for f in floors:
    p=center(f);reground(hutgroups[f.name],p.x,-p.y)
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
    p=sum((center(o) for o in objects),Vector())/len(objects);reground(objects,p.x,-p.y)
for ob in bpy.data.collections['Reference_Rocks'].objects:
    p=center(ob);reground([ob],p.x,-p.y)
bpy.context.view_layer.update()
(LOG/'regrounded_assemblies.json').write_text(json.dumps(moves,indent=2),encoding='utf8')

# Small growth clusters break the silhouette, rooted in the continuous grass.
# They do not form another covering sheet and are exported as non-colliding leaves.
rng=random.Random(231120);vv=[];ff=[];cc=[];accepted=0
for k in range(8500):
    z=rng.uniform(1,81);d=rng.uniform(2.5,30)
    h,g,b,p=new_sample(d,z)
    if g<.90 or p>.15 or b>.15:continue
    if math.sin(z*.88+d*1.27)+math.sin(z*2.13-d*.73)<.65:continue
    if accepted>=1500:break
    x=shore(z)+d;h=ground(x,z)-.015;accepted+=1
    for n in range(4):
        angle=rng.uniform(0,math.tau);w=rng.uniform(.025,.042);height=rng.uniform(.075,.16)
        dx=math.cos(angle);dy=math.sin(angle);cx=x+rng.uniform(-.09,.09);cy=-z+rng.uniform(-.09,.09);root=ground(cx,-cy)-.018
        a=len(vv);vv.extend([(cx-w*dx,cy-w*dy,root),(cx+w*dx,cy+w*dy,root),(cx+dy*.045,cy-dx*.045,root+height)])
        ff.append((a,a+1,a+2));tone=rng.uniform(.90,1.08);cc.extend([(tone*.37,tone*.48,tone*.16,1)]*3)
tm=bpy.data.meshes.new('S23_RootedGrassAccents');tm.from_pydata(vv,[],ff);tm.update();tufts=bpy.data.objects.new('S23_GrassTufts',tm);fol.objects.link(tufts)
mat=material('S23_GrassGrowth','66852e','plain');mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.98;mat.use_backface_culling=False;tm.materials.append(mat)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_landscape_redesign_mcp.blend'))
print('REGROUNDED',len(moved),'components','growth clusters',accepted,'triangles',len(ff))
