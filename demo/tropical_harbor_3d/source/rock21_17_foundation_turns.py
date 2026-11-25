exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
assert terrain.get('rock21_wide_forms') and not terrain.get('rock21_foundation_turns'),'Wrong stage'
src=(ROOT/'source/rock21_01_rebuild.py').read_text(encoding='utf8')
exec(src[src.index('def inside('):src.index('def cliff_value(')],globals())
floors=[[(p[0],-p[1]) for p in f['corners'][:4]] for f in found]
def ss(a,b,t):
    t=max(0.,min(1.,(t-a)/(b-a)));return t*t*(3-2*t)
def window(z,a,b,c,d):return ss(a,b,z)*(1-ss(c,d,z))
ca=mesh.color_attributes['LandUse'];cv={}
for p in mesh.polygons:
    for li in p.loop_indices:cv[mesh.loops[li].vertex_index]=np.array(ca.data[li].color)
count=0;flat=0;quay=0
for v in mesh.vertices:
    x,y,h=map(float,v.co);z=-y
    if not -15<z<66 or x<6 or x>35:continue
    if any(inside(x,z,p) for p in floors):continue
    col=cv.get(v.index,np.array([1,0,0,0],float)).copy()
    # Eliminate retained old spikes in the foundation buffer itself. Flat bearing
    # levels are taken from the actual floor, not the previous irregular cliff.
    nearest=min(enumerate(floors),key=lambda pair:edge_distance(x,z,pair[1]))
    k,poly=nearest;d=edge_distance(x,z,poly)
    if d<1.30 and z>35.7:
        w=1-ss(.20,1.30,d);target=found[k]['bounds'][2][0]-.315
        v.co.z=h*(1-w)+target*w
        col=col*(1-w)+np.array([1,0,0,0])*w;count+=1
    # Retain a shared working apron under the diner tables and entry steps.
    if 44.8<z<52.9 and 10.8<x<18.7:
        w=window(z,44.8,46.0,51.8,52.9)*ss(10.8,12.3,x)*(1-ss(18.1,18.7,x))
        v.co.z=float(v.co.z)*(1-w)+1.18*w
        col=col*(1-w)+np.array([.86,0,.14,0])*w;flat+=w>.01
    # Broad rounded earth return in front of the cargo basin. Do not touch the
    # hull's actual z>=63.432 footprint or its underwater bed.
    if 58.2<z<63.15 and 7.8<x<15:
        w=window(z,58.2,59.5,62.55,63.15)*ss(7.8,8.6,x)*(1-ss(14,15,x))
        t=ss(9.6,14.0,x);target=.24+.94*t
        v.co.z=float(v.co.z)*(1-w)+target*w
        g=ss(.28,.58,t);earth=ss(.09,.22,t)*(1-g)
        col=col*(1-w)+np.array([g,0,0,earth])*w;quay+=w>.01
    cv[v.index]=col
for p in mesh.polygons:
    for li in p.loop_indices:ca.data[li].color=cv[mesh.loops[li].vertex_index]
mesh.update();mesh.set_sharp_from_angle(angle=math.radians(62))
terrain['rock21_foundation_turns']=True
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
refresh_height();export_land();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print(json.dumps({'foundation_margin_vertices':count,'courtyard_vertices':flat,'quay_return_vertices':quay,'saved':True}))
