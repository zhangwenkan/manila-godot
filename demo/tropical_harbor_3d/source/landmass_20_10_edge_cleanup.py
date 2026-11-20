# Smooth sampling teeth on the small banks, keeping broad authored plans.
import bmesh
bm=bmesh.new();bm.from_mesh(terrain.data);bm.verts.ensure_lookup_table()
selected=[]
for v in bm.verts:
    gx,gy,gh=v.co;gz=-gy;gd=gx-float(shore(gz))
    if not (.6<gd<22 and -8<gz<82):continue
    if abs(gz-65.2)<4.7 and gx<19.6:continue
    if any(abs(gx-s['center'][0])<s['depth']*.5+.4 and abs(gz-s['gz'])<s['w']*.5+.4 for s in SITES):continue
    if v.normal.z<.96:selected.append(v)
for iteration in range(3):bmesh.ops.smooth_vert(bm,verts=selected,factor=.38,use_axis_x=True,use_axis_y=True,use_axis_z=True)
bm.to_mesh(terrain.data);bm.free();terrain.data.update()
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
refresh_height()
# Re-root every blade on the final smoothed surface.
growth=bpy.data.objects['L24_GrassTuftClusters']
for i in range(0,len(growth.data.vertices),3):
    vs=[growth.data.vertices[i+k] for k in range(3)]
    cx=(vs[0].co.x+vs[1].co.x)/2;cy=(vs[0].co.y+vs[1].co.y)/2
    dz=ground(cx,-cy)-.012-vs[0].co.z
    for v in vs:v.co.z+=dz
growth.data.update();export_land()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_landform_mass_mcp.blend'))
print('EDGE_CLEANUP',len(selected),'vertices smoothed locally; height queries and growth roots updated')
