# Inspect contact on the actual current Blender surface before final export.
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
support=[]
for s in SITES:
    cx,cz=s['center'][0],s['gz'];ddsite=s['depth'];wwsite=s['w']
    samples=[ground(cx+dx,cz+dz) for dx in [-ddsite*.45,0,ddsite*.45] for dz in [-wwsite*.45,0,wwsite*.45]]
    obs=[ob for ob in town.objects if ob.get('town_building')==s['name']]
    support.append({'name':s['name'],'height':ground(cx,cz),'spread':max(samples)-min(samples),'objects':len(obs)})
print('BUILDING_SUPPORT',json.dumps(support))
(LOG/'building_support_final.json').write_text(json.dumps(support,indent=2),encoding='utf8')
# Trees remain rooted after the refinements; relocate only roots on exposed cliffs.
tree_moves=[]
for i,t in enumerate(trunks):
    p=foot(t);hit,n,*_=ground_bvh.ray_cast(Vector((p.x,p.y,80)),Vector((0,0,-1)),300)
    dx=dy=0
    if hit and n.z<.7:
        candidates=[]
        for dist in [.8,1.4,2.0,2.6]:
            for a in np.arange(0,math.tau,math.pi/4):
                cx=p.x+dist*math.cos(a);cy=p.y+dist*math.sin(a)
                q,nn,*_=ground_bvh.ray_cast(Vector((cx,cy,80)),Vector((0,0,-1)),300)
                if q and nn.z>.91:candidates.append((dist,abs(q.z-hit.z),cx,cy,q.z))
            if candidates:break
        if candidates:
            q=min(candidates);dx=q[2]-p.x;dy=q[3]-p.y
    delta=ground(p.x+dx,-p.y-dy)-p.z-.09
    obs=[t]+crowns[i*6:(i+1)*6]+branches[i*5:(i+1)*5]
    for ob in obs:ob.location+=Vector((dx,dy,delta))
    if dx or dy:tree_moves.append({'tree':t.name,'dx':dx,'dy':dy})
for i,t in enumerate(palms):
    p=foot(t);delta=ground(p.x,-p.y)-p.z-.07
    obs=[t]+parts['rachis'][i*8:(i+1)*8]+parts['leaves'][i*8:(i+1)*8]+parts['nuts'][i*3:(i+1)*3]+parts['rings'][i*12:(i+1)*12]
    for ob in obs:ob.location.z+=delta
for ob in fol.objects:
    if ob.name.startswith('S20_CourtyardShrub'):
        p=center(ob);low=min((ob.matrix_world@v.co).z for v in ob.data.vertices);ob.location.z+=ground(p.x,-p.y)-low-.1
print('TREE_MOVES',json.dumps(tree_moves))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_landform_mass_mcp.blend'))
