exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
assert terrain.get('rock21_relief') and not terrain.get('rock21_headland'),'Wrong stage'
src=(ROOT/'source/rock21_01_rebuild.py').read_text(encoding='utf8')
exec(src[src.index('def inside('):src.index('def cliff_value(')],globals())
changed=[]
for v in mesh.vertices:
    x,y,h=v.co;z=-y
    if not 38<z<63:continue
    ct=line(z,crown);ft=line(z,toe);lh=low(z);hh=high(z)
    if any(inside(x,z,p) or edge_distance(x,z,p)<.6 for p in floors):continue
    head=1.05*math.exp(-((z-44.0)/1.55)**4)+.70*math.exp(-((z-59.2)/1.8)**4)
    influence=float(smooth(ft-2.2,ft-.15,x))*(1-float(smooth(ct+.4,ct+3.3,x)))
    dx=head*influence
    if dx>.0001:
        v.co.x-=dx;changed.append(v.index)
    # A visibly broad, short shelf on one side of the first protruding mass.
    shelf=float(smooth(42.9,43.7,z)*(1-smooth(44.8,45.65,z)))
    if ft<x<ct and lh<h<hh and shelf>0:
        q=float(np.clip((h-lh)/(hh-lh),0,1))
        target=lh+(hh-lh)*float(np.interp(q,[0,.18,.34,.69,.82,1],[0,.18,.43,.49,.80,1]))
        v.co.z=h*(1-shelf)+target*shelf
mesh.update()
# Vary exposed soil by place: broad grass descent between the short earth cuts.
ca=mesh.color_attributes['LandUse']
newcols={}
for v in mesh.vertices:
    x,y,h=v.co;z=-y
    if not 42.2<z<48.1:continue
    ef=line(z,earthfoot);et=line(z,earthtop)
    if not ef<x<et+.1:continue
    w=float(smooth(42.2,43.7,z)*(1-smooth(46.3,48.1,z)))
    t=float(np.clip((x-ef)/(et-ef),0,1));g=float(smooth(.32,.49,t));s=float(smooth(.15,.27,t))*(1-g)
    newcols[v.index]=(np.array([g,0,0,s]),w)
for p in mesh.polygons:
    for li in p.loop_indices:
        i=mesh.loops[li].vertex_index
        if i in newcols:
            c,w=newcols[i];ca.data[li].color=tuple(np.array(ca.data[li].color)*(1-w)+c*w)
mesh.set_sharp_from_angle(angle=math.radians(58));mesh.update()
terrain['rock21_headland']=True
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
refresh_height();export_land();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print(json.dumps({'protruding_mass_vertices':len(changed),'grassed_descent_vertices':len(newcols)}))
