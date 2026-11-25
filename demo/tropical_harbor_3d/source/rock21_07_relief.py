exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
assert terrain.get('rock21_contours') and not terrain.get('rock21_relief'),'Wrong stage'
src=(ROOT/'source/rock21_01_rebuild.py').read_text(encoding='utf8')
exec(src[src.index('def inside('):src.index('def cliff_value(')],globals())
before=[tuple(v.co) for v in mesh.vertices];moved=0
for v in mesh.vertices:
    x,y,h=v.co;z=-y
    if 37.8<z<63.3:
        ft=line(z,toe);ct=line(z,crown)
        if ft<x<ct and not any(inside(x,z,p) or edge_distance(x,z,p)<.75 for p in floors):
            t=(x-ft)/(ct-ft)
            a=.12+.13*(.5+.5*math.sin(z*2.1+.5))
            weight=float(smooth(37.8,39,z))*(1-float(smooth(62,63.3,z)))
            weight*=1-.9*float(smooth(49.8,51.2,z)*(1-smooth(53,55,z)))
            # x'(t) stays positive: broad convex faces cannot fold across each other.
            v.co.x=x-(ct-ft)*a*math.sin(math.pi*t)*weight;moved+=1
# A continuous fan of earth rounds into the cargo apron, stopping before the basin.
for v in mesh.vertices:
    x,y,h=v.co;z=-y
    if 57.8<z<61.0 and 8.7<x<14.8:
        w=float(smooth(57.8,58.7,z)*(1-smooth(60.3,61,z)))
        w*=float(smooth(8.7,9.5,x))*(1-float(smooth(13.9,14.8,x)))
        ef=line(z,earthfoot);et=line(z,earthtop)
        t=float(np.clip((x-ef)/(et-ef),0,1));target=.24+.94*float(smooth(0,1,t))
        v.co.z=h*(1-w)+target*w
        col=(float(smooth(.64,.74,t)),0,0,float(smooth(.18,.32,t))*(1-float(smooth(.64,.74,t))))
        for p in []:pass
mesh.update()
ca=mesh.color_attributes['LandUse']
for p in mesh.polygons:
    for li in p.loop_indices:
        v=mesh.vertices[mesh.loops[li].vertex_index];x,y,h=v.co;z=-y
        if 57.8<z<61 and 8.7<x<14.8:
            w=float(smooth(57.8,58.7,z)*(1-smooth(60.3,61,z)))*float(smooth(8.7,9.5,x))*(1-float(smooth(13.9,14.8,x)))
            t=float(np.clip((x-line(z,earthfoot))/(line(z,earthtop)-line(z,earthfoot)),0,1));g=float(smooth(.64,.74,t));s=float(smooth(.18,.32,t))*(1-g)
            old=np.array(ca.data[li].color);ca.data[li].color=tuple(old*(1-w)+np.array([g,0,0,s])*w)
mesh.set_sharp_from_angle(angle=math.radians(58));mesh.update()
terrain['rock21_relief']=True
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
refresh_height();export_land();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print(json.dumps({'convex_face_vertices':moved,'cargo_bounds':{n:bounds(bpy.data.objects[n]) for n in ['R20_UpperHull','R20_LowerHull','R20_HullBottom']}}))
