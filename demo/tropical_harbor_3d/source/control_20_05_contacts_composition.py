# Resolve the observed path/grass-strip problems and compose two shared edge clusters.
mesh=terrain.data;attr=mesh.color_attributes['LandUse']
for p in mesh.polygons:
    gx,gy,gh=p.center;gz=-gy;ddg=gx-float(shore(gz))
    if not 37.5<gz<60.5:continue
    # Sand remains a broad beach; no continuous 20cm green stripe at the foot.
    if gh<.35 and ddg<5:
        for li in p.loop_indices:attr.data[li].color=(0,0,0,0)
    # The sea access occupies the low break in the bank and meets the shared lane.
    if 51.6<gz<54.1 and .6<ddg<8.8:
        for li in p.loop_indices:attr.data[li].color=(0,0,1,0)
    # Road excavation has mineral side slopes, not stretched green triangles.
    if 49<gz<59 and 10.3<ddg<22.2 and p.normal.z<.78:
        if attr.data[p.loop_start].color[2]<.5:
            for li in p.loop_indices:attr.data[li].color=(0,1,0,0)
mesh.update();bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
def place(ob,gx,gz,scale=1,embed=.1):
    p=center(ob);ob.scale*=scale;bpy.context.view_layer.update()
    ob.location.x+=gx-p.x;ob.location.y+=-gz-p.y;bpy.context.view_layer.update()
    low=min((ob.matrix_world@v.co).z for v in ob.data.vertices)
    ob.location.z+=ground(gx,gz)-low-embed

# Three sizes overlap the rock foot and grass verge; their plan avoids the lane.
clusters=[('Bank_Boulder.008',15.0,44.8,1.25,.20),('Bank_Boulder.025',15.9,45.1,1.35,.18),('Bank_Boulder.007',14.6,45.5,1.0,.12),
          ('Bank_Boulder.005',20.5,55.6,1.25,.15),('Bank_Boulder.022',21.1,55.8,1.15,.15),('Bank_Boulder.003',20.0,56.1,1.0,.11)]
for name,gx,gz,scale,embed in clusters:place(bpy.data.objects[name],gx,gz,scale,embed)
for suffix,gx,gz in [('036',15.0,45.5),('037',16.3,45.1),('038',15.7,45.6),('039',14.4,45.3),('032',20.9,56.1),('033',19.8,55.8),('034',21.5,56.2),('035',20.4,56.5)]:
    ob=bpy.data.objects.get('S20_CourtyardShrub.'+suffix)
    if ob:place(ob,gx,gz,1.0,.09)

# Regrow only blades that have a real horizontal grass support beneath them.
growth=bpy.data.objects.get('L24_GrassTuftClusters')
if growth:
    vv=[];ff=[]
    for i in range(0,len(growth.data.vertices),3):
        vs=[growth.matrix_world@growth.data.vertices[i+k].co for k in range(3)]
        cx=(vs[0].x+vs[1].x)/2;cy=(vs[0].y+vs[1].y)/2
        hit,n,idx,_=ground_bvh.ray_cast(Vector((cx,cy,80)),Vector((0,0,-1)),300)
        if not hit:continue
        p=mesh.polygons[idx];color=attr.data[p.loop_start].color
        if n.z<.88 or color[0]<.6:continue
        shift=hit.z-.012-vs[0].z;base=len(vv)
        vv.extend([(v.x,v.y,v.z+shift) for v in vs]);ff.append((base,base+1,base+2))
    dm=bpy.data.meshes.new('C25_GrassRootedToActualFaces');dm.from_pydata(vv,[],ff);dm.update()
    dm.materials.append(growth.data.materials[0]);growth.data=dm;growth.matrix_world=Matrix.Identity(4)
refresh_height();export_land();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print('COMPOSITION two rock/shrub clusters, beach stripe removed, access connected, grass rooted')
