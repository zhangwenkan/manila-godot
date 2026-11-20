# A restrained number of rooted silhouettes; no covering turf sheet.
rng=random.Random(20499);vertices=[];faces=[];accepted=0
attr=terrain.data.color_attributes['LandUse']
polys=terrain.data.polygons
for k in range(34000):
    gz=rng.uniform(1,81);ddg=rng.uniform(1.5,27);gx=float(shore(gz))+ddg
    hit,n,idx,_=ground_bvh.ray_cast(Vector((gx,-gz,80)),Vector((0,0,-1)),300)
    if hit is None or n.z<.88 or hit.z<.3:continue
    color=sum((Vector(attr.data[v].color) for v in polys[idx].vertices),Vector((0,0,0,0)))/len(polys[idx].vertices)
    if color.x<.75 or color.z>.12:continue
    # Patches leave open lawns and preserve the paths and useful yard spaces.
    patch=math.sin(gx*.46+gz*.37)+.7*math.sin(gx*.83-gz*.29)
    if patch<.25:continue
    for blade in range(rng.randint(3,5)):
        angle=rng.uniform(0,math.tau);bx=gx+rng.uniform(-.1,.1);bz=gz+rng.uniform(-.1,.1)
        root=ground(bx,bz)-.012;w=rng.uniform(.018,.034);tall=rng.uniform(.09,.20);dx=math.cos(angle);dy=math.sin(angle)
        start=len(vertices)
        vertices.extend([(bx-w*dx,-bz-w*dy,root),(bx+w*dx,-bz+w*dy,root),(bx+dy*.045,-bz-dx*.045,root+tall)])
        faces.append((start,start+1,start+2))
    accepted+=1
    if accepted>=2400:break
mesh=bpy.data.meshes.new('L24_RootedGrowth');mesh.from_pydata(vertices,[],faces);mesh.update()
ob=bpy.data.objects.new('L24_GrassTuftClusters',mesh);fol.objects.link(ob)
gm=bpy.data.materials.new('Ref_L24_GrassGrowth');gm.use_nodes=True
bs=gm.node_tree.nodes.get('Principled BSDF');rgb=np.array([99,126,48])/255
bs.inputs['Base Color'].default_value=(*np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4),1)
bs.inputs['Roughness'].default_value=.98;bs.inputs['Specular IOR Level'].default_value=.08;gm.use_backface_culling=False
mesh.materials.append(gm)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_landform_mass_mcp.blend'))
print('ROOTED_GROWTH',accepted,'clusters',len(faces),'blade triangles')
