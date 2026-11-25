exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
assert terrain.get('rock21_prop_misclassification_corrected') and not terrain.get('rock21_clean_foot'),'Wrong stage'
src=(ROOT/'source/rock21_01_rebuild.py').read_text(encoding='utf8')
exec(src[src.index('def inside('):src.index('def cliff_value(')],globals())
src=(ROOT/'source/rock21_14_wide_forms.py').read_text(encoding='utf8')
exec(src[src.index('def ss('):src.index('old_vertex_colors=')],globals())
ca=mesh.color_attributes['LandUse'];colors={}
for p in mesh.polygons:
    for li in p.loop_indices:colors[mesh.loops[li].vertex_index]=np.array(ca.data[li].color)
changed=0
for v in mesh.vertices:
    x,y,h=map(float,v.co);z=-y
    if not 40.0<z<44.7 or not 15.2<x<20:continue
    if any(inside(x,z,p) for p in floors):continue
    w=window(z,40.0,41.0,43.6,44.7)*ss(15.2,15.8,x)*(1-ss(19.2,20,x))
    ft=line(z,newtoe);ct=line(z,newcrown);t=max(0,min(1,(x-ft)/(ct-ft)))
    q=float(np.interp(t,[0,.16,.30,.73,.87,1],[0,.025,.11,.89,.97,1]))
    target=low(z)+(line(z,crest)-low(z))*q
    v.co.z=h*(1-w)+target*w
    rock=ss(.1,.22,t)*(1-ss(.87,.97,t));col=np.array([1-rock,rock,0,0])
    colors[v.index]=colors.get(v.index,col)*(1-w)+col*w;changed+=1
for p in mesh.polygons:
    for li in p.loop_indices:ca.data[li].color=colors[mesh.loops[li].vertex_index]
mesh.update();mesh.set_sharp_from_angle(angle=math.radians(62))
terrain['rock21_clean_foot']=True
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
refresh_height();export_land();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print(json.dumps({'local_foot_vertices':changed,'saved':True}))
