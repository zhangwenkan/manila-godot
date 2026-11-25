exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
assert terrain.get('rock21_repaired') and not terrain.get('rock21_grounded'),'Wrong stage'
raw=np.load(str(LOG/'terrain_before.npz'));old={k:raw[k] for k in raw.files};raw.close()
oldfaces=[old['loops'][s:s+n].tolist() for s,n in zip(old['starts'],old['sizes'])]
old_bvh=BVHTree.FromPolygons([Vector(p) for p in old['positions']],oldfaces)
def oldground(x,z):
    h,*_=old_bvh.ray_cast(Vector((float(x),-float(z),80)),Vector((0,0,-1)),300)
    return h.z if h else -15
def foot(o):
    ps=[o.matrix_world@v.co for v in o.data.vertices];m=min(p.z for p in ps)
    low=[p for p in ps if p.z<m+.04];return sum(low,Vector())/len(low)
def suffix(o):
    s=o.name.rsplit('.',1)[-1];return int(s) if s.isdigit() else 0
def region(p):return 35.7<-p.y<66 and 6<p.x<38
moved=[]
def shift(obs,dz,dx=0,dy=0):
    if abs(dz)+abs(dx)+abs(dy)<.001:return
    for o in obs:o.location+=Vector((dx,dy,dz))
    moved.append({'objects':[o.name for o in obs],'delta':[dx,dy,dz]})
fol=bpy.data.collections['Reference_Foliage']
trunks=sorted([o for o in fol.objects if o.name=='Tree_Trunk' or o.name.startswith('Tree_Trunk.')],key=suffix)
crowns=sorted([o for o in fol.objects if o.name.startswith('D19_Tree_Crown')],key=suffix)
branches=sorted([o for o in fol.objects if o.name=='Tree_Branch' or o.name.startswith('Tree_Branch.')],key=suffix)
assert len(crowns)==len(trunks)*6 and len(branches)==len(trunks)*5
for i,t in enumerate(trunks):
    p=foot(t)
    if region(p):shift([t]+crowns[i*6:(i+1)*6]+branches[i*5:(i+1)*5],ground(p.x,-p.y)-p.z-.09)
palms=sorted([o for o in fol.objects if o.name=='Palm_Trunk' or o.name.startswith('Palm_Trunk.')],key=suffix)
parts={k:sorted([o for o in fol.objects if o.name.startswith(prefix)],key=suffix) for k,prefix in [('rachis','D19_Palm_FrondRachis'),('leaves','D19_Palm_FrondLeaflets'),('nuts','Palm_Coconut'),('rings','D19_Palm_GrowthRing')]}
assert all(len(parts[k])==len(palms)*n for k,n in [('rachis',8),('leaves',8),('nuts',3),('rings',12)])
for i,t in enumerate(palms):
    p=foot(t)
    if region(p):shift([t]+parts['rachis'][i*8:(i+1)*8]+parts['leaves'][i*8:(i+1)*8]+parts['nuts'][i*3:(i+1)*3]+parts['rings'][i*12:(i+1)*12],ground(p.x,-p.y)-p.z-.07)
bpy.context.view_layer.update()
# Pull the former shelf shrubs down to the two feet of the exposed headland.
placements={'S20_CourtyardShrub.036':(16.0,43.7),'S20_CourtyardShrub.037':(17.4,45.6),'S20_CourtyardShrub.038':(17.1,45.2),'S20_CourtyardShrub.039':(15.8,43.5)}
for o in fol.objects:
    if not o.name.startswith('S20_CourtyardShrub'):continue
    p=center(o)
    if not region(p):continue
    if o.name in placements:
        x,z=placements[o.name];o.location.x+=x-p.x;o.location.y+=-z-p.y;bpy.context.view_layer.update();p=center(o)
    b=bounds(o);dh=ground(p.x,-p.y)-b[2][0]-.11;shift([o],dh)
bpy.context.view_layer.update()
rock_places={'Bank_Boulder.008':(15.65,43.8),'Bank_Boulder.025':(17.3,45.5),'Bank_Boulder.007':(15.7,44.6)}
for o in bpy.data.collections['Reference_Rocks'].objects:
    if o.type!='MESH':continue
    p=center(o)
    if not region(p):continue
    if o.name in rock_places:
        x,z=rock_places[o.name];o.location.x+=x-p.x;o.location.y+=-z-p.y;bpy.context.view_layer.update();p=center(o)
    dh=ground(p.x,-p.y)-bounds(o)[2][0]-min(.30,o.dimensions.z*.2);shift([o],dh)
# Coast props move as touching groups. A bounded box check excludes unaffected piers and houses.
excluded=('Hut_','D19_Hut','D19_Thatch','D19_Reed','Pier_','Arrival_','Pile_Lashing','S20_DeckPeg','S20_PileEndGrain','S20_MooringKnot','S20_RopeTail','S20_PileBracket','D19_Deck','D19_Pile','D19_Mooring','D19_RopeTail')
obs=[o for o in bpy.data.collections['Reference_Coast'].objects if o.type=='MESH' and not o.name.startswith(excluded) and region(center(o))]
bb=[bounds(o) for o in obs];parent=list(range(len(obs)))
def find(a):
    while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
    return a
for i,b in enumerate(bb):
    for j in range(i):
        a=bb[j]
        if b[0][0]<=a[0][1]+.07 and b[0][1]>=a[0][0]-.07 and b[1][0]<=a[1][1]+.07 and b[1][1]>=a[1][0]-.07:parent[find(i)]=find(j)
groups={}
for i,o in enumerate(obs):groups.setdefault(find(i),[]).append(o)
for group in groups.values():
    support=min(group,key=lambda o:bounds(o)[2][0]);p=foot(support)
    # Preserve the assembly's original intended foot offset while matching new terrain.
    oldgap=p.z-oldground(p.x,-p.y);targetgap=max(-.08,min(.04,oldgap))
    delta=ground(p.x,-p.y)-p.z+targetgap
    if abs(ground(p.x,-p.y)-oldground(p.x,-p.y))>.02:shift(group,delta)
bpy.context.view_layer.update()
# Replant grass blades using exact final surface heights and grass role.
growth=bpy.data.objects['L24_GrassTuftClusters'];vv=[];ff=[];removed=0;replanted=0;attr=mesh.color_attributes['LandUse']
for i in range(0,len(growth.data.vertices),3):
    vs=[growth.matrix_world@growth.data.vertices[i+k].co for k in range(3)]
    x=(vs[0].x+vs[1].x)/2;y=(vs[0].y+vs[1].y)/2
    if 35.5<-y<66.5:
        hit,n,pi,_=ground_bvh.ray_cast(Vector((x,y,80)),Vector((0,0,-1)),300)
        color=np.mean([attr.data[li].color for li in mesh.polygons[pi].loop_indices],axis=0) if pi is not None else [0]
        if not hit or n.z<.83 or color[0]<.65:removed+=1;continue
        dh=hit.z-.012-min(vs[0].z,vs[1].z);replanted+=1
    else:dh=0
    a=len(vv);vv.extend((v.x,v.y,v.z+dh) for v in vs);ff.append((a,a+1,a+2))
gm=bpy.data.meshes.new('R27_RootedGrass');gm.from_pydata(vv,[],ff);gm.update();gm.materials.append(growth.data.materials[0]);growth.data=gm;growth.matrix_world=Matrix.Identity(4)
terrain['rock21_grounded']=True
(LOG/'grounding_changes.json').write_text(json.dumps({'moves':moved,'grass_removed':removed,'grass_replanted':replanted},indent=2),encoding='utf8')
export_collection('Reference_Foliage','foliage.glb');export_collection('Reference_Rocks','rocks.glb');export_collection('Reference_Coast','coast.glb')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print(json.dumps({'groups_moved':len(moved),'components_moved':sum(len(r['objects']) for r in moved),'grass_removed':removed,'grass_replanted':replanted,'saved':True}))
