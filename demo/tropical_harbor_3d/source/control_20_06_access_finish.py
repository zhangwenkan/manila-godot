mesh=terrain.data;bpy.context.view_layer.update();before_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
# Reuse the proven local road remesh, now with a narrow sea-entry route.
source=(ROOT/'source/control_20_03_path_topology.py').read_text(encoding='utf8')
source=source.replace('if 48.6<gz<58.8 and 10.3<ddg<22.2:','if 50.0<gz<56.1 and .1<ddg<10.3:')
source=source.replace("width=.62 if i<len(pathstations)-4 else .8","width=.55")
source=source.replace("if inpath:col=(0,0,1,0)","if inpath:col=(0,0,1,0) if p.x-float(shore(-p.y))>3.0 else (0,0,0,0)")
source=source[:source.index("print('ROCKS'")]
route=[(1.7,52.1,.28),(3.2,52.6,.45),(5.0,53.2,1.18),(7.0,53.2,1.18),(9.1,52.8,1.18)]
exec(source,globals())

mesh=terrain.data;attr=mesh.color_attributes['LandUse']
# The school stands on one upper court, with the ascent terminating beside it.
for v in mesh.vertices:
    gx,gy,gh=v.co;gz=-gy
    if 23.2<gx<29.0 and 56.6<gz<62.3 and gh>2.5:
        weight=(1-float(smooth(2.1,2.9,abs(gx-26.1))))*(1-float(smooth(2.15,2.85,abs(gz-59.1))))
        v.co.z=gh*(1-weight)+4.29*weight
mesh.update()
for p in mesh.polygons:
    gx,gy,gh=p.center;gz=-gy;ddg=gx-float(shore(gz))
    if 37.5<gz<60.5 and gh>1.6 and p.normal.z<.70:
        for li in p.loop_indices:
            if attr.data[li].color[0]>.5:attr.data[li].color=(0,1,0,0)
    if 50<gz<56.2 and ddg<3.05 and gh<.6:
        for li in p.loop_indices:attr.data[li].color=(0,0,0,0)
mesh.update();bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get());refresh_height();export_land()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print('ACCESS_FINISH narrow entrance blending into beach; school bearing court')
